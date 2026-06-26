@echo off
setlocal EnableExtensions
title Business Research Agent - Full Stack

cd /d "%~dp0"

echo ============================================
echo   Starting Proxy + Backend + Frontend
echo ============================================
echo.

where docker >nul 2>&1
if errorlevel 1 (
    echo WARNING: Docker not found. Skipping proxy pool.
    echo Set USE_PROXY_POOL=false in .env or install Docker.
    echo.
    goto :start_app
)

docker ps --filter "name=business-research-proxy" --format "{{.Names}}" | findstr /i "business-research-proxy" >nul
if errorlevel 1 (
    echo Starting proxy-in-a-box...
    docker run -d --name business-research-proxy ^
      -p 8080:8080 -p 8081:8081 -p 8083:8083 ^
      -v "%~dp0proxy-pool\data:/app/data" ^
      --restart unless-stopped ^
      ghcr.io/naiba/proxy-in-a-box:latest
    if errorlevel 1 (
        echo WARNING: Could not start proxy container. Continuing without it.
    ) else (
        echo Proxy dashboard: http://127.0.0.1:8083
    )
) else (
    echo Proxy pool already running.
)
echo.

:start_app
call "%~dp0start-dev.bat"

endlocal
