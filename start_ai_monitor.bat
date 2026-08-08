@echo off
title 9REALMS AI Monitor
echo.
echo  =========================================
echo   9REALMS - AI TRAINING MONITOR
echo   Dashboard must be running first!
echo  =========================================
echo.

:: Install requests if needed
py -3.11 -m pip install requests -q 2>nul

:: Start monitor in watch mode
py -3.11 "%~dp0ai_monitor.py" --watch --interval 30

pause
