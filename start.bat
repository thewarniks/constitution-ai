@echo off
rem Double-click to start Constitution Ai, then open http://localhost:8000
cd /d "%~dp0"
start "" http://localhost:8000
.venv\Scripts\python.exe server.py
pause
