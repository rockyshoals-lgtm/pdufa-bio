@echo off
title SweepRunner Setup
echo.
echo ==========================================
echo   SWEEPRUNNER - First Time Setup
echo ==========================================
echo.
python --version >nul 2>&1
if errorlevel 1 (echo ERROR: Python not found. Install from https://python.org & pause & exit /b 1)
echo [1/4] Installing Python dependencies...
pip install flask playwright apscheduler requests beautifulsoup4 lxml win10toast --quiet
echo [2/4] Installing Playwright Chrome...
playwright install chromium
echo [3/4] Done!
echo.
echo Run START.bat to launch SweepRunner
pause
