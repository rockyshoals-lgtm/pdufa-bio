@echo off
setlocal EnableDelayedExpansion
title pdufa.bio - Phase Readout Miner
cd /d "C:\Users\dcmoo\Documents\Python\9realms"
echo =====================================================
echo   PHASE READOUT MINER
echo   [1] CT.gov  - every trial's primary completion date
echo   [2] SEC     - what the company TOLD the market
echo   sponsor-independent ^| fully paginated ^| no caps
echo =====================================================
echo.
set "PY="
where python >nul 2>&1 && set "PY=python"
if not defined PY ( where py >nul 2>&1 && set "PY=py" )
if not defined PY ( echo [ERROR] Python not found. & echo. & pause & exit /b 1 )
echo Using Python: %PY%
echo.
echo   [1]  FULL  - CT.gov + SEC filings, rest of 2026   (recommended, ~5-15 min)
echo        Scrubs non-catalysts, tiers by imminence, and KILLS already-read-out
echo        readouts from company PRs (needs FMP_API_KEY). No slow sector sweep.
echo   [2]  FAST  - CT.gov only, rest of 2026            (~1-2 min, incl. kill-enrichment)
echo   [3]  SEC only - company guidance, rest of 2026    (no CT.gov, so no kill-enrichment)
echo   [4]  FULL  - next 12 months
echo   [5]  PIPELINE VIEW - readouts + still-enrolling trials (flagged)
echo   [6]  Custom
echo   [7]  EVERYTHING + NEWSWIRE SWEEP - options 1 PLUS a 900-ticker sweep for
echo        brand-new EXACT-DAY scheduling PRs + conference dates  (~20-40 min)
echo        Newswire rows are redistribute=False - QA yardstick only, DO NOT PUBLISH.
echo.
set "CH="
set /p CH="Choice [1]: "
if "%CH%"=="" set "CH=1"

set "SRC=--sec"
set "TO=2026-12-31"
set "DOCS=1500"
set "OUT=phase_readouts_2026H2.csv"
set "FROMARG="

if "%CH%"=="2" ( set "SRC=" & set "OUT=phase_readouts_ctgov.csv" )
if "%CH%"=="3" ( set "SRC=--sec-only" & set "OUT=phase_readouts_guidance.csv" )
if "%CH%"=="4" ( set "TO=2027-07-12" & set "OUT=phase_readouts_next12m.csv" )
if "%CH%"=="5" ( set "SRC=--sec --include-enrolling" & set "OUT=phase_readouts_pipeline.csv" )
if "%CH%"=="7" ( set "SRC=--sec --pr" & set "OUT=phase_readouts_2026H2_newswire.csv" )
if "%CH%"=="6" (
  set /p FROM="  From (YYYY-MM-DD, blank=today): "
  set /p TO="  To   (YYYY-MM-DD): "
  set /p DOCS="  Max SEC docs [1500]: "
  set /p OUT="  Output filename: "
  set /p WSEC="  Include SEC filings? (Y/n): "
  if /i "!WSEC!"=="n" set "SRC="
  if not "!FROM!"=="" set "FROMARG=--from !FROM!"
  if "!DOCS!"=="" set "DOCS=1500"
)

set /p LISTED="  US-listed tickers only? (Y/n): "
set "LARG=--listed-only"
if /i "%LISTED%"=="n" set "LARG="

if not exist "logs" mkdir "logs"
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value 2^>nul') do set "DT=%%I"
set "LOG=logs\readout_miner_%DT:~0,8%_%DT:~8,6%.log"

echo.
echo -----------------------------------------------------
echo  to=%TO%  %SRC%  max-docs=%DOCS%  %LARG%
echo  out=%OUT%
echo  log=%LOG%
echo -----------------------------------------------------
echo.
powershell -NoProfile -ExecutionPolicy Bypass -Command "& { & '%PY%' phase_readout_miner.py %FROMARG% --to %TO% %SRC% --max-docs %DOCS% %LARG% --out '%OUT%' 2>&1 | Tee-Object -FilePath '%LOG%'; exit $LASTEXITCODE }"
set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" (
  echo =====================================================
  echo   DONE.  -^> %OUT%
  echo   date_basis=company_guidance = the company said it
  echo   date_basis=ctgov_pcd        = trial completion PROXY
  echo =====================================================
) else (
  echo   FINISHED WITH ERRORS ^(exit %RC%^) - see %LOG%
)
echo.
echo Press any key to close...
pause >nul
endlocal

