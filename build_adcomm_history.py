# -*- coding: utf-8 -*-
"""build_adcomm_history.py -- FDA advisory committee meetings 2020-2026 from Federal Register notices (audit 4.2).

/adcomm listed 2 meetings. The order: build a historical calendar from
Odin Perfection/fda_adcom_historical_meetings_2020-2026.csv (140 Federal Register notices; columns
pub_date,title,doc_num,fr_url,abstract), parse committee and meeting date, notices only: no votes, no
company or drug (votes stay hand-sourced). Opened 2026-10-03: the CSV's abstracts are cut at 300
characters and only 4 of 140 carry the meeting date, and it holds 8 notices for 2025-2026. So the CSV
seeds the list and the Federal Register's own API supplies each notice's DATES field ("The meeting will
be held on February 26, 2020 ...") and the notices the CSV missed. Medical-device panels are left out
(this site covers drugs and biologics) and the page says so. Cancelled/postponed notices are labelled.

Writes _adcomm_fr_notices.json (cache) and a section on /adcomm between markers.

    python build_adcomm_history.py [--offline]
"""
import argparse
import csv
import datetime as dt
import html
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
CSV = os.path.join(HERE, "Odin Perfection", "fda_adcom_historical_meetings_2020-2026.csv")
CACHE = os.path.join(HERE, "_adcomm_fr_notices.json")
B, E = "<!--ADCH:BEGIN-->", "<!--ADCH:END-->"
API = "https://www.federalregister.gov/api/v1/documents"
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]
DATE_RE = re.compile(r"(" + "|".join(MONTHS) + r") (\d{1,2})(?:,? (\d{4}))?")


def get(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "pdufa.bio rockyshoals@gmail.com"}),
                                    timeout=40) as r:
            return json.load(r)
    except Exception:
        return None


def meeting_dates(text, pub):
    """All meeting days stated in the notice's DATES field (year may be stated once, at the end)."""
    out, year = [], None
    for m in reversed(list(DATE_RE.finditer(text or ""))):
        if m.group(3):
            year = int(m.group(3))
        y = year or int(pub[:4])
        try:
            out.append(dt.date(y, MONTHS.index(m.group(1)) + 1, int(m.group(2))))
        except ValueError:
            pass
    return sorted(set(out))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    a = ap.parse_args()
    cache = json.load(io.open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}
    seed = list(csv.DictReader(io.open(CSV, encoding="utf-8"))) if os.path.exists(CSV) else []
    if not a.offline:
        # the FR's own list (the CSV is a subset); then DATES for any notice we have not read
        q = {"conditions[agencies][]": "food-and-drug-administration", "conditions[type][]": "NOTICE",
             "conditions[term]": '"Notice of Meeting"', "conditions[publication_date][gte]": "2020-01-01",
             "per_page": "100", "order": "oldest"}
        fields = "&".join(f"fields[]={f}" for f in ("title", "publication_date", "document_number", "dates", "html_url"))
        page, found = 1, 0
        while page <= 15:
            j = get(f"{API}.json?{urllib.parse.urlencode(q)}&{fields}&page={page}")
            if not j:
                break
            for d in j.get("results", []):
                cache.setdefault(d["document_number"], {}).update(
                    {"title": d["title"], "pub": d["publication_date"], "dates": d.get("dates") or "",
                     "url": d.get("html_url")})
                found += 1
            if page >= (j.get("total_pages") or 1):
                break
            page += 1
            time.sleep(0.3)
        for r in seed:
            dn = r["doc_num"]
            if dn not in cache or "dates" not in cache[dn]:
                j = get(f"{API}/{dn}.json?fields[]=dates&fields[]=title&fields[]=publication_date&fields[]=html_url")
                if j:
                    cache[dn] = {"title": j["title"], "pub": j["publication_date"], "dates": j.get("dates") or "",
                                 "url": j.get("html_url") or r["fr_url"]}
                time.sleep(0.2)
        io.open(CACHE, "w", encoding="utf-8", newline="\n").write(json.dumps(cache, indent=1, sort_keys=True) + "\n")
        print(f"adcomm history: {found} FR notice(s) read from the Federal Register API; CSV seed {len(seed)}")
    meetings, skipped = [], {"device panel": 0, "not a committee meeting notice": 0, "no meeting date": 0}
    seeded = {r["doc_num"] for r in seed}
    for dn, n in cache.items():
        t = n.get("title", "")
        if not re.search(r"(Advisory Committee|Subcommittee|Panel)\b.*;\s*(Notice of Meeting|Amendment of Notice|"
                         r"Cancellation|Postponement)", t):
            skipped["not a committee meeting notice"] += 1
            continue
        if re.search(r"Medical Devices Advisory Committee|Devices Panel|Device Good Manufacturing|Tobacco", t):
            skipped["device panel"] += 1
            continue
        committee = t.split(";")[0].strip()
        status = ("cancelled" if re.search(r"Cancel", t) else "postponed" if re.search(r"Postpone", t)
                  else "amended notice" if re.search(r"Amendment of Notice", t) else "")
        ds = meeting_dates(n.get("dates"), n.get("pub", "2020-01-01"))
        if not ds and not status:
            skipped["no meeting date"] += 1
            continue
        meetings.append({"doc": dn, "committee": committee, "dates": [d.isoformat() for d in ds], "status": status,
                         "pub": n.get("pub"), "url": n.get("url") or f"https://www.federalregister.gov/d/{dn}",
                         "in_seed_csv": dn in seeded})
    meetings.sort(key=lambda m: (m["dates"][0] if m["dates"] else m["pub"]), reverse=True)
    # render
    years = {}
    for m in meetings:
        y = (m["dates"][0] if m["dates"] else m["pub"])[:4]
        years.setdefault(y, []).append(m)
    rows = []
    for y in sorted(years, reverse=True):
        rows.append(f'<h3 style="color:#e3ba5e;font-size:15px;margin:18px 0 6px">{y} &middot; {len(years[y])} notice'
                    f'{"s" if len(years[y]) != 1 else ""}</h3><table style="width:100%;border-collapse:collapse;font-size:13.5px">'
                    '<tr><th style="text-align:left">Meeting date</th><th style="text-align:left">Committee</th>'
                    '<th style="text-align:left">Federal Register notice</th></tr>')
        for m in years[y]:
            ds = m["dates"]
            when = (f"{MONTHS[int(ds[0][5:7]) - 1][:3]} {int(ds[0][8:])}, {ds[0][:4]}" if len(ds) == 1 else
                    f"{MONTHS[int(ds[0][5:7]) - 1][:3]} {int(ds[0][8:])} and {MONTHS[int(ds[-1][5:7]) - 1][:3]} "
                    f"{int(ds[-1][8:])}, {ds[-1][:4]}" if ds else "&middot;")
            st = f' <span style="color:#ff8f6b">({m["status"]})</span>' if m["status"] else ""
            rows.append(f'<tr><td style="padding:5px 4px;white-space:nowrap">{when}</td><td style="padding:5px 4px">'
                        f'{html.escape(m["committee"])}{st}</td><td style="padding:5px 4px"><a href="{html.escape(m["url"], quote=True)}" '
                        f'rel="noopener">FR {html.escape(m["doc"])}</a>, published {m["pub"]}</td></tr>')
        rows.append("</table>")
    n_all = len(meetings)
    # Audit 2026-10-04 UX P1: join each hand-sourced vote (the "Meetings & results" cards) to its FR notice
    # row, both ways, so the two July CTGTAC meetings are not listed twice unjoined.
    p = os.path.join(SITE, "adcomm", "index.html")
    doc = io.open(p, encoding="utf-8", errors="replace").read()
    voted = re.findall(r'<a class="row" href="/adcomm/([A-Z]{1,6})-(\d{4}-\d{2}-\d{2})"', doc)
    by_day = {}
    for tk, dday in voted:
        by_day.setdefault(dday, []).append(tk)
    joined = {}
    for m in meetings:
        for dday in m["dates"]:
            if dday in by_day and "Cellular" in m["committee"] and dday[:7] == "2026-07":
                joined[dday] = m
    rows2 = []
    for row in rows:
        mm = re.search(r'FR ([0-9]{4}-[0-9]+)</a>', row)
        if mm:
            for dday, m in joined.items():
                if m["doc"] == mm.group(1):
                    tks = ", ".join(f'<a href="/adcomm/{tk}-{dday}">{tk}</a>' for tk in by_day[dday])
                    row = row.replace("</td></tr>", f' &middot; vote recorded above: {tks}</td></tr>', 1)
        rows2.append(row)
    rows = rows2
    for dday, m in joined.items():
        for tk in by_day[dday]:
            pat = re.compile(r'(<a class="row" href="/adcomm/' + tk + '-' + dday + r'".*?</b>)(<!--FRJ-->.*?<!--/FRJ-->)?(</span></span></a>)', re.S)
            fr = (f'<!--FRJ--> &middot; <a href="{html.escape(m["url"], quote=True)}" rel="noopener" '
                  f'style="color:#9ec5ff">FR {html.escape(m["doc"])}</a><!--/FRJ-->')
            doc = pat.sub(lambda x: x.group(1) + fr + x.group(3), doc, count=1)
    n_voted = len(voted)
    sec = (f'{B}<h2>FDA advisory committee meetings, 2020 to 2026: {n_all} Federal Register notices</h2>'
           f'<p class="sub">Every drug and biologic advisory committee meeting the FDA announced in the Federal '
           f'Register since January 2020, with the meeting date the notice states. Notices only: which product a '
           f'meeting reviewed, and any vote, are on the FDA&#x27;s meeting page and are not restated here; votes we '
           f'cite are sourced by hand in the table above. Medical-device panels are not listed. Cancelled and '
           f'postponed meetings are marked.</p>' + "".join(rows) + E)
    new = re.sub(re.escape(B) + r".*?" + re.escape(E), "", doc, flags=re.S)
    # above the FAQ (its <h2> carries a style attribute; the bare-tag search fell through to the footer)
    # ... and OUTSIDE the FAQ's own marker block, which build_hub_faq rewrites whole every run.
    i = new.find("<!--HUBFAQ:BEGIN-->")
    if i < 0:
        mq = re.search(r"<h2[^>]*>Questions</h2>", new)
        i = mq.start() if mq else new.find('<div class="legal"')
    new = new[:i] + sec + new[i:]
    # the page is a historical record now: title and description say what it holds (one owner for the counts)
    title = f"FDA Advisory Committee Meetings 2020-2026: {n_all} Federal Register Notices, {n_voted} Votes | pdufa.bio"
    desc = (f"All {n_all} FDA drug and biologic advisory committee meetings announced in the Federal Register since "
            f"2020, each notice linked; {n_voted} with a hand-sourced vote.")
    new = re.sub(r"<title>.*?</title>", f"<title>{html.escape(title)}</title>", new, count=1, flags=re.S)
    for pat_ in (r'(<meta name="description" content=")[^"]*(")', r'(<meta property="og:description" content=")[^"]*(")',
                 r'(<meta name="twitter:description" content=")[^"]*(")'):
        new = re.sub(pat_, lambda x: x.group(1) + html.escape(desc, quote=True) + x.group(2), new, count=1)
    for pat_ in (r'(<meta property="og:title" content=")[^"]*(")', r'(<meta name="twitter:title" content=")[^"]*(")'):
        new = re.sub(pat_, lambda x: x.group(1) + html.escape(title, quote=True) + x.group(2), new, count=1)
    io.open(os.path.join(HERE, "_adcomm_counts.json"), "w", encoding="utf-8", newline="\n").write(
        json.dumps({"notices": n_all, "voted": n_voted}) + "\n")
    if new != doc:
        io.open(p, "w", encoding="utf-8", newline="").write(new)
    print(f"/adcomm history: {n_all} meeting notice(s) rendered ({sum(1 for m in meetings if m['in_seed_csv'])} "
          f"from the CSV seed); skipped {skipped}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
