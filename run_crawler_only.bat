@echo off
REM ============================================================================
REM  pdufa.bio — CRAWL ONLY (mine + compare vs BPC). No site build, no deploy.
REM  Use this to do a fresh mining pass and see head-to-head vs BPC BEFORE publishing.
REM    [1] FULL MINE      catalyst_crawler.py (SEC EDGAR + CT.gov + FDA + openFDA + FMP),
REM                       primary-sourced, ~2-4 hrs. Leave the window open.
REM    [2] QA vs BPC      recall diff + our head-to-head with DATE-CONFLICT audit.
REM  Keys read from  Odin Perfection\.env_master.  Outputs in  catalysts_out\.
REM ============================================================================
setlocal
cd /d "%~dp0"
title pdufa.bio — crawl only (mine + compare vs BPC)

set "PY=python"
where py >nul 2>&1 && set "PY=py -3"

echo Loading API keys from "Odin Perfection\.env_master" ...
for /f "usebackq eol=# tokens=1,* delims==" %%a in ("Odin Perfection\.env_master") do set "%%a=%%b"

echo Installing Python deps (one-time) ...
%PY% -m pip install -q requests pandas python-dateutil openpyxl

echo(
echo ============================================================
echo  [1/2] FULL MINE — primary sources, ~2-4 hrs. Leave this open.
echo        (BPC used ONLY as a private QA yardstick; never republished.)
echo ============================================================
%PY% catalyst_crawler.py --tickers pdufa_universe.txt --auto-universe --discover --bpc fda_2026-07-09.xlsx --fmp --options --ua "pdufa.bio catalyst research rockyshoals@gmail.com"

echo(
echo ============================================================
echo  [2/2] Head-to-head vs BPC + DATE-CONFLICT audit
echo ============================================================
%PY% compare_vs_bpc.py --ours catalysts_out\catalysts_public.csv --bpc fda_2026-07-09.xlsx

echo(
echo ============================================================
echo  DONE. Send these back to Claude to compare + close any gaps:
echo    catalysts_out\catalysts_public.csv   (our mined feed, provenance-tagged)
echo    catalysts_out\qa_diff.json           (recall vs BPC)
echo    catalysts_out\coverage_gaps.csv      (PDUFAs BPC has that we missed)
echo    compare_vs_bpc.csv                   (wins / gaps / DATE CONFLICTS to verify)
echo  DATES ARE THE PRIORITY: every DATE_CONFLICT gets verified vs the primary
echo  source (our rows carry a source_url) before anything goes live.
echo ============================================================
pause
