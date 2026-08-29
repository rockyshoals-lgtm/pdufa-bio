"""A /condition page titled "Upcoming" must contain only genuinely upcoming events.

Found 2026-08-29, from the red-team audit's SEO read: /condition/cancer was Google's #2
page by impressions and had never been examined. The whole family had been built once from
a June 23 CSV and never rebuilt -- past-dated events presented as upcoming, ACHV's
cytisinicline PDUFA labelled with custirsen (a discontinued drug from before the 2017
OncoGenex merger, and the wrong therapeutic area entirely), and NUVL's 09-18 row carrying
the wrong drug for an event the FDA had already approved on 07-22. Third instance of the
build-once-never-rebuild class after the ticker hubs (08-26) and the calendar month pages.

Three checks per page:
  1. no event row dated before today (grace for month-precision rows in the current month);
  2. no (ticker, date) pair the dataset records as a decided PDUFA;
  3. the page parses at all -- a family this old can fail by being absent, and a guard that
     skips missing pages passes vacuously.
"""
import datetime as dt, glob, io, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(os.path.dirname(HERE), "pdufa_site_src")
TODAY = dt.date.today().isoformat()
rd = lambda p: io.open(p, encoding="utf-8", errors="replace").read()

ROW = re.compile(r'<(?:div|span) class="t">([A-Z]{1,6})\s*(?:&middot;|·)\s*'
                 r'(\d{4}-\d{2}-\d{2}|[A-Z][a-z]{2} \d{4} \(est\.\))')
MON = {m: i for i, m in enumerate(
    "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split(), 1)}


def decided():
    d = rd(os.path.join(SITE, "api", "v1", "dataset.mjs")).replace("\x00", "")
    rows = json.loads(d[d.index("["):d.rindex("]") + 1])
    out = set()
    for r in rows:
        if r.get("type") == "PDUFA" and str(r.get("st", "")).lower() == "decided":
            for dt_ in filter(None, (r.get("d"), r.get("dcd"))):
                out.add((str(r.get("t") or "").upper(), str(dt_)))
    return out


def main():
    done = decided()
    pages = sorted(glob.glob(os.path.join(SITE, "condition", "*", "index.html")))
    if not pages:
        print("FAIL: no /condition pages found -- the family or the layout moved")
        return 1
    if not done:
        print("FAIL: no decided PDUFAs parsed from dataset.mjs -- check 2 would pass "
              "vacuously")
        return 1
    bad = 0
    for p in pages:
        slug = os.path.basename(os.path.dirname(p))
        doc = rd(p)
        for tk, when in ROW.findall(doc):
            if when.endswith("(est.)"):                       # month precision
                mon, yr = when.split()[0], when.split()[1]
                iso_month = f"{yr}-{MON.get(mon, 0):02d}"
                if iso_month < TODAY[:7]:
                    print(f"  FAIL /condition/{slug}: {tk} {when} is a past month on an "
                          f"'Upcoming' page")
                    bad += 1
                continue
            if when < TODAY:
                print(f"  FAIL /condition/{slug}: {tk} {when} is in the past on an "
                      f"'Upcoming' page")
                bad += 1
            if (tk, when) in done:
                print(f"  FAIL /condition/{slug}: {tk} {when} is a DECIDED event "
                      f"presented as upcoming")
                bad += 1
    if bad:
        print(f"\n{bad} stale row(s). Rebuild with build_condition_pages.py -- and if "
              f"this recurs, check the builder is still in the workflow.")
        return 1
    print(f"  PASS: {len(pages)} condition pages, all rows current, none decided")
    return 0


if __name__ == "__main__":
    sys.exit(main())
