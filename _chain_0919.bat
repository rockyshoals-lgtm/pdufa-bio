@echo off
cd /d C:\Users\dcmoo\Documents\Python\9realms
set PYTHONIOENCODING=utf-8
set PY=C:\Python314\python.exe
del /q _chain_0919.log 2>nul
rem 2026-09-23: two CI steps the local chain lacked. The slate sweep (else test_slate_no_decided
rem fails on a freshly published decision) and build_stock_runup (else 24 ticker hubs that CI had
rem lifted out of noindex regress to noindex and drop from the sitemap on a local commit).
echo == build_slate_from_crawl.py --sweep-only >> _chain_0919.log
%PY% -X utf8 pdufa_site_src/build_slate_from_crawl.py --sweep-only >> _chain_0919.log 2>&1
for %%s in (capture_crl_corpus.py link_crl_letters.py build_crl_hub.py sync_runup_study_size.py build_runup_by_year.py build_home_board.py sync_decisions_listing.py mark_calendar_decided.py mark_calendar_awaiting.py build_early_decisions.py sync_learn_timing.py inject_calendar_explainer.py build_monthly_decisions.py sync_decisions_listing.py sync_api_from_pages.py refresh_provenance_counts.py build_decision_faq.py rewrite_decision_snippets.py fix_unsourced_earliness_prose.py sync_jsonld_name_to_title.py build_drug_pages.py add_drug_schema.py build_ticker_hubs.py enrich_ticker_hubs.py build_stock_runup.py build_condition_pages.py build_today_page.py build_pdufa_event_pages.py refresh_moved_pdufa_pages.py normalize_calendar_windows.py mark_event_pages_decided.py fix_event_page_windows.py mark_goal_date_passed.py fix_calendar_windowed_rows.py canonicalise_duplicate_event_pages.py fix_dead_internal_links.py build_calendar_feed.py sync_calendar_itemlist.py build_hub_lede.py build_hub_faq.py build_breadcrumbs.py add_og_tags.py build_llms_txt.py strip_dashes.py fix_meta_lengths.py rebuild_nav.py apply_legal_footer.py build_sitemap.py build_freshness_stamp.py build_date_modified.py) do (
  echo == %%s >> _chain_0919.log
  %PY% -X utf8 %%s >> _chain_0919.log 2>&1
  if errorlevel 1 echo    ^^^ EXIT %%s nonzero >> _chain_0919.log
)
echo CHAIN DONE >> _chain_0919.log
