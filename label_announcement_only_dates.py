# -*- coding: utf-8 -*-
"""label_announcement_only_dates.py -- a decision page whose FDA action day is not on the FDA's record yet
states the announcement day AS the announcement day (2026-11-17 currency audit).

SMMT-2026-11-15, CYTK-2026-11-16 and TEVA-2026-11-16 carried, on the same page,
  "Verified against: FDA action day not yet posted on Drugs@FDA · Announcement November 16, 2026 (...)"
and, above it,
  "<h1>CYTK FDA decision: Nov 16, 2026</h1>"  ·  key facts "FDA decision date 2026-11-16"  ·  chart "FDA decision 11/16/26."
The 16th is the day the sponsor announced; the FDA's action may have come earlier (a weekend, a letter dated the
day before). The page asserted a fact its own Verified line says we do not have.

On every /fda-decision page whose Verified line says the FDA action day is not yet posted:
  * h1   "FDA decision: Nov 16, 2026"            -> "FDA decision: announced Nov 16, 2026"
  * kv   "FDA decision date | 2026-11-16"        -> "FDA decision date | not yet posted on Drugs@FDA" + "Announced | 2026-11-16"
  * chart caption "FDA decision 11/16/26."       -> "Decision announced 11/16/26."
Each change carries an <!--ANNONLY--> marker. When the Verified line later names the FDA record (sync_fda_action_dates
fills it), the page is put back to the canonical form, and fix_decision_h1_action_date / fix_chart_captions then state
the FDA day. Runs after inject_verified_against.py and before fix_decision_h1_action_date.py. Idempotent.
Guard: tests/test_announcement_only_dates.py. Facts only; not investment advice.

2026-11-25 (currency red team): the "after the close" note lived only in the labelled form, so once the FDA's own day
reached the record (CAPR-2026-11-20: FDA letter dated Nov 20, Capricor's release 7:55 PM ET that evening) the restore
to canonical form dropped it. The home card then called the Nov 20 close "reaction day up 1%", a close taken before the
news. The note now survives in canonical form as its own row, <!--ANNLATE-->Announced | YYYY-MM-DD, after the
close<!--/ANNLATE-->, right after the FDA decision date. Its source is the page itself or the hand-verified ledger
_announced_after_close.json (sponsor release time stamps). Guard: tests/test_decision_timing_current.py.
"""
import glob
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
# 2026-11-17 red team: "not yet posted on Drugs@FDA" was wrong for a device (Drugs@FDA never lists a PMA) and for a
# complete response letter (not a Drugs@FDA action). The line now says what we know: no public FDA record states the day.
NOT_POSTED_RX = re.compile(r"FDA action day (?:not yet posted|not found in a public FDA record)")
KV_TEXT = "not found in a public FDA record"
H1 = re.compile(r'(<h1>[A-Z][A-Z./ ]{0,12} <span class="g">FDA decision</span>: )([A-Z][a-z]{2} \d{1,2}, \d{4})(</h1>)')
H1_DONE = re.compile(r'(<h1>[A-Z][A-Z./ ]{0,12} <span class="g">FDA decision</span>: )<!--ANNONLY-->announced '
                     r'([A-Z][a-z]{2} \d{1,2}, \d{4})(</h1>)')
KV = re.compile(r'<div class="kv"><span>FDA decision date</span><b>(\d{4}-\d{2}-\d{2})</b></div>')
# 2026-11-21: an announcement made after that day's close keeps its note (CAPR-2026-11-20: Capricor, 7:55 PM ET),
# which sync_decision_runup_chip.py and build_home_board.py read so the same day's close is not called the reaction.
KV_DONE = re.compile(r'<!--ANNONLY:KV--><div class="kv"><span>FDA decision date</span><b>(?:not yet posted on Drugs@FDA|not found in a public FDA record)</b></div>'
                     r'<div class="kv"><span>Announced</span><b>(\d{4}-\d{2}-\d{2})(?:, after the close)?</b></div><!--/ANNONLY:KV-->')
AFTER_CLOSE = re.compile(r'<span>Announced</span><b>(\d{4}-\d{2}-\d{2}), after the close</b>')
LATE_ROW = re.compile(r'<!--ANNLATE--><div class="kv"><span>Announced</span><b>\d{4}-\d{2}-\d{2}, after the close</b></div>'
                      r'<!--/ANNLATE-->')
LEDGER = os.path.join(HERE, "_announced_after_close.json")
CAP = re.compile(r"FDA decision (\d{1,2}/\d{1,2}/\d{2})\. ")
CAP_DONE = re.compile(r"<!--ANNONLY-->Decision announced (\d{1,2}/\d{1,2}/\d{2})\. ")


def verified_block(doc):
    m = re.search(r"<!--VERIFIED:BEGIN-->(.*?)<!--VERIFIED:END-->", doc, re.S)
    return m.group(1) if m else ""


def label(doc):
    doc = H1.sub(lambda m: m.group(1) + "<!--ANNONLY-->announced " + m.group(2) + m.group(3), doc, count=1)
    doc = KV.sub(lambda m: ('<!--ANNONLY:KV--><div class="kv"><span>FDA decision date</span><b>' + KV_TEXT +
                            '</b></div><div class="kv"><span>Announced</span><b>' + m.group(1) +
                            '</b></div><!--/ANNONLY:KV-->'), doc, count=1)
    # 2026-11-19: build_decision_page.py now names the chart (design change 12) with an aria-label that repeats the
    # caption, so "FDA decision m/d/yy. " also sits inside that attribute. A comment marker there ends the <svg> tag
    # at its ">" (REGN-2026-11-18 blocked test_accessibility). Inside a tag the phrase is reworded with no marker;
    # the marker goes only on the visible caption text.
    parts = re.split(r"(<[^>]*>)", doc)
    for i, seg in enumerate(parts):
        if seg.startswith("<"):
            if "aria-label=" in seg:
                parts[i] = CAP.sub(lambda m: "Decision announced " + m.group(1) + ". ", seg)
        else:
            parts[i] = CAP.sub(lambda m: "<!--ANNONLY-->Decision announced " + m.group(1) + ". ", seg)
    return "".join(parts)


def after_close_ledger():
    """{page slug: announcement day} for decisions the sponsor made public after that day's close (hand-verified)."""
    try:
        led = json.load(io.open(LEDGER, encoding="utf-8")).get("after_close", {})
        return {k: v["announced"] for k, v in led.items() if re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(v.get("announced")))}
    except Exception:  # noqa: BLE001
        return {}


def keep_late(doc, day):
    """The page says the news came after the close on `day`: on the Announced row when it has one, else in a row of its
    own right after the FDA decision date."""
    if f"<span>Announced</span><b>{day}, after the close</b>" in doc:
        return doc
    if f"<span>Announced</span><b>{day}</b>" in doc:
        return doc.replace(f"<span>Announced</span><b>{day}</b>", f"<span>Announced</span><b>{day}, after the close</b>", 1)
    m = KV.search(doc)
    if not m:
        return doc
    return (doc[:m.end()] + f'<!--ANNLATE--><div class="kv"><span>Announced</span><b>{day}, after the close</b></div>'
            f"<!--/ANNLATE-->" + doc[m.end():])


def unlabel(doc):
    doc = LATE_ROW.sub("", doc)
    doc = H1_DONE.sub(lambda m: m.group(1) + m.group(2) + m.group(3), doc)
    doc = KV_DONE.sub(lambda m: f'<div class="kv"><span>FDA decision date</span><b>{m.group(1)}</b></div>', doc)
    doc = CAP_DONE.sub(lambda m: "FDA decision " + m.group(1) + ". ", doc)
    return doc


def main():
    n_lab = n_un = n_late = 0
    led = after_close_ledger()
    for p in sorted(glob.glob(os.path.join(SITE, "fda-decision", "*", "index.html"))):
        slug = os.path.basename(os.path.dirname(p))
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        if "ANNONLY" not in doc and "ANNLATE" not in doc and slug not in led and not NOT_POSTED_RX.search(doc):
            continue
        base = unlabel(doc)
        new = label(base) if NOT_POSTED_RX.search(verified_block(base)) else base
        # an "after the close" note survives the unlabel/label round trip, and the restore to canonical form
        late = AFTER_CLOSE.search(doc)
        day = late.group(1) if late else led.get(slug)
        if day:
            new = keep_late(new, day)
        if new != doc:
            io.open(p, "w", encoding="utf-8", newline="").write(new)
            if NOT_POSTED_RX.search(verified_block(base)):
                n_lab += 1
                print(f"  labelled announcement-only: {os.path.relpath(p, SITE)}")
            elif "ANNONLY" in doc:
                n_un += 1
                print(f"  FDA day now on record, canonical form restored: {os.path.relpath(p, SITE)}")
            else:
                n_late += 1
                print(f"  announced after the close, noted in key facts: {os.path.relpath(p, SITE)}")
    print(f"announcement-only decision pages labelled: {n_lab}; restored: {n_un}; after-close notes added: {n_late}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
