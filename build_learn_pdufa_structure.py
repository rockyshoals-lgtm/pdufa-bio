# -*- coding: utf-8 -*-
"""/learn/what-is-a-pdufa-date restructured into five H2 sections. Audit 09-14 item 7b.

WHY. Our citation SHARE is falling on the two queries this site exists to own, while volume
grows: `pdufa date` 18.23% -> 16.10% and `fda calendar 2026` 30.83% -> 28.96% in six days. The
auditor's reading is that the pool is expanding faster than we are holding it, and that the
counter is "the definitional scaffolding Bing's answer box assembles" -- headings that match the
shape of the question, so an extractive engine can lift a clean answer per section.

The page was already accurate. It was organised as five arbitrary headings, one of which was
"What happens to the stock?", which is trade framing this page should not carry: there is a
separate page for that question and this one is a definition.

FIVE SECTIONS, per the 09-10b item-4 spec:
    1. What a PDUFA date is
    2. Why PDUFA dates exist: the Prescription Drug User Fee Act
    3. How the review timeline works
    4. What the FDA can do on the date
    5. Why the date matters

MARKER-BOUNDED between <!--LEARN5:BEGIN--> and <!--LEARN5:END-->, and it deliberately does NOT
touch the lede or the FAQ. The lede carries the citable blockquote with the live timing
statistic, which sync_learn_timing.py rewrites by pattern and which
tests/test_cross_surface_values.py compares against /calendar and the study page. Regenerating
the whole page would put that sentence under two owners, which is the defect this week was
about.

    python build_learn_pdufa_structure.py [--dry-run]
"""
import argparse
import io
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(HERE, "pdufa_site_src", "learn", "what-is-a-pdufa-date", "index.html")
B, E = "<!--LEARN5:BEGIN-->", "<!--LEARN5:END-->"

SECTIONS = B + (
    '<h2 id="what">What a PDUFA date is</h2>'
    "<p class='sub'>A PDUFA date is the date by which the FDA has committed to complete its "
    "review of a drug application and issue a decision. It is a <b>goal date, not a deadline in "
    "law and not an approval date</b>. The agency can act before it, can extend it, and on the "
    "date itself can say no as easily as yes. Nothing about a PDUFA date implies an outcome.</p>"

    '<h2 id="why">Why PDUFA dates exist: the Prescription Drug User Fee Act</h2>'
    "<p class='sub'>Before 1992 the FDA had no funded commitment to review drug applications "
    "within a set time, and reviews could run for years. The <b>Prescription Drug User Fee "
    "Act</b>, enacted in 1992 and reauthorised by Congress roughly every five years since, set "
    "up a trade: drug companies pay user fees, and in exchange the FDA commits to performance "
    "goals for how quickly it completes reviews. A PDUFA date is one of those goals, applied to "
    "a single application. The money funds reviewer capacity; the goal dates are what the public "
    "gets back for it.</p>"

    '<h2 id="timeline">How the review timeline works</h2>'
    "<p class='sub'>When a company submits a New Drug Application (NDA) or Biologics License "
    "Application (BLA), the FDA first decides whether to <i>file</i> it for review, which takes "
    "about 60 days. The goal clock for a new molecular entity runs from that filing date, not "
    "from the day the company submitted. From filing, the goal is about <b>ten months under "
    "standard review</b> and about <b>six months under priority review</b>, which is granted "
    "when a drug may offer a significant improvement over available options. If the company "
    "sends substantial new information late in the cycle, the FDA can treat it as a "
    "<b>major amendment</b> and extend the goal date, usually by three months. Companies "
    "normally disclose the date in a press release or an SEC filing, which is where the dates on "
    "this site come from.</p>"

    '<h2 id="decide">What the FDA can do on the date</h2>'
    "<div class='card'><div class='kv'><span>Approval</span><b>The drug may be marketed in the "
    "United States</b></div><div class='kv'><span>Complete Response Letter</span><b>Not approved "
    "as submitted; the letter sets out what must be resolved</b></div><div class='kv'>"
    "<span>Extension</span><b>The review period is pushed back, commonly by three months</b>"
    "</div><div class='kv'><span>No action on the day</span><b>The goal is missed and the "
    "application stays under review</b></div></div>"
    "<p class='sub' style=\"margin-top:10px\">A Complete Response Letter is not a rejection of "
    "the drug forever: companies frequently resubmit, and a resubmission starts a new review "
    "clock of its own, two or six months depending on what changed. "
    "<a href=\"/learn/what-is-a-crl\">More on Complete Response Letters</a>.</p>"

    '<h2 id="matters">Why the date matters</h2>'
    "<p class='sub'>It is the day the answer becomes public. For patients and clinicians waiting "
    "on a treatment, the PDUFA date is when they find out whether it will be available; for the "
    "company it is the date around which manufacturing, launch and staffing are planned. It is "
    "also the only scheduled point in a long private process: almost everything else about an "
    "FDA review happens out of view, and the goal date is the one part of the calendar that is "
    "announced in advance.</p>"
    "<p class='sub'>Because it is a goal rather than a guarantee, the useful question is how "
    "often it holds. We publish that from our own sourced archive rather than asserting it: see "
    "<a href=\"/research/fda-decision-timing\">does the FDA decide on the PDUFA date?</a>, which "
    "counts every 2026 decision where we hold both the goal date and the actual action date with "
    "a primary source for each. This site publishes dates, sources and historical statistics; it "
    "does not publish approval odds, and nothing here is investment advice.</p>"
    '<a class="cta" href="/calendar"><b>See the live FDA PDUFA calendar &rarr;</b></a>'
) + E


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    if not os.path.isfile(PAGE):
        print("  page not found")
        return 1
    doc = io.open(PAGE, encoding="utf-8", errors="replace").read()
    orig = doc

    if B in doc and E in doc:
        doc = re.sub(re.escape(B) + r".*?" + re.escape(E), lambda m: SECTIONS, doc, flags=re.S)
    else:
        # first run: replace everything from the first <h2> up to (not including) the FAQ
        m_first = re.search(r"<h2[^>]*>", doc)
        m_faq = re.search(r"<h2[^>]*>\s*FAQ\s*</h2>", doc)
        if not (m_first and m_faq):
            print("  could not locate the section block (no <h2> or no FAQ heading)")
            return 1
        doc = doc[:m_first.start()] + SECTIONS + doc[m_faq.start():]

    # the citable blockquote and the timing sentence must survive untouched
    for must in ("data-citable", "came before the goal date"):
        if must not in doc:
            print(f"  ABORT: '{must}' disappeared; refusing to write")
            return 1

    heads = [re.sub(r"<[^>]+>", "", h) for h in re.findall(r"<h2[^>]*>(.*?)</h2>", doc, re.S)]
    print("  H2 sections now:")
    for h in heads:
        print(f"     - {h.strip()[:70]}")
    if "What happens to the stock?" in doc:
        print("  WARNING: the trade-framing section is still present")

    if doc != orig and not a.dry_run:
        io.open(PAGE, "w", encoding="utf-8").write(doc)
        print(f"\n  written ({len(orig)} -> {len(doc)} bytes)")
    elif a.dry_run:
        print("\n  --dry-run, nothing written")
    else:
        print("\n  already current")
    return 0


if __name__ == "__main__":
    sys.exit(main())
