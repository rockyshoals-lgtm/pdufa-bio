# -*- coding: utf-8 -*-
"""build_crl_dataset.py -- every released Complete Response Letter as a citable, versioned data file
(Nov 17 2026 audit, moat move 6: "licensed open data with versioned snapshots").

The FDA's release (openFDA transparency/crl) is a raw OCR dump with repeats, a heading where a company name should
be, and no link to what happened next. This writes the table /crl and /crl/facts are built from, one row per distinct
Complete Response Letter, with the same rules those pages state:

    pdufa_site_src/crl/data/crl-letters.json   (meta: source, openFDA last_updated, rules, licence; rows)
    pdufa_site_src/crl/data/crl-letters.csv    (the rows)
    pdufa_site_src/crl/data/crl-letters-<openFDA last_updated>.json   written once per FDA release, never rewritten

and puts a schema.org Dataset (CC BY 4.0, with both downloads) and a visible download line on /crl/facts.

Columns are the FDA's fields as printed, plus three joins, each named for its source: the Orange Book's first listed
approval after the letter (original NDAs only; BLAs are not in the Orange Book), the letter's own deficiency headings
(2024+ letters whose PDF holds only that letter; extract_crl_headings.py), and pdufa.bio's decision page for the
letter where one cites it. No rates, no predictions. The letters are the FDA's; the table is pdufa.bio's.

    python build_crl_dataset.py
"""
import collections
import csv
import datetime as dt
import glob
import io
import json
import os
import re
import sys
from urllib.parse import unquote as _uq
from zoneinfo import ZoneInfo

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
sys.path.insert(0, HERE)
from build_crl_facts import CORPUS, GARBLED, esc, is_supplement, orange_book  # noqa: E402
from build_crl_companies import label_of  # noqa: E402
from build_feeds import crl_letters  # noqa: E402

BASE = "https://www.pdufa.bio"
OUT = os.path.join(SITE, "crl", "data")
FACTS = os.path.join(SITE, "crl", "facts", "index.html")
LIC = "https://creativecommons.org/licenses/by/4.0/"
SRC = "https://open.fda.gov/apis/transparency/completeresponseletters/"
DS, DE = "<!--CRLDATA:LD:BEGIN-->", "<!--CRLDATA:LD:END-->"
VS, VE = "<!--CRLDATA:BEGIN-->", "<!--CRLDATA:END-->"
COLS = ["letter_date", "application_numbers", "company_name_as_printed", "company_group", "openfda_approval_status",
        "rescinded_by_fda", "rescission_date", "letter_pdf", "orange_book_nda_first_approval_after_letter",
        "orange_book_trade_name", "deficiency_sections", "pdufa_bio_page"]


def rows(corpus=None):
    letters, last_updated, _ = crl_letters(include_rescinded=True, corpus=corpus)
    ob, ob_as_of = orange_book()
    try:
        from extract_crl_headings import substantive_sections, OUT as HP
        hcache = json.load(io.open(HP, encoding="utf-8")) if os.path.exists(HP) else {}
    except Exception:
        substantive_sections, hcache = None, {}
    files = collections.Counter(L["file"] for L in letters)
    by_key = collections.defaultdict(list)            # the /crl/companies group label: its most common printed form
    for L in letters:
        if L["ckey"]:
            by_key[L["ckey"]].append(label_of(L["name"]))
    group = {k: collections.Counter(v).most_common(1)[0][0] for k, v in by_key.items()}
    ours = {}
    for p in glob.glob(os.path.join(SITE, "fda-decision", "*", "index.html")):
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        if re.search(r'<meta name="robots" content="[^"]*noindex', doc):
            continue
        m = re.search(r'<!--CRLSRC:BEGIN-->.*?href="https://download\.open\.fda\.gov/crl/([^"]+)"', doc, re.S)
        if m:
            ours.setdefault(_uq(m.group(1)), []).append(os.path.basename(os.path.dirname(p)))
    out = []
    for L in sorted(letters, key=lambda x: (x["date"], x["app_txt"], x["file"]), reverse=True):
        ndas = list(dict.fromkeys(n for t, n, s in L["apps"] if t == "NDA" and not is_supplement(s)))
        after = sorted((ob[n][0], ob[n][1]) for n in ndas if n in ob and ob[n][0] > L["date"])
        secs = ""
        if L["date"].year >= 2024 and files[L["file"]] == 1 and substantive_sections:
            s_ = substantive_sections(L["file"], hcache)
            secs = "; ".join(s_) if s_ else ""
        page = ""
        if files[L["file"]] == 1 and len(ours.get(L["file"], [])) == 1:
            page = f"{BASE}/fda-decision/{ours[L['file']][0]}"
        out.append({
            "letter_date": L["date"].isoformat(),
            "application_numbers": L["app_txt"],
            "company_name_as_printed": L["name"],
            "company_group": group.get(L["ckey"], ""),
            "openfda_approval_status": L["status"],
            "rescinded_by_fda": bool(L["rescinded"]),
            "rescission_date": L["resc_date"].isoformat() if L["resc_date"] else "",
            "letter_pdf": L["url"],
            "orange_book_nda_first_approval_after_letter": after[0][0].isoformat() if after else "",
            "orange_book_trade_name": after[0][1] if after else "",
            "deficiency_sections": secs,
            "pdufa_bio_page": page,
        })
    return out, last_updated, ob_as_of


def sig(rows_):
    return sorted((r["letter_date"], r["application_numbers"], r["openfda_approval_status"]) for r in rows_)


def csv_cell(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    v = str(v)
    return "'" + v if v[:1] in ("=", "+", "-", "@") else v   # a spreadsheet would run it as a formula


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", help="an older dated FDA snapshot: write only its dated copy")
    a = ap.parse_args()
    corpus = a.corpus or CORPUS
    data, last_updated, ob_as_of = rows(corpus)
    snap = (re.search(r"(\d{4}-\d{2}-\d{2})", os.path.basename(corpus)) or [None, ""])[1]
    n_live = sum(1 for r in data if not r["rescinded_by_fda"])
    meta = {
        "name": "FDA Complete Response Letters, one row per distinct letter",
        "publisher": "pdufa.bio", "url": f"{BASE}/crl/facts", "license": LIC,
        "licence_note": "The letters are the FDA's (public domain). This table, its cleaning and its joins are "
                        "pdufa.bio's, under CC BY 4.0: cite pdufa.bio and link the page.",
        "source": "FDA CRL release, openFDA transparency/crl", "source_url": SRC,
        "openfda_last_updated": last_updated, "snapshot_read": snap,
        "orange_book_files_dated": ob_as_of,
        "rows": len(data), "rows_not_rescinded": n_live,
        "rules": [
            "Only records the FDA typed COMPLETE RESPONSE; tentative approvals, refusals to file, provisional "
            "determinations, rescissions and untyped records are left out.",
            "A record repeats another when its letter date, application numbers and text are the same; it is kept once.",
            "rescinded_by_fda is true where the FDA's own rescission letter names the letter as issued in error; "
            "rescission_date is that rescission letter's date. /crl/facts keeps them in its total and its yearly "
            "table and leaves them out of its repeat and letter-to-approval counts; /feed leaves them out.",
            "openfda_approval_status is the release's own approval_status field, as printed.",
            "company_group is the company's group on /crl/companies: printed names are grouped with case, accents, "
            "punctuation and corporate-form words set aside, and the group is labeled with its most common printed "
            "form. Blank where the release prints a heading or a bare corporate-form word in place of a name (no "
            "lower-case letter).",
            "orange_book_nda_first_approval_after_letter: the earliest approval the Orange Book products file lists "
            "for the NDA, when that date is after the letter (original NDAs only; the earliest such NDA when a letter "
            "names several), with orange_book_trade_name its trade name. Blank for BLAs (not in the Orange Book), "
            "supplements, NDAs with no listed approval, and NDAs whose first listed approval is on or before the "
            "letter's date (the NDA was already approved, or approved the same day), even when other products under "
            "that NDA were approved later.",
            "deficiency_sections: the letter's own section headings read from its PDF text layer, labeling and "
            "administrative sections left out; only 2024+ letters whose PDF holds this letter alone; blank when "
            "none was read.",
            "pdufa_bio_page: pdufa.bio's decision page that cites this letter's PDF, when exactly one indexable page "
            "does and the PDF holds this letter alone; blank otherwise.",
            "In the CSV, booleans are true or false, and a text cell that starts with = + - or @ is written with a "
            "leading apostrophe so a spreadsheet shows it as text; the JSON keeps every value as printed.",
        ],
        "columns": COLS,
        "not_advice": "Facts from FDA documents. Not a prediction about any application and not investment advice.",
    }
    os.makedirs(OUT, exist_ok=True)
    body = json.dumps({"meta": meta, "rows": data}, indent=1, ensure_ascii=False) + "\n"
    dated = bool(data) and bool(re.match(r"^\d{4}-\d{2}-\d{2}$", last_updated or ""))
    if not a.corpus:
        io.open(os.path.join(OUT, "crl-letters.json"), "w", encoding="utf-8").write(body)
        with io.open(os.path.join(OUT, "crl-letters.csv"), "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f, quoting=csv.QUOTE_ALL)    # utf-8-sig: a spreadsheet then reads accents right
            w.writerow(COLS)
            for r in data:
                w.writerow([csv_cell(r[c]) for c in COLS])
        with io.open(os.path.join(OUT, "crl-letters.csv"), encoding="utf-8-sig", newline="") as f:
            back = sum(1 for _ in csv.DictReader(f))
        if back != len(data):                         # a quoting slip would lose rows
            raise SystemExit(f"  CSV round trip lost rows: wrote {len(data)}, read {back}")
    if dated:
        # one file per FDA release, never rewritten. openFDA has changed a release's records without changing its
        # last_updated date, so when the rows differ from every copy kept for that date, a second copy is named with
        # the day pdufa.bio read the snapshot as well.
        same = [p for p in glob.glob(os.path.join(OUT, f"crl-letters-{last_updated}*.json"))]
        if not any(sig(json.load(io.open(p, encoding="utf-8")).get("rows", [])) == sig(data) for p in same):
            name = f"crl-letters-{last_updated}.json" if not same else f"crl-letters-{last_updated}-read-{snap}.json"
            if not os.path.exists(os.path.join(OUT, name)):
                io.open(os.path.join(OUT, name), "w", encoding="utf-8").write(body)
                print(f"  crl dataset: wrote dated copy {name}")
    else:
        print("  crl dataset: no rows or no openFDA last_updated date; no dated copy written this run")
    if a.corpus:
        return

    versions = sorted(os.path.basename(p)[12:-5] for p in glob.glob(os.path.join(OUT, "crl-letters-????-??-??*.json")))
    if os.path.exists(FACTS):
        doc = io.open(FACTS, encoding="utf-8", errors="replace").read()
        ld = {"@context": "https://schema.org", "@type": "Dataset",
              "name": "FDA Complete Response Letters, one row per distinct letter (pdufa.bio)",
              "description": (f"{len(data)} distinct Complete Response Letters from the FDA's CRL release (openFDA, "
                              f"last updated {last_updated}), each with its application, the company as printed, "
                              "openFDA's status, the FDA's PDF, the first Orange Book approval after the letter for "
                              "original NDAs, and the letter's own deficiency headings for 2024+ letters."),
              "url": f"{BASE}/crl/facts", "license": LIC, "isAccessibleForFree": True,
              "creator": {"@type": "Organization", "name": "pdufa.bio", "url": BASE + "/"},
              "isBasedOn": SRC, "version": last_updated or snap,
              "dateModified": dt.datetime.now(ZoneInfo("America/New_York")).date().isoformat(),
              "distribution": [{"@type": "DataDownload", "encodingFormat": "text/csv",
                                "contentUrl": f"{BASE}/crl/data/crl-letters.csv"},
                               {"@type": "DataDownload", "encodingFormat": "application/json",
                                "contentUrl": f"{BASE}/crl/data/crl-letters.json"}]}
        blk = DS + '<script type="application/ld+json">' + json.dumps(ld, separators=(",", ":"), ensure_ascii=False) \
            + "</script>" + DE
        line = (VS + '<p class="sub">Download every letter as data: <a href="/crl/data/crl-letters.csv">CSV</a> '
                f'&middot; <a href="/crl/data/crl-letters.json">JSON</a> ({len(data)} rows, one per distinct letter; the '
                f'{len(data) - n_live} the FDA rescinded as issued in error are flagged). A dated copy is kept for each FDA release ('
                + ", ".join(f'<a href="/crl/data/crl-letters-{v}.json">{esc(v.replace("-read-", " read "))}</a>'
                            for v in versions)
                + '). Free under CC BY 4.0: cite pdufa.bio and link this page.</p>' + VE)
        doc2 = re.sub(re.escape(DS) + ".*?" + re.escape(DE), "", doc, flags=re.S)
        doc2 = re.sub(re.escape(VS) + ".*?" + re.escape(VE), "", doc2, flags=re.S)
        doc2 = doc2.replace("</head>", blk + "</head>", 1)
        m = re.search(r"every CRL, by company</a>.*?</p>", doc2, re.S)
        if m:
            doc2 = doc2[:m.end()] + line + doc2[m.end():]
        if doc2 != doc:
            io.open(FACTS, "w", encoding="utf-8").write(doc2)
    print(f"  crl dataset: {len(data)} rows ({n_live} not rescinded), openFDA {last_updated}, versions {versions}")


if __name__ == "__main__":
    main()
