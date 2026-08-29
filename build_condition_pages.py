# -*- coding: utf-8 -*-
"""build_condition_pages.py -- /condition/{slug} rebuilt from the living dataset.

WHY THIS EXISTS (2026-08-29 audit, item 2)
/condition/cancer is Google's #2 page by impressions (373) and had never been examined.
Examining it found the whole /condition/* family frozen: built once by build_seo_pages.py
from catalysts_public_latest.csv (dated June 23), with neither the builder in CI nor the CSV
refreshed. Two months of drift produced, on a page titled "Upcoming":
  - past-dated events presented as upcoming (ARVN 06-05, ACHV 06-20, HOOK 08-17),
  - ACHV 06-20 labelled "Custirsen: Non-Small Cell Lung Cancer" -- custirsen is a
    discontinued OncoGenex drug from before the 2017 merger; the real ACHV event was the
    cytisinicline PDUFA (smoking cessation, not oncology, and it drew a CRL on 06-22),
  - NUVL 09-18 labelled "Neladalkib" -- 09-18 was zidesamtinib's goal date, approved 07-22;
    neladalkib's own date is 11-27.
Same silent-degradation shape as the ticker hubs found on 08-26, third instance of the
build-once-never-rebuild class.

build_seo_pages.py is NOT simply rerun because it also writes the /calendar and /readouts
month pages, which the daily chain now owns (ensure_calendar_rows, mark_calendar_decided);
rerunning it would clobber their decided marks. This builder regenerates ONLY
condition/{slug}/index.html, from api/v1/dataset.mjs -- the same living source the ticker
hub fix switched to -- with the page template kept byte-compatible with build_seo_pages.py
so downstream marker passes (nav, breadcrumbs, legal footer, freshness) re-apply cleanly.

Selection rules, each one a lesson already paid for:
  - a PDUFA row with st=Decided never appears, whatever its goal date (NUVL 09-18);
  - a Readout row with st=Reported never appears (AMLX);
  - nothing past-dated appears on a page titled "Upcoming";
  - names and indications come from the dataset row itself, never a side lookup by ticker
    (the custirsen failure was a stale ticker->drug mapping).

Guard: tests/test_condition_pages_current.py. CI: runs right after the ticker hub rebuild.
"""
import datetime as dt
import html
import io
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
TODAY = dt.date.today().isoformat()
MON = ["", "January", "February", "March", "April", "May", "June", "July",
       "August", "September", "October", "November", "December"]

COND = {
    "oncology": ("Cancer & Oncology", "cancer", "cancer & oncology"),
    "metabolic": ("Obesity & Metabolic", "obesity-metabolic", "obesity & metabolic"),
    "cns": ("CNS & Neurology", "cns-neurology", "CNS & neurology"),
    "immunology": ("Immunology & Inflammation", "immunology", "immunology & inflammation"),
    "cardiovascular": ("Cardiovascular", "cardiovascular", "cardiovascular"),
    "rare": ("Rare Disease", "rare-disease", "rare disease"),
    "infectious": ("Infectious Disease & Vaccines", "infectious-disease",
                   "infectious disease & vaccines"),
    "hematology": ("Hematology", "hematology", "hematology"),
    "ophthalmology": ("Ophthalmology & Eye", "ophthalmology", "ophthalmology & eye"),
}


def esc(s):
    return html.escape(str(s or "").strip())


def _js(s):
    return json.dumps(str(s))


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", str(s or "").lower()).strip("-")[:60] or "x"


# The dataset rows carry their own therapeutic-area label, which is authoritative where
# present -- readouts usually have a null indication, so the text classifier below dumps
# them all in "other" (the first run produced a cancer page with 1 readout when the dataset
# held 43 live oncology readouts). Dataset label first, text classification as fallback.
TA_MAP = {"oncology": "oncology", "cns": "cns", "cns/neurology": "cns",
          "cardiovascular": "cardiovascular", "hematology": "hematology",
          "immunology": "immunology", "infectious": "infectious",
          "metabolic": "metabolic", "endocrinology / metabolic": "metabolic",
          "ophthalmology": "ophthalmology", "rare disease": "rare"}


def classify_ta(ind, drug=""):
    """Copied from build_seo_pages.py so a row lands in the same bucket it always did."""
    s = ((ind or "") + " " + (drug or "")).lower()

    def has(*w):
        return any(x in s for x in w)

    if has("cancer", "tumor", "tumour", "carcinoma", "myeloma", "lymphoma", "leukemia",
           "leukaemia", "melanoma", "sarcoma", "glioma", "oncolog", "nsclc", "sclc",
           "neoplasm", "malignan", "metasta"):
        return "oncology"
    if has("ophthalm", "macular", "retina", "uveitis", "glaucoma", "intravitreal",
           "geographic atrophy", "dry eye", "keratitis", "conjunctiv"):
        return "ophthalmology"
    if has("obesity", "weight", "overweight", "nash", "mash", "nafld", "dyslipid",
           "hypercholester", "metabolic", "type 2 diab", "type-2 diab", "t2dm") or (
            has("diabet") and not has("retinop", "macular", "ophthalm", "nephropathy",
                                      "neuropathy", "kidney", "foot ulcer")):
        return "metabolic"
    if has("depress", "anxiety", "parkinson", "alzheimer", "schizophren", "epilep",
           "migraine", "cns", "psychiat", "bipolar", " als", "sclerosis", "neuro",
           "cognit", "seizure", "huntington", "pain"):
        return "cns"
    if has("dermatitis", "psoriasis", "arthritis", "asthma", "lupus", "colitis", "crohn",
           "eczema", "immune", "ulcerative", "atopic", "rheumat", "ibd"):
        return "immunology"
    if has("heart", "cardiac", "cardiovascular", "hypertension", "hfpef", "hfref",
           "thrombos", "atrial", "coronary", "angina"):
        return "cardiovascular"
    if has("anemia", "anaemia", "hemophilia", "haemophilia", "sickle",
           "thrombocytopenia", "hematolog", "myelofibrosis", "itp"):
        return "hematology"
    if has("influenza", "hepatitis", "covid", "hiv", "infection", "viral", "bacterial",
           "vaccine", "pneumococc", "rsv", "sepsis", "tuberculosis"):
        return "infectious"
    if has("duchenne", "dystrophy", "angioedema", "cystic fibrosis", "rare", "orphan",
           "amyloid", "gaucher", "fabry", "pompe", "hereditary", "ataxia",
           "spinal muscular"):
        return "rare"
    return "other"


# ---- page shell, byte-compatible with build_seo_pages.py --------------------------------
CSS = ("*{box-sizing:border-box}body{margin:0;background:#02060d;color:#f2f6fc;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;-webkit-font-smoothing:antialiased;line-height:1.55}"
       "a{color:#6fb6ff;text-decoration:none}a:hover{text-decoration:underline}.wrap{max-width:820px;margin:0 auto;padding:22px 18px 60px}"
       ".top{display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #1a3358;padding-bottom:12px}.brand{font-size:19px;font-weight:800}.brand b{color:#e3ba5e}"
       ".nav a{color:#a7bcd9;font-size:13px;margin-left:14px}.bc{font-size:12px;color:#94a9c9;margin:16px 0 4px}.bc a{color:#94a9c9}"
       "h1{font-size:27px;line-height:1.18;letter-spacing:-.4px;margin:6px 0 6px}h1 .g{color:#e3ba5e}h2{font-size:19px;margin:26px 0 8px}"
       ".sub{color:#a7bcd9;font-size:15px;margin:6px 0 14px}.pn{display:flex;justify-content:space-between;gap:10px;margin:8px 0 16px;font-size:13px}"
       ".count{display:inline-block;background:#13315c;color:#e3ba5e;border:1px solid #2a496f;border-radius:20px;padding:4px 12px;font-weight:700;font-size:13px}"
       ".grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}@media(max-width:560px){.grid{grid-template-columns:1fr}}"
       ".row{display:block;background:#0c1d38;border:1px solid #1a3358;border-radius:10px;padding:11px 13px;color:#f2f6fc}.row:hover{border-color:#2a496f;text-decoration:none}"
       ".row .t{font-weight:800}.row .d{font-size:12.5px;color:#a7bcd9}.mhead{font-size:15px;color:#e3ba5e;font-weight:800;margin:20px 0 8px}"
       ".prose p{color:#dce6f5;font-size:15.5px;margin:12px 0}.prose b{color:#fff}.chips{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0}"
       ".chips a{font-size:13px;color:#a7bcd9;border:1px solid #2a496f;border-radius:20px;padding:5px 12px}.callout{background:#0c1d38;border:1px solid #2a496f;border-left:3px solid #e3ba5e;border-radius:8px;padding:12px 14px;margin:14px 0}"
       "footer{border-top:1px solid #1a3358;margin-top:34px;padding-top:16px;font-size:11.5px;color:#94a9c9;line-height:1.6}footer b{color:#a7bcd9}")

NAV = ('<a href="/calendar">Calendar</a><a href="/readouts">Readouts</a><a href="/devices">Devices</a>'
       '<a href="/decisions">Decisions</a><a href="/fda-approval-rate">Approvals/yr</a>'
       '<a href="/clinical-trial-success-rates">Trial odds</a><a href="/learn">Learn</a><a href="/research">Research</a><a href="/methodology">Methodology</a><a href="/coverage">Coverage</a><a href="/pricing">Pricing</a>')

FOOTER = ('<footer><b>Not affiliated with or endorsed by the FDA.</b> pdufa.bio is owned and operated by Odin Catalyst LLC, an independent service; "FDA", "PDUFA", and all'
          'company, drug, and ticker names are used descriptively and remain the property of their owners. <b>Informational and '
          'educational only. Not investment advice.</b> No individual-drug approval probabilities; verify every date and '
          'outcome against primary FDA / SEC / company filings. &copy; 2026 Odin Catalyst LLC &middot; pdufa.bio</footer>')


def shell(title, desc, canonical, body, jsonld=""):
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
            f'<title>{esc(title)}</title><meta name="description" content="{esc(desc)}">'
            f'<link rel="canonical" href="{canonical}"><meta name="robots" content="index,follow,max-image-preview:large">'
            f'<meta name="theme-color" content="#02060d"><link rel="icon" type="image/png" href="/icon-192.png">'
            f'<meta property="og:type" content="website"><meta property="og:site_name" content="pdufa.bio">'
            f'<meta property="og:url" content="{canonical}"><meta property="og:title" content="{esc(title)}">'
            f'<meta property="og:description" content="{esc(desc)}"><meta property="og:image" content="https://www.pdufa.bio/og.png">'
            f'<meta name="twitter:card" content="summary_large_image">{jsonld}'
            f'<style>{CSS}</style></head><body><div class="wrap">'
            f'<div class="top"><a class="brand" href="/">pdufa<b>.bio</b></a><div class="nav">{NAV}</div></div>'
            f'{body}{FOOTER}</div></body></html>')


def faq_jsonld(qa):
    items = ",".join('{"@type":"Question","name":%s,"acceptedAnswer":{"@type":"Answer","text":%s}}'
                     % (_js(q), _js(a)) for q, a in qa)
    return ('<script type="application/ld+json">{"@context":"https://schema.org",'
            '"@type":"FAQPage","mainEntity":[' + items + ']}</script>')


# ---- events from the living dataset -----------------------------------------------------
def load_events():
    p = os.path.join(SITE, "api", "v1", "dataset.mjs")
    src = io.open(p, encoding="utf-8", errors="replace").read().replace("\x00", "")
    rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    out = []
    for r in rows:
        typ, st = r.get("type"), str(r.get("st") or "")
        if typ == "PDUFA":
            if st.lower() == "decided":       # the FDA already acted; never "upcoming"
                continue
            cat = "drug"
        elif typ == "Readout":
            if st.lower() == "reported":      # the result is out; never "upcoming"
                continue
            cat = "readout"
        else:
            continue
        d = str(r.get("d") or "")
        if len(d) < 7 or not d[:4].isdigit():
            continue
        prec = str(r.get("dp") or "day")
        # A month-precision event stays listed through its whole month; a day-precision
        # event leaves the page the day after its date.
        if (d[:7] < TODAY[:7]) if prec == "month" else (d[:10] < TODAY):
            continue
        ind = (r.get("_d") or {}).get("indication") or ""
        drug = str(r.get("name") or "").strip() or "-"
        date = (f"{MON[int(d[5:7])][:3]} {d[:4]} (est.)"
                if prec == "month" and d[5:7].isdigit() else d[:10])
        ta = (TA_MAP.get(str(r.get("ta") or "").strip().lower())
              or classify_ta(str(ind), drug))
        out.append(dict(cat=cat, tk=str(r.get("t") or "").upper(), _d=d, date=date,
                        drug=drug, ind=str(ind), url=str(r.get("url") or ""), ta=ta))
    return out


def rowhtml(r):
    ind = (": " + esc(r["ind"])) if r["ind"] else ""
    u = r["url"]
    if r["cat"] == "readout":
        rid = (slugify(r["tk"]) + "-" + slugify(r["drug"])).strip("-")[:70]
        if os.path.exists(os.path.join(SITE, "readout", rid, "index.html")):
            u = "/readout/" + rid
    elif r["tk"] and os.path.exists(os.path.join(SITE, "pdufa", r["tk"], "index.html")):
        u = "/pdufa/" + r["tk"]
    if not u:
        u = "#"
    rel = "" if u.startswith("/") else ' rel="nofollow"'
    return (f'<a class="row" href="{esc(u)}"{rel}><div class="t">{esc(r["tk"])} &middot; '
            f'{esc(r["date"])}</div><div class="d">{esc(r["drug"])}{ind}</div></a>')


def main():
    events = load_events()
    if len(events) < 20:
        print(f"FAIL: only {len(events)} live events parsed from dataset.mjs -- refusing "
              f"to overwrite 9 condition pages from what is probably a broken read")
        return 1
    built = 0
    for key, (label, slug, noun) in COND.items():
        ev = sorted([e for e in events if e["ta"] == key], key=lambda x: x["_d"])
        out = os.path.join(SITE, "condition", slug, "index.html")
        # Below the floor, a NEW page is not created -- but an EXISTING page is still
        # rebuilt with whatever is real. Leaving it alone means leaving the stale June
        # build claiming past events are upcoming, which is strictly worse than a short
        # honest page. (First run of this script made exactly that mistake: 5 of 9 pages
        # "left as is", every one of them wrong.)
        if len(ev) < 3 and not os.path.exists(out):
            print(f"  skip /condition/{slug}: only {len(ev)} live events and no existing "
                  f"page; not creating a thin one")
            continue
        pd = [e for e in ev if e["cat"] == "drug"]
        rd = [e for e in ev if e["cat"] == "readout"]
        kinds = ("FDA Decisions & Readouts" if (pd and rd)
                 else ("FDA Decisions" if pd else "Clinical-Trial Readouts"))
        title = f"Upcoming {label} {kinds} (2026) | pdufa.bio"
        canonical = f"https://www.pdufa.bio/condition/{slug}"
        desc = (f"Upcoming FDA PDUFA decisions and clinical-trial readouts in {noun}, "
                f"by date with primary-source links. Facts only, no approval odds.")
        body = [f'<div class="bc"><a href="/">Home</a> &rsaquo; Condition &rsaquo; {esc(label)}</div>'
                f'<h1>Upcoming <span class="g">{esc(label)}</span> FDA decisions &amp; readouts</h1>'
                f'<div class="sub">PDUFA target dates and trial readouts in {noun}, each linked to its primary source. '
                f'Updated from FDA/SEC/ClinicalTrials.gov; dates can shift.</div>'
                f'<div class="chips">' + "".join(
                    f'<a href="/condition/{s}">{esc(l)}</a>'
                    for k, (l, s, _) in COND.items() if k != key) + '</div>']
        if pd:
            body.append(f'<h2>PDUFA decisions ({len(pd)})</h2><div class="grid">'
                        + "".join(rowhtml(r) for r in pd) + '</div>')
        if rd:
            body.append(f'<h2>Trial readouts ({len(rd)})</h2><div class="grid">'
                        + "".join(rowhtml(r) for r in rd) + '</div>')
        body.append(f'<div class="callout">We don\'t show an approval percentage for these '
                    f'{esc(label.lower())} catalysts: '
                    f'<a href="/why-no-approval-probability">here\'s why</a>.</div>')
        qa = [("What upcoming FDA catalysts are there in " + label + "?",
               f"pdufa.bio tracks {len(ev)} upcoming {label} catalysts ({len(pd)} PDUFA "
               f"decisions, {len(rd)} trial readouts), each with a date and a "
               f"primary-source link."),
              ("Does pdufa.bio predict whether these will be approved?",
               "No. We do not publish per-drug approval probabilities; we show verified "
               "facts, primary-source links, and historical base rates so you can judge "
               "for yourself.")]
        if not ev:
            body = body[:1] + [
                f'<h1>Upcoming <span class="g">{esc(label)}</span> FDA decisions &amp; readouts</h1>',
                f'<div class="sub">No dated {noun} catalyst is on our calendar right now. '
                f'That means no scheduled decision or readout date has been published in a '
                f'source we can point to, not that none exists.</div>', body[3]]
        items = ",".join('{"@type":"ListItem","position":%d,"name":%s}'
                         % (i + 1, _js((e["tk"] + " " + e["drug"]).strip()))
                         for i, e in enumerate(ev[:50]))
        itemld = (('<script type="application/ld+json">{"@context":"https://schema.org",'
                   '"@type":"ItemList","itemListElement":[' + items + ']}</script>')
                  if ev else "")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        io.open(out, "w", encoding="utf-8").write(
            shell(title, desc, canonical, "".join(body), faq_jsonld(qa) + itemld))
        built += 1
        print(f"  /condition/{slug}: {len(pd)} PDUFA + {len(rd)} readouts")
    print(f"condition pages rebuilt from dataset.mjs: {built}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
