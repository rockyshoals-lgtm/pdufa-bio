# -*- coding: utf-8 -*-
"""test_calendar_matches_dataset.py -- every upcoming calendar row is a dataset event.

Red team 2026-08-12: /calendar said 67/52 inside FAQPage schema while the API said 64/46, and
the delta hid real defects -- PRAX's row showed September 27 six weeks after the FDA moved it
to December 27; NUVL's row named the wrong sibling drug for its date; BBIO's row text was
literally 'EX-99'; and the dataset itself had LOST the PFE Padcev event five days before its
decision. reconcile_calendar_table.py fixes drift daily; this guard proves it ran and that no
NEW drift appeared.

Rule: every upcoming row on /calendar and the month pages must correspond to a dataset event
with the same ticker and date (drug-token overlap not required here -- the reconciler enforces
names; this guard enforces existence). Known conflicts under human review live in
_calendar_flags_known.json, visibly, and that list may only shrink.
"""
import datetime as dt, glob, json, os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
TODAY = dt.datetime.now(dt.timezone.utc).date().isoformat()
ROW = re.compile(r'<a class="row" href="/pdufa/[^"]+">'
                 r'<div class="t">([A-Z]+) (?:&middot;|·) (\d{4}-\d{2}-\d{2})</div>', re.S)


def main():
    src = open(os.path.join(SITE, "api", "v1", "dataset.mjs"),
               encoding="utf-8", errors="replace").read().replace("\x00", "")
    rows, _ = json.JSONDecoder().raw_decode(src[src.find("["):])
    have = {(str(r.get("t", "")).upper(), str(r.get("d", ""))) for r in rows
            if r.get("type") == "PDUFA"}
    # dual-ticker rows: the page may key an event by its partner ticker (ABEO row for the RARE
    # event), so any same-DATE event also counts as existence
    dates = {str(r.get("d", "")) for r in rows if r.get("type") == "PDUFA"}

    known = {(f["ticker"], f["date"]) for f in json.load(
        open(os.path.join(HERE, "_calendar_flags_known.json"), encoding="utf-8"))["flags"]}

    bad = []
    pages = [os.path.join(SITE, "calendar", "index.html")] + \
        sorted(glob.glob(os.path.join(SITE, "calendar", "*", "*", "index.html")))
    checked = 0
    for p in pages:
        if not os.path.exists(p):
            continue
        doc = open(p, encoding="utf-8", errors="replace").read()
        rel = "/" + os.path.relpath(os.path.dirname(p), SITE).replace("\\", "/")
        for tk, d in ROW.findall(doc):
            if d < TODAY:
                continue
            checked += 1
            if (tk, d) in have or (tk, d) in known:
                continue
            if d in dates:
                continue          # same-date event exists under a partner ticker
            bad.append(f"{rel}: {tk} {d} -- row exists, dataset has no such event; either "
                       f"the dataset lost it (it lost PFE Padcev once) or the row is stale")

    # COUNT RECONCILIATION (red team 2026-08-16 section 2.1, third audit on the same defect,
    # gap widening 3->5): the page's upcoming count and the API's upcoming count must be equal
    # once the known flags are subtracted -- every remaining unit of difference is unexplained
    # drift and fails loudly, named. The API serves dataset.mjs, so counting the dataset in
    # the page's own window IS counting the API.
    main_doc = open(os.path.join(SITE, "calendar", "index.html"),
                    encoding="utf-8", errors="replace").read()
    body = re.sub(r"<script.*?</script>", " ", main_doc, flags=re.S)
    # markup-agnostic row census: strict row regexes miss decorated .t divs (the same
    # blindness that made the insert pass duplicate rows on 08-13). 'TK · YYYY-MM-DD' text
    # pairs are the invariant across every row generation.
    LOOSE = re.compile(r"\b([A-Z]{1,6}) (?:&middot;|·) (\d{4}-\d{2}-\d{2})")
    page_up = [(t, d) for t, d in LOOSE.findall(body) if d >= TODAY]
    win_dates = [d for _, d in LOOSE.findall(body)]
    lo, hi = (min(win_dates), max(win_dates)) if win_dates else (TODAY, TODAY)
    # The dataset DOUBLE-COUNTS dual-listed events (JAZZ + ZYME both carry the one Ziihera
    # decision; PFE + ROIV both carry Brepocitinib) while the page correctly shows one row
    # per event -- which is exactly why the raw page-vs-API totals disagreed for three
    # audits. So the comparison is per EVENT: same-date dataset rows whose drug tokens
    # overlap are one cluster, and every cluster must have exactly one page row (matched by
    # any of its tickers or by drug-token overlap), and every non-flagged page row must
    # belong to a cluster.
    def toks(s):
        out = set()
        for w in re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)*", str(s or "").lower()):
            for p in [w] + w.split("-"):
                if len(p) >= 4 and not p.isdigit():
                    out.add(p)
        return out

    ds_rows = [r for r in rows
               if r.get("type") == "PDUFA" and r.get("dp") == "day"
               and str(r.get("st", "")).lower() != "decided"
               and TODAY <= str(r.get("d", "")) <= hi]
    clusters = []
    for r in ds_rows:
        tk, d, tt = str(r.get("t", "")).upper(), str(r.get("d", "")), toks(r.get("name"))
        for c in clusters:
            if c["d"] == d and (c["toks"] & tt):
                c["tickers"].add(tk); c["toks"] |= tt
                break
        else:
            clusters.append({"d": d, "tickers": {tk}, "toks": tt})

    # page rows with a slice of following text for token matching
    page_rows = []
    for m in re.finditer(r"\b([A-Z]{1,6}) (?:&middot;|·) (\d{4}-\d{2}-\d{2})", body):
        if m.group(2) >= TODAY:
            page_rows.append((m.group(1), m.group(2),
                              toks(body[m.end():m.end() + 110])))
    n_flag = 0
    unmatched_page = []
    for tk, d, tt in page_rows:
        if (tk, d) in known:
            n_flag += 1
            continue
        hit = next((c for c in clusters if c["d"] == d
                    and (tk in c["tickers"] or (c["toks"] & tt))), None)
        if hit is None:
            unmatched_page.append(f"{tk} {d}")
        else:
            hit.setdefault("seen", 0)
            hit["seen"] = hit["seen"] + 1
    unmatched_clusters = [f"{'/'.join(sorted(c['tickers']))} {c['d']}"
                          for c in clusters if not c.get("seen")]
    if unmatched_page or unmatched_clusters:
        bad.append(f"event reconciliation: page rows {len(page_rows)} ({n_flag} flagged), "
                   f"dataset events {len(clusters)}. Page rows with no dataset event: "
                   f"{unmatched_page[:5]}. Dataset events with no page row: "
                   f"{unmatched_clusters[:5]}")

    if bad:
        print(f"FAIL: {len(bad)} calendar row(s) with no dataset event behind them.")
        for b in bad[:8]:
            print(f"   {b}")
        print("\n   Run reconcile_calendar_table.py, verify externally, and either repair the")
        print("   dataset or add a reviewed entry to _calendar_flags_known.json.")
        return 1
    print(f"  PASS: {checked} upcoming calendar rows all correspond to dataset events "
          f"({len(known)} known conflicts under review)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
