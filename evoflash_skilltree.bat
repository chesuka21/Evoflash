@echo off
chcp 65001 >nul
rem Skill Tree — servidor primero, luego navegador
cd /d "%~dp0"

REM Matar cualquier servidor viejo en 8766
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8766') do taskkill //F //PID %%a >nul 2>&1

REM 1. Exportar datos frescos
"venv\Scripts\python.exe" web_dashboard\export_data.py

REM 2. Servidor en background (ventana minimizada propia)
start "EvoFlash Server" /min "venv\Scripts\python.exe" web_dashboard\servidor.py

REM 3. Esperar a que responda (hasta 15 intentos)
set /a tries=0
:waitloop
set /a tries+=1
if %tries% GTR 15 goto fail
powershell -NoProfile -Command "try { (Invoke-WebRequest -UseBasicParsing -Uri http://127.0.0.1:8766/api/pending -TimeoutSec 2).StatusCode } catch { exit 1 }" >nul 2>&1
if errorlevel 1 (
    timeout /t 1 /nobreak >nul
    goto waitloop
)

REM 4. Servidor listo → abrir navegador
echo Servidor OK en http://127.0.0.1:8766
start "" "http://127.0.0.1:8766/index.html"
echo Presiona una tecla para cerrar el servidor...
pause >nul
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8766') do taskkill //F //PID %%a >nul 2>&1
exit

:fail
echo ERROR: el servidor no respondio en 15 segundos. Revisa C:\Users\cesar\Desktop\EVOFLASH\evoflash\web_dashboard\servidor.py
pause

