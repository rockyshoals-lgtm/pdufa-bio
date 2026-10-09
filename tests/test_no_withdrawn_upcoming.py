# -*- coding: utf-8 -*-
"""CI guard: a WITHDRAWN application never renders as upcoming, anywhere (audit 2026-10-08 P0).

Merck and Daiichi Sankyo withdrew the ifinatamab deruxtecan BLA on 2026-09-25. For thirteen days the
homepage, /build-info.json (next_ticker MRK), the event page, the calendar and the API said the FDA
would decide on 2026-10-10, and Bing's answer box repeated it under our name. For every dataset row with
st "Withdrawn", on the RENDERED output, this fails when:

  1. the row lacks a day-precision withdrawn_date or a withdrawn_source_url;
  2. api/_build-info.json names it as the next decision (next_ticker + next_date);
  3. api/data.js SLATE (the homepage forward list) still carries (ticker, goal date);
  4. the homepage "Next FDA decisions" board mentions the drug;
  5. a calendar row for (ticker, goal date) is not marked data-wd (withdrawn);
  6. /fda-this-month lists the drug under "Still ahead";
  7. the event page lacks its withdrawn marker or still carries an Event schema;
  8. ANY published page has a sentence naming the drug together with pending-tense language
     ("upcoming", "nearest", "next catalyst", "under FDA review", "PDUFA date is", "goal date to
     complete") -- the event page included, since its own copy must not say it either.

    python tests/test_no_withdrawn_upcoming.py
"""
import glob
import html
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PENDING = re.compile(r"\bupcoming\b|\bnearest\b|next catalyst|under FDA review|PDUFA date is|"
                     r"goal date to complete|is scheduled|still ahead", re.I)


def text(doc):
    doc = re.sub(r"<script.*?</script>|<style.*?</style>", " ", doc, flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", doc)))


def main():
    src = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8", errors="replace").read()
    rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    wd = [r for r in rows if str(r.get("st") or "").lower() == "withdrawn"]
    fails = []
    if not wd:
        print("OK -- no withdrawn rows in the dataset.")
        return 0
    bi = {}
    try:
        bi = json.load(io.open(os.path.join(SITE, "api", "_build-info.json"), encoding="utf-8"))
    except Exception:
        pass
    djs = io.open(os.path.join(SITE, "api", "data.js"), encoding="utf-8").read()
    k = djs.find("const SLATE=") + len("const SLATE=")
    slate, _ = json.JSONDecoder().raw_decode(djs[k:])
    home = io.open(os.path.join(SITE, "index.html"), encoding="utf-8", errors="replace").read()
    hb = home.find('<div class="list">')
    board = text(home[hb:hb + 20000]) if hb >= 0 else ""
    month = io.open(os.path.join(SITE, "fda-this-month", "index.html"), encoding="utf-8", errors="replace").read()
    mt = text(month)
    ahead = mt[mt.find("Still ahead"):]
    ahead = ahead[:max(ahead.find("Withdrawn before a decision"), 0) or ahead.find("Questions")]
    cal_pages = [os.path.join(SITE, "calendar", "index.html")] + sorted(
        glob.glob(os.path.join(SITE, "calendar", "*", "*", "index.html")))
    # undeployed backup trees (.vercelignore: _pdufa_bak*, *xbak*) are not published pages
    all_pages = [p for p in glob.glob(os.path.join(SITE, "**", "index.html"), recursive=True)
                 if not re.search(r"[\\/]_[^\\/]*bak", p)]
    page_text = {}

    for r in wd:
        x = r.get("_d") or {}
        rid, tk, d = r["id"], str(r.get("t") or "").upper(), str(r.get("d") or "")[:10]
        tok = (re.findall(r"[A-Za-z][A-Za-z-]{4,}", str(r.get("name") or "")) or [tk])[0].lower()
        if not (ISO.match(str(x.get("withdrawn_date") or "")[:10]) and x.get("withdrawn_source_url")):
            fails.append(f"{rid}: Withdrawn without a sourced withdrawn_date / withdrawn_source_url")
        if str(bi.get("next_ticker") or "").upper() == tk and str(bi.get("next_date") or "")[:10] == d:
            fails.append(f"{rid}: /build-info.json names it as the next decision ({tk} {d})")
        if any(c.get("ticker") == tk and str(c.get("date"))[:10] == d for c in slate.get("catalysts", [])):
            fails.append(f"{rid}: api/data.js SLATE still lists {tk} {d} (homepage forward list)")
        if tok in board.lower():
            fails.append(f"{rid}: homepage 'Next FDA decisions' board mentions {tok!r}")
        if tok in ahead.lower():
            fails.append(f"{rid}: /fda-this-month lists {tok!r} under 'Still ahead'")
        row_rx = re.compile(r'<a class="row"([^>]*)>\s*<div class="t">' + re.escape(tk) +
                            r'\s*(?:&middot;|·)\s*' + re.escape(d))
        for p in cal_pages:
            if not os.path.exists(p):
                continue
            for m in row_rx.finditer(io.open(p, encoding="utf-8", errors="replace").read()):
                if 'data-wd="1"' not in m.group(1):
                    fails.append(f"{rid}: calendar row {tk} {d} on /{os.path.relpath(os.path.dirname(p), SITE)} "
                                 f"is not marked withdrawn")
        url = str(r.get("url") or "")
        ep = os.path.join(SITE, url.strip("/").replace("/", os.sep), "index.html")
        if url.startswith("/pdufa/") and os.path.exists(ep):
            doc = io.open(ep, encoding="utf-8", errors="replace").read()
            if f'data-withdrawn="{rid}"' not in doc:
                fails.append(f"{rid}: event page {url} has no withdrawn marker")
            if '"@type":"Event"' in doc.replace(" ", ""):
                fails.append(f"{rid}: event page {url} still carries an Event schema")
        else:
            fails.append(f"{rid}: row url {url!r} is not an existing /pdufa/ event page")
        for p in all_pages:
            if p not in page_text:
                page_text[p] = text(io.open(p, encoding="utf-8", errors="replace").read())
            t = page_text[p]
            if tok not in t.lower():
                continue
            for sent in re.split(r"(?<=[.?!])\s+", t):
                if tok in sent.lower() and PENDING.search(sent) and not re.search(
                        r"\bno (upcoming|longer)\b|\bnot (upcoming|pending)\b|withdr", sent, re.I):
                    fails.append(f"{rid}: /{os.path.relpath(os.path.dirname(p), SITE).replace(os.sep, '/')} "
                                 f"says {sent.strip()[:160]!r}")
                    break
    if fails:
        print(f"FAIL: {len(fails)} withdrawn-application problem(s). A withdrawn application is not a "
              f"pending decision on any surface. DO NOT PUBLISH.")
        for f in fails[:30]:
            print("   " + f)
        return 1
    print(f"OK -- {len(wd)} withdrawn row(s); none renders as upcoming on {len(all_pages)} pages, the "
          f"board, the slate, build-info, the calendar or /fda-this-month.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
