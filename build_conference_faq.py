# -*- coding: utf-8 -*-
"""build_conference_faq.py -- FAQPage + visible Q&A on the 14 per-conference pages.

Console read 2026-08-18c item 7: the /conference/{CODE} pages still carry Question=0 while
FAQ-bearing pages are what the AI-citation channel (115 -> 413 in six days) actually quotes.
These pages are static artifacts of the initial import -- no generator owns them -- so this is
a marker-based injector in the house pattern (idempotent via CFAQ markers), and every answer is
a fact the site already holds:

  - dates/city come from conferences.json (each entry carries its organiser source URL),
  - presenters come through the SAME gate build_conferences.py applies to the page and
    sync_conferences_to_api.py applies to the API -- one selection, three surfaces,
  - the "why it matters" answer links the published conference run-up study rather than
    asserting numbers inline.

A question we cannot answer from held data is skipped, not padded.

    python build_conference_faq.py [--dry-run]
"""
import argparse, datetime as dt, glob, json, os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
B, E = "<!--CFAQ:BEGIN-->", "<!--CFAQ:END-->"
SB, SE = "<!--CFAQS:BEGIN-->", "<!--CFAQS:END-->"

import build_conferences as BC

MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]


def esc(s):
    return (str(s or "").replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def human(d):
    y, m, day = int(d[:4]), int(d[5:7]), int(d[8:10])
    return f"{MONTHS[m - 1]} {day}, {y}"


def span(c):
    s, e = str(c.get("start", "")), str(c.get("end", ""))
    if not s:
        return ""
    if not e or e == s:
        return human(s)
    if s[:7] == e[:7]:
        return f"{MONTHS[int(s[5:7]) - 1]} {int(s[8:10])}–{int(e[8:10])}, {s[:4]}"
    return f"{human(s)} – {human(e)}"


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    confs = json.load(open(os.path.join(HERE, "conferences.json"),
                           encoding="utf-8")).get("conferences", [])
    by_code = {}
    for c in confs:
        by_code.setdefault(str(c.get("code", "")).upper(), []).append(c)
    presenters = BC.load_presenters()
    today = dt.date.today().isoformat()

    done = 0
    for p in sorted(glob.glob(os.path.join(SITE, "conference", "*", "index.html"))):
        code = os.path.basename(os.path.dirname(p)).upper()
        editions = sorted(by_code.get(code, []), key=lambda c: str(c.get("start", "")))
        nxt = next((c for c in editions if str(c.get("start", "")) >= today),
                   editions[-1] if editions else None)
        if not nxt:
            continue
        name = nxt.get("name") or code
        year = str(nxt.get("start", ""))[:4]

        qa = []
        when = span(nxt)
        if when:
            a1 = (f"{name} {year} runs {when}"
                  + (f" in {nxt['city']}" if nxt.get("city") else "")
                  + ". The date comes from the organiser's own announcement; check the "
                    "organiser's site for the final programme.")
            qa.append((f"When is {code} {year}?", a1))

        pres = BC.presenters_for(nxt, presenters) if hasattr(BC, "presenters_for") else []
        if pres:
            tks = sorted({str(x.get("ticker", "")).upper() for x in pres if x.get("ticker")})
            a2 = (f"From company filings and releases we have sourced "
                  f"{len(pres)} presenter commitment{'s' if len(pres) != 1 else ''} for this "
                  f"edition: {', '.join(tks)}. This is not the organiser's programme -- only "
                  f"presentations companies have themselves announced, each linked to its "
                  f"filing on the conferences page.")
        else:
            a2 = ("None sourced yet. We list a company as presenting only when its own SEC "
                  "filing or press release commits to this edition -- abstract titles and "
                  "rumours don't qualify. The conferences page updates as filings land.")
        qa.append((f"Which biotech companies are presenting at {code} {year}?", a2))

        qa.append((
            "Why do medical conference dates matter for biotech stocks?",
            "Trial results are often presented first at medical meetings, so a company's "
            "announced presentation is a dated, public catalyst. We publish a study of how "
            "biotech stocks have historically traded into conference presentations on the "
            "research page; it is historical measurement, not a prediction, and none of this "
            "is investment advice."))

        jsonld = json.dumps({"@context": "https://schema.org", "@type": "FAQPage",
                             "mainEntity": [{"@type": "Question", "name": q,
                                             "acceptedAnswer": {"@type": "Answer", "text": ans}}
                                            for q, ans in qa]}, ensure_ascii=False)
        cards = "".join(
            f'<div class="card" style="background:#0c1d38;border:1px solid #1e3a63;'
            f'border-radius:12px;padding:14px 16px;margin:12px 0"><b>{esc(q)}</b>'
            f'<div style="color:#9db3d4;font-size:14px;margin-top:6px">{esc(ans)}</div></div>'
            for q, ans in qa)
        block = (f'{B}<h2 style="font-size:18px;color:#f0c86a;margin:26px 0 8px">FAQ</h2>'
                 f'{cards}{E}')
        sblock = f'{SB}<script type="application/ld+json">{jsonld}</script>{SE}'

        doc = open(p, encoding="utf-8", errors="replace").read()
        if B in doc:
            doc = re.sub(re.escape(B) + ".*?" + re.escape(E), block, doc, count=1, flags=re.S)
        else:
            # these pages close with a legal-footer DIV inside </main>, not a <footer> tag
            i = doc.find("Not affiliated with or endorsed by the FDA")
            i = doc.rfind("<div", 0, i) if i > 0 else doc.rfind("</main>")
            if i < 0:
                continue
            doc = doc[:i] + block + doc[i:]
        if SB in doc:
            doc = re.sub(re.escape(SB) + ".*?" + re.escape(SE), sblock, doc, count=1,
                         flags=re.S)
        else:
            doc = doc.replace("</head>", sblock + "</head>", 1)
        if not a.dry_run:
            open(p, "w", encoding="utf-8").write(doc)
        done += 1
        print(f"  {code}: {len(qa)} question(s) ({year}, "
              f"{len(pres) if pres else 0} sourced presenter(s))")

    print(f"conference FAQ on {done} page(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
