@echo off
REM ===== pdufa.bio — publish the built site to Vercel prod (pdufa.bio) =====
REM Standalone deploy (the full pipeline is run_pdufa_bio.bat). Use this to re-publish
REM the current pdufa_site_src without re-mining.
REM One-time: add  VERCEL_TOKEN=your_token_here  to  "Odin Perfection\.env_master"
REM           (get it at https://vercel.com/account/tokens)
cd /d "%~dp0"

echo Loading VERCEL_TOKEN from "Odin Perfection\.env_master" ...
for /f "usebackq eol=# tokens=1,* delims==" %%a in ("Odin Perfection\.env_master") do set "%%a=%%b"

if "%VERCEL_TOKEN%"=="" (
  echo.
  echo   ERROR: VERCEL_TOKEN not found in "Odin Perfection\.env_master".
  echo   Add one line:   VERCEL_TOKEN=your_token_here
  echo.
  pause
  exit /b 1
)

where vercel >nul 2>&1 || ( echo Installing Vercel CLI one-time ... & npm i -g vercel )

echo.
echo Publishing pdufa_site_src to pdufa.bio (production) ...
echo ------------------------------------------------------------------
cd pdufa_site_src
vercel deploy --prod --yes --token %VERCEL_TOKEN%
cd ..
echo ------------------------------------------------------------------
echo If a *.vercel.app production URL printed above, it published. Give it ~30s, then hard-refresh pdufa.bio.
echo.
pause
