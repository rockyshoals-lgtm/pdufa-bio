# -*- coding: utf-8 -*-
"""test_decision_dates_labeled.py -- a decision page labels each of its dates for what it is.

Design red team 2026-11-18 (change 2). GSK's approval page marked its chart "PDUFA 11/17/26": the marker sits on the
FDA's decision, and the PDUFA goal was Nov 27. The same "PDUFA" label was on 457 pages. And /fda-decision/CAPR-2025-07-11
gave "FDA decision date 2025-07-11" and called the FDA's letter "dated July 11, 2025", while the letter it links is
dated July 9 (Capricor announced on July 11); eight older pages had the same split. This fails if:

  1. any decision page's chart marker labels a day "PDUFA m/d/yy" (it marks the FDA decision or its announcement);
  2. a page's "The FDA's own letter" card names a day the FDA acted that differs from its key facts' FDA decision
     date (the announcement day belongs in an "Announced" row);
  3. a card's "dated" day is not the date in the FDA file name it links (CRL_<app>_<YYYYMMDD>.pdf), unless the card
     says it is a corrected letter.
  4. a home "Recently decided" card shows a date other than the FDA's action day for its page (the dataset's
     fda_action_date, else the page's own key facts), or the cards lack the note that says how the move is measured;
  5. a /ticker hub's "FDA decision history" row leads with any day but that same FDA action day.
  6. a chart marker on the page's day says "FDA decision" while key facts give another FDA day or none, or says
     "announced"/"move day" while key facts put the FDA decision on that day (and no announcement note says otherwise);
  7. key facts disagree with the page's own "FDA record of the action" block.
A home card or hub row whose page holds no public FDA day must say "announced". PLANT=1 puts the announcement day back
on CAPR-2025-07-11's key facts, PLANT=marker relabels GSK-2026-03-19's marker "FDA decision"; both must FAIL.

    python tests/test_decision_dates_labeled.py
"""
import datetime as dt
import glob
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
MARK = re.compile(r'text-anchor="end"[^>]*>PDUFA (\d{1,2}/\d{1,2}/\d{2})<')
CARD = re.compile(r'<!--CRLSRC:BEGIN-->(.*?)<!--CRLSRC:END-->', re.S)
KV = re.compile(r'<div class="kv"><span>FDA decision date</span><b>(\d{4}-\d{2}-\d{2})</b></div>')
KV_ANY = re.compile(r'<div class="kv"><span>FDA decision date</span><b>([^<]*)</b></div>')
KV_ANN = re.compile(r'<div class="kv"><span>Announced</span><b>([^<]*)</b></div>')
MARKER = re.compile(r'text-anchor="end"[^>]*>([A-Za-z ]+?) (\d{1,2}/\d{1,2}/\d{2})<')
FDAREC = re.compile(r'<!--FDAREC:BEGIN-->.*?<b>FDA record of the action:</b> the FDA [a-z ]+? on <b>([A-Z][a-z]+ \d{1,2}, '
                    r'\d{4})</b>, per <a href="https://www\.(?:accessdata\.)?fda\.gov/', re.S)


def iso(text):
    return dt.datetime.strptime(text, "%B %d, %Y").date().isoformat()


def main():
    bad, pages, cards = [], 0, 0
    for p in sorted(glob.glob(os.path.join(SITE, "fda-decision", "*", "index.html"))):
        slug = os.path.basename(os.path.dirname(p))
        doc = open(p, encoding="utf-8", errors="replace").read()
        if os.environ.get("PLANT") and slug == "CAPR-2025-07-11":
            doc = KV.sub('<div class="kv"><span>FDA decision date</span><b>2025-07-11</b></div>', doc, 1)
        if os.environ.get("PLANT") == "marker" and slug == "GSK-2026-03-19":
            doc = doc.replace(">announced 3/19/26<", ">FDA decision 3/19/26<")
        pages += 1
        day = slug[-10:]
        mdy = f"{int(day[5:7])}/{int(day[8:])}/{day[2:4]}"
        kvf, kva = KV_ANY.search(doc), KV_ANN.search(doc)
        fda = kvf.group(1) if kvf and re.fullmatch(r"\d{4}-\d{2}-\d{2}", kvf.group(1)) else None
        rec = FDAREC.search(doc)
        if rec and fda and iso(rec.group(1)) != fda:
            bad.append(f"/fda-decision/{slug}: key facts give FDA decision date {fda}, the page's FDA record of the "
                       f"action says {iso(rec.group(1))}")
        # the marker on the page's own day says "FDA decision" only when key facts put the FDA's decision on that day
        for lab, md in MARKER.findall(doc):
            if md != mdy or lab not in ("FDA decision", "announced", "move day"):
                continue
            if lab == "FDA decision" and fda != day:
                bad.append(f"/fda-decision/{slug}: chart marker says 'FDA decision {md}', but key facts give the FDA's "
                           f"day as {fda or (kvf.group(1) if kvf else 'nothing')}")
            elif lab != "FDA decision" and fda == day and not (kva and kva.group(1) != day):
                bad.append(f"/fda-decision/{slug}: chart marker says '{lab} {md}', but key facts put the FDA decision "
                           f"on that day")
        for m in MARK.findall(doc):
            bad.append(f"/fda-decision/{slug}: chart marker reads 'PDUFA {m}'; it marks the FDA decision, not the goal")
        c = CARD.search(doc)
        if not c:
            continue
        cards += 1
        card = re.sub(r"<[^>]+>", "", c.group(1))
        acted = re.search(r"the FDA acted on ([A-Z][a-z]+ \d{1,2}, \d{4})\.", card)
        dated = re.search(r"\(PDF\), dated ([A-Z][a-z]+ \d{1,2}, \d{4})", card)
        fn = re.search(r"download\.open\.fda\.gov/crl/CRL_[A-Za-z]+\d+_(\d{8})", c.group(1))
        kv = KV.search(doc)
        action = iso(acted.group(1)) if acted else (iso(dated.group(1)) if dated else None)
        if action and kv and kv.group(1) != action:
            bad.append(f"/fda-decision/{slug}: key facts give FDA decision date {kv.group(1)}, but the FDA's letter "
                       f"card says the FDA acted on {action}")
        if dated and fn and "corrected letter" not in card:
            fd = f"{fn.group(1)[:4]}-{fn.group(1)[4:6]}-{fn.group(1)[6:]}"
            if iso(dated.group(1)) != fd:
                bad.append(f"/fda-decision/{slug}: card says the letter is dated {iso(dated.group(1))}, its FDA file "
                           f"is dated {fd}")
    # 4. home cards
    import json
    src = open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8", errors="replace").read()
    rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    fad = {}
    for r in rows:
        f = str((r.get("_d") or {}).get("fda_action_date") or "") if isinstance(r.get("_d"), dict) else ""
        u = re.match(r"/fda-decision/([A-Z.]+-\d{4}-\d{2}-\d{2})/?$", str(r.get("url") or ""))
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", f) and u:
            fad[u.group(1)] = f
        elif re.fullmatch(r"\d{4}-\d{2}-\d{2}", f) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(r.get("dcd") or "")):
            fad.setdefault(f"{str(r.get('t') or '').upper()}-{r['dcd']}", f)

    def want_day(slug):
        """(the FDA's day, True), or (the page day, False) when no public FDA record holds the day."""
        if slug in fad:
            return fad[slug], True
        pp = os.path.join(SITE, "fda-decision", slug, "index.html")
        d = open(pp, encoding="utf-8", errors="replace").read() if os.path.exists(pp) else ""
        m = KV.search(d)
        if m:
            return m.group(1), True
        m = FDAREC.search(d)
        if m:
            return iso(m.group(1)), True
        return slug[-10:], False

    home = open(os.path.join(SITE, "index.html"), encoding="utf-8", errors="replace").read()
    i = home.find('<div class="decs">')
    block = home[i:home.find("</div>", i)] if i >= 0 else ""
    homecards = 0
    if i < 0:
        bad.append("home: the Recently decided block is missing")
    for slug, shown, ann in re.findall(r'<a class="dec [a-z]+" href="/fda-decision/([A-Z.]+-\d{4}-\d{2}-\d{2})"[^>]*>.*?'
                                       r'<span class="dd">(\d{4}-\d{2}-\d{2})( announced)? ', block, re.S):
        homecards += 1
        want, known = want_day(slug)
        if shown != want:
            bad.append(f"home: Recently decided card {slug} shows {shown}; the FDA's action day is {want}")
        elif known == bool(ann):
            bad.append(f"home: Recently decided card {slug} " + ("calls the FDA's day 'announced'" if known else
                       "shows its announcement as the FDA's day; no public FDA record holds that day"))
    if homecards and "first trading day after the decision was made public" not in block:
        bad.append("home: Recently decided cards do not say how the move is measured")
    # 5. ticker hubs: each "FDA decision history" row leads with the FDA's action day
    hubrows = 0
    for hp in sorted(glob.glob(os.path.join(SITE, "ticker", "*", "index.html"))):
        hdoc = open(hp, encoding="utf-8", errors="replace").read()
        for slug, shown in re.findall(r'<a class="row" href="/fda-decision/([A-Z.]+-\d{4}-\d{2}-\d{2})"><span class="t">'
                                      r'([A-Z][a-z]{2} \d{1,2}, \d{4})', hdoc):
            hubrows += 1
            want, known = want_day(slug)
            if not known and not re.search(re.escape(f'href="/fda-decision/{slug}"><span class="t">{shown}') +
                                           r' <small[^>]*>\(announced; no public FDA record', hdoc):
                bad.append(f"/ticker/{os.path.basename(os.path.dirname(hp))}: history row {slug} shows {shown} as the "
                           f"FDA's day; no public FDA record holds it")
            if dt.datetime.strptime(shown, "%b %d, %Y").date().isoformat() != want:
                bad.append(f"/ticker/{os.path.basename(os.path.dirname(hp))}: history row {slug} shows {shown}; "
                           f"the FDA's action day is {want}")
    print(f"{pages} decision pages, {cards} with the FDA's own letter, {homecards} home card(s), {hubrows} hub row(s)")
    if bad:
        for b in bad[:30]:
            print("  FAIL " + b)
        if len(bad) > 30:
            print(f"  ... and {len(bad) - 30} more")
        print("  fix: python link_crl_letters.py && python fix_decision_kv_action_date.py && python fix_chart_captions.py "
              "&& python build_home_board.py && python build_ticker_hubs.py")
        sys.exit(1)
    print("  PASS: chart markers name the FDA decision, and key facts and letter cards agree on the FDA's day")


if __name__ == "__main__":
    main()
