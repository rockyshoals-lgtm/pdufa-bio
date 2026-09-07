"""Mine the ACTUAL presentation language from filings our phrase list missed.

7 tickers (GRI ABBV OCUL LLY NKTR SANA IMMP) have 8-K/6-Ks announcing a congress
presentation that our FTS phrase walk never surfaced. Rather than guess new phrases,
pull those companies' recent filings, find the ones that mention the target congress,
and print the sentence around the presentation verb. The phrases write themselves.
"""
import datetime as dt
import json, os, re, sys, time, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from readout_scan import ua, _get, ARCHIVES

TARGETS = {"GRI": "respiratory", "ABBV": "lung cancer", "OCUL": "retina",
           "LLY": "dermatolog", "NKTR": "dermatolog", "SANA": "diabet",
           "IMMP": "medical oncology"}
agent = ua()
TAG = re.compile(r"<[^>]+>")
WS = re.compile(r"\s+")
PRES = re.compile(r"\b(present\w*|poster|oral|abstract|late[- ]break\w*|symposi\w*)\b", re.I)


_CIK = {}


def cik_map():
    """_edgar_ticker_map.json is ticker->NAME, not ticker->CIK. Pull SEC's official
    company_tickers.json once instead of guessing."""
    if _CIK:
        return _CIK
    raw = _get("https://www.sec.gov/files/company_tickers.json", agent)
    try:
        for v in (json.loads(raw) if raw else {}).values():
            _CIK[str(v["ticker"]).upper()] = int(v["cik_str"])
    except Exception:
        pass
    return _CIK


def submissions(tk):
    cik = cik_map().get(tk.upper())
    if not cik:
        return None
    raw = _get(f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json", agent)
    try:
        return json.loads(raw) if raw else None
    except Exception:
        return None


for tk, needle in TARGETS.items():
    sub = submissions(tk)
    if not sub:
        print(f"\n### {tk}: no CIK/submissions")
        continue
    rec = (sub.get("filings") or {}).get("recent") or {}
    forms, dates = rec.get("form") or [], rec.get("filingDate") or []
    cutoff = (dt.date.today() - dt.timedelta(days=75)).isoformat()
    hits = 0
    print(f"\n### {tk}  (looking for '{needle}')")
    for j, fm in enumerate(forms):
        if fm not in ("8-K", "6-K") or dates[j] < cutoff or hits >= 2:
            continue
        doc = (rec.get("primaryDocument") or [None] * len(forms))[j]
        accn = (rec.get("accessionNumber") or [""] * len(forms))[j]
        if not doc:
            continue
        cik = str(int(sub["cik"]))
        raw = _get(f"{ARCHIVES}/{cik}/{accn.replace('-', '')}/{doc}", agent)
        time.sleep(0.15)
        if not raw:
            continue
        txt = WS.sub(" ", TAG.sub(" ", raw[:3_000_000].decode("utf-8", "replace")))
        if needle.lower() not in txt.lower():
            continue
        hits += 1
        low = txt.lower()
        i = low.find(needle.lower())
        for m in PRES.finditer(txt[max(0, i - 1200):i + 1200]):
            s = max(0, i - 1200) + m.start()
            snip = txt[max(0, s - 130):s + 150]
            print(f"   [{dates[j]} {fm}] ...{snip.strip()[:250]}...")
            break
print("\nDone — read the snippets and add the missing verb/noun forms to PRESENT_PHRASES.")
