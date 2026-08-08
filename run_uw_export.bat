@echo off
setlocal EnableDelayedExpansion
title UW BULK EXPORT - dark pool + option flow for 2026 catalysts (before cancel)
cd /d "C:\Users\dcmoo\Documents\Python\9realms"

REM ============================================================================
REM  ONE-TIME: put your Unusual Whales API token in "Odin Perfection\.env_master"
REM            as a single line:   UW_API_KEY=your_token_here
REM            (get it at unusualwhales.com -> Settings -> API)
REM  Then double-click this file. It pulls EVERYTHING UW has for all 134 catalyst
REM  tickers - dark pool (paginated deep), option flow, greeks, OI, net-premium -
REM  and saves raw JSON to uw_export_2026\. Resumable: re-run to continue if it stops.
REM ============================================================================

set "PY="
where python >nul 2>&1 && set "PY=python"
if not defined PY ( where py >nul 2>&1 && set "PY=py" )
if not defined PY ( echo [ERROR] Python not found on PATH. & echo. & pause & exit /b 1 )

findstr /b /i "UW_API_KEY UNUSUAL_WHALES_API_KEY UNUSUALWHALES_API_KEY UW_TOKEN" "Odin Perfection\.env_master" >nul 2>&1
if errorlevel 1 (
  echo.
  echo   No UW key found in "Odin Perfection\.env_master".
  echo   Add one line:   UW_API_KEY=your_unusualwhales_token
  echo   Then re-run this file.
  echo.
  pause
  exit /b 1
)

if not exist "logs" mkdir "logs"
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value 2^>nul') do set "DT=%%I"
set "LOG=logs\uw_export_%DT:~0,8%_%DT:~8,6%.log"

echo =====================================================
echo   UW BULK EXPORT  (UW cancels soon - grabbing it all)
echo   134 catalyst tickers, ~23 endpoints each + deep dark pool
echo   Output: uw_export_2026\   Log: %LOG%
echo =====================================================
echo.
echo [1/2] Discovery - checking which endpoints your account can reach...
"%PY%" uw_export.py --discover
echo.
echo [2/2] Full export (resumable). This runs a while; leave it open.
echo        (progress prints here; per-request status also in uw_export_2026\_log.csv)
echo.
"%PY%" uw_export.py --rps 3 --workers 5 --dp-max 8000

echo.
echo -----------------------------------------------------------------
echo  Done. Raw JSON in uw_export_2026\<TICKER>\<endpoint>.json
echo  Per-request status log: uw_export_2026\_log.csv
echo  If it stopped early (rate limit / network), just double-click again;
echo  it skips files already saved and continues.
echo -----------------------------------------------------------------
echo.
pause
