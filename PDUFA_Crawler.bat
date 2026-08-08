@echo off
setlocal EnableDelayedExpansion
title PDUFA Catalyst Crawler
cd /d "C:\Users\dcmoo\Documents\Python\9realms"

REM ==========================================================================
REM  pdufa.bio catalyst crawler - double-click to refresh the catalyst calendar
REM  from primary sources (SEC 8-K/6-K, FDA AdComm, ClinicalTrials.gov, FMP).
REM
REM  Fast every day (universe only). On SUNDAY it automatically adds the wide
REM  --discover pass (SEC full-text across ALL filers) to catch off-list names.
REM
REM  Writes to catalysts_out\ . This refreshes the CRAWL DATA only - it does NOT
REM  publish to the live website. Review the diff, then run the merge/deploy.
REM ==========================================================================

set "PY="
where python >nul 2>&1 && set "PY=python"
if not defined PY ( where py >nul 2>&1 && set "PY=py" )
if not defined PY ( echo [ERROR] Python not found on PATH. & echo. & pause & exit /b 1 )

REM --- Sundays run the THOROUGH pass, fast universe-only the rest of the week ---
REM   weekdays : static universe (382 known biotech tickers) -- fast, catches on-list filers
REM   Sunday   : --discover (SEC full-text across ALL filers) + --auto-universe (rebuild the
REM              universe from FMP's full healthcare screener) -- catches off-list / new / small
REM              caps the static list misses (this is the completeness lever the BPC audit found)
for /f %%D in ('powershell -NoProfile -Command "(Get-Date).DayOfWeek"') do set "DOW=%%D"
set "DISC="
set "MODE=DAILY (universe only, fast)"
if /I "%DOW%"=="Sunday" ( set "DISC=--discover --auto-universe" & set "MODE=WEEKLY (Sunday: --discover + --auto-universe full sweep)" )

echo =====================================================
echo   PDUFA CATALYST CRAWLER
echo   Today: %DOW%   Mode: %MODE%
echo   Sources: SEC 8-K/6-K, FDA AdComm, ClinicalTrials.gov, FMP
echo   Output:  catalysts_out\   (crawl data only - not published)
echo =====================================================
echo.

"%PY%" -u catalyst_crawler.py --out "./catalysts_out" --fmp %DISC%
set "RC=%ERRORLEVEL%"

echo.
if not "%RC%"=="0" (
  echo [crawler exited with code %RC%] - see the messages above.
  echo.
  pause
  exit /b %RC%
)

echo -----------------------------------------------------------------
echo  Crawl complete. What changed this run:
powershell -NoProfile -Command "$m=Get-Content 'catalysts_out\meta.json' -Raw | ConvertFrom-Json; ('   catalysts: {0}   new: {1}   moved: {2}   dropped: {3}   corrections: {4}' -f $m.catalysts,$m.counts.new,$m.counts.moved,$m.counts.dropped,$m.counts.corrections)"
echo.
echo  Full output: catalysts_out\catalysts_public.csv
echo  Per-catalyst diff: catalysts_out\changes.json
echo.
echo  NOTE: this refreshed the crawl data only. Tell Claude "crawl's done"
echo  to review the diff and publish the verified rows to the live site.
echo -----------------------------------------------------------------
echo.
pause
