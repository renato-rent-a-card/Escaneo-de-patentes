FROM python:3.11-slim

WORKDIR /app
ENV TZ=America/Santiago

COPY templates/requirements.txt .
RUN pip install --no-cache-dir --default-timeout=300 --retries=10 \
	--extra-index-url https://download.pytorch.org/whl/cpu \
	-r requirements.txt

COPY templates/ .
RUN mkdir -p static/uploads

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]