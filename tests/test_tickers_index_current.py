# -*- coding: utf-8 -*-
"""CI guard: the /tickers A-Z index is current.

2026-11-25 (red team, David: "Continue building moat and red team everything"). /tickers was built by hand in
August and the daily rebuild never ran its builder, so it listed 208 of 367 ticker hubs and showed 26 PDUFA
goal dates that had already passed as each company's next catalyst. This fails if:
  * the workflow does not run build_tickers_hub.py --refresh
  * a ticker hub on disk is missing from the index, or the index links a hub that does not exist
  * any gold "next catalyst" date on the page is earlier than today (Eastern), or a day-precise date is shown for a
    row the dataset holds only to a month, quarter or year
  * the page's company count disagrees with the number of hubs

    python tests/test_tickers_index_current.py      (PLANT=1 plants a passed date; the guard must fail)
"""
import datetime as dt
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
PAGE = os.path.join(SITE, "tickers", "index.html")
TICKERS = os.path.join(SITE, "ticker")
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")
WORKFLOW = os.path.join(HERE, ".github", "workflows", "pdufa-rebuild.yml")


def today_et():
    # The market and the site run on Eastern; CI runs in UTC (RULE 1).
    try:
        from zoneinfo import ZoneInfo
        return dt.datetime.now(ZoneInfo("America/New_York")).date()
    except Exception:
        return (dt.datetime.utcnow() - dt.timedelta(hours=5)).date()


def main():
    if not os.path.exists(PAGE):
        print("FAIL test_tickers_index_current: /tickers is missing; fix: python build_tickers_hub.py")
        return 1
    fails = []
    doc = io.open(PAGE, encoding="utf-8").read()
    if os.environ.get("PLANT") == "1":
        doc = doc.replace('<b style="color:var(--gold)">', '<b style="color:var(--gold)">PDUFA 2025-01-02</b><b>', 1)
    wf = io.open(WORKFLOW, encoding="utf-8").read() if os.path.exists(WORKFLOW) else ""
    if "python build_tickers_hub.py --refresh" not in wf:
        fails.append("the workflow does not run build_tickers_hub.py --refresh, so /tickers freezes")

    hubs = {d for d in os.listdir(TICKERS) if os.path.exists(os.path.join(TICKERS, d, "index.html"))}
    listed = set(re.findall(r'<a class="trow" href="/ticker/([^"]+)"', doc))
    if hubs - listed:
        fails.append(f"{len(hubs - listed)} ticker hub(s) not on /tickers, e.g. {sorted(hubs - listed)[:5]}")
    if listed - hubs:
        fails.append(f"/tickers links {len(listed - hubs)} hub(s) that do not exist, e.g. {sorted(listed - hubs)[:5]}")
    m = re.search(r'Companies tracked</div><div class="big">(\d+)<', doc)
    if not m or int(m.group(1)) != len(hubs):
        fails.append(f"company count {m.group(1) if m else None} on the page, {len(hubs)} hubs on disk")

    # the dataset's precision for each ticker's rows
    coarse = set()
    if os.path.exists(DATASET):
        src = io.open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
        arr, _ = json.JSONDecoder().raw_decode(src[src.find("["):])
        coarse = {(r.get("t"), str(r.get("d") or "")[:10]) for r in arr if r.get("dp") not in (None, "day")}
        day_rows = {(r.get("t"), str(r.get("d") or "")[:10]) for r in arr if r.get("dp") in (None, "day")}
        coarse -= day_rows
    today = today_et().isoformat()
    for tk, body in re.findall(r'<a class="trow" href="/ticker/([^"]+)">(.*?)</a>', doc, re.S):
        for when in re.findall(r'<b style="color:var\(--gold\)">[A-Za-z]+ ([^<]+)</b>', body):
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", when):
                if when < today:
                    fails.append(f"{tk}: next catalyst {when} has passed (today {today} ET)")
                if (tk, when) in coarse:
                    fails.append(f"{tk}: {when} shown to the day, but the dataset holds it only to a window")
            elif re.fullmatch(r"\d{4}-\d{2}", when):
                if when < today[:7]:
                    fails.append(f"{tk}: next catalyst {when} has passed")
            elif re.fullmatch(r"Q([1-4]) (\d{4})", when):
                q, y = re.fullmatch(r"Q([1-4]) (\d{4})", when).groups()
                if (int(y), int(q)) < (int(today[:4]), (int(today[5:7]) - 1) // 3 + 1):
                    fails.append(f"{tk}: next catalyst {when} has passed")
            elif re.fullmatch(r"\d{4}", when):
                if when < today[:4]:
                    fails.append(f"{tk}: next catalyst {when} has passed")
            else:
                fails.append(f"{tk}: next catalyst date {when!r} is in no known form")

    if fails:
        print(f"FAIL test_tickers_index_current: {len(fails)} problem(s); fix: python build_tickers_hub.py --refresh")
        for f in fails[:30]:
            print("   " + f)
        return 1
    print(f"  PASS /tickers: all {len(hubs)} ticker hubs listed, no passed date shown as a next catalyst")
    return 0


if __name__ == "__main__":
    sys.exit(main())
