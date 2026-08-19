# -*- coding: utf-8 -*-
"""build_pdufa_event_pages.py -- complete the /pdufa/{TICKER}-{drug} per-event page set.

Console read 2026-08-18c: /pdufa/REGN-garetosmab converts at 25% CTR -- the best page on the
site -- and the red team's own correction says the per-event scheme was already shipped and
working; coverage is just partial (/pdufa/CAPR-deramiocel 404s). The original generator predates
the repo (every event page traces to the initial import commit), so new events never get pages.
This builder closes that permanently: every UPCOMING PDUFA event in dataset.mjs gets its page.

Rules:
  - NEVER overwrites an existing page (hand-grown pages carry story cards and charts; a rebuild
    that flattened them would destroy the best content on the site). New slugs only.
  - Drug names pass build_drug_pages.clean_name -- the same validator that keeps junk like
    'EX-99' from becoming a URL.
  - Date claims carry the row's precision: day-precision prints the date; month/quarter prints
    the month, never an invented day (the API's own rule: claim no more than the source).
  - Facts on the page are the dataset row's facts; nothing new is asserted. Downstream passes
    (nav rebuild, breadcrumbs, freshness, date-modified, story blocks) treat these like any page.

    python build_pdufa_event_pages.py [--dry-run]
"""
import argparse, datetime as dt, json, os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")
OUTDIR = os.path.join(SITE, "pdufa")

from build_drug_pages import clean_name, slugify, esc  # same validator, same slugs

MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]

STYLE = ("*{box-sizing:border-box}body{margin:0;background:#02060d;color:#f2f6fc;"
         "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,"
         "sans-serif;-webkit-font-smoothing:antialiased;line-height:1.5}a{color:#6fb6ff;"
         "text-decoration:none}a:hover{text-decoration:underline}.wrap{max-width:820px;"
         "margin:0 auto;padding:22px 18px 60px}.top{display:flex;align-items:center;"
         "justify-content:space-between;border-bottom:1px solid #1a3358;padding-bottom:12px}"
         ".brand{font-size:19px;font-weight:800}.brand b{color:#e3ba5e}.nav a{color:#a7bcd9;"
         "font-size:13px;margin-left:14px}.bc{font-size:12px;color:#94a9c9;margin:16px 0 4px}"
         ".bc a{color:#94a9c9}h1{font-size:27px;line-height:1.18;letter-spacing:-.4px;"
         "margin:6px 0 4px}h1 .g{color:#e3ba5e}h2{font-size:18px;margin:26px 0 8px;"
         "color:#e3ba5e}.sub{color:#a7bcd9;font-size:15px;margin:6px 0 16px}.card{"
         "background:#0c1d38;border:1px solid #1a3358;border-radius:12px;padding:14px 16px;"
         "margin:14px 0}.kv{display:flex;justify-content:space-between;gap:12px;font-size:14px;"
         "padding:7px 0;border-bottom:1px solid #112b48}.kv:last-child{border:0}.kv span{"
         "color:#a7bcd9}.kv b{color:#f2f6fc;text-align:right}.cta{display:block;background:"
         "linear-gradient(135deg,#13315c,#0c1d38);border:1px solid #e3ba5e;border-radius:12px;"
         "padding:15px 16px;margin:20px 0;color:#f2f6fc}.cta b{color:#e3ba5e}.note{font-size:"
         "12px;color:#94a9c9}footer{border-top:1px solid #1a3358;margin-top:34px;padding-top:"
         "16px;font-size:11.5px;color:#94a9c9;line-height:1.6}footer b{color:#a7bcd9}")

NAV = ('<!--NAVC:BEGIN--><a href="/calendar">Calendar</a><a href="/decisions">Decisions</a>'
       '<a href="/readouts">Readouts</a><a href="/patent-cliff">Patents</a>'
       '<a href="/drug">Drug Index</a><a href="/tickers">Stocks</a>'
       '<a href="/learn/what-is-a-pdufa-date">Learn</a>'
       '<a href="/pricing" style="color:#e3ba5e">Pro</a><!--NAVC:END-->')

FOOTER = ('<footer><b>Not affiliated with or endorsed by the FDA.</b> pdufa.bio is an '
          'independent publication with no affiliation with, endorsement by, sponsorship by, or '
          'connection to the U.S. Food and Drug Administration or any other government agency. '
          '&ldquo;FDA&rdquo;, &ldquo;PDUFA&rdquo; and all company, drug and ticker names are '
          'used descriptively and remain the property of their respective owners.<br><br>'
          '<b>Informational and educational purposes only. Not investment advice.</b> Nothing '
          'on this page is investment, legal, tax or medical advice, or an offer or '
          'solicitation to buy or sell any security. pdufa.bio is not a registered investment '
          'adviser or broker-dealer and does not recommend trades or publish individual-drug '
          'approval probabilities. Verify every date and outcome against primary FDA, SEC or '
          'company filings. Data is provided as is, without warranty of any kind, and past '
          'behaviour does not predict future outcomes.<br><br>&copy; 2026 pdufa.bio. '
          'All rights reserved.</footer>')


def when_text(d, dp):
    """Human date at the row's own precision."""
    y, m = int(d[:4]), int(d[5:7])
    if dp == "day":
        return f"{MONTHS[m - 1][:3]} {int(d[8:10])}, {y}", d
    return f"{MONTHS[m - 1]} {y}", d[:7]        # month/quarter: never print an invented day


def page(r, slug):
    tk = str(r.get("t", "")).upper()
    drug = clean_name(r.get("name")) or str(r.get("name", "")).strip()
    comp = r.get("company") or tk
    ind = (r.get("_d") or {}).get("indication") or ""
    d, dp = str(r.get("d", "")), str(r.get("dp") or "day")
    human, iso_claim = when_text(d, dp)
    prec_note = ("" if dp == "day"
                 else " The sponsor has guided this window, not a specific day; the date shown "
                      "is the window, at the precision the source gave.")
    url = f"https://www.pdufa.bio/pdufa/{slug}"
    title = f"{tk} PDUFA date: {drug.split('(')[0].strip()}, {human} | pdufa.bio"
    desc = (f"{tk}'s FDA PDUFA target is {human} for {drug.split('(')[0].strip()}"
            + (f" ({ind[:70]})" if ind else "")
            + ". Date, company and indication, each linked to its source.")
    if len(desc) > 158:
        # word-boundary truncation only -- a description ending mid-word fails the meta guard
        # (the ZYME-ziihera lesson: [:158] cut 'linked' to 'linke')
        desc = desc[:158].rsplit(" ", 1)[0].rstrip(",;:") + "."

    q1 = f"When is the {tk} PDUFA date?"
    a1 = (f"The FDA PDUFA target date for {tk} ({comp}) is "
          + (d if dp == "day" else human) + f" for {drug}."
          + prec_note + " Dates are company/FDA-sourced and can slip. Verify against primary "
                        "filings.")
    q2 = f"What is {tk}'s drug {drug.split('(')[0].strip()}?"
    a2 = (f"{drug} is {comp}'s candidate under FDA review"
          + (f" for {ind}" if ind else "") + ".")

    jsonld = json.dumps({
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "BreadcrumbList", "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Home",
                 "item": "https://www.pdufa.bio/"},
                {"@type": "ListItem", "position": 2, "name": "PDUFA Calendar",
                 "item": "https://www.pdufa.bio/calendar"},
                {"@type": "ListItem", "position": 3, "name": tk,
                 "item": f"https://www.pdufa.bio/pdufa/{tk}"}]},
            {"@type": "FAQPage", "mainEntity": [
                {"@type": "Question", "name": q1,
                 "acceptedAnswer": {"@type": "Answer", "text": a1}},
                {"@type": "Question", "name": q2,
                 "acceptedAnswer": {"@type": "Answer", "text": a2}}]},
            {"@type": "Event", "name": f"{drug.split('(')[0].strip()} FDA decision",
             "description": f"{drug.split('(')[0].strip()} FDA decision: FDA PDUFA target "
                            f"decision date. Facts only, not advice.",
             "eventStatus": "https://schema.org/EventScheduled",
             "eventAttendanceMode": "https://schema.org/OnlineEventAttendanceMode",
             "organizer": {"@type": "Organization",
                           "name": "U.S. Food and Drug Administration",
                           "url": "https://www.fda.gov"},
             "location": {"@type": "VirtualLocation", "url": url},
             "url": url, "startDate": iso_claim, "endDate": iso_claim}]},
        ensure_ascii=False)

    kv = [("FDA PDUFA target date", d if dp == "day" else human + " (window)"),
          ("Drug / candidate", drug), ("Company", comp)]
    if ind:
        kv.insert(2, ("Indication", ind))
    if r.get("cap"):
        kv.append(("Market-cap tier", r["cap"]))
    nct = (r.get("_d") or {}).get("nct_id")
    if isinstance(nct, str) and nct.startswith("NCT"):
        kv.append(("ClinicalTrials.gov", nct))
    kv_html = "".join(f'<div class="kv"><span>{esc(k)}</span><b>{esc(v)}</b></div>'
                      for k, v in kv)

    month_link = ""
    if d[:4] == "2026":
        mname = MONTHS[int(d[5:7]) - 1]
        mdir = os.path.join(SITE, "calendar", "2026", mname.lower())
        if os.path.isdir(mdir):
            month_link = (f'<a class="cta" href="/calendar/2026/{mname.lower()}">'
                          f'<b>All {mname} 2026 PDUFA dates &rarr;</b></a>')

    src_url = str(r.get("url") or "")
    src_row = ""
    if src_url.startswith("http"):
        src_row = (f'<div class="note" style="margin:8px 0">Primary source: '
                   f'<a href="{esc(src_url)}" rel="nofollow">sponsor announcement</a></div>')

    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><title>{esc(title)}</title><meta name="description" content="{esc(desc)}"><link rel="canonical" href="{url}"><meta name="robots" content="index,follow,max-image-preview:large"><meta name="theme-color" content="#02060d"><link rel="icon" type="image/svg+xml" href="/favicon.svg"><meta property="og:type" content="article"><meta property="og:site_name" content="pdufa.bio"><meta property="og:url" content="{url}"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}"><meta name="twitter:card" content="summary"><meta name="twitter:title" content="{esc(title)}"><style>{STYLE}</style><script type="application/ld+json">{jsonld}</script></head><body><div class="wrap"><div class="top"><a class="brand" href="/">pdufa<b>.bio</b></a><div class="nav">{NAV}</div></div><div class="bc"><a href="/">Home</a> &rsaquo; <a href="/calendar">PDUFA Calendar</a> &rsaquo; {esc(tk)}</div><h1>{esc(tk)} PDUFA Date: <span class="g">{esc(drug.split('(')[0].strip())}</span></h1><div class="sub">FDA decision (PDUFA) target <b>{esc(human)}</b> &middot; {esc(comp)}{(' &middot; ' + esc(ind)) if ind else ''}</div>{src_row}<!--story-v1--><!--/story-v1--><h2>Key facts</h2><div class="card">{kv_html}</div><p class="sub" style="margin-top:14px">New to FDA decisions? Read <a href="/learn/what-is-a-pdufa-date">what a PDUFA date is</a> and <a href="/fda-approval-rate">how often the FDA approves drugs</a>.</p><a class="cta" href="/calendar"><b>See the full 2026 PDUFA calendar &rarr;</b></a>{month_link}<h2>FAQ</h2><div class="card"><b>{esc(q1)}</b><div class="sub" style="margin-top:6px">{esc(a1)}</div></div><div class="card"><b>{esc(q2)}</b><div class="sub" style="margin-top:6px">{esc(a2)}</div></div>{FOOTER}</div><script src="/cmdk.js" defer></script></body></html>"""


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    src = open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
    rows, _ = json.JSONDecoder().raw_decode(src[src.find("["):])
    today = dt.date.today().isoformat()

    existing = {n.lower() for n in os.listdir(OUTDIR)} if os.path.isdir(OUTDIR) else set()
    written, skipped = 0, []
    for r in rows:
        if r.get("type") != "PDUFA" or str(r.get("st") or "").lower() == "decided":
            continue
        d = str(r.get("d") or "")
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", d) or d < today:
            continue
        drug = clean_name(r.get("name"))
        if not drug:
            skipped.append(str(r.get("name"))[:40])
            continue
        tk = str(r.get("t", "")).upper()
        slug = f"{tk}-{slugify(drug.split('(')[0].strip())}"
        if not slug.split("-", 1)[1:] or slug.lower() in existing:
            continue
        # brand/generic duplicate check: an existing page for this ticker that already NAMES this
        # drug covers the event even under a different slug (BAYRY-hyrnuo covers sevabertinib).
        tok = re.sub(r"[^a-z0-9]", "", drug.split("(")[0].strip().lower())[:10]
        covered = False
        for name in list(existing):
            if not name.startswith(tk.lower() + "-"):
                continue
            ep = os.path.join(OUTDIR, name, "index.html")
            try:
                if tok and tok in open(ep, encoding="utf-8", errors="replace").read().lower() \
                        .replace("-", ""):
                    covered = True
                    break
            except OSError:
                continue
        if covered:
            continue
        out = os.path.join(OUTDIR, slug)
        if a.dry_run:
            print(f"  would write /pdufa/{slug}  ({d})")
            written += 1
            continue
        os.makedirs(out, exist_ok=True)
        open(os.path.join(out, "index.html"), "w", encoding="utf-8").write(page(r, slug))
        existing.add(slug.lower())
        written += 1
        print(f"  wrote /pdufa/{slug}  ({d} {r.get('dp') or 'day'})")

    if skipped:
        print(f"  rejected {len(skipped)} row(s) with non-drug names: {skipped[:4]}")
    print(f"per-event pages written: {written}; existing pages untouched")
    return 0


if __name__ == "__main__":
    sys.exit(main())
