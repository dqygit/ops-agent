@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0.."

set PYTHONPATH=%PYTHONPATH%;%~dp0..\src

if not exist logs (
    mkdir logs
)

if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
)

if exist .env (
    echo Loading environment from .env...
    for /f "usebackq tokens=*" %%a in (".env") do (
        set "line=%%a"
        if not "!line:~0,1!"=="#" (
            if not "!line!"=="" (
                set "!line!"
            )
        )
    )
)

echo Stopping processes on ports 8000 and 5173...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING"') do (
    taskkill /T /F /PID %%a 2>nul
)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5173" ^| findstr "LISTENING"') do (
    taskkill /T /F /PID %%a 2>nul
)

echo Starting Ops Agent Backend...
start /b python src\app\main.py >logs\backend.log 2>&1

echo Starting Ops Agent Frontend...
cd web
npm run dev

echo.
echo Frontend server started. Backend running in background.
echo Check logs\backend.log for backend logs.
echo Press Ctrl+C to stop servers
echo.
