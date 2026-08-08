@echo off
title ODIN Perpetual Honing v1108 (Interactions)
echo ============================================
echo  ODIN v1108 — 54 weights (6 interactions)
echo  Plateau-breaking architecture upgrade
echo ============================================
echo.

:loop
echo [%date% %time%] Starting honing run...
python odin_honing_engine_v1108.py --anchor odin_v1108_anchor.json --data ODIN_MODEL_READY_v1070_T1_2015on_ENRICHED.csv
echo.
echo [%date% %time%] Run complete. Bumping version...
python bump_version.py
echo.
echo [%date% %time%] Sleeping 5 seconds before next run...
timeout /t 5 /nobreak >nul
goto loop
