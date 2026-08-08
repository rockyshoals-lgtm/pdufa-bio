@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
REM Ensure local package import works regardless of CWD
set "PYTHONPATH=%SCRIPT_DIR%;%PYTHONPATH%"
python "%SCRIPT_DIR%run_v38a_signal_discovery.py" %*
REM Ensure prompt starts on a new line even if Python output omitted final newline
echo.
endlocal
