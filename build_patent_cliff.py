# -*- coding: utf-8 -*-
"""build_patent_cliff.py -- /patent-cliff: 427 brand drugs losing protection 2026-2031, daily.

Red team 2026-08-12e delivered the dataset (patent_cliff_2026_2031_TA.csv: Orange Book LOE
aggregation, 97% ATC-classified, their own classifier red-teamed -- the BALCOLTRA
contraceptive-as-Cancer defect found and fixed before delivery) and the full copy pack. This
builds the surface exactly to that pack:

    /patent-cliff                     hub: by year, by company, by family
    /patent-cliff/{2026..2031}        year pages
    /patent-cliff/company/{slug}      companies with 5+ cliffs
    /patent-cliff/{family-slug}       families with 12+ cliffs
    /drug/{name}                      'Patent protection' module where a cliff matches a page

Non-negotiables, from the pack and the plain-language spec:
  - EVERY cliff page carries the disclosure: earliest date a generic could enter, not a
    guarantee; settlements are not in this data. Guard 41's dormant LOE rule arms on these
    pages the moment they exist.
  - No prediction, no 'company needs to' -- state the drug, the date, the patent count, stop.
  - Jargon in the URL/title because it IS the query; plain English in the first sentence.
  - Families are filters, not claims (the tafamidis limitation): drug rows lead with names
    and dates; the family is navigation.

    python build_patent_cliff.py [--dry-run]
"""
import argparse, collections, csv, datetime as dt, html, json, os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
CSVP = os.path.join(HERE, "patent_cliff_2026_2031_TA.csv")
BASE = "https://www.pdufa.bio"
TODAY = dt.datetime.now(dt.timezone.utc).date().isoformat()
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]

DISCLOSURE = (
    '<div style="background:rgba(240,200,106,.08);border:1px solid #6b5a2f;border-radius:10px;'
    'padding:12px 14px;margin:16px 0;font-size:13.5px;line-height:1.6;color:#e8d9a8">'
    '<b>This is the earliest date a generic could enter; it is not a guarantee one will.</b> '
    'We calculate it as the later of the last patent the company listed with the FDA and the '
    'last regulatory exclusivity. Companies often reach settlement agreements with generic '
    'makers for a different date, and those agreements are not public in this data.</div>')

SHELL = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{canon}">
<meta name="robots" content="index,follow,max-image-preview:large">
<link rel="preload" href="/fonts/SpaceGrotesk-700.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="/fonts/fonts.css">
<style>
:root{{--bg:#0b1017;--line:#1f2a3c;--mut2:#8fa3bd;--gold:#e8b44c}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:#dfe9f7;
font:15px/1.65 "IBM Plex Mono",ui-monospace,monospace}}
.wrap{{max-width:900px;margin:0 auto;padding:18px 16px 60px}}
.top{{display:flex;justify-content:space-between;align-items:center;margin-bottom:22px}}
.brand{{font-family:"Space Grotesk",sans-serif;font-weight:700;font-size:20px;color:#fff;
text-decoration:none}}.brand b{{color:var(--gold)}}
.nav a{{color:var(--mut2);text-decoration:none;margin-left:14px;font-size:13px}}
h1{{font-family:"Space Grotesk",sans-serif;font-size:26px;margin:0 0 6px}}
h2{{font-family:"Space Grotesk",sans-serif;font-size:17px;margin:26px 0 8px}}
p{{max-width:74ch}}
.row{{display:flex;flex-wrap:wrap;gap:10px;justify-content:space-between;padding:10px 0;
border-top:1px solid var(--line);color:inherit;text-decoration:none}}
.row:hover{{background:#141d2d}}
.t{{font-weight:600}}.d{{color:var(--mut2);font-size:13px}}
a.lit{{color:#9ec5ff;text-decoration:none}}
.chip{{display:inline-block;border:1px solid #2a496f;border-radius:16px;padding:3px 11px;
margin:3px 6px 3px 0;font-size:12.5px;color:#a7bcd9;text-decoration:none}}
.chip:hover{{border-color:var(--gold);color:#eef4fc}}
.legal{{margin-top:40px;padding-top:14px;border-top:1px solid var(--line);color:var(--mut2);
font-size:12px;line-height:1.7}}
</style>{extra}</head><body><div class="wrap">
<div class="top"><a class="brand" href="/">pdufa<b>.bio</b></a>
<div class="nav"><a href="/calendar">Calendar</a><a href="/decisions">Decisions</a>
<a href="/patent-cliff">Patent Cliff</a></div></div>
{body}
<div class="legal">Dates from the FDA Orange Book, the official record of which patents cover
which approved drug; updated monthly. Facts only, not investment advice. Verify against the
Orange Book and primary filings. pdufa.bio is not affiliated with the FDA.</div>
</div></body></html>
"""


def esc(s):
    return html.escape(str(s or ""), quote=True)


def _fit_desc(s, limit=158):
    """Trim a description at a word boundary only when it actually exceeds the limit."""
    if len(s) <= limit:
        return s
    return s[:limit].rsplit(" ", 1)[0].rstrip(".,;") + "."


def slugify(s):
    return re.sub(r"-{2,}", "-", re.sub(r"[^a-z0-9]+", "-", str(s).lower())).strip("-")[:50]


def pretty(d):
    return f"{MONTHS[int(d[5:7]) - 1]} {int(d[8:10])}, {d[:4]}"


def tc(s):
    """Company/brand casing for prose: ORANGE BOOK ALLCAPS -> Title Case, keep short caps.
    Legal-name tails are cut: 'MERCK SHARP AND DOHME LLC A SUB OF MERCK AND CO INC' made a
    102-char title and an unlinkable slug. The registrant's operating name is the fact a
    reader needs; the Orange Book row keeps the legal form."""
    s = re.sub(r"\s+A SUB(?:SIDIARY)? OF .*$", "", str(s), flags=re.I)
    s = re.sub(r"\b(LLC|INC|CORP|CO|LTD|LP|PLC|SA|AG|DESIGNATED ACTIVITY CO)\b\.?\s*$", "",
               s.strip(), flags=re.I).strip(" ,.")
    out = []
    for w in s.split():
        out.append(w if (len(w) <= 3 and w.isupper() and w.isalpha()) or any(c.isdigit() for c in w)
                   else w.capitalize())
    return " ".join(out)


def faq_block(url, qa):
    vis = ('<h2>Questions</h2>' + "".join(
        f'<h3 style="font-size:14.5px;margin:12px 0 3px">{esc(q)}</h3>'
        f'<p style="margin:0;font-size:14px;opacity:.85">{esc(a)}</p>' for q, a in qa))
    ld = ('<script type="application/ld+json">' + json.dumps(
        {"@context": "https://schema.org", "@type": "FAQPage", "url": url,
         "mainEntity": [{"@type": "Question", "name": q,
                         "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in qa]},
        separators=(",", ":")) + "</script>")
    return vis + ld


def drug_rows(rows):
    out = []
    for r in rows:
        out.append(
            f'<div class="row"><span class="t">{esc(tc(r["brand"]))} '
            f'<span class="d">({esc(r["ingredient"].lower()[:40])})</span></span>'
            f'<span class="d">{esc(tc(r["company"])[:34])} &middot; '
            f'{r["n_patents"]} patent{"s" if r["n_patents"] != "1" else ""} &middot; '
            f'<b style="color:#eef4fc">{pretty(r["loe"])}</b></span></div>')
    return "".join(out)


def write(path, doc, dry):
    if dry:
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf-8").write(doc)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    rows = sorted(csv.DictReader(open(CSVP, encoding="utf-8-sig")), key=lambda r: r["loe"])
    upcoming = [r for r in rows if r["loe"] >= TODAY]
    years = collections.Counter(r["loe"][:4] for r in rows)
    fams = collections.Counter(r["therapeutic_family"] for r in rows
                               if r["therapeutic_family"] not in ("", "Unclassified"))
    cos = collections.Counter(tc(r["company"]) for r in rows)
    top_co = [(c, n) for c, n in cos.most_common() if n >= 5]
    big_fams = [(f, n) for f, n in fams.most_common() if n >= 12]
    n_pages = 0

    # ---- hub -------------------------------------------------------------------------------
    nearest = upcoming[:8]
    yr_chips = "".join(f'<a class="chip" href="/patent-cliff/{y}">{y} &middot; {n}</a>'
                       for y, n in sorted(years.items()))
    co_chips = "".join(f'<a class="chip" href="/patent-cliff/company/{slugify(c)}">'
                       f'{esc(c)} &middot; {n}</a>' for c, n in top_co)
    fam_chips = "".join(f'<a class="chip" href="/patent-cliff/{slugify(f)}">'
                        f'{esc(f)} &middot; {n}</a>' for f, n in big_fams)
    top_faq = faq_block(f"{BASE}/patent-cliff", [
        ("What is a patent cliff?",
         "The point when a drug's patent protection ends and generic manufacturers can apply "
         "to sell the same medicine, usually at a much lower price and usually taking most of "
         "the sales."),
        ("How many drugs lose patent protection between 2026 and 2031?",
         f"{len(rows)} brand-name drugs lose patent protection between 2026 and 2031, per the "
         f"FDA Orange Book."),
        ("Which company has the most patent expirations?",
         f"{top_co[0][0]}, with {top_co[0][1]} drugs losing protection between 2026 and "
         f"2031 in this data."),
        ("Where does this data come from?",
         "The FDA Orange Book, the official record of which patents cover which approved "
         "drug. It updates monthly, and every date here is the later of the last listed "
         "patent and the last regulatory exclusivity.")])
    body = (f"<h1>Patent Cliff Tracker</h1>"
            f'<p><b>{len(rows)} brand-name drugs lose their patent protection between 2026 '
            f"and 2031.</b> When protection ends, generic manufacturers can apply to sell the "
            f"same medicine, usually at a much lower price, and the original maker usually "
            f"loses most of the sales within a year or two. This page tracks which drugs, "
            f"which companies, and when, from the FDA's own Orange Book.</p>"
            + DISCLOSURE
            + "<h2>By year</h2><div>" + yr_chips + "</div>"
            + "<h2>By company (5+ drugs)</h2><div>" + co_chips + "</div>"
            + "<h2>By therapeutic family</h2><div>" + fam_chips + "</div>"
            + "<h2>The nearest cliffs</h2>" + drug_rows(nearest)
            + top_faq)
    write(os.path.join(SITE, "patent-cliff", "index.html"), SHELL.format(
        title="Patent Cliff Tracker: 427 Drugs Losing Protection 2026-2031 | pdufa.bio",
        desc=f"{len(rows)} brand-name drugs lose patent protection between 2026 and 2031, "
             f"from the FDA Orange Book. By year, company and therapeutic family.",
        canon=f"{BASE}/patent-cliff", extra="", body=body), a.dry_run)
    n_pages += 1

    # ---- year pages ------------------------------------------------------------------------
    for y in sorted(years):
        yr = [r for r in rows if r["loe"][:4] == y]
        yfam = collections.Counter(r["therapeutic_family"] for r in yr
                                   if r["therapeutic_family"] not in ("", "Unclassified"))
        bigf, bign = (yfam.most_common(1)[0] if yfam else ("", 0))
        qa = [(f"How many drugs lose patent protection in {y}?",
               f"{len(yr)} brand-name drugs lose patent protection in {y}, per the FDA "
               f"Orange Book."),
              (f"What is the largest therapeutic group in the {y} patent cliff?",
               f"{bigf}, with {bign} drugs." if bigf else
               f"The {y} set spans many therapeutic families; see the list on this page.")]
        body = (f"<h1>{y} Patent Cliff</h1>"
                f"<p><b>{len(yr)} drugs lose patent protection in {y}.</b> "
                + (f"The biggest single group is {esc(bigf)}, with {bign} drugs. " if bigf
                   else "")
                + "Losing protection does not mean a drug disappears: it means other "
                  "manufacturers can apply to sell the same medicine, and the original maker "
                  "usually loses most of the sales within a year or two.</p>"
                + DISCLOSURE + drug_rows(yr) + faq_block(f"{BASE}/patent-cliff/{y}", qa)
                + '<p style="margin-top:18px"><a class="lit" href="/patent-cliff">'
                  "All years &rarr;</a></p>")
        write(os.path.join(SITE, "patent-cliff", y, "index.html"), SHELL.format(
            title=f"{y} Patent Cliff: {len(yr)} Drugs Lose Patent Protection | pdufa.bio",
            desc=f"{len(yr)} brand-name drugs lose patent protection in {y}, from the FDA "
                 f"Orange Book: brand, ingredient, company and the last-patent date.",
            canon=f"{BASE}/patent-cliff/{y}", extra="", body=body), a.dry_run)
        n_pages += 1

    # ---- company pages ---------------------------------------------------------------------
    for co, n in top_co:
        cr = [r for r in rows if tc(r["company"]) == co]
        nx = next((r for r in cr if r["loe"] >= TODAY), cr[-1])
        qa = [(f"How many {co} drugs lose patent protection between 2026 and 2031?",
               f"{n} {co} drugs lose patent protection between 2026 and 2031 in this data."),
              (f"What is {co}'s nearest patent expiration?",
               f"{tc(nx['brand'])} ({nx['ingredient'].lower()[:40]}) on {pretty(nx['loe'])}; "
               f"the company listed {nx['n_patents']} patents on it with the FDA.")]
        body = (f"<h1>{esc(co)} Patent Expirations</h1>"
                f"<p><b>{esc(co)} has {n} drugs losing patent protection between 2026 and "
                f"2031</b> in this data. The nearest is {esc(tc(nx['brand']))} "
                f"({esc(nx['ingredient'].lower()[:40])}) on {pretty(nx['loe'])}; the company "
                f"listed {nx['n_patents']} patents on it with the FDA, and that is the last "
                f"one to expire.</p>" + DISCLOSURE + drug_rows(cr)
                + faq_block(f"{BASE}/patent-cliff/company/{slugify(co)}", qa)
                + '<p style="margin-top:18px"><a class="lit" href="/patent-cliff">'
                  "All companies &rarr;</a></p>")
        write(os.path.join(SITE, "patent-cliff", "company", slugify(co), "index.html"),
              SHELL.format(
                  title=f"{co[:52]} Patent Expirations 2026-2031: {n} Drugs | pdufa.bio",
                  desc=_fit_desc(f"{co} has {n} drugs losing patent protection between 2026 "
                                 f"and 2031, per the FDA Orange Book. Every brand, ingredient "
                                 f"and date."),
                  canon=f"{BASE}/patent-cliff/company/{slugify(co)}", extra="", body=body),
              a.dry_run)
        n_pages += 1

    # ---- family pages ----------------------------------------------------------------------
    for fam, n in big_fams:
        fr = [r for r in rows if r["therapeutic_family"] == fam]
        qa = [(f"How many {fam.lower()} drugs lose patent protection between 2026 and 2031?",
               f"{n} drugs classified under {fam} (WHO ATC) lose patent protection between "
               f"2026 and 2031 in this data.")]
        body = (f"<h1>{esc(fam)}: Patent Cliff 2026-2031</h1>"
                f"<p><b>{n} drugs in the {esc(fam)} family lose patent protection between "
                f"2026 and 2031.</b> The family comes from the WHO ATC classification of each "
                f"drug's ingredient; it is a filter, not a claim about any drug's approved "
                f"indication.</p>" + DISCLOSURE + drug_rows(fr)
                + faq_block(f"{BASE}/patent-cliff/{slugify(fam)}", qa)
                + '<p style="margin-top:18px"><a class="lit" href="/patent-cliff">'
                  "All families &rarr;</a></p>")
        write(os.path.join(SITE, "patent-cliff", slugify(fam), "index.html"), SHELL.format(
            title=f"{fam} Patent Cliff 2026-2031: {n} Drugs | pdufa.bio",
            desc=f"{n} {fam.lower()} drugs lose patent protection between 2026 and 2031, per "
                 f"the FDA Orange Book.",
            canon=f"{BASE}/patent-cliff/{slugify(fam)}", extra="", body=body), a.dry_run)
        n_pages += 1

    # ---- /drug/{name} module ---------------------------------------------------------------
    # Match cliff brands/ingredients against existing drug pages; insert the module the pack
    # calls 'the higher-value half'. Marker-based, idempotent, daily.
    drug_dir = os.path.join(SITE, "drug")
    n_mod = 0
    if os.path.isdir(drug_dir):
        by_slug = {}
        for r in rows:
            by_slug.setdefault(slugify(tc(r["brand"])), r)
            lead = r["ingredient"].split(";")[0].strip()
            lead = re.sub(r"\b(HYDROBROMIDE|HYDROCHLORIDE|SULFATE|HEMIFUMARATE|SODIUM|"
                          r"CALCIUM|MALEATE|TARTRATE|MESYLATE|FUMARATE|CITRATE|ACETATE)\b",
                          "", lead, flags=re.I).strip()
            by_slug.setdefault(slugify(lead.lower()), r)
        for d in os.scandir(drug_dir):
            if not d.is_dir():
                continue
            r = by_slug.get(d.name)
            if not r:
                continue
            p = os.path.join(d.path, "index.html")
            if not os.path.exists(p):
                continue
            doc = open(p, encoding="utf-8", errors="replace").read()
            mod = ('<!--PATMOD:BEGIN--><h2>Patent protection</h2>'
                   f'<p style="max-width:72ch"><b>{esc(tc(r["brand"]))}\'s last listed patent '
                   f'expires {pretty(r["loe"])}.</b> {esc(tc(r["company"]))} listed '
                   f'{r["n_patents"]} patent{"s" if r["n_patents"] != "1" else ""} on it with '
                   f'the FDA. This is the earliest date a generic could enter; it is not a '
                   f'guarantee one will, and settlement agreements are not in this data. '
                   f'<a class="lit" href="/patent-cliff/{r["loe"][:4]}">The '
                   f'{r["loe"][:4]} patent cliff</a>.</p><!--PATMOD:END-->')
            if "PATMOD:BEGIN" in doc:
                doc2 = re.sub(r"<!--PATMOD:BEGIN-->.*?<!--PATMOD:END-->",
                              lambda _: mod, doc, flags=re.S)
            else:
                anchor = "<h2>Questions</h2>"
                if anchor not in doc:
                    continue
                doc2 = doc.replace(anchor, mod + anchor, 1)
            if doc2 != doc and not a.dry_run:
                open(p, "w", encoding="utf-8").write(doc2)
            n_mod += 1

    print(f"patent cliff: {n_pages} pages ({len(rows)} drugs, {len(top_co)} companies, "
          f"{len(big_fams)} families), {n_mod} /drug modules")
    return 0


if __name__ == "__main__":
    sys.exit(main())
