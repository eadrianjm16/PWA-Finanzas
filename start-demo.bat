@echo off
setlocal
cd /d "%~dp0"

echo ============================================
echo   Finanzas - arranque local (modo demo)
echo ============================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo ERROR: no se encuentra "python" en el PATH. Instala Python 3.11+ desde python.org y vuelve a intentarlo.
    pause
    exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
    echo ERROR: no se encuentra "npm" en el PATH. Instala Node.js 20+ desde nodejs.org y vuelve a intentarlo.
    pause
    exit /b 1
)

echo [1/5] Preparando entorno del backend...
cd backend
if not exist .venv (
    python -m venv .venv
)
call .venv\Scripts\activate.bat
pip install -q -r requirements.txt

if not exist .env (
    echo [2/5] Generando configuracion de demo ^(backend\.env^)...
    python seed_demo.py --write-env
) else (
    echo [2/5] backend\.env ya existe, no se toca.
)

echo [3/5] Sembrando datos de ejemplo ^(si la base esta vacia^)...
python seed_demo.py

echo [4/5] Arrancando backend en http://localhost:8000 ...
start "Finanzas - backend" cmd /k "cd /d %~dp0backend && call .venv\Scripts\activate.bat && uvicorn app.main:app --reload --port 8000"

cd /d "%~dp0frontend"
if not exist node_modules (
    echo Instalando dependencias del frontend ^(puede tardar un par de minutos^)...
    call npm install
)
if not exist .env.local (
    echo NEXT_PUBLIC_API_BASE_URL=http://localhost:8000> .env.local
)

echo [5/5] Arrancando frontend en http://localhost:3000 ...
start "Finanzas - frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

cd /d "%~dp0"
echo.
echo Esperando a que arranquen los dos servidores...
timeout /t 8 /nobreak >nul

start "" "http://localhost:3000"

echo.
echo ============================================
echo   Backend:  http://localhost:8000/docs
echo   Frontend: http://localhost:3000
echo   Contrasena de demo: demo1234
echo ============================================
echo.
echo Los datos y las credenciales de Enable Banking son de PRUEBA:
echo conectar un banco real no funcionara hasta que pongas tus
echo credenciales reales en backend\.env y borres backend\finanzas.db
echo para volver a sembrar en limpio si hace falta.
echo.
pause
