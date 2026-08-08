@echo off
REM ═══════════════════════════════════════════════════════════
REM  9REALMS — Gracefully stop the LightGBM Daemon
REM  Creates a STOP file that the daemon checks between rounds.
REM ═══════════════════════════════════════════════════════════

cd /d "%~dp0"
echo. > STOP
echo STOP signal sent. The daemon will halt after the current round finishes.
echo (This may take 1-3 minutes depending on Optuna trial progress.)
pause
