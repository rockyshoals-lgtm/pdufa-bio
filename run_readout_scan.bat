@echo off
setlocal
title pdufa.bio - FORWARD READOUT SCAN (fast, daily)
REM ============================================================================
REM  FORWARD READOUT SCAN  ->  readout_forward.csv
REM
REM  Double-click. ~2 minutes. Run it every morning.
REM
REM  THIS IS NOT run_readout_max.bat. Different question, different runtime:
REM
REM    run_readout_max.bat  = the CENSUS. CT.gov + SEC + newswire, 1,500-6,000 doc
REM                           fetches, 7-30 min. Answers "what is the 2026H2 pipeline".
REM                           Still correct. Run it WEEKLY.
REM
REM    THIS FILE            = "who SAID, in the last 45 days, that a readout is COMING?"
REM                           ~105 FTS calls, ~70 seconds + an optional doc-fetch pass.
REM                           Run it DAILY. It is the list that actually pays.
REM
REM  WHY IT EXISTS - the red team of run_readout_max.bat, 2026-07-17, measured live:
REM
REM   1) THE PHRASE LIST MIXED FORWARD AND PAST, AND THE FLAT QUOTA TREATED THEM ALIKE.
REM        FORWARD  "expects to report topline"     81 docs  -> a readout is COMING. TRADEABLE.
REM        PAST     "Topline Results"            2,337 docs  -> already printed. History.
REM      Same 57-doc quota each. The past-tense phrase (29x bigger) drowned the forward one,
REM      and the forward one is the entire point. This file walks FORWARD phrases only.
REM
REM   2) TWO GENERIC PHRASES WERE 45% OF THE CORPUS AND ~0 SIGNAL:
REM        "will host a conference call"  8,000+ docs (29.3%)
REM        "conference call to discuss"   4,288  docs (15.7%)
REM      Every company hosts conference calls. Excluded here on purpose.
REM
REM   3) A DUPLICATE: "Topline Results" and "topline results" BOTH return 2,337 -- EDGAR FTS
REM      is CASE-INSENSITIVE. It was the same query twice: one wasted quota slot, 57 wasted
REM      fetches. So the list had 25 unique phrases while the quota divided by 26.
REM
REM   4) THE SAMPLE WAS RELEVANCE-RANKED, NOT TIME-RANKED. One call per phrase over 450 days
REM      keeping "the first 57" is not arbitrary -- it is BIASED. And a 14-month-old guidance
REM      is worthless: the window it promised has already closed.
REM
REM  THE FIX IS TIME-SLICING, NOT A BIGGER BUDGET:
REM        450-day window, take 4.6%   -> a thin random skim of mostly-dead guidance (30 min)
REM         45-day window, take ~100%  -> a CENSUS of live guidance                  (70 sec)
REM  PROVEN 2026-07-17: 56 FTS calls, 8 seconds, ZERO doc fetches -> 21 biotech tickers the
REM  workbook did not have, incl. CRBP + AVLN with FORWARD guidance. CRBP is already in the
REM  tape recorder's always-record list and we did not know it had filed 11 days earlier.
REM
REM  ADJACENCY (David's finding, and it is correct): EDGAR FTS matches quoted phrases by
REM  ADJACENCY -- "to report topline" does NOT match "to Report 36-Week Topline Results".
REM  So: search SHORT fragments FTS can hit, then regex the FETCHED DOC for the date. Two
REM  stages. --dates turns on stage 2.
REM ============================================================================
cd /d "C:\Users\dcmoo\Documents\Python\9realms"

set "PY="
where python >nul 2>&1 && set "PY=python"
if not defined PY ( where py >nul 2>&1 && set "PY=py" )
if not defined PY ( echo [ERROR] Python not found on PATH. & pause & exit /b 1 )

REM SEC REQUIRES an identifying User-Agent. Anonymous scrapers are blocked outright.
set "SEC_USER_AGENT=David Moody rockyshoals@gmail.com"

REM 45 days. Long enough to catch guidance filed before a readout; short enough that the
REM window it promised is probably still open. Raise to 90 on a Monday if you want more.
set "DAYS=45"
set "STEP=7"
set "FETCH=60"

if not exist "logs" mkdir "logs"
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value 2^>nul') do set "DT=%%I"
set "LOG=logs\readout_scan_%DT:~0,8%_%DT:~8,6%.log"

echo =====================================================
echo   FORWARD READOUT SCAN
echo   "who said a readout is COMING?"
echo   Last %DAYS% days, %STEP%-day slices, FORWARD phrases only
echo   ~70s for the search + ~%FETCH% doc fetches for the windows
echo =====================================================
echo.

"%PY%" -u readout_scan.py --days %DAYS% --step %STEP% --dates --max-fetch %FETCH% ^
   --out readout_forward.csv 2>&1
if errorlevel 1 (
  echo.
  echo [ERROR] scan failed - see above. readout_forward.csv left as it was.
  pause
  exit /b 1
)

echo.
echo -----------------------------------------------------------------
echo  readout_forward.csv
echo    kind=FORWARD  the company said a readout is COMING  <- the tradeable list
echo    window        the date/period the LEAD regex found IN the filing
echo    url           the actual 8-K/6-K. READ IT before acting.
echo.
echo  A company saying "we expect topline in 2H 2026" is a PLAN, not a commitment.
echo  Readout dates slip constantly. Verify against IR before acting.
echo  Not investment advice.
echo.
echo  Weekly, still run run_readout_max.bat for the full CT.gov+SEC+newswire census.
echo -----------------------------------------------------------------
start "" "readout_forward.csv"
pause
