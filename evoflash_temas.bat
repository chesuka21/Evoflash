@echo off
chcp 65001 >nul
rem Gestor de areas de estudio
cd /d "%~dp0"
"venv\Scripts\python.exe" ui_cli\temas.py
pause
