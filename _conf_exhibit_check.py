"""Is the presentation announcement hiding in an EX-99.1 exhibit?

_conf_phrase_mine.py found ZERO congress mentions in these companies' 8-K PRIMARY
documents. But an 8-K's primaryDocument is usually the cover page — the actual press
release is EX-99.1. That is exactly the trap task #141 caught before (exhibit_991 missed
descriptively-named exhibits, proven live on CBRS).

This walks the full filing INDEX for each miss and searches EVERY document in the filing,
not just the primary. If the congress name turns up in an exhibit, the fix is in the
FETCH LAYER (fetch exhibits too), not the phrase list.
"""
import datetime as dt
import json, os, re, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from readout_scan import ua, _get, ARCHIVES

TARGETS = {"GRI": "respiratory", "OCUL": "retina", "LLY": "dermatolog",
           "NKTR": "dermatolog", "SANA": "diabet", "IMMP": "oncology"}
agent = ua()
TAG = re.compile(r"<[^>]+>")
WS = re.compile(r"\s+")
_CIK = {}


def cik_map():
    if _CIK:
        return _CIK
    raw = _get("https://www.sec.gov/files/company_tickers.json", agent)
    try:
        for v in (json.loads(raw) if raw else {}).values():
            _CIK[str(v["ticker"]).upper()] = int(v["cik_str"])
    except Exception:
        pass
    return _CIK


cutoff = (dt.date.today() - dt.timedelta(days=75)).isoformat()
for tk, needle in TARGETS.items():
    cik = cik_map().get(tk.upper())
    if not cik:
        print(f"\n### {tk}: no CIK")
        continue
    raw = _get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json", agent)
    try:
        sub = json.loads(raw) if raw else None
    except Exception:
        sub = None
    if not sub:
        print(f"\n### {tk}: no submissions")
        continue
    rec = (sub.get("filings") or {}).get("recent") or {}
    forms, dates = rec.get("form") or [], rec.get("filingDate") or []
    accns = rec.get("accessionNumber") or []
    print(f"\n### {tk}  needle='{needle}'")
    found = 0
    for j, fm in enumerate(forms):
        if fm not in ("8-K", "6-K") or dates[j] < cutoff or found >= 1:
            continue
        a = accns[j].replace("-", "")
        idx = _get(f"{ARCHIVES}/{cik}/{a}/index.json", agent)
        time.sleep(0.15)
        try:
            items = json.loads(idx)["directory"]["item"]
        except Exception:
            continue
        for it in items:
            nm = it.get("name", "")
            if not nm.lower().endswith((".htm", ".html", ".txt")):
                continue
            body = _get(f"{ARCHIVES}/{cik}/{a}/{nm}", agent)
            time.sleep(0.12)
            if not body:
                continue
            txt = WS.sub(" ", TAG.sub(" ", body[:2_000_000].decode("utf-8", "replace")))
            if needle.lower() in txt.lower():
                i = txt.lower().find(needle.lower())
                print(f"   HIT {dates[j]} {fm}  doc={nm}")
                print(f"       ...{txt[max(0,i-180):i+160].strip()[:320]}...")
                found = 1
                break
    if not found:
        print(f"   no '{needle}' in ANY document of any recent 8-K/6-K "
              f"-> genuinely not filed with the SEC")
