@echo off
title 9REALMS DUAL SPEAR KAIZEN - ODIN x GUNGNIR
cd /d "%~dp0"

echo.
echo  ╔══════════════════════════════════════════════════════════════╗
echo  ║  9REALMS DUAL SPEAR KAIZEN                                  ║
echo  ║  🔱 ODIN (PDUFA) × 🔱 GUNGNIR (Phase Readouts)             ║
echo  ║  改善 KAIZEN MODE ENABLED                                   ║
echo  ║                                                              ║
echo  ║  Dashboard: kaizen_dual\dual_dashboard.json                  ║
echo  ║  ODIN Kaizen: kaizen\kaizen_dashboard.json                   ║
echo  ║  GUNGNIR Kaizen: kaizen_gungnir\kaizen_dashboard.json        ║
echo  ║  Stop: Create STOP_DUAL file or Ctrl+C                      ║
echo  ║  Logs: alerts\dual_spear_log.txt                             ║
echo  ╚══════════════════════════════════════════════════════════════╝
echo.

py -3.11 mcp_core\dual_spear_kaizen.py

echo.
echo Dual Spear daemon stopped. Press any key to close.
pause >nul
