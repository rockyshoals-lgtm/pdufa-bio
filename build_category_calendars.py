# -*- coding: utf-8 -*-
"""Build /readouts and /devices calendar pages for pdufa.bio from the crawler's
categorized output (catalysts_public.csv has a `category` field: drug/readout/device/earnings).
Matches the LIVE pdufa.bio/calendar design (same CSS/nav/footer), facts-only, source-linked.
Usage:  python build_category_calendars.py [catalysts_public.csv] [out_dir]"""
import sys, os, csv, html, re, datetime as dt

SRC = sys.argv[1] if len(sys.argv) > 1 else "catalysts_public.csv"
OUT = sys.argv[2] if len(sys.argv) > 2 else "site_category_pages"
os.makedirs(OUT, exist_ok=True)
TODAY = dt.date.today(); TODAY_ISO = TODAY.isoformat()
MON = ["", "January","February","March","April","May","June","July","August","September","October","November","December"]
DASH = "—"  # em-dash (kept out of source literals to avoid tool truncation)

CSS = ("*{box-sizing:border-box}body{margin:0;background:#02060d;color:#f2f6fc;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;-webkit-font-smoothing:antialiased;line-height:1.5}"
"a{color:#6fb6ff;text-decoration:none}a:hover{text-decoration:underline}.wrap{max-width:820px;margin:0 auto;padding:22px 18px 60px}"
".top{display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #1a3358;padding-bottom:12px}.brand{font-size:19px;font-weight:800}.brand b{color:#e3ba5e}"
".nav a{color:#a7bcd9;font-size:13px;margin-left:14px}.nav a.on{color:#e3ba5e}.bc{font-size:12px;color:#94a9c9;margin:16px 0 4px}.bc a{color:#94a9c9}"
"h1{font-size:27px;line-height:1.18;letter-spacing:-.4px;margin:6px 0 4px}h1 .g{color:#e3ba5e}"
".sub{color:#a7bcd9;font-size:15px;margin:6px 0 16px}.toggle{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0 4px}"
".toggle a{font-size:13px;font-weight:700;color:#a7bcd9;border:1px solid #2a496f;border-radius:20px;padding:5px 13px}.toggle a.on{background:#13315c;color:#e3ba5e;border-color:#e3ba5e}"
".note{font-size:12px;color:#94a9c9}.grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}@media(max-width:560px){.grid{grid-template-columns:1fr}}"
".row{display:block;background:#0c1d38;border:1px solid #1a3358;border-radius:10px;padding:11px 13px;color:#f2f6fc}.row:hover{border-color:#2a496f;text-decoration:none}"
".row .t{font-weight:800}.row .d{font-size:12.5px;color:#a7bcd9}.mhead{font-size:15px;color:#e3ba5e;font-weight:800;margin:20px 0 8px}"
"footer{border-top:1px solid #1a3358;margin-top:34px;padding-top:16px;font-size:11.5px;color:#94a9c9;line-height:1.6}footer b{color:#a7bcd9}")

NAV = ('<a href="/calendar">Calendar</a><a href="/readouts"{readouts}>Readouts</a>'
       '<a href="/devices"{devices}>Devices</a><a href="/decisions">Decisions</a>'
       '<a href="/fda-approval-rate">Approvals/yr</a><a href="/clinical-trial-success-rates">Trial odds</a><a href="/learn">Learn</a>'
       '<a href="/research">Research</a><a href="/methodology">Methodology</a>')
TOGGLE = ('<div class="toggle"><a href="/calendar">PDUFA dates</a>'
          '<a href="/readouts"{readouts}>Trial readouts</a><a href="/devices"{devices}>Devices</a></div>')
FOOTER = ('<footer><b>Not affiliated with or endorsed by the FDA.</b> pdufa.bio is owned and operated by Odin Catalyst LLC, an independent service;'
          '"FDA", "PDUFA", and all company, drug, and ticker names are used descriptively and remain the property '
          'of their owners. <b>Informational and educational only ' + DASH + ' not investment advice.</b> Data and historical '
          'statistics only; no trade recommendations and no individual-drug approval probabilities. Verify every date '
          'and outcome against primary FDA / SEC / company filings. &copy; 2026 Odin Catalyst LLC &middot; pdufa.bio</footer>')

def esc(s): return html.escape(str(s or "").strip())
def _plain(s): return re.sub(r"<[^>]+>","",str(s))

def date_group(d):
    d = str(d).strip(); y = d[:4]
    if not y.isdigit(): return None
    rest = d[5:7] if len(d) >= 7 else ""
    if re.fullmatch(r"\d{2}", rest) and 1 <= int(rest) <= 12:
        return (f"{y}-{rest}-1", f"{MON[int(rest)]} {y}", d[:10] if len(d) >= 10 else f"{y}-{rest}")
    if re.fullmatch(r"[Qq][1-4]", rest):
        return (f"{y}-{rest.upper()}", f"{rest.upper()} {y} (est.)", f"{rest.upper()} {y}")
    if re.fullmatch(r"[Hh][12]", rest):
        return (f"{y}-{rest.upper()}", f"{rest.upper()} {y} (est.)", f"{rest.upper()} {y}")
    return (f"{y}-zz", f"{y} (est.)", f"{y}")

def keep(d):
    y = d[:4]
    if not y.isdigit(): return False
    yr = int(y)
    if yr < TODAY.year: return False
    if yr > TODAY.year: return True
    if len(d) >= 10: return d[:10] >= TODAY_ISO
    rest = (d[5:7] if len(d) >= 7 else "").upper()
    endm = {"Q1":3,"Q2":6,"Q3":9,"Q4":12,"H1":6,"H2":12}.get(rest)
    if endm: return endm >= TODAY.month
    return True

def page(active, title, desc, canonical, h1, sub, groups, note, chart=""):
    nav = NAV.format(readouts=' class="on"' if active == "readouts" else "", devices=' class="on"' if active == "devices" else "")
    tog = TOGGLE.format(readouts=' class="on"' if active == "readouts" else "", devices=' class="on"' if active == "devices" else "")
    import json as _json
    _li = []; _pos = 0
    for _sk in sorted(groups):
        for _r in groups[_sk]["rows"]:
            _pos += 1
            _nm = (str(_r.get("tk", "")).strip() + " " + str(_r.get("drug", "")).strip()).strip()
            _li.append('{"@type":"ListItem","position":%d,"name":%s}' % (_pos, _json.dumps(_nm)))
    _itemld = ('<script type="application/ld+json">{"@context":"https://schema.org","@type":"ItemList","name":%s,"numberOfItems":%d,"itemListElement":[%s]}</script>' % (_json.dumps(_plain(h1)), _pos, ",".join(_li))) if _li else ""
    p = [f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
         f'<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
         f'<title>{esc(title)}</title><meta name="description" content="{esc(desc)}">'
         f'<link rel="canonical" href="{canonical}"><meta name="robots" content="index,follow,max-image-preview:large">'
         f'<meta name="theme-color" content="#02060d"><link rel="icon" type="image/png" href="/icon-192.png">'
         f'<meta property="og:type" content="article"><meta property="og:site_name" content="pdufa.bio">'
         f'<meta property="og:url" content="{canonical}"><meta property="og:title" content="{esc(title)}">'
         f'<meta property="og:description" content="{esc(desc)}"><meta property="og:image" content="https://www.pdufa.bio/og.png">'
         f'<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{esc(title)}">{_itemld}'
         f'<style>{CSS}</style></head><body><div class="wrap">'
         f'<div class="top"><a class="brand" href="/">pdufa<b>.bio</b></a><div class="nav">{nav}</div></div>'
         f'<div class="bc"><a href="/">Home</a> &rsaquo; {esc(_plain(h1))}</div>'
         f'<h1>{h1}</h1><div class="sub">{sub}</div>{tog}{chart}']
    for sk in sorted(groups):
        g = groups[sk]
        p.append(f'<div class="mhead">{esc(g["label"])}</div><div class="grid">')
        for r in g["rows"]:
            sep = (" " + DASH + " " + esc(r["ind"])) if r["ind"] else ""
            p.append(f'<a class="row" href="{esc(r["url"] or "#")}" rel="nofollow"><div class="t">{esc(r["tk"])} &middot; {esc(r["date"])}</div>'
                     f'<div class="d">{esc(r["drug"])}{sep}</div></a>')
        p.append('</div>')
    p.append(f'<div class="note" style="margin-top:18px">{note}</div>{FOOTER}</div></body></html>')
    return "".join(p)

def month_chart(groups):
    """Inline SVG bar chart: upcoming readouts per dated month (quarter/half-only items omitted)."""
    ms = []
    for sk, g in groups.items():
        m = re.match(r"^(\d{4})-(\d{2})-1$", sk)
        if m: ms.append((int(m.group(1)), int(m.group(2)), len(g["rows"])))
    if len(ms) < 2: return ""
    ms.sort()
    n = len(ms); mx = max(c for _, _, c in ms) or 1
    W = 782; H = 150; padT = 22; plotH = 106; bw = (W - 16) / n
    out = [f'<svg viewBox="0 0 {W} {H}" width="100%" style="max-width:{W}px;display:block;margin:8px 0 2px" role="img" aria-label="Upcoming readouts per month">',
           f'<line x1="8" y1="{padT+plotH}" x2="{W-8}" y2="{padT+plotH}" stroke="#1a3358"/>']
    for i, (y, mo, c) in enumerate(ms):
        bh = plotH * c / mx; x = 8 + i * bw; by = padT + plotH - bh
        out.append(f'<rect x="{x+bw*0.16:.1f}" y="{by:.1f}" width="{bw*0.68:.1f}" height="{bh:.1f}" rx="2" fill="#e3ba5e" opacity=".92"/>')
        out.append(f'<text x="{x+bw/2:.1f}" y="{by-3:.1f}" text-anchor="middle" font-size="9" fill="#a7bcd9">{c}</text>')
        lab = MON[mo][:3] + (f" '{y%100:02d}" if (mo == 1 or i == 0) else "")
        out.append(f'<text x="{x+bw/2:.1f}" y="{H-6:.1f}" text-anchor="middle" font-size="9" fill="#94a9c9">{lab}</text>')
    out.append('</svg><div class="note" style="margin:0 0 6px">Upcoming readouts per month (dated estimates; quarter/half-year-only items not charted).</div>')
    return "".join(out)

rows = list(csv.DictReader(open(SRC, encoding="utf-8", errors="ignore")))
def col(*names):
    for n in names:
        if rows and n in rows[0]: return n
    return None
c_cat, c_tk, c_dt, c_drug, c_ind, c_url = col("category"), col("ticker"), col("catalyst_date"), col("drug"), col("indication"), col("source_url")
c_qa = col("qa_flag")  # set by the crawler's canonicalize_and_qa step (absent in older files)
c_prec = col("date_precision")  # day/month/quarter/half — month-precision readouts shown as "(est.)"

def bucket(cat):
    groups = {}
    for r in rows:
        if str(r.get(c_cat, "")).lower() != cat: continue
        if c_qa and any(f in str(r.get(c_qa, "") or "") for f in ("stale_alias", "blank_drug")): continue
        if cat == "readout" and re.match(r"^\s*healthy\b", str(r.get(c_ind, "") or ""), re.I): continue  # drop Ph1 healthy-volunteer noise
        d = str(r.get(c_dt, "")).strip()
        if not keep(d): continue
        g = date_group(d)
        if not g: continue
        sk, label, disp = g
        prec = (str(r.get(c_prec, "") or "").lower() if c_prec else "")
        if cat == "readout" and (prec == "month" or (not prec and re.fullmatch(r"\d{4}-\d{2}-01", d))):
            mm = d[5:7]
            if mm.isdigit() and 1 <= int(mm) <= 12: disp = f"{MON[int(mm)][:3]} {d[:4]} (est.)"  # month estimate, not a hard date
        groups.setdefault(sk, {"label": label, "rows": []})["rows"].append(
            {"tk": r.get(c_tk, ""), "date": disp, "drug": r.get(c_drug, "") or "-", "ind": r.get(c_ind, ""), "url": r.get(c_url, ""), "_s": d})
    for sk in groups: groups[sk]["rows"].sort(key=lambda x: x["_s"])
    return groups

readouts, devices = bucket("readout"), bucket("device")
nR = sum(len(g["rows"]) for g in readouts.values()); nD = sum(len(g["rows"]) for g in devices.values())

open(os.path.join(OUT, "readouts.html"), "w", encoding="utf-8").write(page(
    "readouts",
    "2026 Clinical Trial Readout Calendar - Upcoming Phase 1/2/3 Data | pdufa.bio",
    "Upcoming clinical-trial data readouts by month: drug, company, indication and the trial source. Estimated primary-completion windows from ClinicalTrials.gov. Facts, not advice.",
    "https://www.pdufa.bio/readouts",
    '2026 <span class="g">Clinical Trial Readout Calendar</span>',
    "Upcoming Phase 1/2/3 data readouts " + DASH + " company, drug, indication, and the registered trial. "
    "Dates are <b>estimated primary-completion windows</b> from ClinicalTrials.gov, not fixed announcements " + DASH + " they shift. Tap any row for the trial record.",
    readouts,
    f"{nR} upcoming readouts. Source: ClinicalTrials.gov primary-completion estimates (month precision). Readout timing is not a guaranteed announcement date.",
    chart=month_chart(readouts)))

open(os.path.join(OUT, "devices.html"), "w", encoding="utf-8").write(page(
    "devices",
    "2026 FDA Medical Device Calendar - PMA / 510(k) / De Novo Decisions | pdufa.bio",
    "Upcoming FDA medical-device milestones by month: PMA, 510(k), De Novo and device data readouts, with company, product and source. Facts, not advice.",
    "https://www.pdufa.bio/devices",
    '2026 <span class="g">FDA Medical Device Calendar</span>',
    "Upcoming medical-device FDA milestones " + DASH + " PMA, 510(k), De Novo submissions/decisions and pivotal device readouts. "
    "Company, product, indication and the source filing. Tap any row for the source.",
    devices,
    f"{nD} upcoming device milestones. Sources: company filings / curated device seed. Many device dates are quarter/half-year windows."))

print(f"readouts: {nR} rows across {len(readouts)} groups -> {OUT}/readouts.html")
print(f"devices:  {nD} rows across {len(devices)} groups -> {OUT}/devices.html")
# Pass 19: /readouts + /devices now emit ItemList JSON-LD (see page()).
