# -*- coding: utf-8 -*-
"""fix_chart_captions.py -- a run-up caption never calls the announcement day the FDA decision when the FDA acted
on a different day (audit 2026-10-04 P2).

JUVMO's chart said "FDA decision 9/28/26" and marked the chart "PDUFA 9/28/26"; the FDA's letter is dated
9/25 and AbbVie announced on 9/28. The chart is keyed on the announcement (the day the price could react),
which is fine; the caption must say so. For every decision page whose dataset row carries an fda_action_date
different from the page's day, the caption becomes "Announced m/d/yy (FDA action m/d/yy)." and the SVG label
"announced m/d/yy". build_decision_page.py writes new pages this way; this repairs the ones already out.

2026-11-18 (design red team, change 2): the decision-day marker read "PDUFA m/d/yy" on 457 pages, though it marks
the FDA's decision, not the goal date (GSK: "PDUFA 11/17/26", goal Nov 27). It now reads "FDA decision m/d/yy".
Pages with no dataset row take the FDA's day from their own key facts (FDA decision date + Announced).
Red team of that change: a page whose FDA day is "not found in a public FDA record" is "announced m/d/yy" with the
caption saying no public record holds the FDA's day, and a page whose Announced row carries a note ("after the
close", "per the 8-K") is "move day m/d/yy": the trading day the move is measured on, with both other days named.

    python fix_chart_captions.py [--dry-run]
"""
import argparse
import glob
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")


def mdy(iso):
    y, m, d = iso.split("-")
    return f"{int(m)}/{int(d)}/{y[2:]}"


def pairs():
    """(ticker, page day, fda action day) for rows where the two differ."""
    src = io.open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
    rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    out = {}
    for r in rows:
        if r.get("type") != "PDUFA" or str(r.get("st") or "").lower() != "decided":
            continue
        fad = str((r.get("_d") or {}).get("fda_action_date") or "")[:10]
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", fad):
            continue
        tk = str(r.get("t") or "").upper()
        for day in {str(r.get("dcd") or "")[:10], str(r.get("d") or "")[:10]}:
            if re.match(r"^\d{4}-\d{2}-\d{2}$", day) and day != fad:
                out[(tk, day)] = fad
    return out


KV_FDA = re.compile(r'<div class="kv"><span>FDA decision date</span><b>([^<]*)</b></div>')
KV_ANN = re.compile(r'<div class="kv"><span>Announced</span><b>([^<]*)</b></div>')
MARK = r'(text-anchor="end"[^>]*>)(?:PDUFA|FDA decision|announced|move day) '
CAP = r'(?:FDA decision|Announced|Move measured on) '


def basis(doc, day, ds_fad=None):
    """What the chart's decision-day marker can truthfully be called, from the page's own key facts (and the dataset).
    Returns (label, caption sentence without the final period)."""
    kf = KV_FDA.search(doc)
    ka = KV_ANN.search(doc)
    fv = kf.group(1).strip() if kf else ""
    fad = ds_fad or (fv if re.fullmatch(r"\d{4}-\d{2}-\d{2}", fv) else None)
    av = ka.group(1).strip() if ka else ""
    ann = av[:10] if re.match(r"\d{4}-\d{2}-\d{2}", av) else None
    fda_txt = f"FDA action {mdy(fad)}" if fad else "no public FDA record of the action day"
    if ann and av != ann:
        # the announcement carries a note ("2026-03-19, after the close", "2025-05-16 per the Novavax 8-K; ..."): the
        # page's day is the trading day the move is measured on, which is neither the FDA's day nor plainly the
        # announcement. Say exactly that.
        note = av[10:].lstrip(" ,;")
        return "move day", f"Move measured on {mdy(day)} (announced {mdy(ann)}{', ' + note if note else ''}; {fda_txt})"
    if fad == day:
        return "FDA decision", f"FDA decision {mdy(day)}"
    if fad or ann == day or kf:
        return "announced", f"Announced {mdy(day)} ({fda_txt})"
    return None, None                   # no key facts to go on: leave the page as it is


def fix(doc, day, label, caption):
    new = doc
    if not label:
        return re.sub(r'(text-anchor="end"[^>]*>)PDUFA ' + re.escape(mdy(day)) + "<",
                      r"\1FDA decision " + mdy(day) + "<", new)
    new = re.sub(MARK + re.escape(mdy(day)) + "<", lambda m: m.group(1) + f"{label} {mdy(day)}<", new)
    new = re.sub(CAP + re.escape(mdy(day)) + r"(?: \([^)]*\))?\. ", lambda m: caption + ". ", new)
    return new


MOVE_ROW = re.compile(r'(<div class="kv"><span>Decision-day move</span><b>[^<]*</b></div>)'
                      r'(<div class="kv"><span>Move measured on</span><b>[^<]*</b></div>)?')


def move_basis(doc, day, label, tk=None):
    """Red team of change 2: once key facts give the FDA's day, the "Decision-day move" row beside it still measures the
    page's day (CAPR: -33.0% beside FDA decision date 2025-07-09; the move is Jul 11's). Name the day it is measured
    on, in a row of its own, so the label other tools match stays as it is."""
    # a "move day" page's own Announced row says when the news came; the row states the day and nothing more, since
    # that day is not always after the news (NVO-2026-03-26: announced after the close the same day)
    # change 10: the row names the session and the close it is measured against, the same text
    # sync_decision_runup_chip.py writes for every page whose event the run-up study measured
    from sync_decision_runup_chip import NOT_RECORDED, after_close, basis_row, study_eves
    global _EVES
    if _EVES is None:
        _EVES = study_eves()
    eve = _EVES.get((tk, day))
    if eve:
        row = basis_row(day, eve, label == "announced", after_close(doc, day))
    else:
        row = NOT_RECORDED
    return MOVE_ROW.sub(lambda m: m.group(1) + row, doc, count=1)


_EVES = None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    n = 0
    ds = pairs()
    for p in sorted(glob.glob(os.path.join(SITE, "fda-decision", "*", "index.html"))):
        slug = os.path.basename(os.path.dirname(p))
        m = re.match(r"([A-Z.]{1,8})-(\d{4}-\d{2}-\d{2})$", slug)
        if not m:
            continue
        tk, day = m.group(1), m.group(2)
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        label, caption = basis(doc, day, ds.get((tk, day)))
        new = fix(doc, day, label, caption)
        if label in ("announced", "move day"):
            new = move_basis(new, day, label, tk)
        if new != doc:
            n += 1
            print(f"  /fda-decision/{slug}: chart marker '{label or 'FDA decision'}'" + (f" ({caption})" if caption else ""))
            if not a.dry_run:
                io.open(p, "w", encoding="utf-8", newline="").write(new)
    print(f"chart captions: {n} page(s) corrected")
    return 0


if __name__ == "__main__":
    sys.exit(main())
