@echo off
setlocal EnableExtensions
title Atlas Research - Stop

echo Stopping Atlas Research...

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do (
    echo Stopping backend PID %%a
    taskkill /F /PID %%a >nul 2>&1
)

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":3000" ^| findstr "LISTENING"') do (
    echo Stopping frontend PID %%a
    taskkill /F /PID %%a >nul 2>&1
)

echo Done.
timeout /t 2 /nobreak >nul

endlocal
