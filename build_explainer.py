# -*- coding: utf-8 -*-
"""build_explainer.py -- say what a PDUFA date is, on the page that uses the word.

The homepage lede reads "every upcoming PDUFA date, the stock's run-up history, market-cap cohort
base rates". Every one of those is jargon, and the site never once defines the term it is named
after. A retail visitor arriving from "MRNA FDA approval date" has to already know what a PDUFA is
to understand what they are looking at, which is the single largest reason a first-time visitor
leaves.

It is also a search opportunity we were declining. "What is a PDUFA date" is a real, high-volume
informational query with weak competition, and we are better placed to answer it than anyone: we
have 1,827 decisions of evidence for what actually happens around one. Answering it in plain
language, with FAQ structured data, targets that query and warms up a reader for the calendar.

Written for someone who has never heard the term, at roughly a 9th-grade reading level, with no
prediction and no advice. The numbers come from the study file so they cannot drift from the
published statistics.

    python build_explainer.py [--dry-run]
"""
import argparse, datetime as dt, html, json, os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
HOME = os.path.join(SITE, "index.html")
STATS = os.path.join(HERE, "runup_study_stats.json")
B, E = "<!--EXPLAIN:BEGIN-->", "<!--EXPLAIN:END-->"

QA = [
    ("What is a PDUFA date?",
     "It is the deadline the FDA sets for itself to decide whether to approve a new medicine. "
     "When a drug company applies, it pays a fee, and in return the FDA commits to answering by a "
     "specific day. That day is the PDUFA date. The name comes from the Prescription Drug User Fee "
     "Act, the 1992 law that set the system up."),
    ("What actually happens on the day?",
     "One of two things. The FDA approves the drug, or it sends the company a Complete Response "
     "Letter, usually shortened to CRL, which is a rejection that lists what would need to be fixed. "
     "A CRL is not always permanent: companies often fix the problem and reapply. The FDA can also "
     "decide early, or miss its own deadline entirely, and it does not have to explain a delay."),
    ("Does the stock usually move before or after the decision?",
     "Measured across {n:,} decisions since {y}, most of the movement happens in the months before "
     "the date rather than on it. The median stock rose {peak:.1f}% at its best point in the 120 "
     "trading days before the decision, but was only {t1:.1f}% higher on the day before it. In "
     "other words the typical run-up was largely given back before the answer arrived. That is what "
     "happened historically, across the whole group. It is not a prediction about any one stock."),
    ("What is an advisory committee, and does it decide?",
     "It is a panel of outside experts the FDA can convene to discuss a hard application in public. "
     "They vote, but the vote is advice. The FDA usually follows it and is not required to. A "
     "negative vote is a serious signal, not a verdict."),
    ("What does a trial readout mean?",
     "It is the moment a company reports results from a clinical trial. Readouts happen years "
     "before an FDA decision and are often the bigger share-price event, because they are the first "
     "time anyone outside the trial learns whether the drug worked."),
    ("Where do these numbers come from?",
     "FDA publications, company filings with the SEC, company press releases and "
     "ClinicalTrials.gov, with prices measured from daily closing data. Every date and outcome on "
     "this site links to the document it came from. Where we have inferred something rather than "
     "sourced it, the page says so."),
]


def esc(s):
    return html.escape(str(s), quote=True)


def build(stats):
    n = stats.get("n_events", 0)
    y = str(stats.get("date_min", ""))[:4]
    peak = stats.get("T-120_peak_median_pct", 0.0)
    t1 = stats.get("T-120_T-1_median_pct", 0.0)
    qa = [(q, a.format(n=n, y=y, peak=peak, t1=t1)) for q, a in QA]

    items = "".join(
        f'<details style="border-top:1px solid var(--line);padding:11px 0">'
        f'<summary style="cursor:pointer;font-weight:600;color:#eef4fc;font-size:14.5px;'
        f'list-style:none">{esc(q)}</summary>'
        f'<p style="margin:8px 0 0;font-size:14px;line-height:1.75;color:var(--mut2)">'
        f'{esc(a)}</p></details>' for q, a in qa)

    ld = {"@context": "https://schema.org", "@type": "FAQPage",
          "mainEntity": [{"@type": "Question", "name": q,
                          "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in qa]}

    return (
        f'{B}<section class="explain" style="margin:22px 0 8px">'
        f'<div style="background:var(--card);border:1px solid var(--line);border-radius:14px;'
        f'padding:16px 18px">'
        f'<h2 style="font-size:17px;margin:0 0 7px">New here? Start with this.</h2>'
        f'<p style="font-size:15px;line-height:1.75;color:#dce7f7;margin:0 0 4px">'
        f'A <b style="color:#eef4fc">PDUFA date</b> is the deadline the FDA sets for itself to '
        f'decide whether to approve a new medicine. On that day the drug is either approved or sent '
        f'back with a rejection letter. This site tracks every one of those deadlines, what the '
        f'stock did on the way in, and what the FDA actually decided.</p>'
        f'<div style="margin-top:6px">{items}</div>'
        f'<p style="font-size:11.5px;color:var(--mut2);margin:12px 0 0;line-height:1.6">'
        f'Informational only, and not investment advice. pdufa.bio is not affiliated with the FDA.'
        f'</p></div></section>'
        f'<script type="application/ld+json">{json.dumps(ld, separators=(",", ":"))}</script>{E}')


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    stats = json.load(open(STATS, encoding="utf-8")) if os.path.exists(STATS) else {}
    if not stats.get("n_events"):
        print("no study stats; refusing to publish an explainer quoting numbers it cannot source")
        return

    block = build(stats)
    html_doc = open(HOME, encoding="utf-8", errors="replace").read()

    if B in html_doc:
        html_doc = re.sub(re.escape(B) + ".*?" + re.escape(E), lambda _: block, html_doc, flags=re.S)
        where = "refreshed"
    else:
        # Below the board, not above it. Someone who searched for a specific ticker wants the board
        # first; the explainer is for the visitor who scrolls because they did not understand it.
        anchor = '<div class="legal"'
        if anchor not in html_doc:
            anchor = "<footer"
        if anchor not in html_doc:
            print("could not find an insertion point on the homepage"); return
        html_doc = html_doc.replace(anchor, block + anchor, 1)
        where = "inserted"

    if not a.dry_run:
        open(HOME, "w", encoding="utf-8").write(html_doc)
    print(f"explainer {where}: {len(QA)} Q&A, FAQ schema, quoting {stats['n_events']:,} events"
          + (" [dry run]" if a.dry_run else ""))


if __name__ == "__main__":
    main()
