# -*- coding: utf-8 -*-
"""build_crl_letters.py -- /crl/letter/<slug>: one page per released Complete Response Letter, with its text.

The FDA's CRL release (openFDA transparency/crl) holds each letter as a PDF and as the text openFDA extracted from
it. Until now the site linked only the PDF. This writes one page per distinct letter (the /crl repeat rule, the 2
the FDA rescinded included and flagged), so a search for an application number finds the letter's own words:

  * the facts the release states: letter date, application numbers, the company as openFDA's field prints it,
    openFDA's approval status, the signing division, office and Center as /crl/offices reads them, whether the
    signature shows (b) (4), and whether the FDA later rescinded the letter;
  * the letter's text exactly as openFDA released it (spacing aside), OCR errors and the FDA's (b) (4) redactions
    included, inside <blockquote class="crl-text" data-verbatim="fda">. On these pages only, the site's copy fixers
    and copy guards skip that block (crl_verbatim.py), so nothing rewrites the FDA's words;
  * links: the FDA's PDF (the record), the company's /crl/company page when that page lists this letter (same PDF,
    same date), and the decision page that cites the PDF (the dataset's pdufa_bio_page rule).

Addresses are permanent: _crl_letter_slugs.json (committed) keeps each letter's slug, so a new letter with the same
application and date takes "-2" and never moves an existing page. A letter whose text openFDA re-extracts keeps its
slug (same PDF, date and applications).

A letter with too little text to read (under 400 characters) is written with noindex and says so. Facts only: the
page adds no summary, reading or forecast of its own.

    python build_crl_letters.py
"""
import collections
import datetime as dt
import glob
import hashlib
import html
import io
import json
import os
import re
import shutil
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
sys.path.insert(0, HERE)
from build_crl_facts import CORPUS, esc, pretty  # noqa: E402
from build_crl_companies import page, slug_of  # noqa: E402
from build_feeds import crl_letters  # noqa: E402
from crl_verbatim import TAG  # noqa: E402

ROOT = os.path.join(SITE, "crl", "letter")
LEDGER = os.path.join(HERE, "_crl_letter_slugs.json")
MIN_TEXT = 400
VERBATIM = re.compile(re.escape(TAG) + r"(.*?)</blockquote>", re.S)   # group 1: the FDA text
CENTER = {"CDER": "Center for Drug Evaluation and Research", "CBER": "Center for Biologics Evaluation and Research"}


def norm(s):
    return re.sub(r"\s+", " ", str(s or "")).strip()


def ident(key):
    """A letter's identity without its text hash: PDF file, date, applications."""
    return key.rsplit("|", 1)[0]


def _base(L):
    first = (L["app_txt"].split(",")[0] if L["app_txt"] else "") or os.path.splitext(L["file"])[0]
    return re.sub(r"[^a-z0-9]+", "-", f"{first} {L['date'].isoformat()}".lower()).strip("-")


def load_ledger():
    if os.path.exists(LEDGER):
        return json.load(io.open(LEDGER, encoding="utf-8"))
    return {}


def slugs(letters, led=None):
    """{letter key: slug}. A letter in the ledger keeps its slug; a letter whose key changed only in its text hash
    takes the slug of its predecessor; a new letter takes the first free of base, base-2, base-3, ..."""
    led = load_ledger() if led is None else led
    present = {L["key"] for L in letters}
    gone = collections.defaultdict(list)
    for k, v in sorted(led.items()):
        if k not in present:
            gone[ident(k)].append(v)
    out = {L["key"]: led[L["key"]] for L in letters if L["key"] in led}
    used = set(led.values()) | set(out.values())
    for L in sorted(letters, key=lambda x: (x["date"], x["app_txt"], x["key"])):
        if L["key"] in out:
            continue
        if gone.get(ident(L["key"])):
            out[L["key"]] = gone[ident(L["key"])].pop(0)
            continue
        base, n = _base(L), 1
        s = base
        while s in used:
            n += 1
            s = f"{base}-{n}"
        out[L["key"]] = s
        used.add(s)
    return out


def by_file_date(letters):
    """{(PDF file name, ISO date): slug} where exactly one letter has that file and date (combined PDFs hold several)."""
    sl, cnt = slugs(letters), collections.Counter((L["file"], L["date"].isoformat()) for L in letters)
    return {(L["file"], L["date"].isoformat()): sl[L["key"]] for L in letters
            if L["file"] and cnt[(L["file"], L["date"].isoformat())] == 1}


def repeat_key(iso_date, apps, text):
    """The /crl repeat rule as a lookup key: letter date, sorted application numbers, the text's hash."""
    appn = ", ".join(sorted(str(x).strip() for x in (apps or [])))
    txt = re.sub(r"\s+", " ", str(text or "")).strip().lower()
    return (iso_date, appn, hashlib.sha1(txt.encode("utf-8")).hexdigest()[:8])


def by_repeat_key(letters):
    """{repeat_key: slug} for every letter (the hub links each letter's page with it)."""
    sl = slugs(letters)
    return {(L["date"].isoformat(), L["app_txt"], L["key"].rsplit("|", 1)[1]): sl[L["key"]] for L in letters}


def paragraphs(text):
    """The released text in paragraphs: a blank line splits, a single line break is the PDF's line wrap."""
    paras = [norm(p) for p in re.split(r"\n\s*\n", str(text or ""))]
    return [p for p in paras if p]


def company_rows():
    """{company slug: {(FDA PDF address, letter date as printed)}} from the /crl/company pages' letter rows."""
    out = {}
    for p in glob.glob(os.path.join(SITE, "crl", "company", "*", "index.html")):
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        out[os.path.basename(os.path.dirname(p))] = {
            (html.unescape(u), html.unescape(d).strip()) for u, d in
            re.findall(r'<td class="dt"><a href="(https://download\.open\.fda\.gov/crl/[^"]+)"[^>]*>([^<]+)</a>', doc)}
    return out


def company_page(L, rows):
    """The letter's company page, only where that page lists this letter (same PDF, same date)."""
    slug = slug_of(L["ckey"]) if L["ckey"] else ""
    return f"/crl/company/{slug}" if slug and (L["url"], pretty(L["date"])) in rows.get(slug, set()) else None


def decision_pages(letters):
    """{letter key: decision page path} by the dataset's rule (one indexable page cites the PDF, which holds this
    letter alone). A failure here fails the build."""
    import build_crl_dataset as D
    rows, _, _ = D.rows()
    want = collections.Counter((L["date"].isoformat(), L["url"]) for L in letters)
    page_of = {}
    for r in rows:
        k = (r["letter_date"], r["letter_pdf"])
        if r["pdufa_bio_page"] and want[k] == 1:      # only where the date and PDF name one letter
            page_of[k] = re.sub(r"^https://www\.pdufa\.bio", "", r["pdufa_bio_page"])
    return {L["key"]: page_of[(L["date"].isoformat(), L["url"])] for L in letters
            if (L["date"].isoformat(), L["url"]) in page_of}


_MON = r"(?:January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2}, \d{4}"


def corrected_action(L):
    """For a letter the FDA heads "Corrected Complete Response": the action date the letter itself says stands (the
    original letter's), else None. 2026-11-25 (CRL red team): /crl/letter/bla-761401-2026-04-10 and
    nda-219398-2026-01-28 showed only the correction's date, though each letter says the FDA's action date is the
    original letter's (August 27, 2025; December 30, 2025). The hand ledger's fda_action_date wins; otherwise the
    letter's own words are read, and nothing is shown when they name no date."""
    t = re.sub(r"\s+", " ", L.get("text") or "")
    if not re.search(r"CORRECTED COMPLETE RESPONSE|corrected (?:CRL|complete response letter|action letter)", t, re.I):
        return None
    fn = os.path.basename(str(L.get("url") or ""))
    try:
        led = {x["file_name"]: x for x in json.load(io.open(os.path.join(HERE, "_crl_letter_findings.json"),
                                                               encoding="utf-8"))["letters"]}
    except Exception:  # noqa: BLE001
        led = {}
    fad = (led.get(fn) or {}).get("fda_action_date")
    if fad:
        return pretty(dt.date.fromisoformat(fad))
    for pat in (rf"effective action date will remain ({_MON})",
                rf"(?:original CRL|original complete response letter|original letter) (?:issued|sent to you|dated) on ({_MON})",
                rf"(?:CRL|complete response letter) sent to you on ({_MON})"):
        m = re.search(pat, t, re.I)
        if m:
            return m.group(1)
    return None


def name_of(L):
    """openFDA's company field when it reads as a name (not a misread such as "CLASS 2 RESUBMISSION" or "LLC")."""
    return L["name"] if L["name"] and L["ckey"] else ""


def apps_short(L):
    """The first application number, and how many more: never cut inside a number."""
    a = [x.strip() for x in L["app_txt"].split(",") if x.strip()] if L["app_txt"] else []
    if not a:
        return "an application the release does not give"
    return a[0] + (f" and {len(a) - 1} more" if len(a) > 1 else "")


def facts(L):
    g = L["sig"]
    tidy = lambda s: re.sub(r"[\s|]+$", "", s or "")   # noqa: E731  (a table rule the scan read as "|")
    unit = ", ".join(x for x in (tidy(g["division"]), tidy(g["office"])) if x)
    nm = name_of(L)
    rows = [("Letter date", pretty(L["date"])),
            ("Application", L["app_txt"] or "not given in the release"),
            ("Company (openFDA's field)", nm or ("not a readable name in the release" if L["name"] else
                                                  "not given in the release")),
            ("openFDA approval status", L["status"] or "not given"),
            ("Signed by (division, office)", unit or "none named in text this page can read"),
            ("Center", CENTER.get(g["center"], "none named in the letter's text or openFDA's center field")),
            ("Signature shows (b) (4)", "yes" if g["withheld"] else "no")]
    ca = corrected_action(L)
    if ca:
        rows.insert(1, ("Corrected letter", f"yes; it states the FDA's action date remains {ca}, the date of the "
                                            f"original letter"))
    if L["rescinded"]:
        rows.append(("Rescinded by the FDA", f"yes, by a letter dated {pretty(L['resc_date'])}, as issued in error"))
    return rows


def lede_text(L, last_updated):
    who = name_of(L) or "the applicant"                # a misread name is not repeated
    return (f"The FDA's Complete Response Letter to {who}, dated {pretty(L['date'])}. It is one of the letters in "
            f"the FDA's public CRL release (openFDA transparency/crl, last updated {last_updated})."
            + (" The FDA later rescinded it as issued in error." if L["rescinded"] else "")
            + (f" It is a corrected letter: it states that the FDA's action date remains {corrected_action(L)}, the "
               f"date of the original letter." if corrected_action(L) else ""))


def title_desc(L):
    a = apps_short(L)
    title = (f"FDA Complete Response Letter, {a}, {pretty(L['date'])}"
             + (" (rescinded)" if L["rescinded"] else "") + " | pdufa.bio")
    desc = (f"The FDA's Complete Response Letter on {a}, dated {pretty(L['date'])}"
            + (", later rescinded" if L["rescinded"] else "") + ": its text as the FDA released it, its facts and its PDF.")
    if len(desc) > 158:
        desc = desc.replace(", its facts and its PDF.", " and its PDF.")
    return title, desc


def write(L, slug, comp, dec, last_updated):
    paras = paragraphs(L["text"])
    readable = len(norm(L["text"])) >= MIN_TEXT
    title, desc = title_desc(L)
    B = [f'<h1>Complete Response Letter, <span class="g">{esc(L["app_txt"] or "application not given")}</span></h1>',
         f'<p class="sub" data-crl-letter="lede">{esc(lede_text(L, last_updated))}</p>',
         '<table data-crl-letter="facts">' + "".join(f'<tr><th>{esc(k)}</th><td>{esc(v)}</td></tr>'
                                                       for k, v in facts(L)) + '</table>']
    links = []
    if L["url"]:
        links.append(f'<a href="{esc(L["url"])}" rel="noopener" data-crl-letter="pdf">the letter as the FDA released '
                     f'it (PDF)</a>')
    if comp:
        links.append(f'<a href="{comp}" data-crl-letter="company">this company\'s page of released CRLs</a>')
    if dec:
        links.append(f'<a href="{dec}" data-crl-letter="decision">this site\'s decision page</a>')
    links.append('<a href="/crl/offices">which FDA office signed each CRL</a>')
    links.append('<a href="/crl">every released letter, by year</a>')
    B.append('<p class="sub">' + " &middot; ".join(links) + '</p>')
    from build_crl_phrases import PHRASES, matches   # the /crl/phrases terms this letter's text contains
    terms = {p[0]: p[1] for p in PHRASES}
    found = matches(L)
    if found:
        B.append('<p class="sub" data-crl-letter="terms">Terms from <a href="/crl/phrases">/crl/phrases</a> that this '
                 'letter\'s released text contains: ' + ", ".join(f'<a href="/crl/phrase/{s}">{esc(terms[s])}</a>'
                                                            for s in found) + '.</p>')
    B.append('<h2>The letter\'s text</h2>')
    if paras:
        B.append('<p class="sub">As openFDA extracted it from the PDF, with line breaks and spacing collapsed and '
                 'nothing else changed: misread characters, page headers and the FDA\'s "(b) (4)" redactions are as '
                 'released. The PDF is the record.' +
                 ('' if readable else ' openFDA holds too little text for this letter to read here; open the PDF.')
                 + '</p>')
        B.append('<div style="margin:12px 0;padding:4px 16px;border-left:3px solid #1e3a63;color:#c9d6ea;'
                 'font-size:14px;line-height:1.55">' + TAG
                 + "".join(f"<p>{esc(p)}</p>" for p in paras) + '</blockquote></div>')
    else:
        B.append('<p class="sub">openFDA holds no text for this letter; open the PDF.</p>')
    doc = page(title, desc, f"/crl/letter/{slug}", B)
    if not readable:
        doc = doc.replace('content="index,follow,max-image-preview:large"', 'content="noindex,follow"', 1)
    out = os.path.join(ROOT, slug, "index.html")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    io.open(out, "w", encoding="utf-8").write(doc)
    return readable


def main():
    letters, last_updated, _ = crl_letters(include_rescinded=True)
    led = load_ledger()
    sl = slugs(letters, led)
    led.update(sl)                                # every slug ever given stays reserved for its letter
    io.open(LEDGER, "w", encoding="utf-8").write(json.dumps(led, indent=0, sort_keys=True) + "\n")
    rows, dec = company_rows(), decision_pages(letters)
    comp = {L["key"]: company_page(L, rows) for L in letters}
    if os.path.isdir(ROOT):                       # a letter the FDA drops from its release leaves no stale page
        shutil.rmtree(ROOT)
    n_read = sum(write(L, sl[L["key"]], comp[L["key"]], dec.get(L["key"]), last_updated) for L in letters)
    print(f"/crl/letter: {len(letters)} pages ({n_read} indexable, {len(letters) - n_read} noindex for too little "
          f"text); {sum(1 for v in comp.values() if v)} link a company page, {len(dec)} a decision page "
          f"(corpus {os.path.basename(CORPUS)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
