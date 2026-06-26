@echo off
setlocal EnableExtensions
title Atlas Research - Start

cd /d "%~dp0"

echo.
echo  ============================================
echo    Atlas Research
echo    Backend + ngrok + Local UI
echo  ============================================
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.10+
    pause
    exit /b 1
)

where npm >nul 2>&1
if errorlevel 1 (
    echo ERROR: npm not found. Install Node.js 20+
    pause
    exit /b 1
)

if not exist "backend\main.py" (
    echo ERROR: Run this from the business-research-agent folder.
    pause
    exit /b 1
)

if not exist ".env" (
    echo WARNING: No .env file. Copy .env.example to .env and add API keys.
    echo.
)

rem --- Find ngrok ---
set "NGROK="
where ngrok >nul 2>&1
if not errorlevel 1 set "NGROK=ngrok"
if not defined NGROK if exist "%LOCALAPPDATA%\Microsoft\WinGet\Packages\Ngrok.Ngrok_Microsoft.Winget.Source_8wekyb3d8bbwe\ngrok.exe" (
    set "NGROK=%LOCALAPPDATA%\Microsoft\WinGet\Packages\Ngrok.Ngrok_Microsoft.Winget.Source_8wekyb3d8bbwe\ngrok.exe"
)

rem --- Frontend deps ---
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

rem --- Clear ports ---
echo Clearing ports 8000 and 3000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":3000" ^| findstr "LISTENING"') do taskkill /F /PID %%a >nul 2>&1
taskkill /F /IM ngrok.exe >nul 2>&1
timeout /t 2 /nobreak >nul

rem --- Start backend ---
echo [1/3] Backend  http://127.0.0.1:8000
start "Atlas Backend" cmd /k "cd /d "%~dp0backend" && python -m uvicorn main:app --host 127.0.0.1 --port 8000"
timeout /t 4 /nobreak >nul

rem --- Start ngrok ---
if defined NGROK (
    echo [2/3] ngrok tunnel to port 8000
    start "Atlas ngrok" cmd /k "cd /d "%~dp0" && "%NGROK%" http 8000"
    timeout /t 3 /nobreak >nul
) else (
    echo [2/3] ngrok skipped - not installed
    echo       Install: winget install ngrok.ngrok
    echo.
)

rem --- Start local frontend ---
echo [3/3] Frontend http://localhost:3000
start "Atlas Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"
timeout /t 3 /nobreak >nul

echo.
echo  ============================================
echo    Running
echo  ============================================
echo    Local UI:   http://localhost:3000
echo    Backend:    http://127.0.0.1:8000
echo    API docs:   http://127.0.0.1:8000/docs
echo    Vercel UI:  https://frontend-three-pi-73.vercel.app
echo.
if defined NGROK (
    echo    ngrok:      copy https URL from "Atlas ngrok" window
    echo                set VITE_API_URL in Vercel, then redeploy
)
echo.
echo    Stop everything: stop.bat
echo  ============================================
echo.

start "" "http://localhost:3000"

endlocal
