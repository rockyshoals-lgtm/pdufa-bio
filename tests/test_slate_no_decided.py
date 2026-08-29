"""The forward slate in api/data.js must not carry an event the dataset says is decided.

Found 2026-08-29, by David, on the live homepage: the board showed LNTH's MK-6240 as "due
today" sixteen days after the FDA approved it. Eight decided events were on the forward
slate. Chain of causes, each silent: the decided-sweep lives in build_slate_from_crawl.py,
which (a) was not in the CI workflow, (b) required a crawl CSV that stopped existing, and
(c) had its archive parser broken by strip_dashes.py, the site's own house-style pass,
which removed the em dash the parser split on -- so even run by hand it matched nothing.
Three independent failures and no guard, which is why the first sign was a reader.

The check is an identity join, not text matching: any slate (ticker, date) that appears in
dataset.mjs as a Decided PDUFA is a failure. The fix is one command:
    python pdufa_site_src/build_slate_from_crawl.py --sweep-only
"""
import io, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(os.path.dirname(HERE), "pdufa_site_src")


def main():
    d = io.open(os.path.join(SITE, "api", "data.js"), encoding="utf-8",
                errors="replace").read()
    i = d.find("const SLATE=")
    if i < 0:
        print("FAIL: no SLATE literal in api/data.js -- the layout changed")
        return 1
    slate, _ = json.JSONDecoder().raw_decode(d[i + len("const SLATE="):])
    cats = slate.get("catalysts") or []
    if len(cats) < 10:
        print(f"FAIL: only {len(cats)} slate catalysts -- an over-eager sweep can empty "
              f"the board, which is as wrong as a stale one")
        return 1

    src = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8",
                  errors="replace").read().replace("\x00", "")
    rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    decided = {(r.get("t"), r.get("d")) for r in rows
               if r.get("type") == "PDUFA" and str(r.get("st", "")).lower() == "decided"}
    if not decided:
        print("FAIL: no decided PDUFAs parsed from dataset.mjs -- vacuous pass refused")
        return 1

    bad = [c for c in cats if (c.get("ticker"), c.get("date")) in decided]
    for c in bad:
        print(f"  FAIL slate carries {c['ticker']} {c['date']} "
              f"({str(c.get('drug'))[:40]}) -- the dataset records it as DECIDED, and the "
              f"homepage board will show an approved drug as a pending decision")
    if bad:
        print(f"\n{len(bad)} decided event(s) on the forward slate. Run "
              f"build_slate_from_crawl.py --sweep-only; if this recurs, check the step is "
              f"still in the workflow.")
        return 1
    print(f"  PASS: {len(cats)} forward slate rows, none among {len(decided)} decided "
          f"events")
    return 0


if __name__ == "__main__":
    sys.exit(main())
