@echo off
echo ========================================
echo SmartQueue AI - Starting Application
echo ========================================
echo.

:: Navigate to project folder first
cd /d "C:\Users\JIYA SADARIA\OneDrive\Desktop\AI  SMART QUEUE"

echo [1/2] Starting Backend Server...
start "SmartQueue Backend" cmd /k "cd /d "C:\Users\JIYA SADARIA\OneDrive\Desktop\AI  SMART QUEUE" && python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
timeout /t 4 /nobreak >nul

echo [2/2] Starting Frontend Server...
start "SmartQueue Frontend" cmd /k "cd /d "C:\Users\JIYA SADARIA\OneDrive\Desktop\AI  SMART QUEUE\al smart queue frontend" && python -m http.server 3000"
timeout /t 2 /nobreak >nul

echo.
echo ========================================
echo SmartQueue AI is now running!
echo ========================================
echo.
echo Backend API:  http://localhost:8000
echo API Docs:     http://localhost:8000/docs
echo Frontend:     http://localhost:3000
echo Test Page:    http://localhost:3000/test-connection.html
echo.
echo Press any key to open the application in your browser...
pause >nul

start http://localhost:3000/test-connection.html
timeout /t 1 /nobreak >nul
start http://localhost:8000/docs

echo.
echo Both servers are running in separate windows.
echo Close those windows to stop the servers.
echo.