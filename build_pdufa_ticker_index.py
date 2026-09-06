# -*- coding: utf-8 -*-
"""build_pdufa_ticker_index.py -- /pdufa/{TICKER} must never point a live catalyst at a dead one.

Red team, 2026-08-11, two days before Lantheus's decision: /pdufa/LNTH 308-redirected to the June
CRL for LNTH-2501 -- a different molecule -- while the API's canonical url for the UPCOMING Aug 13
MK-6240 event was that same /pdufa/LNTH. Anyone following the link for Thursday's decision landed
on June's rejection. Six tickers were affected (ARQT worst: same brand, different strength -- a
reader could conclude the 0.05% cream is approved when only the 0.3% is), and the mechanism will
recur forever: the bare-ticker redirects were CORRECT when written, because each ticker had one
finished story; they became wrong the day the same ticker got a new catalyst.

So this is a standing rule, run daily, not a repair:

  1. A bare /pdufa/{T} redirect to a decision page is allowed ONLY while ticker T has no upcoming
     PDUFA. The moment a new catalyst appears, the redirect is removed here.
  2. /pdufa/{T} then serves an INDEX of that ticker's PDUFA events -- upcoming first with drug,
     date and countdown, decided ones linking their own /fda-decision pages. One URL, one job:
     the audit's '/pdufa/{T} should behave like an index, not a redirect to whichever event
     happens to be first.'
  3. An existing bare-ticker page is left alone when its headline names ANY of the ticker's
     upcoming drugs by any of its name tokens (it is the live event page the calendar links --
     EXEL's page says 'XL092 with atezolizumab' while the dataset says 'Zanzalintinib (XL092)',
     same drug, different alias), and regenerated as an index when it names none of them
     (VTRS's page still headlined the drug approved in July; MRK's and PFE's still headlined
     the decided KEYTRUDA+Padcev event with different drugs now pending).

Drug-slugged redirects (/pdufa/LNTH-lnth-2501 -> the June decision) are untouched: they name a
specific finished event and remain correct forever.

    python build_pdufa_ticker_index.py [--dry-run]
"""
import argparse, datetime as dt, html, json, os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")
VJ = os.path.join(SITE, "vercel.json")
BASE = "https://www.pdufa.bio"
TODAY = dt.datetime.now(dt.timezone.utc).date().isoformat()
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def esc(s):
    return html.escape(str(s or ""), quote=True)


def pretty(d, dp="day"):
    y, m, day = int(d[:4]), int(d[5:7]), int(d[8:10])
    if dp == "day":
        return f"{MONTHS[m-1]} {day}, {y}"
    if dp == "month":
        return f"{MONTHS[m-1]} {y}"
    return f"Q{(m-1)//3+1} {y}"


SHELL = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{canon}">
<link rel="preload" href="/fonts/SpaceGrotesk-700.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="/fonts/fonts.css">
<style>
:root{{--bg:#0b1017;--line:#1f2a3c;--mut2:#8fa3bd;--gold:#e8b44c}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:#dfe9f7;
font:15px/1.65 "IBM Plex Mono",ui-monospace,monospace}}
.wrap{{max-width:880px;margin:0 auto;padding:18px 16px 60px}}
.top{{display:flex;justify-content:space-between;align-items:center;margin-bottom:22px}}
.brand{{font-family:"Space Grotesk",sans-serif;font-weight:700;font-size:20px;color:#fff;
text-decoration:none}}.brand b{{color:var(--gold)}}
.nav a{{color:var(--mut2);text-decoration:none;margin-left:14px;font-size:13px}}
h1{{font-family:"Space Grotesk",sans-serif;font-size:26px;margin:0 0 6px}}
h2{{font-family:"Space Grotesk",sans-serif;font-size:17px;margin:26px 0 8px}}
.row{{display:flex;flex-wrap:wrap;gap:10px;justify-content:space-between;padding:11px 0;
border-top:1px solid var(--line);color:inherit;text-decoration:none}}
.row:hover{{background:#141d2d}}
.t{{font-weight:600}}.d{{color:var(--mut2);font-size:13.5px}}
.ok{{color:#46d17f}}.bad{{color:#ff8f6b}}.up{{color:var(--gold);font-weight:700}}
a.lit{{color:#9ec5ff}}
.legal{{margin-top:40px;padding-top:14px;border-top:1px solid var(--line);color:var(--mut2);
font-size:12px;line-height:1.7}}
</style></head><body><div class="wrap">
<div class="top"><a class="brand" href="/">pdufa<b>.bio</b></a>
<div class="nav"><a href="/calendar">Calendar</a><a href="/decisions">Decisions</a>
<a href="/readouts">Readouts</a></div></div>
<h1>{h1}</h1>
{body}
<div class="legal">Facts and dates only; not investment advice. Verify against primary FDA, SEC
and company filings. pdufa.bio is not affiliated with the FDA.</div>
</div></body></html>
"""


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    src = open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
    rows, _ = json.JSONDecoder().raw_decode(src[src.find("["):])

    # decided facts from the archive for the index's history section
    arch = {}
    darch = os.path.join(SITE, "decisions", "index.html")
    if os.path.exists(darch):
        dh = open(darch, encoding="utf-8", errors="replace").read()
        for m in re.finditer(
                r'href="/fda-decision/([A-Z]{1,6})-(\d{4}-\d{2}-\d{2})"[^>]*>(.*?)</a>', dh, re.S):
            txt = html.unescape(re.sub(r"<[^>]+>", " ", m.group(3)))
            oc = ("Approved" if re.search(r"\bapproved\b", txt, re.I)
                  else "CRL" if re.search(r"\bcrl\b|complete response", txt, re.I) else "")
            body = re.split(r"(?:Approved|CRL|Complete Response Letter)\s*:?\s*", txt, maxsplit=1)
            drug = re.sub(r"\s+", " ", body[1]).strip(" :") if len(body) > 1 else ""
            arch.setdefault(m.group(1), []).append((m.group(2), oc, drug))

    up_by, all_by = {}, {}
    for r in rows:
        if r.get("type") != "PDUFA" or not r.get("t"):
            continue
        t = str(r["t"]).upper()
        all_by.setdefault(t, []).append(r)
        if str(r.get("st", "")).lower() != "decided" and str(r.get("d", "")) >= TODAY:
            up_by.setdefault(t, []).append(r)

    # 1. redirect hygiene
    cfg = json.load(open(VJ, encoding="utf-8"))
    kept, dropped = [], []
    for rd in cfg.get("redirects", []):
        m = re.match(r"^/pdufa/([A-Z]{1,6})$", str(rd.get("source", "")))
        if m and m.group(1) in up_by:
            dropped.append(rd["source"])
            continue
        kept.append(rd)
    if dropped and not a.dry_run:
        cfg["redirects"] = kept
        json.dump(cfg, open(VJ, "w", encoding="utf-8"), indent=1)
    print(f"stale bare-ticker redirects removed: {len(dropped)} {dropped}")

    # 2 + 3. index pages
    STOP = {"the", "with", "plus", "and", "for", "cream", "tablet", "tablets", "capsule",
            "capsules", "injection", "oral", "dose", "low", "high", "weekly", "daily", "patch",
            "gel", "solution", "spray", "extended", "release", "acid", "sodium", "hydrochloride"}
    written = kept_pages = 0
    for t, ups in sorted(up_by.items()):
        ups.sort(key=lambda r: r["d"])
        nearest = ups[0]
        drug0 = str(nearest.get("name") or "")
        # any name token of ANY upcoming drug counts: pages may use an alias the dataset
        # doesn't lead with (EXEL: page 'XL092', dataset 'Zanzalintinib (XL092)')
        toks = {w for r in ups
                for w in re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)*",
                                    str(r.get("name") or "").lower())
                if len(w) >= 3 and w not in STOP and not w.isdigit()}
        p = os.path.join(SITE, "pdufa", t, "index.html")

        if os.path.exists(p):
            existing = open(p, encoding="utf-8", errors="replace").read()
            h1 = re.search(r"<h1[^>]*>(.*?)</h1>", existing, re.S)
            h1t = html.unescape(re.sub(r"<[^>]+>", " ", h1.group(1))).lower() if h1 else ""
            h1toks = set(re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)*", h1t))
            # Audit 2026-09-05 (0800 slot) P1-5: /pdufa/CORT said "Decided: Approved March
            # 25, 2026 ... no longer an upcoming decision" and, lower down, "1 business days
            # to decision ... FDA decision expected July 11, 2026" -- the ROSELLA page kept
            # by the token rule because the NEW catalyst (GRACE, Cushing's, Dec 17) is the
            # same molecule. A page that declares itself decided is not the live event page,
            # whatever its headline names; it is regenerated as the index.
            self_decided = ("no longer an upcoming decision" in existing
                            or "<!--DECBAN:BEGIN-->" in existing)
            if toks & h1toks and not self_decided:
                kept_pages += 1
                continue          # live event page already about a currently-upcoming drug

        evs = []
        for r in ups:
            days = (dt.date.fromisoformat(r["d"]) - dt.date.fromisoformat(TODAY)).days \
                if re.match(r"^\d{4}-\d{2}-\d{2}$", str(r.get("d"))) else None
            cd = (f'<span class="up">in {days} day{"s" if days != 1 else ""}</span>'
                  if days is not None and (r.get("dp") or "day") == "day" and days >= 0 else "")
            evs.append(f'<a class="row" href="/calendar"><span class="t">'
                       f'{esc(pretty(r["d"], r.get("dp") or "day"))} {cd}</span>'
                       f'<span class="d">{esc(str(r.get("name") or ""))[:70]}</span></a>')
        hist = "".join(
            f'<a class="row" href="/fda-decision/{t}-{d}"><span class="t">{esc(pretty(d))} '
            + (f'<span class="ok">&#10003; Approved</span>' if oc == "Approved"
               else f'<span class="bad">CRL</span>' if oc == "CRL" else "")
            + f'</span><span class="d">{esc(drug)[:70]}</span></a>'
            for d, oc, drug in sorted(arch.get(t, []), reverse=True))

        lede = (f"{t} has {len(ups)} upcoming FDA decision date"
                f"{'s' if len(ups) != 1 else ''}; the nearest is "
                f"{esc(pretty(nearest['d'], nearest.get('dp') or 'day'))} for "
                f"{esc(drug0[:60])}."
                + (f" {len(arch.get(t, []))} past decision"
                   f"{'s are' if len(arch.get(t, [])) != 1 else ' is'} on record below, each on "
                   f"its own page." if arch.get(t) else "")
                + " One event, one page: past decisions never share a URL with a live catalyst.")
        body = (f'<p style="color:var(--mut2);max-width:74ch">{lede}</p>'
                f'<p><a class="lit" href="/ticker/{t}">{t} catalyst hub</a> &middot; '
                f'<a class="lit" href="/calendar">full calendar</a></p>'
                "<h2>Upcoming</h2>" + "".join(evs)
                + ("<h2>Decided</h2>" + hist if hist else ""))
        page = SHELL.format(
            title=f"{t} PDUFA Dates: {esc(drug0[:40])} &amp; History | pdufa.bio",
            desc=esc(f"{t}'s FDA decision dates: {pretty(nearest['d'], nearest.get('dp') or 'day')}"
                     f" for {drug0[:50]}, plus every past decision with its outcome."[:158]),
            canon=f"{BASE}/pdufa/{t}", h1=f"{t} FDA decision dates", body=body)
        if not a.dry_run:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, "w", encoding="utf-8").write(page)
        written += 1
        print(f"  index -> /pdufa/{t}  (nearest: {nearest['d']} {drug0[:40]})")

    print(f"indexes written: {written}; healthy event pages left alone: {kept_pages}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
