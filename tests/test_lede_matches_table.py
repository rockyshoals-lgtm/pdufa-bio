# -*- coding: utf-8 -*-
"""test_lede_matches_table.py -- the summary sentence must agree with the table under it.

Each hub now opens with one declarative sentence ("This page lists 452 FDA decisions, 334 approvals
and 118 Complete Response Letters"). That sentence exists to be extracted into a Bing snippet or an
AI answer, which means it travels away from the page and gets read by people who never see the
table. A number that drifts is therefore not a cosmetic bug: it is us publishing a wrong fact under
our own name, in the format most likely to be quoted.

Drift is easy. The sentence is generated once per build from a row-count regex. Change the row
markup, or add a build step that filters rows after the lede is written, and the count silently
stops matching while the page still looks fine.

So this recounts the rows and checks the leading figure against them. It also fails on a lede
claiming zero, which is what a broken row parse looks like.
"""
import glob, html, os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
B, E = "<!--LEDE:BEGIN-->", "<!--LEDE:END-->"


_ABBR = {m: i + 1 for i, m in enumerate("jan feb mar apr may jun jul aug sep oct nov dec".split())}


def _row_month(t):
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", t)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.search(r"\b([A-Za-z]{3})[a-z]*\.?\s+(?:\d{1,2},\s*)?(\d{4})", t)
    if m and m.group(1).lower() in _ABBR:
        return int(m.group(2)), _ABBR[m.group(1).lower()]
    return None


def _readouts_ahead(frags):
    """Rows whose window has not passed: dated at or after the current Eastern month, or undated."""
    sys.path.insert(0, HERE)
    from site_dates import eastern_today
    td = eastern_today()
    cur = (td.year, td.month)
    n = 0
    for fr in frags:
        t = html.unescape(re.sub(r"<[^>]+>", " ", fr))
        t = re.sub(r"(?:as of|Sponsor release|ClinicalTrials\.gov)\s+\d{4}-\d{2}-\d{2}", "", t, flags=re.I)
        d = _row_month(t)
        if not d or d >= cur:
            n += 1
    return n


def main():
    bad = []
    checked = 0
    for p in glob.glob(os.path.join(SITE, "**", "index.html"), recursive=True):
        doc = open(p, encoding="utf-8", errors="replace").read()
        if B not in doc:
            continue
        rel = "/" + os.path.relpath(os.path.dirname(p), SITE).replace("\\", "/")
        checked += 1

        lede = html.unescape(re.sub(r"<[^>]+>", "", doc.split(B, 1)[1].split(E, 1)[0]))
        body = re.sub(re.escape(B) + ".*?" + re.escape(E), "", doc, flags=re.S)
        rows = len(re.findall(r'<a class="row"[^>]*>', body))

        # The homepage is a summary, not a table, so its figures come from the sibling pages.
        # Check them against those pages rather than against its own 7 board tiles: the failure
        # that matters is the homepage advertising a number /calendar contradicts.
        if rel == "/.":
            ok = True
            for pat, src, pred in (
                (r"([\d,]+) upcoming FDA decision dates", "calendar", "ahead"),
                (r"([\d,]+) expected clinical trial readouts", "readouts", "all"),
                (r"([\d,]+) decisions already made", "decisions", "all"),
            ):
                mm = re.search(pat, lede)
                if not mm:
                    continue
                f = os.path.join(SITE, src, "index.html")
                if not os.path.exists(f):
                    continue
                sib = open(f, encoding="utf-8", errors="replace").read()
                sib = re.sub(re.escape(B) + ".*?" + re.escape(E), "", sib, flags=re.S)
                frags = re.findall(r'<a class="row"[^>]*>(.*?)</a>', sib, re.S)
                if pred == "ahead":
                    import datetime as _dt
                    today_ = _dt.date.today().isoformat()
                    n = 0
                    for fr in frags:
                        s_ = html.unescape(re.sub(r"<[^>]+>", " ", fr)).lower()
                        if "approved" in s_ or "crl" in s_ or "complete response" in s_:
                            continue
                        d_ = re.search(r"\d{4}-\d{2}-\d{2}", s_)
                        if not d_ or d_.group(0) >= today_:
                            n += 1
                elif src == "readouts":
                    # audit 2026-10-11: "expected" readouts are the windows not yet passed; a passed
                    # window is listed on /readouts with what we found, and counted separately there
                    n = _readouts_ahead(frags)
                else:
                    n = len(frags)
                if int(mm.group(1).replace(",", "")) != n:
                    bad.append((rel, f"homepage says {mm.group(1)} for /{src}, that page has {n}"))
                    ok = False
            # The stat tiles under the CTA were static HTML until 2026-08-29, when the
            # same screen said 52 in the lede and 72 in the tile, with "decided in 2026"
            # off by 11. build_hub_lede now writes the tiles from the lede's own numbers;
            # this holds them together, so drift on either side fails the build.
            full = open(os.path.join(SITE, "index.html"), encoding="utf-8",
                        errors="replace").read()
            tile = re.search(r'<span class="stat gld"><b>([\d,]+)</b><span>upcoming', full)
            said = re.search(r"([\d,]+) upcoming FDA decision dates", lede)
            if tile and said and tile.group(1).replace(",", "") != \
                    said.group(1).replace(",", ""):
                bad.append((rel, f"stat tile says {tile.group(1)} upcoming, the lede on "
                                 f"the same page says {said.group(1)}"))
            if ok:
                pass
            continue

        m = re.search(r"This page lists ([\d,]+)", lede)
        if not m:
            bad.append((rel, "lede does not state a count in the expected form")); continue
        claimed = int(m.group(1).replace(",", ""))

        if claimed == 0:
            bad.append((rel, "lede claims 0 -- the row parse is broken")); continue
        if rel == "/readouts":
            # two-part lede: "{A} expected ... A further {B} readouts whose window has already passed"
            m2 = re.search(r"A further ([\d,]+) readouts whose window has already passed", lede)
            past_claim = int(m2.group(1).replace(",", "")) if m2 else 0
            frags = re.findall(r'<a class="row"[^>]*>(.*?)</a>', body, re.S)
            n_ahead = _readouts_ahead(frags)
            if claimed != n_ahead or claimed + past_claim != rows:
                bad.append((rel, f"lede says {claimed} expected + {past_claim} passed, page has "
                                 f"{n_ahead} not-yet-passed of {rows} rows")); continue
            continue
        if claimed != rows:
            bad.append((rel, f"lede says {claimed}, page has {rows} rows")); continue

        # The breakdown, where present, must add up to the total it is a breakdown of.
        parts = [int(x.replace(",", "")) for x in
                 re.findall(r"([\d,]+) (?:approvals|Complete Response Letters)", lede)]
        if len(parts) == 2 and sum(parts) != claimed:
            bad.append((rel, f"breakdown {parts[0]}+{parts[1]}={sum(parts)} != {claimed}"))

    if bad:
        print(f"FAIL: {len(bad)} hub lede(s) disagree with their own table.")
        for rel, why in bad:
            print(f"   {rel}: {why}")
        print("\n   This sentence is written to be quoted in a search result, away from the table.")
        print("   Re-run build_hub_lede.py; if it still disagrees, the row markup changed.")
        return 1

    print(f"  PASS: {checked} hub lede(s) match their tables")
    return 0


if __name__ == "__main__":
    sys.exit(main())
