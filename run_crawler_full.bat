@echo off
REM ===== pdufa.bio full-universe catalyst crawler (Windows) =====
REM Double-click this file, or run it from Command Prompt. Outputs to .\catalysts_out\
cd /d "%~dp0"

echo Loading API keys from "Odin Perfection\.env_master" ...
for /f "usebackq eol=# tokens=1,* delims==" %%a in ("Odin Perfection\.env_master") do set "%%a=%%b"

echo Installing Python dependencies (one-time) ...
python -m pip install -q requests pandas python-dateutil openpyxl

echo.
echo Starting FULL-UNIVERSE crawl: screener (~960) + static list + SEC discovery across ALL filers.
echo This takes ~2-4 hours. Leave this window open.
echo ------------------------------------------------------------------
python catalyst_crawler.py --tickers pdufa_universe.txt --auto-universe --discover --bpc fda_2026-07-09.xlsx --fmp --options --ua "pdufa.bio catalyst research rockyshoals@gmail.com"

echo ------------------------------------------------------------------
echo Post-processing (self-populating pipeline) ...
echo  [1/4] Scoring readouts with GUNGNIR v46 ...
python gungnir_score_catalysts.py catalysts_out\catalysts_public.csv catalysts_out\catalysts_scored.csv
echo  [2/4] Building /readouts + /devices calendar pages ...
python build_category_calendars.py catalysts_out\catalysts_public.csv site_category_pages
echo  [3/4] Archiving dated snapshot + updating runs\runs_index.csv ...
python archive_run.py catalysts_out runs
echo  [4/4] Option-chart backlog (ALL catalysts, concurrent ~900/min; cache makes repeat runs cheap) ...
python build_chart_universe.py
python build_option_charts.py --universe option_chart_universe.csv --workers 12 --max-calls 80000
echo  [5/5] Building competitive SEO pages (month archives + condition + brand) ...
python build_seo_pages.py catalysts_out\catalysts_public.csv seo_pages

echo ------------------------------------------------------------------
echo DONE. Outputs in catalysts_out\ :
echo   catalysts_public.csv   - republishable catalysts (provenance-tagged)
echo   catalysts_scored.csv   - same + GUNGNIR readout scores/tiers
echo   qa_diff.json           - PDUFA recall vs BPC ; coverage_gaps.csv - misses
echo   site_category_pages\   - regenerated /readouts + /devices HTML
echo   runs\(date)\           - dated snapshot ; runs\runs_index.csv - run history
echo Send catalysts_out\catalysts_public.csv AND qa_diff.json back to Claude.
echo.
pause

echo   [6/6] SEO Pass-14 fixups (run LAST: ld+json -^> single @graph, titles^<=60, metas^<=155, Dataset, ItemList) ...
python seo_pass14_fixups.py
python seo_pass14b_generic.py
