# -*- coding: utf-8 -*-
"""Calendar rows must not show a day the dataset no longer claims.

After the 2026-09-10 precision pass, ten PDUFA rows stopped being day-precision. Their calendar
rows still read "TAK  2026-09-30" -- the manufactured day, on the site's most-visited surface,
after we had already withdrawn it from the API. reconcile_calendar_table.py correctly refused to
touch them (it only knows day-precision events, and it flags rather than deletes), so this makes
the edit deliberately.

The row keeps its place and its link; only the date text changes to the granularity we can
source:
    quarter -> "Q3 2026"      month -> "Dec 2026"
A YEAR-precision row has no month to live on, so it comes off the month page rather than sitting
under a heading that asserts a month the sponsor never gave. It stays reachable via the API, the
windowed .ics entry, its ticker hub and its drug page.

MATCHING IS TOKEN-GATED, and the first version of this script was not -- it keyed on ticker plus
date and immediately proved why the house rule exists. NVO has TWO rows on 2026-12-31 (CagriSema
at month precision, denecimig at year precision after its move) and the loose matcher took
whichever came first, deleting the wrong one. It also relabelled an AZN row on /calendar that was
showing its DECISION date 2026-06-12, not a goal date, making a correct row less precise. So: a
row is only touched when the ticker matches, the shown date equals the exact day we withdrew
(read from `_unsourced_day_dates.json`, not inferred), AND the row's own drug text shares a token
with the dataset row's drug name.
"""
import glob
import io
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SITE = "pdufa_site_src"
LEDGER = "_unsourced_day_dates.json"
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
       "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
ROW = re.compile(r'<a class="row"([^>]*)>\s*<div class="t">([A-Z]{1,6}) (?:&middot;|·) '
                 r'(\d{4}-\d{2}-\d{2})(.*?)<div class="d">(.*?)</div>', re.S)
STOP = {"tablets", "capsules", "injection", "phase", "trial", "study", "acetate", "pdufa",
        "ticker", "https", "fda", "decision", "bio", "www"}


def toks(s):
    """Alphanumeric, because drug codes carry digits.

    The first run of this script SKIPPED the NVO Mim8 row: the tokenizer was [a-z]{4,}, so
    "Mim8" produced nothing and the row shared no token with the dataset name "Mim8
    (denecimig)". Skipping was the right failure -- it surfaced rather than guessed -- but the
    fix is to tokenize the way drug names are actually written, and to read the row's href
    (/pdufa/NVO-mim8) as evidence too.
    """
    return {w for w in re.findall(r"[a-z][a-z0-9]{3,}", str(s or "").lower())
            if w not in STOP}


def label(r):
    dp = r.get("dp")
    dm = str(r.get("dm") or str(r.get("d") or "")[:7])
    if dp == "quarter":
        return f"Q{(int(dm[5:7]) - 1) // 3 + 1} {dm[:4]}"
    if dp == "month":
        return f"{MON[int(dm[5:7]) - 1]} {dm[:4]}"
    return None                       # year


def main():
    src = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"),
                  encoding="utf-8", errors="replace").read().replace("\x00", "")
    rows, _ = json.JSONDecoder().raw_decode(src[src.find("["):])
    led = json.loads(io.open(LEDGER, encoding="utf-8").read())

    # (ticker, withdrawn_day) -> [(drug tokens, label)] built from the ledger, so we only ever
    # touch a row whose exact day we ourselves withdrew.
    targets = {}
    for e in led.get("rows", []):
        tk, was = e["ticker"].upper(), e["was_date"]
        for r in rows:
            if str(r.get("t") or "").upper() != tk or r.get("type") != "PDUFA":
                continue
            if r.get("dp") == "day":
                continue
            note = str((r.get("_d") or {}).get("date_note") or "")
            # the row that carries this withdrawal: either it still sits on the old day, or its
            # note records the withdrawal and it moved (year precision)
            if str(r.get("d") or "") != was and "withdrawn" not in note.lower():
                continue
            targets.setdefault((tk, was), []).append((toks(r.get("name")), label(r), r))

    if not targets:
        print("nothing to do")
        return 0

    pages = [os.path.join(SITE, "calendar", "index.html")] + \
        sorted(glob.glob(os.path.join(SITE, "calendar", "*", "*", "index.html")))

    relabelled = removed = skipped = 0
    for path in pages:
        doc = io.open(path, encoding="utf-8", errors="replace").read()
        orig = doc
        for m in list(ROW.finditer(doc))[::-1]:
            attrs, tk, shown, drugtext = m.group(1), m.group(2), m.group(3), m.group(5)
            cands = targets.get((tk, shown))
            if not cands:
                continue
            rt = toks(re.sub(r"<[^>]+>", " ", drugtext)) | toks(attrs.replace("-", " "))
            hit = next((c for c in cands if c[0] & rt), None)
            if hit is None:
                skipped += 1
                print(f"  SKIP {tk} {shown} on {os.path.relpath(path, SITE)}: no drug token "
                      f"shared with any withdrawn row ({sorted(rt)[:4]}) -- left for a human")
                continue
            lab = hit[1]
            start = m.start()
            end = doc.find("</a>", start)
            if end == -1:
                continue
            end += 4
            if lab is None:
                doc = doc[:start] + doc[end:]
                removed += 1
                print(f"  REMOVED {tk} {shown} ({os.path.relpath(path, SITE)}) -- year "
                      f"precision, no month page can hold it honestly")
            else:
                seg = doc[start:end]
                seg = seg.replace(f"{tk} &middot; {shown}", f"{tk} &middot; {lab}", 1) \
                         .replace(f"{tk} · {shown}", f"{tk} · {lab}", 1)
                doc = doc[:start] + seg + doc[end:]
                relabelled += 1
                print(f"  {tk} {shown} -> {lab}  ({os.path.relpath(path, SITE)})")

        if doc != orig:
            n = len(re.findall(r'<div class="t">[A-Z]{1,6} (?:&middot;|·) '
                               r'(?:\d{4}-\d{2}-\d{2}|Q[1-4] \d{4}|[A-Z][a-z]{2} \d{4})', doc))
            doc = re.sub(r'<span class="count">\d+ PDUFA dates?</span>',
                         f'<span class="count">{n} PDUFA dates</span>', doc)
            io.open(path, "w", encoding="utf-8").write(doc)

    print(f"\n{relabelled} relabelled, {removed} removed, {skipped} skipped for review")
    return 0


if __name__ == "__main__":
    sys.exit(main())
