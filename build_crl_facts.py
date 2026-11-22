# -*- coding: utf-8 -*-
"""build_crl_facts.py -- /crl/facts: counts from the FDA's released Complete Response Letters, each reproducible.

David, 2026-11-22: "can we increase our CRL library and present facts about CRLs that no one else has?" The
/crl hub lists every letter; this page states what the release shows when it is joined to other primary
sources, and how each count is made, so a reader can redo it:

  1. letters per year, and the record types the release mixes in (tentative approvals, a rescission, ...)
  2. which deficiency sections the FDA's own 2024+ letters name (headings read from each PDF's text layer by
     extract_crl_headings.py; a letter whose sections carry no heading is counted as such, never guessed)
  3. applications with more than one released CRL
  4. for NDAs, the days from the last released CRL to the first approval the FDA's Orange Book records
  5. letters openFDA still labels "Unapproved" whose NDA the Orange Book lists as approved after the letter
  6. the FDA's rescission of letters "issued in error"
  7. CRLs on this site's decision pages: the FDA letter date against the date the decision became public

FACTS ONLY. No rates of approval after a CRL (the pre-2024 release is approved by construction and 2024+ is
right-censored; see CRL_corpus_README.md), no predictions, no scores. Every number is a count or a date
difference from the files named on the page. Rebuilt on every run from the newest corpus snapshot.

    python build_crl_facts.py
"""
import collections
import datetime as dt
import glob
import html as _html
import io
import json
import os
import re
import statistics
import sys
from urllib.parse import quote as _urlq, unquote as _uq

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
sys.path.insert(0, HERE)
from capture_crl_corpus import newest_corpus  # noqa: E402
CORPUS = newest_corpus() or os.path.join(HERE, "CRL_corpus_openFDA_2026-08-29.json")
OB_DIR = os.path.join(HERE, "_orange_book")
BASE = "https://www.pdufa.bio"
PDF = "https://download.open.fda.gov/crl/"
MON = ["", "January", "February", "March", "April", "May", "June", "July", "August",
       "September", "October", "November", "December"]
CR = "COMPLETE RESPONSE"
GARBLED = re.compile(r"RESUBMISSION|^[^a-z]*$")   # openFDA's company_name sometimes holds a heading ("CLASS 2 RESUBMISSION")

# a letter's section headings -> the families this page counts (matched on the letter's own words)
FAMILIES = [
    ("Product quality or CMC", r"product quality|drug product quality|drug substance|chemistry, manufacturing|\bcmc\b|"
                               r"quality microbiolog|product quality microbiolog|sterility|biopharmaceutic|immunogenicity"),
    ("Facility inspections", r"facilit"),
    ("Clinical or statistical", r"^clinical(?! pharmacology| microbiology)|statistic|biostatistic|efficacy"),
    ("Clinical pharmacology", r"clinical pharmacology"),
    ("Nonclinical", r"nonclinical|pharmacology/toxicology|toxicolog"),
    ("Human factors or device", r"human factors|device"),
    ("Clinical microbiology", r"clinical microbiology"),
    # red team: all ten bare "Microbiology" headings in the 2024+ letters sit in product-quality sections, so a bare
    # heading is counted as written and assigned to no clinical or quality family
    ("Microbiology (heading as written, not further specified)", r"^microbiology$"),
    ("REMS", r"risk evaluation"),
]


def esc(s):
    return _html.escape(str(s or "").strip())


def pretty(d):
    return f"{MON[d.month]} {d.day}, {d.year}"


def iso(s):
    m = re.match(r"(\d{2})/(\d{2})/(\d{4})", str(s or ""))
    return dt.date(int(m.group(3)), int(m.group(1)), int(m.group(2))) if m else None


def parse_app(a):
    """'NDA 018680/S-074' -> ('NDA', 18680, 'S-074'); 'BL 125842' -> ('BLA', 125842, '')."""
    m = re.match(r"\s*(NDA|BLA|BL|ANDA)\s*0*(\d+)\s*(?:/\s*(.*))?$", str(a or ""), re.I)
    if not m:
        return None
    t = m.group(1).upper()
    return ("BLA" if t in ("BL", "BLA") else t), int(m.group(2)), (m.group(3) or "").strip()


def is_supplement(sfx):
    return bool(re.match(r"S-?\d", sfx or "", re.I))


def orange_book():
    """NDA number -> (first approval date, trade name, applicant), from the Orange Book products file."""
    p = os.path.join(OB_DIR, "products.txt")
    out = {}
    if not os.path.exists(p):
        return out, ""
    for line in io.open(p, encoding="utf-8", errors="replace").read().splitlines()[1:]:
        f = line.split("~")
        if len(f) < 14 or f[5].strip() != "N":
            continue
        try:
            d = dt.datetime.strptime(f[9].strip(), "%b %d, %Y").date()
        except ValueError:
            continue          # "Approved Prior to Jan 1, 1982" -- no date to count from
        n = int(f[6])
        if n not in out or d < out[n][0]:
            out[n] = (d, f[2].strip().title(), f[13].strip() or f[3].strip())
    as_of = ""
    ap = os.path.join(OB_DIR, "_as_of.txt")
    if os.path.exists(ap):
        parts = io.open(ap, encoding="utf-8").read().split()   # "<FDA files' date> <date we checked>"
        as_of = parts[0] if parts else ""
    return out, as_of


def main():
    raw = json.load(io.open(CORPUS, encoding="utf-8"))
    recs = raw.get("results") if isinstance(raw, dict) else raw
    last_updated = str((raw.get("meta") or {}).get("last_updated") or "") if isinstance(raw, dict) else ""
    snap = re.search(r"(\d{4}-\d{2}-\d{2})", os.path.basename(CORPUS))
    snap = snap.group(1) if snap else ""

    # one row per letter, a repeat counted once. Red team: keying on (file, date) alone merged two different
    # applications that share one combined PDF (Gilead NDA 215974, ViiV NDA 212887) and kept a true repeat released
    # under a second file name (BLA 761215); a record repeats another when its date, type, application numbers and
    # text are all the same (the /crl hub uses the same rule).
    seen, letters = set(), []
    for r in recs:
        d = iso(r.get("letter_date"))
        fn = str(r.get("file_name") or "").strip()
        k = (d, str(r.get("letter_type")), tuple(sorted(str(x).strip() for x in (r.get("application_number") or []))),
             re.sub(r"\s+", " ", str(r.get("text") or "")).strip().lower())
        if not d or k in seen:
            continue
        seen.add(k)
        apps = [x for x in (parse_app(a) for a in (r.get("application_number") or [])) if x]
        letters.append({"date": d, "file": fn, "type": str(r.get("letter_type") or "(none given)"),
                        "status": str(r.get("approval_status") or ""), "company": str(r.get("company_name") or "").strip(),
                        "apps": apps, "app_txt": ", ".join(r.get("application_number") or []),
                        "url": PDF + _urlq(fn) if fn.lower().endswith(".pdf") else "",
                        "text": re.sub(r"\s+", " ", str(r.get("text") or ""))})
    crl = [L for L in letters if L["type"] == CR]
    # letters the FDA later rescinded as "issued in error": the rescission names them by date; they stay in the
    # yearly count (they are in the release) and leave the repeat and letter-to-approval counts
    rescind = [L for L in letters if "RESCIND" in L["type"].upper()]
    voided = set()
    for R in rescind:
        m = re.search(r"refer to our letters? dated (.{0,120}?)(?:,? informing|\.)", R["text"], re.I)
        for ds in re.findall(r"(?:" + "|".join(MON[1:]) + r") \d{1,2}, \d{4}", m.group(1) if m else ""):
            vd = dt.datetime.strptime(ds, "%B %d, %Y").date()
            for L in crl:
                if L["date"] == vd and set(L["apps"]) & set(R["apps"]):
                    voided.add(id(L))
    counted = [L for L in crl if id(L) not in voided]
    n_all, n_cr = len(letters), len(crl)
    types = collections.Counter(L["type"] for L in letters if L["type"] != CR)
    by_year = collections.Counter(L["date"].year for L in crl)

    # --- 2. sections named in the 2024+ letters (one letter per PDF, FDA's CRL_*.pdf files) -------------------------
    try:
        from extract_crl_headings import substantive_sections, OUT as HP
        hcache = json.load(io.open(HP, encoding="utf-8")) if os.path.exists(HP) else {}
    except Exception:
        substantive_sections, hcache = None, {}
    files = collections.Counter(L["file"] for L in crl)
    own = [L for L in crl if L["date"].year >= 2024 and files[L["file"]] == 1 and L["url"]]
    fam_n = collections.Counter()
    n_read = n_head = 0
    for L in own:
        rec = hcache.get(L["file"])
        if not rec or not rec.get("text_layer"):
            continue
        n_read += 1
        secs = (substantive_sections(L["file"], hcache) if substantive_sections else None) or []
        fams = {name for name, rx in FAMILIES for s in secs if re.search(rx, s, re.I)}
        if not fams:
            continue
        n_head += 1
        for f_ in fams:
            fam_n[f_] += 1

    # --- 3. applications with more than one released CRL --------------------------------------------------------
    by_app = collections.defaultdict(list)
    for L in counted:
        for t, n, sfx in L["apps"]:
            key = (t, n, sfx if is_supplement(sfx) else "")
            if L not in by_app[key]:
                by_app[key].append(L)
    multi = sorted(((k, sorted(v, key=lambda x: x["date"])) for k, v in by_app.items() if len(v) >= 2),
                   key=lambda kv: (-len(kv[1]), kv[1][-1]["date"]), reverse=False)
    n_multi = len(multi)
    n_multi3 = sum(1 for _, v in multi if len(v) >= 3)

    # --- 4/5. NDA originals: last released CRL -> first Orange Book approval ------------------------------------
    ob, ob_as_of = orange_book()
    gaps, gap_rows, stale_status, ob_before = [], [], [], 0
    for (t, n, sfx), ls in by_app.items():
        if t != "NDA" or sfx:
            continue
        last = max(ls, key=lambda x: x["date"])
        hit = ob.get(n)
        if not hit:
            continue
        if hit[0] <= last["date"]:
            ob_before += 1      # the listed product predates the letter (an earlier product on the same NDA)
            continue
        days = (hit[0] - last["date"]).days
        gaps.append(days)
        gap_rows.append((n, last, hit, days))
        # only an approval the Orange Book dates before openFDA's own last update can show openFDA's label is stale
        if last["status"] == "Unapproved" and (not last_updated or hit[0].isoformat() < last_updated):
            stale_status.append((n, last, hit))
    gaps.sort()
    # quartiles: Python statistics.quantiles(n=4), its default "exclusive" method
    q = statistics.quantiles(gaps, n=4) if len(gaps) >= 4 else [0, 0, 0]
    med = statistics.median(gaps) if gaps else 0
    med_s = f"{med:g}"
    buckets = collections.OrderedDict([("under 1 year", 0), ("1 to 2 years", 0), ("2 to 3 years", 0),
                                       ("3 years or more", 0)])
    for g in gaps:
        buckets["under 1 year" if g < 365 else "1 to 2 years" if g < 730 else "2 to 3 years" if g < 1095
                else "3 years or more"] += 1
    fastest = sorted(gap_rows, key=lambda x: x[3])[:5]


    # --- 7. our decision pages that carry the FDA's letter -------------------------------------------------------
    lag, lag_skipped = [], []
    try:   # hand-verified letters: a corrected letter carries a later date than the FDA's action
        act = {x["file_name"]: dt.date.fromisoformat(x["fda_action_date"]) for x in json.load(io.open(
            os.path.join(HERE, "_crl_letter_findings.json"), encoding="utf-8"))["letters"] if x.get("fda_action_date")}
    except Exception:
        act = {}
    for p in sorted(glob.glob(os.path.join(SITE, "fda-decision", "*", "index.html"))):
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        m = re.search(r'<!--CRLSRC:BEGIN-->.*?href="https://download\.open\.fda\.gov/crl/([^"]+)"', doc, re.S)
        if not m:
            continue
        slug = os.path.basename(os.path.dirname(p))
        sd = re.search(r"(\d{4}-\d{2}-\d{2})$", slug)
        fn = _uq(m.group(1))
        ld = act.get(fn) or next((L["date"] for L in crl if L["file"] == fn), None)
        if not sd or not ld:
            lag_skipped.append(slug)
            continue
        lag.append(((dt.date.fromisoformat(sd.group(1)) - ld).days, slug, ld))
    lag.sort()
    lag_n = collections.Counter(min(x[0], 4) for x in lag)

    # --- page ---------------------------------------------------------------------------------------------------
    yr0, yr1 = min(by_year), max(by_year)
    title = f"FDA Complete Response Letter Facts: What {n_cr} Released CRLs Show | pdufa.bio"
    desc = (f"Counts from {n_cr} FDA Complete Response Letters: sections cited, repeat CRLs, days from a CRL to "
            f"approval (Orange Book), each reproducible from FDA files.")
    B = []
    B.append(f'<h1>FDA Complete Response Letters: <span class="g">facts from the release</span></h1>')
    n_rec = len(recs)
    B.append(f'<p class="sub">The FDA has released {n_rec} records under its CRL transparency program '
             f'(openFDA, last updated {esc(last_updated)}; snapshot read {esc(snap)}). '
             + (f'{n_rec - n_all} of them {"repeats" if n_rec - n_all == 1 else "repeat"} another record (same date, application numbers and text), '
                f'leaving {n_all} distinct records. ' if n_rec != n_all else '') +
             f'{n_cr} are Complete Response Letters dated {yr0} to {yr1}. Each count below says which files it comes from and how it is made, so '
             f'anyone can redo it. Counts and date differences only: no approval rates, no predictions. '
             f'<a href="/crl">Every letter, by year</a>; <a href="/crl/companies">every CRL, by company</a>.</p>')

    B.append('<h2>Letters in the release, by year</h2><table><tr><th>Letter year</th><th>Complete Response Letters</th></tr>')
    for y in sorted(by_year, reverse=True):
        B.append(f'<tr><td class="dt">{y}</td><td>{by_year[y]}</td></tr>')
    B.append('</table>')
    if types:
        B.append('<p class="sub">The release also holds ' + "; ".join(
            f"{v} record{'s' if v != 1 else ''} typed {esc(k.title() if k != '(none given)' else 'with no letter type')}"
            for k, v in types.most_common()) + '. They are not counted as CRLs on this page.</p>')

    B.append(f'<h2>What the 2024+ letters name as deficient</h2>'
             f'<p class="sub">{len(own)} Complete Response Letters dated 2024 or later have a PDF of their own. '
             f'{n_read} of them have a text layer we read; {n_head} carry at least one deficiency section heading in '
             f'the FDA\'s own words (labeling, safety update and other administrative sections set aside). The other '
             f'{n_read - n_head} carry no deficiency heading that the extractor recognizes yet, so they are left out of '
             f'the table rather than guessed; they are read again as its vocabulary grows. A letter can name several '
             f'sections.</p>'
             f'<table><tr><th>Section family (the letter\'s own heading)</th><th>Letters, of {n_head}</th></tr>')
    for name, _ in FAMILIES:
        if fam_n[name]:
            B.append(f'<tr><td class="dt">{esc(name)}</td><td>{fam_n[name]}</td></tr>')
    B.append('</table><p class="sub">Headings are read from the PDF text layer only (extract_crl_headings.py), '
             'never from openFDA\'s OCR text.</p>')

    B.append(f'<h2>Applications with more than one released CRL</h2>'
             f'<p class="sub">{n_multi} applications (an original NDA or BLA, or one supplement) have two or more '
             f'Complete Response Letters in the release; {n_multi3} have three or more. Grouped on the application '
             f'number the FDA printed on each record' + (f'; {len(voided)} letters the FDA later rescinded as issued in '
                                                    f'error are left out' if voided else '') + '.</p>'
             '<table><tr><th>Application</th><th>Company</th><th>Letters</th><th>Letter dates</th></tr>')
    for (t, n, sfx), ls in multi[:15]:
        app = f"{t} {n:06d}" + (f"/{sfx}" if sfx else "")
        dates = ", ".join(f'<a href="{esc(L["url"])}" rel="noopener">{esc(pretty(L["date"]))}</a>' if L["url"]
                          else esc(pretty(L["date"])) for L in ls)
        co = next((L["company"] for L in reversed(ls) if L["company"] and not GARBLED.search(L["company"])), "")
        B.append(f'<tr><td class="dt">{esc(app)}</td><td>{esc(co[:40])}</td>'
                 f'<td>{len(ls)}</td><td style="font-size:12.5px">{dates}</td></tr>')
    B.append('</table>' + (f'<p class="sub">The {n_multi - 15} others are on <a href="/crl">the full list</a>.</p>'
                           if n_multi > 15 else ''))

    B.append(f'<h2>From the last released CRL to approval (NDAs)</h2>'
             f'<p class="sub">For {len(gaps)} original NDAs, the FDA\'s Orange Book (products file, '
             f'FDA files dated {esc(ob_as_of) or "as downloaded"}) lists a first approval after the last Complete Response Letter '
             f'in the release' + (' (rescinded letters left out)' if voided else '') + f'. Days from that letter to that approval: median <b>{med_s}</b>, '
             f'middle half (quartiles) {q[0]:g} to {q[2]:g}, shortest {gaps[0] if gaps else 0}, longest '
             f'{gaps[-1] if gaps else 0}.</p><table><tr><th>Letter to approval</th><th>NDAs</th></tr>')
    for k, v in buckets.items():
        B.append(f'<tr><td class="dt">{esc(k)}</td><td>{v}</td></tr>')
    B.append(f'</table><p class="sub">Read this as a description of the released letters, not of CRLs in '
             f'general: the FDA released its older letters for applications it had approved, and recent letters '
             f'have had little time to resolve. BLAs are not in the Orange Book and are not counted. {ob_before} '
             f'NDAs whose earliest listed product predates the letter are left out. Shortest gaps:</p>'
             '<table><tr><th>NDA</th><th>Product (Orange Book)</th><th>Last CRL</th><th>Approved</th><th>Days</th></tr>')
    for n, L, hit, days in fastest:
        B.append(f'<tr><td class="dt">{n:06d}</td><td>{esc(hit[1][:36])}</td>'
                 f'<td><a href="{esc(L["url"])}" rel="noopener">{esc(pretty(L["date"]))}</a></td>'
                 f'<td>{esc(pretty(hit[0]))}</td><td>{days}</td></tr>')
    B.append('</table>')

    if stale_status:
        B.append(f'<h2>Labeled "Unapproved" by openFDA, approved in the Orange Book</h2>'
                 f'<p class="sub">openFDA\'s approval_status field says these {len(stale_status)} letters belong '
                 f'to applications not approved. The Orange Book lists each NDA as approved after the letter. '
                 f'Both are FDA files; the Orange Book lists each product as approved, and each approval it lists is dated '
                 f'before openFDA\'s last update ({esc(last_updated)}).</p>'
                 '<table><tr><th>NDA</th><th>Product</th><th>CRL</th><th>Orange Book approval</th></tr>')
        for n, L, hit in sorted(stale_status, key=lambda x: x[2][0], reverse=True):
            B.append(f'<tr><td class="dt">{n:06d}</td><td>{esc(hit[1][:36])}</td>'
                     f'<td><a href="{esc(L["url"])}" rel="noopener">{esc(pretty(L["date"]))}</a></td>'
                     f'<td>{esc(pretty(hit[0]))}</td></tr>')
        B.append('</table>')

    if rescind:
        B.append('<h2>Letters the FDA rescinded</h2>')
        for L in rescind:
            B.append(f'<p class="sub">{esc(L["app_txt"])}, {esc(L["company"])}: a record typed '
                     f'"{esc(L["type"].title())}" dated {esc(pretty(L["date"]))}'
                     + (f' (<a href="{esc(L["url"])}" rel="noopener">PDF</a>)' if L["url"] else "")
                     + '. It is not counted as a CRL above. It names the FDA\'s earlier letters on the application as '
                     'issued in error; those letters stay in the yearly count, because they are in the release, and are '
                     'left out of the repeat-CRL and letter-to-approval counts.</p>')

    if lag:
        B.append(f'<h2>The letter\'s date against our decision page\'s date</h2>'
                 f'<p class="sub">{len(lag)} decision pages on this site carry the FDA\'s own released letter. '
                 f'Days from the letter\'s date (the FDA\'s stated action date, for a corrected letter) to the date our decision page '
                 f'is filed under:</p><table><tr><th>Days after the letter</th><th>Pages</th></tr>')
        for k in sorted(lag_n):
            B.append(f'<tr><td class="dt">{"4 or more" if k == 4 else k}</td><td>{lag_n[k]}</td></tr>')
        B.append('</table>' + (f'<p class="sub">{len(lag_skipped)} more page{"s" if len(lag_skipped) != 1 else ""} {"link" if len(lag_skipped) != 1 else "links"} '
                               f'a letter that is not in the snapshot read here and {"are" if len(lag_skipped) != 1 else "is"} '
                               f'not counted.</p>' if lag_skipped else ''))
        late = [x for x in lag if x[0] >= 4]
        if late:
            B.append('<p class="sub">Four days or more: ' + "; ".join(
                f'<a href="/fda-decision/{esc(s)}">{esc(s)}</a> ({d} days after the letter of {esc(pretty(ld))})'
                for d, s, ld in late) + '.</p>')

    B.append('<h2>How this page is made</h2><p class="sub">Inputs: the FDA\'s CRL release (openFDA '
             f'transparency/crl, snapshot {esc(snap)}), the section headings each PDF\'s text layer carries '
             '(_crl_headings.json), the Orange Book products file (_orange_book/products.txt), and this site\'s '
             'decision pages. The script is build_crl_facts.py in the site\'s public repository; it runs on every '
             'rebuild. A letter the FDA released twice (same date, application numbers and text) is counted once. <a href="/crl/capricor-deramiocel">'
             'Capricor\'s two CRLs for deramiocel</a>, from the primary sources.</p>')

    doc = (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
           f'<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
           f'<title>{esc(title)}</title><meta name="description" content="{esc(desc)}">'
           f'<link rel="canonical" href="{BASE}/crl/facts">'
           f'<meta name="robots" content="index,follow,max-image-preview:large">'
           f'<meta name="theme-color" content="#02060d"><meta property="og:type" content="website">'
           f'<meta property="og:site_name" content="pdufa.bio"><meta property="og:url" content="{BASE}/crl/facts">'
           f'<meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}">'
           f'<style>{CSS}</style></head><body><div class="wrap">{NAV}' + "".join(B) + "</div></body></html>")
    out = os.path.join(SITE, "crl", "facts", "index.html")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    io.open(out, "w", encoding="utf-8").write(doc)
    print(f"/crl/facts: {n_cr} CRLs ({n_all} distinct of {len(recs)} records); sections {n_head}/{n_read} read 2024+ letters; "
          f"{n_multi} repeat-CRL applications; {len(gaps)} NDA CRL->approval gaps (median "
          f"{med_s} d); {len(stale_status)} openFDA-unapproved but OB-approved; "
          f"{len(rescind)} rescission(s); {len(lag)} decision pages with the letter")
    return 0


CSS = ("*{box-sizing:border-box}body{margin:0;background:#02060d;color:#f2f6fc;"
       "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,"
       "Arial,sans-serif;line-height:1.55}a{color:#6fb6ff;text-decoration:none}"
       "a:hover{text-decoration:underline}.wrap{max-width:900px;margin:0 auto;"
       "padding:22px 18px 60px}.top{display:flex;align-items:center;"
       "justify-content:space-between;border-bottom:1px solid #1a3358;"
       "padding-bottom:12px}.brand{font-size:19px;font-weight:800}"
       ".brand b{color:#e3ba5e}.nav a{color:#a7bcd9;font-size:13px;margin-left:14px}"
       "h1{font-size:27px;line-height:1.18;margin:10px 0 6px}h1 .g{color:#e3ba5e}"
       "h2{font-size:18px;color:#e3ba5e;margin:26px 0 8px}"
       ".sub{color:#a7bcd9;font-size:15px;margin:6px 0 14px;max-width:76ch}"
       "table{width:100%;border-collapse:collapse;font-size:13.5px;margin-top:6px}"
       "th{text-align:left;color:#e3ba5e;font-size:11.5px;text-transform:uppercase;"
       "letter-spacing:.4px;padding:7px 6px;border-bottom:1px solid #294d80}"
       "td{padding:7px 6px;border-bottom:1px solid #14263f;color:#a7bcd9;"
       "vertical-align:top}td.dt{color:#f2f6fc;white-space:nowrap}"
       "footer{border-top:1px solid #1a3358;margin-top:34px;padding-top:16px;"
       "font-size:11.5px;color:#94a9c9;line-height:1.6}")
NAV = ('<div class="top"><a class="brand" href="/">pdufa<b>.bio</b></a>'
       '<div class="nav"><!--NAVC:BEGIN--><!--NAVC:END--></div></div>')


if __name__ == "__main__":
    sys.exit(main())
