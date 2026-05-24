@echo off
title SmartQueue Backend Server
color 0A
echo ========================================
echo   SmartQueue AI - Backend Server
echo ========================================
echo.
echo Starting backend on http://localhost:8000
echo API Documentation: http://localhost:8000/docs
echo.
echo Press CTRL+C to stop the server
echo ========================================
echo.

python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

pause
