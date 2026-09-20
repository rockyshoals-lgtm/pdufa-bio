@echo off
cd /d C:\Users\dcmoo\Documents\Python\9realms
set PYTHONIOENCODING=utf-8
del /q _tail.log 2>nul
for %%s in (strip_dashes.py fix_meta_lengths.py sync_jsonld_name_to_title.py build_sitemap.py build_freshness_stamp.py build_date_modified.py) do (
  echo == %%s >> _tail.log
  C:\Python314\python.exe -X utf8 %%s >> _tail.log 2>&1
)
echo TAIL DONE >> _tail.log
