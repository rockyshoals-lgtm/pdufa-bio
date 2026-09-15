# -*- coding: utf-8 -*-
"""One event, one page: the API's `url` for an upcoming PDUFA row is the page /calendar links
for that row. Audit 09-09b item 5 (source_url / page_url split) and 09-15 ORDER 1 (CORT's url
was an off-site registry link) are the same defect: `url` was carrying whatever was to hand --
a filing, a press release, a registry record, the bare ticker page -- while the calendar linked
the per-event page. Found on 2026-09-15: 11 of 49 upcoming rows sent an API consumer somewhere
other than where the calendar sends a reader (MRK x2, VTRS x2, NUVL, ABBV, AZN, BAYRY, NVO,
CORT, CAPR).

Now that `source_url` exists (ORDER 4), the split is clean: `source_url` is the document, `url`
is the page. This script reads the calendar's rows (ticker(s), date or window, href) and, for
every upcoming PDUFA row it can match on ticker + date (day rows) or ticker + drug token (window
rows), sets `url` to the calendar's href when it differs and the page exists. An external `url`
is first preserved in `_d.source_url` if that is empty.

    python sync_api_urls_to_calendar.py [--dry-run]
"""
import argparse
import html as H
import io
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")
CAL = os.path.join(SITE, "calendar", "index.html")
STOP = {"pdufa", "date", "and", "the", "plus", "with", "for", "est", "resubmission", "snda", "nda", "bla"}


def toks(s):
    return {w for w in re.findall(r"[a-z][a-z0-9]{3,}", str(s or "").lower()) if w not in STOP}


def calendar_rows():
    t = io.open(CAL, encoding="utf-8", errors="replace").read()
    out = []
    for m in re.finditer(r'<a class="row"([^>]*)href="([^"]+)"[^>]*>(.*?)</a>', t, re.S):
        href, body = m.group(2), m.group(3)
        if not href.startswith("/pdufa/"):
            continue
        txt = H.unescape(re.sub(r"<[^>]+>", " ", body))
        txt = re.sub(r"\s+", " ", txt).strip()
        head = txt.split("·")[0] if "·" in txt else txt[:30]
        tickers = set(re.findall(r"\b[A-Z]{2,6}\b", head))
        d = re.search(r"(\d{4}-\d{2}-\d{2})", txt)
        out.append({"href": href, "tickers": tickers, "date": d.group(1) if d else None,
                    "toks": toks(txt) | toks(href.replace("/pdufa/", "").replace("-", " "))})
    return out


def match(r, cal):
    tk = str(r.get("t", "")).upper()
    cands = [c for c in cal if tk in c["tickers"]]
    if not cands:
        return None
    if r.get("dp") == "day":
        # a day row matches a calendar row on its DATE, never on ticker alone (BBIO's 2027 encaleret
        # row is not BBIO's 2026 BBP-418 row)
        same = [c for c in cands if c["date"] == r.get("d")]
        if len(same) == 1:
            return same[0]
        if not same:
            return None
        cands = same
    rt = toks(r.get("name")) | toks(str(r.get("url", "")).replace("/pdufa/", "").replace("-", " "))
    rt -= {str(r.get("t", "")).lower()}
    scored = sorted(((len(rt & c["toks"]), c) for c in cands), key=lambda x: -x[0])
    if scored and scored[0][0] >= 1 and (len(scored) == 1 or scored[0][0] > scored[1][0]):
        return scored[0][1]
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    src = io.open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
    i, j = src.index("["), src.rindex("]") + 1
    rows = json.loads(src[i:j])
    cal = calendar_rows()
    cal_html = io.open(CAL, encoding="utf-8", errors="replace").read()
    n = n_cal = unmatched = 0
    for r in rows:
        if r.get("type") != "PDUFA" or r.get("st") != "Upcoming":
            continue
        c = match(r, cal)
        if not c:
            unmatched += 1
            continue
        if not os.path.exists(os.path.join(SITE, c["href"].strip("/"), "index.html")):
            continue
        cur = str(r.get("url") or "")
        if cur == c["href"]:
            continue
        bare = f"/pdufa/{str(r.get('t', '')).upper()}"
        # The per-event page wins over the bare ticker page in BOTH directions. When the dataset
        # already names a per-event page (/pdufa/CORT-relacorilant) and the calendar links the
        # ticker's history page (/pdufa/CORT), the calendar moves, not the dataset.
        if (cur.startswith("/pdufa/") and cur != bare and c["href"] == bare
                and os.path.exists(os.path.join(SITE, cur.strip("/"), "index.html"))):
            before = cal_html
            cal_html = re.sub(rf'(<a class="row"[^>]*href=")({re.escape(bare)})("[^>]*>\s*<div class="t">\s*'
                              rf'{re.escape(str(r.get("t")))}\s*(?:&middot;|·)\s*{re.escape(str(r.get("d")))})',
                              rf"\g<1>{cur}\3", cal_html)
            cal_html = cal_html.replace(f'"url": "https://www.pdufa.bio{bare}", "eventAttendanceMode"',
                                        f'"url": "https://www.pdufa.bio{cur}", "eventAttendanceMode"') \
                if f'"name": "{r.get("t")}: {r.get("name")}"' in cal_html else cal_html
            if cal_html != before:
                print(f"  {r['id']:<30} calendar {bare:<41} -> {cur}")
                n_cal += 1
            continue
        dd = r.setdefault("_d", {})
        if cur.startswith("http") and not dd.get("source_url"):
            dd["source_url"] = cur
        print(f"  {r['id']:<30} {cur[:48]:<48} -> {c['href']}")
        r["url"] = c["href"]
        n += 1
    if not a.dry_run and n:
        io.open(DATASET, "w", encoding="utf-8").write(
            src[:i] + json.dumps(rows, indent=1, ensure_ascii=False) + src[j:])
    if not a.dry_run and n_cal:
        io.open(CAL, "w", encoding="utf-8").write(cal_html)
    print(f"{n} url(s) aligned to the calendar's page; {unmatched} upcoming row(s) have no calendar "
          f"row to align to (2027 rows, co-listed partners)" + ("   (--dry-run)" if a.dry_run else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
