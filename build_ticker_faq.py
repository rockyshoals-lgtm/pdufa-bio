# -*- coding: utf-8 -*-
"""build_ticker_faq.py -- answer the questions people actually type, in a form Google can lift.

The competitive read is that the hub-page war ("fda calendar 2026") is crowded and we are behind on
authority, while the long tail is empty: no competitor has a per-ticker URL at all, because their
event data lives behind query parameters. The queries nobody is contesting look like:

    when is the SLS phase 3 readout        <- Google's own People-Also-Ask question
    VKTX PDUFA date
    Replimune FDA decision date

Those are questions. Google surfaces question-shaped content through PAA boxes, and PAA eligibility
is driven by FAQPage structured data plus an answer written to be extracted. Zero of our 209 ticker
hubs had FAQPage on them.

Every answer here is generated from data we already hold and can show: the next catalyst and its
date precision, the decision history with outcomes, and the measured run-up. Nothing is written by
hand per ticker, so this cannot drift from the pages it describes.

Two rules that matter more than the schema:

  * ANSWER FIRST, EVIDENCE SECOND. Both Google and the AI assistants lift the first clean sentence.
    A paragraph that warms up before answering gets skipped.
  * NEVER ANSWER WHAT WE DO NOT KNOW. A ticker with no dated catalyst gets an answer that says so.
    Inventing a plausible date is how a site loses the trust that is the entire moat here.

    python build_ticker_faq.py [--dry-run] [--limit N]
"""
import argparse, datetime as dt, glob, html, json, os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")
STATS = os.path.join(HERE, "runup_study_stats.json")
B, E = "<!--TICKERFAQ:BEGIN-->", "<!--TICKERFAQ:END-->"

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]


def esc(s):
    return html.escape(str(s or ""), quote=True)


def pretty(d, precision):
    """A date rendered at the precision we actually have. Never invent a day."""
    y, m, day = int(d[:4]), int(d[5:7]), int(d[8:10])
    if precision == "day":
        return f"{MONTHS[m - 1]} {day}, {y}"
    if precision == "month":
        return f"{MONTHS[m - 1]} {y}"
    return f"Q{(m - 1) // 3 + 1} {y}"


def company_of(html_doc, tk):
    m = re.search(r"<h1[^>]*>(.*?)</h1>", html_doc, re.S)
    if not m:
        return tk
    name = html.unescape(re.sub(r"<[^>]+>", " ", m.group(1)))
    name = re.sub(r"\s+", " ", name).strip()
    name = re.split(r"\s+FDA\b|\s*\(", name)[0].strip()
    return name or tk


def faqs(tk, company, rows, decisions, runup, cohort):
    today = dt.date.today().isoformat()
    out = []

    # 1. The timing question. This is the query.
    upcoming = sorted([r for r in rows if (r.get("d") or "") >= today
                       and str(r.get("st") or "").lower() not in ("decided",)],
                      key=lambda r: r["d"])
    if upcoming:
        n = upcoming[0]
        when = pretty(n["d"], n.get("dp") or "day")
        conf = {"day": "a confirmed date",
                "month": "known to the month only",
                "quarter": "known to the quarter only"}.get(n.get("dp") or "day", "")
        extra = ""
        if len(upcoming) > 1:
            extra = f" {len(upcoming)} catalysts are scheduled in total."
        out.append((
            f"When is the next FDA decision or readout for {company} ({tk})?",
            f"{when}. {company} has a {n.get('type', 'catalyst')} for "
            f"{n.get('name') or 'an undisclosed program'}, and that date is {conf}."
            f"{extra} Dates are taken from FDA notices, company filings or ClinicalTrials.gov, and "
            f"we do not publish a specific day when the source only gives a month or a quarter."))
    else:
        out.append((
            f"When is the next FDA decision for {company} ({tk})?",
            f"{company} has no dated FDA catalyst on our calendar right now. That means no "
            f"scheduled decision or readout date has been published in a source we can point to, "
            f"not that none exists. We would rather say that than estimate one."))

    # 2. History. Answers "has X been approved before".
    if decisions:
        ap = sum(1 for _, _, o in decisions if o == "ap")
        crl = len(decisions) - ap
        last_t, last_d, last_o = decisions[0]
        out.append((
            f"Has {company} ({tk}) had an FDA decision before?",
            f"Yes, {len(decisions)} in our archive: {ap} approval(s) and {crl} Complete Response "
            f"Letter(s). The most recent was on {pretty(last_d, 'day')} and was "
            f"{'an approval' if last_o == 'ap' else 'a Complete Response Letter'}. Each one has its "
            f"own page with the source document and the share-price reaction we measured."))

    # 3. The run-up question, answered with measurement rather than opinion.
    if runup:
        out.append((
            f"How has {tk} stock moved into its FDA decisions?",
            f"Measured from this company's own daily closing prices: {runup} These are historical "
            f"measurements of what already happened, not forecasts, and we publish no price targets "
            f"or probability of approval."))
    elif cohort:
        out.append((
            f"How do stocks like {tk} move into an FDA decision?",
            f"We have no measured history for {tk} itself. Across the whole study of "
            f"{cohort.get('n_events', 0):,} FDA decisions, the median stock rose "
            f"{cohort.get('T-120_peak_median_pct', 0):.1f}% at its best point in the 120 trading "
            f"days before the decision, but was only "
            f"{cohort.get('T-120_T-1_median_pct', 0):.1f}% higher the day before it. Most of the "
            f"move happened before the answer arrived and was largely given back."))

    # 4. Provenance. The differentiator, stated plainly.
    out.append((
        f"Where does this {tk} data come from?",
        f"FDA publications, company filings with the SEC, company press releases and "
        f"ClinicalTrials.gov, with share prices measured from daily closing data. Every date and "
        f"outcome links the document it came from. Where an outcome was inferred from the price "
        f"reaction rather than read from a filing, the page says so on its face."))

    return out


def render(items):
    body = "".join(
        f'<details style="border-top:1px solid var(--line);padding:11px 0">'
        f'<summary style="cursor:pointer;font-weight:600;color:#eef4fc;font-size:14px;'
        f'list-style:none">{esc(q)}</summary>'
        f'<p style="margin:8px 0 0;font-size:13.5px;line-height:1.75;color:var(--mut2)">'
        f'{esc(a)}</p></details>' for q, a in items)
    ld = {"@context": "https://schema.org", "@type": "FAQPage",
          "mainEntity": [{"@type": "Question", "name": q,
                          "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in items]}
    return (f'{B}<section style="margin:26px 0">'
            f'<h2 style="font-size:17px;margin:0 0 6px">Common questions</h2>{body}'
            f'</section>'
            f'<script type="application/ld+json">{json.dumps(ld, separators=(",", ":"))}</script>'
            f'{E}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int)
    a = ap.parse_args()

    src = open(DATASET, encoding="utf-8", errors="replace").read()
    rows = json.loads(re.search(r"export default (\[.*\])", src, re.S).group(1))
    by_tk = {}
    for r in rows:
        if r.get("t"):
            by_tk.setdefault(str(r["t"]).upper(), []).append(r)

    cohort = {}
    if os.path.exists(STATS):
        try:
            cohort = json.load(open(STATS, encoding="utf-8"))
        except Exception:
            pass

    dec_by_tk = {}
    darch = os.path.join(SITE, "decisions", "index.html")
    if os.path.exists(darch):
        dh = open(darch, encoding="utf-8", errors="replace").read()
        seen = set()
        for m in re.finditer(r'href="/fda-decision/([A-Z]{1,6})-(\d{4}-\d{2}-\d{2})"', dh):
            key = (m.group(1), m.group(2))
            if key in seen:
                continue
            seen.add(key)
            tail = dh[m.end():m.end() + 160].lower()
            dec_by_tk.setdefault(m.group(1), []).append(
                (m.group(1), m.group(2), "crl" if ("crl" in tail or "complete response" in tail)
                 else "ap"))
    for v in dec_by_tk.values():
        v.sort(key=lambda x: x[1], reverse=True)

    pages = sorted(glob.glob(os.path.join(SITE, "ticker", "*", "index.html")))
    if a.limit:
        pages = pages[:a.limit]

    n = 0
    for p in pages:
        tk = os.path.basename(os.path.dirname(p))
        doc = open(p, encoding="utf-8", errors="replace").read()

        # Pull the measured run-up sentence straight off the page, so the FAQ can never disagree
        # with the table above it.
        # Unescape after stripping tags. The page text is already HTML-escaped, and escaping it a
        # second time on the way out rendered "company&#x27;s" as literal punctuation-gibberish in
        # both the visible answer and the JSON-LD an assistant would quote.
        runup = ""
        m = re.search(r"Median across these (\d+) decisions:.*?</div>", doc, re.S)
        if m:
            runup = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m.group(0)))).strip()
            runup = runup.split("A median over")[0].strip()
        elif "Since its T-120 baseline" in doc:
            mm = re.search(r"Since its T-120 baseline.*?</div>", doc, re.S)
            if mm:
                runup = html.unescape(
                    re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", mm.group(0)))).strip()[:320]

        items = faqs(tk, company_of(doc, tk), by_tk.get(tk, []), dec_by_tk.get(tk, []),
                     runup, cohort)
        block = render(items)

        if B in doc:
            doc = doc.split(B, 1)[0] + block + doc.split(E, 1)[1]
        else:
            anchor = '<div class="legal"'
            if anchor not in doc:
                anchor = "<footer"
            if anchor not in doc:
                continue
            doc = doc.replace(anchor, block + anchor, 1)

        if not a.dry_run:
            open(p, "w", encoding="utf-8").write(doc)
        n += 1

    print(f"FAQ blocks on {n} ticker hub(s), FAQPage schema included"
          + (" [dry run]" if a.dry_run else ""))


if __name__ == "__main__":
    main()
