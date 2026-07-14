# Pronto Pizza Backend

Backend desarrollado con **Python**, **FastAPI** y **PostgreSQL** (utilizando `asyncpg` y `SQLAlchemy`). Además, el proyecto está preparado para integrarse con servicios de **Supabase**.

## Requisitos Previos

- **Python** (versión 3.10 o superior)
- Gestor de paquetes `pip`

## Guía de Instalación y Ejecución Local

1. **Entrar al directorio del proyecto**:
   ```bash
   cd Pronto_Pizza_Backend
   ```

2. **Crear y activar un entorno virtual**:
   - En **Windows** (PowerShell):
     ```powershell
     python -m venv venv
     .\venv\Scripts\Activate.ps1
     ```
   - En **Linux / macOS**:
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

3. **Instalar dependencias**:
   Asegúrate de tener el entorno virtual activado y ejecuta:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configurar Variables de Entorno**:
   El proyecto requiere un archivo `.env` en la raíz del backend para funcionar correctamente. Puedes crearlo copiando el archivo de ejemplo:
   - En **Windows**:
     ```powershell
     Copy-Item .env.example .env
     ```
   - En **Linux / macOS**:
     ```bash
     cp .env.example .env
     ```
   *Nota: Asegúrate de revisar y configurar correctamente los valores dentro del archivo `.env`, particularmente `DATABASE_URL` y las credenciales de Supabase.*

5. **Levantar el Servidor**:
   Para iniciar el servidor de FastAPI en modo desarrollo (el cual incluye recarga automática al detectar cambios en el código):
   ```bash
   uvicorn app.main:app --reload
   ```

6. **Verificar el Funcionamiento**:
   Una vez que el servidor esté en ejecución, puedes verificar que todo está en orden ingresando a las siguientes rutas desde tu navegador:
   - **Endpoint de prueba (Health Check)**: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
   - **Documentación Interactiva (Swagger UI)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
