# -*- coding: utf-8 -*-
"""build_sls_ownership.py -- who has crossed 5% of SELLAS, and what that does and does not mean.

Two Schedule 13G filings landed a week apart, and the activity log filed both under "plus 19 routine
filings (Form 4, S-8, 13G and similar)". A 13G is routine in form and not always routine in content:
it means a holder crossed the 5% beneficial-ownership threshold, and on a company whose whole story
is a binary Phase 3 readout, who owns 12% of it is worth stating.

It is also the easiest thing on this page to report dishonestly. Both filers here are passive index
and custodian managers, and the giveaway is in the filing itself: State Street reports ZERO sole
voting power over 7% of the company. That is mechanical ownership arriving through index inclusion
and ETF flows, not a fund taking a view on galinpepimut-S. Writing it up as institutional
accumulation would be the single most misleading true sentence available on this page.

One naming trap, checked rather than assumed: the 31 July filer is "Vanguard Capital Management
LLC", CIK 2100119. The Vanguard Group, Inc. is CIK 102909. They are different registrants. The name
is published exactly as filed with its CIK, and no affiliation is asserted either way.

Data comes from the 13G/13D primary documents on EDGAR, so every number is the filer's own.

    python build_sls_ownership.py [--dry-run]
"""
import argparse, datetime as dt, html, json, os, re, sys, time, urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
PAGE = os.path.join(SITE, "sls", "index.html")
OUT = os.path.join(HERE, "_sls_ownership.json")
CIK = "1390478"
UA = {"User-Agent": os.environ.get("SEC_USER_AGENT", "pdufa.bio (rockyshoals@gmail.com)")}
B, E = "<!--SLSOWN:BEGIN-->", "<!--SLSOWN:END-->"


def get(u, t=25):
    return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=t).read()


def one(acc):
    """Filer, shares, percent and voting split from a 13G/13D primary document."""
    nod = acc.replace("-", "")
    try:
        x = get(f"https://www.sec.gov/Archives/edgar/data/{CIK}/{nod}/primary_doc.xml").decode(
            "utf-8", "replace")
    except Exception:
        return None
    def f(tag):
        m = re.search(rf"<{tag}>([^<]*)</{tag}>", x, re.I)
        return (m.group(1) or "").strip() if m else ""
    # The accession prefix is usually the filer's CIK, but not always: an agent can file on a
    # holder's behalf, and two of these came back nameless that way. Fall back to the filing index,
    # which names the actual reporting person.
    filer_cik = nod[:10].lstrip("0")
    name = ""
    try:
        j = json.loads(get(f"https://data.sec.gov/submissions/CIK{nod[:10]}.json", 20))
        name = j.get("name") or ""
    except Exception:
        pass
    if not name:
        for tag in ("filerCompanyName", "companyConformedName", "rptOwnerName", "name"):
            v = f(tag)
            if v and "sellas" not in v.lower():
                name = v
                break
    if not name:
        try:
            idx = get(f"https://www.sec.gov/Archives/edgar/data/{CIK}/{nod}/"
                      f"{acc}-index.htm").decode("utf-8", "replace")
            for m in re.finditer(r"companyName[^>]*>\s*([^<(]{4,80})", idx):
                cand = m.group(1).strip()
                if "sellas" not in cand.lower():
                    name = cand
                    break
        except Exception:
            pass
    def num(s):
        try:
            return float(s)
        except Exception:
            return None
    return {"accession": acc, "filer": name, "filer_cik": filer_cik,
            "shares": num(f("reportingPersonBeneficiallyOwnedAggregateNumberOfShares")),
            "percent": num(f("classPercent")),
            "sole_voting": num(f("soleVotingPower")),
            "shared_voting": num(f("sharedVotingPower")),
            "url": f"https://www.sec.gov/Archives/edgar/data/{CIK}/{nod}/primary_doc.xml"}


def collect(activity):
    rows = []
    for e in activity:
        form = (e.get("form") or "").upper()
        if "13G" not in form and "13D" not in form:
            continue
        r = one(e.get("accession") or "")
        if not r or not r.get("percent"):
            continue
        r["date"] = e.get("date")
        rows.append(r)
        time.sleep(0.3)
    rows.sort(key=lambda r: (r.get("date") or ""), reverse=True)
    return rows


def current_holders(rows):
    """Latest filing per holder, and only those still at or above 5%.

    Two corrections live here. First, the same holder files amendments, so summing every filing
    double-counts: BlackRock's April 6.8% and a later amendment are one position, not two. Keep the
    most recent per filer. Second, a 13G/A reporting 4.9% or 3.7% is a holder dropping BELOW the
    threshold, which is the opposite of what a table headed "who has crossed 5%" implies. Those are
    shown separately as exits rather than folded in.
    """
    latest = {}
    for r in sorted(rows, key=lambda x: (x.get("date") or "")):
        key = (r.get("filer") or r.get("filer_cik") or "?").lower()
        latest[key] = r
    cur = [r for r in latest.values() if (r.get("percent") or 0) >= 5]
    below = [r for r in latest.values() if (r.get("percent") or 0) < 5]
    cur.sort(key=lambda r: -(r.get("percent") or 0))
    below.sort(key=lambda r: (r.get("date") or ""), reverse=True)
    return cur, below


def render(all_rows):
    rows, below = current_holders(all_rows)
    if not rows:
        return ""
    tot = sum(r["percent"] for r in rows if r.get("percent"))
    passive = all((r.get("sole_voting") or 0) < (r.get("shares") or 1) * 0.5 for r in rows)
    body = "".join(
        f'<tr><td class="lit" style="padding:7px 10px;white-space:nowrap">{html.escape(r["date"] or "")}</td>'
        f'<td style="padding:7px 10px;color:#dce7f7">{html.escape(r["filer"] or "?")}'
        f'<span style="color:var(--mut2);font-size:11.5px"> · CIK {html.escape(r["filer_cik"])}</span></td>'
        f'<td class="lit" style="padding:7px 10px;text-align:right">{r["percent"]:.2f}%</td>'
        f'<td class="lit" style="padding:7px 10px;text-align:right;color:var(--mut2)">'
        f'{int(r["shares"]):,}</td>'
        f'<td class="lit" style="padding:7px 10px;text-align:right;color:var(--mut2)">'
        f'{int(r.get("sole_voting") or 0):,}</td>'
        f'<td style="padding:7px 10px;text-align:right">'
        f'<a href="{html.escape(r["url"])}" rel="nofollow noopener">13G</a></td></tr>'
        for r in rows)

    note = (
        "Both filers are passive index and custodian managers, and the filings say so themselves: "
        "sole voting power is a small fraction of the shares held, or zero. That is ownership "
        "arriving mechanically through index inclusion and fund flows, not a manager taking a view "
        "on galinpepimut-S. It would be easy, and wrong, to describe this as institutional "
        "accumulation ahead of the readout."
        if passive else
        "Read the voting columns before drawing conclusions: sole voting power is what distinguishes "
        "an active position from custodial or index holdings.")

    return (
        f'{B}<section style="margin:26px 0">'
        f'<h2 style="font-size:17px;margin:0 0 6px">Who has crossed 5%</h2>'
        f'<p style="font-size:12.5px;color:var(--mut2);line-height:1.65;margin:0 0 10px">'
        f'Every Schedule 13G or 13D filed against SELLAS, taken from the filer\'s own document on '
        f'EDGAR. A 13G means a holder crossed the 5% beneficial-ownership threshold.</p>'
        f'<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;'
        f'font-size:13px;border:1px solid var(--line);border-radius:10px">'
        f'<thead><tr style="color:var(--mut2);text-align:left;font-size:11.5px;'
        f'text-transform:uppercase;letter-spacing:.4px">'
        f'<th style="padding:8px 10px">Filed</th><th style="padding:8px 10px">Holder</th>'
        f'<th style="padding:8px 10px;text-align:right">% of class</th>'
        f'<th style="padding:8px 10px;text-align:right">Shares</th>'
        f'<th style="padding:8px 10px;text-align:right">Sole voting</th>'
        f'<th style="padding:8px 10px;text-align:right">Filing</th></tr></thead>'
        f'<tbody>{body}</tbody></table></div>'
        f'<div style="font-size:12.5px;color:var(--mut2);line-height:1.7;margin-top:9px">'
        f'<b style="color:#eef4fc">These holders report {tot:.1f}% of the class between them.</b> '
        f'{note} Each holder is counted once, at its most recent filing, because an amendment '
        f'restates a position rather than adding to it.'
        + (f' A further {len(below)} filer(s) most recently reported BELOW 5%, which is a holding '
           f'falling under the disclosure threshold rather than a new position: '
           + ', '.join(f'{(b.get("filer") or "an undisclosed filer")} at {b["percent"]:.2f}% on '
                       f'{b.get("date")}' for b in below[:3]) + '.' if below else '')
        + f'</div></section>{E}')


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    try:
        act = json.load(open(os.path.join(HERE, "_sls_activity.json"), encoding="utf-8"))
    except Exception:
        print("no _sls_activity.json; run sls_daily.py first"); return
    events = act.get("events") if isinstance(act, dict) else act
    rows = collect(events or [])
    print(f"{len(rows)} ownership filing(s) resolved")
    for r in rows:
        print(f"   {r['date']}  {r['filer'][:38]:<40} {r['percent']:.2f}%  "
              f"sole voting {int(r.get('sole_voting') or 0):,}")

    if not a.dry_run:
        json.dump({"as_of": dt.date.today().isoformat(), "filings": rows},
                  open(OUT, "w", encoding="utf-8"), indent=1)

    block = render(rows)
    if not block or not os.path.exists(PAGE):
        return
    doc = open(PAGE, encoding="utf-8", errors="replace").read()
    if B in doc:
        doc = doc.split(B, 1)[0] + block + doc.split(E, 1)[1]
    else:
        anchor = '<div class="legal"'
        if anchor not in doc:
            anchor = "<footer"
        if anchor not in doc:
            print("no insertion point on /sls"); return
        doc = doc.replace(anchor, block + anchor, 1)
    if not a.dry_run:
        open(PAGE, "w", encoding="utf-8").write(doc)
    print("ownership block written to /sls" + (" [dry run]" if a.dry_run else ""))


if __name__ == "__main__":
    main()
