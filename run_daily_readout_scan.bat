@echo off
setlocal EnableDelayedExpansion
title pdufa.bio - DAILY readout scan (unattended)
cd /d "%~dp0"

REM ============================================================================
REM  DAILY UNIVERSAL READOUT SCAN  -- runs unattended, no prompts.
REM
REM  WHY DAILY, AND WHY IT MUST BE DAILY:
REM  A company that names an exact readout day gives a MEASURED MEDIAN OF 3 DAYS
REM  of warning (n=4: NTLA T-3, APGE T-1, MANE T-3, QTTB T-3). A weekly scan
REM  would have missed EVERY ONE of them. There is no version of this that works
REM  on a weekly cadence.
REM
REM  The conference leg is the early one -- TLSA/ECTRIMS surfaced at T-99 -- but
REM  those announcements also drop on no schedule. Both legs need a daily sweep.
REM ============================================================================

set "PY="
where python >nul 2>&1 && set "PY=python"
if not defined PY ( where py >nul 2>&1 && set "PY=py" )
if not defined PY ( echo [ERROR] Python not found. & exit /b 1 )

if not exist "logs" mkdir "logs"
if not exist "daily" mkdir "daily"

for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value 2^>nul') do set "DT=%%I"
set "STAMP=%DT:~0,8%"
set "LOG=logs\daily_scan_%STAMP%_%DT:~8,6%.log"
set "OUT=daily\readouts_%STAMP%.csv"

REM 12-month forward window. --pr turns on BOTH the newswire and conference legs.
REM No --pr-seeded: we sweep the whole listed biotech sector, because a leg that only
REM scans tickers we already found cannot DISCOVER anything (that is how QTTB was missed).
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "& { & '%PY%' phase_readout_miner.py --to (Get-Date).AddDays(365).ToString('yyyy-MM-dd') --sec --pr --max-docs 1500 --listed-only --out '%OUT%' 2>&1 | Tee-Object -FilePath '%LOG%'; exit $LASTEXITCODE }"
set "RC=%ERRORLEVEL%"

if not "%RC%"=="0" (
  echo [%DATE% %TIME%] FAILED rc=%RC% >> logs\daily_scan_status.log
  exit /b %RC%
)

REM ---- surface what is NEW vs yesterday: that is the whole point of running daily ----
"%PY%" daily_diff.py "%OUT%" >> "%LOG%" 2>&1

REM ============================================================================
REM  PRICES: FRESH, NOT LIVE.
REM  The site makes ZERO third-party calls at runtime, deliberately. So the
REM  run-up charts cannot be "live" without re-opening that door AND the
REM  unresolved FMP redistribution question. But they were 26 DAYS stale (stuck
REM  at Jun 18) -- staleness was the real problem, not liveness. Refreshing here
REM  keeps them never more than a day old, with no runtime dependency and no new
REM  redistribution surface. A 120-day run-up path needs a recent last point,
REM  not tick data.
REM ============================================================================
echo [%DATE% %TIME%] refreshing price cache >> "%LOG%"
"%PY%" refresh_pxcache.py >> "%LOG%" 2>&1
"%PY%" _build_pdufa_charts_2026.py >> "%LOG%" 2>&1

REM ---- has the FDA already decided something we still show as pending? ----
REM The archive sweep in build_slate_from_crawl.py can only remove a phantom that
REM is IN the decisions archive. This catches the ones nobody has logged yet --
REM a company announces its own approval within minutes. Reports only, never
REM mutates: a wrong auto-delete on a public calendar beats a stale row for harm.
echo [%DATE% %TIME%] checking for already-decided PDUFAs >> "%LOG%"
"%PY%" check_pdufa_decided.py >> "%LOG%" 2>&1

REM ============================================================================
REM  HOMEPAGE: sweep decided rows + RE-TIME every countdown.
REM  The homepage bakes "<b>7</b><i>days</i>" into the HTML as a literal. It does
REM  not tick. So every countdown drifts one day per day until a rebuild. On
REM  2026-07-15 the page claimed CELC was 7 days out (approved the day before),
REM  MNKD 16 (really 11), CAPR/OTLK 19 (really 14) -- wrong about EVERY row.
REM  This re-derives them from today and promotes the newly decided. Run daily.
REM ============================================================================
echo [%DATE% %TIME%] refreshing homepage (drop decided + re-time countdowns) >> "%LOG%"
"%PY%" refresh_home.py >> "%LOG%" 2>&1

echo [%DATE% %TIME%] OK -> %OUT% >> logs\daily_scan_status.log
endlocal
