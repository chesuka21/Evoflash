@echo off
chcp 65001 >nul
rem Gestor de Exámenes — cuándo y qué temas
cd /d "%~dp0"
"venv\Scripts\python.exe" ui_cli\examenes.py
pause
