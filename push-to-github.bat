@echo off
setlocal EnableExtensions
title Atlas Research - Push to GitHub

echo.
echo  Atlas Research - GitHub Setup
echo  =============================
echo.

where gh >nul 2>&1
if errorlevel 1 (
    echo ERROR: GitHub CLI ^(gh^) is not installed.
    echo Install from: https://cli.github.com/
    pause
    exit /b 1
)

gh auth status >nul 2>&1
if errorlevel 1 (
    echo You are not logged into GitHub. Running: gh auth login
    echo.
    gh auth login
)

echo.
echo Creating repo and pushing to github.com/YOUR_USERNAME/atlas-business-search ...
echo.

gh repo create atlas-business-search --public --source=. --remote=origin --description "AI-powered business intelligence with source-attributed, hallucination-resistant data" --push

if errorlevel 1 (
    echo.
    echo If the repo already exists, run:
    echo   git remote add origin https://github.com/YOUR_USERNAME/atlas-business-search.git
    echo   git push -u origin main
)

echo.
echo Done!
pause
endlocal
