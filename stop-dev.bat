@echo off
setlocal EnableExtensions
title Business Research Agent - Stop

echo Stopping services on ports 8000 and 3000...

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do (
    echo Killing backend PID %%a
    taskkill /F /PID %%a >nul 2>&1
)

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":3000" ^| findstr "LISTENING"') do (
    echo Killing frontend PID %%a
    taskkill /F /PID %%a >nul 2>&1
)

echo Done. Close any "BRA Backend" / "BRA Frontend" windows if still open.
timeout /t 2 /nobreak >nul

endlocal
