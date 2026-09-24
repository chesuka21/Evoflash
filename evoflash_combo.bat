@echo off
chcp 65001 >nul
rem EvoFlash — Deck Combo (Nivel 5 — fusión de N4)
cd /d "%~dp0"
"venv\Scripts\python.exe" ingestion\combos.py
pause
