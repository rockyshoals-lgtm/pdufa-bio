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
                else:
                    n = len(frags)
                if int(mm.group(1).replace(",", "")) != n:
                    bad.append((rel, f"homepage says {mm.group(1)} for /{src}, that page has {n}"))
                    ok = False
            if ok:
                pass
            continue

        m = re.search(r"This page lists ([\d,]+)", lede)
        if not m:
            bad.append((rel, "lede does not state a count in the expected form")); continue
        claimed = int(m.group(1).replace(",", ""))

        if claimed == 0:
            bad.append((rel, "lede claims 0 -- the row parse is broken")); continue
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
