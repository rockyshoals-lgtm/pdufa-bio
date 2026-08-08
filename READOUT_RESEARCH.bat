@echo off
setlocal enabledelayedexpansion
title 9Realms - PHASE READOUT RESEARCH
REM ============================================================================
REM  PHASE READOUT RESEARCH  --  double-click me.
REM
REM  Put this on your desktop. It runs the two readout jobs back to back and
REM  leaves a timestamped log you can reopen any time:
REM
REM    1) FORWARD SCAN   readout_scan.py -> readout_forward.csv
REM       "who told the SEC, in the last 45 days, that a readout is COMING?"
REM       ~2 minutes, hits EDGAR. Now with the QUARTER-BUCKET fix: a "Sep 30"
REM       that is really "3Q 2026" is labelled Q3, not trusted as a hard day.
REM
REM    2) RESEARCH       readout_research.py
REM       how many readouts per week, the reaction base rate since 2025
REM       (median +3%, only 1 in 8 pops >=15%), and the forward names
REM       BiopharmaCatalyst lists that we do NOT cover yet.
REM       Reads the NEWEST historical_*.xlsx and fda_*.xlsx from bpc_data\.
REM
REM  TO REFRESH WITH NEWER DATA: download the BiopharmaCatalyst historical and
REM  FDA exports, drop them in the bpc_data\ folder (keep the date in the name,
REM  e.g. historical_2026-08-01.xlsx), and run this again. It always uses the
REM  newest of each.
REM
REM  Not investment advice. Daily-close reactions understate the intraday move.
REM ============================================================================
cd /d "C:\Users\dcmoo\Documents\Python\9realms"

REM --- find python -----------------------------------------------------------
set "PY="
where python >nul 2>&1 && set "PY=python"
if not defined PY ( where py >nul 2>&1 && set "PY=py" )
if not defined PY ( echo [ERROR] Python not found on PATH. & pause & exit /b 1 )

REM SEC requires an identifying User-Agent for the forward EDGAR scan.
set "SEC_USER_AGENT=David Moody rockyshoals@gmail.com"

if not exist "logs" mkdir "logs"
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value 2^>nul') do set "DT=%%I"
set "STAMP=%DT:~0,8%_%DT:~8,6%"
set "LOG=logs\readout_research_%STAMP%.log"

echo =====================================================
echo   9REALMS PHASE READOUT RESEARCH
echo   %DATE% %TIME%
echo   log: %LOG%
echo =====================================================
echo.

REM ============================ 1) FORWARD SCAN ============================
REM  Straight redirect to the log (2>&1 captures errors too), then TYPE it so
REM  you see the results. No fragile pipe/tee -- a .bat that breaks on quoting
REM  is worse than one that streams a little late.
echo [1/5] FORWARD EDGAR SCAN  (who SAID a readout is coming) ... please wait ~2 min
"%PY%" -u readout_scan.py --days 45 --step 7 --dates --max-fetch 80 --out readout_forward.csv  > "%LOG%" 2>&1
if errorlevel 1 echo   [warn] forward scan returned an error - see the log.
type "%LOG%"
echo.

REM ============================ 2) CT.GOV READOUTS ============================
REM  The SPECIFIC-DATE pass. EDGAR only finds companies that SAID a readout is coming
REM  in the last 45 days, in our phrasing -- it missed SLS entirely (guided months ago,
REM  went quiet). ClinicalTrials.gov has the trial's PRIMARY COMPLETION DATE, which is
REM  the calendar "data locks on <date>" signal -- far more specific ("2026-12-30" vs
REM  "2H 2026") and it does NOT depend on any EDGAR filing. Reads readout_watchlist.txt
REM  (seed it with names you KNOW have a readout coming) + every ticker already found.
echo [2/5] CT.GOV READOUTS  (specific primary-completion dates; catches SLS) ...
"%PY%" -u ctgov_readouts.py  >> "%LOG%" 2>&1
if errorlevel 1 echo   [warn] ctgov readouts returned an error - see the log.

REM ============================ 3) SMART MONEY ============================
REM  Adds options-flow + dark-pool columns to readout_forward.csv (what smart
REM  money is doing INTO each readout). Reads the CSV step 1 just wrote.
REM  IMPORTANT: if readout_forward.csv is OPEN (Excel / a viewer) the write is
REM  locked and it falls back to readout_forward_enriched.csv -- so CLOSE the
REM  CSV before running if you want the columns in the main file.
echo [3/5] SMART MONEY  (options flow + dark pool per catalyst) ...
"%PY%" -u smart_money_enrich.py  >> "%LOG%" 2>&1
if errorlevel 1 echo   [warn] smart-money enrich returned an error - see the log.

REM ============================ 4) MERGE -> CALENDAR ============================
REM  THE MASTER VIEW. Unifies EDGAR guidance (vague dates + smart money) with the
REM  CT.gov specific dates into readout_calendar.csv -- one row per ticker, the most
REM  specific date we have, sorted by IMMINENCE (data pending now at the top, stale
REM  overdue at the bottom). Flags where EDGAR and CT.gov disagree (EDGAR "Q4 2026"
REM  vs CT.gov "data locked already") -- those disagreements are the sharp signals.
echo [4/5] MERGE  (unify EDGAR + CT.gov -^> readout_calendar.csv) ...
"%PY%" -u readout_merge.py  >> "%LOG%" 2>&1
if errorlevel 1 echo   [warn] merge returned an error - see the log.

REM ============================ 4) RESEARCH ================================
echo [5/5] HISTORICAL RESEARCH  (frequency, reactions, gaps) ...
echo. >> "%LOG%"
REM --cached: use the saved reaction-price cache instead of re-fetching ~900 tickers
REM every run. The reaction base rate is 2025-2026 HISTORY -- it does not change day to
REM day, and re-fetching is the slow, dead-hostname-hang-prone part. Frequency and the gap
REM list still come from the FRESH xlsx each run. Drop a much newer historical file and
REM delete Momentum Scanner\_DATA\_hist_eod_cache.json if you want prices rebuilt.
"%PY%" -u readout_research.py --cached  >> "%LOG%" 2>&1
if errorlevel 1 echo   [warn] research returned an error - see the log.
REM show just the research section that we appended (skip re-typing the scan)
"%PY%" -c "import io;t=io.open(r'%LOG%',encoding='utf-8',errors='replace').read();i=t.rfind('9REALMS PHASE-READOUT RESEARCH');print(t[i-2:] if i>0 else t[-4000:])"

echo.
echo -----------------------------------------------------------------
echo  DONE.
echo    readout_calendar.csv  ** THE MASTER VIEW ** one row per ticker, best date,
echo       sorted by imminence: DATA PENDING NOW at top, STALE at bottom.
echo       confidence BOTH = EDGAR said AND CT.gov dated (highest).  !DISAGREE = the
echo       two sources conflict (EDGAR "Q4" vs CT.gov "locked already") -- sharp signal.
echo    readout_forward.csv   EDGAR "company SAID a readout is coming" + smart-money:
echo       window     the readout quarter/date  (from EDGAR, quarter-bucket aware)
echo       sm_signal  BULLISH / MIXED / BEARISH / QUIET  (options + dark pool)
echo       sm_cp_ratio  call/put volume   sm_unusual_x  vol vs 30-day avg
echo       sm_dp_lean   ACCUM / DISTRIB   sm_dp_prem  dark-pool dollars
echo    ctgov_readouts.csv    ClinicalTrials.gov "data LOCKS on <specific date>":
echo       pcd  the primary completion date (~ = estimated)   days_to_pcd  countdown
echo       negative days_to_pcd = OVERDUE, data pending -- often the most imminent
echo    %LOG%
echo.
echo  A readout is +3%% on average and only 1 in 8 pops >=15%%. The edge is
echo  FILTERING (real catalyst, Phase 1/2, small-cap, cheap) + a fast exit,
echo  not holding. sm_* is a READ on positioning, NOT a signal -- options flow
echo  mixes smart money, dealer hedging and retail. Verify dates against IR/EDGAR.
echo  Not investment advice.
echo -----------------------------------------------------------------

REM open the results so you can read them
start "" "%LOG%"
if exist "readout_calendar.csv" start "" "readout_calendar.csv"
if exist "readout_forward.csv" start "" "readout_forward.csv"
if exist "ctgov_readouts.csv" start "" "ctgov_readouts.csv"
pause
