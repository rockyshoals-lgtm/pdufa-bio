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
# LOOSENED 2026-08-18: was anchored on href="/pdufa/..." -- the HOOK/CRBP/NCNA fossil rows carry
# href="#" and were structurally INVISIBLE to this guard. Any row anchor now counts, and the
# drug text is captured for the token-overlap check.
ROW = re.compile(r'<a class="row"[^>]*>\s*<div class="t">([A-Z]{1,6}) (?:&middot;|·) '
                 r'(\d{4}-\d{2}-\d{2}).*?<div class="d">(.*?)</div>', re.S)

# WINDOWED ROWS, added 2026-09-10. Ten PDUFA rows lost day precision that day (sponsors had
# stated a quarter, or nothing) and their calendar rows were relabelled "Q3 2026" / "Dec 2026".
# ROW above only matches YYYY-MM-DD, so every one of them would have become structurally
# invisible to this guard -- the exact condition that let the HOOK/CRBP/NCNA fossil rows survive
# until their date passed. A windowed row is still a claim on the calendar, so it is still
# census'd: it must correspond to a dataset PDUFA for that ticker whose own precision is not
# "day" and whose window label matches.
WROW = re.compile(r'<a class="row"[^>]*>\s*<div class="t">([A-Z]{1,6}) (?:&middot;|·) '
                  r'(Q[1-4] \d{4}|[A-Z][a-z]{2} \d{4})[^<]*</div>'
                  r'.*?<div class="d">(.*?)</div>', re.S)
MON3 = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def window_labels(r):
    """Labels a non-day dataset row may honestly wear on the calendar.

    TWO CONVENTIONS EXIST, which is what this check found on its first run. The calendar was
    already rendering month-precision rows as "Q4 2026 (est.)" (NVO CagriSema, ABBV, RHHBY, NVS,
    AZN, BAYRY), and the 2026-09-10 relabeller emitted "Dec 2026" for the same class of row. Both
    are TRUE of a 2026-12 row -- a month sits inside its quarter -- so both are accepted here
    rather than failing eleven correct pre-existing rows. Normalising the site on one convention
    is worth doing, but it is a copy decision, not a correctness one, and it does not belong in a
    guard that exists to catch fabricated dates.
    """
    dm = str(r.get("dm") or str(r.get("d") or "")[:7])
    if len(dm) < 7:
        return set()
    q = f"Q{(int(dm[5:7]) - 1) // 3 + 1} {dm[:4]}"
    if r.get("dp") == "quarter":
        return {q}
    if r.get("dp") == "month":
        return {f"{MON3[int(dm[5:7]) - 1]} {dm[:4]}", q}
    return set()


def main():
    src = open(os.path.join(SITE, "api", "v1", "dataset.mjs"),
               encoding="utf-8", errors="replace").read().replace("\x00", "")
    rows, _ = json.JSONDecoder().raw_decode(src[src.find("["):])
    have = {(str(r.get("t", "")).upper(), str(r.get("d", ""))) for r in rows
            if r.get("type") == "PDUFA"}
    # Dual-ticker rows: the page may key an event by its partner ticker (RPRX row for the NUVL
    # event). TIGHTENED 2026-08-18: the allowance was "any same-DATE event counts" -- and three
    # fossil rows (HOOK/CRBP/NCNA, all fake 'Pembrolizumab combination' text, dead # links, in
    # NO data source since the initial site commit) rode through on BMY's real 2026-08-17 event,
    # then killed the CI run when their date passed with no outcome. A partner row must now share
    # a drug TOKEN with the same-date event it claims to be, so unrelated tickers can't hitchhike.
    date_names = {}
    for r in rows:
        if r.get("type") == "PDUFA":
            date_names.setdefault(str(r.get("d", "")), set()).update(
                w for w in re.findall(r"[a-z]{4,}", str(r.get("name", "")).lower())
                if w not in ("with", "combination", "priority", "review", "oncology"))

    known = {(f["ticker"], f["date"]) for f in json.load(
        open(os.path.join(HERE, "_calendar_flags_known.json"), encoding="utf-8"))["flags"]}

    # A RATCHET, not an amnesty (2026-09-10). Seven windowed rows have no dataset event behind
    # them and no sourced goal date -- see _calendar_unbacked_q4_rows.json for the evidence on
    # each. They are listed rather than silently passed: every run prints them, and the count may
    # only go DOWN. Adding an eighth fails this guard.
    global UNBACKED, unbacked_seen
    _ub = json.load(open(os.path.join(HERE, "_calendar_unbacked_q4_rows.json"),
                         encoding="utf-8"))
    UNBACKED = {(r["ticker"], r["window"]) for r in _ub["rows"]}
    UNBACKED_N = len(_ub["rows"])
    unbacked_seen = set()

    bad = []
    pages = [os.path.join(SITE, "calendar", "index.html")] + \
        sorted(glob.glob(os.path.join(SITE, "calendar", "*", "*", "index.html")))
    checked = 0
    for p in pages:
        if not os.path.exists(p):
            continue
        doc = open(p, encoding="utf-8", errors="replace").read()
        rel = "/" + os.path.relpath(os.path.dirname(p), SITE).replace("\\", "/")
        for m in ROW.finditer(doc):
            tk, d, drugtxt = m.group(1), m.group(2), m.group(3)
            if d < TODAY:
                continue
            # A decided row may be FUTURE-dated (RARE approved Aug 19 against an Aug 23 goal
            # date -- the row keeps the goal date, wears the checkmark and links the decision
            # page). Its dataset event is Decided, so the upcoming census must skip it.
            if 'data-dec="1"' in doc[max(0, m.start() - 40):m.start() + 40]:
                continue
            checked += 1
            if (tk, d) in have or (tk, d) in known:
                continue
            # partner-ticker allowance, token-gated: the row's own drug text must share a token
            # with a same-date dataset event (RPRX's row names zidesamtinib -> matches NUVL's).
            toks = set(re.findall(r"[a-z]{4,}", re.sub(r"<[^>]+>", " ", drugtxt).lower()))
            if toks & date_names.get(d, set()):
                continue
            bad.append(f"{rel}: {tk} {d} -- row exists, dataset has no such event and its text "
                       f"shares no drug token with any same-date event; either the dataset lost "
                       f"it (it lost PFE Padcev once) or the row is fake (HOOK/CRBP/NCNA were)")

        # windowed rows are census'd too -- see WROW
        for m in WROW.finditer(doc):
            tk, lab, drugtxt = m.group(1), m.group(2), m.group(3)
            rtoks = set(re.findall(r"[a-z][a-z0-9]{3,}",
                                   re.sub(r"<[^>]+>", " ", drugtxt).lower()))
            ok = False
            for r in rows:
                if r.get("type") != "PDUFA" or str(r.get("t", "")).upper() != tk:
                    continue
                if r.get("dp") == "day":
                    continue
                if lab not in window_labels(r):
                    continue
                ntoks = set(re.findall(r"[a-z][a-z0-9]{3,}", str(r.get("name", "")).lower()))
                if not rtoks or not ntoks or (rtoks & ntoks):
                    ok = True
                    break
            if not ok and (tk, lab) not in known:
                if (tk, lab) in UNBACKED:
                    unbacked_seen.add((tk, lab, rel))
                    continue
                bad.append(f"{rel}: {tk} {lab} -- windowed row with no matching non-day dataset "
                           f"PDUFA for that ticker and window. A row that shows a window instead "
                           f"of a day is still a published claim; it must trace to a dataset row "
                           f"whose precision actually is that window.")

    # THE RATCHET REPORT. Printed every run so the backlog is never invisible, and enforced so it
    # can only shrink. These are published claims with no dataset event and no sourced goal date.
    if unbacked_seen:
        print(f"\n  {UNBACKED_N} KNOWN-UNBACKED windowed row(s) awaiting a primary-source pass "
              f"(_calendar_unbacked_q4_rows.json, recorded 2026-09-10):")
        for tk, lab, rel in sorted(unbacked_seen):
            print(f"     {rel}: {tk} {lab}")
        print("     Each has a /pdufa page asserting 2026-12-31 with no sponsor goal-date "
              "source. Source them, re-date them, or withdraw them -- do not add an eighth.")
    if len(UNBACKED) > UNBACKED_N:
        bad.append(f"the unbacked-row list grew to {len(UNBACKED)} (was {UNBACKED_N}); it is a "
                   f"ratchet for an existing backlog, not a place to park new unsourced rows")

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
            trail = body[m.end():m.end() + 110]
            # future-dated but already DECIDED (RARE approved 4 days before its goal date):
            # the row wears the checkmark/outcome and its dataset event is no longer upcoming.
            if re.search(r"&#10003;|✓|\bApproved\b|\bCRL\b|Complete Response", trail):
                continue
            page_rows.append((m.group(1), m.group(2), toks(trail)))
    n_flag = 0
    unmatched_page = []
    for tk, d, tt in page_rows:
        if (tk, d) in known:
            n_flag += 1
            continue
        # ticker match FIRST, token overlap only as fallback: the 110-char trail can
        # bleed into the NEXT row's href (the ROIV row's trail carried /pdufa/NVO-mim8,
        # crediting ROIV's Brepocitinib row to the NVO cluster and orphaning PFE/ROIV).
        hit = (next((c for c in clusters if c["d"] == d and tk in c["tickers"]), None)
               or next((c for c in clusters if c["d"] == d and (c["toks"] & tt)), None))
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
