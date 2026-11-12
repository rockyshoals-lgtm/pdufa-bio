@echo off
cd /d C:\Users\dcmoo\Documents\Python\9realms
set PYTHONIOENCODING=utf-8
set PY=C:\Python314\python.exe
del /q _chain_1111b.log 2>nul
for %%s in (sync_decisions_listing.py sync_fda_action_dates.py sync_api_from_pages.py refresh_provenance_counts.py build_decision_faq.py build_hub_faq.py rewrite_decision_snippets.py inject_fda_action_record.py inject_verified_against.py build_decision_lede.py fix_decision_h1_action_date.py build_fda_letters_hub.py build_drug_pages.py add_drug_schema.py build_ticker_hubs.py build_today_page.py build_weekly_decisions.py build_monthly_decisions.py mark_event_pages_decided.py fix_decided_event_meta.py fix_event_page_windows.py fix_dead_internal_links.py fix_not_announced_pages.py build_decision_subhubs.py build_crl_months.py build_hub_lede.py sync_home_event_schema.py build_breadcrumbs.py add_og_tags.py build_llms_txt.py sync_jsonld_name_to_title.py strip_dashes.py fix_meta_lengths.py rebuild_nav.py inject_mobile_nav.py apply_legal_footer.py build_dropbox_index.py inject_site_links.py build_google_request_list.py "build_sitemap.py --no-state" build_freshness_stamp.py build_date_modified.py inject_decision_article_schema.py "quarantine_leads.py apply") do (
  echo == %%s >> _chain_1111b.log
  %PY% -X utf8 %%~s >> _chain_1111b.log 2>&1
  if errorlevel 1 echo    ^^^ EXIT %%s nonzero >> _chain_1111b.log
)
%PY% -X utf8 run_ci_guards.py --report _blocked_local.md > _guards_1111b.log 2>&1
echo CHAIN DONE >> _chain_1111b.log
