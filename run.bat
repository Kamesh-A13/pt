@echo off
setlocal enabledelayedexpansion

title StudyOS - AI Student Assistant Launcher
echo ==================================================================
echo   StudyOS Launcher (Windows)
echo   Zero API Keys ^| Local Ollama AI ^| FastAPI Backend ^| React UI
echo ==================================================================

cd /d "%~dp0"

:: ------------------------------------------------------------------
:: 1. Check and Auto-Install Ollama if Missing
:: ------------------------------------------------------------------
echo [1/4] Checking Ollama AI engine...

:: Check standard Ollama installation paths
if exist "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" (
    set "PATH=%LOCALAPPDATA%\Programs\Ollama;%PATH%"
)

where ollama >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ==================================================================
    echo [!] Ollama was NOT found on your computer.
    echo [*] Downloading and installing Ollama for Windows automatically...
    echo ==================================================================
    echo.

    set "OLLAMA_INSTALLER=%TEMP%\OllamaSetup.exe"

    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
        "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; " ^
        "Write-Host '--> Downloading official Ollama installer (approx. 70MB)...' -ForegroundColor Cyan; " ^
        "try { Invoke-WebRequest -Uri 'https://ollama.com/download/OllamaSetup.exe' -OutFile '%OLLAMA_INSTALLER%' -UseBasicParsing } " ^
        "catch { Write-Host 'Download failed via Invoke-WebRequest, trying curl...' -ForegroundColor Yellow; curl.exe -L 'https://ollama.com/download/OllamaSetup.exe' -o '%OLLAMA_INSTALLER%' }; " ^
        "Write-Host '--> Running Ollama installer...' -ForegroundColor Cyan; " ^
        "Start-Process -FilePath '%OLLAMA_INSTALLER%' -ArgumentList '/SILENT /NORESTART' -Wait; " ^
        "Write-Host '--> Ollama installation finished!' -ForegroundColor Green"

    :: Refresh PATH for current command session
    if exist "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" (
        set "PATH=%LOCALAPPDATA%\Programs\Ollama;%PATH%"
        echo [v] Ollama detected at %LOCALAPPDATA%\Programs\Ollama\ollama.exe
    ) else (
        echo [!] Silent install did not locate ollama.exe. Launching interactive setup...
        start /wait "" "%OLLAMA_INSTALLER%"
        if exist "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" (
            set "PATH=%LOCALAPPDATA%\Programs\Ollama;%PATH%"
        )
    )
) else (
    echo [v] Ollama executable detected in PATH.
)

:: ------------------------------------------------------------------
:: 2. Ensure Ollama Server is Running & Pull llama3.2
:: ------------------------------------------------------------------
echo.
echo [*] Verifying Ollama server is running...
curl -s http://localhost:11434/api/tags >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [*] Starting Ollama server in background...
    if exist "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" (
        start "Ollama Engine" /B "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" serve
    ) else (
        start "Ollama Engine" /B ollama serve
    )
    
    :: Wait up to 10 seconds for Ollama server to wake up
    set /a RETRIES=0
    :WAIT_OLLAMA
    timeout /t 2 /nobreak >nul
    curl -s http://localhost:11434/api/tags >nul 2>&1
    if %ERRORLEVEL% NEQ 0 (
        set /a RETRIES+=1
        if !RETRIES! LEQ 5 (
            echo     Waiting for Ollama service to start... [!RETRIES!/5]
            goto WAIT_OLLAMA
        )
    )
)

echo [v] Ollama server is online on http://localhost:11434

:: Check for llama3.2 model
echo [*] Checking for 'llama3.2' AI model...
ollama list 2>nul | findstr /i "llama3.2" >nul
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ==================================================================
    echo [*] Pulling 'llama3.2' model (approx. 2.0 GB - first time only)...
    echo ==================================================================
    ollama pull llama3.2
    echo [v] Model 'llama3.2' downloaded successfully!
) else (
    echo [v] Model 'llama3.2' is ready.
)

:: ------------------------------------------------------------------
:: 3. Start Backend (FastAPI on Port 8000)
:: ------------------------------------------------------------------
echo.
echo [2/4] Initializing Python FastAPI Backend...
cd /d "%~dp0backend"

:: Verify Python is installed
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [!] Python is not installed or not in PATH!
    echo     Please install Python 3.10+ from https://www.python.org/downloads/
    pause
    exit /b 1
)

if not exist "venv\Scripts\activate.bat" (
    echo [*] Creating Python virtual environment (one-time setup)...
    python -m venv venv
    call venv\Scripts\activate.bat
    python -m pip install --upgrade pip --quiet
    echo [*] Installing backend dependencies from requirements.txt...
    pip install -r requirements.txt --quiet
)

echo [*] Launching FastAPI Backend on http://localhost:8000...
start "StudyOS Backend" cmd /c "%~dp0backend\run_backend.bat"

:: ------------------------------------------------------------------
:: 4. Start Frontend (Vite on Port 5173)
:: ------------------------------------------------------------------
echo.
echo [3/4] Initializing React/TypeScript Frontend...
cd /d "%~dp0frontend"

:: Verify Node / npm is installed
where npm >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [!] Node.js / npm is not installed or not in PATH!
    echo     Please install Node.js from https://nodejs.org/
    pause
    exit /b 1
)

if not exist "node_modules\" (
    echo [*] Installing node dependencies (one-time setup)...
    npm install
)

echo [*] Launching Vite Frontend on http://localhost:5173...
start "StudyOS Frontend" cmd /c "%~dp0frontend\run_frontend.bat"

:: ------------------------------------------------------------------
:: 5. Open Default Browser
:: ------------------------------------------------------------------
echo.
echo [4/4] Launching StudyOS in your web browser...
timeout /t 4 /nobreak >nul

start http://localhost:5173

echo.
echo ==================================================================
echo   🎉 StudyOS is up and running!
echo   --------------------------------------------------------------
echo   - Web App UI:  http://localhost:5173
echo   - Backend API: http://localhost:8000/docs
echo   - Ollama AI:   http://localhost:11434 (llama3.2)
echo.
echo   NOTE: Keep the two backend and frontend terminal windows open.
echo   Close them when you want to terminate StudyOS.
echo ==================================================================
echo.
pause
