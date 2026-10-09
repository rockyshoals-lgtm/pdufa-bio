# -*- coding: utf-8 -*-
"""build_withdrawn_pages.py -- an application the sponsor WITHDREW gets an event page that says so.

Audit 2026-10-08 P0: MRK's ifinatamab deruxtecan BLA was withdrawn on 2026-09-25 and the event page still
read "MRK PDUFA Date ... is under FDA review" thirteen days later, with an Event schema dated on a goal
day that would never come; Bing's answer box quoted it under our name. For every dataset row with
st "Withdrawn" and a sourced withdrawn_date, this rewrites /pdufa/{slug} (the row's url):

  * title / description / og / twitter: "{TK} {drug} {APP} withdrawn {date}, before {goal} PDUFA date";
  * h1 and a fact-first lede: who withdrew, when, how many days before the goal date, and why in
    the sponsor's own words (quoted, linked);
  * a key-facts card (status, withdrawal date + source, the goal date + its source, trial);
  * a visible FAQ and matching FAQPage JSON-LD, led by "Was {drug} approved?";
  * no Event schema, no countdown, no run-up module: no decision is coming.

The page keeps the existing head <style>, the frozen nav block (NAVC) and the footer verbatim; the
chain's normalisers add breadcrumbs, OG and the freshness stamp. A withdrawal is neither an approval nor
a CRL and is never counted as an FDA decision. Facts only; not investment advice.

    python build_withdrawn_pages.py [--dry-run]
"""
import argparse
import datetime as dt
import html
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")
MONTHS = ["", "January", "February", "March", "April", "May", "June", "July", "August", "September",
          "October", "November", "December"]
MON3 = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
NUM = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven",
       "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen", "twenty"]
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def esc(s):
    return html.escape(str(s or ""), quote=True)


def long_d(iso):
    d = dt.date.fromisoformat(iso)
    return f"{MONTHS[d.month]} {d.day}, {d.year}"


def short_d(iso):
    d = dt.date.fromisoformat(iso)
    return f"{MON3[d.month]} {d.day}, {d.year}"


def days_words(n):
    return NUM[n] if 0 <= n < len(NUM) else str(n)


def page_for(r, shell):
    x = r.get("_d") or {}
    tk = str(r.get("t") or "").upper()
    name = str(r.get("name") or "")
    drug = re.sub(r"\s*\([^)]*\)\s*$", "", name).strip() or name      # "Ifinatamab deruxtecan"
    drug_l = drug[:1].lower() + drug[1:] if drug[:2] != drug[:2].upper() else drug
    app = "BLA" if re.search(r"\bBLA\b|biologics license", (x.get("withdrawn_quote") or "") + " " +
                             (x.get("source_quote") or "") + " " + (x.get("withdrawn_note") or ""), re.I) else "application"
    wd, gd = x["withdrawn_date"][:10], str(r.get("d"))[:10]
    gap = (dt.date.fromisoformat(gd) - dt.date.fromisoformat(wd)).days
    who = x.get("withdrawn_by") or r.get("company")
    wsrc, wlab = x.get("withdrawn_source_url") or "", x.get("withdrawn_source") or "sponsor release"
    gsrc, glab = x.get("source_url") or "", x.get("source") or "company filing"
    quote = x.get("withdrawn_quote") or ""
    ind = x.get("indication") or ""
    trial = x.get("trial") or ""
    url = str(r.get("url"))
    canon = f"https://www.pdufa.bio{url}"

    title = f"{tk} {drug_l} {app} withdrawn {short_d(wd)}, before {short_d(gd)} PDUFA date | pdufa.bio"
    desc = (f"{who} withdrew the {app} for {drug_l} ({ind.lower() if ind else 'its proposed use'}) on {long_d(wd)}, "
            f"{days_words(gap)} days before its {long_d(gd)} goal date. No FDA decision was issued.")
    lede = (f"{esc(who)} withdrew the {esc(app)} for {esc(drug_l)} on {esc(long_d(wd))}, {esc(days_words(gap))} days "
            f"before its {esc(long_d(gd))} goal date. In the companies' words, the decision was based on "
            f"discussions with the FDA that \"{esc(quote[quote.find('data supporting'):].rstrip('.'))}\" "
            f'(<a href="{esc(wsrc)}" rel="noopener">{esc(wlab)}</a>). No FDA decision was issued, so this is '
            f"neither an approval nor a Complete Response Letter, and it is not counted in pdufa.bio's FDA "
            f"decision timing statistic.") if "data supporting" in quote else (
            f"{esc(who)} withdrew the {esc(app)} for {esc(drug_l)} on {esc(long_d(wd))}, {esc(days_words(gap))} days "
            f'before its {esc(long_d(gd))} goal date (<a href="{esc(wsrc)}" rel="noopener">{esc(wlab)}</a>). '
            f"No FDA decision was issued.")
    faq = [
        (f"Was {drug_l} approved?",
         f"No. {who} withdrew the {app} for {drug_l} on {long_d(wd)}, before the FDA acted on it, so no FDA "
         f"decision was issued. The {long_d(gd)} PDUFA goal date no longer applies."),
        (f"Why was the {drug_l} {app} withdrawn?",
         f"{who} said the withdrawal was based on discussions with the FDA that {quote[quote.find('data supporting'):]}"
         if "data supporting" in quote else f"{who} announced the withdrawal on {long_d(wd)}."),
        (f"Is the {long_d(gd)} PDUFA date for {drug_l} still on?",
         f"No. The goal date was set for the {app} that was withdrawn on {long_d(wd)}. A new goal date would "
         f"follow only a new submission and its acceptance by the FDA."),
    ]
    if x.get("withdrawn_note") and "IDeate-Lung02" in x["withdrawn_note"]:
        faq.append((f"What happens next for {drug_l} in small cell lung cancer?",
                    "The companies said patient enrollment continues in the IDeate-Lung02 Phase 3 trial, and "
                    "that they will assess a potential future filing based on its results."))
    ld = {"@context": "https://schema.org", "@type": "FAQPage",
          "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
                         for q, a in faq]}
    kv = [("Status", "Application withdrawn by the sponsor; no FDA decision"),
          ("Withdrawn", f'{long_d(wd)} (<a href="{esc(wsrc)}" rel="noopener">{esc(wlab)}</a>)'),
          ("Goal date that no longer applies", f'{long_d(gd)} (<a href="{esc(gsrc)}" rel="noopener">{esc(glab)}</a>)'),
          ("Drug", esc(name)), ("Indication", esc(ind)), ("Company", esc(r.get("company")))]
    if trial:
        kv.append(("Trial behind the application", esc(trial)))
    card = "".join(f'<div class="kv"><span>{k}</span><b>{v}</b></div>' for k, v in kv)
    body = (f'<div class="bc"><a href="/">Home</a> &rsaquo; <a href="/calendar">PDUFA Calendar</a> &rsaquo; '
            f'<a href="/pdufa/{esc(tk)}">{esc(tk)}</a></div>'
            f'<h1>{esc(drug)} <span class="g">{esc(app)} withdrawn</span>: {esc(short_d(wd))}</h1>'
            f'<p class="sub" data-withdrawn="{esc(r.get("id"))}"><span class="badge amb">Withdrawn</span> {lede}</p>'
            f'<div class="card">{card}</div>'
            f'<p>The application was listed on the pdufa.bio calendar with {"an" if long_d(gd)[0] in "AEIOU" else "a"} {esc(long_d(gd))} goal date, sourced to '
            f'<a href="{esc(gsrc)}" rel="noopener">{esc(glab)}</a>. It has been removed from every upcoming list. '
            f'Other {esc(tk)} FDA dates and decisions: <a href="/pdufa/{esc(tk)}">{esc(tk)} FDA calendar</a>; all dates: '
            f'<a href="/calendar">PDUFA calendar</a>.</p>'
            f'<h2>FAQ</h2>' + "".join(f"<h3>{esc(q)}</h3><p>{esc(a)}</p>" for q, a in faq) +
            '<p class="note">Facts from the sponsor\'s release and SEC filing, each linked. Not a prediction, and not '
            'investment advice.</p>')
    head, nav, footer = shell
    head = re.sub(r"<title>.*?</title>", f"<title>{esc(title)}</title>", head, count=1, flags=re.S)
    head = re.sub(r'<script type="application/ld\+json">.*?</script>', "", head, flags=re.S)
    for pat, val in ((r'(<meta name="description" content=")[^"]*(")', desc),
                     (r'(<meta property="og:title" content=")[^"]*(")', title),
                     (r'(<meta property="og:description" content=")[^"]*(")', desc),
                     (r'(<meta name="twitter:title" content=")[^"]*(")', title),
                     (r'(<meta name="twitter:description" content=")[^"]*(")', desc),
                     (r'(<link rel="canonical" href=")[^"]*(")', canon),
                     (r'(<meta property="og:url" content=")[^"]*(")', canon)):
        head = re.sub(pat, lambda m: m.group(1) + esc(val) + m.group(2), head, count=1)
    head = head.replace("</head>", f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script></head>', 1)
    return head + nav + body + footer, title, desc


def shell_of(doc):
    """(head, body-start-through-nav, footer) from an existing event page."""
    hi = doc.find("</head>") + len("</head>")
    ne = doc.find("<!--NAVC:END-->")
    bc = doc.find('<div class="bc">', ne)
    fi = doc.find("<footer")
    if min(hi, ne, bc, fi) < 0 or not (hi < ne < bc < fi):
        return None
    return doc[:hi], doc[hi:bc], doc[fi:]


def mark_calendar(r, dry):
    """Mark the withdrawn row on every calendar page: data-dec (so no 'still ahead' count, ItemList or
    census takes it) plus data-wd, linking the event page, labelled Withdrawn with its date."""
    import glob
    x = r.get("_d") or {}
    tk, d = str(r.get("t") or "").upper(), str(r.get("d"))[:10]
    wd = x["withdrawn_date"][:10]
    drug = str(r.get("name") or "")
    new = (f'<a class="row" data-dec="1" data-wd="1" href="{esc(r["url"])}"><div class="t">{tk} &middot; {d} '
           f'<span style="color:#ffce85;font-weight:700">withdrawn</span></div><div class="d">'
           f'<span style="color:#ffce85;font-weight:700">Withdrawn {esc(short_d(wd))}</span>: {esc(drug)}, '
           f'no FDA decision</div></a>')
    rx = re.compile(r'<a class="row"(?:(?!data-dec)[^>])*>\s*<div class="t">' + re.escape(tk) +
                    r'\s*(?:&middot;|·)\s*' + re.escape(d) + r'</div>\s*<div class="d">.*?</div>\s*</a>', re.S)
    rx_done = re.compile(r'<a class="row" data-dec="1" data-wd="1" href="[^"]*"><div class="t">' + re.escape(tk) +
                         r' &middot; ' + re.escape(d) + r' .*?</a>', re.S)
    n = 0
    pages = [os.path.join(SITE, "calendar", "index.html")] + sorted(
        glob.glob(os.path.join(SITE, "calendar", "*", "*", "index.html")))
    for p in pages:
        if not os.path.exists(p):
            continue
        doc = io.open(p, encoding="utf-8").read()
        out = rx_done.sub(lambda m: new, rx.sub(lambda m: new, doc))
        if out != doc:
            n += 1
            if not dry:
                io.open(p, "w", encoding="utf-8", newline="\n").write(out)
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    src = io.open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
    rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    n = 0
    for r in rows:
        x = r.get("_d") or {}
        if r.get("type") != "PDUFA" or str(r.get("st") or "").lower() != "withdrawn":
            continue
        if not (ISO.match(str(x.get("withdrawn_date") or "")[:10]) and ISO.match(str(r.get("d") or "")[:10])
                and x.get("withdrawn_source_url") and str(r.get("url") or "").startswith("/pdufa/")):
            print(f"  SKIP {r['id']}: withdrawn without a sourced day, a source URL or a /pdufa/ url")
            continue
        p = os.path.join(SITE, r["url"].strip("/").replace("/", os.sep), "index.html")
        if not os.path.exists(p):
            print(f"  SKIP {r['id']}: {p} does not exist")
            continue
        doc = io.open(p, encoding="utf-8").read()
        shell = shell_of(doc)
        if not shell:
            print(f"  SKIP {r['id']}: page has no head/NAVC/bc/footer shell")
            continue
        out, title, _ = page_for(r, shell)
        n += 1
        print(f"  {r['url']}: {title}")
        if not a.dry_run and out != doc:
            io.open(p, "w", encoding="utf-8", newline="\n").write(out)
        print(f"    calendar pages marked: {mark_calendar(r, a.dry_run)}")
    print(f"withdrawn pages: {n}")


if __name__ == "__main__":
    main()
