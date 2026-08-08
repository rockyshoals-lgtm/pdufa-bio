@echo off
REM ╔══════════════════════════════════════════════════════════════════╗
REM ║  ODIN LAUNCH — One-Click Perpetual Loop + Audit Cycle          ║
REM ║                                                                ║
REM ║  Usage:                                                        ║
REM ║    launch_odin.bat              (full system)                  ║
REM ║    launch_odin.bat preflight    (check only)                   ║
REM ║    launch_odin.bat dashboard    (dashboard only)               ║
REM ║    launch_odin.bat loop-only    (perpetual loop only)          ║
REM ║    launch_odin.bat audit-only   (audit cycle only)             ║
REM ╚══════════════════════════════════════════════════════════════════╝

title ODIN Perpetual Loop System
cd /d "%USERPROFILE%\Documents\Python"

echo.
echo  ╔═══════════════════════════════════════════════╗
echo  ║    ODIN PERPETUAL LOOP — SYSTEM LAUNCHER     ║
echo  ╚═══════════════════════════════════════════════╝
echo.

REM ── Handle modes ──
if "%1"=="preflight" goto PREFLIGHT
if "%1"=="dashboard" goto DASHBOARD
if "%1"=="loop-only" goto LOOP_ONLY
if "%1"=="audit-only" goto AUDIT_ONLY

REM ── Default: Full system launch ──

echo  [1/4] Running preflight checks...
echo.
python odin_preflight.py
if errorlevel 1 (
    echo.
    echo  ❌ Preflight FAILED. Fix errors above before launching.
    echo  Press any key to exit...
    pause >nul
    exit /b 1
)

echo.
echo  [2/4] Starting Perpetual Loop (background)...
start "ODIN Perpetual Loop" /min cmd /c "python perpetual_loop.py --mode continuous --interval 30 & pause"

echo  [3/4] Starting Audit Cycle (background)...
timeout /t 5 /nobreak >nul
start "ODIN Audit Cycle" /min cmd /c "python audit_cycle.py --mode continuous --interval 1800 & pause"

echo  [4/4] Launching Dashboard...
echo.
echo  ✅ All systems online.
echo  - Perpetual Loop: running in background (30min cycles)
echo  - Audit Cycle: running in background (30min cycles)
echo  - Dashboard: launching now...
echo.
echo  To stop: close the ODIN Perpetual Loop and ODIN Audit Cycle windows
echo.

python odin_dashboard.py --mode watch --interval 120

goto END

:PREFLIGHT
echo  Running preflight checks only...
python odin_preflight.py
goto END

:DASHBOARD
echo  Launching dashboard only...
python odin_dashboard.py --mode watch
goto END

:LOOP_ONLY
echo  Starting Perpetual Loop only (foreground)...
python perpetual_loop.py --mode continuous --interval 30
goto END

:AUDIT_ONLY
echo  Starting Audit Cycle only (foreground)...
python audit_cycle.py --mode continuous --interval 1800
goto END

:END
echo.
echo  ODIN session ended.
pause
