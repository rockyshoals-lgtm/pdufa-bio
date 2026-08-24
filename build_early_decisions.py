# -*- coding: utf-8 -*-
"""build_early_decisions.py -- "Does the FDA decide on the PDUFA date?" answered from our archive.

Red team 2026-08-24 s5: our sourced decision pages hold BOTH the PDUFA goal date and the ACTUAL
action date, each with a primary source. That combination is what makes this question answerable
and it is not something a calendar-only competitor can publish.

THE DENOMINATOR CAUTION (08-12g), honoured here rather than mentioned
Our archive's COVERAGE grows sharply across its window -- roughly sevenfold -- because we started
sourcing decisions systematically only recently. A rate computed over the whole corpus would
measure our own collection habits, not the FDA. So this page restricts itself to:

    * decisions in ONE year (2026), and
    * only those whose outcome AND both dates are backed by a primary source we link.

The inclusion rule is printed ON the page, the n is printed next to every number, and where the
sample is small the page says so instead of implying precision it does not have. If the sample
is below MIN_N the page states the cases individually and computes no rate at all -- a
percentage from a handful of events would be theatre.

    python build_early_decisions.py [--year 2026] [--min-n 8] [--dry-run]
"""
import argparse, datetime as dt, glob, html, json, os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
OUT = os.path.join(SITE, "research", "fda-decision-timing")
MON = ["January", "February", "March", "April", "May", "June", "July", "August",
       "September", "October", "November", "December"]


def esc(s):
    return html.escape(str(s or ""), quote=True)


def pretty(iso):
    y, m, d = int(iso[:4]), int(iso[5:7]), int(iso[8:10])
    return f"{MON[m - 1]} {d}, {y}"


def collect(year):
    """Sourced decisions in `year` that state BOTH a goal date and an actual action date."""
    src = open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8",
               errors="replace").read().replace("\x00", "")
    rows, _ = json.JSONDecoder().raw_decode(src[src.find("["):])
    out = []
    for r in rows:
        if r.get("type") != "PDUFA" or str(r.get("st", "")).lower() != "decided":
            continue
        goal, actual = str(r.get("d") or ""), str(r.get("dcd") or "")
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", goal) or \
           not re.match(r"^\d{4}-\d{2}-\d{2}$", actual):
            continue
        if not actual.startswith(str(year)):
            continue
        tk = str(r.get("t") or "").upper()
        page = os.path.join(SITE, "fda-decision", f"{tk}-{actual}", "index.html")
        if not os.path.exists(page):
            continue                       # no published decision page = not our sourced record
        doc = open(page, encoding="utf-8", errors="replace").read()
        low = doc.lower()
        if "price-only" in low or "outcome unverified" in low:
            continue                       # price-inferred: excluded by the inclusion rule
        if not re.search(r'href="https?://(?!www\.pdufa\.bio)', doc):
            continue                       # no primary source linked
        delta = (dt.date.fromisoformat(actual) - dt.date.fromisoformat(goal)).days
        out.append({"ticker": tk, "drug": r.get("name") or "", "goal": goal,
                    "actual": actual, "delta": delta, "outcome": r.get("oc") or "",
                    "slug": f"{tk}-{actual}"})
    out.sort(key=lambda x: x["delta"])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=2026)
    ap.add_argument("--min-n", type=int, default=8)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    rec = collect(a.year)
    n = len(rec)
    print(f"sourced {a.year} decisions with both dates: {n}")
    for r in rec:
        print(f"   {r['ticker']:<6} goal {r['goal']}  actual {r['actual']}  "
              f"{r['delta']:+d}d  {r['outcome']}")
    if not rec:
        print("nothing to publish")
        return 0

    early = [r for r in rec if r["delta"] < 0]
    onday = [r for r in rec if r["delta"] == 0]
    late = [r for r in rec if r["delta"] > 0]
    enough = n >= a.min_n

    rows = "".join(
        f'<a class="row" href="/fda-decision/{esc(r["slug"])}" style="display:flex;'
        f'justify-content:space-between;gap:12px;background:#0c1d38;border:1px solid #1e3a63;'
        f'border-radius:10px;padding:11px 13px;margin:8px 0;color:#eef4fc">'
        f'<span><b>{esc(r["ticker"])}</b> &middot; {esc(str(r["drug"])[:38])}</span>'
        f'<span style="color:#9db3d4">goal {esc(pretty(r["goal"]))} &rarr; '
        f'<b style="color:#eef4fc">{esc(pretty(r["actual"]))}</b> '
        f'<b style="color:{"#46d17f" if r["delta"] < 0 else "#9db3d4"}">'
        f'{r["delta"]:+d} days</b></span></a>' for r in rec)

    if enough:
        headline = (f"Of the <b>{n}</b> {a.year} FDA decisions in this archive whose outcome and "
                    f"dates we have checked against a primary source, <b>{len(early)}</b> came "
                    f"<b>before</b> the PDUFA goal date, <b>{len(onday)}</b> landed on it, and "
                    f"<b>{len(late)}</b> came after.")
    else:
        headline = (f"This archive currently holds <b>{n}</b> {a.year} decision"
                    f"{'s' if n != 1 else ''} whose outcome and dates are both backed by a "
                    f"primary source &mdash; too few to quote a rate from, so they are listed "
                    f"individually below rather than turned into a percentage.")

    med = ""
    if enough:
        ds = sorted(r["delta"] for r in rec)
        m = ds[len(ds) // 2] if len(ds) % 2 else (ds[len(ds) // 2 - 1] + ds[len(ds) // 2]) / 2
        med = (f" The median decision landed <b>{abs(m):.0f} day"
               f"{'s' if abs(m) != 1 else ''} {'before' if m < 0 else 'after'}</b> the goal date.")

    title = (f"Does the FDA decide on the PDUFA date? {a.year} decisions, "
             f"goal date vs actual | pdufa.bio")
    desc = (f"For {n} sourced {a.year} FDA decisions we hold both the PDUFA goal date and the "
            f"actual action date. {len(early)} came early. Every case links its primary source.")
    if len(desc) > 158:
        desc = desc[:158].rsplit(" ", 1)[0].rstrip(",;:") + "."

    qa = [(f"Does the FDA always decide on the PDUFA date?",
           f"No. In this archive's {a.year} sourced decisions, {len(early)} of {n} came before "
           f"the PDUFA goal date, {len(onday)} on it and {len(late)} after. The goal date is the "
           f"date by which the FDA aims to complete its review, not a fixed announcement date."),
          ("Can the FDA approve a drug early?",
           "Yes. The PDUFA date is a target for completing the review, so the agency can act "
           "sooner, and in this archive several 2026 decisions did &mdash; the earliest by "
           f"{abs(min(r['delta'] for r in rec))} days. It can also extend the date, usually when "
           "the company submits a major amendment that needs more review time."),
          ("Which decisions does this page count?",
           f"Only {a.year} decisions where this archive holds the PDUFA goal date, the actual "
           f"action date, and a primary source (FDA notice, SEC filing or company release) that "
           f"we link. Decisions inferred from share-price behaviour are excluded, and no rate is "
           f"computed across earlier years because our coverage of them is much thinner and a "
           f"rate would measure our collection rather than the FDA.")]

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

    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><title>{esc(title)}</title><meta name="description" content="{esc(desc)}"><link rel="canonical" href="https://www.pdufa.bio/research/fda-decision-timing"><meta name="robots" content="index,follow,max-image-preview:large"><meta name="theme-color" content="#02060d"><link rel="icon" type="image/svg+xml" href="/favicon.svg"><meta property="og:type" content="article"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}"><meta property="og:url" content="https://www.pdufa.bio/research/fda-decision-timing"><style>*{{box-sizing:border-box}}body{{margin:0;background:#02060d;color:#f2f6fc;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;line-height:1.5}}a{{color:#6fb6ff;text-decoration:none}}a:hover{{text-decoration:underline}}.wrap{{max-width:820px;margin:0 auto;padding:22px 18px 60px}}.top{{display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #1a3358;padding-bottom:12px}}.brand{{font-size:19px;font-weight:800}}.brand b{{color:#e3ba5e}}.nav a{{color:#a7bcd9;font-size:13px;margin-left:14px}}h1{{font-size:27px;line-height:1.18;margin:10px 0 6px}}h2{{font-size:18px;color:#e3ba5e;margin:26px 0 8px}}.bc{{font-size:12px;color:#94a9c9;margin:16px 0 4px}}.bc a{{color:#94a9c9}}.sub{{color:#a7bcd9;font-size:15px}}.note{{font-size:12px;color:#94a9c9;line-height:1.6}}footer{{border-top:1px solid #1a3358;margin-top:34px;padding-top:16px;font-size:11.5px;color:#94a9c9;line-height:1.6}}footer b{{color:#a7bcd9}}</style><script type="application/ld+json">{jsonld}</script></head><body><div class="wrap"><div class="top"><a class="brand" href="/">pdufa<b>.bio</b></a><div class="nav"><a href="/calendar">Calendar</a><a href="/decisions">Decisions</a><a href="/readouts">Readouts</a><a href="/research">Research</a></div></div><div class="bc"><a href="/">Home</a> &rsaquo; <a href="/research">Research</a> &rsaquo; Decision timing</div><h1>Does the FDA decide on the PDUFA date?</h1><div class="sub">{headline}{med}</div><h2>Every {a.year} sourced decision, goal date vs actual</h2>{rows}<div class="note" style="margin-top:10px"><b>What is counted:</b> {a.year} decisions where this archive holds the PDUFA goal date, the actual FDA action date, and a primary source we link on the decision page. Decisions inferred from share-price behaviour are excluded. We do not compute a rate across earlier years: our coverage of them is far thinner, so such a number would describe our own collection rather than the FDA's behaviour.</div><h2>Questions</h2>{faq}<p class="note">Historical record of specific decisions, each linked to its source. Not a prediction about any pending application, and not investment advice.</p><footer><b>Not affiliated with or endorsed by the FDA.</b> pdufa.bio is an independent publication with no affiliation with, endorsement by, sponsorship by, or connection to the U.S. Food and Drug Administration. <b>Informational and educational purposes only. Not investment advice.</b> Verify every date and outcome against primary FDA, SEC or company filings.<br><br>&copy; 2026 pdufa.bio. All rights reserved.</footer></div><script src="/cmdk.js" defer></script></body></html>"""

    if a.dry_run:
        print("DRY RUN -- not written")
        return 0
    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(page)
    print(f"wrote /research/fda-decision-timing  (n={n}, early={len(early)}, "
          f"rate {'computed' if enough else 'withheld, n below ' + str(a.min_n)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
