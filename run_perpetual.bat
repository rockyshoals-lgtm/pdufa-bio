@echo off
REM ═══════════════════════════════════════════════════════════════
REM  ODIN Perpetual Honing — Runs all night
REM  
REM  Automatically: runs engine -> bumps version -> repeats
REM  Press Ctrl+C to stop between runs
REM  
REM  Progress tracker:
REM    v1095: Val Brier 0.10345  WF AUC 0.9089  WF Brier 0.0878
REM    v1096: Val Brier 0.10309  WF AUC 0.9085  WF Brier 0.0880
REM    v1097: Val Brier 0.10286  WF AUC 0.9081  WF Brier 0.0878
REM    v1101: Val Brier 0.10183  WF AUC 0.9076  WF Brier 0.0885
REM    v1102+: running overnight...
REM ═══════════════════════════════════════════════════════════════

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║  ODIN Perpetual Honing — Leave me running overnight         ║
echo ║  Press Ctrl+C to stop gracefully                            ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

python run_perpetual.py

echo.
echo Perpetual honing stopped.
pause
