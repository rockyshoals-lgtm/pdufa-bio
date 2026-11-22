# -*- coding: utf-8 -*-
"""build_crl_companies.py -- /crl/companies and /crl/company/<slug>: every released CRL, by the company it went to.

David, 2026-11-22: "Continue to hone and build the moat." The FDA's CRL release (openFDA transparency/crl) is a
flat list; nobody publishes it by sponsor. These pages do, joined to other FDA files:

  * /crl/companies: every company in the release with its count of Complete Response Letters
  * /crl/company/<slug>: one page per company with two or more letters, each letter with its date, application,
    openFDA's approval_status, the first approval the Orange Book lists for the NDA after the letter, the
    deficiency sections the letter's own PDF names (2024+ letters, extract_crl_headings.py), and this site's
    decision page where one links the same letter

Grouping rule (stated on the pages): the company name as openFDA prints it, with capitalization, punctuation and
corporate-form words (Inc., LLC, Ltd., Limited, Corp., SA, USA, ...) ignored. Different legal entities of one
group that differ only by those words are grouped; each letter still shows the name as printed. A record openFDA
gives a heading instead of a name ("CLASS 2 RESUBMISSION") is counted under "name not given".

FACTS ONLY: counts and dates from FDA files. No approval rates, no predictions, no view on any company.

    python build_crl_companies.py
"""
import collections
import glob
import io
import json
import os
import re
import shutil
import unicodedata
import sys
from urllib.parse import unquote as _uq

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
sys.path.insert(0, HERE)
from build_crl_facts import (CSS, NAV, CORPUS, GARBLED, MON, PDF, esc, iso, is_supplement, orange_book,  # noqa: E402
                             parse_app, pretty)
from urllib.parse import quote as _urlq  # noqa: E402

BASE = "https://www.pdufa.bio"
CR = "COMPLETE RESPONSE"
# Red team 2026-11-22: a form word only counts at a word boundary ("Evolus" kept whole, not "Evol"), and a
# trailing "and"/"&" left by "and Company"/"& Co." goes with it.
FORM = (r"inc|incorporated|llc|l\.l\.c|ltd|limited|corp|corporation|co|company|plc|ag|sa|s\.a|gmbh|lp|l\.p|"
        r"bv|b\.v|nv|n\.v|pvt|private|usa|u\.s\.a|us|u\.s|holdings?|ab|as|a/s|kk|k\.k|spa|s\.p\.a|srl|s\.r\.l|"
        r"sas|se|ulc")
SUF = re.compile(r"(?:(?:,\s*|\s+)(?:" + FORM + r")\.?-?)+$|(?:\s+(?:and|&))$", re.I)
GRP = "the company name as openFDA prints it, with capitalization, accents, punctuation and corporate-form words " \
      "(Inc., LLC, Ltd., Limited, Corp., SA, USA and the like) ignored"


def _strip_forms(n):
    prev = None
    while prev != n:
        prev = n
        n = SUF.sub("", n).strip(" ,.-")
    return n


def key_of(name):
    n = unicodedata.normalize("NFKD", str(name or "")).encode("ascii", "ignore").decode()
    n = n.lower().replace("’", "'").strip()
    n = re.sub(r"[^a-z0-9&' ,./\-]", " ", n)
    n = re.sub(r"\s+", " ", n).strip(" ,.-")
    n = _strip_forms(" " + n).strip()
    return re.sub(r"\s+", " ", re.sub(r"[.,']", "", n)).strip()


def label_of(name):
    """The printed name without its corporate-form words, as printed otherwise: 'Dr. Reddy's Laboratories'."""
    n = re.sub(r"\s+", " ", str(name or "")).strip(" ,.-")
    return _strip_forms(" " + n).strip() or n


def slug_of(key):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", key)).strip("-")


def short(s, n):
    """At most n characters, cut at a word, with no bracket left open."""
    s = s.strip()
    if len(s) <= n:
        return s
    s = s[:n].rsplit(" ", 1)[0].rstrip(" ,.-(")
    if s.count("(") > s.count(")"):
        s = s[:s.rfind("(")].rstrip(" ,.-")
    return s


def pl(k, one, many):
    return f"{k} {one if k == 1 else many}"


def page(title, desc, canon, body):
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
            f'<title>{esc(title)}</title><meta name="description" content="{esc(desc)}">'
            f'<link rel="canonical" href="{BASE}{canon}">'
            f'<meta name="robots" content="index,follow,max-image-preview:large">'
            f'<meta name="theme-color" content="#02060d"><meta property="og:type" content="website">'
            f'<meta property="og:site_name" content="pdufa.bio"><meta property="og:url" content="{BASE}{canon}">'
            f'<meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}">'
            f'<style>{CSS}</style></head><body><div class="wrap">{NAV}' + "".join(body) + "</div></body></html>")


def main():
    raw = json.load(io.open(CORPUS, encoding="utf-8"))
    recs = raw.get("results") if isinstance(raw, dict) else raw
    last_updated = str((raw.get("meta") or {}).get("last_updated") or "") if isinstance(raw, dict) else ""
    snap = (re.search(r"(\d{4}-\d{2}-\d{2})", os.path.basename(CORPUS)) or [None, ""])[1]

    # the same repeat rule as /crl: among CRLs, a record repeats another when its date, application numbers and
    # text are the same
    seen, letters, rescinds = set(), [], []
    for r in recs:
        d = iso(r.get("letter_date"))
        typ = str(r.get("letter_type") or "")
        apps = [x for x in (parse_app(a) for a in (r.get("application_number") or [])) if x]
        if d and "RESCIND" in typ.upper():
            rescinds.append({"date": d, "apps": apps, "text": re.sub(r"\s+", " ", str(r.get("text") or ""))})
        if not d or typ != CR:
            continue
        k = (d, tuple(sorted(str(x).strip() for x in (r.get("application_number") or []))),
             re.sub(r"\s+", " ", str(r.get("text") or "")).strip().lower())
        if k in seen:
            continue
        seen.add(k)
        fn = str(r.get("file_name") or "").strip()
        nm = re.sub(r"\s+", " ", str(r.get("company_name") or "")).strip()
        kk = key_of(nm) if nm and not GARBLED.search(nm) else ""
        letters.append({"date": d, "file": fn, "name": nm, "key": kk, "label": label_of(nm) if kk else "",
                        "apps": apps, "app_txt": ", ".join(r.get("application_number") or []),
                        "status": str(r.get("approval_status") or "").strip(), "rescinded": None,
                        "url": PDF + _urlq(fn) if fn.lower().endswith(".pdf") else ""})
    # letters the FDA later rescinded as "issued in error" (the same reading as /crl/facts): the rescission names
    # them by date and application
    for R in rescinds:
        m = re.search(r"refer to our letters? dated (.{0,120}?)(?:,? informing|\.)", R["text"], re.I)
        for ds in re.findall(r"(?:" + "|".join(MON[1:]) + r") \d{1,2}, \d{4}", m.group(1) if m else ""):
            vd = __import__("datetime").datetime.strptime(ds, "%B %d, %Y").date()
            for L in letters:
                if L["date"] == vd and set(L["apps"]) & set(R["apps"]):
                    L["rescinded"] = R["date"]
    groups = collections.defaultdict(list)
    for L in letters:
        groups[L["key"]].append(L)
    no_name = groups.pop("", [])

    ob, ob_as_of = orange_book()
    try:
        from extract_crl_headings import substantive_sections, OUT as HP
        hcache = json.load(io.open(HP, encoding="utf-8")) if os.path.exists(HP) else {}
    except Exception:
        substantive_sections, hcache = None, {}
    # a PDF can hold more than one letter (combined files); a section reading or a decision-page link is shown only
    # where the file holds this one letter and nothing else from the release
    files = collections.Counter(str(r.get("file_name") or "").strip() for r in recs)
    ours = {}
    for p in glob.glob(os.path.join(SITE, "fda-decision", "*", "index.html")):
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        m = re.search(r'<!--CRLSRC:BEGIN-->.*?href="https://download\.open\.fda\.gov/crl/([^"]+)"', doc, re.S)
        if m:
            ours.setdefault(_uq(m.group(1)), []).append(os.path.basename(os.path.dirname(p)))

    caveat = ('Grouped on ' + GRP + '; each row shows the name as printed. A misspelled name forms its own group, and '
              'a letter printed with a heading or a bare corporate-form word where the name should be is on no '
              'company page, so a count here can be lower than the letters the release holds for a company.')
    out_root = os.path.join(SITE, "crl", "company")
    if os.path.isdir(out_root):
        shutil.rmtree(out_root)          # regenerated from scratch: a company that leaves the release loses its page
    made, labels = {}, {}
    for key, ls in groups.items():
        labels[key] = collections.Counter(L["label"] for L in ls).most_common(1)[0][0]
    for key, ls in groups.items():
        if len(ls) < 2:
            continue
        ls.sort(key=lambda x: x["date"], reverse=True)
        shown = labels[key]
        slug = slug_of(key)
        if not slug or slug in made.values():
            continue
        made[key] = slug
        norm = lambda t, n, s: (t, n, s if is_supplement(s) else "")   # noqa: E731
        live = [L for L in ls if not L["rescinded"]]
        apps = {norm(*a) for L in ls for a in L["apps"]}
        by_app = collections.Counter(a for L in live for a in {norm(*x) for x in L["apps"]})   # once per letter
        rep = sum(1 for v in by_app.values() if v >= 2)
        n_resc = len(ls) - len(live)
        y0, y1 = min(L["date"].year for L in ls), max(L["date"].year for L in ls)
        yrs = f"{y0}" if y0 == y1 else f"{y0} to {y1}"
        printed = collections.Counter(L["name"] for L in ls)
        title = f"{short(shown, 52)} FDA Complete Response Letters ({len(ls)}) | pdufa.bio"
        desc = f"{len(ls)} FDA Complete Response Letters to {shown}, {yrs}, from the FDA's release: each letter, its application and the FDA's PDF."
        if len(desc) > 160:
            desc = (f"{len(ls)} FDA Complete Response Letters to {short(shown, 60)}, {yrs}, from the FDA's release, "
                    f"each with its PDF.")
        if len(apps) == 1:
            app_s = "all on one application"
        else:
            app_s = f"on {len(apps)} applications" + (
                f"; {rep} of them received more than one" if rep > 1 else "; one of them received more than one" if rep else "")
        B = [f'<h1>{esc(shown)}: <span class="g">{len(ls)} Complete Response Letters</span></h1>',
             f'<p class="sub">The FDA\'s CRL release (openFDA transparency/crl, last updated {esc(last_updated)}; '
             f'snapshot read {esc(snap)}) holds {len(ls)} Complete Response Letters to this company, dated {yrs}, '
             f'{app_s}'
             + (f'. The FDA later rescinded {pl(n_resc, "of them", "of them")} as issued in error (marked below; left '
                f'out of the count of applications with more than one letter)' if n_resc else '')
             + '. The FDA releases letters selectively, so this may not be every letter the company received. '
             f'Printed in the release as: '
             + "; ".join(f'{esc(n)} ({c})' for n, c in printed.most_common()) + '.</p>',
             f'<p class="sub">{esc(caveat)} Facts only: no view on any outcome.</p>',
             '<table><tr><th>Letter date</th><th>Application</th><th>Name as printed</th><th>openFDA status</th>'
             '<th>Orange Book approval after the letter</th><th>Sections the letter names</th></tr>']
        for L in ls:
            ndas = list(dict.fromkeys(n for t, n, s in L["apps"] if t == "NDA" and not is_supplement(s)))
            obs = [f"{esc(ob[n][1][:30])}, {esc(pretty(ob[n][0]))}" for n in ndas if n in ob and ob[n][0] > L["date"]]
            if obs:
                ob_cell = "; ".join(obs)
            elif ndas:
                ob_cell = "none listed after the letter"
            elif any(t == "BLA" for t, n, s in L["apps"]):
                ob_cell = "not in the Orange Book (a BLA)"
            elif any(t == "NDA" for t, n, s in L["apps"]):
                ob_cell = "not shown (a supplement)"
            else:
                ob_cell = "not shown"
            secs = "none read"
            if L["date"].year >= 2024 and files[L["file"]] == 1 and substantive_sections:
                s_ = substantive_sections(L["file"], hcache)
                secs = "; ".join(esc(x) for x in s_) if s_ else "none read"
            dp = ("".join(f' &middot; <a href="/fda-decision/{esc(s)}">our decision page</a>'
                          for s in ours.get(L["file"], [])) if files[L["file"]] == 1 else "")
            dcell = (f'<a href="{esc(L["url"])}" rel="noopener">{esc(pretty(L["date"]))}</a>' if L["url"]
                     else esc(pretty(L["date"])))
            st = esc(L["status"]) + (f'; the FDA rescinded this letter on {esc(pretty(L["rescinded"]))} as issued in '
                                     f'error' if L["rescinded"] else "")
            B.append(f'<tr><td class="dt">{dcell}{dp}</td><td>{esc(L["app_txt"])}</td><td>{esc(L["name"])}</td>'
                     f'<td>{st}</td><td>{ob_cell}</td><td style="font-size:12.5px">{secs}</td></tr>')
        B.append('</table>')
        B.append(f'<p class="sub">How each column is made: the letter date and the PDF are the FDA\'s release; '
                 f'"openFDA status" is openFDA\'s approval_status field as released; "Orange Book approval" is the earliest '
                 f'approval date the FDA\'s Orange Book products file (FDA files dated {esc(ob_as_of) or "as downloaded"}) '
                 f'lists for the NDA, shown when it falls after the letter date and the letter is not on a supplement; '
                 f'BLAs are not in the Orange Book, so no date is shown for them; "sections" are the letter\'s own '
                 f'deficiency headings read from its PDF text layer, for letters dated 2024 or later whose PDF holds no '
                 f'other letter from the release ("none read" otherwise, or where no heading could be read).</p>')
        B.append('<p class="sub"><a href="/crl/companies">Every company in the release</a> &middot; '
                 '<a href="/crl/facts">facts from all released CRLs</a> &middot; <a href="/crl">every released letter</a></p>')
        out = os.path.join(out_root, slug, "index.html")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        io.open(out, "w", encoding="utf-8").write(page(title, desc, f"/crl/company/{slug}", B))

    # --- index ---------------------------------------------------------------------------------------------------
    rows = sorted(groups.items(), key=lambda kv: (-len(kv[1]), labels[kv[0]].lower()))
    n_co, n_l = len(rows), sum(len(v) for _, v in rows)
    title = f"FDA Complete Response Letters by Company: {n_co} Companies | pdufa.bio"
    desc = (f"Every company in the FDA's released Complete Response Letters, {n_co} in all, with each one's letters "
            f"and the FDA's PDFs.")
    B = [f'<h1>Complete Response Letters <span class="g">by company</span></h1>',
         f'<p class="sub">The FDA\'s CRL release (openFDA transparency/crl, last updated {esc(last_updated)}; snapshot '
         f'read {esc(snap)}) holds {n_l + len(no_name)} distinct Complete Response Letters. {n_l} of them name '
         f'{n_co} companies'
         + (f'; {pl(len(no_name), "carries", "carry")} a heading or a bare corporate-form word where the name should '
            f'be and {"is" if len(no_name) == 1 else "are"} counted under "name not given"' if no_name else '')
         + '. A company with two or more letters has its own page. The FDA releases letters selectively; a count '
         'here is what the release holds, not every letter a company received.</p>',
         f'<p class="sub">{esc(caveat)}</p>',
         '<table><tr><th>Company</th><th>Letters</th><th>Latest letter</th></tr>']
    for key, ls in rows:
        last = max(ls, key=lambda x: x["date"])
        name_cell = (f'<a href="/crl/company/{made[key]}">{esc(labels[key])}</a>' if key in made else esc(labels[key]))
        lc = (f'<a href="{esc(last["url"])}" rel="noopener">{esc(pretty(last["date"]))}</a>' if last["url"]
              else esc(pretty(last["date"])))
        B.append(f'<tr><td>{name_cell}</td><td>{len(ls)}</td><td class="dt">{lc}</td></tr>')
    if no_name:
        last = max(no_name, key=lambda x: x["date"])
        B.append(f'<tr><td>name not given</td><td>{len(no_name)}</td><td class="dt">{esc(pretty(last["date"]))}</td></tr>')
    B.append('</table><p class="sub"><a href="/crl/facts">Facts from all released CRLs</a> &middot; '
             '<a href="/crl">every released letter, by year</a></p>')
    out = os.path.join(SITE, "crl", "companies", "index.html")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    io.open(out, "w", encoding="utf-8").write(page(title, desc, "/crl/companies", B))
    print(f"/crl/companies: {n_co} companies, {n_l} letters ({len(no_name)} with no name); "
          f"{len(made)} company pages under /crl/company/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
