@echo off
setlocal EnableDelayedExpansion
title pdufa.bio - Conference Crawler
cd /d "%~dp0"

echo ===============================================
echo   pdufa.bio  -  CONFERENCE CRAWLER
echo   40 conference searches ^| 92 aliases
echo ===============================================
echo.

REM ---- find Python (PATH, then py launcher, then common install dirs) ----
set "PY="
where python >nul 2>&1 && set "PY=python"
if not defined PY ( where py >nul 2>&1 && set "PY=py" )
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
if not defined PY if exist "C:\Python312\python.exe" set "PY=C:\Python312\python.exe"
if not defined PY (
  echo [ERROR] Could not find Python on this machine.
  echo         Install it, or edit this file and set PY= to your python.exe
  echo.
  pause
  exit /b 1
)
echo Using Python: %PY%
echo.

echo Pick a run:
echo.
echo   [1]  REBUILD (recommended)  - re-derive from scratch, since 2024   (~30-60 min)
echo        The extractor was fixed (it used to turn PAST presentations into
echo        FUTURE catalysts). An append would keep the old wrong rows, because
echo        the fix changes their dates. Rebuild is the only clean option.
echo.
echo   [2]  Quick update  - append only, last 6 months          (~5-10 min)
echo   [3]  Full backfill - append only, since 2024             (~30-60 min)
echo   [4]  Custom
echo.
set "CH="
set /p CH="Choice [1]: "
if "%CH%"=="" set "CH=1"

set "REBUILD="
if "%CH%"=="1" ( set "SINCE=2024-01-01" & set "DOCS=2500" & set "REBUILD=--rebuild" )
if "%CH%"=="2" ( set "SINCE=2026-01-01" & set "DOCS=600" )
if "%CH%"=="3" ( set "SINCE=2024-01-01" & set "DOCS=2500" )
if "%CH%"=="4" (
  set /p SINCE="  Since date (YYYY-MM-DD): "
  set /p DOCS="  Max filings to fetch: "
  set /p RB="  Rebuild from scratch? (y/N): "
  if /i "!RB!"=="y" set "REBUILD=--rebuild"
)
if not defined SINCE ( echo Invalid choice. & echo. & pause & exit /b 1 )

REM ---- timestamped log so a crash is never invisible ----
if not exist "logs" mkdir "logs"
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value 2^>nul') do set "DT=%%I"
set "STAMP=%DT:~0,8%_%DT:~8,6%"
set "LOG=logs\conference_crawl_%STAMP%.log"

echo.
echo -----------------------------------------------
echo  since=%SINCE%   max-docs=%DOCS%   %REBUILD%
echo  log:  %LOG%
echo -----------------------------------------------
echo.

REM Run python INSIDE powershell so we get live output AND a log AND python's real exit code.
REM (A plain cmd pipe would set ERRORLEVEL from the last command in the pipe, not from python.)
powershell -NoProfile -ExecutionPolicy Bypass -Command "& { & '%PY%' run_conference_crawl.py --since %SINCE% --max-docs %DOCS% %REBUILD% 2>&1 | Tee-Object -FilePath '%LOG%'; exit $LASTEXITCODE }"

set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" (
  echo ===============================================
  echo   DONE.  History file updated:
  echo   catalysts_out\conference_presentations_history.csv
  echo   A rollback copy sits next to it (.bak / .pre_rebuild_*).
  echo ===============================================
) else (
  echo ===============================================
  echo   FINISHED WITH ERRORS  ^(exit code %RC%^)
  echo   Full output saved to: %LOG%
  echo ===============================================
)
echo.
echo Press any key to close...
pause >nul
endlocal
