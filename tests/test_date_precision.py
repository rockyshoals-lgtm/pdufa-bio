# -*- coding: utf-8 -*-
"""test_date_precision.py -- a date is printed at the precision a source gave it, in both directions.

Design red team 2026-11-18 (change 1). /screener printed the storage key of every row as a day: 202 estimated and 236
guided readouts showed as 2026-12-15 or 2026-12-31 when the source said "December" or "Q4". The home page counted down
to 2026-11-30 for REGN cemdisiran, whose goal is only known as November 2026. Decided PDUFAs sat under their goal date
with a check mark, so Summit's complete response letter wore a tick and September approvals read as December
catalysts. This fails if any of that returns, and equally if a fix over-corrects:

  1. screener DATA: a row stored as month / quarter / year carries its window label (site_windows.window_label, with
     " (est.)" for Estimated); a day-precision row carries no label and keeps its exact day;
  2. screener DATA: a decided PDUFA with a decision date sits on that date with its outcome, and nothing else
     carries an outcome; the page's JS marks only a recorded outcome, a check for approvals and a cross for CRLs;
  3. the server-rendered screener table prints no "YYYY-MM-DD (est.)" and prints day rows as their day;
  4. home: no countdown card names a day for a goal the dataset holds only as a window, and every day goal keeps
     its countdown.

    python tests/test_date_precision.py
"""
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from site_windows import is_closed, is_day, window_label, window_span  # noqa: E402
import datetime as dt  # noqa: E402
try:
    from site_dates import eastern_today
except Exception:  # noqa: BLE001
    eastern_today = dt.date.today
FLOOR = (eastern_today() - dt.timedelta(days=150)).isoformat()   # sync_screener_data.py's window

SITE = os.path.join(HERE, "pdufa_site_src")
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")
SCREENER = os.path.join(SITE, "screener", "index.html")
HOME = os.path.join(SITE, "index.html")


def load_rows():
    src = open(DATASET, encoding="utf-8", errors="replace").read()
    return json.loads(src[src.index("["):src.rindex("]") + 1])


def main():
    rows = load_rows()
    doc = open(SCREENER, encoding="utf-8", errors="replace").read()
    bad = []

    m = re.search(r"const DATA=(\[.*?\]);", doc, re.S)
    data = json.loads(m.group(1)) if m else []
    if not data:
        bad.append("/screener: const DATA missing or empty")
    by_key = {}
    for r in rows:
        by_key.setdefault((r.get("t") or "", r.get("url") or f"/ticker/{r.get('t')}", str(r.get("name") or "")[:50],
                           r.get("type")), []).append(r)
    labelled = exact = placed = 0
    for e in data:
        cands = by_key.get((e["t"], e["url"], e["name"], e["type"]), [])
        if not cands:
            continue
        decided = [r for r in cands if r.get("type") == "PDUFA" and r.get("st") == "Decided"
                   and len(str(r.get("dcd") or "")) == 10 and r["dcd"] == e["d"]]
        if decided:
            r = decided[0]
            placed += 1
            if e.get("w"):
                bad.append(f"/screener {e['t']} {e['d']}: decided row printed as window {e['w']!r}")
            if r.get("oc") and e.get("oc") != r.get("oc"):
                bad.append(f"/screener {e['t']} {e['d']}: outcome {e.get('oc')!r}, dataset says {r.get('oc')!r}")
            continue
        r = next((r for r in cands if str(r.get("d")) == e["d"]), None)
        if r is None:
            if any(x.get("type") == "PDUFA" and x.get("st") == "Decided" and len(str(x.get("dcd") or "")) == 10
                   for x in cands):
                bad.append(f"/screener {e['t']} {e['d']}: decided PDUFA not placed on its decision date")
            continue
        if e.get("oc"):
            bad.append(f"/screener {e['t']} {e['d']}: carries an outcome {e['oc']!r} the row has not got")
        if is_day(r):
            exact += 1
            if e.get("w"):
                bad.append(f"/screener {e['t']} {e['d']}: exact day coarsened to {e['w']!r}")
        else:
            labelled += 1
            want = window_label(r) + (" (est.)" if r.get("st") == "Estimated" else "")
            if e.get("w") != want:
                bad.append(f"/screener {e['t']} {e['d']} ({r.get('dp')}): prints {e.get('w') or e['d']!r}, "
                           f"want {want!r}")
    # every decided PDUFA with a decision date in the screener's range is on that date
    for r in rows:
        if r.get("type") == "PDUFA" and r.get("st") == "Decided" and len(str(r.get("dcd") or "")) == 10:
            if r["dcd"] >= FLOOR:
                if not any(e["t"] == r.get("t") and e["d"] == r["dcd"] and e["type"] == "PDUFA" for e in data):
                    bad.append(f"/screener: decided {r.get('t')} {r.get('id')} missing from its decision date "
                               f"{r['dcd']}")
                if any(e["t"] == r.get("t") and e["d"] == str(r.get("d")) and e["d"] != r["dcd"]
                       and e["url"] == (r.get("url") or "") and e["type"] == "PDUFA" for e in data):
                    bad.append(f"/screener: decided {r.get('t')} {r.get('id')} still listed on goal date {r.get('d')}")

    js = doc[doc.find("function render(){"):]
    if "e.st==='Decided'?' · ✓'" in doc:
        bad.append("/screener JS: any Decided row still gets a check mark, CRLs included")
    if "esc(e.w||e.d)" not in js:
        bad.append("/screener JS: rows are not printed from their window label")

    ssr = re.search(r"<!--ssr-rows-->(.*?)<!--/ssr-rows-->", doc, re.S)
    ssr = ssr.group(1) if ssr else ""
    for d in re.findall(r"<td>(\d{4}-\d{2}-\d{2}) \(est\.\)</td>", ssr):
        bad.append(f"/screener table: {d} (est.) prints a made-up day")
    for tk, cell in re.findall(r'<tr><td><a href="/ticker/([^"]+)">[^<]*</a></td><td>([^<]*)</td>', ssr):
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", cell):
            if not any(r.get("t") == tk and str(r.get("d")) == cell and is_day(r) for r in rows):
                bad.append(f"/screener table: {tk} printed as day {cell} with no day-precision row behind it")

    home = open(HOME, encoding="utf-8", errors="replace").read()
    open_pdufa = [r for r in rows if r.get("type") == "PDUFA" and not is_closed(r)]
    cards = 0
    for card in re.findall(r'<a class="row" href="/pdufa/[^"]+">.*?</a>', home, re.S):
        tk = re.search(r'<span class="tk">([A-Z.]+)(?=[\s<])', card)
        if not tk:
            continue
        tk = tk.group(1)
        dd = re.search(r"· PDUFA (\d{4}-\d{2}-\d{2})", card)
        cd = re.search(r'<span class="cd"><b>([^<]*)</b>', card)
        if dd:
            cards += 1
            date = dd.group(1)
            if any(is_day(r) and r.get("t") == tk and str(r.get("d")) == date for r in open_pdufa):
                if cd and not re.fullmatch(r"\d+", cd.group(1)):
                    bad.append(f"home {tk} {date}: a stated day lost its countdown")
                continue
            for r in open_pdufa:
                if r.get("t") == tk and not is_day(r):
                    s, e = window_span(r)
                    if s and s <= date <= e:
                        bad.append(f"home {tk}: counts down to {date}, but the goal is only {window_label(r)}")
        wm = re.search(r"· PDUFA window ([^<]+)</span>", card)
        if wm and cd and re.fullmatch(r"\d+", cd.group(1)):
            bad.append(f"home {tk}: window card {wm.group(1)} still shows a countdown")

    print(f"screener: {labelled} window row(s) labelled, {exact} exact day(s) kept, {placed} decision(s) on their "
          f"action date; home: {cards} dated card(s) checked")
    if bad:
        for b in bad[:40]:
            print("  FAIL " + b)
        if len(bad) > 40:
            print(f"  ... and {len(bad) - 40} more")
        print("  fix: python sync_screener_data.py && python build_screener_rows.py && python build_home_board.py")
        sys.exit(1)
    print("  PASS: dates print at the precision their source gave, in both directions")


if __name__ == "__main__":
    main()
