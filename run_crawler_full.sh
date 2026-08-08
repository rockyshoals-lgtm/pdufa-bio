#!/usr/bin/env bash
# pdufa.bio — full-universe catalyst crawl (primary sources only -> original content)
# Outputs ./catalysts_out/catalysts_public.csv  (redistribute==True, provenance-tagged)
set -e
cd "$(dirname "$0")"

# 1) deps (one time)
python3 -m pip install -q requests pandas python-dateutil openpyxl

# 2) API keys (edit these — FMP is the important one; ORATS/UW/openFDA are optional enrichment)
export FMP_API_KEY="g68I3Or52j9BKJRVuVMidJ3SG7d6ka7l"
export ORATS_API_KEY="cc1aa61c-ebfa-42e9-8fc0-6bc8f23aaa3d"        # optional (--options)
export UW_API_KEY="70fc151e-1d58-44e3-8825-21d90e9dfc11"  # optional (--options)
# export OPENFDA_API_KEY="j3eLDwnktH7CPacXZe0HrBaUdMbCBcudUt3iDXoc"   # optional (outcome confirmation; works without a key, just rate-limited)

# 3) run it (SEC requires a real contact in the UA string)
python3 catalyst_crawler.py \
  --tickers pdufa_universe.txt \
  --auto-universe --discover \
  --bpc fda_2026-06-19.xlsx \
  --fmp --options \
  --ua "pdufa.bio catalyst research rockyshoals@gmail.com"

# 4) self-populating post-processing (each step is non-fatal so the others still run)
echo "Post-processing (self-populating pipeline) ..."
echo "  [1/4] GUNGNIR readout scoring ..."
python3 gungnir_score_catalysts.py catalysts_out/catalysts_public.csv catalysts_out/catalysts_scored.csv || echo "  [warn] scoring step failed"
echo "  [2/4] Building /readouts + /devices pages ..."
python3 build_category_calendars.py catalysts_out/catalysts_public.csv site_category_pages || echo "  [warn] page build failed"
echo "  [3/4] Archiving dated snapshot + runs_index.csv ..."
python3 archive_run.py catalysts_out runs || echo "  [warn] archive failed"
echo "  [4/4] Option-chart backlog (ALL catalysts, concurrent ~900/min; cache makes repeat runs cheap) ..."
python3 build_chart_universe.py || echo "  [warn] chart-universe refresh failed"
python3 build_option_charts.py --universe option_chart_universe.csv --workers 12 --max-calls 80000 || echo "  [warn] option-chart pull failed"
echo "  [5/6] Building competitive SEO pages (month archives + condition + brand) ..."
python3 build_seo_pages.py catalysts_out/catalysts_public.csv seo_pages || echo "  [warn] SEO page build failed"
echo "  [6/6] SEO Pass-14 fixups (must run LAST, after pages land in pdufa_site_src/) ..."
# Re-applies: per-event/sitewide ld+json -> single @graph (kills NO_TYPE), titles<=60,
# metas<=155, /coverage Dataset, month ItemList+BreadcrumbList. Idempotent. Run AFTER
# build_pdufa_story_blocks.py + xlink_schema_injector.py so the merged schema survives.
python3 seo_pass14_fixups.py   || echo "  [warn] pass14 fixups failed"
python3 seo_pass14b_generic.py || echo "  [warn] pass14b generic failed"

echo
echo "DONE. Key outputs in ./catalysts_out/ :"
echo "  catalysts_public.csv  <- republishable (provenance-tagged). SEND ME THIS."
echo "  catalysts_scored.csv  <- same + GUNGNIR readout scores/tiers."
echo "  catalysts_primary.csv <- everything we found (incl. low-confidence)."
echo "  qa_diff.json          <- PDUFA recall vs BPC ; coverage_gaps.csv <- misses."
echo "  ../site_category_pages/ <- regenerated /readouts + /devices HTML."
echo "  ../runs/<date>/ + runs/runs_index.csv <- dated history (self-populating)."
