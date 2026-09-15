# -*- coding: utf-8 -*-
"""38 ids embed a date the row no longer holds. Two causes, two treatments.

  A MOVE: the sponsor or the registry moved the date after the row was created (CAPR's Aug 22 ->
  Nov 22 extension; a registry estimate that slid). The id is a primary key consumers may hold;
  re-keying breaks their continuity, and the old date in the key is history, not error -- IF the
  row documents the move in date_history.

  A CORRECTION: the original date was our mistake (a manufactured 15th, a wrong year, CORT's
  09-15). Nothing legitimate was ever keyed on it. Re-key.

Which is which? Check whether each row carries date_history explaining the id's date.
"""
import io
import json
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

src = io.open("pdufa_site_src/api/v1/dataset.mjs", encoding="utf-8",
              errors="replace").read().replace("\x00", "")
rows, _ = json.JSONDecoder().raw_decode(src[src.find("["):])

has_hist = 0
for r in rows:
    rid, d = str(r.get("id") or ""), str(r.get("d") or "")
    m = re.search(r"(\d{4}-\d{2}-\d{2})$", rid)
    if not m or m.group(1) == d or r.get("type") not in ("PDUFA", "Readout"):
        continue
    dd = r.get("_d") or {}
    hist = dd.get("date_history") or r.get("date_history")
    hist_has_id_date = bool(hist) and any(m.group(1) in json.dumps(h) for h in hist)
    if hist:
        has_hist += 1
    print(f"{rid:<32} d={d}  type={r.get('type'):<8} st={str(r.get('st')):<10} "
          f"history={'YES' if hist else '-':<4} covers_id_date={'yes' if hist_has_id_date else 'no'}"
          f"  | {str(r.get('name'))[:30]}")
print(f"\nrows with any date_history: {has_hist}")
print("date_history keys present anywhere:",
      sum(1 for r in rows if (r.get('_d') or {}).get('date_history') or r.get('date_history')))
