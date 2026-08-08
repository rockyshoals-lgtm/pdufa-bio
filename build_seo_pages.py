# -*- coding: utf-8 -*-
"""
build_seo_pages.py  —  competitive-battle-plan SEO surfaces for pdufa.bio.

Generates (server-rendered, crawlable, on-brand, facts-only):
  /calendar/2026/<month>/        PDUFA month-archive pages   (contest CatalystAlert's month SERP)
  /readouts/2026/<month>/        readout month-archive pages
  /condition/<slug>/             per-therapeutic-area pages  (own the "obesity drug FDA 2026" long tail)
  /why-no-approval-probability/  flagship brand page         (turn the no-fake-% guardrail into the wedge)
Each month page has prev/next nav, a count strip, an About blurb, and FAQPage JSON-LD.

Usage:  python build_seo_pages.py [catalysts_public.csv] [out_dir]
"""
import sys, os, csv, html, re, datetime as dt

SRC = sys.argv[1] if len(sys.argv) > 1 else "catalysts_public.csv"
OUT = sys.argv[2] if len(sys.argv) > 2 else "seo_pages"
TODAY = dt.date.today(); TODAY_ISO = TODAY.isoformat()
MON = ["", "January","February","March","April","May","June","July","August","September","October","November","December"]
def esc(s): return html.escape(str(s or "").strip())
def slugify(s):
    s = re.sub(r"[^a-z0-9]+", "-", str(s or "").lower()).strip("-")
    return s[:60] or "x"

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
    items = ",".join('{"@type":"Question","name":%s,"acceptedAnswer":{"@type":"Answer","text":%s}}' %
                     (_js(q), _js(a)) for q, a in qa)
    return '<script type="application/ld+json">{"@context":"https://schema.org","@type":"FAQPage","mainEntity":[' + items + ']}</script>'
def _js(s):
    import json as _json; return _json.dumps(str(s))
def breadcrumb_jsonld(items):
    li = ",".join('{"@type":"ListItem","position":%d,"name":%s%s}' %
                  (i + 1, _js(n), (',"item":%s' % _js(u)) if u else "") for i, (n, u) in enumerate(items))
    return '<script type="application/ld+json">{"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[' + li + ']}</script>'
RO_CSS = (".facts{background:#0c1d38;border:1px solid #1a3358;border-radius:12px;padding:6px 16px;margin:14px 0}"
 ".facts .kv{display:flex;justify-content:space-between;gap:12px;font-size:14px;padding:9px 0;border-bottom:1px solid #112b48}"
 ".facts .kv:last-child{border:0}.facts .kv span{color:#a7bcd9}.facts .kv b{color:#f2f6fc;text-align:right}")
def readout_page(e):
    tk = esc(e["tk"]); drug = esc(e["drug"]); ind = esc(e["ind"]) or "n/a"
    rid = e["rid"]; ym = e["ym"]; y = ym[:4]; m = int(ym[5:7]); mname = MON[m]; mslug = mname.lower()
    canonical = f"https://www.pdufa.bio/readout/{rid}"
    cond = COND.get(e["ta"]); cond_link = ("/condition/" + cond[1]) if cond else None
    title = f"{e['tk']} trial readout: {e['drug']} | pdufa.bio"
    desc = (f"{e['tk']}'s clinical-trial readout for {e['drug']} ({e['ind']}) is estimated around "
            f"{e['date']}. Facts only, primary-source linked - no hyped odds.")[:154]
    facts = [("Estimated readout window", esc(e["date"])), ("Drug / candidate", drug),
             ("Indication", ind), ("Ticker", tk)]
    if cond_link: facts.append(("Therapeutic area", f'<a href="{cond_link}">{esc(cond[0])}</a>'))
    src = e["url"]
    if src and str(src).startswith("http"):
        facts.append(("Primary source", f'<a href="{esc(src)}" rel="nofollow noopener" target="_blank">ClinicalTrials.gov / filing &nearr;</a>'))
    facts_html = "".join(f'<div class="kv"><span>{k}</span><b>{v}</b></div>' for k, v in facts)
    chips = [f'<a href="/readouts/{y}/{mslug}">All {mname} {y} readouts</a>']
    if cond_link: chips.append(f'<a href="{cond_link}">More {esc(cond[0])} catalysts</a>')
    chips.append('<a href="/readouts">All readouts</a>')
    body = (f'<style>{RO_CSS}</style>'
            f'<div class="bc"><a href="/">Home</a> &rsaquo; <a href="/readouts">Readouts</a> &rsaquo; <a href="/readouts/{y}/{mslug}">{mname} {y}</a> &rsaquo; {tk}</div>'
            f'<h1>{tk} trial readout: <span class="g">{drug}</span></h1>'
            f'<div class="sub">Estimated readout window <b>{esc(e["date"])}</b> &middot; {ind}</div>'
            f'<div class="facts">{facts_html}</div>'
            f'<div class="prose"><p>This page tracks the expected clinical-trial readout for <b>{drug}</b>. '
            f'A <b>readout</b> is when a trial reports topline results; the date shown is an estimate from the study\'s '
            f'registered primary-completion window and <b>can shift</b>. We link the primary source rather than guess an outcome.</p></div>'
            f'<div class="chips">' + "".join(chips) + '</div>'
            f'<div class="callout">We don\'t publish a success or approval probability for this readout: '
            f'<a href="/why-no-approval-probability">here\'s why</a>, and what we show instead.</div>'
            f'<a class="row" href="/app" style="display:block;margin-top:14px"><div class="t">Track this live &rarr;</div>'
            f'<div class="d">Price, run-up and options context in the pdufa.bio app (private beta)</div></a>')
    qa = [(f"When is {e['tk']}'s readout for {e['drug']}?",
           f"The clinical-trial readout for {e['drug']} is estimated around {e['date']}. Readout dates come from the trial's registered primary-completion window and shift - verify against the primary source."),
          ("What is a clinical-trial readout?",
           "A readout is when a trial reports its topline results. The date is an estimate based on the registered primary-completion date, not a fixed event."),
          ("Does pdufa.bio predict whether this readout will be positive?",
           "No. We do not publish per-drug success or approval probabilities. We show verified facts, the primary-source link, and historical base rates so you can judge for yourself.")]
    jsonld = breadcrumb_jsonld([("Home", "https://www.pdufa.bio/"), ("Readouts", "https://www.pdufa.bio/readouts"),
                                (f"{mname} {y}", f"https://www.pdufa.bio/readouts/{y}/{mslug}"), (e["tk"], None)]) + faq_jsonld(qa)
    return shell(title, desc, canonical, body, jsonld)

SITE_DIR = "pdufa_site_src"
def onsite_url(r):
    if r.get("cat") == "readout" and r.get("rid"):
        return "/readout/" + r["rid"]
    tk = str(r.get("tk","")).upper().strip()
    if tk and os.path.exists(os.path.join(SITE_DIR, "pdufa", tk, "index.html")): return "/pdufa/" + tk
    return r.get("url") or "#"
def rowhtml(r):
    ind = ("n/a" + esc(r["ind"])) if r["ind"] else ""
    _u = onsite_url(r); _rel = "" if _u.startswith("/") else " rel=\"nofollow\""
    return (f'<a class="row" href="{esc(_u)}"{_rel}><div class="t">{esc(r["tk"])} &middot; {esc(r["date"])}</div>'
            f'<div class="d">{esc(r["drug"])}{ind}</div></a>')

# ------------------------------------------------------------------ TA / condition buckets
COND = {  # bucket key -> (label, slug, blurb noun)
 "oncology": ("Cancer & Oncology", "cancer", "cancer & oncology"),
 "metabolic": ("Obesity & Metabolic", "obesity-metabolic", "obesity & metabolic"),
 "cns": ("CNS & Neurology", "cns-neurology", "CNS & neurology"),
 "immunology": ("Immunology & Inflammation", "immunology", "immunology & inflammation"),
 "cardiovascular": ("Cardiovascular", "cardiovascular", "cardiovascular"),
 "rare": ("Rare Disease", "rare-disease", "rare disease"),
 "infectious": ("Infectious Disease & Vaccines", "infectious-disease", "infectious disease & vaccines"),
 "hematology": ("Hematology", "hematology", "hematology"),
 "ophthalmology": ("Ophthalmology & Eye", "ophthalmology", "ophthalmology & eye"),
}
def classify_ta(ind, drug=""):
    s = ((ind or "") + " " + (drug or "")).lower()
    def has(*w): return any(x in s for x in w)
    if has("cancer","tumor","tumour","carcinoma","myeloma","lymphoma","leukemia","leukaemia","melanoma","sarcoma","glioma","oncolog","nsclc","sclc","neoplasm","malignan","metasta"): return "oncology"
    if has("ophthalm","macular","retina","uveitis","glaucoma","intravitreal","geographic atrophy","dry eye","keratitis","conjunctiv"): return "ophthalmology"
    if has("obesity","weight","overweight","nash","mash","nafld","dyslipid","hypercholester","metabolic","type 2 diab","type-2 diab","t2dm") or (has("diabet") and not has("retinop","macular","ophthalm","nephropathy","neuropathy","kidney","foot ulcer")): return "metabolic"
    if has("depress","anxiety","parkinson","alzheimer","schizophren","epilep","migraine","cns","psychiat","bipolar"," als","sclerosis","neuro","cognit","seizure","huntington","pain"): return "cns"
    if has("dermatitis","psoriasis","arthritis","asthma","lupus","colitis","crohn","eczema","immune","ulcerative","atopic","rheumat","ibd"): return "immunology"
    if has("heart","cardiac","cardiovascular","hypertension","hfpef","hfref","thrombos","atrial","coronary","angina"): return "cardiovascular"
    if has("anemia","anaemia","hemophilia","haemophilia","sickle","thrombocytopenia","hematolog","myelofibrosis","itp"): return "hematology"
    if has("influenza","hepatitis","covid","hiv","infection","viral","bacterial","vaccine","pneumococc","rsv","sepsis","tuberculosis"): return "infectious"
    if has("duchenne","dystrophy","angioedema","cystic fibrosis","rare","orphan","amyloid","gaucher","fabry","pompe","hereditary","ataxia","spinal muscular"): return "rare"
    return "other"

# ------------------------------------------------------------------ load + normalize rows
raw = list(csv.DictReader(open(SRC, encoding="utf-8", errors="ignore")))
def col(*n):
    for x in n:
        if raw and x in raw[0]: return x
    return None
C = {k: col(k) for k in ("category","ticker","catalyst_date","date_precision","drug","indication","source_url","qa_flag")}
def g(r, k): return r.get(C[k], "") if C[k] else ""

def disp_date(d, prec, cat):
    if cat == "drug" and len(d) >= 10: return d[:10]
    if (prec == "month" or re.fullmatch(r"\d{4}-\d{2}-01", d)) and len(d) >= 7 and d[5:7].isdigit():
        return f"{MON[int(d[5:7])][:3]} {d[:4]} (est.)"
    return d[:10] if len(d) >= 10 else d

events = []
for r in raw:
    cat = str(g(r, "category")).lower()
    if cat not in ("drug", "readout"): continue
    if C["qa_flag"] and any(f in str(g(r, "qa_flag")) for f in ("stale_alias", "blank_drug")): continue
    d = str(g(r, "catalyst_date")).strip()
    if len(d) < 7 or not d[:4].isdigit(): continue
    ind = g(r, "indication")
    if cat == "readout" and re.match(r"^\s*healthy\b", str(ind), re.I): continue
    events.append({"cat": cat, "tk": g(r, "ticker"), "_d": d, "ym": d[:7],
                   "date": disp_date(d, str(g(r, "date_precision")).lower(), cat),
                   "drug": g(r, "drug") or "-", "ind": ind, "url": g(r, "source_url"),
                   "ta": classify_ta(ind, g(r, "drug"))})
os.makedirs(OUT, exist_ok=True)
def write(path, content):
    p = os.path.join(OUT, path); os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", encoding="utf-8").write(content); return p

# ---- readout detail-page ids (added): every upcoming readout gets a stable on-site /readout/<id> ----
readout_events = [e for e in events if e["cat"] == "readout" and e["ym"] >= TODAY_ISO[:7]]
_ro_used = set()
for e in readout_events:
    base = (slugify(e["tk"]) + "-" + slugify(e["drug"])).strip("-")[:70] or (slugify(e["tk"]) or "readout")
    rid = base; _k = 1
    while rid in _ro_used:
        _k += 1; rid = f"{base}-{_k}"
    _ro_used.add(rid); e["rid"] = rid

# ------------------------------------------------------------------ 1) month-archive pages
n_month = 0
for cat, base, noun, verb in [("drug", "calendar", "FDA PDUFA decisions", "PDUFA target dates"),
                               ("readout", "readouts", "clinical-trial readouts", "trial-readout estimates")]:
    ev = [e for e in events if e["cat"] == cat and e["ym"][5:7].isdigit() and e["ym"] >= TODAY_ISO[:7]]
    months = sorted({e["ym"] for e in ev})  # numeric YYYY-MM only (quarter/half estimates skip month pages)
    for i, ym in enumerate(months):
        y, m = ym[:4], int(ym[5:7]); mname = MON[m]; mslug = mname.lower()
        rows = sorted([e for e in ev if e["ym"] == ym], key=lambda x: x["_d"])
        prev = f'<a href="/{base}/{months[i-1][:4]}/{MON[int(months[i-1][5:7])].lower()}">&larr; {MON[int(months[i-1][5:7])]} {months[i-1][:4]}</a>' if i > 0 else "<span></span>"
        nxt = f'<a href="/{base}/{months[i+1][:4]}/{MON[int(months[i+1][5:7])].lower()}">{MON[int(months[i+1][5:7])]} {months[i+1][:4]} &rarr;</a>' if i < len(months)-1 else "<span></span>"
        title = f"{mname} {y} {noun} — FDA Calendar | pdufa.bio" if cat == "drug" else f"{mname} {y} Clinical Trial Readouts | pdufa.bio"
        canonical = f"https://www.pdufa.bio/{base}/{y}/{mslug}"
        desc = (f"Every {noun} scheduled for {mname} {y}: company, ticker, drug and indication, each linked to its primary "
                f"FDA/SEC/registry source. Facts only — no hyped approval odds.")
        body = (f'<div class="bc"><a href="/">Home</a> &rsaquo; <a href="/{base}">{base.title()}</a> &rsaquo; {mname} {y}</div>'
                f'<h1>{mname} {y} <span class="g">{noun}</span></h1>'
                f'<div class="sub">{verb} for {mname} {y}, each row linked to its primary source. '
                f'{"PDUFA target dates are FDA-set goal dates." if cat=="drug" else "Readout dates are estimated primary-completion windows from ClinicalTrials.gov and shift."}</div>'
                f'<div class="pn">{prev}{nxt}</div><span class="count">{len(rows)} {"PDUFA dates" if cat=="drug" else "readouts"}</span>'
                f'<div class="grid" style="margin-top:12px">' + "".join(rowhtml(r) for r in rows) + '</div>'
                f'<div class="callout">Looking for an approval probability for these? We deliberately don\'t publish one: '
                f'<a href="/why-no-approval-probability">here\'s why</a>, and what we show instead (verified history + base rates).</div>')
        qa = [(f"How many {noun} are scheduled for {mname} {y}?",
               f"pdufa.bio currently tracks {len(rows)} {noun} with dates in {mname} {y}, each linked to a primary source. The list updates as new filings appear and dates shift."),
              ("What is a PDUFA date?" if cat=="drug" else "What is a clinical-trial readout date?",
               "A PDUFA date is the FDA's goal date to decide on a drug application under the Prescription Drug User Fee Act." if cat=="drug"
               else "A readout date is the estimated time a trial reports topline results, based on its registered primary-completion date; these are estimates and shift."),
              ("Does pdufa.bio predict whether these will be approved?",
               "No. We do not publish per-drug approval probabilities. We provide the verified facts, primary-source links, and historical base rates so you can judge for yourself.")]
        write(f"{base}/{y}/{mslug}/index.html", shell(title, desc, canonical, body, faq_jsonld(qa)))
        n_month += 1

# ------------------------------------------------------------------ 2) condition pages
n_cond = 0
for key, (label, slug, noun) in COND.items():
    ev = sorted([e for e in events if e["ta"] == key and e["ym"] >= TODAY_ISO[:7]], key=lambda x: x["_d"])
    if len(ev) < 3: continue
    pd = [e for e in ev if e["cat"] == "drug"]; rd = [e for e in ev if e["cat"] == "readout"]
    kinds = "FDA Decisions & Readouts" if (pd and rd) else ("FDA Decisions" if pd else "Clinical-Trial Readouts")
    title = f"Upcoming {label} {kinds} (2026) | pdufa.bio"
    canonical = f"https://www.pdufa.bio/condition/{slug}"
    desc = f"Upcoming FDA PDUFA decisions and clinical-trial readouts in {noun}, by date with primary-source links. Facts only, no approval odds."
    body = [f'<div class="bc"><a href="/">Home</a> &rsaquo; Condition &rsaquo; {esc(label)}</div>'
            f'<h1>Upcoming <span class="g">{esc(label)}</span> FDA decisions &amp; readouts</h1>'
            f'<div class="sub">PDUFA target dates and trial readouts in {noun}, each linked to its primary source. '
            f'Updated from FDA/SEC/ClinicalTrials.gov; dates can shift.</div>'
            f'<div class="chips">' + "".join(f'<a href="/condition/{s}">{esc(l)}</a>' for k,(l,s,_) in COND.items() if k!=key) + '</div>']
    if pd: body.append(f'<h2>PDUFA decisions ({len(pd)})</h2><div class="grid">' + "".join(rowhtml(r) for r in pd) + '</div>')
    if rd: body.append(f'<h2>Trial readouts ({len(rd)})</h2><div class="grid">' + "".join(rowhtml(r) for r in rd) + '</div>')
    body.append(f'<div class="callout">We don\'t show an approval percentage for these {esc(label.lower())} catalysts: '
                f'<a href="/why-no-approval-probability">here\'s why</a>.</div>')
    cond_faq = [("What upcoming FDA catalysts are there in " + label + "?",
                 f"pdufa.bio tracks {len(ev)} upcoming {label} catalysts ({len(pd)} PDUFA decisions, {len(rd)} trial readouts), each with a date and a primary-source link."),
                ("Does pdufa.bio predict whether these will be approved?",
                 "No. We do not publish per-drug approval probabilities; we show verified facts, primary-source links, and historical base rates so you can judge for yourself.")]
    _items = ",".join('{"@type":"ListItem","position":%d,"name":%s}' % (i+1, _js((e["tk"] + " " + e["drug"]).strip())) for i, e in enumerate(ev[:50]))
    _itemld = '<script type="application/ld+json">{"@context":"https://schema.org","@type":"ItemList","itemListElement":[' + _items + ']}</script>'
    write(f"condition/{slug}/index.html", shell(title, desc, canonical, "".join(body), faq_jsonld(cond_faq) + _itemld))
    n_cond += 1

# ------------------------------------------------------------------ 2.5) readout detail pages (on-site; stop CT.gov leak)
n_readout = 0
for e in readout_events:
    write(f"readout/{e['rid']}/index.html", readout_page(e))
    n_readout += 1

# ------------------------------------------------------------------ 3) "Why no approval %" brand page
why_body = (
 '<div class="bc"><a href="/">Home</a> &rsaquo; Why we don\'t show an approval %</div>'
 '<h1>Why we will never show a <span class="g">fake approval probability</span></h1>'
 '<div class="prose">'
 '<p>Several catalyst sites now print an &ldquo;AI&rdquo; approval percentage on every drug, <b>82%</b>, <b>99%</b>, a tidy number that feels like insight. '
 'We refuse to. Not because we can\'t generate one, but because a single per-drug percentage is, for a binary regulatory event, <b>false precision that misleads</b>.</p>'
 '<div class="callout"><b>The failure mode that breaks the number:</b> a drug can have two clean, statistically significant Phase&nbsp;3 trials and <i>still</i> get a '
 'Complete Response Letter, for a manufacturing (CMC) problem, a third-party facility inspection, or a labeling dispute that has nothing to do with whether the drug works. '
 'A &ldquo;99% approval&rdquo; tile cannot see that. The history is full of strong-data drugs that were delayed or rejected on issues no efficacy model captures.</p>'
 '<p>So instead of inventing a probability, we show you the things that are <b>actually true and verifiable</b>:</p>'
 '<p>&bull; <b>The verified facts</b>, the FDA-set or company-guided date, the drug, the indication, each tagged by how we know it and linked to a primary FDA, SEC, or ClinicalTrials.gov source.<br>'
 '&bull; <b>Historical base rates</b>: how this <i>kind</i> of decision has resolved (by therapeutic area, by cap size, after a prior CRL), with the sample size shown, not a confident point estimate dressed up as one.<br>'
 '&bull; <b>The run-up path and options-implied move</b>; what the market is actually pricing into the date, not what we guess the FDA will do.<br>'
 '&bull; <b>Our own misses</b>, we label price-only data, flag unverified items, and post corrections. A black box can\'t do that.</p>'
 '<p>A fake 82% asks you to trust a model you can\'t inspect. Verified history and sourced facts ask you to <b>think for yourself</b>, and give you what you need to. '
 'That is the entire difference, and it is the one thing none of the &ldquo;AI %&rdquo; sites can copy without rebuilding their pipeline around the truth.</p>'
 '<div class="chips"><a href="/calendar">See the calendar</a><a href="/research">Read the data</a><a href="/methodology">How we source it</a><a href="/sources">Coverage &amp; sources</a></div>'
 '</div>')
why_faq = [("Does pdufa.bio predict FDA approval probability?",
            "No. We deliberately do not publish a per-drug approval percentage. A single number is false precision for a binary regulatory event that can fail on manufacturing or labeling grounds unrelated to efficacy. We provide verified facts, primary-source links, and historical base rates instead."),
           ("Why do other sites show an AI approval %?",
            "Some catalyst sites publish an AI-generated probability per drug. It is easy to display and feels precise, but it cannot account for CMC, facility-inspection, or labeling CRLs that reject strong-data drugs, so it can badly mislead."),
           ("What does pdufa.bio show instead of a probability?",
            "Verified FDA/SEC/registry facts with source links, historical base rates by therapeutic area and cap size (with sample sizes), the pre-event run-up path and options-implied move, and transparent labeling of our own data limitations.")]
write("why-no-approval-probability/index.html",
      shell("Why pdufa.bio won't show a fake FDA approval probability | pdufa.bio",
            "Why pdufa.bio refuses to publish a per-drug approval percentage: a single number is false precision for a binary event that can fail on CMC or labeling grounds. We show verified facts, primary sources, and historical base rates instead.",
            "https://www.pdufa.bio/why-no-approval-probability", why_body, faq_jsonld(why_faq)))

# ------------------------------------------------------------------ 4) coverage statemen