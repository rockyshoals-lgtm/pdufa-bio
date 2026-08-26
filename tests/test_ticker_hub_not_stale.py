"""A ticker hub must not advertise an already-decided event as an upcoming FDA decision.

Found 2026-08-26, after David asked whether the JAZZ/ZYME approval was fully published. It
was, everywhere except here: /ticker/JAZZ and /ticker/ZYME still listed the Ziihera PDUFA
under "Upcoming FDA catalysts", and JAZZ's own decision-history section did not include it.
Nine hubs were in that state, each telling a reader that an approved drug was still awaiting
an FDA decision.

Root cause was not a bug in build_ticker_hubs.py -- it was that the script is not in the CI
workflow at all. Only enrich_ticker_hubs.py runs daily, and enrichment cannot remove a row
that the builder put there. So the hubs were frozen at whatever the last manual build said,
and drifted a little further from the truth with every decision published. This is the same
silent-degradation shape as the earlier incidents: nothing errors, the page simply keeps
saying something that used to be true.

The guard needs the builder in CI to stay green; the two go together.
"""
import glob, io, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(os.path.dirname(HERE), "pdufa_site_src")
rd = lambda p: io.open(p, encoding="utf-8", errors="replace").read()

MON = {m: i for i, m in enumerate(
    "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split(), 1)}
# The hubs render rows as <span class="t">, the calendar as <div class="t">. Accept either:
# a detector locked to one tag reported a clean zero on pages where the fault was visible.
ROW = re.compile(r'<(?:span|div) class="t">([A-Z]{1,6})\s*(?:&middot;|·)\s*'
                 r'([A-Z][a-z]{2})\s+(\d{1,2}),\s*(\d{4})')


def decided_events():
    d = rd(os.path.join(SITE, "api", "v1", "dataset.mjs"))
    rows = json.loads(d[d.index("["):d.rindex("]") + 1])
    out = {}
    for r in rows:
        if r.get("type") != "PDUFA" or str(r.get("st", "")).lower() != "decided":
            continue
        for dt in filter(None, (r.get("d"), r.get("dcd"))):
            out[(r["t"], dt)] = r.get("oc") or "decided"
    return out


def main():
    decided = decided_events()
    hubs = sorted(glob.glob(os.path.join(SITE, "ticker", "*", "index.html")))
    if not hubs:
        print("FAIL: no ticker hubs found -- the glob or the layout changed")
        return 1
    if not decided:
        print("FAIL: no decided PDUFAs parsed from dataset.mjs -- the guard would pass "
              "vacuously, which is not the same as passing")
        return 1

    bad = []
    for p in hubs:
        doc = rd(p)
        i = doc.find("Upcoming FDA catalysts")
        if i < 0:
            continue
        j = doc.find("<h2", i + 10)          # the upcoming block only, not the whole page
        for tk, mon, day, yr in ROW.findall(doc[i:j if j > 0 else len(doc)]):
            iso = f"{yr}-{MON.get(mon, 0):02d}-{int(day):02d}"
            if (tk, iso) in decided:
                bad.append((os.path.basename(os.path.dirname(p)), tk, iso,
                            decided[(tk, iso)]))

    for hub, tk, iso, oc in bad:
        print(f"  FAIL /ticker/{hub}: lists {tk} {iso} under Upcoming FDA catalysts, "
              f"but that event was {oc}")
    if bad:
        print(f"\n{len(bad)} ticker hub(s) advertise a decided event as upcoming. Rebuild "
              f"them (build_ticker_hubs.py, then the enrich chain) -- and if this reappears, "
              f"check that build_ticker_hubs.py is still in the workflow, because the hubs "
              f"go stale silently when it is not.")
        return 1
    print(f"  PASS: {len(hubs)} ticker hubs, none listing any of {len(decided)} decided "
          f"events as upcoming")
    return 0


if __name__ == "__main__":
    sys.exit(main())
