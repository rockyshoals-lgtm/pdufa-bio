@echo off
REM ==================================================================================
REM  READOUT MINER - DEEP company-guidance run
REM
REM  Mines readout dates the companies themselves stated, from SEC EDGAR full text
REM  (8-K / 6-K / 10-Q / 10-K / 20-F / S-1 / 424B), then FETCHES each filing and reads
REM  the guided date out of the sentence around the phrase.
REM
REM  --source edgar     skips the ClinicalTrials.gov sponsor loop entirely (that stage
REM                     rate-limits and was stalling; it is not needed for company guidance)
REM  --edgar-docs 1500  reads up to 1500 filings instead of the default 150. The doc cap
REM                     is THE binding constraint on coverage: a 180-day window turns up
REM                     ~1,370 candidates, so the old 150 cap read only ~11% of them.
REM
REM  Output (both go to the readout_runs folder so nothing collides with the daily bot):
REM     readout_runs\readout_miner_deep.csv
REM     readout_runs\readout_miner_deep_<timestamp>.log
REM
REM  Expect 25-45 minutes. Progress prints live - you'll see query N/132, then fetched N/1500.
REM  Safe to leave running; it checkpoints and will not overwrite the site's data.
REM ==================================================================================
cd /d "C:\Users\dcmoo\Documents\Python\9realms"

REM SEC fair-use requires an identifying User-Agent on every request.
set "SEC_USER_AGENT=David Moody rockyshoals@gmail.com"

if not exist "readout_runs" mkdir "readout_runs"

for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "TS=%%i"
set "LOG=readout_runs\readout_miner_deep_%TS%.log"
set "CSV=readout_runs\readout_miner_deep.csv"

echo.
echo  ==============================================================================
echo   READOUT MINER - DEEP company-guidance run
echo  ==============================================================================
echo   Source   : SEC EDGAR full text (company-stated readout dates)
echo   Doc cap  : 1500 filings   (default is 150 - this is ~10x the coverage)
echo   Window   : 180 days
echo   CSV      : %CSV%
echo   Log      : %LOG%
echo.
echo   This takes roughly 25-45 minutes. Progress prints below.
echo   Tell Claude when it finishes and point at the CSV above.
echo  ==============================================================================
echo.

powershell -NoProfile -Command "python -u readout_miner.py --source edgar --edgar-days 180 --edgar-docs 1500 --out '%CSV%' 2>&1 | Tee-Object -FilePath '%LOG%'"

echo.
echo  ==============================================================================
echo   DONE.
echo   Results : %CSV%
echo   Log     : %LOG%
echo.
echo   Columns : ticker, best_date, date_source, confidence,
echo             guided_date, guided_precision (month/quarter/half/year),
echo             guided_form (which SEC form), guided_filed (filing date)
echo  ==============================================================================
pause
