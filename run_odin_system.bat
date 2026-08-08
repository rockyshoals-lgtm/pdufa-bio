@echo off
REM ══════════════════════════════════════════════════════════════
REM  ODIN PERPETUAL SYSTEM LAUNCHER v1.0
REM  Starts both perpetual_loop.py AND audit_cycle.py
REM ══════════════════════════════════════════════════════════════
REM
REM  USAGE:
REM    run_odin_system.bat              (default: both continuous)
REM    run_odin_system.bat loop         (perpetual loop only)
REM    run_odin_system.bat audit        (audit cycle only)
REM    run_odin_system.bat snapshot     (one-shot snapshot + report)
REM    run_odin_system.bat sweep 20     (generate 20 sweep configs)
REM    run_odin_system.bat stop         (kill both processes)
REM
REM ══════════════════════════════════════════════════════════════

setlocal
set PYTHON=python
set SCRIPT_DIR=%~dp0
set LOOP_SCRIPT=%SCRIPT_DIR%perpetual_loop.py
set AUDIT_SCRIPT=%SCRIPT_DIR%audit_cycle.py
set ODIN_DATA=%USERPROFILE%\odin_data
set LOOP_INTERVAL=30
set AUDIT_INTERVAL=1800

REM Create odin_data if missing
if not exist "%ODIN_DATA%" mkdir "%ODIN_DATA%"
if not exist "%ODIN_DATA%\best_runs" mkdir "%ODIN_DATA%\best_runs"

REM Check Python
%PYTHON% --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.10+ and add to PATH.
    pause
    exit /b 1
)

REM Check required files
if not exist "%LOOP_SCRIPT%" (
    echo ERROR: perpetual_loop.py not found at %LOOP_SCRIPT%
    pause
    exit /b 1
)
if not exist "%AUDIT_SCRIPT%" (
    echo ERROR: audit_cycle.py not found at %AUDIT_SCRIPT%
    pause
    exit /b 1
)

REM Route by argument
if "%1"=="" goto BOTH
if "%1"=="both" goto BOTH
if "%1"=="loop" goto LOOP_ONLY
if "%1"=="audit" goto AUDIT_ONLY
if "%1"=="snapshot" goto SNAPSHOT
if "%1"=="sweep" goto SWEEP
if "%1"=="report" goto REPORT
if "%1"=="stop" goto STOP
if "%1"=="status" goto STATUS

echo Unknown command: %1
echo Usage: run_odin_system.bat [both^|loop^|audit^|snapshot^|sweep^|report^|stop^|status]
pause
exit /b 1

:BOTH
echo ══════════════════════════════════════════════════════════════
echo  ODIN SYSTEM — Starting perpetual loop + audit cycle
echo  Loop interval: %LOOP_INTERVAL% min  ^|  Audit interval: %AUDIT_INTERVAL% sec
echo  Data dir: %ODIN_DATA%
echo  Press Ctrl+C in either window to stop that component
echo ══════════════════════════════════════════════════════════════
echo.

REM Generate initial snapshot first
echo [1/3] Generating initial snapshot...
%PYTHON% "%LOOP_SCRIPT%" --mode snapshot > "%ODIN_DATA%\audit_snapshot.json" 2>nul
echo       Snapshot saved to %ODIN_DATA%\audit_snapshot.json

REM Run initial audit report
echo [2/3] Running initial audit report...
%PYTHON% "%AUDIT_SCRIPT%" --mode report
echo.

REM Start both in separate windows
echo [3/3] Launching continuous processes...
start "ODIN Perpetual Loop" cmd /k "%PYTHON% "%LOOP_SCRIPT%" --mode continuous --interval %LOOP_INTERVAL% --train"
timeout /t 5 /nobreak >nul
start "ODIN Audit Cycle" cmd /k "%PYTHON% "%AUDIT_SCRIPT%" --mode continuous --interval %AUDIT_INTERVAL%"

echo.
echo  ✓ Both processes launched in separate windows.
echo  ✓ Perpetual Loop: discovers, enriches, scores, trains every %LOOP_INTERVAL% min
echo  ✓ Audit Cycle: monitors health, promotes, alerts every %AUDIT_INTERVAL% sec
echo.
echo  To stop: run_odin_system.bat stop
echo  To check: run_odin_system.bat status
goto END

:LOOP_ONLY
echo Starting perpetual loop only (continuous, %LOOP_INTERVAL% min interval)...
start "ODIN Perpetual Loop" cmd /k "%PYTHON% "%LOOP_SCRIPT%" --mode continuous --interval %LOOP_INTERVAL% --train"
goto END

:AUDIT_ONLY
echo Starting audit cycle only (continuous, %AUDIT_INTERVAL% sec interval)...
start "ODIN Audit Cycle" cmd /k "%PYTHON% "%AUDIT_SCRIPT%" --mode continuous --interval %AUDIT_INTERVAL%"
goto END

:SNAPSHOT
echo Generating snapshot + audit report...
%PYTHON% "%LOOP_SCRIPT%" --mode snapshot > "%ODIN_DATA%\audit_snapshot.json"
echo Snapshot saved. Running audit...
%PYTHON% "%AUDIT_SCRIPT%" --mode report
goto END

:SWEEP
set TRIALS=%2
if "%TRIALS%"=="" set TRIALS=20
echo Generating %TRIALS% hyperparameter sweep configs...
%PYTHON% "%AUDIT_SCRIPT%" --mode sweep --trials %TRIALS%
echo Sweep configs saved to %ODIN_DATA%\sweep_queue.json
goto END

:REPORT
echo Running audit report...
%PYTHON% "%AUDIT_SCRIPT%" --mode report
goto END

:STOP
echo Stopping ODIN processes...
taskkill /FI "WINDOWTITLE eq ODIN Perpetual Loop" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq ODIN Audit Cycle" /F >nul 2>&1
echo Done. Both processes stopped.
goto END

:STATUS
echo ══════════════════════════════════════════════════════════════
echo  ODIN SYSTEM STATUS
echo ══════════════════════════════════════════════════════════════
echo.

REM Check if processes are running
tasklist /FI "WINDOWTITLE eq ODIN Perpetual Loop" 2>nul | find "cmd" >nul
if errorlevel 1 (echo  Perpetual Loop:  STOPPED) else (echo  Perpetual Loop:  RUNNING)

tasklist /FI "WINDOWTITLE eq ODIN Audit Cycle" 2>nul | find "cmd" >nul
if errorlevel 1 (echo  Audit Cycle:     STOPPED) else (echo  Audit Cycle:     RUNNING)

echo.

REM Show latest audit if available
if exist "%ODIN_DATA%\audit_snapshot.json" (
    echo  Latest snapshot: %ODIN_DATA%\audit_snapshot.json
    for %%A in ("%ODIN_DATA%\audit_snapshot.json") do echo  Last modified:   %%~tA
) else (
    echo  No snapshot found. Run: run_odin_system.bat snapshot
)

REM Show audit history count
if exist "%ODIN_DATA%\audit_history.jsonl" (
    for /f %%C in ('find /c /v "" ^< "%ODIN_DATA%\audit_history.jsonl"') do echo  Audit history:   %%C entries
) else (
    echo  No audit history yet.
)

REM Count best runs
set /a BEST_COUNT=0
for %%F in ("%ODIN_DATA%\best_run_AUC_*.json") do set /a BEST_COUNT+=1
for %%F in ("%ODIN_DATA%\best_runs\best_run_AUC_*.json") do set /a BEST_COUNT+=1
echo  Best runs found: %BEST_COUNT%
echo.
goto END

:END
endlocal
