@echo off
color 0E
title SmartQueue AI - Setup Checker
echo ========================================
echo   SmartQueue AI - Setup Checker
echo ========================================
echo.

echo [1/5] Checking Python installation...
python --version 2>nul
if %errorlevel% neq 0 (
    echo ❌ Python is NOT installed!
    echo    Please install Python from https://www.python.org/
    goto :end
) else (
    echo ✅ Python is installed
)
echo.

echo [2/5] Checking required packages...
pip show fastapi >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ FastAPI is NOT installed
    echo    Installing required packages...
    pip install -r requirements.txt
) else (
    echo ✅ FastAPI is installed
)
echo.

echo [3/5] Checking if backend files exist...
if exist "app\main.py" (
    echo ✅ Backend files found
) else (
    echo ❌ Backend files NOT found
    echo    Make sure you're in the correct directory
    goto :end
)
echo.

echo [4/5] Checking if frontend files exist...
if exist "al smart queue frontend\healthcare.html" (
    echo ✅ Frontend files found
) else (
    echo ❌ Frontend files NOT found
    echo    Make sure you're in the correct directory
    goto :end
)
echo.

echo [5/5] Checking if ports are available...
netstat -ano | findstr :8000 >nul
if %errorlevel% equ 0 (
    echo ⚠️  Port 8000 is already in use
    echo    You may need to close other applications
) else (
    echo ✅ Port 8000 is available
)

netstat -ano | findstr :3000 >nul
if %errorlevel% equ 0 (
    echo ⚠️  Port 3000 is already in use
    echo    You may need to close other applications
) else (
    echo ✅ Port 3000 is available
)
echo.

echo ========================================
echo   Setup Check Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Double-click: 1-start-backend.bat
echo 2. Double-click: 2-start-frontend.bat
echo 3. Double-click: 3-open-browser.bat
echo.

:end
pause
