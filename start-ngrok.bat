@echo off
setlocal EnableExtensions
title Atlas Research - ngrok Tunnel

cd /d "%~dp0"

echo ============================================
echo   Atlas Research - Public Backend Tunnel
echo   Exposes localhost:8000 to the internet
echo ============================================
echo.

where ngrok >nul 2>&1
if errorlevel 1 (
    echo ngrok is NOT installed.
    echo.
    echo Install one of these ways:
    echo   winget install ngrok.ngrok
    echo   OR download from https://ngrok.com/download
    echo.
    echo After install, sign up free at https://ngrok.com and run:
    echo   ngrok config add-authtoken YOUR_TOKEN
    echo.
    pause
    exit /b 1
)

netstat -ano | findstr ":8000" | findstr "LISTENING" >nul 2>&1
if errorlevel 1 (
    echo WARNING: Nothing is listening on port 8000.
    echo Start the backend first with start-demo.bat or start-dev.bat
    echo.
    pause
)

echo Starting ngrok tunnel to http://127.0.0.1:8000 ...
echo.
echo Copy the https://....ngrok-free.app URL and set it in Vercel:
echo   Project Settings - Environment Variables - VITE_API_URL
echo.
echo Also add your Vercel URL to backend .env CORS_ORIGINS:
echo   CORS_ORIGINS=https://frontend-three-pi-73.vercel.app,http://localhost:3000
echo.
echo Press Ctrl+C to stop the tunnel.
echo ============================================
echo.

ngrok http 8000

endlocal
