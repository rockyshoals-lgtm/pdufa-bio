@echo off
REM ═══════════════════════════════════════════════════════════════
REM  ODIN Perpetual Honing — Run from your Python directory
REM  
REM  Progress tracker:
REM    v1095: Val Brier 0.10345  WF AUC 0.9089  WF Brier 0.0878
REM    v1096: Val Brier 0.10309  WF AUC 0.9085  WF Brier 0.0880
REM    v1097: Val Brier 0.10286  WF AUC 0.9081  WF Brier 0.0878
REM    v1108: ???  (this run)
REM
REM  After each run completes:
REM    1. Note the final Val Brier from the summary
REM    2. Run: python bump_version.py  (auto-increments to v1108, v1108, etc.)
REM    3. Re-run this batch file
REM ═══════════════════════════════════════════════════════════════

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║  ODIN Perpetual Honing — Starting v1249 run                 ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

REM Delete stale state so it starts fresh from anchor
if exist odin_honing_state.json del odin_honing_state.json
if exist odin_honing_history.csv del odin_honing_history.csv

python odin_honing_engine_v1249.py

echo.
echo Run complete. Check odin_v1108_honed.json for results.
echo To continue: python bump_version.py then re-run this batch file.
pause
