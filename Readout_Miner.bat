@echo off
REM ==================================================================================
REM  Readout Miner - REAL readout dates only
REM    source 1: company guidance mined from EDGAR (8-K/6-K/10-Q/10-K/20-F/S-1/424B)
REM    source 2: ClinicalTrials.gov, ENROLLMENT-COMPLETE trials only
REM              (ACTIVE_NOT_RECRUITING / COMPLETED - never recruiting/enrolling)
REM  Writes readout_miner.csv + a timestamped log. Double-click to run.
REM
REM  Expect roughly 8-15 minutes: it full-text searches EDGAR and then FETCHES the
REM  actual filings to read the guided date out of the text. Progress prints live.
REM ==================================================================================
cd /d "C:\Users\dcmoo\Documents\Python\9realms"

REM SEC fair-use requires an identifying User-Agent on every request.
set "SEC_USER_AGENT=David Moody rockyshoals@gmail.com"

for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "TS=%%i"
set "LOG=readout_miner_%TS%.log"

echo.
echo  Readout Miner starting...  (EDGAR guidance + CT.gov enrollment-complete)
echo  Log file: %LOG%
echo  This takes ~8-15 min. Progress appears below as it runs.
echo.

REM Tee: show progress live AND save the full log (plain ^> would hide output until the end).
powershell -NoProfile -Command "python readout_miner.py 2>&1 | Tee-Object -FilePath '%LOG%'"

echo.
echo ==================================================================================
echo  Done.  Readout dates  -^> readout_miner.csv
echo  Full log             -^> %LOG%
echo.
echo  Columns: best_date, date_source (BOTH^|EDGAR^|CTGOV), confidence,
echo           guided_date + guided_precision (month/quarter/half/year), status, nct
echo ==================================================================================
pause
