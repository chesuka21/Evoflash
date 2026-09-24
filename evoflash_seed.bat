@echo off
chcp 65001 >nul
rem Sembrar flashcards desde tus apuntes de Obsidian
cd /d "%~dp0"
"venv\Scripts\python.exe" ingestion\ingest_from_obsidian.py
pause
