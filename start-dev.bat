@echo off
setlocal EnableExtensions
title Business Research Agent - Launcher

cd /d "%~dp0"

echo ============================================
echo   AI Business Research Agent
echo   Starting Backend + Frontend...
echo ============================================
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.10+ and try again.
    pause
    exit /b 1
)

where npm >nul 2>&1
if errorlevel 1 (
    echo ERROR: npm not found. Install Node.js 20+ and try again.
    pause
    exit /b 1
)

if not exist "backend\main.py" (
    echo ERROR: Run this file from the business-research-agent folder.
    pause
    exit /b 1
)

if not exist "frontend\node_modules" (
    echo Installing frontend dependencies...
    pushd frontend
    call npm install
    if errorlevel 1 (
        echo ERROR: npm install failed.
        pause
        exit /b 1
    )
    popd
    echo.
)

echo Checking ports 8000 and 3000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do (
    echo Port 8000 in use — stopping old backend PID %%a
    taskkill /F /PID %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":3000" ^| findstr "LISTENING"') do (
    echo Port 3000 in use — stopping old frontend PID %%a
    taskkill /F /PID %%a >nul 2>&1
)
timeout /t 2 /nobreak >nul
echo.

echo Starting backend on http://127.0.0.1:8000
start "BRA Backend" cmd /k "cd /d "%~dp0backend" && python -m uvicorn main:app --host 127.0.0.1 --port 8000"

timeout /t 3 /nobreak >nul

echo Starting frontend on http://localhost:3000
start "BRA Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"

timeout /t 4 /nobreak >nul

echo.
echo ============================================
echo   Backend:  http://127.0.0.1:8000
echo   API docs: http://127.0.0.1:8000/docs
echo   Frontend: http://localhost:3000
echo ============================================
echo.
echo Two terminal windows opened. Close them to stop the app.
echo.

start "" "http://localhost:3000"

endlocal
