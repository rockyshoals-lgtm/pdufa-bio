# -*- coding: utf-8 -*-
"""build_readout_months.py -- each /readouts/<year>/<month> page lists that month's readouts from today's dataset.

WHY (OMW, 2026-11-27). The month pages were written once by build_seo_pages.py from an old crawler export and no
rebuild step ever rewrote their rows, only the site-wide blocks around them. Measured on 2026-11-27: the December
2026 page listed 49 "estimates" where the dataset holds 20 registry estimates (plus 113 company-guided dates at
day or month precision it never showed); June through October 2026 still read "trial-readout estimates for <month>"
months after those windows passed, with no word on what came of them; and no row linked its drug page, though every
readout row in the dataset has one. /readouts itself was rebuilt the same way on 2026-11-26
(build_readout_forward.py); these pages are its month-by-month views, so they now come from the same rows.

WHAT IT WRITES, between <!--RMONTH:BEGIN--> and <!--RMONTH:END--> (replacing the old intro, row grid and count),
for every month page already on disk:

  * Reported: readouts the company reported that month (day-precision Reported rows), the result as the dataset
    records it and the company release.
  * Company-guided: dates a company stated in an SEC filing or release that fall in this month at day or month
    precision, printed at that precision, with the filing. Quarter and looser guidance is counted, not listed,
    since printing it under one month would claim a precision the company did not give.
  * Registry estimates: Estimated rows whose ClinicalTrials.gov primary-completion month is this month, each with
    its NCT record. In a month that has passed, each says what was found since (sponsor release, registry status,
    or "no topline found as of <date>"), from the row's own resolution record (resolve_past_readouts.py).

Every program links its /drug page and every ticker its company hub, each only when the page exists
(readout_links.py), so the links can never be dead in the build that writes them. The FAQ count follows the
rows. Nothing is estimated here: dates, results and statuses are the dataset's.
Idempotent; run after build_drug_pages.py (so drug links resolve) and resolve_past_readouts.py.

    python build_readout_months.py [--site DIR] [--today YYYY-MM-DD]
"""
import argparse
import datetime as dt
import html
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from readout_links import drug_page  # noqa: E402

SITE = os.path.join(HERE, "pdufa_site_src")
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")
B, E = "<!--RMONTH:BEGIN-->", "<!--RMONTH:END-->"
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]
SUB_START = '<div class="sub">'
CALLOUT = '<div class="callout">'
NOTE = '<p class="note" style="color:#94a9c9;font-size:13px;line-height:1.5;margin:4px 0 10px">'  # the page has no .note rule

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass


def esc(s):
    return html.escape(str(s or ""), quote=True)


def eastern_today():
    try:
        from zoneinfo import ZoneInfo
        return dt.datetime.now(ZoneInfo("America/New_York")).date()
    except Exception:  # noqa: BLE001
        return dt.date.today()


def load_rows(path=DATASET):
    src = io.open(path, encoding="utf-8", errors="replace").read().replace("\x00", "")
    rows, _ = json.JSONDecoder().raw_decode(src[src.find("["):])
    return [r for r in rows if r.get("type") == "Readout" and r.get("t") and re.match(r"^\d{4}-\d{2}", str(r.get("d")))]


def day(d):
    d = dt.date.fromisoformat(str(d)[:10])
    return f"{d:%b} {d.day}, {d.year}"


def mon(d):
    d = dt.date.fromisoformat(str(d)[:10])
    return f"{d:%b} {d.year}"


def nct(r):
    raw = (r.get("_d") or {}).get("nct_id")
    n = raw.get("nct") if isinstance(raw, dict) else raw
    n = str(n or "").strip().upper()
    return n if re.match(r"^NCT\d{8}$", n) else ""


def program(r):
    d = r.get("_d") or {}
    p = d.get("program") or re.sub(r"\s+readout$", "", str(r.get("name") or ""), flags=re.I)
    return re.sub(r"\s+", " ", str(p)).strip()[:120]


def sections(rows, ym):
    """(reported, guided, estimated, n_loose_guided) for month 'YYYY-MM'."""
    inm = [r for r in rows if str(r["d"])[:7] == ym]
    rep = [r for r in inm if r.get("st") == "Reported"]
    gd = [r for r in inm if r.get("st") == "Guided" and r.get("dp") in ("day", "month")]
    loose = [r for r in inm if r.get("st") == "Guided" and r.get("dp") not in ("day", "month")]
    est = [r for r in inm if r.get("st") == "Estimated" and nct(r)]
    key = lambda r: (str(r["d"]), str(r["t"]), str(r.get("id")))  # noqa: E731
    return sorted(rep, key=key), sorted(gd, key=key), sorted(est, key=key), len(loose)


def found(r):
    """What came of a passed estimate window, from the row's own resolution and registry records."""
    d = r.get("_d") or {}
    res, reg = d.get("resolution") or {}, d.get("registry") or {}
    ros = str(reg.get("overall_status") or "").upper()
    if res.get("state") == "sponsor_release" and res.get("date"):
        return f"sponsor release {day(res['date'])}", res.get("url")
    if res.get("state") == "company_stopped" and res.get("date"):
        return f"stopped per the company {day(res['date'])}", res.get("url")
    if ros in ("TERMINATED", "WITHDRAWN", "SUSPENDED"):
        return f"{ros.lower()} per ClinicalTrials.gov", None
    if res.get("state") == "no_topline" and res.get("checked"):
        what = "scheduled date passed; no company results release found" if r.get("dp") == "day" else "no topline found"
        return f"{what} as of {day(res['checked'])}", None  # 2026-11-27: a dated presentation is not a topline window
    if res.get("state") == "results_posted_registry" and res.get("date"):
        return f"results posted on ClinicalTrials.gov {day(res['date'])}", None
    if ros == "COMPLETED":
        return "trial completed per ClinicalTrials.gov; no sponsor result on record", None
    return "window passed; not yet checked", None


def hub_link(tk, site):
    t = esc(tk)
    return f'<a href="/ticker/{t}">{t}</a>' if os.path.isfile(os.path.join(site, "ticker", tk, "index.html")) else t


def prog_link(r):
    p, dp = esc(program(r)), drug_page(r)
    return f'<a href="{esc(dp)}">{p}</a>' if dp else p


def ext(url, words):
    u = str(url or "")
    return f'<a href="{esc(u)}" rel="nofollow">{esc(words)}</a>' if u.startswith("https://") else ""


def row(tk, when, bits, site):
    bits = [b for b in bits if b]
    return (f'<div class="row"><div class="t">{hub_link(tk, site)} &middot; {when}</div>'
            f'<div class="d">{" &middot; ".join(bits)}</div></div>')


def render(rows, ym, today, site):
    y, m = int(ym[:4]), int(ym[5:7])
    name = f"{MONTHS[m - 1]} {y}"
    past = ym < today.strftime("%Y-%m")
    rep, gd, est, loose = sections(rows, ym)
    n = len(rep) + len(gd) + len(est)
    out = [B]
    lede = (f"Readouts on file for {name}, a month that has passed, from our dataset." if past else
            f"Readouts on file for {name} from our dataset. Company-guided dates are printed at the precision the "
            f"company used.")
    out.append(f'<div class="sub">{lede}</div>')
    out.append(f'<span class="count">{n} readout{"s" if n != 1 else ""}</span>')
    if rep:
        out.append(f'<div class="mhead">Reported ({len(rep)})</div><div class="grid">')
        for r in rep:
            when = day(r["d"]) if r.get("dp") == "day" else mon(r["d"])
            out.append(row(r["t"], when, [prog_link(r), esc(r.get("oc") or ""), ext(r.get("url"), "company release")],
                           site))
        out.append("</div>")
    if gd:
        out.append(f'<div class="mhead">Company-guided ({len(gd)})</div><div class="grid">')
        for r in gd:
            d = r.get("_d") or {}
            when = day(r["d"]) if r.get("dp") == "day" else mon(r["d"])
            src = " ".join(x for x in (str(d.get("guided_form") or "company filing"), str(d.get("guided_filed") or ""))
                           if x).strip()
            out.append(row(r["t"], f"{when} (company-guided)", [prog_link(r), ext(r.get("url"), src)], site))
        out.append("</div>")
    if est:
        out.append(f'<div class="mhead">ClinicalTrials.gov estimates ({len(est)})</div>'
                   + (NOTE + f'Trials whose registry primary-completion estimate fell in {name}, each with '
                      f'what was found since.</p>' if past else
                      NOTE + f'Trials whose registry primary-completion estimate falls in {name}: when the trial '
                      f'is expected to finish collecting its main data, not an announced readout date. Sponsors move '
                      f'it.</p>') + '<div class="grid">')
        for r in est:
            n_ = nct(r)
            bits = [prog_link(r), ext(f"https://clinicaltrials.gov/study/{n_}", n_)]
            if past:
                words, url = found(r)
                bits.append(ext(url, words) if url else esc(words))
            out.append(row(r["t"], f"{mon(r['d'])} (est.)", bits, site))
        out.append("</div>")
    if not n:
        out.append(NOTE + f'No readout on file for {name} at day or month precision. '
                   f'<a href="/readouts">Every upcoming readout</a>.</p>')
    if loose:
        out.append(NOTE.replace("margin:4px", "margin:12px") + f'{loose} more company-guided date{"s" if loose != 1 else ""} '
                   f'give{"" if loose != 1 else "s"} only a quarter or a looser window ending in {name}. They are on '
                   f'<a href="/readouts">/readouts</a> at the precision the company gave, not listed under one month.</p>')
    out.append(E)
    return "".join(out), n


def apply(doc, blk, n):
    if B in doc and E in doc:
        a, b = doc.index(B), doc.index(E) + len(E)
        new = doc[:a] + blk + doc[b:]
    else:
        a, b = doc.find(SUB_START), doc.find(CALLOUT)
        if a < 0 or b < 0 or b < a:
            return None
        pn = re.search(r'<div class="pn">.*?</div>', doc[a:b], re.S)  # the month-to-month links stay above the rows
        new = doc[:a] + (pn.group(0) if pn else "") + blk + doc[b:]
    return re.sub(r"currently tracks \d+ clinical-trial readouts with dates in",
                  f"currently tracks {n} clinical-trial readouts with dates in", new)


def month_pages(site):
    root = os.path.join(site, "readouts")
    for y in sorted(os.listdir(root)) if os.path.isdir(root) else []:
        if not re.match(r"^\d{4}$", y):
            continue
        for mname in os.listdir(os.path.join(root, y)):
            if mname.capitalize() in MONTHS:
                p = os.path.join(root, y, mname, "index.html")
                if os.path.isfile(p):
                    yield f"{y}-{MONTHS.index(mname.capitalize()) + 1:02d}", p


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", default=SITE)
    ap.add_argument("--today", default="")
    a = ap.parse_args(argv)
    today = dt.date.fromisoformat(a.today) if a.today else eastern_today()
    rows = load_rows(os.path.join(a.site, "api", "v1", "dataset.mjs"))
    n_ch = 0
    for ym, p in sorted(month_pages(a.site)):
        doc = io.open(p, encoding="utf-8").read()
        blk, n = render(rows, ym, today, a.site)
        new = apply(doc, blk, n)
        if new is None:
            print(f"  {p}: anchors not found; left alone")
            continue
        if new != doc:
            io.open(p, "w", encoding="utf-8", newline="").write(new)
            n_ch += 1
        print(f"  /readouts/{ym}: {n} readouts")
    print(f"readout month pages: {n_ch} changed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
