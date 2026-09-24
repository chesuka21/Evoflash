@echo off
chcp 65001 >nul
cd /d "%~dp0"

for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8766 ^| findstr LISTENING') do taskkill /F /PID %%a >nul 2>&1

venv\Scripts\python.exe web_dashboard\export_data.py
if errorlevel 1 (
    echo ERROR: export_data falló
    pause
    exit /b 1
)

start "EvoFlash Server" /min venv\Scripts\python.exe web_dashboard\servidor.py
timeout /t 4 /nobreak >nul

curl -s http://127.0.0.1:8766/api/stats >nul 2>&1
if errorlevel 1 (
    echo ERROR: servidor no respondio
    pause
    exit /b 1
)

start "" http://127.0.0.1:8766/menu.html
echo Servidor OK en http://127.0.0.1:8766
echo Presiona tecla para cerrar...
pause >nul
