# -*- coding: utf-8 -*-
"""build_conferences.py -- own /conferences from data, and stop promising presenters we do not have.

Two defects on the live page, and the second is the one that matters.

1. COVERAGE. It listed 14 conferences and stopped on 15 December 2026. A conference calendar with no
   2027 in it goes stale on its own, silently, in a few months. It also omitted a dozen H2 2026
   meetings where biotechs report real data: ERS, ASTRO, AHA, SNO, ObesityWeek, ENA, ESMO Asia,
   ESMO IO, ACG, AAO, ASBMR, ACAAI and World Muscle Society.

2. THE PROMISE IT COULD NOT KEEP. The page's own subtitle offered "the small/mid-cap names
   presenting", and then printed "0 presenters" against every single conference. That is worse than
   omitting the feature: it tells a reader that no biotech is presenting at ESMO, which is plainly
   false. The cause is not a bug in the matcher so much as a fact about the world: abstract titles
   are embargoed until a few weeks before most meetings, so in early August there is very little
   forward presenter data to have.

   So the page now says which of those two situations it is in. Where we can source presenters, they
   are listed with the filing or release they came from. Where the organiser has not released the
   programme yet, the page says so and says when it usually lands, instead of printing a zero that
   reads as an absence of interest.

Dates come from conferences.json, each row carrying the organiser URL it was verified against.
Nothing here is estimated: a conference whose dates the organiser has not published is listed under
"not yet announced" rather than given a plausible-looking date.

    python build_conferences.py [--dry-run]
"""
import argparse, csv, datetime as dt, html, json, os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
DATA = os.path.join(HERE, "conferences.json")
PRES = os.path.join(HERE, "catalysts_out", "conference_presentations_history.csv")
MINED = os.path.join(HERE, "catalysts_out", "conference_presenters_mined.csv")
OUT = os.path.join(SITE, "conferences", "index.html")
BEGIN, END = "<!--CONFLIST:BEGIN-->", "<!--CONFLIST:END-->"

# How far before a meeting a company's own announcement still counts as being about that meeting.
LOOKBACK_DAYS = 150


def esc(s):
    return html.escape(str(s or ""), quote=True)


def pretty(start, end):
    a = dt.date.fromisoformat(start)
    b = dt.date.fromisoformat(end)
    if a.month == b.month:
        return f"{a.strftime('%b')} {a.day} to {b.day}, {a.year}"
    return f"{a.strftime('%b')} {a.day} to {b.strftime('%b')} {b.day}, {a.year}"


def load_presenters():
    """conference code -> [rows], from both sourced presenter files.

    Two sources, same discipline. The history file is the curated set. The mined file is what
    companies have said in their own SEC filings, which is usually months ahead of the organiser
    publishing a programme, and is the only reason this page can name anyone at all before abstract
    titles drop.
    """
    # THE GATE (red team 2026-08-12c section 3): of 102 raw mined rows, fewer than 10% were
    # about an upcoming conference -- 10-Ks recite history, and the name-only matcher filed
    # January-2026 data under 2027 editions. Publishing the raw file would put ~93 false
    # statements on pages titled 'Biotech Presenters'. So: the hand-verified file publishes
    # as-is (each row carries a reviewer note), and MINED rows publish ONLY with
    # confidence == 'high' (edition-anchored + forward-committed + verb-proximate + event
    # filing + ticker, per the 3.5 spec now implemented in the miner). Legacy mined rows have
    # no confidence column and are therefore excluded by construction.
    out = {}
    verified = os.path.join(HERE, "catalysts_out",
                            "conference_presenters_VERIFIED_2026-08-12.csv")
    for path, dated, gate in ((PRES, "catalyst_date", False),
                              (verified, "conf_start", False),
                              (MINED, "conf_start", True)):
        if not os.path.exists(path):
            continue
        for r in csv.DictReader(open(path, encoding="utf-8-sig", errors="replace")):
            code = (r.get("conference") or "").strip()
            if not code:
                continue
            if gate and (r.get("confidence") or "").strip().lower() != "high":
                continue
            # Normalise the schemas onto the fields the renderer uses.
            r.setdefault("catalyst_date", r.get(dated) or "")
            if not r.get("catalyst_date"):
                r["catalyst_date"] = r.get(dated) or ""
            r["source_url"] = r.get("source_url") or r.get("filing_url") or ""
            out.setdefault(code.upper(), []).append(r)
    return out


def presenters_for(conf, by_code):
    """Rows plausibly about THIS instance of the meeting: right code, and dated inside a window
    ending at the meeting's close. Without the window an ASCO 2023 row would be published as an
    ASCO 2027 presenter."""
    rows = by_code.get(conf["code"].upper(), [])
    start = dt.date.fromisoformat(conf["start"])
    lo = (start - dt.timedelta(days=LOOKBACK_DAYS)).isoformat()
    hi = conf["end"]
    keep, seen = [], set()
    for r in rows:
        d = (r.get("catalyst_date") or "")[:10]
        if not (lo <= d <= hi):
            continue
        # Identify by ticker where we have one, else by company name. Requiring a ticker silently
        # dropped every mined row whose SEC display name did not carry one, which is most large
        # caps, and would have made the page look emptier than the evidence we hold.
        t = (r.get("ticker") or "").upper()
        ident = t or (r.get("company") or "").strip().lower()
        if not ident or ident in seen:
            continue
        seen.add(ident)
        keep.append(r)
    return sorted(keep, key=lambda r: (r.get("ticker") or r.get("company") or "").upper())


def render(data, by_code, today):
    confs = [c for c in data["conferences"] if c["end"] >= today]
    confs.sort(key=lambda c: c["start"])

    n_pres = 0
    cards = []
    for c in confs:
        pres = presenters_for(c, by_code)
        n_pres += len(pres)
        days = (dt.date.fromisoformat(c["start"]) - dt.date.fromisoformat(today)).days

        if pres:
            body = ('<div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:9px">' + "".join(
                f'<a href="/ticker/{esc(r["ticker"])}" style="display:inline-flex;gap:6px;'
                f'align-items:baseline;padding:5px 9px;border:1px solid var(--line);'
                f'border-radius:8px;text-decoration:none;font-size:12.5px">'
                f'<b class="lit" style="color:#f0c86a">{esc(r["ticker"] or (r.get("company") or "")[:14])}</b>'
                f'<span style="color:var(--mut2)">{esc((r.get("drug") or r.get("pres_type") or "")[:34])}</span></a>'
                for r in pres[:24]) + '</div>'
                f'<div style="font-size:11.5px;color:var(--mut2);margin-top:7px">'
                f'{len(pres)} company presentation(s) we can source to a filing or company release. '
                f'This is not the full programme.</div>')
        else:
            body = ('<div style="font-size:12.5px;color:var(--mut2);margin-top:8px;line-height:1.65">'
                    'Presenter list not published yet. Organisers usually release abstract titles a '
                    'few weeks before the meeting, and we only name a company once its own filing or '
                    'release says it is presenting. We do not estimate this.</div>')

        cards.append(
            f'<div style="border:1px solid var(--line);border-radius:12px;padding:13px 15px;'
            f'margin:0 0 11px;background:var(--card)">'
            f'<div style="display:flex;flex-wrap:wrap;gap:8px;align-items:baseline;'
            f'justify-content:space-between">'
            f'<div><b class="lit" style="color:#eef4fc;font-size:15px">{esc(c["code"])}</b> '
            f'<span style="color:#dce7f7;font-size:14px">{esc(c["name"])}</span></div>'
            f'<div class="lit" style="font-size:12.5px;color:var(--mut2)">'
            f'{esc(pretty(c["start"], c["end"]))}'
            + (f' · in {days} days' if 0 <= days <= 120 else '') + '</div></div>'
            f'<div style="font-size:12.5px;color:var(--mut2);margin-top:3px">'
            f'{esc(c["city"])} · {esc(c["focus"])} · '
            f'<a href="{esc(c["source"])}" rel="nofollow noopener">official site</a></div>'
            f'{body}</div>')

    una = "".join(
        f'<li><b>{esc(u["code"])}</b> {esc(u["name"])}. {esc(u["why"])} '
        f'<a href="{esc(u["source"])}" rel="nofollow noopener">source</a></li>'
        for u in data.get("_unannounced", []))
    una_block = (f'<div style="margin-top:16px;padding-top:12px;border-top:1px solid var(--line)">'
                 f'<div style="font-size:13px;color:#eef4fc;font-weight:600;margin-bottom:5px">'
                 f'Announced but undated</div>'
                 f'<ul style="font-size:12.5px;color:var(--mut2);line-height:1.7;'
                 f'padding-left:18px;margin:0">{una}</ul></div>') if una else ""

    ld = {"@context": "https://schema.org", "@type": "ItemList",
          "name": "Biotech medical conference calendar",
          "numberOfItems": len(confs),
          "itemListElement": [
              {"@type": "ListItem", "position": i + 1,
               "item": {"@type": "Event", "name": f'{c["name"]} ({c["code"]})',
                        "startDate": c["start"], "endDate": c["end"],
                        "eventStatus": "https://schema.org/EventScheduled",
                        "eventAttendanceMode":
                            "https://schema.org/OfflineEventAttendanceMode",
                        "location": {"@type": "Place", "name": c["city"],
                                     "address": c["city"]},
                        "url": c["source"]}}
              for i, c in enumerate(confs)]}

    head = (f'<div style="font-size:12.5px;color:var(--mut2);line-height:1.7;margin:0 0 14px">'
            f'{len(confs)} upcoming conferences where biotech companies report clinical data, '
            f'through {pretty(confs[-1]["start"], confs[-1]["end"]).split(", ")[-1]}. '
            f'Every date is taken from the organiser\'s own site, linked on each row. '
            f'Where a meeting has announced itself but not its dates, it is listed at the bottom '
            f'rather than given a plausible-looking date.</div>')

    return (BEGIN + head + "".join(cards) + una_block +
            f'<script type="application/ld+json">{json.dumps(ld, separators=(",", ":"))}</script>'
            + END), len(confs), n_pres


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    data = json.load(open(DATA, encoding="utf-8"))
    by_code = load_presenters()
    today = dt.date.today().isoformat()

    block, n_conf, n_pres = render(data, by_code, today)

    doc = open(OUT, encoding="utf-8", errors="replace").read()
    if BEGIN in doc:
        doc = doc.split(BEGIN, 1)[0] + block + doc.split(END, 1)[1]
    else:
        # Replace everything from the old list marker down to the legal footer, so the stale
        # hand-built list does not survive alongside the generated one.
        m = re.search(r"<h2[^>]*>\s*H2 2026 conferences\s*</h2>", doc)
        anchor = '<div class="legal"'
        if m and anchor in doc:
            doc = doc[:m.start()] + block + doc[doc.index(anchor):]
        elif anchor in doc:
            doc = doc.replace(anchor, block + anchor, 1)
        else:
            print("no insertion point on /conferences"); return

    # The old subtitle promised presenter lists the page could not deliver.
    doc = doc.replace(
        "dates, location, therapeutic focus, and the small/mid-cap names presenting",
        "dates, location, therapeutic focus, and any presenting companies we can source")
    # The audit's honest-and-quotable sentence (2026-08-12c section 3.7): say where the
    # presenter list comes from and what it is not. Idempotent via the marker.
    DISC = ('<!--PRESDISC--><p style="font-size:12.5px;opacity:.75;max-width:74ch">'
            'The presenter list is built from companies\' own SEC filings and press releases, '
            'each row linking the document it came from. It is not the organiser\'s programme: '
            'abstract titles are embargoed until close to most meetings, so absence here is '
            'not absence of presentations.</p>')
    if "PRESDISC" not in doc:
        doc = doc.replace(BEGIN, DISC + BEGIN, 1)

    if not a.dry_run:
        open(OUT, "w", encoding="utf-8").write(doc)
    print(f"conferences: {n_conf} upcoming through {data['conferences'][-1]['start'][:4]}, "
          f"{n_pres} sourced presenter row(s), "
          f"{len(data.get('_unannounced', []))} announced but undated"
          + (" [dry run]" if a.dry_run else ""))


if __name__ == "__main__":
    main()
