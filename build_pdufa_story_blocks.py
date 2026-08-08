# -*- coding: utf-8 -*-
"""
build_pdufa_story_blocks.py  - Red Team Pass 8, Workstream C
============================================================
Injects a sourced "The story" card into every per-event PDUFA page under
pdufa_site_src/pdufa/<TICKER>/index.html.

The card carries, in plain English:
  1. What the drug treats (humanized indication, leading with the patient).
  2. Regulatory history - prior Complete Response Letter (CRL) if any (THE key fact).
  3. Cash runway (months / label) + dilution risk if flagged.
  4. 2-3 related internal links (/calendar + same-TA / same-month neighbour pages
     that actually exist on disk).

Idempotent via <!--story-v1--> markers. Native CSS classes. No deploy.
Backup already at pdufa_site_src/_pdufa_bak8.
"""
import csv
import glob
import html
import os
import re

ROOT = os.path.dirname(os.path.abspath(__file__))
PDUFA_DIR = os.path.join(ROOT, "pdufa_site_src", "pdufa")
CATALYSTS = os.path.join(ROOT, "catalysts_out", "catalysts_public.csv")
CRL_CMC = os.path.join(ROOT, "CRL_CMC_cases.csv")

MARKER_OPEN = "<!--story-v1-->"
MARKER_CLOSE = "<!--/story-v1-->"

PLAIN_INDICATION = {
    "UNCY": "high blood phosphate (hyperphosphatemia) in patients on kidney dialysis - a daily pill burden for dialysis patients",
    "HRMY": "gastrointestinal symptoms (a label expansion for the narcolepsy drug WAKIX/pitolisant)",
    "GSK": "complicated urinary tract infections (cUTI) - a serious kidney/bladder infection",
    "GSK-tebipenem-hbr": "complicated urinary tract infections (cUTI) - an oral alternative to IV antibiotics",
    "GSK-tebipenem-pivoxil": "complicated urinary tract infections (cUTI) - an oral alternative to IV antibiotics",
    "SPRO": "complicated urinary tract infections (cUTI) - an oral alternative to IV antibiotics",
    "AZN": "advanced breast and other PTEN-altered cancers (the AKT-inhibitor Truqap/capivasertib)",
    "AZN-truqap": "advanced cancers with PTEN/PIK3CA alterations (the AKT-inhibitor Truqap/capivasertib)",
    "GH": "advanced hormone-receptor-positive breast cancer (the next-generation oral SERD camizestrant)",
    "AZN-camizestrant": "advanced ER-positive/HER2-negative breast cancer (the oral SERD camizestrant)",
    "LLY": "reducing heart-attack and stroke risk in people on tirzepatide (a cardiovascular-outcomes label for the GLP-1/GIP drug)",
    "NVO-am833": "obesity / chronic weight management (the CagriSema combination)",
    "IRD": "presbyopia - age-related loss of near vision (eye drops instead of reading glasses)",
    "VTRS-mr-141": "presbyopia - age-related loss of near vision (eye drops instead of reading glasses)",
    "VTRS-mr-100a-01": "contraception (a low-dose estrogen birth-control product)",
    "VTRS": "contraception (a low-dose estrogen birth-control product)",
    "VTRS-mr-107a-02": "acute pain",
    "NRXP": "pain, using a preservative-free IV ketamine formulation",
    "ACHV": "helping adults quit smoking (the plant-derived smoking-cessation drug cytisinicline)",
    "MNKD": "fluid overload (edema) in chronic heart failure - an at-home under-the-skin alternative to IV diuretics (FUROSCIX)",
    "BTAI": "acute agitation in bipolar I/II disorder (a dissolvable film of dexmedetomidine)",
    "PHAR": "activated PI3K-delta syndrome (APDS) - a rare inherited immune disorder",
    "TLX": "recurrent or progressive glioma - an aggressive type of brain cancer",
    "ABEO": "Sanfilippo syndrome type A (MPS IIIA) - a fatal childhood neurodegenerative disease",
    "VNDA": "generalized pustular psoriasis (GPP) - a rare, severe and painful skin disease",
    "ANAB": "generalized pustular psoriasis (GPP) - a rare, severe and painful skin disease",
    "MRNA": "seasonal influenza in adults 50 and older (an mRNA flu vaccine)",
    "INO": "recurrent respiratory papillomatosis caused by HPV 6/11 - benign airway tumours that keep coming back",
    "SVRA": "autoimmune pulmonary alveolar proteinosis (aPAP) - a rare lung disease where protein clogs the air sacs",
    "BFRI": "basal cell carcinoma - the most common form of skin cancer (a light-activated gel, Ameluz)",
    "ARQT": "plaque psoriasis in young children aged 2 to 5 (a steroid-free roflumilast cream)",
}

TA_KEYWORDS = [
    ("Oncology", ["cancer", "carcinoma", "tumor", "tumour", "lymphoma", "myeloma",
                  "melanoma", "glioma", "leukemia", "leukaemia", "oncolog", "mastocytosis",
                  "polycythemia", "neuroendocrine", "nsclc", "mibc", "her2", "breast"]),
    ("Nephrology", ["kidney", "nephropathy", "dialysis", "phosphate", "iga", "renal"]),
    ("Neurology", ["parkinson", "alzheimer", "epilep", "narcolepsy", "myasthenia",
                   "neuro", "agitation", "ketamine", "alexander", "dystrophy", "duchenne",
                   "muscular", "vitiligo"]),
    ("Immunology / Dermatology", ["psoriasis", "lupus", "dermatomyositis", "vitiligo",
                                  "immune", "apds", "pi3k", "papulopustular", "skin"]),
    ("Rare / Genetic", ["sanfilippo", "mps", "fibrodysplasia", "ossificans", "noonan",
                        "glycogen", "hearing", "girdle", "presbyopia", "alveolar"]),
    ("Infectious disease", ["hiv", "urinary tract", "cuti", "infection", "influenza", "papillomatosis"]),
    ("Metabolic / Cardio", ["obesity", "weight", "hypertension", "cardiovascular",
                            "diabetes", "hypertriglyceridemia", "heart failure", "edema"]),
]


def text_of(s):
    return re.sub(r"<[^>]+>", "", s)


def parse_page(path):
    h = open(path, encoding="utf-8").read()
    drug = ""
    m = re.search(r'<h1>.*?<span class="g">(.*?)</span></h1>', h, re.S)
    if m:
        drug = text_of(m.group(1)).strip()
    date = company = indic = ""
    s = re.search(
        r'</h1>\s*<div class="sub">FDA decision \(PDUFA\) target <b>(.*?)</b> . (.*?) . (.*?)</div>',
        h, re.S)
    if s:
        date = text_of(s.group(1)).strip()
        company = text_of(s.group(2)).strip()
        indic = html.unescape(text_of(s.group(3)).strip())
    tier = ""
    tm = re.search(r"Market-cap tier</span><b>(.*?)</b>", h)
    if tm:
        tier = text_of(tm.group(1)).strip()
    return h, drug, date, company, indic, tier


def load_catalysts():
    by = {}
    with open(CATALYSTS, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            by.setdefault(r["ticker"], []).append(r)
    return by


def load_crl():
    by = {}
    with open(CRL_CMC, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            by.setdefault(r["ticker"], []).append(r)
    return by


def drug_tokens(s):
    return set(re.findall(r"[a-z]{4,}", s.lower()))


def pick_catalyst_row(rows, date, drug):
    if not rows:
        return None
    dtok = drug_tokens(drug)
    for r in rows:
        if r.get("catalyst_date") == date and r.get("category") == "drug":
            return r
    for r in rows:
        if r.get("catalyst_date") == date:
            return r
    best, best_ov = None, 0
    for r in rows:
        ov = len(dtok & drug_tokens(r.get("drug", "")))
        if ov > best_ov:
            best, best_ov = r, ov
    return best or rows[0]


def pick_crl(crl_rows, drug):
    if not crl_rows:
        return None
    dtok = drug_tokens(drug)
    dn = re.sub(r"[^a-z0-9]", "", drug.lower())
    for c in crl_rows:
        cn = re.sub(r"[^a-z0-9]", "", c["drug"].lower())
        ctok = drug_tokens(c["drug"])
        prefix = bool(dn) and bool(cn) and (dn[:6] in cn or cn[:6] in dn)
        if prefix or (dtok & ctok):
            return c
    return None


def fmt_month_year(iso):
    months = ["", "January", "February", "March", "April", "May", "June",
              "July", "August", "September", "October", "November", "December"]
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", iso or "")
    if not m:
        return iso or ""
    return months[int(m.group(2))] + " " + m.group(1)


def ta_for(indic):
    low = (indic or "").lower()
    for name, kws in TA_KEYWORDS:
        if any(k in low for k in kws):
            return name
    return "Other"


def humanize_indication(name, base, indic):
    if name in PLAIN_INDICATION:
        return PLAIN_INDICATION[name], True
    if base in PLAIN_INDICATION:
        return PLAIN_INDICATION[base], True
    s = (indic or "").strip().rstrip(" *.-").strip()
    return s, False


def esc(s):
    return html.escape(s or "", quote=True)


def build_story(name, base, ph_drug, ph_date, ph_company, ph_indic, ph_tier,
                cat_row, crl_row, neighbors):
    lead, curated = humanize_indication(name, base, ph_indic)
    drug_label = ph_drug or (cat_row.get("drug") if cat_row else "") or "This candidate"
    if lead:
        s1 = "<b>" + esc(drug_label) + "</b> is under FDA review to treat " + esc(lead) + "."
    else:
        s1 = "<b>" + esc(drug_label) + "</b> is under FDA review by " + esc(ph_company) + "."

    s2 = ""
    crl_badge = ""
    if crl_row:
        my = fmt_month_year(crl_row.get("crl_date", ""))
        try:
            n = int(crl_row.get("num_crls", "1") or "1")
        except ValueError:
            n = 1
        crl_badge = ' <span class="badge crl">PRIOR CRL</span>'
        if n >= 2:
            s2 = ("Regulatory history: the FDA issued <b>" + str(n) +
                  " prior Complete Response Letters</b> (most recent " + esc(my) +
                  "); this PDUFA is the resubmission.")
        else:
            s2 = ("Regulatory history: the FDA issued a <b>Complete Response Letter</b> in " +
                  esc(my) + " - this PDUFA is the resubmission.")
        if base == "UNCY":
            s2 += (" The prior CRL cited only chemistry/manufacturing (CMC) issues - a factory fix, "
                   "not an efficacy or safety problem - so no new trial was required.")

    s3 = ""
    if cat_row:
        runway = (cat_row.get("cash_runway_months") or "").strip()
        label = (cat_row.get("runway_label") or "").strip()
        src = (cat_row.get("runway_source") or "").strip()
        dil = (cat_row.get("dilution_risk") or "").strip()
        parts = []
        if runway:
            try:
                mo = float(runway)
                parts.append("about <b>" + ("%.0f" % mo) + " months of cash</b>")
            except ValueError:
                pass
        if label:
            parts.append("runway " + esc(label))
        if parts:
            srctxt = (" (" + esc(src) + ")") if (src and src.lower() not in label.lower()) else ""
            s3 = "Balance sheet: " + ", ".join(parts) + srctxt + "."
        if dil:
            s3 += ' <span class="badge amb">' + esc(dil) + "</span>"

    body = " ".join([b for b in [s1, s2, s3] if b])

    links_html = ['<a class="row" href="/calendar"><span class="t">Full PDUFA calendar -&gt;</span>'
                  '<span class="d">Every upcoming FDA decision date, by month</span></a>']
    for nb in neighbors:
        links_html.append(
            '<a class="row" href="/pdufa/' + esc(nb["ticker"]) + '">'
            '<span class="t">' + esc(nb["ticker"]) + ' . ' + esc(nb["date"]) + '</span>'
            '<span class="d">' + esc(nb["why"]) + '</span></a>')
    links_block = '<div class="grid" style="margin-top:10px">' + "".join(links_html) + "</div>"

    card = (
        MARKER_OPEN +
        '<h2 id="the-story">The story' + crl_badge + '</h2>'
        '<div class="card">'
        '<div class="sub" style="margin:2px 0 6px">' + body + '</div>' +
        links_block +
        '<div class="note" style="margin-top:10px">Plain-English summary compiled by pdufa.bio '
        'from public FDA, SEC and company sources. Informational only - not investment advice.</div>'
        '</div>' +
        MARKER_CLOSE
    )
    return card, curated, bool(crl_row), bool(s3)


def main():
    cats = load_catalysts()
    crl = load_crl()
    dirs = sorted(glob.glob(os.path.join(PDUFA_DIR, "*", "")))
    pages = {}
    for d in dirs:
        name = os.path.basename(d.rstrip("/"))
        path = os.path.join(d, "index.html")
        if not os.path.exists(path):
            continue
        h, drug, date, company, indic, tier = parse_page(path)
        base = name.split("-")[0]
        pages[name] = dict(path=path, name=name, base=base, drug=drug, date=date,
                           company=company, indic=indic, tier=tier, ta=ta_for(indic),
                           month=(date[:7] if re.match(r"\d{4}-\d{2}", date or "") else ""))

    def neighbours_for(p):
        out = []
        same_ta = sorted(
            (q for q in pages.values()
             if q["name"] != p["name"] and q["base"] != p["base"]
             and q["ta"] == p["ta"] and q["ta"] != "Other"),
            key=lambda q: q["date"])
        for q in same_ta:
            if q["base"] in {o["ticker"].split("-")[0] for o in out}:
                continue
            out.append({"ticker": q["name"], "date": q["date"],
                        "why": "Same area: " + q["ta"] + " . " + q["drug"][:38]})
            if len(out) >= 2:
                break
        if p["month"]:
            same_mo = sorted(
                (q for q in pages.values()
                 if q["name"] != p["name"] and q["base"] != p["base"]
                 and q["month"] == p["month"]),
                key=lambda q: q["date"])
            for q in same_mo:
                bases = {o["ticker"].split("-")[0] for o in out} | {p["base"]}
                if q["base"] in bases:
                    continue
                out.append({"ticker": q["name"], "date": q["date"],
                            "why": "Same month decision . " + q["drug"][:38]})
                if len(out) >= 3:
                    break
        return out[:3]

    stats = dict(total=0, injected=0, skipped_existing=0, with_crl=0,
                 with_cash=0, curated_ind=0, minimal=0)
    crl_pages = []
    skipped = []

    for name, p in pages.items():
        stats["total"] += 1
        h = open(p["path"], encoding="utf-8").read()
        if MARKER_OPEN in h:
            stats["skipped_existing"] += 1
            skipped.append((name, "already has story-v1 block"))
            continue
        rows = cats.get(p["base"], [])
        cat_row = pick_catalyst_row(rows, p["date"], p["drug"])
        crl_row = pick_crl(crl.get(p["base"], []), p["drug"])
        nbrs = neighbours_for(p)
        card, curated, has_crl, has_cash = build_story(
            name, p["base"], p["drug"], p["date"], p["company"], p["indic"],
            p["tier"], cat_row, crl_row, nbrs)
        anchor_re = re.compile(
            r'(</h1>\s*<div class="sub">FDA decision \(PDUFA\) target.*?</div>)', re.S)
        m = anchor_re.search(h)
        if not m:
            m2 = re.search(r"</h1>", h)
            if not m2:
                skipped.append((name, "no <h1> anchor - left untouched"))
                continue
            new_h = h[:m2.end()] + card + h[m2.end():]
        else:
            new_h = h[:m.end()] + card + h[m.end():]
        if "</html>" not in new_h or len(new_h) <= len(h):
            skipped.append((name, "post-build sanity failed - left untouched"))
            continue
        with open(p["path"], "w", encoding="utf-8") as f:
            f.write(new_h)
        stats["injected"] += 1
        if has_crl:
            stats["with_crl"] += 1
            crl_pages.append(name)
        if has_cash:
            stats["with_cash"] += 1
        if curated:
            stats["curated_ind"] += 1
        if not has_crl and not has_cash and not curated:
            stats["minimal"] += 1

    print("=== build_pdufa_story_blocks.py summary ===")
    for k, v in stats.items():
        print("  %s: %s" % (k, v))
    print("  CRL pages: %s" % sorted(crl_pages))
    if skipped:
        print("  Skipped/notes:")
        for n, why in skipped:
            print("    %s: %s" % (n, why))


if __name__ == "__main__":
    main()
