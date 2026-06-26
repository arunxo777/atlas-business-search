@echo off
setlocal EnableExtensions
title Atlas Research - Hackathon Demo

cd /d "%~dp0"

echo ============================================
echo   Atlas Research - HACKATHON DEMO MODE
echo   Backend on laptop + ngrok + Vercel UI
echo ============================================
echo.
echo   Vercel UI:  https://frontend-three-pi-73.vercel.app
echo   Backend:    your laptop :8000
echo   Tunnel:     ngrok (public URL for Vercel)
echo.
echo ============================================
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found.
    pause
    exit /b 1
)

if not exist "backend\main.py" (
    echo ERROR: Run from business-research-agent folder.
    pause
    exit /b 1
)

if not exist ".env" (
    echo WARNING: No .env file. Copy .env.example to .env and add API keys.
    echo.
)

echo [1/3] Clearing port 8000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)
timeout /t 2 /nobreak >nul

echo [2/3] Starting backend on http://127.0.0.1:8000 ...
start "Atlas Backend" cmd /k "cd /d "%~dp0backend" && python -m uvicorn main:app --host 127.0.0.1 --port 8000"

timeout /t 4 /nobreak >nul

where ngrok >nul 2>&1
if errorlevel 1 (
    echo.
    echo [3/3] ngrok NOT installed - backend only mode.
    echo.
    echo Install ngrok for Vercel demo:
    echo   winget install ngrok.ngrok
    echo   ngrok config add-authtoken YOUR_TOKEN
    echo   Then run: start-ngrok.bat
    echo.
    echo Or use local UI: http://localhost:3000 with start-dev.bat
    echo.
    pause
    exit /b 0
)

echo [3/3] Starting ngrok tunnel...
start "Atlas ngrok" cmd /k "cd /d "%~dp0" && ngrok http 8000"

timeout /t 3 /nobreak >nul

echo.
echo ============================================
echo   DEMO CHECKLIST
echo ============================================
echo.
echo  1. In the ngrok window, copy the https URL
echo     Example: https://abc123.ngrok-free.app
echo.
echo  2. Vercel Dashboard:
echo     frontend project - Settings - Environment Variables
echo     VITE_API_URL = your ngrok https URL
echo     Redeploy frontend (Deployments - Redeploy)
echo.
echo  3. In your .env file, set CORS:
echo     CORS_ORIGINS=https://frontend-three-pi-73.vercel.app
echo     Restart backend window if you change .env
echo.
echo  4. Open for judges:
echo     https://frontend-three-pi-73.vercel.app
echo.
echo  KEEP THIS LAPTOP ON during the demo!
echo ============================================
echo.

start "" "https://frontend-three-pi-73.vercel.app"

endlocal
