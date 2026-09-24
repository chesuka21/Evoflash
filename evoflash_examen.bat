@echo off
chcp 65001 >nul
rem EvoFlash — Modo Examen N1→N4
cd /d "%~dp0"
"venv\Scripts\python.exe" ui_cli\examen.py
pause
