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


_XP = os.path.join(HERE, "_decision_extra_faq.json")
EXTRA = {k: v for k, v in (json.load(open(_XP, encoding="utf-8")) if os.path.exists(_XP) else {}).items()
         if not k.startswith("_")}


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
    # Audit 09-20 P0-A: rows whose decision date is the sponsor's ANNOUNCEMENT day (the filing
    # does not state when the FDA acted) must not be answered "The FDA approved ... on <date>".
    announced = set()
    try:
        srcd = open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8",
                    errors="replace").read().replace("\x00", "")
        rows_d, _ = json.JSONDecoder().raw_decode(srcd[srcd.find("["):])
        announced = {(str(r.get("t") or "").upper(), str(r.get("dcd") or "")[:10])
                     for r in rows_d if (r.get("_d") or {}).get("decision_date_unsourced")}
    except Exception:
        rows_d = []
    # 2026-10-04 red team: the FAQ answered "The FDA approved ... on <page date>", and the page date is
    # the ANNOUNCEMENT day (JUVMO: FDA letter Sep 25, page Sep 28). The FDA's date is used wherever an
    # FDA record holds it (API row fda_action_date, or Drugs@FDA via _fda_action_archive.json); with no
    # FDA record the answer says "was announced", never that the FDA acted that day.
    fda_day = {(str(r.get("t") or "").upper(), str(r.get("dcd") or "")[:10]): str((r.get("_d") or {}).get("fda_action_date"))
               for r in rows_d if (r.get("_d") or {}).get("fda_action_date")
               and not (r.get("_d") or {}).get("decision_date_unsourced")}
    _ap = os.path.join(HERE, "_fda_action_archive.json")
    for _slug, _e in (json.load(open(_ap, encoding="utf-8")) if os.path.exists(_ap) else {}).items():
        _m = re.match(r"([A-Z]{1,6})-(\d{4}-\d{2}-\d{2})$", _slug)
        if _m and _e.get("date"):
            fda_day.setdefault((_m.group(1), _m.group(2)), _e["date"])

    # Drugs@FDA approval dates the decision verifier matched (kind approval, Drugs@FDA source)
    _vp = os.path.join(HERE, "_decision_verification.json")
    for _slug, _v in ((json.load(open(_vp, encoding="utf-8")).get("results") or {}) if os.path.exists(_vp) else {}).items():
        _ev = (_v or {}).get("evidence") or {}
        _m = re.match(r"([A-Z]{1,6})-(\d{4}-\d{2}-\d{2})$", _slug)
        if _m and _ev.get("kind") == "approval" and _ev.get("approval_date") and "Drugs@FDA" in str(_ev.get("source_label")):
            fda_day.setdefault((_m.group(1), _m.group(2)), _ev["approval_date"])

    def art(word):
        return "an" if str(word)[:1].lower() in "aeiou" else "a"

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
        # 2026-10-04: pages built by build_decision_page.py since July carry
        # "TK FDA Decision (Oct 2, 2026): Drug: Approved" (or, after the snippet rewrite, the
        # answer-format title), which the pattern above never matched -- JUVMO, Gazyva, Atebrioz and
        # Jaypirca had no FAQ. The page's own outcome banner is the reliable signal.
        if t:
            outcome = "Approved" if t.group(1) == "Approved" else "CRL"
        elif 'class="ban ap"' in doc:
            outcome = "Approved"
        elif 'class="ban cr"' in doc:
            outcome = "CRL"
        elif re.search(r"<title>[^<]*\b(?:Approved|Approval Announced)\b", doc):
            outcome = "Approved"          # answer-format title on the older template
        elif re.search(r"<title>[^<]*\b(?:CRL|Complete Response)\b", doc):
            outcome = "CRL"
        else:
            skipped += 1
            continue
        dm = re.search(r"<span>Drug(?: / candidate)?</span><b>([^<]+)</b>", doc)
        drug = html.unescape(dm.group(1)).strip() if dm else fallback.get((tk, date), "")
        if not drug:
            skipped += 1
            continue                       # no honest name to ask the question with
        drug = re.sub(r"\s+", " ", drug)[:70]
        sys.path.insert(0, HERE)
        from drug_names import clean_drug_name
        drug = clean_drug_name(drug) or drug     # 4.7: never a cut name ("RP1 ... and OPDIVO (")

        q = f"Was {drug} approved by the FDA?"
        fd = fda_day.get((tk, date))
        ann = (f" The company announced it on {pretty(date)}." if fd and fd != date else "")
        if outcome == "Approved" and (tk, date) in announced:
            ans = (f"Yes. The sponsor announced on {pretty(date)} that the FDA had approved the "
                   f"application for {drug}; the announcement does not state the day the FDA "
                   f"acted. The primary source is linked on this page.")
        elif outcome == "Approved" and fd:
            ans = (f"Yes. The FDA approved the application for {drug} on {pretty(fd)}, per the FDA's "
                   f"own record.{ann} The primary source is linked on this page.")
        elif outcome == "Approved":
            ans = (f"Yes. The approval of the application for {drug} was announced on {pretty(date)}; "
                   f"pdufa.bio holds no FDA record stating the exact day the FDA acted. The primary "
                   f"source is linked on this page.")
        elif fd:
            ans = (f"Not in this review cycle. On {pretty(fd)} the FDA issued a Complete "
                   f"Response Letter, declining to approve the application for {drug} in its "
                   f"current form.{ann} A CRL is not final; the primary source is linked on this page.")
        else:
            ans = (f"Not in this review cycle. A Complete Response Letter, declining to approve the "
                   f"application for {drug} in its current form, was announced on {pretty(date)}. A CRL "
                   f"is not final; the primary source is linked on this page.")

        # Console read 2026-08-18c item 8: 1 -> 3 questions per sourced page, each answered ONLY
        # from facts the page already renders (company row, measured T-120 run-up). A page
        # missing the fact skips the question -- 334 questions became ~1,000 with zero new claims.
        # Two page generations, two kv vocabularies: newer pages carry Company + '120-day
        # run-up'; older ones carry Indication + 'Decision-day move' (the actual reaction --
        # the better fact). Ask only what the page itself renders.
        qa = [(q, ans)]
        cm = re.search(r"<span>Company</span><b>([^<]+)</b>", doc)
        im = re.search(r"<span>Indication</span><b>([^<]+)</b>", doc)
        if cm:
            from drug_names import clean_company
            comp = clean_company(html.unescape(cm.group(1)).strip())
            qa.append((f"Which company is behind {drug}?",
                       f"{drug} is {art(comp)} {comp} ({tk}) program. "
                       + (f"The company announced the FDA decision on {pretty(date)}; "
                          if (tk, date) in announced or not fd else
                          f"The FDA decision came on {pretty(fd)}; ")
                       + ("the company's own announcement is linked on this page."
                          if re.search(r'href="https?://(?!www\.pdufa\.bio|[a-z.]*fda\.gov|www\.sec\.gov|clinicaltrials\.gov)[^"]+"[^>]*>[^<]*(?:announce|release|Lilly|AbbVie|Roche|Mirum|Incyte)', doc, re.I)
                          else "the FDA's own record of the decision is linked on this page."
                          if re.search(r'href="https?://[a-z.]*fda\.gov/', doc)
                          else "the primary source is linked on this page.")))
        elif im and __import__("drug_names").clean_indication(html.unescape(im.group(1))):
            ind = __import__("drug_names").clean_indication(html.unescape(im.group(1)))
            oc_txt = ("approved the application" if outcome == "Approved"
                      else "declined to approve the application in its current form")
            qa.append((f"What was {drug} under FDA review for?",
                       f"The application covered {ind}. The FDA {oc_txt} on {pretty(date)}."))
        mm = re.search(r"<span>Decision-day move</span><b>([^<]+)</b>", doc)
        rm = re.search(r"<span>120-day run-up[^<]*</span><b>([^<]+)</b>", doc)
        if mm:
            mv = html.unescape(mm.group(1)).strip()
            qa.append((f"How did {tk} stock react to the FDA decision?",
                       f"On the decision day {tk} moved {mv}. That is the recorded reaction "
                       f"to this specific event. Historical measurement, not a prediction, "
                       f"and not investment advice."))
        elif rm:
            runup = html.unescape(rm.group(1)).strip()
            qa.append((f"How did {tk} stock trade into the FDA decision?",
                       f"Measured over the 120 trading days before the decision (T-120 to "
                       f"T-1), {tk} moved {runup}. That is the recorded price path into this "
                       f"specific event. Historical measurement, not a prediction, and not "
                       f"investment advice."))

        # 2026-10-04: hand-written, sourced Q&As for a page (_decision_extra_faq.json), each answer a fact
        # stated in the FDA's own document; appended after the generated questions.
        for qq, aa in EXTRA.get(slug, []):
            if qq not in {x for x, _ in qa}:
                qa.append((qq, aa))
        cards = "".join(
            f'<h3 style="font-size:14.5px;margin:10px 0 3px">{html.escape(qq)}</h3>'
            f'<p style="margin:0;font-size:14px;line-height:1.6;opacity:.85">'
            f'{html.escape(aa)}</p>' for qq, aa in qa)
        blk = (B + '<section style="max-width:820px;margin:24px auto 0">'
               f'<h2 style="font-size:17px;margin:0 0 4px">'
               f'Question{"s" if len(qa) > 1 else ""}</h2>{cards}</section>'
               '<script type="application/ld+json">'
               + json.dumps({"@context": "https://schema.org", "@type": "FAQPage",
                             "url": f"{BASE}/fda-decision/{slug}",
                             "mainEntity": [{"@type": "Question", "name": qq,
                                             "acceptedAnswer": {"@type": "Answer", "text": aa}}
                                            for qq, aa in qa]},
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
