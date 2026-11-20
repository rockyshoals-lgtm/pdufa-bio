# -*- coding: utf-8 -*-
"""CI guard: a decision page's sources belong to its company and to its FDA action, and a study page names its drug.

WHY (citation audit, 2026-11-18)
Three decision pages cited a document about a different FDA action: ALDX-2025-04-03 linked Aldeyra's release on
the SECOND reproxalap CRL (March 2026), ATRA-2025-01-16 linked a May 2025 release about a clinical-hold lift, and
FBIO-2025-10-01 linked the January 2026 approval letter in place of the September 2025 CRL. Fourteen decision
pages in the run-up study had no drug row, so their FAQ read the verification badge as the drug ("Was
source-verified approved by the FDA?"), and SNY-2026-02-24 (Dupixent) was carried in the study as venglustat.
apply_1118d_decision_sources.py corrected them from the FDA's own letters.

THE INVARIANTS, on every /fda-decision/ page:
  1. an SEC filing link names the page's own company: its CIK is the ticker's (ticker_cik_map.json, then
     sec_ticker_cik.json), a specialist fund's 13F in the holders table (_13f_specialists.json), or a partner
     listed in PARTNERS with the reason;
  2. an FDA letter cited as the page's source (Primary source row, Validation row, FDA record paragraph) is the
     letter for this action: an openFDA CRL file is dated the page's FDA decision day (or, with no such row, within
     seven days before the page date); a CRL page never cites an approval letter, and an approval letter's year is
     the year of the FDA decision; and the cited letter's application number is this action's (the archive's
     record for the page, or, with no record, a number the page itself states). A CRL file must be in the openFDA
     corpus unless it is newer than the corpus;
  3. a dated release cited as the source (GlobeNewswire /YYYY/MM/DD/, Business Wire /news/home/YYYYMMDD) is not
     more than seven days after the page date;
  4. the Drug row shares a name word with the archive's drug name for the page, where the archive has one;
  5. every page in the run-up study (pdufa_runup_bifrost_v2.csv) names its drug in a key-facts or facts-table row,
     and no FAQ asks whether a badge ("source-verified", "primary-sourced") was approved.

Plants (each must FAIL): PLANT=cik (MRK page cites Pfizer's CIK), PLANT=letter (FBIO CRL page cites its approval
letter), PLANT=crl_day (ALDX-2025-04-03 cites the March 2026 CRL),
PLANT=release (PHAR-2026-02-01 cites a May release), PLANT=drug (a study page loses its drug row),
PLANT=crl_other (ALDX-2025-04-03 cites Amneal's CRL of the same day), PLANT=letter_other (SNY cites Eton's approval
letter of the same year), PLANT=styled (a CRL page on the styled template cites an approval letter),
PLANT=drug_wrong (SNY's Drug row says venglustat).

NOT CAUGHT (known limit): an undated company IR page from another review cycle. Only GlobeNewswire and Business
Wire URLs carry a date this test can read.

    python tests/test_decision_citations_match.py
"""
import csv
import datetime as dt
import glob
import io
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src", "fda-decision")

# ticker -> {cik: why}. A page may cite a partner's filing when the partner holds or co-owns the application.
PARTNERS = {
    "GSK": {1701108: "Spero Therapeutics: tebipenem partner", 874015: "Ionis: GSK-licensed program"},
    "INCY": {1759425: "Mirum Pharmaceuticals: the goal date's source"},
    "JAZZ": {1937653: "Zymeworks: zanidatamab partner"},
    "TEVA": {1720893: "BioXcel: the goal date's source"},
}
# openFDA CRL files whose file date is not the action date (a corrected letter keeps the original action date)
CORRECTED = {"CRL_NDA219398_20260128.pdf": "2025-12-30"}
BADGE_Q = re.compile(r"Was (?:source-verified|primary-sourced|verified|price-only)[^?<]{0,20} approved by the FDA\?", re.I)


def jl(name):
    return json.load(io.open(os.path.join(HERE, name), encoding="utf-8"))


def ciks():
    m = {}
    for v in jl("sec_ticker_cik.json").values():
        m.setdefault(v["ticker"], set()).add(int(v["cik_str"]))
    for t, c in jl("ticker_cik_map.json")["matched"].items():
        m.setdefault(t, set()).add(int(c))
    return m


def fund_ciks():
    out = set()

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k == "cik":
                    try:
                        out.add(int(v))
                    except (TypeError, ValueError):
                        pass
                walk(v)
        elif isinstance(o, list):
            for x in o:
                walk(x)
    walk(jl("_13f_specialists.json"))
    return out


def d(s):
    return dt.date.fromisoformat(s)


def kv(doc, label):
    m = re.search(r'<div class="kv"><span>' + label + r'</span><b[^>]*>(.*?)</b></div>', doc, re.S)
    return m.group(1) if m else None


def source_links(doc):
    """links the page cites as its source: Primary source and Validation rows, the FDA record paragraph"""
    parts = [kv(doc, "Primary source") or "", kv(doc, "Validation") or ""]
    m = re.search(r"<!--FDAREC:BEGIN-->(.*?)<!--FDAREC:END-->", doc, re.S)
    if m:
        parts.append(m.group(1))
    return re.findall(r'href="([^"]+)"', " ".join(parts))


def is_crl_page(doc):
    o = kv(doc, "Outcome") or ""
    return "badge crl" in o or "CRL" in re.sub(r"<[^>]+>", "", o)


def has_drug(doc):
    return bool(re.search(r'<div class="kv"><span>(?:Drug|Drug / candidate|Brand / candidate)</span><b>[^<\s]', doc)
                or re.search(r'>Drug</td>\s*<td[^>]*>[^<\s]', doc))


def corpus():
    c = jl("CRL_corpus_openFDA_2026-08-29.json")
    return {r["file_name"]: r for r in c["results"]}, c["meta"]["last_updated"]


def words(s):
    return set(re.findall(r"[a-z]{5,}", re.sub(r"<[^>]+>", " ", s or "").lower()))


def check(pages, study, plant=""):
    tk_cik, funds = ciks(), fund_ciks()
    crls, corpus_day = corpus()
    archive = jl("_fda_action_archive.json")
    bad = []
    for slug, doc in pages.items():
        tk, day = slug.rsplit("-", 3)[0], "-".join(slug.rsplit("-", 3)[1:])
        own = tk_cik.get(tk, set()) | set(PARTNERS.get(tk, {}))
        # 1. SEC filings belong to the company (or a fund's 13F, or a listed partner)
        for m in re.finditer(r'https?://www\.sec\.gov/(?:Archives/edgar/data/|cgi-bin/browse-edgar\?[^"]*CIK=)0*(\d+)', doc):
            c = int(m.group(1))
            if c not in own and c not in funds:
                bad.append(f"{slug}: cites SEC filer CIK {c}, which is not {tk}'s (nor a listed partner or 13F fund)")
        fda_day = re.sub(r"<[^>]+>", "", kv(doc, "FDA decision date") or "").strip()
        fda_day = fda_day if re.fullmatch(r"\d{4}-\d{2}-\d{2}", fda_day) else None
        crl_page = is_crl_page(doc)
        arc = archive.get(slug) or {}
        rec = re.search(r"\d{6}", arc.get("record") or "")
        rec = rec.group(0) if rec else None
        text = re.sub(r'href="[^"]*"', "", doc)

        def same_app(num, f):
            if rec:
                if num != rec:
                    bad.append(f"{slug}: cites {f} (application {num}) but this action is {arc['record']}")
            elif not re.search(r"(?<!\d)" + num[:3] + ",?" + num[3:] + r"(?!\d)", text):
                bad.append(f"{slug}: cites {f} (application {num}), a number the page never names")
        for u in source_links(doc):
            f = u.rsplit("/", 1)[-1]
            m = re.search(r"/crl/(CRL_[A-Z]+(\d+)_(\d{8})\.pdf)", u)
            if m:
                fd = f"{m.group(3)[:4]}-{m.group(3)[4:6]}-{m.group(3)[6:]}"
                if m.group(1) not in crls and fd <= corpus_day:
                    bad.append(f"{slug}: cites {m.group(1)}, which is not in the openFDA CRL corpus")
                same_app(m.group(2), m.group(1))
                ld = CORRECTED.get(m.group(1)) or fd
                if fda_day and ld != fda_day:
                    bad.append(f"{slug}: cites {m.group(1)} (letter {ld}) but its FDA decision date is {fda_day}")
                elif not fda_day and not (0 <= (d(day) - d(ld)).days <= 7):
                    bad.append(f"{slug}: cites {m.group(1)} (letter {ld}), not within 7 days before {day}")
                continue
            m = re.search(r"/appletter/(\d{4})/", u)
            if m and "OtherActionLtrs" not in f:
                n = re.match(r"(\d{6})", f)
                if n:
                    same_app(n.group(1), f)
                if crl_page and re.search(r"ltr\.pdf$", f):
                    bad.append(f"{slug}: a Complete Response page cites an approval letter ({f})")
                elif m.group(1) != (fda_day or day)[:4]:
                    bad.append(f"{slug}: cites a {m.group(1)} FDA letter ({f}) for a {(fda_day or day)[:4]} decision")
                continue
            m = (re.search(r"globenewswire\.com/news-release/(\d{4})/(\d{2})/(\d{2})/", u)
                 or re.search(r"businesswire\.com/news/home/(\d{4})(\d{2})(\d{2})", u))
            if m:
                rd = dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
                if (rd - d(day)).days > 7:
                    bad.append(f"{slug}: cites a release of {rd} for a {day} decision")
        # 4. the Drug row names the archive's drug
        drug = kv(doc, "Drug") or kv(doc, "Drug / candidate") or kv(doc, "Brand / candidate")
        if drug and arc.get("name") and not (words(drug) & words(arc["name"])):
            bad.append(f"{slug}: Drug row {re.sub(r'<[^>]+>', '', drug)!r} does not name the archive's {arc['name']!r}")
        # 5. study pages name their drug
        if slug in study:
            if not has_drug(doc):
                bad.append(f"{slug}: in the run-up study but names no drug (no Drug row)")
            q = BADGE_Q.search(doc)
            if q:
                bad.append(f"{slug}: FAQ asks about a badge, not a drug: {q.group(0)!r}")
    return list(dict.fromkeys(bad))


def load():
    pages = {}
    for p in glob.glob(os.path.join(SITE, "*", "index.html")):
        pages[os.path.basename(os.path.dirname(p))] = io.open(p, encoding="utf-8", errors="replace").read()
    study = set()
    with io.open(os.path.join(HERE, "pdufa_runup_bifrost_v2.csv"), encoding="utf-8-sig", errors="replace") as f:
        for r in csv.DictReader(f):
            study.add(f"{r['ticker']}-{(r.get('pdufa_date') or '')[:10]}")
    return pages, study


def plant(pages, study, which):
    if which == "cik":
        s = next(k for k in sorted(pages) if k.startswith("MRK-"))
        pages[s] += '<a href="https://www.sec.gov/Archives/edgar/data/78003/000007800326000001/x.htm">x</a>'
    elif which == "letter":
        s = "FBIO-2025-10-01"
        pages[s] = pages[s].replace("https://download.open.fda.gov/crl/CRL_NDA211241_20250930.pdf",
                                    "https://www.accessdata.fda.gov/drugsatfda_docs/appletter/2026/211241Orig1s000ltr.pdf")
    elif which == "crl_day":
        s = "ALDX-2025-04-03"
        pages[s] = pages[s].replace("CRL_NDA216442_20250402.pdf", "CRL_NDA216442_20260316.pdf")
    elif which == "release":
        s = "PHAR-2026-02-01"
        pages[s] = pages[s].replace("globenewswire.com/news-release/2026/02/01/", "globenewswire.com/news-release/2026/05/05/")
    elif which == "drug":
        s = "MIST-2025-03-28"
        pages[s] = re.sub(r'<div class="kv"><span>Drug</span><b>[^<]*</b></div>', "", pages[s])
        pages[s] = pages[s].replace("Was Etripamil nasal spray approved", "Was source-verified approved")
    elif which == "crl_other":
        s = "ALDX-2025-04-03"
        pages[s] = pages[s].replace("CRL_NDA216442_20250402.pdf", "CRL_NDA218345_20250402.pdf")
    elif which == "letter_other":
        s = "SNY-2026-02-24"
        pages[s] = pages[s].replace("761055Orig1s075ltr.pdf", "219873Orig1s000ltr.pdf")
    elif which == "styled":
        s = "ALDX-2026-03-17"
        assert re.search(r'<span>Outcome</span><b style=', pages[s]), "plant expects the styled template"
        pages[s] = pages[s].replace("https://download.open.fda.gov/crl/CRL_NDA216442_20260316.pdf",
                                    "https://www.accessdata.fda.gov/drugsatfda_docs/appletter/2026/216442Orig1s000ltr.pdf")
    elif which == "drug_wrong":
        s = "SNY-2026-02-24"
        pages[s] = re.sub(r'(<div class="kv"><span>Drug</span><b[^>]*>)[^<]*', r"\1Venglustat", pages[s])


if __name__ == "__main__":
    pages, study = load()
    which = os.environ.get("PLANT", "")
    if which:
        plant(pages, study, which)
    bad = check(pages, study)
    if bad:
        print(f"FAIL -- {len(bad)} decision page citation(s) do not match the page:")
        for b in bad:
            print("  " + b)
        sys.exit(1)
    print(f"OK -- {len(pages)} decision pages: SEC filings are the company's own (or a listed partner's or a 13F "
          f"fund's), cited FDA letters match the action, and all {len(study & set(pages))} run-up study pages name "
          "their drug.")
