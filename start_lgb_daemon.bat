@echo off
title 9REALMS LightGBM Kaizen Daemon
cd /d "%~dp0"

echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║  9REALMS LightGBM AUTO-ML DAEMON                ║
echo  ║  改善 KAIZEN MODE ENABLED                       ║
echo  ║                                                  ║
echo  ║  Dashboard: Open kaizen\dashboard.html           ║
echo  ║  Stop: Run stop_lgb_daemon.bat or Ctrl+C         ║
echo  ║  Logs: alerts\lgb_daemon_log.txt                 ║
echo  ╚══════════════════════════════════════════════════╝
echo.

py -3.11 mcp_core\lgb_perpetual_daemon.py

echo.
echo Daemon stopped. Press any key to close.
pause >nul
