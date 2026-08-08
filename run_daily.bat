@echo off
REM ╔══════════════════════════════════════════════════════════════════╗
REM ║  9REALMS — Manual Daily Run                                      ║
REM ║  Double-click to run the daily update loop manually              ║
REM ╚══════════════════════════════════════════════════════════════════╝

cd /d "C:\Users\dcmoo\Documents\Python\9realms"
echo [%date% %time%] Starting 9REALMS daily update... >> alerts\scheduler_log.txt
py -3.11 mcp_core\9realms_update_loop.py >> alerts\scheduler_log.txt 2>&1
echo [%date% %time%] 9REALMS daily update complete. >> alerts\scheduler_log.txt
echo.
echo Done. Check alerts\scheduler_log.txt for results.
pause
