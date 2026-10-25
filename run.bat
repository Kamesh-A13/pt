@echo off
setlocal enabledelayedexpansion

title StudyOS - AI Student Assistant Launcher
echo ==================================================================
echo   StudyOS Launcher (Windows)
echo   Local Ollama AI + FastAPI Backend + React/TypeScript Frontend
echo ==================================================================

cd /d "%~dp0"

:: ------------------------------------------------------------------
:: 1. Check Ollama
:: ------------------------------------------------------------------
echo [1/4] Checking Ollama status...
curl -s http://localhost:11434/api/tags >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [!] Ollama is not running. Starting Ollama...
    start "Ollama Engine" /B ollama serve
    timeout /t 3 /nobreak >nul
) else (
    echo [v] Ollama is running on http://localhost:11434
)

echo Checking for model 'llama3.2'...
ollama list 2>nul | findstr /i "llama3.2" >nul
if %ERRORLEVEL% NEQ 0 (
    echo [*] Pulling 'llama3.2' model (first-time only)...
    ollama pull llama3.2
) else (
    echo [v] Model 'llama3.2' is ready.
)

:: ------------------------------------------------------------------
:: 2. Start Backend
:: ------------------------------------------------------------------
echo.
echo [2/4] Starting Backend (FastAPI on Port 8000)...
cd /d "%~dp0backend"

if not exist "venv\Scripts\activate.bat" (
    echo Creating Python virtual environment...
    python -m venv venv
    call venv\Scripts\activate.bat
    python -m pip install --upgrade pip
    pip install -r requirements.txt
)

start "StudyOS Backend" cmd /k "title StudyOS Backend && cd /d "%~dp0backend" && call venv\Scripts\activate.bat && uvicorn app.main:app --host 0.0.0.0 --port 8000"

:: ------------------------------------------------------------------
:: 3. Start Frontend
:: ------------------------------------------------------------------
echo.
echo [3/4] Starting Frontend (Vite on Port 5173)...
cd /d "%~dp0frontend"

if not exist "node_modules\" (
    echo Installing node dependencies...
    npm install
)

start "StudyOS Frontend" cmd /k "title StudyOS Frontend && cd /d "%~dp0frontend" && npm run dev"

:: ------------------------------------------------------------------
:: 4. Open in Browser
:: ------------------------------------------------------------------
echo.
echo [4/4] Launching StudyOS in your default browser...
timeout /t 4 /nobreak >nul

start http://localhost:5173

echo.
echo ==================================================================
echo   StudyOS is running!
echo   - Web Application: http://localhost:5173
echo   - Backend API:     http://localhost:8000/docs
echo   - Ollama AI:       http://localhost:11434 (llama3.2)
echo.
echo   Keep the two open command windows running while using StudyOS.
echo   Close those windows when you want to exit.
echo ==================================================================
pause
