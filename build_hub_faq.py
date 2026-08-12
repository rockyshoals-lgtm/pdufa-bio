# -*- coding: utf-8 -*-
"""build_hub_faq.py -- FAQPage on every hub, answered with numbers the pages already publish.

2026-08-12 audit, the mechanism proven by our own pages: /drug/rusfertide (363 words, FAQPage)
holds 16.67% AI citation share on its query; /calendar (1,612 words, ranks #1, no FAQPage) earns
zero citations. The unit an engine lifts is one declarative sentence containing a number and a
date. This builder puts that unit on every hub, visible text and FAQPage JSON-LD mirroring each
other exactly.

Two rules keep it honest:

  1. Numbers come from what the page or dataset already states -- the calendar FAQ parses the
     calendar's own lede so the two can never disagree; the decisions FAQ parses the archive's
     own published counts, including the refusal to compute an approval rate over price-inferred
     records. A question we cannot answer from held data is skipped, not padded.
  2. The next-decision answer bakes a real countdown ("in N days"). That sentence changes every
     day, so /calendar and /decisions genuinely change daily and their honest dateModified stops
     reading four days stale next to competitors' "16 hours ago" (audit section 3). This is the
     approved additive change: nothing above the fold, no title, H1, URL or lede touched -- the
     Bing #1 lives on /calendar and stays untouched for four weeks by standing order.

Idempotent via HUBFAQ markers; runs daily after build_hub_lede.

    python build_hub_faq.py [--dry-run]
"""
import argparse, datetime as dt, html, json, os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
BASE = "https://www.pdufa.bio"
B, E = "<!--HUBFAQ:BEGIN-->", "<!--HUBFAQ:END-->"
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]


def pretty(d):
    return f"{MONTHS[int(d[5:7]) - 1]} {int(d[8:10])}, {d[:4]}"


def load_rows():
    src = open(os.path.join(SITE, "api", "v1", "dataset.mjs"),
               encoding="utf-8", errors="replace").read().replace("\x00", "")
    rows, _ = json.JSONDecoder().raw_decode(src[src.find("["):])
    return rows


def read(rel):
    p = os.path.join(SITE, rel, "index.html")
    return (p, open(p, encoding="utf-8", errors="replace").read()) \
        if os.path.exists(p) else (p, None)


def block(url, qa):
    """Visible FAQ section + FAQPage JSON-LD, mirrored, wrapped in markers."""
    vis = ('<section style="max-width:820px;margin:28px auto 0;padding:0 2px">'
           '<h2 style="font-size:17px;margin:0 0 4px">Questions</h2>'
           + "".join(
               f'<h3 style="font-size:14.5px;margin:14px 0 3px">{html.escape(q)}</h3>'
               f'<p style="margin:0;font-size:14px;line-height:1.6;opacity:.85">'
               f'{html.escape(a)}{link}</p>'
               for q, a, link in qa)
           + "</section>")
    ld = ('<script type="application/ld+json">' + json.dumps(
        {"@context": "https://schema.org", "@type": "FAQPage", "url": url,
         "mainEntity": [
             {"@type": "Question", "name": q, "acceptedAnswer":
                 {"@type": "Answer", "text": a}} for q, a, _ in qa]},
        separators=(",", ":")) + "</script>")
    return B + vis + ld + E


def inject(rel, qa, dry):
    p, doc = read(rel)
    if doc is None:
        print(f"  missing page: /{rel}")
        return False
    blk = block(f"{BASE}/{rel}".rstrip("/"), qa)
    if B in doc:
        doc2 = re.sub(re.escape(B) + ".*?" + re.escape(E), lambda _: blk, doc, flags=re.S)
    else:
        anchor = "<footer" if "<footer" in doc else '<div class="legal"'
        if anchor not in doc:
            anchor = "</body>"
        doc2 = doc.replace(anchor, blk + anchor, 1)
    if doc2 != doc and not dry:
        open(p, "w", encoding="utf-8").write(doc2)
    print(f"  faq -> /{rel}  ({len(qa)} questions)")
    return True


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    today = dt.datetime.now(dt.timezone.utc).date()
    tstr = pretty(today.isoformat())
    rows = load_rows()

    # the one countdown sentence, shared by /calendar and /decisions: changes daily, honestly
    up = sorted((r for r in rows if r.get("type") == "PDUFA"
                 and str(r.get("d", "")) >= today.isoformat()
                 and str(r.get("st", "")).lower() != "decided"), key=lambda r: r["d"])
    nxt = ""
    if up:
        n = up[0]
        days = (dt.date.fromisoformat(n["d"]) - today).days
        when = "today" if days == 0 else ("tomorrow" if days == 1 else f"in {days} days")
        nxt = (f"{str(n.get('t', '')).upper()}'s "
               f"{re.split(r'[(]', str(n.get('name') or 'application'))[0].strip()} "
               f"on {pretty(n['d'])}, {when}.")

    ok = True

    # /calendar -- numbers parsed from its own lede so page and FAQ cannot disagree
    _, cal = read("calendar")
    caltxt = re.sub(r"<[^>]+>", " ", cal or "")
    m = re.search(r"lists\s+([\d,]+)\s+FDA decision dates.*?([\d,]+)\s+are still ahead",
                  caltxt, re.S)
    # the WINDOW must ride with the number (red team 2026-08-12: the FAQ said '67 on the 2026
    # calendar' while the lede said 'covering June 2026 to December 2026' -- half a year
    # silently became a full year, in the exact sentence offered to AI engines to repeat)
    w = re.search(r"covering\s+([A-Z][a-z]+ \d{4})\s+to\s+([A-Z][a-z]+ \d{4})", caltxt)
    window = f", covering {w.group(1)} to {w.group(2)}," if w else ""
    qa = []
    if m:
        qa.append(("How many FDA decisions are scheduled in 2026?",
                   f"{m.group(1)} FDA decision dates are on this calendar{window} and "
                   f"{m.group(2)} are still ahead as of {tstr}.", ""))
    if nxt:
        qa.append(("When is the next FDA decision?", nxt, ""))
    qa += [("How often is this calendar updated?",
            "Daily. Dates come from FDA announcements, sponsor press releases and SEC filings, "
            "and every date on the page links its source.", ""),
           ("What happens on a PDUFA date?",
            "The FDA approves the application, issues a Complete Response Letter, or extends "
            "the review.",
            ' <a href="/learn/what-is-a-pdufa-date" style="opacity:.9">What a PDUFA date is</a>.')]
    ok &= inject("calendar", qa, a.dry_run)

    # /decisions -- published counts + the quotable refusal
    _, dec = read("decisions")
    dtxt = re.sub(r"<[^>]+>", " ", dec or "")
    total = re.search(r"([\d,]+)\s+records", dtxt)
    unver = re.search(r"([\d,]+)\s+unverified", dtxt)
    first = re.search(r'href="/fda-decision/([A-Z]{1,6})-(\d{4}-\d{2}-\d{2})"', dec or "")
    qa = []
    if total and unver:
        t = int(total.group(1).replace(",", "")); u = int(unver.group(1).replace(",", ""))
        qa.append(("How many FDA decisions are in this archive?",
                   f"{t} records: {t - u} verified against primary sources and {u} inferred "
                   f"from the share-price reaction and marked unverified.", ""))
        qa.append(("What share of FDA decisions are approvals?",
                   f"We do not publish an overall approval rate. {u} of the {t} records are "
                   f"price-inferred, and a rate computed over unverified outcomes would be "
                   f"false precision; outcome counts are shown for verified records only.", ""))
    if first:
        qa.append(("What was the most recent FDA decision?",
                   f"{first.group(1)} on {pretty(first.group(2))}; its decision page carries "
                   f"the source document and the measured share-price reaction.", ""))
    if nxt:
        qa.append(("When is the next FDA decision?", nxt, ""))
    ok &= inject("decisions", qa, a.dry_run)

    # /readouts
    n_ro = sum(1 for r in rows if r.get("type") == "Readout"
               and str(r.get("d", "")) >= today.isoformat()
               and str(r.get("st", "")).lower() != "decided")
    ok &= inject("readouts", [
        ("How many clinical trial readouts are tracked?",
         f"{n_ro} expected readouts are on the calendar as of {tstr}, each with its "
         f"company-guided window and source.", ""),
        ("Does pdufa.bio predict readout outcomes?",
         "No. We publish dates, trial designs and measured stock reactions, each linked to its "
         "source; we do not publish outcome predictions or approval probabilities.", ""),
        ("What is a readout?",
         "The date a clinical trial's results become public, usually announced by the sponsor; "
         "unlike a PDUFA date it is an estimate until the company fixes it.", "")], a.dry_run)

    # /drug
    n_drug = sum(1 for x in os.scandir(os.path.join(SITE, "drug")) if x.is_dir())
    ok &= inject("drug", [
        ("How many drugs are in this index?",
         f"{n_drug} drug programs have pages as of {tstr}, rebuilt daily from the catalyst "
         f"dataset and the decisions archive.", ""),
        ("What is on each drug page?",
         "The program's next FDA decision or readout date, its catalyst history with outcomes, "
         "the sponsor, and links to every source.", ""),
        ("How current are these pages?",
         "Rebuilt daily; a decided event moves from upcoming to history with its outcome the "
         "day it resolves.", "")], a.dry_run)

    # /tickers
    n_tk = sum(1 for x in os.scandir(os.path.join(SITE, "ticker")) if x.is_dir())
    ok &= inject("tickers", [
        ("How many companies are tracked?",
         f"{n_tk} companies have catalyst hubs as of {tstr}.", ""),
        ("What is on a company hub?",
         "Every tracked FDA decision date, readout window and conference presentation for that "
         "ticker, with outcomes and sources.", ""),
        ("Where does the data come from?",
         "FDA announcements, sponsor press releases and SEC filings; every date links its "
         "source.", "")], a.dry_run)

    # /research
    ok &= inject("research", [
        ("What datasets does pdufa.bio publish?",
         "Four studies: PDUFA stock run-up by market cap (763 decisions), readout reactions "
         "(1,752 readouts), conference run-ups (1,425 presentations), and short interest into "
         "FDA decisions.", ""),
        ("Can the data be reused?",
         "Yes. The study data tables are published under CC BY 4.0; reuse with attribution to "
         "pdufa.bio.", ""),
        ("Do the studies predict outcomes?",
         "No. They measure what happened, with n and interquartile ranges stated; we do not "
         "publish predictions or approval probabilities.", "")], a.dry_run)

    # /conferences
    ok &= inject("conferences", [
        ("What does this page track?",
         "Upcoming presentations of tracked drug programs at major medical conferences, with "
         "dates, presenting companies and sources.", ""),
        ("Why do conference presentations matter?",
         "Abstract acceptance is public, scheduled information about a program's data; our "
         "conference run-up study measures how stocks have behaved around 1,425 such "
         "presentations.",
         ' <a href="/research/conference-runup" style="opacity:.9">The study</a>.'),
        ("Where do the dates come from?",
         "Conference programs and sponsor announcements; every entry links its source.", "")],
        a.dry_run)

    # /adcomm
    n_ac = sum(1 for x in os.scandir(os.path.join(SITE, "adcomm")) if x.is_dir())
    ok &= inject("adcomm", [
        ("What is an FDA advisory committee?",
         "A panel of outside experts convened to review an application's evidence and vote on "
         "questions the FDA poses.", ""),
        ("Is the FDA bound by the vote?",
         "No. The vote is advisory; the FDA usually follows it but is free not to.", ""),
        ("How many meetings are on record here?",
         f"{n_ac} advisory committee meetings are documented with their votes and outcomes as "
         f"of {tstr}.", "")], a.dry_run)

    # /developers
    ok &= inject("developers", [
        ("Is the pdufa.bio API free?",
         "Yes. The read API at /api/v1/ is free, and /llms.txt documents it for AI agents.", ""),
        ("What does the API return?",
         "The tracked catalyst dataset: PDUFA dates, readout windows, conference presentations "
         "and advisory committee meetings, each record with its canonical page URL.", ""),
        ("How current is the API?",
         "Rebuilt daily with the site; the as_of field carries the build date.", "")], a.dry_run)

    # the cross-trial explainer: already Q&A-shaped prose with Article schema; the audit calls
    # it the most citable asset on the site. Static answers drawn from its own text.
    ok &= inject("learn/why-cross-trial-comparisons-mislead", [
        ("Can you compare response rates from two different trials?",
         "No. Trials of different drugs enroll different populations, use different endpoints "
         "and run in different eras, so cross-trial efficacy comparison is not valid and we do "
         "not publish one.", ""),
        ("What can honestly be compared between two drugs?",
         "Trial design, the approved label, route and dosing frequency, and any head-to-head "
         "result that actually exists.", "")], a.dry_run)

    # Dataset/DataCatalog (audit 2.3): the four research pages already carry Dataset schema;
    # the gaps verified today are /research (no catalog tying them together) and /developers
    # (the API itself, the only surface Google Dataset Search can find it by). Same markers,
    # same daily run, so regeneration of either page can never strip the nodes.
    DS, DE = "<!--DSCAT:BEGIN-->", "<!--DSCAT:END-->"
    studies = [
        ("PDUFA Stock Run-Up by Market Cap", "pdufa-stock-run-up-by-market-cap",
         "763 FDA decisions (2024-2026) with pre-decision stock run-up by market-cap cohort."),
        ("Clinical Trial Readout Reactions", "readout-reaction",
         "1,752 phase readouts with measured next-day stock reactions."),
        ("Conference Run-up Study", "conference-runup",
         "1,425 biotech conference presentations (2017-2026) with pre-event run-up data."),
        ("Short Interest into FDA Decisions", "short-interest-fda",
         "Short interest positioning ahead of FDA decisions and what followed.")]
    def ds_node(name, slug, desc):
        return {"@type": "Dataset", "name": name, "url": f"{BASE}/research/{slug}",
                "description": desc, "license": "https://creativecommons.org/licenses/by/4.0/",
                "creator": {"@type": "Organization", "name": "pdufa.bio", "url": BASE + "/"}}
    for rel, node in (
            ("research", {"@context": "https://schema.org", "@type": "DataCatalog",
                          "name": "pdufa.bio research datasets",
                          "url": f"{BASE}/research",
                          "license": "https://creativecommons.org/licenses/by/4.0/",
                          "creator": {"@type": "Organization", "name": "pdufa.bio",
                                      "url": BASE + "/"},
                          "dataset": [ds_node(*s) for s in studies]}),
            ("developers", {"@context": "https://schema.org", "@type": "Dataset",
                            "name": "pdufa.bio FDA catalyst dataset",
                            "url": f"{BASE}/developers",
                            "description": "Tracked FDA catalyst events: PDUFA decision dates, "
                                           "clinical trial readout windows, conference "
                                           "presentations and advisory committee meetings, "
                                           "rebuilt daily, each record with its canonical "
                                           "page URL.",
                            "creator": {"@type": "Organization", "name": "pdufa.bio",
                                        "url": BASE + "/"},
                            "distribution": [{"@type": "DataDownload",
                                              "encodingFormat": "application/json",
                                              "contentUrl": f"{BASE}/api/v1/"}]})):
        p, doc = read(rel)
        if doc is None:
            ok = False
            continue
        blk = (DS + '<script type="application/ld+json">'
               + json.dumps(node, separators=(",", ":")) + "</script>" + DE)
        if DS in doc:
            doc2 = re.sub(re.escape(DS) + ".*?" + re.escape(DE), lambda _: blk, doc, flags=re.S)
        else:
            doc2 = doc.replace("</head>", blk + "</head>", 1)
        if doc2 != doc and not a.dry_run:
            open(p, "w", encoding="utf-8").write(doc2)
        print(f"  dataset schema -> /{rel}")

    print("all targets present" if ok else "SOME TARGETS MISSING")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
