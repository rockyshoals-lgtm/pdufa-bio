# -*- coding: utf-8 -*-
"""build_decision_faq.py -- 'Was {drug} approved?' answered on every sourced decision page.

Red team 2026-08-12g, section 5.3: ~286 sourced decision pages can each carry the exact-match
answer to the highest-intent query in the category -- 'was X approved' / 'did X get FDA
approval' -- each backed by the citation the page already links. Same mechanism that gives
/drug/rusfertide its 16.67% AI citation share, applied to the archive.

Rules, in the house discipline:
  - SOURCED pages only. A page still carrying the price-only banner answers no question as
    fact, so it gets no FAQ; the honest banner stays alone.
  - Everything comes from the page itself: outcome from its own title, drug from its Drug row
    (or the listing's row text where the page predates the Drug row), source from the page's
    linked citation. Nothing is invented here.
  - CRL phrasing per the plain-language spec: 'declined to approve in its current form',
    never 'rejected' (guard 41 enforces this everywhere anyway).

Idempotent via DFAQ markers; daily in CI after the verification/upgrade steps.

    python build_decision_faq.py [--dry-run]
"""
import argparse, glob, html, json, os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
BASE = "https://www.pdufa.bio"
B, E = "<!--DFAQ:BEGIN-->", "<!--DFAQ:END-->"
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]


def pretty(d):
    return f"{MONTHS[int(d[5:7]) - 1]} {int(d[8:10])}, {d[:4]}"


def listing_drugs():
    """(ticker, date) -> drug text from the /decisions listing rows, as fallback naming."""
    out = {}
    p = os.path.join(SITE, "decisions", "index.html")
    if not os.path.exists(p):
        return out
    doc = open(p, encoding="utf-8", errors="replace").read()
    for m in re.finditer(r'href="/fda-decision/([A-Z]+)-(\d{4}-\d{2}-\d{2})"[^>]*>(.*?)</a>',
                         doc, re.S):
        txt = html.unescape(re.sub(r"<[^>]+>", " ", m.group(3)))
        body = re.split(r"(?:Approved|CRL)\s*:?\s*", txt, maxsplit=1)
        if len(body) > 1:
            d = re.sub(r"\s+", " ", body[1]).strip(" :")
            if d and "price-only" not in d.lower():
                out[(m.group(1), m.group(2))] = d[:70]
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    fallback = listing_drugs()

    added = kept = skipped = 0
    for p in sorted(glob.glob(os.path.join(SITE, "fda-decision", "*", "index.html"))):
        doc = open(p, encoding="utf-8", errors="replace").read()
        slug = os.path.basename(os.path.dirname(p))
        m = re.match(r"([A-Z]+)-(\d{4}-\d{2}-\d{2})$", slug)
        if not m:
            continue
        tk, date = m.groups()
        low = doc.lower()
        # sourced pages only: no price-inference language, and an external citation present
        if ("price-only" in low or "outcome unverified" in low
                or not re.search(r'href="https?://(?!www\.pdufa\.bio)', doc)):
            skipped += 1
            continue
        t = re.search(r"<title>[A-Z]+ FDA Decision [^:]+: (Approved|Complete Response Letter"
                      r"|CRL)", doc)
        if not t:
            skipped += 1
            continue
        outcome = "Approved" if t.group(1) == "Approved" else "CRL"
        dm = re.search(r"<span>Drug(?: / candidate)?</span><b>([^<]+)</b>", doc)
        drug = html.unescape(dm.group(1)).strip() if dm else fallback.get((tk, date), "")
        if not drug:
            skipped += 1
            continue                       # no honest name to ask the question with
        drug = re.sub(r"\s+", " ", drug)[:70]

        q = f"Was {drug} approved by the FDA?"
        if outcome == "Approved":
            ans = (f"Yes. The FDA approved the application for {drug} on {pretty(date)}. "
                   f"The primary source is linked on this page.")
        else:
            ans = (f"Not in this review cycle. On {pretty(date)} the FDA issued a Complete "
                   f"Response Letter, declining to approve the application for {drug} in its "
                   f"current form. A CRL is not final; the primary source is linked on this "
                   f"page.")

        blk = (B + '<section style="max-width:820px;margin:24px auto 0">'
               f'<h2 style="font-size:17px;margin:0 0 4px">Question</h2>'
               f'<h3 style="font-size:14.5px;margin:10px 0 3px">{html.escape(q)}</h3>'
               f'<p style="margin:0;font-size:14px;line-height:1.6;opacity:.85">'
               f'{html.escape(ans)}</p></section>'
               '<script type="application/ld+json">'
               + json.dumps({"@context": "https://schema.org", "@type": "FAQPage",
                             "url": f"{BASE}/fda-decision/{slug}",
                             "mainEntity": [{"@type": "Question", "name": q,
                                             "acceptedAnswer": {"@type": "Answer",
                                                                "text": ans}}]},
                            separators=(",", ":")) + "</script>" + E)
        if B in doc:
            doc2 = re.sub(re.escape(B) + ".*?" + re.escape(E), lambda _: blk, doc, flags=re.S)
            kept += 1
        else:
            anchor = "<footer" if "<footer" in doc else '<div class="legal"'
            if anchor not in doc:
                anchor = "</body>"
            doc2 = doc.replace(anchor, blk + anchor, 1)
            added += 1
        if doc2 != doc and not a.dry_run:
            open(p, "w", encoding="utf-8").write(doc2)

    print(f"decision FAQs: {added} added, {kept} refreshed, {skipped} skipped "
          f"(unsourced/unnamed stay silent)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
