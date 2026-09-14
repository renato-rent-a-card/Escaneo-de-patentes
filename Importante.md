# Captor de Patentes

Sistema de escaneo y reconocimiento de patentes vehiculares implementado con FastAPI, EasyOCR y PyTorch, desplegado mediante contenedores Docker y expuesto de forma segura mediante Cloudflare Tunnels.

---

## 🛠️ Tecnologías Utilizadas

- **Backend / OCR**: Python 3.11, FastAPI, EasyOCR, PyTorch (CPU)
- **Servidor Web**: Uvicorn
- **Contenedores**: Docker & Docker Compose
- **Túnel de Red**: Cloudflare Cloudflared

---

## 📋 Requisitos Previos

Asegúrate de tener instalados los siguientes componentes antes de comenzar:

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (debe estar en ejecución)
- [Git](https://git-scm.com/)

---

## 🚀 Guía de Instalación y Despliegue

### 1. Clonar el Repositorio

Abre tu terminal o consola de comandos y ejecuta:

```bash
git clone https://github.com/renato-rent-a-card/Escaneo-de-patentes.git
cd Escaneo-de-patentes
```

### 2. Configurar las Variables de Entorno

Copia el archivo de ejemplo `.env.example` para crear tu archivo `.env`:

#### En Windows (PowerShell):
```powershell
Copy-Item .env.example .env
```

#### En Linux / macOS / Git Bash:
```bash
cp .env.example .env
```

> **Nota**: Dentro del archivo `.env`, puedes ajustar las siguientes variables:
> - `N8N_WEBHOOK_URL`: URL del webhook para procesar o guardar la información registrada.
> - `CORS_ORIGINS`: Dominios y orígenes permitidos.
> - `CLOUDFLARED_TUNNEL_TOKEN`: Token para un túnel estable de Cloudflare (*opcional*).

---

### 3. Construir e Iniciar los Contenedores

Para compilar la imagen Docker e iniciar los servicios en segundo plano, ejecuta:

```bash
docker compose up -d --build
```

> **Primera ejecución**: La primera vez puede tomar unos minutos mientras se descargan las dependencias de PyTorch y los modelos de EasyOCR.

---

### 4. Acceso a la Aplicación

Una vez iniciados los contenedores:

- **Acceso Local**: Abre tu navegador e ingresa a [http://localhost:8000](http://localhost:8000).
- **Acceso Remoto (Cloudflare Quick Tunnel)**: Si no configuraste un token privado, Cloudflare generará un enlace público temporal. Para obtener la URL pública asignada, ejecuta:

  ```bash
  docker compose logs tunnel
  ```

---

## ⚙️ Uso del Túnel Estable (Opcional)

Si configuraste un token en la variable `CLOUDFLARED_TUNNEL_TOKEN` dentro de tu `.env`, puedes levantar el perfil estable ejecutando:

```bash
docker compose --profile stable up -d
```

---

## 🛑 Comandos Útiles de Mantenimiento

- **Ver logs en tiempo real de la app web**:
  ```bash
  docker compose logs -f web
  ```

- **Detener los servicios**:
  ```bash
  docker compose down
  ```

- **Reiniciar los servicios**:
  ```bash
  docker compose restart
  ```
