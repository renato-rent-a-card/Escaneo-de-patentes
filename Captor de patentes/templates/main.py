import os
import datetime
import json
import re
from io import BytesIO
from urllib.request import Request as UrlRequest, urlopen
from urllib.error import HTTPError, URLError
import numpy as np
from PIL import Image
from fastapi import FastAPI, Body, File, UploadFile, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import easyocr

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

app = FastAPI(title="ANPR Human-in-the-Loop")

# Configuración de Google Sheets (Fallback en caso de no usar n8n)
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SERVICE_ACCOUNT_FILE = 'credentials.json'
SPREADSHEET_ID = '1lwGSMRrhQm9yx-cSE3BmCMWnWYzl1X5S32cFbht_eZo'
RANGE_NAME = 'sheet1!A:F'

# Configuración del Webhook de n8n (reemplaza con tu URL de producción cuando esté activo)
N8N_WEBHOOK_URL = os.getenv(
    "N8N_WEBHOOK_URL", 
    "https://chileanrentacar.app.n8n.cloud/webhook/guardar-patente"
).strip()

def append_to_sheet(row_data: list):
    """Inserta una fila de datos al final de Google Sheets directamente."""
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('sheets', 'v4', credentials=creds)
    sheet = service.spreadsheets()
    
    body = {'values': [row_data]}
    
    return sheet. values().append(
        spreadsheetId=SPREADSHEET_ID,
        range=RANGE_NAME,
        valueInputOption='USER_ENTERED',
        body=body
    ).execute()

def send_to_n8n(record: dict):
    """Envía la información de la patente a n8n mediante HTTP POST."""
    if not N8N_WEBHOOK_URL:
        return False

    request = UrlRequest(
        N8N_WEBHOOK_URL,
        data=json.dumps(record).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=10) as response:
        if response.status < 200 or response.status >= 300:
            raise RuntimeError(f"n8n devolvió HTTP {response.status}")
    return True

# Carpetas para archivos estáticos e imágenes subidas
UPLOAD_DIR = "static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory=".")

# Carga perezosa de EasyOCR
reader = None

def normalize_plate(value: str) -> str:
    """Conserva solo letras y números y normaliza el texto a mayúsculas."""
    return re.sub(r"[^A-Za-z0-9]", "", value).upper()

def persist_record(detected_text: str, final_text: str, confidence: float = 0.0) -> dict:
    """Guarda un registro sin conservar la imagen original."""
    detected_text = normalize_plate(detected_text)
    final_text = normalize_plate(final_text)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    is_corrected = detected_text != final_text

    record = {
        "timestamp": timestamp,
        "image_url": "",
        "detected_text": detected_text,
        "final_text": final_text,
        "confidence": confidence,
        "is_corrected": "SI" if is_corrected else "NO",
        "status": "CONFIRMADA"
    }
    row_data = [
        timestamp,
        final_text,
        detected_text,
        "SI" if is_corrected else "NO",
        "",
        "CONFIRMADA"
    ]

    if N8N_WEBHOOK_URL:
        send_to_n8n(record)
    else:
        append_to_sheet(row_data)
    return record

def select_plate_result(results: list) -> tuple[str, float]:
    """Elige el texto más probable de ser una patente entre los resultados OCR."""
    ignored_words = {"CHILE", "PATENTE", "MERCOSUR", "REPUBLICA"}
    candidates = []

    for _, raw_text, confidence in results:
        text = normalize_plate(raw_text)
        if text in ignored_words or len(text) < 4:
            continue

        letters = sum(character.isalpha() for character in text)
        digits = sum(character.isdigit() for character in text)
        score = float(confidence)
        if letters and digits:
            score += 0.35
        if 5 <= len(text) <= 8:
            score += 0.15
        if digits >= 2:
            score += 0.10
        candidates.append((score, text, float(confidence)))

    if not candidates:
        return "", 0.0

    _, text, confidence = max(candidates, key=lambda candidate: candidate[0])
    return text, confidence

def get_reader():
    global reader
    if reader is None:
        reader = easyocr.Reader(['es', 'en'], gpu=False)
    return reader

@app.get("/", response_class=HTMLResponse)
async def read_index(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"request": request},
    )

@app.post("/api/scan")
async def scan_plate(file: UploadFile = File(...)):
    image_data = await file.read()

    # Procesar la imagen en memoria para no conservar archivos subidos.
    with Image.open(BytesIO(image_data)) as image:
        image.thumbnail((1600, 1600))
        image_array = np.asarray(image.convert("RGB"))

    # Inferencia con EasyOCR
    results = get_reader().readtext(image_array)

    detected_text, confidence = select_plate_result(results)

    return {
        "detected_text": detected_text,
        "confidence": round(float(confidence) * 100, 2)
    }

@app.post("/api/save")
async def save_plate(
    image_url: str = Form(""),
    detected_text: str = Form(...),
    final_text: str = Form(...)
):
    try:
        record = persist_record(detected_text, final_text)
    except Exception as e:
        print(f"Error al guardar el registro: {e}")
        return JSONResponse(
            status_code=502,
            content={"status": "error", "message": f"No se pudo guardar el registro: {e}"}
        )
    
    print("\n--- NUEVA PATENTE ENVIADA A N8N ---")
    print(record)
    print("-----------------------------------\n")
    
    return JSONResponse(status_code=200, content={"status": "success", "data": record})

@app.post("/api/save-batch")
async def save_batch(payload: dict = Body(...)):
    records = payload.get("records", [])
    if not isinstance(records, list) or not records:
        return JSONResponse(status_code=400, content={"status": "error", "message": "La lista está vacía."})

    saved_records = []
    try:
        for item in records:
            final_text = normalize_plate(str(item.get("final_text", "")))
            if not final_text:
                continue
            saved_records.append(persist_record(
                str(item.get("detected_text", "")),
                final_text,
                float(item.get("confidence", 0))
            ))
    except Exception as e:
        print(f"Error al guardar la lista: {e}")
        return JSONResponse(
            status_code=502,
            content={"status": "error", "message": f"No se pudo guardar la lista: {e}"}
        )

    return JSONResponse(status_code=200, content={"status": "success", "data": saved_records})