@echo off
REM ==================================================================================
REM  READOUT MINER - DEEP company-guidance run   (v2)
REM
REM  Mines readout dates the companies themselves stated, from SEC EDGAR full text
REM  (8-K / 6-K / 10-Q / 10-K / 20-F / S-1 / 424B), then FETCHES each filing and reads
REM  the guided date out of the sentence around the phrase.
REM
REM  WHAT CHANGED after the first deep run returned 222 unusable rows:
REM    * INDUSTRY GATE  - only SEC SIC 2834/2836/8731/2835/2833 filers get fetched, so
REM                       gold miners, utilities, banks and Waste Management can no
REM                       longer enter the set. It runs BEFORE the document fetch, so
REM                       the doc budget is now spent only on drug companies (which
REM                       also makes 1500 docs go roughly twice as far).
REM    * NAMED PROGRAM  - a row is kept only if the matched sentence names the drug,
REM                       the trial, or an NCT number. "Results are expected in Q4"
REM                       with nothing attached is not a calendar entry.
REM    * PROVENANCE     - every row carries filing_url, accession and the exact
REM                       matched_sentence, so it can be checked without re-searching.
REM    * CALENDAR VS WATCHLIST - only month/quarter guidance reaches the main CSV.
REM                       "1H 2027" and bare "2027" go to a separate watchlist file
REM                       with the precision stated, instead of inventing a Dec 31st.
REM
REM  EXPECT FEWER ROWS THAN LAST TIME. That is the point.
REM
REM  Output (all in readout_runs\ so nothing collides with the daily bot):
REM     readout_runs\readout_miner_deep.csv             calendar-grade
REM     readout_runs\readout_miner_deep_watchlist.csv   guided but too vague to date
REM     readout_runs\readout_miner_deep_<timestamp>.log
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
echo   READOUT MINER - DEEP company-guidance run  (v2: gated + program-verified)
echo  ==============================================================================
echo   Source   : SEC EDGAR full text (company-stated readout dates)
echo   Filter   : drug developers only, and every row must name a program
echo   Doc cap  : 1500 filings
echo   Window   : 180 days
echo   CSV      : %CSV%
echo   Watchlist: readout_runs\readout_miner_deep_watchlist.csv
echo   Log      : %LOG%
echo.
echo   First run also builds an SEC industry-code cache (a few minutes, once).
echo   Roughly 25-45 minutes total. Progress prints below.
echo   Tell Claude when it finishes and point at the CSV above.
echo  ==============================================================================
echo.

powershell -NoProfile -Command "python -u readout_miner.py --source edgar --edgar-days 180 --edgar-docs 1500 --out '%CSV%' 2>&1 | Tee-Object -FilePath '%LOG%'"

echo.
echo  ==============================================================================
echo   DONE.
echo   Calendar grade : %CSV%
echo   Watchlist      : readout_runs\readout_miner_deep_watchlist.csv
echo   Log            : %LOG%
echo.
echo   Key columns : ticker, best_date, guided_precision (month/quarter only in the
echo                 main CSV), program, program_kind, filing_url, accession,
echo                 matched_sentence, sic_desc
echo  ==============================================================================
pause
