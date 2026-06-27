@echo off

setlocal EnableExtensions

title Atlas Research - Start



cd /d "%~dp0"

if not exist "logs" mkdir logs



echo.

echo  ============================================

echo    Atlas Research (local)

echo    UI: http://localhost:3000

echo    API: http://localhost:8000

echo  ============================================

echo.



where python >nul 2>&1

if errorlevel 1 (

    echo ERROR: Python not found. Install Python 3.10+

    exit /b 1

)



where npm >nul 2>&1

if errorlevel 1 (

    echo ERROR: npm not found. Install Node.js 20+

    exit /b 1

)



if not exist "backend\main.py" (

    echo ERROR: Run this from the business-research-agent folder.

    exit /b 1

)



if not exist ".env" (

    echo WARNING: No .env file. Copy .env.example to .env and add API keys.

    echo.

)



if not exist "frontend\node_modules" (

    echo Installing frontend dependencies...

    pushd frontend

    call npm install

    if errorlevel 1 (

        echo ERROR: npm install failed.

        exit /b 1

    )

    popd

    echo.

)



echo Clearing ports 8000 and 3000...

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do taskkill /F /PID %%a >nul 2>&1

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":3000" ^| findstr "LISTENING"') do taskkill /F /PID %%a >nul 2>&1

timeout /t 2 /nobreak >nul



echo [1/2] Backend starting in background...

start /B cmd /c "cd /d "%~dp0backend" && python -m uvicorn main:app --host 127.0.0.1 --port 8000 >> "%~dp0logs\backend.log" 2>&1"

timeout /t 4 /nobreak >nul



echo.

echo  ============================================

echo    Services running

echo  ============================================

echo    Open:  http://localhost:3000

echo    API:   http://localhost:8000

echo    Logs:  logs\backend.log

echo    Stop:  stop.bat  or  Ctrl+C then stop.bat

echo  ============================================

echo.

echo [2/2] Frontend starting below...

echo.



cd /d "%~dp0frontend"

npm run dev



endlocal

