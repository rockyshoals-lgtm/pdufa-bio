@echo off
setlocal EnableDelayedExpansion
title pdufa.bio - MAX READOUT MINE (double-click)
REM ============================================================================
REM  MAX READOUT MINE  ->  phase_readouts_2026H2.csv  ->  phase_readouts_2026H2.xlsx
REM
REM  Double-click. No menu, no prompts. Runs everything and opens the workbook.
REM
REM  This is option [7] of run_phase_readout_miner.bat (CT.gov + SEC + newswire
REM  sector sweep) PLUS the horizon filter PLUS the Excel build, in one shot.
REM
REM  WHAT "MAX" MEANS HERE, AND WHAT IT DELIBERATELY EXCLUDES:
REM    max SOURCES  - CT.gov + SEC full-text + 900-ticker newswire/conference sweep
REM    NOT max ROWS - still-enrolling trials are NOT mined. A trial still taking
REM                   patients has not read out and will not read out on its stated
REM                   date. 67% of the old H2 file (1,552 of 2,323) was exactly that.
REM                   For pipeline visibility use run_phase_readout_miner.bat [5].
REM
REM  ABSOLUTE cd: this file gets copied to the Desktop, where %~dp0 is the Desktop
REM  and every relative path breaks. Hard-code the repo. (Same reason as the other .bat.)
REM ============================================================================
cd /d "C:\Users\dcmoo\Documents\Python\9realms"

set "PY="
where python >nul 2>&1 && set "PY=python"
if not defined PY ( where py >nul 2>&1 && set "PY=py" )
if not defined PY ( echo [ERROR] Python not found on PATH. & echo. & pause & exit /b 1 )

REM Horizon. IMMINENT (<=45d) + NEAR (46-90d) + OVERDUE (data locked, topline pending).
REM Drops SCHEDULED (91-180d) and DISTANT (>180d) - closed enrollment alone is not imminence.
set "TO=2026-12-31"
set "DAYS=90"

REM ---------------------------------------------------------------------------
REM  DOCS: the single most important number in this file. RAISED 1500 -> 6000.
REM
REM  phase_readout_miner.sec_guidance_readouts() sets a PER-PHRASE quota:
REM        quota = max(30, max_docs // len(GUIDANCE_PHRASES))
REM  With 26 phrases, --max-docs 1500 gives quota = 57. That is the wall of "57"s
REM  in every run log, and ~16 of the 26 phrases hit it EXACTLY - i.e. they
REM  saturated and were silently truncated.
REM
REM  Measured 2026-07-16 against EDGAR FTS over the miner's own 450d window:
REM        "topline results"            2,337 available -> 57 taken
REM        "topline data"               2,409 available -> 57 taken
REM        "conference call to discuss" 4,298 available -> 57 taken
REM        10 phrases:                 12,900 available -> 570 taken  = 4.4% COVERAGE
REM  And WHICH 57 is arbitrary - whatever EDGAR happens to return first.
REM
REM  6000 -> quota 230, ~4x the coverage. This buys company_guidance rows, which
REM  are the ONLY committed windows we get (CT.gov gives an estimate; the newswire
REM  gives ~1 exact day per run). Today only 17% of workbook rows are company-stated.
REM  That ratio is the scoreboard, and this is the lever that moves it.
REM
REM  Cost: docs are fetched one-by-one, so runtime scales with this number.
REM  1500 docs ~= 7 min (measured on the 6:15pm daily). 6000 ~= 25-30 min.
REM  Raise further only if you are willing to sit through it - EDGAR is rate-capped,
REM  not bandwidth-capped, so there is no way to make this fast.
REM ---------------------------------------------------------------------------
set "DOCS=6000"
set "OUT=phase_readouts_2026H2.csv"
set "XLSX=phase_readouts_2026H2.xlsx"

if not exist "logs" mkdir "logs"
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value 2^>nul') do set "DT=%%I"
set "LOG=logs\readout_max_%DT:~0,8%_%DT:~8,6%.log"

echo =====================================================
echo   MAX READOUT MINE
echo   CT.gov (enrollment closed + data lock hit)
echo   SEC full-text guidance   (what the company SAID)
echo   Newswire sector sweep    (the only EXACT DAY there is)
echo   Horizon: %DAYS%d + OVERDUE   To: %TO%
echo   Python: %PY%
echo =====================================================
echo.
echo Expect ~30-50 min. SEC doc fetch (%DOCS% docs) and the newswire sweep are the slow legs.
echo Log: %LOG%
echo.
echo NOTE: this writes %OUT% - NOT the 6:15pm daily scan, which writes
echo       daily\readouts_YYYYMMDD.csv and keeps ALL tiers on purpose. The two
echo       files are different scopes; do not compare their row counts.
echo.

echo [1/3] mining...
"%PY%" phase_readout_miner.py --to %TO% --sec --pr --max-docs %DOCS% --listed-only --imminent-days %DAYS% --out "%OUT%" 2>&1
if errorlevel 1 (
  echo.
  echo [ERROR] miner failed - see the console above. Workbook NOT rebuilt,
  echo         so the existing %XLSX% is untouched rather than half-updated.
  echo.
  pause
  exit /b 1
)

echo.
echo [2/3] building workbook...
REM build_readout_xlsx.py ABORTS if a still-enrolling or DISTANT row got through, and
REM drops PAST rows (stated window already closed). If it aborts, the old .xlsx is left
REM alone on purpose - a stale workbook beats a contaminated one.
"%PY%" build_readout_xlsx.py --csv "%OUT%" --out "%XLSX%"
if errorlevel 1 (
  echo.
  echo [ERROR] workbook build refused the data - read the ABORT line above.
  echo         %XLSX% was left as it was. Fix the mine, do not force it.
  echo.
  pause
  exit /b 1
)

echo.
echo [3/3] done. Opening %XLSX% ...
start "" "%XLSX%"
echo.
echo -----------------------------------------------------------------
echo  Read the DATE COLOUR before the date:
echo    GREEN  company told the market (SEC filing)
echo    BLUE   exact day from a conference session / scheduling PR
echo    AMBER  CT.gov ESTIMATE - sponsor-typed, slips, proxy only
echo    GREY   no date (topline overdue) - use data_lock_date
echo  Any row marked redistribute=False is INTERNAL: FMP terms unread.
echo  Not investment advice. Verify against company IR / SEC before acting.
echo -----------------------------------------------------------------
echo.
pause
