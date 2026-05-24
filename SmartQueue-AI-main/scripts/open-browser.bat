@echo off
echo Opening SmartQueue AI in your browser...
timeout /t 2 /nobreak >nul

start http://localhost:3000/test-connection.html
timeout /t 1 /nobreak >nul

start http://localhost:8000/docs

echo.
echo Opened:
echo - Test Connection Page
echo - Backend API Documentation
echo.
echo If the pages don't load, make sure both servers are running:
echo 1. Run 1-start-backend.bat
echo 2. Run 2-start-frontend.bat
echo.
pause
