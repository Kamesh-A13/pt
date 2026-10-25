@echo off
title StudyOS Backend API
cd /d "%~dp0"

echo ==================================================================
echo   Starting StudyOS FastAPI Backend (Port 8000)
echo ==================================================================

if not exist "venv\Scripts\activate.bat" (
    echo Creating Python virtual environment...
    python -m venv venv
    call venv\Scripts\activate.bat
    python -m pip install --upgrade pip
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate.bat
)

uvicorn app.main:app --host 0.0.0.0 --port 8000
pause
