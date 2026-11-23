# -*- coding: utf-8 -*-
"""CI guard: /crl/letter/<slug> (build_crl_letters.py) holds every released CRL, in the FDA's own words.

  * One page file per distinct Complete Response Letter in the release (the /crl repeat rule), and no page for a
    letter that is not there. Every slug is the one the committed ledger (_crl_letter_slugs.json) gives it.
  * Each page holds exactly one verbatim block, and it is the letter's text exactly as openFDA released it
    (whitespace aside). No page outside /crl/letter carries the verbatim block (the copy guards skip it only there).
  * Each page's facts table states the release's own fields, read here from the raw corpus without the builder's
    code: letter date, applications, openFDA's company field (or that it is not a readable name), openFDA's status,
    and the rescission. The signature rows equal build_crl_letters.facts, and the (b) (4) row agrees with a
    hand-checked list of letters whose signature prints the mark in OCR forms.
  * The lede names the date, the company where readable and the rescission where there is one; the PDF link is the
    FDA address of the letter's own file; a company link goes to a page that lists this letter (same PDF and date);
    a decision link goes to a page that cites this letter's PDF.
  * Canonical is the page's own address; noindex only when the text is too short to read.
  * The /crl hub and the month pages link each letter page from that letter's own row (same PDF, same date), and
    the link counts stay above a floor (a silent failure would drop them all).
  * Outside the FDA's text and the site's legal footer, and in the title and description, no forecast words.

PLANT=1 changes one letter's text in memory and must FAIL; PLANT=2 puts a second verbatim block on /about and must
FAIL; PLANT=3 says "(b) (4): no" for Capricor's 2025 letter and must FAIL.

    python tests/test_crl_letters.py      (fix: python build_crl_letters.py)
"""
import datetime as dt
import glob
import hashlib
import html
import io
import json
import os
import re
import sys
from urllib.parse import quote

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
SITE = os.path.join(HERE, "pdufa_site_src")
MONTHS = ["", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]
FORECAST = re.compile(r"\b(probabilit|odds\b|chances?\b|likel[yi]|predict|forecast|expected to|will be approved"
                      r"|will likely)", re.I)
# letters whose signature, as released, prints the (b) (4) mark in an OCR form (read by hand, 2026-11-23)
HAND_B4 = {("BL 125842", "2025-07-09"), ("BL 125745", "2025-01-15"), ("BL 125827", "2025-07-21"),
           ("BL 125845", "2025-07-07"), ("BL 125806", "2024-06-14")}
FLOOR = {"company": 150, "decision": 15, "hub": 400, "months": 50}


def text_of(fragment):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def raw_index():
    """{letter key: raw record}, the key rebuilt here from the corpus fields."""
    import build_crl_facts as F
    raw = json.load(io.open(F.CORPUS, encoding="utf-8"))
    out = {}
    for r in (raw.get("results") if isinstance(raw, dict) else raw):
        m = re.match(r"(\d{2})/(\d{2})/(\d{4})$", str(r.get("letter_date") or ""))
        if not m or str(r.get("letter_type") or "") != "COMPLETE RESPONSE":
            continue
        d = dt.date(int(m.group(3)), int(m.group(1)), int(m.group(2)))
        appn = tuple(sorted(str(x).strip() for x in (r.get("application_number") or [])))
        txt = re.sub(r"\s+", " ", str(r.get("text") or "")).strip().lower()
        k = f"{str(r.get('file_name') or '').strip()}|{d.isoformat()}|{','.join(appn)}|" \
            f"{hashlib.sha1(txt.encode('utf-8')).hexdigest()[:8]}"
        out.setdefault(k, dict(r, _date=d, _apps=appn))
    return out


def row_dates(d):
    return {d.isoformat(), f"{MONTHS[d.month]} {d.day}, {d.year}", f"{MONTHS[d.month][:3]} {d.day}, {d.year}"}


def main():
    import build_crl_letters as C
    from build_feeds import crl_letters
    from crl_verbatim import TAG
    letters, _, _ = crl_letters(include_rescinded=True)
    plant = os.environ.get("PLANT")
    if plant == "1":
        letters[0] = dict(letters[0], text=letters[0]["text"] + " planted words")
    if plant == "3":
        letters = [dict(L, sig=dict(L["sig"], withheld=False)) if (L["app_txt"], L["date"].isoformat())
                   == ("BL 125842", "2025-07-09") else L for L in letters]
    sl = C.slugs(letters)
    led = C.load_ledger()
    raw = raw_index()
    by_slug = {v: L for L in letters for k, v in sl.items() if k == L["key"]}
    fails = []
    if not led:
        fails.append("the slug ledger _crl_letter_slugs.json is missing")
    for L in letters:
        if led and led.get(L["key"]) not in (None, sl[L["key"]]):
            fails.append(f"{L['app_txt']} {L['date']}: slug {sl[L['key']]} is not the ledger's {led[L['key']]}")
    have = {os.path.basename(os.path.dirname(p)) for p in glob.glob(os.path.join(C.ROOT, "*", "index.html"))}
    want = set(sl.values())
    if have != want:
        fails.append(f"/crl/letter holds {len(have)} page files for {len(want)} letters "
                     f"(missing {sorted(want - have)[:3]}, extra {sorted(have - want)[:3]})")
    n_comp = n_dec = 0
    for L in letters:
        slug = sl[L["key"]]
        p = os.path.join(C.ROOT, slug, "index.html")
        tag = f"{L['app_txt']} {L['date']}"
        if not os.path.exists(p):
            continue
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        blocks = C.VERBATIM.findall(doc)
        if doc.count(TAG) != 1 or len(blocks) != 1:
            fails.append(f"{tag}: {doc.count(TAG)} verbatim blocks, not 1")
        got = text_of(blocks[0]) if blocks else ""
        if C.norm(L["text"]) and got != C.norm(L["text"]):
            fails.append(f"{tag}: the page's text is not the letter's text as released")
        if blocks and re.search(r"<(?!/?p>)[^>]+>", blocks[0]):
            fails.append(f"{tag}: the verbatim block holds markup other than paragraphs")
        tab = re.search(r'<table data-crl-letter="facts">(.*?)</table>', doc, re.S)
        rows = dict((text_of(a), text_of(b)) for a, b in re.findall(r"<th>(.*?)</th><td>(.*?)</td>",
                                                                     tab.group(1) if tab else "", re.S))
        r = raw.get(L["key"])
        if r is None:
            fails.append(f"{tag}: no raw record has this letter's key")
        else:
            d = r["_date"]
            exp = {"Letter date": f"{MONTHS[d.month]} {d.day}, {d.year}",
                   "Application": ", ".join(r["_apps"]) or "not given in the release",
                   "openFDA approval status": str(r.get("approval_status") or "").strip() or "not given"}
            for k, v in exp.items():
                if rows.get(k) != v:
                    fails.append(f"{tag}: facts row {k!r} says {rows.get(k)!r}, the release says {v!r}")
            nm = re.sub(r"\s+", " ", str(r.get("company_name") or "")).strip()
            co = rows.get("Company (openFDA's field)")
            if co != nm and not (nm and co == "not a readable name in the release") \
                    and not (not nm and co == "not given in the release"):
                fails.append(f"{tag}: company row {co!r} is not openFDA's field {nm!r}")
            lede = text_of((re.search(r'data-crl-letter="lede">(.*?)</p>', doc, re.S) or [None, ""])[1]
                           if re.search(r'data-crl-letter="lede">', doc) else "")
            if exp["Letter date"] not in lede:
                fails.append(f"{tag}: the lede does not give the letter's date")
            if co == nm and nm and nm not in lede:
                fails.append(f"{tag}: the lede does not name the company the release gives")
            if co != nm and nm and nm in lede:
                fails.append(f"{tag}: the lede repeats a misread company field")
            if ("rescinded" in lede.lower()) != bool(L["rescinded"]) or \
                    ("Rescinded by the FDA" in rows) != bool(L["rescinded"]):
                fails.append(f"{tag}: the page's rescission does not match the release")
            fn = str(r.get("file_name") or "").strip()
            pdf = re.findall(r'href="([^"]+)"[^>]*data-crl-letter="pdf"', doc)
            want_pdf = ["https://download.open.fda.gov/crl/" + quote(fn)] if fn.lower().endswith(".pdf") else []
            if [html.unescape(x) for x in pdf] != want_pdf:
                fails.append(f"{tag}: PDF link {pdf} is not the letter's own file {want_pdf}")
        for k, v in C.facts(L):
            if k.startswith(("Signed by", "Center", "Signature")) and rows.get(k) != C.norm(v):
                fails.append(f"{tag}: facts row {k!r} is not the signature reading")
        b4 = rows.get("Signature shows (b) (4)")
        if (L["app_txt"], L["date"].isoformat()) in HAND_B4 and b4 != "yes":
            fails.append(f"{tag}: the signature prints (b) (4) but the page says {b4!r}")
        for c in re.findall(r'href="(/crl/company/[^"]+)" data-crl-letter="company"', doc):
            n_comp += 1
            cp = os.path.join(SITE, c.strip("/"), "index.html")
            cd = io.open(cp, encoding="utf-8", errors="replace").read() if os.path.exists(cp) else ""
            ok = any(html.unescape(u) == L["url"] and text_of(t) in row_dates(L["date"]) for u, t in
                     re.findall(r'<td class="dt"><a href="([^"]+)"[^>]*>([^<]+)</a>', cd))
            if not ok:
                fails.append(f"{tag}: company link {c} goes to a page that does not list this letter")
        for c in re.findall(r'href="(/fda-decision/[^"]+)" data-crl-letter="decision"', doc):
            n_dec += 1
            cp = os.path.join(SITE, c.strip("/"), "index.html")
            cd = html.unescape(io.open(cp, encoding="utf-8", errors="replace").read()) if os.path.exists(cp) else ""
            if not L["url"] or L["url"] not in cd:
                fails.append(f"{tag}: decision link {c} goes to a page that does not cite this letter's PDF")
        if f'<link rel="canonical" href="https://www.pdufa.bio/crl/letter/{slug}">' not in doc:
            fails.append(f"{tag}: canonical is not its own address")
        noindex = bool(re.search(r'name="robots"[^>]*noindex', doc))
        if noindex != (len(C.norm(L["text"])) < C.MIN_TEXT):
            fails.append(f"{tag}: noindex is {noindex} for a text of {len(C.norm(L['text']))} characters")
        end = doc.find('<div class="legal"')
        own = text_of(C.VERBATIM.sub(" ", doc[doc.find("<h1"):end if end > 0 else None]))
        head = " ".join(re.findall(r"<title>(.*?)</title>", doc, re.S) +
                        re.findall(r'name="description" content="([^"]*)"', doc))
        if FORECAST.search(own) or FORECAST.search(html.unescape(head)):
            fails.append(f"{tag}: the page's own words, title or description carry a forecast word")

    # the verbatim block, which the copy guards skip on letter pages, may sit on no other page
    for p in glob.glob(os.path.join(SITE, "**", "*.html"), recursive=True):
        if os.path.dirname(os.path.dirname(p)) == C.ROOT:
            continue
        d = io.open(p, encoding="utf-8", errors="replace").read()
        if plant == "2" and p == os.path.join(SITE, "about", "index.html"):
            d += TAG + "<p>house copy</p></blockquote>"
        if TAG in d:
            fails.append(f"{os.path.relpath(p, SITE)}: carries the FDA verbatim block outside /crl/letter")

    # every "its text" link sits in that letter's own row
    n_hub = n_mon = 0
    for p in [os.path.join(SITE, "crl", "index.html")] + glob.glob(os.path.join(SITE, "crl", "20*", "*", "index.html")):
        d = io.open(p, encoding="utf-8", errors="replace").read() if os.path.exists(p) else ""
        for row in re.findall(r"<tr>(.*?)</tr>", d, re.S):
            for s in re.findall(r'href="/crl/letter/([a-z0-9-]+)"', row):
                if p.endswith(os.path.join("crl", "index.html")):
                    n_hub += 1
                else:
                    n_mon += 1
                L = by_slug.get(s)
                if L is None:
                    fails.append(f"{os.path.relpath(p, SITE)}: links /crl/letter/{s}, which is no letter's page")
                    continue
                cells = [text_of(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)]
                if L["url"] not in html.unescape(row) or not (set(cells) & row_dates(L["date"])):
                    fails.append(f"{os.path.relpath(p, SITE)}: /crl/letter/{s} sits in another letter's row")
    hub = io.open(os.path.join(SITE, "crl", "index.html"), encoding="utf-8", errors="replace").read() \
        if os.path.exists(os.path.join(SITE, "crl", "index.html")) else ""
    linked = set(re.findall(r'href="/crl/letter/([a-z0-9-]+)"', hub))
    if want - linked:
        fails.append(f"/crl does not link {len(want - linked)} letter page(s), e.g. {sorted(want - linked)[:3]}")
    for k, n in (("company", n_comp), ("decision", n_dec), ("hub", n_hub), ("months", n_mon)):
        if n < FLOOR[k]:
            fails.append(f"only {n} {k} link(s) to or from letter pages (floor {FLOOR[k]}): a build step failed")
    if fails:
        print(f"FAIL test_crl_letters: {len(fails)} problem(s); fix: python build_crl_letters.py")
        for f in fails[:20]:
            print("  " + f)
        return 1
    print(f"PASS test_crl_letters: {len(want)} letter pages, each the FDA's text; {n_comp} company, {n_dec} decision, "
          f"{n_hub} hub and {n_mon} month links checked")
    return 0


if __name__ == "__main__":
    sys.exit(main())
