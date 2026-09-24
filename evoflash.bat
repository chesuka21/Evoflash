@echo off
rem EvoFlash launcher — usa el venv del proyecto
cd /d "%~dp0"
"venv\Scripts\python.exe" ui_cli\play.py %*
pause
