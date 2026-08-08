@echo off
title 9REALMS GUNGNIR LightGBM Kaizen Daemon
cd /d "%~dp0"

echo.
echo  ╔══════════════════════════════════════════════════════════════╗
echo  ║  9REALMS GUNGNIR LightGBM AUTO-ML DAEMON                    ║
echo  ║  Phase Readout Prediction Engine                             ║
echo  ║  改善 KAIZEN MODE ENABLED                                   ║
echo  ║                                                              ║
echo  ║  Dashboard: kaizen_gungnir\kaizen_dashboard.json             ║
echo  ║  Stop: Create STOP_GUNGNIR file or Ctrl+C                   ║
echo  ║  Logs: alerts\gungnir_lgb_daemon_log.txt                     ║
echo  ╚══════════════════════════════════════════════════════════════╝
echo.

py -3.11 mcp_core\gungnir_historical_evolve.py

echo.
echo Gungnir daemon stopped. Press any key to close.
pause >nul
