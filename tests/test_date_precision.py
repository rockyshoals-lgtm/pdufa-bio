# -*- coding: utf-8 -*-
"""test_date_precision.py -- a date is printed at the precision a source gave it, in both directions.

Design red team 2026-11-18 (change 1). /screener printed the storage key of every row as a day: 202 estimated and 236
guided readouts showed as 2026-12-15 or 2026-12-31 when the source said "December" or "Q4". The home page counted down
to 2026-11-30 for REGN cemdisiran, whose goal is only known as November 2026. Decided PDUFAs sat under their goal date
with a check mark, so Summit's complete response letter wore a tick and September approvals read as December
catalysts. This fails if any of that returns, and equally if a fix over-corrects:

  1. screener DATA: a row stored as month / quarter / year carries its window label (site_windows.window_label, with
     " (est.)" for Estimated); a day-precision row carries no label and keeps its exact day;
  2. screener DATA: a decided PDUFA sits on the FDA's action date (_d.fda_action_date) with its outcome, never on
     the announcement / URL date (dcd) when the FDA date is known; with no FDA date it sits on dcd marked "announced".
     Nothing else carries an outcome; the page's JS marks a check for approvals and a cross for CRLs;
  3. the server-rendered screener table prints no "YYYY-MM-DD (est.)" and prints day rows as their day;
  4. home: no countdown card names a day for a goal the dataset holds only as a window, and every day goal keeps
     its countdown. Cards are matched to dataset rows by drug identity (shared name tokens), whatever the row's
     status, so a window cannot swallow another drug's day and a decided-but-unarchived goal keeps its window;
  5. order and filters follow the window: DATA is sorted by window end (a day row's own day), To keeps a window
     that starts by then.

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


def decision_day(r):
    """(day, announced) for a decided PDUFA, computed here and not imported, so a builder bug cannot pass its own
    test: the FDA's action date (_d.fda_action_date) when on record, else the announcement / URL date (dcd)."""
    if r.get("type") != "PDUFA" or r.get("st") != "Decided":
        return None
    fda = str((r.get("_d") or {}).get("fda_action_date") or "") if isinstance(r.get("_d"), dict) else ""
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", fda):
        return fda, False
    dcd = str(r.get("dcd") or "")
    return (dcd, True) if re.fullmatch(r"\d{4}-\d{2}-\d{2}", dcd) else None


def load_rows():
    src = open(DATASET, encoding="utf-8", errors="replace").read()
    return json.loads(src[src.index("["):src.rindex("]") + 1])


def main():
    rows = load_rows()
    doc = open(SCREENER, encoding="utf-8", errors="replace").read()
    bad = []

    m = re.search(r"const DATA=(\[.*?\]);\s*\nconst q=", doc, re.S)
    data = json.loads(m.group(1)) if m else []
    if not data:
        bad.append("/screener: const DATA missing or empty")
    by_key = {}
    for r in rows:
        by_key.setdefault((r.get("t") or "", r.get("url") or f"/ticker/{r.get('t')}", str(r.get("name") or "")[:50],
                           r.get("type")), []).append(r)

    def not_announced(r):
        return bool(isinstance(r.get("_d"), dict) and str(r["_d"].get("goal_date") or "").lower() == "not announced")

    labelled = exact = placed = 0
    for e in data:
        cands = by_key.get((e["t"], e["url"], e["name"], e["type"]), [])
        if not cands:
            continue
        decided = [r for r in cands if decision_day(r) and decision_day(r)[0] == e["d"]]
        if decided:
            r = decided[0]
            placed += 1
            if e.get("w"):
                bad.append(f"/screener {e['t']} {e['d']}: decided row printed as window {e['w']!r}")
            if (e.get("oc") or "") != (r.get("oc") or ""):
                bad.append(f"/screener {e['t']} {e['d']}: outcome {e.get('oc')!r}, dataset says {r.get('oc')!r}")
            if bool(e.get("a")) != decision_day(r)[1]:
                bad.append(f"/screener {e['t']} {e['d']}: 'announced' mark is {bool(e.get('a'))}, but the dataset "
                           f"{'has no' if decision_day(r)[1] else 'has an'} FDA action date for it")
            continue
        r = next((r for r in cands if str(r.get("d")) == e["d"]), None)
        if r is None:
            if any(decision_day(x) for x in cands):
                bad.append(f"/screener {e['t']} {e['d']}: decided PDUFA not placed on its decision date")
            continue
        if (e.get("oc") or "") != ((r.get("oc") or "") if r.get("type") == "PDUFA" and r.get("st") == "Decided"
                                   else ""):
            bad.append(f"/screener {e['t']} {e['d']}: outcome {e.get('oc')!r}, dataset row says "
                       f"{r.get('oc') if r.get('st') == 'Decided' else None!r}")
        if e.get("a"):
            bad.append(f"/screener {e['t']} {e['d']}: 'announced' mark on a row that is not a decision")
        est = " (est.)" if r.get("st") == "Estimated" else ""
        if not_announced(r):
            if e.get("w") != "Not announced" + est:
                bad.append(f"/screener {e['t']}: goal date not announced, but prints {e.get('w') or e['d']!r}")
        elif is_day(r):
            exact += 1
            if (e.get("w") or e["d"]) != e["d"] + est:
                bad.append(f"/screener {e['t']} {e['d']}: exact day printed as {e.get('w')!r}")
        else:
            labelled += 1
            want = window_label(r) + est
            if e.get("w") != want:
                bad.append(f"/screener {e['t']} {e['d']} ({r.get('dp')}): prints {e.get('w') or e['d']!r}, "
                           f"want {want!r}")
            s0, e0 = window_span(r)
            if (e.get("s") or e["d"]) != s0 or (e.get("e") or e["d"]) != e0:
                bad.append(f"/screener {e['t']} {e.get('w')}: filters on {e.get('s') or e['d']}..{e.get('e') or e['d']}, "
                           f"window is {s0}..{e0}")
    # every decided PDUFA in the screener's range is on its FDA action date: not its goal date, and not the
    # announcement / URL date (dcd) when the FDA date is known
    for r in rows:
        dd = decision_day(r)
        if dd and dd[0] >= FLOOR:
            day = dd[0]
            nm = str(r.get("name") or "")[:50]
            url = r.get("url") or f"/ticker/{r.get('t')}"
            mine = [e for e in data if e["t"] == r.get("t") and e["type"] == "PDUFA" and e["name"] == nm
                    and e["url"] == url]
            if not any(e["d"] == day for e in mine):
                bad.append(f"/screener: decided {r.get('t')} {r.get('id')} missing from its "
                           f"{'announcement' if dd[1] else 'FDA action'} date {day}")
            for wrong, what in ((str(r.get("d") or ""), "goal"), (str(r.get("dcd") or ""), "announcement")):
                if wrong and wrong != day and any(e["d"] == wrong and e.get("oc") for e in mine):
                    bad.append(f"/screener: decided {r.get('t')} {r.get('id')} listed on its {what} date {wrong}, "
                               f"not the FDA action date {day}")
    ends = [e.get("e") or e["d"] for e in data]
    if ends != sorted(ends):
        k = next(i for i in range(1, len(ends)) if ends[i] < ends[i - 1])
        bad.append(f"/screener: DATA not in window-end order ({data[k - 1]['t']} {ends[k - 1]} before "
                   f"{data[k]['t']} {ends[k]})")

    js = doc[doc.find("function mark(e){"):]
    if "e.st==='Decided'?' · ✓'" in doc:
        bad.append("/screener JS: any Decided row still gets a check mark, CRLs included")
    if "esc(e.w||e.d)" not in js:
        bad.append("/screener JS: rows are not printed from their window label")
    if "(e.s||e.d)<=t" not in js or "(e.e||e.d)>=f" not in js:
        bad.append("/screener JS: From/To do not filter on the whole window")
    if "/^approved/i" not in js:
        bad.append("/screener JS: the approval check mark is not limited to 'Approved' outcomes")

    ssr = re.search(r"<!--ssr-rows-->(.*?)<!--/ssr-rows-->", doc, re.S)
    ssr = ssr.group(1) if ssr else ""
    for tk, cell in re.findall(r'<tr><td><a href="/ticker/([^"]+)">[^<]*</a></td><td>([^<]*)</td>', ssr):
        dm = re.fullmatch(r"(\d{4}-\d{2}-\d{2})( \(est\.\))?", cell)
        if dm:
            day, est = dm.group(1), bool(dm.group(2))
            if not any(r.get("t") == tk and str(r.get("d")) == day and is_day(r) and not not_announced(r)
                       and (r.get("st") == "Estimated") == est for r in rows):
                bad.append(f"/screener table: {tk} printed as day {cell!r} with no matching day-precision row behind it")

    # home: every card on the board, matched to its goal by drug identity, whatever the goal's status
    def tokens(name):
        return {w for w in re.findall(r"[a-z0-9]{4,}", str(name or "").lower())}

    home = open(HOME, encoding="utf-8", errors="replace").read()
    pdufa = [r for r in rows if r.get("type") == "PDUFA" and r.get("st") != "Withdrawn"]
    cards = 0
    for card in re.findall(r'<a class="row" href="[^"]*">.*?</a>', home, re.S):
        tk = re.search(r'<span class="tk">([A-Z.]+)(?=[\s<])', card)
        dg = re.search(r'<span class="dg">(.*?) · PDUFA (?:(\d{4}-\d{2}-\d{2})|window ([^<]+)|date not announced)</span>',
                       card, re.S)
        if not tk or not dg:
            continue
        tk, gtok = tk.group(1), tokens(re.sub(r"&[a-z]+;", " ", dg.group(1)))
        cards += 1
        cd = re.search(r'<span class="cd"><b>([^<]*)</b>', card)
        same = [r for r in pdufa if r.get("t") == tk and gtok & tokens(r.get("name"))]
        if dg.group(2):
            date = dg.group(2)
            if any(is_day(r) and str(r.get("d")) == date for r in same):
                if cd and not re.fullmatch(r"\d+", cd.group(1)):
                    bad.append(f"home {tk} {date}: a stated day lost its countdown")
                continue
            for r in same:
                if not is_day(r):
                    s0, e0 = window_span(r)
                    if s0 and s0 <= date <= e0:
                        bad.append(f"home {tk}: counts down to {date}, but the goal is only {window_label(r)} "
                                   f"({r.get('st')})")
        else:
            if cd and re.fullmatch(r"\d+", cd.group(1)):
                bad.append(f"home {tk}: window card still shows a countdown")
            lab = dg.group(3) or "Not announced"
            if not any(not is_day(r) or not_announced(r) for r in same if window_label(r) == lab):
                bad.append(f"home {tk}: card shows {lab!r}, but no {lab!r} goal of this drug is in the dataset")

    print(f"screener: {labelled} window row(s) labelled, {exact} exact day(s) kept, {placed} decision(s) on their "
          f"action date; home: {cards} card(s) checked")
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
