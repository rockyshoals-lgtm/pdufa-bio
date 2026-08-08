@echo off
REM ═══════════════════════════════════════════════════════════════
REM  ODIN Perpetual Honing v2 — WITH OVERFITTING GUARD
REM  
REM  KEY IMPROVEMENT: Tracks BOTH Val Brier and WF Brier.
REM  Only bumps version when WF doesn't degrade beyond tolerance.
REM  Saves best-balanced weights to odin_best_balanced.json.
REM  
REM  Progress tracker:
REM    v1101 start:  Val 0.10183  WF_AUC 0.9076  WF_Brier 0.0885
REM    v1135 sweet:  Val 0.10131  WF_AUC 0.9102  WF_Brier 0.0880
REM    v1237 overfit: Val 0.10086  WF_AUC 0.9092  WF_Brier 0.0895 ← BAD
REM
REM  BEFORE RUNNING: Reset anchor to v1102 (pre-overfit baseline)
REM ═══════════════════════════════════════════════════════════════

echo.
echo +--------------------------------------------------------------+
echo ^|  ODIN Perpetual Honing v2 — Overfitting Guard Active         ^|
echo ^|  Press Ctrl+C to stop gracefully                             ^|
echo +--------------------------------------------------------------+
echo.

REM Delete stale state
if exist odin_honing_state.json del odin_honing_state.json
if exist odin_honing_history.csv del odin_honing_history.csv

python run_perpetual_v2.py

echo.
echo Perpetual honing stopped.
echo Best balanced weights: odin_best_balanced.json
pause
