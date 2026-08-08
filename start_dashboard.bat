@echo off
title 9REALMS Kaizen Dashboard
echo.
echo  =========================================
echo   9REALMS - KAIZEN LIVE DASHBOARD
echo   Opening: http://localhost:9876
echo  =========================================
echo.

:: Install flask if needed
py -3.11 -m pip install flask -q 2>nul

:: Open browser after 2 second delay
start "" /b cmd /c "timeout /t 2 /nobreak >nul & start http://localhost:9876"

:: Start dashboard
py -3.11 "%~dp0kaizen_dashboard.py"

pause
