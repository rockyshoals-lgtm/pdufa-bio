@echo off
REM ============================================================================
REM  pdufa.bio  —  ONE-CLICK: mine -> build calendar -> deploy free public site
REM  A single run does everything:
REM    [1] FULL MINE       catalyst_crawler.py (SEC EDGAR + CT.gov + FDA AdCom +
REM                        openFDA + FMP), primary-sourced, ~2-4 hrs. Leave it open.
REM    [2] SCORE + PAGES   GUNGNIR readout scores + category calendars + SEO + archive.
REM    [3] MERGE DATA      build_slate_from_crawl.py folds the fresh mine into the live
REM                        calendar (api/data.js SLATE), KEEPING curated outcomes/NCT.
REM    [4] FLIP SITE       apply_calendar_site_state.py -> FREE PUBLIC PDUFA CALENDAR
REM                        (homepage = calendar, password gate off, pricing stripped).
REM    [5] DEPLOY          Vercel prod -> pdufa.bio  (needs VERCEL_TOKEN in .env_master).
REM  Keys are read from  Odin Perfection\.env_master.
REM ============================================================================
setlocal
cd /d "%~dp0"
title pdufa.bio — mine + build + deploy (one click)

set "PY=python"
where py >nul 2>&1 && set "PY=py -3"

echo Loading API keys + VERCEL_TOKEN from "Odin Perfection\.env_master" ...
for /f "usebackq eol=# tokens=1,* delims==" %%a in ("Odin Perfection\.env_master") do set "%%a=%%b"

echo Installing Python deps (one-time) ...
%PY% -m pip install -q requests pandas python-dateutil openpyxl

echo(
echo ============================================================
echo  [1/5] FULL MINE — primary sources, ~2-4 hrs. Leave this open.
echo ============================================================
%PY% catalyst_crawler.py --tickers pdufa_universe.txt --auto-universe --discover --bpc fda_2026-07-09.xlsx --fmp --options --ua "pdufa.bio catalyst research rockyshoals@gmail.com"

echo(
echo ============================================================
echo  [2/5] Score readouts + build calendar / SEO pages + archive
echo ============================================================
%PY% gungnir_score_catalysts.py catalysts_out\catalysts_public.csv catalysts_out\catalysts_scored.csv
%PY% build_category_calendars.py catalysts_out\catalysts_public.csv site_category_pages
%PY% build_seo_pages.py catalysts_out\catalysts_public.csv seo_pages
%PY% archive_run.py catalysts_out runs

echo(
echo ============================================================
echo  [3/5] Merge the fresh mine into the calendar data (keeps curated)
echo ============================================================
cd pdufa_site_src
%PY% build_slate_from_crawl.py --csv ..\catalysts_out\catalysts_public.csv --api api\data.js

echo(
echo ============================================================
echo  [4/5] Flip site -> FREE PUBLIC 2026 FDA PDUFA CALENDAR
echo ============================================================
%PY% apply_calendar_site_state.py

echo(
echo ============================================================
echo  [5/5] Deploy to pdufa.bio (Vercel production)
echo ============================================================
if "%VERCEL_TOKEN%"=="" (
  echo   VERCEL_TOKEN not found in "Odin Perfection\.env_master".
  echo   Everything is BUILT and STAGED. Add one line:  VERCEL_TOKEN=your_token_here
  echo   ^(https://vercel.com/account/tokens^) then re-run this file, or run deploy_site.bat.
) else (
  where vercel >nul 2>&1 || ( echo Installing Vercel CLI one-time ... & npm i -g vercel )
  vercel deploy --prod --yes --token %VERCEL_TOKEN%
  echo   If you see a *.vercel.app production URL above, it published. Hard-refresh pdufa.bio in ~30s.
)
cd ..

echo(
echo ============================================================
echo  DONE. pdufa.bio rebuilt from the fresh mine.
echo   catalysts_out\catalysts_public.csv  - the mined feed (provenance-tagged)
echo   catalysts_out\qa_diff.json          - PDUFA recall vs BPC ; coverage_gaps.csv
echo ============================================================
pause
