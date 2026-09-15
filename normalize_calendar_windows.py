# -*- coding: utf-8 -*-
"""One event, one window label, on every calendar surface. Audit 09-14 item 5.

The audit's headline is that a corrected value reaches one surface and not another. The calendar
was already doing it to ITSELF: ABBV tavapadon, AZN Ultomiris, BAYRY finerenone and NVO
CagriSema each render as "Dec 2026" on /calendar/2026/december and "Q4 2026 (est.)" on
/calendar. Same four events, two labels, both live, because two renderers each formatted the
date their own way.

site_windows.window_label is now the only thing allowed to decide, and it returns the most
precise honest form: a month-precision row says its MONTH. "Q4 2026" for a row we know lands in
December is true but needlessly vague, and vagueness on a date is the thing this site exists not
to do.

Rows with no dataset event behind them keep whatever they have -- they are the unbacked
population tracked separately, and inventing a tidier label for them would hide that.

    python normalize_calendar_windows.py [--dry-run]
"""
import argparse
import glob
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from site_windows import window_label  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SITE = "pdufa_site_src"
STOP = {"pdufa", "date", "and", "the", "est"}
ROW = re.compile(r'(<a class="row"[^>]*>\s*<div class="t">([A-Z]{1,6}) (?:&middot;|·) )'
                 r'([^<]+?)(</div><div class="d">)(.*?)(</div>)', re.S)


def toks(s):
    return {w for w in re.findall(r"[a-z][a-z0-9]{2,}", str(s or "").lower())
            if w not in STOP}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    src = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"),
                  encoding="utf-8", errors="replace").read().replace("\x00", "")
    rows, _ = json.JSONDecoder().raw_decode(src[src.find("["):])
    nonday = [r for r in rows if r.get("type") == "PDUFA"
              and str(r.get("dp") or "day") != "day"
              and str(r.get("st") or "").lower() != "decided"]

    pages = [os.path.join(SITE, "calendar", "index.html")] + \
        sorted(glob.glob(os.path.join(SITE, "calendar", "*", "*", "index.html")))
    fixed = 0
    for p in pages:
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        orig = doc

        def rep(m):
            global fixed  # noqa: PLW0603
            head, tk, lab, mid, drugtxt, tail = m.groups()
            lab = lab.strip()
            if re.match(r"^\d{4}-\d{2}-\d{2}", lab):
                return m.group(0)                     # a real day; not ours
            rt = toks(re.sub(r"<[^>]+>", " ", drugtxt))
            for r in nonday:
                if str(r.get("t") or "").upper() != tk:
                    continue
                if not (rt & toks(r.get("name"))):
                    continue
                want = window_label(r)
                if want and want != lab:
                    return head + want + mid + drugtxt + tail
                return m.group(0)
            return m.group(0)

        doc2 = ROW.sub(rep, doc)
        if doc2 != doc:
            n = sum(1 for _ in re.finditer(r"", ""))  # placeholder, counted below
            before = set(re.findall(r'<div class="t">[A-Z]{1,6} (?:&middot;|·) ([^<]+)</div>',
                                    doc))
            after = set(re.findall(r'<div class="t">[A-Z]{1,6} (?:&middot;|·) ([^<]+)</div>',
                                   doc2))
            print(f"  {os.path.relpath(p, SITE)}: {sorted(before - after)} -> "
                  f"{sorted(after - before)}")
            fixed += 1
            if not a.dry_run:
                io.open(p, "w", encoding="utf-8").write(doc2)

    print(f"\n{fixed} calendar page(s) normalised to site_windows.window_label"
          + ("   (--dry-run)" if a.dry_run else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
