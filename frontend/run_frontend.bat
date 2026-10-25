@echo off
title StudyOS Frontend UI
cd /d "%~dp0"

echo ==================================================================
echo   Starting StudyOS React/TypeScript Frontend (Port 5173)
echo ==================================================================

if not exist "node_modules\" (
    echo Installing node dependencies...
    npm install
)

npm run dev
pause
