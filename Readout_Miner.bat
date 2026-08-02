@echo off
REM ================================================================
REM  Readout Miner - enrollment-complete readouts only (no enrolling trials)
REM  Writes readout_miner.csv + a timestamped log. Double-click to run.
REM ================================================================
cd /d "C:\Users\dcmoo\Documents\Python\9realms"

set "TS=%date:~-4%%date:~4,2%%date:~7,2%_%time:~0,2%%time:~3,2%%time:~6,2%"
set "TS=%TS: =0%"
set "LOG=readout_miner_%TS%.log"

echo Running readout miner ... (this can take a few minutes across the full universe)
echo Log: %LOG%
echo.

python readout_miner.py 1> "%LOG%" 2>&1

echo.
type "%LOG%"
echo.
echo ================================================================
echo  Done. Readouts written to: readout_miner.csv
echo  Full log: %LOG%
echo ================================================================
pause
