@echo off
REM ╔══════════════════════════════════════════════════════════════════╗
REM ║  9REALMS — Reset Training State for v1071 Dataset Migration     ║
REM ║  Archives old champion models & kaizen state, then starts clean ║
REM ║  Run this ONCE after switching to the v1071 dataset             ║
REM ╚══════════════════════════════════════════════════════════════════╝

cd /d "%~dp0"

echo.
echo  ================================================================
echo   9REALMS v1071 MIGRATION RESET
echo  ================================================================
echo.
echo  This will:
echo    1. Archive old champion models (trained on 1349-event dataset)
echo    2. Archive old kaizen state (stale feature names)
echo    3. Clear __pycache__ (stale bytecode)
echo    4. Leave your training data and code untouched
echo.
echo  Old files will be saved to: _archive_pre_v1071\
echo.

set /p CONFIRM="Continue? (y/n): "
if /i not "%CONFIRM%"=="y" (
    echo Aborted.
    pause
    exit /b
)

echo.
echo [Step 1] Creating archive directory...
set ARCHIVE=_archive_pre_v1071
mkdir "%ARCHIVE%" 2>nul
mkdir "%ARCHIVE%\models" 2>nul
mkdir "%ARCHIVE%\kaizen" 2>nul
mkdir "%ARCHIVE%\kaizen_dual" 2>nul
mkdir "%ARCHIVE%\kaizen_gungnir" 2>nul

echo [Step 2] Archiving ODIN champion models...
if exist "models\lgb_champions\champion_ladder.json" (
    xcopy /E /I /Y "models\lgb_champions" "%ARCHIVE%\models\lgb_champions" >nul 2>&1
    echo   Archived models\lgb_champions\
)

echo [Step 3] Archiving GUNGNIR champion models...
if exist "models\gungnir_lgb_champions" (
    xcopy /E /I /Y "models\gungnir_lgb_champions" "%ARCHIVE%\models\gungnir_lgb_champions" >nul 2>&1
    echo   Archived models\gungnir_lgb_champions\
)

echo [Step 4] Archiving kaizen state files...
if exist "kaizen\kaizen_state.json" (
    copy /Y "kaizen\kaizen_state.json" "%ARCHIVE%\kaizen\" >nul 2>&1
    echo   Archived kaizen\kaizen_state.json
)
if exist "kaizen\kaizen_dashboard.json" (
    copy /Y "kaizen\kaizen_dashboard.json" "%ARCHIVE%\kaizen\" >nul 2>&1
    echo   Archived kaizen\kaizen_dashboard.json
)
if exist "kaizen_gungnir\kaizen_state.json" (
    copy /Y "kaizen_gungnir\kaizen_state.json" "%ARCHIVE%\kaizen_gungnir\" >nul 2>&1
    echo   Archived kaizen_gungnir\kaizen_state.json
)
if exist "kaizen_gungnir\kaizen_dashboard.json" (
    copy /Y "kaizen_gungnir\kaizen_dashboard.json" "%ARCHIVE%\kaizen_gungnir\" >nul 2>&1
    echo   Archived kaizen_gungnir\kaizen_dashboard.json
)
if exist "kaizen_dual\dual_state.json" (
    copy /Y "kaizen_dual\dual_state.json" "%ARCHIVE%\kaizen_dual\" >nul 2>&1
    echo   Archived kaizen_dual\dual_state.json
)
if exist "kaizen_dual\dual_dashboard.json" (
    copy /Y "kaizen_dual\dual_dashboard.json" "%ARCHIVE%\kaizen_dual\" >nul 2>&1
    echo   Archived kaizen_dual\dual_dashboard.json
)
if exist "kaizen_dual\odin\kaizen_state.json" (
    mkdir "%ARCHIVE%\kaizen_dual\odin" 2>nul
    copy /Y "kaizen_dual\odin\kaizen_state.json" "%ARCHIVE%\kaizen_dual\odin\" >nul 2>&1
    echo   Archived kaizen_dual\odin\kaizen_state.json
)
if exist "kaizen_dual\gungnir\kaizen_state.json" (
    mkdir "%ARCHIVE%\kaizen_dual\gungnir" 2>nul
    copy /Y "kaizen_dual\gungnir\kaizen_state.json" "%ARCHIVE%\kaizen_dual\gungnir\" >nul 2>&1
    echo   Archived kaizen_dual\gungnir\kaizen_state.json
)

echo.
echo [Step 5] Clearing old ODIN champion models...
del /Q "models\lgb_champions\*.pkl" 2>nul
del /Q "models\lgb_champions\champion_ladder.json" 2>nul
del /Q "models\lgb_champions\ensemble_pool\*.pkl" 2>nul
echo   Cleared models\lgb_champions\

echo [Step 6] Clearing old GUNGNIR champion models...
del /Q "models\gungnir_lgb_champions\*.pkl" 2>nul
del /Q "models\gungnir_lgb_champions\champion_ladder.json" 2>nul
if exist "models\gungnir_lgb_champions\ensemble_pool" (
    del /Q "models\gungnir_lgb_champions\ensemble_pool\*.pkl" 2>nul
)
echo   Cleared models\gungnir_lgb_champions\

echo [Step 7] Clearing old kaizen state...
del /Q "kaizen\kaizen_state.json" 2>nul
del /Q "kaizen\kaizen_dashboard.json" 2>nul
del /Q "kaizen_gungnir\kaizen_state.json" 2>nul
del /Q "kaizen_gungnir\kaizen_dashboard.json" 2>nul
del /Q "kaizen_dual\dual_state.json" 2>nul
del /Q "kaizen_dual\dual_dashboard.json" 2>nul
del /Q "kaizen_dual\ai_config_override.json" 2>nul
del /Q "kaizen_dual\ai_tuning_log.json" 2>nul
if exist "kaizen_dual\odin" del /Q "kaizen_dual\odin\kaizen_state.json" 2>nul
if exist "kaizen_dual\gungnir" del /Q "kaizen_dual\gungnir\kaizen_state.json" 2>nul
echo   Cleared all kaizen state files

echo [Step 8] Clearing __pycache__...
for /d /r . %%d in (__pycache__) do (
    if exist "%%d" (
        rmdir /s /q "%%d" 2>nul
        echo   Removed %%d
    )
)

echo.
echo  ================================================================
echo   RESET COMPLETE
echo  ================================================================
echo.
echo  Old files archived to: %cd%\%ARCHIVE%\
echo.
echo  Next steps:
echo    1. Stop all running daemons (Ctrl+C or create STOP file)
echo    2. Run start_dual_spear.bat to begin fresh training on v1071
echo    3. Round 1 will establish a new champion baseline
echo    4. The daemon will auto-build new ensemble pool from scratch
echo.
pause
