# -*- coding: utf-8 -*-
"""test_calendar_dates_first.py -- /calendar opens on its dates, and its rows read whole.

Design red team 2026-11-18 (change 7). /calendar put six paragraphs, a subscribe box and a heat map ahead of its first
date (one paragraph about our own pipeline: "26 of the 88 decided rows ... no row in the API dataset"), opened on five
months of decided rows, cut names mid-word ("CTx-1301 (fixed dose, pediatri"), printed "Approved: , LYTENAVA" and
wrote decided rows in two templates. shape_calendar.py shapes the page last in the build. This fails if:

  1. anything but the lede's first sentence, one heading and the search sits between the h1 and the first month;
  2. a month with no open goal date comes before one that has one, or is not folded; open months out of date order;
  3. the notes (the rest of the lede, the explainer, the subscribe box, the heat map) are not in "About this
     calendar" after the months, or the page still describes the API dataset;
  4. a decided row uses the "· ✓ Approved" template, opens with a comma, ends with a dash, or shows a cut-off version
     of its decision page's name (or a drug name cut with "…");
  4b. a folded month's summary miscounts its rows or calls a withdrawn row decided; the subscribe box or heat map
     is gone;
  5. shape_calendar.py would change the page (it is not at its shaped state), undo then shape does not give it back,
     or a block appended before </head> after shaping (build_date_modified.py) would make the next shape move it.

    python tests/test_calendar_dates_first.py
"""
import io
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import shape_calendar as sc  # noqa: E402

PAGE = os.path.join(HERE, "pdufa_site_src", "calendar", "index.html")


def main():
    doc = io.open(PAGE, encoding="utf-8", errors="replace").read()
    if os.environ.get("PLANT") == "order":
        doc = sc.unshape(doc)
    bad = []
    if sc.shape(doc) != doc:
        bad.append("/calendar is not at its shaped state")
    elif sc.shape(sc.unshape(doc)) != doc:
        bad.append("/calendar: undo then shape does not give the page back")
    else:
        # build_date_modified.py re-appends its metas just before </head> after the page is shaped
        late = doc.replace("</head>", '<!--DMOD:BEGIN--><meta property="og:updated_time" content="x"><!--DMOD:END-->'
                           "</head>", 1)
        if sc.shape(late) != late:
            bad.append("/calendar: a block appended before </head> after shaping makes the next shape move the page")
    h1 = doc.find("<h1")
    first = doc.find(sc.MHEAD)
    top = doc[h1:first]
    for what, pat in (("the explainer", r'class="explainer"'), ("the subscribe box", r"<!--SUBSCRIBE:BEGIN-->"),
                      ("the heat map", r'class="hmap"'), ("a jump link", r'class="pd-jump"')):
        if re.search(pat, top):
            bad.append(f"/calendar: {what} sits ahead of the first month")
    lede = re.search(r"<!--LEDE:BEGIN--><p[^>]*>(.*?)</p><!--LEDE:END-->", doc, re.S)
    if lede and len(re.findall(r"\. (?=[A-Z0-9])", re.sub(r"<[^>]+>", "", lede.group(1)))) > 0:
        bad.append("/calendar: the lede ahead of the dates runs past one sentence")
    seq = []
    for b, e, name in sc.month_blocks(doc):
        inside = doc.rfind('<details class="mdone">', 0, b) > doc.rfind("</details>", 0, b)
        seq.append((name, sc.is_open(doc[b:e]), inside))
    opens = [n for n, o, _i in seq if o]
    seen_done = False
    for name, op, inside in seq:
        if op and seen_done:
            bad.append(f"/calendar: {name} still has an open goal date but sits below a decided month")
        if not op:
            seen_done = True
            if not inside:
                bad.append(f"/calendar: {name} has no open goal date and is not folded")
        elif inside:
            bad.append(f"/calendar: {name} has an open goal date but is folded")
    if opens != sorted(opens, key=sc.month_key):
        bad.append(f"/calendar: open months out of date order: {opens}")
    about = doc.find('id="about-this-calendar"')
    last = max((e for _b, e, _n in sc.month_blocks(doc)), default=0)
    if about < 0 or about < last:
        bad.append("/calendar: no 'About this calendar' after the months")
    else:
        rest = doc[about:]
        for what, pat in (("the explainer", r'class="explainer"'), ("the subscribe box", r"<!--SUBSCRIBE:BEGIN-->"),
                          ("the heat map", r'class="hmap"')):
            if re.search(pat, doc) and not re.search(pat, rest):
                bad.append(f"/calendar: {what} is not in 'About this calendar'")
    for what, pat in (("the subscribe box", r"<!--SUBSCRIBE:BEGIN-->"), ("the heat map", r'class="hmap"')):
        if not re.search(pat, doc):
            bad.append(f"/calendar: {what} is gone")
    for sm in re.finditer(r'<details class="mdone"><summary>([A-Za-z]+ \d{4})(\s*)<span>(\d+) dates?, (.*?)</span>'
                          r'</summary>(.*?)</details>', doc, re.S):
        n = len(re.findall(r'<a class="row"', sm.group(5)))
        wd = len(re.findall(r'<a class="row"[^>]*\bdata-wd="1"', sm.group(5)))
        want = "all decided" if not wd else f"{n - wd} decided, {wd} withdrawn"
        if not sm.group(2):
            bad.append(f"/calendar: the {sm.group(1)} summary runs the month into its count for a screen reader")
        if int(sm.group(3)) != n or sm.group(4) != want:
            bad.append(f"/calendar: {sm.group(1)} says '{sm.group(3)} dates, {sm.group(4)}'; it holds {n}, {want}")
    if re.search(r'<a class="row"[^>]*href="/fda-decision/[^"]+"><div class="t">[^<]*? · \d{4}-\d{2}-\d{2} · <span', doc):
        bad.append("/calendar: a decided row uses the '· ✓ Approved' template")
    if re.search(r"API dataset|no row in (?:the|our) API|our API", doc):
        bad.append("/calendar: the page still describes our API dataset")
    if sc.B_ROW.search(doc):
        bad.append("/calendar: a decided row uses the '· ✓ Approved' template")
    for m in sc.A_ROW.finditer(doc):
        body = m.group(3).strip()
        if re.match(r"[,;:]", body):
            bad.append(f"/calendar {m.group(2)}: name opens with '{body[:12]}'")
        if re.search(r"\s[-\u2013\u2014]\s*$", re.sub(r"<[^>]+>", "", body)):
            bad.append(f"/calendar {m.group(2)}: name ends with a dash: '{body[-30:]}'")
        if "<" not in body and body.partition(": ")[0].endswith("\u2026"):
            bad.append(f"/calendar {m.group(2)}: the drug name is cut: '{body.partition(': ')[0]}'")
        bare = re.sub(r"<[^>]+>", "", body).rstrip(" ,;:")
        name = sc.page_name(m.group(2))
        if name and len(name) > len(bare) >= 6 and name.startswith(bare) and (
                name[len(bare)].isalnum() or bare.count("(") > bare.count(")")):
            bad.append(f"/calendar {m.group(2)}: '{bare}' is cut from '{name}'")
    print(f"/calendar: {len(seq)} month(s), {len(opens)} open first")
    if bad:
        for b in bad[:30]:
            print("  FAIL " + b)
        print("  fix: python shape_calendar.py --undo && python inject_calendar_explainer.py && python shape_calendar.py "
              "&& python inject_mobile_polish.py")
        sys.exit(1)
    print("  PASS: the calendar opens on its open months, folds the decided ones and keeps its notes at the end")


if __name__ == "__main__":
    main()
