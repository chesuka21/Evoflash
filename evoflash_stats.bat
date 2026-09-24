@echo off
chcp 65001 >nul
rem Stats — progreso por tema
cd /d "%~dp0"
"venv\Scripts\python.exe" ui_cli\stats.py
pause
