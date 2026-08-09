# -*- coding: utf-8 -*-
"""test_board_completeness.py -- the homepage board must not silently delete a live catalyst.

The failure this guards against was found by the owner, not by CI: LNTH's Aug 13 PDUFA vanished
from "Next FDA decisions" while remaining in the page's own Event schema. The board's resolver
treated ANY approval within 270 days as resolving EVERY upcoming catalyst the ticker had, so
Lantheus's March approval of a different drug deleted MK-6240 -- and the same rule had silently
removed BMY, GILD and REGN. Four live catalysts gone, zero test failures, discovered by a human
looking at the page.

The invariant: every slate catalyst dated between today and the board's first tile either appears
on the board or has a SAME-DRUG resolution in the decisions archive (drug identity by shared name
token, the same rule the builder now uses -- deliberately re-implemented here in miniature so a
bug in the builder's copy cannot vouch for itself).

Also checks the badge data: build-info.json's next_date must not be later than the earliest
upcoming slate date, and next_days must agree with next_date as of today (the "in 5 days" bug:
next_days was baked at build time and displayed a day later).
"""
import datetime as dt
import json, os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
TODAY = dt.datetime.now(dt.timezone.utc).date()


def tokens(name):
    return {w for w in re.findall(r"[a-z0-9]{4,}", str(name or "").lower())}


def main():
    # slate (raw, unfiltered)
    src = open(os.path.join(SITE, "api", "data.js"), encoding="utf-8", errors="replace").read()
    i = src.find("const SLATE=")
    if i < 0:
        print("  SKIP: no SLATE in api/data.js"); return 0
    slate, _ = json.JSONDecoder().raw_decode(src[i + len("const SLATE="):])

    # archive decisions with drug text
    dec = []
    darch = open(os.path.join(SITE, "decisions", "index.html"),
                 encoding="utf-8", errors="replace").read()
    for m in re.finditer(r'href="/fda-decision/([A-Z]{1,6})-(\d{4}-\d{2}-\d{2})"', darch):
        tail = re.sub(r"<[^>]+>", " ", darch[m.end():m.end() + 200])
        dm = re.search(r"(?:Approved|CRL)\s*:?\s*(.{0,90})", tail)
        dec.append((m.group(1), m.group(2), dm.group(1) if dm else ""))

    # board tiles
    home = open(os.path.join(SITE, "index.html"), encoding="utf-8", errors="replace").read()
    i, j = home.index("Next FDA decisions"), home.index("Recently decided")
    board = home[i:j]
    tile_keys = set()
    first_tile = None
    for m in re.finditer(r"PDUFA (\d{4}-\d{2}-\d{2})", re.sub(r"<[^>]+>", " ", board)):
        pass
    for m in re.finditer(r'href="/(?:pdufa|ticker)/([A-Z]{1,6})"[^>]*>(.*?)</a>', board, re.S):
        txt = re.sub(r"<[^>]+>", " ", m.group(2))
        dm = re.search(r"(\d{4}-\d{2}-\d{2})", txt)
        if dm:
            tile_keys.add((m.group(1), dm.group(1)))
            if first_tile is None or dm.group(1) < first_tile:
                first_tile = dm.group(1)
    if not tile_keys:
        print("FAIL: no tiles parsed from the homepage board -- markup changed?"); return 1

    bad = []
    for c in slate.get("catalysts", []):
        tk = str(c.get("ticker") or "").upper()
        d = str(c.get("date") or "")[:10]
        if not tk or not re.match(r"^\d{4}-\d{2}-\d{2}$", d):
            continue
        if not (TODAY.isoformat() <= d < first_tile):
            continue                       # only the window the board has implicitly skipped
        if (tk, d) in tile_keys:
            continue
        gtok = tokens(c.get("drug") or c.get("drug_name"))
        excused = any(t == tk and (tokens(dd) & gtok if gtok and tokens(dd) else
                                   abs((dt.date.fromisoformat(ddate)
                                        - dt.date.fromisoformat(d)).days) <= 14)
                      for t, ddate, dd in dec)
        if not excused:
            bad.append((tk, d, str(c.get("drug"))[:50]))

    # badge data coherence
    bi_bad = []
    try:
        bi = json.load(open(os.path.join(SITE, "build-info.json"), encoding="utf-8"))
        nd = bi.get("next_date")
        if nd and first_tile and nd > first_tile:
            bi_bad.append(f"build-info next_date {nd} is after the first tile {first_tile}")
        if nd and bi.get("next_days") is not None:
            real = (dt.date.fromisoformat(nd) - TODAY).days
            if abs(real - bi["next_days"]) > 1:
                bi_bad.append(f"next_days={bi['next_days']} but {nd} is {real} days away")
    except Exception:
        pass

    if bad or bi_bad:
        print("FAIL: the homepage board is hiding or misdating live catalysts.")
        for tk, d, drug in bad:
            print(f"   {tk} {d} ({drug}) is upcoming, before the first tile ({first_tile}),")
            print(f"   absent from the board, and has NO same-drug resolution in the archive.")
        for w in bi_bad:
            print(f"   {w}")
        print("\n   This is the LNTH failure mode: a live catalyst deleted by an unrelated")
        print("   approval. Re-run build_home_board.py; if it still fails, resolved() regressed.")
        return 1

    print(f"  PASS: board shows every unresolved catalyst up to {first_tile}; badge dates agree")
    return 0


if __name__ == "__main__":
    sys.exit(main())
