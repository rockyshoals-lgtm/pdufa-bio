@echo off
cd /d C:\Users\dcmoo\Documents\Python\9realms
set PYTHONIOENCODING=utf-8
set PY=C:\Python314\python.exe
del /q _chain_1110.log 2>nul
for %%s in (build_pdufa_ticker_index.py inject_sponsor_caveat.py inject_event_page_source.py fix_dead_internal_links.py build_calendar_year_hub.py fix_not_announced_pages.py build_decision_subhubs.py build_crl_months.py build_hub_lede.py sync_home_event_schema.py sync_calendar_itemlist.py retitle_calendar_months.py build_breadcrumbs.py add_og_tags.py build_llms_txt.py sync_jsonld_name_to_title.py strip_dashes.py fix_meta_lengths.py rebuild_nav.py inject_mobile_nav.py apply_legal_footer.py build_dropbox_index.py build_fda_approvals_months.py inject_site_links.py build_google_request_list.py "build_sitemap.py --no-state" build_freshness_stamp.py build_date_modified.py "quarantine_leads.py apply") do (
  echo == %%s >> _chain_1110.log
  %PY% -X utf8 %%~s >> _chain_1110.log 2>&1
  if errorlevel 1 echo    ^^^ EXIT %%s nonzero >> _chain_1110.log
)
%PY% -X utf8 run_ci_guards.py --report _blocked_local.md > _guards_1101.log 2>&1
echo CHAIN DONE >> _chain_1110.log
