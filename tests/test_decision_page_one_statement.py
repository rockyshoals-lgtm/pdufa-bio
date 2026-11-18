# -*- coding: utf-8 -*-
"""test_decision_page_one_statement.py -- a decision page states its decision once, gives the event's own move with
what it is measured on, and says what it was verified against, on every page.

Design red team 2026-11-18 (change 10). GSK's Nelkarmi page stated the approval about nine times (a summary paragraph
the narrative repeated in full, and "Was Nelkarmi (neladalkib) approved by the FDA?" next to "Was neladalkib approved
by the FDA?"), gave the run-up and the cohort's typical move but not the event's own move, and only 66 of 483
decision pages carried the "Verified against" line (51 the first-recorded line). This fails if:

  1. a decision page lacks the Verified-against line or the first-recorded line;
  2. a line built from the page's own sources names an FDA action day the page holds no FDA record for (an FDA-record
     line, the FDA's letter card, or a Drugs@FDA / FDA-letter validation), or a day other than that record's (a
     Drugs@FDA validation holds the FDA's day only when its action date is the page's own day);
     a page whose outcome is inferred from price does not say so;
  3. a page whose event the run-up study measured lacks "Decision-day move" with the study's figure, or any
     "Decision-day move" row lacks the "Move measured on" row (with the study's eve close when it measured it);
  4. a page keeps a summary paragraph under its banner that says nothing the rest of the page does not;
  5. a page's FAQ asks whether the decision was an approval twice, or its FAQPage JSON-LD differs from its questions.
     a page that cites a source (an FDA record, the FDA's letter card, a filing or a primary-source link) is told
     its outcome is inferred or that it cites nothing;
PLANT=fda claims an FDA day on an inferred page, PLANT=move drops GSK-2026-11-17's basis row, PLANT=faq repeats a
question, PLANT=cite tells CORT-2025-12-31 it has no source; each must FAIL.

    python tests/test_decision_page_one_statement.py
"""
import csv
import glob
import html
import io
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
sys.path.insert(0, HERE)
import dedupe_decision_summary as dd  # noqa: E402
import inject_verified_against as iva  # noqa: E402
import sync_decision_runup_chip as sdr  # noqa: E402

APPROVAL_Q = re.compile(r"^(?:Was|Did) (?!.*\balso\b).*\bapproved\b")


def main():
    plant = os.environ.get("PLANT", "")
    src = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8", errors="replace").read()
    rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    owned = {f"{str(r.get('t') or '').upper()}-{str(r['dcd'])[:10]}" for r in rows
             if r.get("type") == "PDUFA" and str(r.get("st")) == "Decided" and r.get("dcd")}
    fig, eves = sdr.study_figures(), sdr.study_eves()
    bad, n, own_lines, moves = [], 0, 0, 0
    for p in sorted(glob.glob(os.path.join(SITE, "fda-decision", "*", "index.html"))):
        slug = os.path.basename(os.path.dirname(p))
        tk, day = slug.split("-", 1)
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        n += 1
        if plant == "move" and slug == "GSK-2026-11-17":
            doc = sdr.BASIS_ROW.sub("", doc, count=1)
        if plant == "faq" and slug == "GSK-2026-11-17":
            doc = doc.replace("<h3", "<h3>Was Nelkarmi (neladalkib) approved by the FDA?</h3><h3", 1)
        # 1
        v = re.search(re.escape(iva.B) + "(.*?)" + re.escape(iva.E), doc, re.S)
        if not v:
            bad.append(f"/fda-decision/{slug}: no Verified-against line")
        if "<!--FIRSTREC:BEGIN-->" not in doc:
            bad.append(f"/fda-decision/{slug}: no first-recorded line")
        # 2
        val = iva._kv(doc, "Validation") or ""
        if v and slug not in owned:
            own_lines += 1
            text = html.unescape(re.sub(r"<[^>]+>", "", v.group(1)))
            if plant == "fda" and val.startswith("Outcome consistent with price"):
                text = "Verified against: FDA action day May 1, 2025 (FDA letter)."
            claim = re.search(r"FDA action day ((?:" + iva.MONTHS + r") \d{1,2}, \d{4})", text)
            rec, crl, daf, let = (iva.FDAREC.search(doc), iva.CRLSRC.search(doc), iva.DAF.search(val),
                                  iva.LETTER.search(val))
            held = None
            if rec:
                held = rec.group(1)
            elif crl:
                card = re.sub(r"<[^>]+>", "", crl.group(1))
                m = (re.search(r"the FDA acted on ((?:" + iva.MONTHS + r") \d{1,2}, \d{4})", card)
                     or re.search(r"dated ((?:" + iva.MONTHS + r") \d{1,2}, \d{4})", card))
                held = m.group(1) if m else None
            elif daf:
                # a Drugs@FDA date names the FDA's day only when it is the page's day (AMRX-2025-01-23 holds Jan 28)
                held = iva.pretty(daf.group(3)) if daf.group(3) == day else None
            elif let:
                held = let.group(2)
            if claim and claim.group(1) != held:
                bad.append(f"/fda-decision/{slug}: its Verified-against line names FDA action day {claim.group(1)}; the "
                           f"page's own FDA record holds {held or 'none'}")
            # red team: CORT-2025-12-31 shows the FDA's CRL card and ALVO-2025-11-02 an SEC filing, yet both were
            # told the outcome was inferred, "not taken from an FDA record or a company filing"
            ps = (re.search(r'<div class="kv"><span>Primary source</span><b>(.*?)</b></div>', doc, re.S)
                  or re.search(r'>Primary source: (.*?)</p>', doc, re.S))
            cited = bool(rec or crl or iva.SEC.search(val) or daf or let
                         or (ps and re.search(r'<a href="https?://', ps.group(1))))
            if plant == "cite" and slug == "CORT-2025-12-31":
                text = "Verified against: no primary source yet. The outcome shown is inferred from the stock's price move."
            if val.startswith("Outcome consistent with price") and not cited and "inferred" not in text:
                bad.append(f"/fda-decision/{slug}: the outcome is inferred from price and the line does not say so")
            if cited and ("inferred from the stock" in text or "no source for this decision is cited" in text):
                bad.append(f"/fda-decision/{slug}: the page cites a source, and its Verified-against line says it has "
                           "none")
        # 3
        run, mv = sdr.expected(fig, tk, day)
        row = (re.search(r'<div class="kv"><span>Decision-day move</span><b>([^<]*)</b></div>', doc)
               or re.search(r'<tr><td[^>]*>Decision-day move</td><td class="lit"[^>]*>([^<]*)</td></tr>', doc))
        basis = (re.search(r'<div class="kv"><span>Move measured on</span><b>([^<]*)</b></div>', doc)
                 or re.search(r'<tr><td[^>]*>Move measured on</td><td class="lit"[^>]*>([^<]*)</td></tr>', doc))
        if mv is not None and (tk, day) in eves:
            moves += 1
            if not row or row.group(1) != mv:
                bad.append(f"/fda-decision/{slug}: key facts lack the event's decision-day move {mv} "
                           f"(shows {row.group(1) if row else 'none'})")
            elif not basis or f"against the {eves[(tk, day)]} close" not in basis.group(1):
                bad.append(f"/fda-decision/{slug}: the decision-day move does not say it is measured against the "
                           f"{eves[(tk, day)]} close")
        elif row and not basis:
            bad.append(f"/fda-decision/{slug}: a decision-day move with no 'Move measured on' row")
        # 4
        if dd.redundant(doc):
            bad.append(f"/fda-decision/{slug}: the summary under the banner says nothing the page does not")
        # 5
        f = re.search(r"<!--DFAQ:BEGIN-->(.*?)<!--DFAQ:END-->", doc, re.S)
        if f:
            qs = [html.unescape(q) for q in re.findall(r"<h3[^>]*>([^<]*)</h3>", f.group(1))]
            if sum(1 for q in qs if APPROVAL_Q.match(q)) > 1:
                bad.append(f"/fda-decision/{slug}: the FAQ asks whether it was approved more than once")
            ld = re.search(r'<script type="application/ld\+json">(.*?)</script>', f.group(1), re.S)
            if ld:
                lq = [q["name"] for q in json.loads(ld.group(1)).get("mainEntity", [])]
                if lq != qs:
                    bad.append(f"/fda-decision/{slug}: the FAQPage structured data differs from the questions shown")
    print(f"{n} decision pages: {own_lines} lines from their own sources, {moves} with the study's move")
    if bad:
        for b in bad[:30]:
            print("  FAIL " + b)
        if len(bad) > 30:
            print(f"  ... and {len(bad) - 30} more")
        print("  fix: python sync_decision_runup_chip.py && python build_decision_faq.py && python "
              "inject_verified_against.py && python inject_first_recorded.py && python dedupe_decision_summary.py")
        sys.exit(1)
    print("  PASS: one statement, the event's own move with its basis, and a verified-against line on every page")


if __name__ == "__main__":
    main()
