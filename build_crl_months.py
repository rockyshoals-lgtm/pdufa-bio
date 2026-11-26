# -*- coding: utf-8 -*-
"""build_crl_months.py -- /crl/{year}/{month}: FDA complete response letters by month (audit 2026-11-09 §5 item 5).

Bing shows 172 impressions and 0 clicks for "fda complete response letter {october|november} 2026": a month-dated
question with no month page to answer it. Each page states two counts for the month, from two different records,
and never blends them:

  1. letters in the FDA's own release (openFDA transparency/crl, the corpus /crl lists), by letter date;
  2. Complete Response Letters among the PDUFA decisions pdufa.bio tracked that month (/decisions/crl rows).

The FDA releases letters in batches and late; a month with no released letters says so, with the release's own
last-updated date, rather than implying the FDA issued none. Counts only, no rates. Facts only, not investment advice.
Months built: every month from January 2025 through the current Eastern month, plus any month a letter is dated in.

    python build_crl_months.py [--dry-run]
"""
import argparse
import collections
import datetime as dt
import html
import io
import json
import os
import re
import sys
from urllib.parse import quote as _q

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
sys.path.insert(0, HERE)
from site_dates import eastern_today  # noqa: E402
from capture_crl_corpus import newest_corpus  # noqa: E402

BASE = "https://www.pdufa.bio"
MON = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november",
       "december"]
B, E = "<!--CRLMONTHS:BEGIN-->", "<!--CRLMONTHS:END-->"
esc = lambda s: html.escape(str(s or "").strip(), quote=True)


def _text_pages():
    """{(PDF file, ISO date): /crl/letter slug}, the per-letter pages build_crl_letters.py writes (2026-11-23)."""
    from build_feeds import crl_letters            # a failure here fails the build: no silent loss of the links
    from build_crl_letters import by_file_date
    return by_file_date(crl_letters(include_rescinded=True)[0])


TEXT = _text_pages()


def corpus():
    p = newest_corpus() or os.path.join(HERE, "CRL_corpus_openFDA_2026-08-29.json")
    raw = json.load(io.open(p, encoding="utf-8"))
    recs = raw if isinstance(raw, list) else raw.get("records") or raw.get("results")
    upd = str((raw.get("meta") or {}).get("last_updated") or "") if isinstance(raw, dict) else ""
    out, seen = [], set()
    for r in recs:
        m = re.match(r"(\d{2})/(\d{2})/(\d{4})", str(r.get("letter_date") or ""))
        fn = str(r.get("file_name") or "").strip()
        if not m or not fn.lower().endswith(".pdf") or (fn, m.group(0)) in seen:
            continue           # same filter as build_crl_hub: no file yet, or a verbatim duplicate record
        seen.add((fn, m.group(0)))
        apps = r.get("application_number")
        out.append({"iso": f"{m.group(3)}-{m.group(1)}-{m.group(2)}", "company": str(r.get("company_name") or "").strip(),
                    "app": ", ".join(apps) if isinstance(apps, list) else str(apps or ""),
                    "status": str(r.get("approval_status") or "").strip(),
                    "url": "https://download.open.fda.gov/crl/" + _q(fn), "fn": fn,
                    "cr": str(r.get("letter_type") or "") == "COMPLETE RESPONSE"})
    return out, upd


def tracked():
    """{'YYYY-MM': [(iso, ticker, drug, href)]} from /decisions/crl's published rows; and decided-row counts by month."""
    crl = collections.defaultdict(list)
    doc = io.open(os.path.join(SITE, "decisions", "crl", "index.html"), encoding="utf-8").read()
    for href, t, iso, drug in re.findall(r'<a class="row" href="(/fda-decision/[^"]+)"><div class="t">([A-Z0-9.]+) '
                                         r'(?:&middot;|·) (\d{4}-\d{2}-\d{2}).*?class="d">.*?</span>:\s*(.*?)</div></a>', doc, re.S):
        drug = re.sub(r"<!--PV:B-->.*?<!--PV:E-->", "", drug, flags=re.S)   # the provenance badge is not drug text
        crl[iso[:7]].append((iso, t, html.unescape(re.sub(r"<[^>]+>", "", drug)).strip(), href))
    alld = collections.Counter(re.findall(r'<a class="row" href="/fda-decision/[^"]+"><div class="t">[A-Z0-9.]+ '
                                          r'(?:&middot;|·) (\d{4}-\d{2})-\d{2}',
                                          io.open(os.path.join(SITE, "decisions", "index.html"), encoding="utf-8").read()))
    # 2026-11-26: /decisions/crl lists only CRLs read from a document. The price-inferred CRL rows still on /decisions
    # are counted here so a month page does not read "1 of 23 was a CRL" when two more are listed there as inferred.
    INFERRED.clear()
    INFERRED.update(re.findall(r'<a class="row" href="/fda-decision/[^"]+"><div class="t">[A-Z0-9.]+ (?:&middot;|·) '
                               r'(\d{4}-\d{2})-\d{2}[^<]*</div><div class="d"><span class="[a-z]+">CRL</span>[^<]*'
                               r'<!--PV:B--> <span class="pv pv-inferred"',
                               io.open(os.path.join(SITE, "decisions", "index.html"), encoding="utf-8").read()))
    return crl, alld


INFERRED = collections.Counter()


def inferred_note(k, where):
    """One sentence for k price-inferred CRL rows, or nothing."""
    if not k:
        return ""
    return (f" A further {k} decision{'s' if k != 1 else ''} {where} {'is' if k == 1 else 'are'} listed on "
            f"/decisions as a CRL inferred from the share price rather than read from a filing, and "
            f"{'is' if k == 1 else 'are'} not counted here.")


_SUFFIX = re.compile(r"[,.]?\s+(?:Inc|LLC|Ltd|Limited|Corp|Corporation|Co|L\.?P|AB|GmbH|S\.L|plc|SA|AG|N\.V)\.?$", re.I)


def short_company(c):
    """'Summit Therapeutics Inc.' -> 'Summit Therapeutics'; '(US)' style parentheticals dropped. Display only."""
    c = re.sub(r"\s*\([^)]*\)", "", str(c or "")).strip().rstrip(",")
    for _ in range(3):
        c2 = _SUFFIX.sub("", c).strip().rstrip(",")
        if c2 == c:
            break
        c = c2
    return c


def short_drug(d):
    """'ZYNYZ (retifanlimab-dlwr) - (POD1UM-304)' -> 'ZYNYZ'; whole words only, capitalised for a title."""
    d = re.split(r"\s*(?:[(/;]| - )", str(d or ""), maxsplit=1)[0].strip()
    words, out = d.split(), ""
    for w in words:
        if len(out) + len(w) + 1 > 28:
            break
        out = (out + " " + w).strip()
    return (out[:1].upper() + out[1:]) if out else ""


_KV_DRUG = re.compile(r"<span>Drug(?: / candidate)?</span><b>(.*?)</b>", re.S)   # older pages: "Drug"


def page_drug(href):
    """The drug a decision page states in its own key facts, or '' (older pages without that row, and rows whose only
    text is a provenance label such as 'price-only', name no drug here rather than a wrong one)."""
    p = os.path.join(SITE, href.strip("/"), "index.html")
    if not os.path.exists(p):
        return ""
    m = _KV_DRUG.search(io.open(p, encoding="utf-8", errors="replace").read())
    return html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip() if m else ""


_PROV = re.compile(r"^(?:source-verified|price-only|inferred|verified)$", re.I)


def drug_cell(drug, href):
    """What a table's Drug cell shows: the decision page's own key fact; else the row's text (sometimes only a provenance
    label such as 'price-only', which is what the table showed before 2026-11-24)."""
    raw = str(drug or "").strip()
    d = page_drug(href) or ("" if _PROV.match(raw) else raw)
    return (d or raw)[:60]          # no named drug: the row's own text, as the table showed before


def names_line(y_m_name, letters, ours, room):
    """2026-11-24: Bing ranks these pages ~7-9 for 'fda complete response letter {month} 2026' with 0 clicks, and the
    title said only '1 Released, 0 Tracked'. The title now names what is on the page: the drugs among tracked CRLs
    (by FDA action date), else the companies in the FDA's release (by letter date). One record per title, so the two
    sources are never blended into one count."""
    named = collections.OrderedDict()
    for iso, t, _, href in sorted(ours):
        d = short_drug(page_drug(href))
        if d:
            named.setdefault(d, [])
            if t not in named[d]:
                named[d].append(t)
    if ours:
        items = [f"{d} ({', '.join(ts)})" for d, ts in named.items()]
        for _, t, _, href in sorted(ours):              # a CRL whose page names no drug still counts, by ticker
            if not short_drug(page_drug(href)) and t not in items:
                items.append(t)
    elif letters:
        items = []
        for l in sorted(letters, key=lambda x: x["iso"]):
            c = short_company(l["company"])
            if c and c not in items:
                items.append(c)
    else:
        return "None Released Yet"
    for k in range(len(items), 0, -1):             # the most names that fit with their own " and N More" tail
        more = len(items) - k
        line = ", ".join(items[:k]) + (f" and {more} More" if more else "")
        if len(line) <= room or k == 1:
            return line


def page(y, m, letters, ours, n_dec, upd, prev_, next_):
    name = f"{MON[m - 1].capitalize()} {y}"
    n = len(letters)
    url = f"{BASE}/crl/{y}/{MON[m - 1]}"
    head = f"FDA Complete Response Letters {name}: "
    title = head + names_line(name, letters, ours, 98 - len(head) - len(" | pdufa.bio")) + " | pdufa.bio"
    first = (f"The FDA's public release of complete response letters holds {n} letter{'s' if n != 1 else ''} dated "
             f"{name}" + (f" (openFDA, last updated {upd})" if upd else "") + ". ")
    if n == 0:
        first += ("The FDA publishes these letters in batches after they are issued, so a month with none released "
                  "may still have letters the FDA has not yet published. ")
    first += (f"Of the {n_dec} FDA decision{'s' if n_dec != 1 else ''} on PDUFA goal dates pdufa.bio tracked in {name}, "
              f"{len(ours)} {'was a Complete Response Letter' if len(ours) == 1 else 'were Complete Response Letters'}."
              + inferred_note(INFERRED.get(f"{y}-{m:02d}", 0), f"in {name}"))
    desc = (f"FDA complete response letters {name}: {n} released by the FDA (openFDA), {len(ours)} among the PDUFA "
            f"decisions pdufa.bio tracked. Counts and sources only.")[:158]
    which = []
    if ours:
        which.append(f"Among the PDUFA decisions pdufa.bio tracked in {name}, the FDA issued Complete Response Letters "
                     f"for " + "; ".join((f"{page_drug(href)} ({t}, FDA action {iso})" if page_drug(href)
                                          else f"{t} (FDA action {iso})") for iso, t, _, href in sorted(ours)) + ".")
    if letters:
        cos = []
        for l in sorted(letters, key=lambda x: x["iso"]):
            c = short_company(l["company"])
            if c and c not in cos:
                cos.append(c)
        which.append(f"The FDA's own release holds {n} letter{'s' if n != 1 else ''} dated {name}, sent to "
                     + ", ".join(cos) + ".")
    if not which:
        which.append(f"None so far: no tracked PDUFA decision in {name} was a Complete Response Letter, and the FDA's "
                     f"release holds no letter dated {name}" + (f" as of {upd}" if upd else "") + ".")
    rows = "".join(f'<tr><td class="dt">{l["iso"]}</td><td>{esc(l["company"][:48])}</td><td>{esc(l["app"][:28])}</td>'
                   f'<td>{esc(l["status"])}</td><td><a href="{esc(l["url"])}" rel="noopener">letter (PDF)</a>'
                   + (f' &middot; <a href="/crl/letter/{TEXT[(l["fn"], l["iso"])]}">its text</a>'
                      if l.get("cr") and (l.get("fn"), l["iso"]) in TEXT else '') + '</td></tr>'
                   for l in sorted(letters, key=lambda x: x["iso"], reverse=True))
    trows = "".join(f'<tr><td class="dt">{iso}</td><td>{esc(t)}</td><td>{esc(drug_cell(drug, href))}</td>'
                    f'<td><a href="{href}">decision page</a></td></tr>' for iso, t, drug, href in sorted(ours, reverse=True))
    nav = " &middot; ".join(x for x in (
        f'<a href="/crl/{prev_[0]}/{MON[prev_[1] - 1]}">&larr; {MON[prev_[1] - 1].capitalize()} {prev_[0]}</a>' if prev_ else "",
        f'<a href="/crl/{next_[0]}/{MON[next_[1] - 1]}">{MON[next_[1] - 1].capitalize()} {next_[0]} &rarr;</a>' if next_ else "",
        f'<a href="/crl/{y}">all of {y}</a>', '<a href="/crl">all released letters</a>',
        '<a href="/decisions/crl">every CRL decision we tracked</a>') if x)
    faq = {"@context": "https://schema.org", "@type": "FAQPage", "url": url, "mainEntity": [
        {"@type": "Question", "name": f"How many FDA complete response letters were issued in {name}?",
         "acceptedAnswer": {"@type": "Answer", "text": first}},
        {"@type": "Question", "name": f"Which companies and drugs received FDA complete response letters in {name}?",
         "acceptedAnswer": {"@type": "Answer", "text": " ".join(which)}}]}
    crumbs = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "CRL letters", "item": f"{BASE}/crl"},
        {"@type": "ListItem", "position": 2, "name": str(y), "item": f"{BASE}/crl/{y}"},
        {"@type": "ListItem", "position": 3, "name": name, "item": url}]}
    css = ("*{box-sizing:border-box}body{margin:0;background:#02060d;color:#f2f6fc;font-family:-apple-system,"
           "BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;line-height:1.55}a{color:#6fb6ff;"
           "text-decoration:none}a:hover{text-decoration:underline}.wrap{max-width:900px;margin:0 auto;padding:22px 18px 60px}"
           ".top{display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #1a3358;"
           "padding-bottom:12px}.brand{font-size:19px;font-weight:800}.brand b{color:#e3ba5e}.nav a{color:#a7bcd9;"
           "font-size:13px;margin-left:14px}h1{font-size:26px;line-height:1.2;margin:10px 0 8px}h2{font-size:17px;"
           "color:#e3ba5e;margin:24px 0 8px}.sub{color:#a7bcd9;font-size:15px;margin:6px 0 14px;max-width:76ch}"
           "table{width:100%;border-collapse:collapse;font-size:13.5px}th{text-align:left;color:#e3ba5e;font-size:11.5px;"
           "text-transform:uppercase;letter-spacing:.4px;padding:7px 6px;border-bottom:1px solid #294d80}td{padding:7px 6px;"
           "border-bottom:1px solid #14263f;color:#a7bcd9;vertical-align:top}td.dt{color:#f2f6fc;white-space:nowrap}")
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" '
            f'content="width=device-width,initial-scale=1,viewport-fit=cover"><title>{esc(title)}</title>'
            f'<meta name="description" content="{esc(desc)}"><link rel="canonical" href="{url}">'
            f'<meta name="robots" content="index,follow,max-image-preview:large"><meta property="og:type" content="website">'
            f'<meta property="og:site_name" content="pdufa.bio"><meta property="og:url" content="{url}">'
            f'<meta property="og:title" content="{esc(title.split(" | ")[0])}"><meta property="og:description" '
            f'content="{esc(desc)}"><script type="application/ld+json">{json.dumps(crumbs)}</script>'
            f'<script type="application/ld+json">{json.dumps(faq, ensure_ascii=False)}</script><style>{css}</style></head>'
            f'<body><div class="wrap"><div class="top"><a class="brand" href="/">pdufa<b>.bio</b></a><div class="nav">'
            f'<!--NAVC:BEGIN--><!--NAVC:END--></div></div>'
            f'<div style="font-size:12px;color:#94a9c9;margin:16px 0 4px"><a href="/" style="color:#94a9c9">Home</a> &rsaquo; '
            f'<a href="/crl" style="color:#94a9c9">CRL letters</a> &rsaquo; '
            f'<a href="/crl/{y}" style="color:#94a9c9">{y}</a> &rsaquo; {MON[m - 1].capitalize()}</div>'
            f'<h1>FDA complete response letters, {name}</h1>'
            f'<!--CRLLEDE:BEGIN--><p class="sub" style="color:#cfe0f5">{esc(first)}</p><!--CRLLEDE:END-->'
            f'<p class="sub">{esc(" ".join(which))}</p>'
            f'<h2>Released by the FDA, dated {name} &middot; {n}</h2>'
            + (f'<table><tr><th>Letter date</th><th>Company</th><th>Application</th><th>openFDA status</th><th>Letter</th></tr>'
               f'{rows}</table>' if n else f'<div class="sub">None in the release as of its last update{(" (" + esc(upd) + ")") if upd else ""}.</div>')
            + f'<h2>Complete Response Letters among decisions pdufa.bio tracked &middot; {len(ours)}</h2>'
            + (f'<table><tr><th>FDA action</th><th>Ticker</th><th>Drug</th><th>Source</th></tr>{trows}</table>' if ours
               else f'<div class="sub">None: the {n_dec} tracked decision{"s" if n_dec != 1 else ""} this month '
                    f'{"was an approval" if n_dec == 1 else "were approvals" if n_dec else "(no tracked decisions)"}.</div>')
            + f'<div class="sub" style="font-size:13px;margin-top:18px">A Complete Response Letter is the FDA&#x27;s notice that it '
              f'will not approve an application in its current form; it is not a permanent rejection, and the sponsor can '
              f'resubmit. The two counts come from different records and are not added together. {nav}</div>'
            + '</div></body></html>')


def year_page(y, months_here, by, ours, alld, upd, years):
    """/crl/{year} (2026-11-24): the year a month page's breadcrumb names had no page. Two tables, two records, never
    added together: letters in the FDA's release by letter date, and CRLs among the PDUFA decisions pdufa.bio tracked
    by FDA action date. Counts per month link to each month page."""
    url = f"{BASE}/crl/{y}"
    keys = [f"{y}-{m:02d}" for m in months_here]
    letters = [l for k in keys for l in by.get(k, [])]
    trk = [o for k in keys for o in ours.get(k, [])]
    ndec = sum(alld.get(k, 0) for k in keys)
    last = MON[months_here[-1] - 1].capitalize()
    span = f"January to {last} {y}" if months_here[-1] != 12 else f"{y}"
    first = (f"The FDA's public release of complete response letters holds {len(letters)} letter"
             f"{'s' if len(letters) != 1 else ''} dated {span}" + (f" (openFDA, last updated {upd})" if upd else "")
             + f". Of the {ndec} FDA decisions on PDUFA goal dates pdufa.bio tracked in {span}, {len(trk)} "
             + ("was a Complete Response Letter." if len(trk) == 1 else "were Complete Response Letters.")
             + inferred_note(sum(INFERRED.get(k, 0) for k in keys), f"in {span}"))
    title = f"FDA Complete Response Letters {y}: {len(trk)} Tracked CRLs, {len(letters)} Released Letters | pdufa.bio"
    desc = (f"FDA complete response letters of {y} by month: {len(letters)} in the FDA's release (openFDA) and "
            f"{len(trk)} among PDUFA decisions pdufa.bio tracked. Sources linked.")
    if len(desc) > 158:
        desc = f"FDA complete response letters {y} by month: {len(letters)} released, {len(trk)} tracked CRLs."
    mrows = "".join(f'<tr><td class="dt"><a href="/crl/{y}/{MON[m - 1]}">{MON[m - 1].capitalize()}</a></td>'
                    f'<td>{len(by.get(f"{y}-{m:02d}", []))}</td><td>{len(ours.get(f"{y}-{m:02d}", []))}</td>'
                    f'<td>{alld.get(f"{y}-{m:02d}", 0)}</td></tr>' for m in reversed(months_here))
    trows = "".join(f'<tr><td class="dt">{iso}</td><td>{esc(t)}</td><td>{esc(drug_cell(drug, href))}</td>'
                    f'<td><a href="{href}">decision page</a></td></tr>' for iso, t, drug, href in sorted(trk, reverse=True))
    lrows = "".join(f'<tr><td class="dt">{l["iso"]}</td><td>{esc(l["company"][:48])}</td><td>{esc(l["app"][:28])}</td>'
                    f'<td><a href="{esc(l["url"])}" rel="noopener">letter (PDF)</a>'
                    + (f' &middot; <a href="/crl/letter/{TEXT[(l["fn"], l["iso"])]}">its text</a>'
                       if l.get("cr") and (l.get("fn"), l["iso"]) in TEXT else '') + '</td></tr>'
                    for l in sorted(letters, key=lambda x: x["iso"], reverse=True))
    other = " &middot; ".join(f'<a href="/crl/{yy}">{yy}</a>' for yy in years if yy != y)
    faq = {"@context": "https://schema.org", "@type": "FAQPage", "url": url, "mainEntity": [
        {"@type": "Question", "name": f"How many FDA complete response letters were issued in {y}?",
         "acceptedAnswer": {"@type": "Answer", "text": first}}]}
    crumbs = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "CRL letters", "item": f"{BASE}/crl"},
        {"@type": "ListItem", "position": 2, "name": str(y), "item": url}]}
    doc = page(y, months_here[-1], [], [], 0, upd, None, None)           # same shell, styles and nav slots
    head_end = doc.index("</head>")
    shell_head = doc[:head_end]
    shell_head = re.sub(r"<title>.*?</title>", f"<title>{esc(title)}</title>", shell_head, count=1, flags=re.S)
    for a_, b_ in ((r'<meta name="description" content="[^"]*"', f'<meta name="description" content="{esc(desc)}"'),
                   (r'<meta property="og:description" content="[^"]*"', f'<meta property="og:description" content="{esc(desc)}"'),
                   (r'<meta property="og:title" content="[^"]*"', f'<meta property="og:title" content="{esc(title.split(" | ")[0])}"'),
                   (r'<link rel="canonical" href="[^"]*"', f'<link rel="canonical" href="{url}"'),
                   (r'<meta property="og:url" content="[^"]*"', f'<meta property="og:url" content="{url}"')):
        shell_head = re.sub(a_, lambda _m, b_=b_: b_, shell_head, count=1)
    shell_head = re.sub(r'<script type="application/ld\+json">.*?</script><script type="application/ld\+json">.*?</script>',
                        lambda _m: f'<script type="application/ld+json">{json.dumps(crumbs)}</script>'
                                   f'<script type="application/ld+json">{json.dumps(faq, ensure_ascii=False)}</script>',
                        shell_head, count=1, flags=re.S)
    body = (f'<body><div class="wrap"><div class="top"><a class="brand" href="/">pdufa<b>.bio</b></a><div class="nav">'
            f'<!--NAVC:BEGIN--><!--NAVC:END--></div></div>'
            f'<div style="font-size:12px;color:#94a9c9;margin:16px 0 4px"><a href="/" style="color:#94a9c9">Home</a> &rsaquo; '
            f'<a href="/crl" style="color:#94a9c9">CRL letters</a> &rsaquo; {y}</div>'
            f'<h1>FDA complete response letters, {y}</h1>'
            f'<!--CRLYEARLEDE:BEGIN--><p class="sub" style="color:#cfe0f5">{esc(first)}</p><!--CRLYEARLEDE:END-->'
            f'<h2>By month</h2><table><tr><th>Month</th><th>Released by the FDA</th><th>CRLs among tracked decisions</th>'
            f'<th>Tracked decisions</th></tr>{mrows}</table>'
            f'<h2>Complete Response Letters among decisions pdufa.bio tracked &middot; {len(trk)}</h2>'
            + (f'<table><tr><th>FDA action</th><th>Ticker</th><th>Drug</th><th>Source</th></tr>{trows}</table>' if trk
               else '<div class="sub">None.</div>')
            + f'<h2>Released by the FDA, dated {y} &middot; {len(letters)}</h2>'
            + (f'<table><tr><th>Letter date</th><th>Company</th><th>Application</th><th>Letter</th></tr>{lrows}</table>'
               if letters else '<div class="sub">None in the release as of its last update.</div>')
            + f'<div class="sub" style="font-size:13px;margin-top:18px">The FDA publishes these letters in batches after '
              f'they are issued, so the latest months may hold fewer released letters than were sent. The two counts come '
              f'from different records and are not added together. '
            + (f'Other years: {other} &middot; ' if other else '')
            + '<a href="/crl">all released letters</a> &middot; <a href="/decisions/crl">every CRL decision we tracked</a>'
              '</div></div></body></html>')
    return shell_head + "</head>" + body


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); a = ap.parse_args()
    letters, upd = corpus()
    ours, alld = tracked()
    by = collections.defaultdict(list)
    for l in letters:
        by[l["iso"][:7]].append(l)
    td = eastern_today()
    months, y, m = [], 2025, 1
    while (y, m) <= (td.year, td.month):
        months.append((y, m)); m += 1
        if m == 13:
            y, m = y + 1, 1
    months = sorted(set(months) | {(int(k[:4]), int(k[5:])) for k in by if k >= "2025-01"})
    written = []
    for i, (y, m) in enumerate(months):
        k = f"{y}-{m:02d}"
        doc = page(y, m, by.get(k, []), ours.get(k, []), alld.get(k, 0), upd,
                   months[i - 1] if i else None, months[i + 1] if i + 1 < len(months) else None)
        p = os.path.join(SITE, "crl", str(y), MON[m - 1], "index.html")
        written.append((y, m, len(by.get(k, [])), len(ours.get(k, []))))
        if not a.dry_run:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            io.open(p, "w", encoding="utf-8").write(doc)
    years = sorted({y for y, _ in months})
    for y in years:
        here = [m for yy, m in months if yy == y]
        doc = year_page(y, here, by, ours, alld, upd, years)
        if not a.dry_run:
            io.open(os.path.join(SITE, "crl", str(y), "index.html"), "w", encoding="utf-8").write(doc)
        print(f"  /crl/{y}: {sum(len(by.get(f'{y}-{m:02d}', [])) for m in here)} released, "
              f"{sum(len(ours.get(f'{y}-{m:02d}', [])) for m in here)} tracked CRLs")
    # month index on /crl
    hub = os.path.join(SITE, "crl", "index.html")
    h = io.open(hub, encoding="utf-8").read()
    chips = " ".join(f'<a href="/crl/{y}/{MON[m - 1]}" style="display:inline-block;padding:4px 9px;margin:2px;'
                     f'border:1px solid #1a3358;border-radius:7px;font-size:12.5px">{MON[m - 1][:3].capitalize()} {y} '
                     f'<b>{n}</b>{(" / " + str(o)) if o else ""}</a>' for y, m, n, o in reversed(written))
    ylinks = " &middot; ".join(f'<a href="/crl/{y}">{y}</a>' for y in reversed(years))
    blk = (f'{B}<h2>By month</h2><div class="sub" style="font-size:13px">By year: {ylinks}. Letters in the FDA release dated each month '
           f'(after the slash: CRLs among the decisions pdufa.bio tracked that month).</div><div>{chips}</div>{E}')
    h = re.sub(re.escape(B) + ".*?" + re.escape(E), lambda _: blk, h, flags=re.S) if B in h else \
        h.replace("<h2>What the FDA has released", blk + "<h2>What the FDA has released", 1)
    if not a.dry_run:
        io.open(hub, "w", encoding="utf-8").write(h)
    for y, m, n, o in written[-4:]:
        print(f"  /crl/{y}/{MON[m - 1]:9s} released {n}, tracked CRLs {o}")
    print(f"crl month pages: {len(written)} (release last updated {upd})" + (" [dry run]" if a.dry_run else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
