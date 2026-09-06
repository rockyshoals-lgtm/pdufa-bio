# -*- coding: utf-8 -*-
"""/fda-this-month -- the month's FDA decisions as dated SENTENCES, rebuilt daily.

Strategy audit 2026-09-05b section 3: Pharmacy Times' "8 PDUFA Dates to Watch" is a
prose walk through the quarter, published Aug 21, already cited by Google's AI
Overview -- while our better-sourced dates sit in a table extractors skip. This page
is the same shape generated from the dataset: every date a sentence, every sentence
linked to its event row, decided outcomes stated in words, precision honesty kept
(month/quarter rows say so instead of inventing a day). Evergreen URL so authority
accrues; the daily rebuild is what makes it better than a frozen article.
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
# Audit 09-05 (0800 slot) P2-7: every date a page prints is the EASTERN calendar date of
# the build, from one shared function (site_dates.py), never the runner's UTC clock.
import sys as _sys; _sys.path.insert(0, HERE)
from site_dates import eastern_today as _eastern_today

SITE = os.path.join(HERE, "pdufa_site_src")
OUT = os.path.join(SITE, "fda-this-month")
MONTHS = ["", "January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]


def esc(s):
    return html.escape(str(s), quote=False)


def load_rows():
    src = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8",
                  errors="replace").read().replace("\x00", "")
    return json.loads(src[src.index("["):src.rindex("]") + 1])


def ev_sentence(r, decided=False):
    tk = str(r.get("t") or "").upper()
    # A partner-held application is one FDA decision listed under two tickers. Counting it
    # twice made /fda-this-month read "8 remain" against /calendar's 7 (audit 09-06 NEW-3,
    # zilurgisertib: Incyte filed the NDA, Mirum in-licensed worldwide rights in May 2026).
    partners = r.get("_partners") or []
    tk_label = " / ".join([tk] + [p for p in partners if p != tk])
    name = str(r.get("name") or "the application").strip()
    company = str(r.get("company") or "").strip()
    who = (f"{esc(name)}"
           + (f" ({esc(company)}, {esc(tk_label)})" if company else f" ({esc(tk_label)})"))
    ind = str((r.get("_d") or {}).get("indication") or "").strip()
    ind_txt = f" in {esc(ind)}" if ind else ""
    d = str(r.get("d") or "")
    day = dt.date.fromisoformat(d)
    href = str(r.get("url") or f"/ticker/{tk}")
    if decided:
        oc = str(r.get("oc") or "").strip()
        dcd = str(r.get("dcd") or "")[:10]
        when = ""
        if re.match(r"^\d{4}-\d{2}-\d{2}$", dcd):
            dd = dt.date.fromisoformat(dcd)
            when = f"On {MONTHS[dd.month]} {dd.day}"
            # OBS-1: a row counted in this month by its GOAL date may have been decided in
            # an earlier month, which is the normal case (the FDA is not obliged to use its
            # full clock). Say why it is here rather than leaving two dates unexplained.
            if d and dcd < d:
                when = (f"Ahead of its {MONTHS[day.month]} {day.day} goal date, on "
                        f"{MONTHS[dd.month]} {dd.day}")
        else:
            when = f"By its {MONTHS[day.month]} {day.day} goal date"
        if oc.lower() == "approved":
            verb = "approved"
        elif oc.upper() == "CRL":
            verb = "issued a Complete Response Letter for"
        else:
            verb = "acted on"
        link = f"/fda-decision/{tk}-{dcd or d}"
        return (f'<p>{when}, the FDA {verb} <a class="lit" href="{esc(link)}">{who}</a>'
                f"{ind_txt}.</p>")
    return (f'<p><b>{MONTHS[day.month]} {day.day}</b>: the FDA is due to decide on '
            f'<a class="lit" href="{esc(href)}">{who}</a>{ind_txt}. That is the goal '
            f"date; the agency can act earlier or extend it.</p>")


def merge_partners(rows):
    """One application listed under several tickers is ONE decision. Group on (goal date,
    normalized drug name); the first ticker keeps the row and the rest become _partners.

    Audit 09-06 NEW-3/OBS-1: without this, PFE+ROIV (brepocitinib) and INCY+MIRM
    (zilurgisertib) each counted twice here while /calendar rendered them as one row, so
    the two pages disagreed on every September number. Same convention as the calendar's
    multi-ticker label ("JAZZ / ONC / ZYME")."""
    def key(r):
        nm = re.sub(r"[^a-z0-9]+", " ", str(r.get("name") or "").lower())
        nm = re.split(r"\s*\(", nm)[0].strip()
        return (str(r.get("d") or ""), nm[:28])
    seen, out = {}, []
    for r in rows:
        k = key(r)
        if k in seen and k[1]:
            seen[k].setdefault("_partners", []).append(str(r.get("t") or "").upper())
            continue
        c = dict(r)
        seen[k] = c
        out.append(c)
    return out


def month_events(rows, y, m):
    """Membership is by GOAL DATE, the same rule /calendar uses (audit 09-06 OBS-1).

    /fda-this-month used to count a decision in the month it was ANNOUNCED, so September
    read 10/2/8 while /calendar read 13/6/7 for the same month -- both defensible, two
    pages disagreeing. A decision that came early still belongs to the month of its goal
    date; the sentence says it was decided ahead of that date. Archive-only decisions have
    no goal date and are keyed by their decision date, exactly as the calendar restores them."""
    pre = f"{y}-{m:02d}"
    day_up, coarse, decided = [], [], []
    for r in merge_partners([x for x in rows if x.get("type") == "PDUFA"]):
        d = str(r.get("d") or "")
        st = str(r.get("st") or "").lower()
        dcd = str(r.get("dcd") or "")[:10]
        if st == "decided":
            key = d if d.startswith(pre) else (dcd if re.match(r"^\d{4}-\d{2}", dcd) else "")
            if key.startswith(pre):
                decided.append(r)
            continue
        if not d.startswith(pre):
            continue
        if (r.get("dp") or "day") == "day":
            day_up.append(r)
        else:
            coarse.append(r)
    day_up.sort(key=lambda r: r.get("d") or "")
    decided.sort(key=lambda r: str(r.get("dcd") or r.get("d") or ""))
    return day_up, coarse, decided


def archive_only_decisions(y, m, have):
    """Decisions in the /fda-decision archive for this month that have NO dataset row
    (the camizestrant class: approved with no tracked event). Rendered from the
    archive page's own answer-format title, so nothing is claimed twice."""
    out = []
    droot = os.path.join(SITE, "fda-decision")
    if not os.path.isdir(droot):
        return out
    pre = f"{y}-{m:02d}"
    for slug in os.listdir(droot):
        mm = re.match(r"^([A-Z]{1,6})-(\d{4}-\d{2}-\d{2})$", slug)
        if not mm or not mm.group(2).startswith(pre) or (mm.group(1), mm.group(2)) in have:
            continue
        p = os.path.join(droot, slug, "index.html")
        if not os.path.isfile(p):
            continue
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        mt = re.search(r"<title>([^<]+)</title>", doc)
        ttl = html.unescape(mt.group(1)) if mt else ""
        md = re.search(r"^(.*?)\s+(Approved|CRL|Withdrawn)\b", ttl)
        if not md:
            continue
        out.append({"t": mm.group(1), "d": mm.group(2), "dcd": mm.group(2),
                    "oc": "Approved" if md.group(2) == "Approved" else md.group(2),
                    "name": md.group(1).strip(), "company": "",
                    "url": f"/fda-decision/{slug}"})
    return out


def main():
    rows = load_rows()
    today = _eastern_today()
    y, m = today.year, today.month
    ny, nm = (y, m + 1) if m < 12 else (y + 1, 1)
    mon = f"{MONTHS[m]} {y}"
    nmon = f"{MONTHS[nm]} {ny}"

    up, coarse, dec = month_events(rows, y, m)
    have = {(str(r.get("t") or "").upper(), str(r.get("dcd") or r.get("d") or "")[:10])
            for r in dec}
    dec += archive_only_decisions(y, m, have)
    dec.sort(key=lambda r: str(r.get("dcd") or r.get("d") or ""))
    up2, coarse2, _ = month_events(rows, ny, nm)

    ahead = [r for r in up if str(r.get("d")) >= today.isoformat()]
    intro = (f"{len(ahead)} FDA decision date{'s' if len(ahead) != 1 else ''} "
             f"remain{'s' if len(ahead) == 1 else ''} on the {mon} calendar, and "
             f"{len(dec)} {mon} decision{'s have' if len(dec) != 1 else ' has'} already "
             f"been made. Every date below comes from a company filing or FDA notice "
             f"and links its event record. The FDA publishes no forward calendar of "
             f"these dates.")

    dec_html = "".join(ev_sentence(r, decided=True) for r in dec) or \
        f"<p>No {mon} decision is in the record yet.</p>"
    up_html = "".join(ev_sentence(r) for r in ahead) or \
        (f"<p>No day-precision PDUFA date remains on the {mon} calendar.</p>")
    coarse_html = ""
    if coarse:
        names = "; ".join(
            f'<a class="lit" href="{esc(str(r.get("url") or "/calendar"))}">'
            f'{esc(str(r.get("name") or r.get("t")))}</a> ({esc(str(r.get("t") or "").upper())})'
            for r in coarse)
        coarse_html = (f"<p>Also expected this month, without a company-disclosed day: "
                       f"{names}. Where the source gives only a month or quarter, we say "
                       f"so instead of inventing a day.</p>")
    nxt_html = ""
    if up2:
        nxt = "".join(ev_sentence(r) for r in up2[:10])
        nxt_html = f"<h2>Looking ahead to {esc(nmon)}</h2>{nxt}"
        if len(up2) > 10:
            nxt_html += (f'<p>Plus {len(up2) - 10} more on the '
                         f'<a class="lit" href="/calendar">full calendar</a>.</p>')

    title = f"What the FDA Decides in {mon}: PDUFA Dates in Plain Language | pdufa.bio"
    desc = (f"{len(ahead)} FDA decision dates remain in {mon}, with {len(dec)} already "
            f"decided. Each date as a sentence, sourced and linked. Updated daily.")
    if len(desc) > 158:
        desc = desc[:158].rsplit(" ", 1)[0].rstrip(",;:") + "."

    qa = [(f"How many FDA decisions are scheduled for {mon}?",
           f"{len(ahead) + len(dec)} tracked PDUFA events fall in {mon}: {len(dec)} "
           f"decided so far and {len(ahead)} still ahead, plus "
           f"{len(coarse)} expected without a company-disclosed day. The FDA does not "
           f"publish a forward calendar; every date here comes from a company filing "
           f"or FDA notice."),
          ("Can these dates change?",
           "Yes. A PDUFA date is the FDA's review goal, not a fixed announcement "
           "date. The agency can decide early, and it can extend the date by three "
           "months when a sponsor submits a major amendment during review.")]
    jsonld = json.dumps({"@context": "https://schema.org", "@type": "FAQPage",
                         "mainEntity": [{"@type": "Question", "name": q,
                                         "acceptedAnswer": {"@type": "Answer",
                                                            "text": re.sub(r"<[^>]+>", "", ans)}}
                                        for q, ans in qa]}, ensure_ascii=False)
    faq = "".join(
        f'<div style="background:#0c1d38;border:1px solid #1e3a63;border-radius:12px;'
        f'padding:14px 16px;margin:12px 0"><b>{esc(q)}</b>'
        f'<div style="color:#9db3d4;font-size:14px;margin-top:6px">{ans}</div></div>'
        for q, ans in qa)

    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><title>{esc(title)}</title><meta name="description" content="{esc(desc)}"><link rel="canonical" href="https://www.pdufa.bio/fda-this-month"><meta name="robots" content="index,follow,max-image-preview:large"><meta name="theme-color" content="#02060d"><link rel="icon" type="image/svg+xml" href="/favicon.svg"><meta property="og:type" content="article"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}"><meta property="og:url" content="https://www.pdufa.bio/fda-this-month"><style>*{{box-sizing:border-box}}body{{margin:0;background:#02060d;color:#f2f6fc;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;line-height:1.6}}a{{color:#6fb6ff;text-decoration:none}}a:hover{{text-decoration:underline}}.wrap{{max-width:820px;margin:0 auto;padding:22px 18px 60px}}.top{{display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #1a3358;padding-bottom:12px}}.brand{{font-size:19px;font-weight:800}}.brand b{{color:#e3ba5e}}.nav a{{color:#a7bcd9;font-size:13px;margin-left:14px}}h1{{font-size:27px;line-height:1.18;margin:10px 0 6px}}h2{{font-size:18px;color:#e3ba5e;margin:26px 0 8px}}.bc{{font-size:12px;color:#94a9c9;margin:16px 0 4px}}.bc a{{color:#94a9c9}}.sub{{color:#a7bcd9;font-size:15px}}p{{max-width:76ch}}.note{{font-size:12px;color:#94a9c9;line-height:1.6}}footer{{border-top:1px solid #1a3358;margin-top:34px;padding-top:16px;font-size:11.5px;color:#94a9c9;line-height:1.6}}footer b{{color:#a7bcd9}}</style><script type="application/ld+json">{jsonld}</script></head><body><div class="wrap"><div class="top"><a class="brand" href="/">pdufa<b>.bio</b></a><div class="nav"><a href="/calendar">Calendar</a><a href="/decisions">Decisions</a><a href="/readouts">Readouts</a><a href="/research">Research</a></div></div><div class="bc"><a href="/">Home</a> &rsaquo; What the FDA decides in {esc(mon)}</div><h1>What the FDA decides in {esc(mon)}</h1><div class="sub">{intro}</div><h2>Decided so far in {esc(mon)}</h2>{dec_html}<h2>Still ahead in {esc(mon)}</h2>{up_html}{coarse_html}{nxt_html}<h2>Questions</h2>{faq}<p class="note">Dates and outcomes only, each linked to its record; see the <a href="/calendar">full calendar</a> and <a href="/learn/what-is-a-pdufa-date">what a PDUFA date is</a>. Not a prediction about any pending application, and not investment advice.</p><footer><b>Not affiliated with or endorsed by the FDA.</b> pdufa.bio is an independent publication with no affiliation with, endorsement by, sponsorship by, or connection to the U.S. Food and Drug Administration. <b>Informational and educational purposes only. Not investment advice.</b> Verify every date and outcome against primary FDA, SEC or company filings.<br><br>&copy; {y} pdufa.bio. All rights reserved.</footer></div><script src="/cmdk.js" defer></script></body></html>"""

    os.makedirs(OUT, exist_ok=True)
    io.open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(page)
    print(f"wrote /fda-this-month ({mon}: {len(dec)} decided, {len(ahead)} ahead, "
          f"{len(coarse)} coarse; {nmon} preview: {len(up2)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
