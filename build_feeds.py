# -*- coding: utf-8 -*-
"""build_feeds.py -- Atom feeds of what changes on pdufa.bio (Nov 17 2026 audit, moat move 4: "a change feed").

No FDA tracker publishes a feed, and the FDA's own CRL release has none. Two feeds, both rebuilt every run:

  /feed/decisions.xml  every FDA decision page with an outcome the FDA or the sponsor stated (approval, Complete
                       Response Letter, not approvable letter), plus every PDUFA goal-date change on
                       /pdufa-date-changes. Pages whose outcome is inferred from a price move, and noindex pages, are
                       left out. Newest 60 by the time the page first entered pdufa.bio's public repository
                       (_decision_first_recorded.json, the same ledger as each page's "first committed" line).
  /feed/crl.xml        every Complete Response Letter in the FDA's CRL release (openFDA transparency/crl), the same
                       letters as /crl: a repeat counted once, letters the FDA rescinded as issued in error left out.
                       Newest 50. Ledger _crl_first_seen.json records the run date a letter first appeared in the
                       release this script reads; letters already there when the ledger was started carry no such
                       date (null) and are dated by the letter itself.

/feed is a plain page listing both. Every hub that a feed follows gets <link rel="alternate"> in its head.

Facts only: each entry restates fields the page or the FDA record already carries, with its source. Times: the
ledger's timestamps carry their own offset (RULE 1) and are written in UTC (Z) in the feed and in Eastern on /feed.

    python build_feeds.py            # page + feeds + alternate links
    python build_feeds.py --xml-only # feeds + alternate links (late in CI, after every fixer has run on the pages)
"""
import argparse
import collections
import hashlib
import datetime as dt
import glob
import html as _html
import io
import json
import os
import re
import sys
from urllib.parse import quote as _urlq, unquote as _uq
from xml.sax.saxutils import escape as xesc
from zoneinfo import ZoneInfo

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
sys.path.insert(0, HERE)
from build_crl_facts import CSS, NAV, CORPUS, GARBLED, MON, PDF, esc, iso, parse_app, pretty  # noqa: E402
from build_crl_companies import key_of, slug_of  # noqa: E402
import build_date_changes  # noqa: E402
from refresh_provenance_counts import page_kind  # noqa: E402

BASE = "https://www.pdufa.bio"
ET = ZoneInfo("America/New_York")
UTC = dt.timezone.utc
IMPORT_CUTOFF = dt.datetime(2026, 7, 27, tzinfo=ET)      # as inject_first_recorded.py: the repository's first import
LEDGER_DEC = os.path.join(HERE, "_decision_first_recorded.json")
LEDGER_CRL = os.path.join(HERE, "_crl_first_seen.json")
OUT = os.path.join(SITE, "feed")
CR = "COMPLETE RESPONSE"
N_DEC, N_CRL = 60, 50
AB, AE = "<!--FEEDLINK:BEGIN-->", "<!--FEEDLINK:END-->"
DEC_TITLE = "pdufa.bio: FDA decisions and PDUFA date changes"
CRL_TITLE = "pdufa.bio: FDA Complete Response Letters, as the FDA releases them"
# hub page -> feeds it links as alternates
ALTS = {
    "index.html": ("decisions", "crl"),
    "decisions/index.html": ("decisions",),
    "pdufa-date-changes/index.html": ("decisions",),
    "calendar/index.html": ("decisions",),
    "crl/index.html": ("crl",),
    "crl/facts/index.html": ("crl",),
    "crl/companies/index.html": ("crl",),
    "developers/index.html": ("decisions", "crl"),
}


def z(t):
    return t.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def day_et(d):
    """A calendar date as noon Eastern (the FDA's and the sponsors' dates are US dates with no time of day; noon keeps
    the date the same in every US zone and in UTC)."""
    return dt.datetime(d.year, d.month, d.day, 12, tzinfo=ET)


def fmt_et(t):
    t = t.astimezone(ET)
    h = t.hour % 12 or 12
    return f"{MON[t.month][:3]} {t.day}, {t.year}, {h}:{t.minute:02d} {'AM' if t.hour < 12 else 'PM'} ET"


def text(s):
    return re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def fdate(s):
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})$", (s or "").strip())
    return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None


# ---------------------------------------------------------------------------------------------------- decisions
def decision_entries():
    led = json.load(io.open(LEDGER_DEC, encoding="utf-8")) if os.path.exists(LEDGER_DEC) else {}
    out = []
    for p in glob.glob(os.path.join(SITE, "fda-decision", "*", "index.html")):
        slug = os.path.basename(os.path.dirname(p))
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        if re.search(r'<meta name="robots" content="[^"]*noindex', doc):
            continue
        canon = (re.search(r'<link rel="canonical" href="([^"]+)"', doc) or [None, ""])[1]
        if canon != f"{BASE}/fda-decision/{slug}":
            continue
        if page_kind(doc) != "sourced":               # the same reading as /decisions: outcome and source on the page
            continue
        kv = {text(k): text(v) for k, v in re.findall(r'<div class="kv"><span>(.*?)</span><b[^>]*>(.*?)</b></div>', doc)}
        outcome = kv.get("Outcome", "")
        if "Unconfirmed" in outcome or "price" in outcome.lower():
            continue                                  # an outcome read from a price move is not a stated outcome
        o = outcome.lower()
        word = ("Approved" if "approv" in o and "not approv" not in o else
                "Complete Response Letter" if "crl" in o or "complete response" in o else
                "Not approvable letter" if "not approvable" in o else "")
        if not word:
            continue
        title = text((re.search(r"<title[^>]*>(.*?)</title>", doc, re.S) or [None, ""])[1])
        title = re.sub(r"\s*\|\s*pdufa\.bio\s*$", "", title)
        fda_d = fdate(kv.get("FDA decision date", ""))
        ann_d = fdate(kv.get("Announced", ""))
        ev = ann_d or fda_d
        if not ev:
            continue
        e = led.get(slug)
        first = dt.datetime.fromisoformat(e["ts"]) if e else None
        by = bool(e) and not e.get("commit")          # no commit named: the page says "by" that time, so does the feed
        if first and first.astimezone(ET) < IMPORT_CUTOFF:
            first = None                              # came in with the repository's first import: no recorded time
        v = re.search(r"<!--VERIFIED:BEGIN-->(.*?)<!--VERIFIED:END-->", doc, re.S)
        srcs = []
        scope = v.group(1) if v else ""
        if not re.search(r'href="https?://(?!(?:www\.)?pdufa\.bio)', scope):   # no verified block: the page's own sources
            scope = re.sub(r"<!--F13:BEGIN-->.*?<!--F13:END-->", "", doc, flags=re.S)
            scope = re.sub(r"<head.*?</head>|<nav.*?</nav>|<footer.*?</footer>", "", scope, flags=re.S)
        for href, lab in re.findall(r'<a href="(https?://[^"]+)"[^>]*>(.*?)</a>', scope):
            href = _html.unescape(href)
            if ("pdufa.bio" not in href and "github.com/rockyshoals-lgtm" not in href
                    and href not in [s[0] for s in srcs]):
                srcs.append((href, text(lab)))
        drug = kv.get("Drug / candidate", "")
        comp = kv.get("Company", "")
        summ = (f"{drug or title}{f', {comp}' if comp else ''}: {word}. "
                + (f"FDA action date: {pretty(fda_d)}. " if fda_d else "FDA action date: not on record. ")
                + (f"Announced: {pretty(ann_d)}." if ann_d else "")).strip()
        lines = [f"<p>{xesc(summ)}</p>"]
        if srcs:
            lines.append("<p>Sources: " + " &middot; ".join(
                f'<a href="{xesc(h, {chr(34): "&quot;"})}">{xesc(lab or h)}</a>' for h, lab in srcs[:4]) + "</p>")
        if first:
            lines.append(f"<p>First committed to pdufa.bio's public repository {'by' if by else 'on'} "
                         f"{xesc(fmt_et(first))}.</p>")
        out.append({"id": f"{BASE}/fda-decision/{slug}", "title": title or f"{drug}: {word}",
                    "link": f"{BASE}/fda-decision/{slug}", "published": day_et(ev),
                    "updated": max(first, day_et(ev)) if first else day_et(ev),
                    "summary": summ, "content": "".join(lines), "cat": word})
    for c in build_date_changes.collect_changes():
        prior, now = fdate(c["prior"]), fdate(c["now"])
        # the day the archive recorded the new date (date_history "changed"); else the row's last update. Never the
        # goal date itself, which is in the future.
        today = dt.datetime.now(ET).date()
        when = fdate(c.get("changed") or "") or fdate(c.get("ua") or "")
        when = min(when, today) if when else None
        ev = day_et(when) if when else day_et(min(now, today))
        nm = re.sub(r"\s+-\s+\(.*?\)\s*$", "", c["name"]).strip()
        days = c["days"]
        ttl = (f"{c['t']} {nm}: PDUFA goal date moved from {pretty(prior)} to {pretty(now)}")
        summ = (f"The PDUFA goal date for {nm} ({c['company'] or c['t']}) moved {abs(days)} "
                f"day{'' if abs(days) == 1 else 's'} "
                f"{'later' if days > 0 else 'earlier'}, from {pretty(prior)} to {pretty(now)}"
                + (f"; pdufa.bio recorded the new date on {pretty(when)}" if when else "") + ".")
        lines = [f"<p>{xesc(summ)}</p>"]
        if c["url"]:
            lines.append(f'<p>Source: <a href="{xesc(c["url"], {chr(34): "&quot;"})}">the announcement</a></p>')
        out.append({"id": f"tag:pdufa.bio,2026:pdufa-date-change/{c['t']}/{c['prior']}/{c['now']}", "title": ttl,
                    "link": f"{BASE}/pdufa-date-changes", "published": ev, "updated": ev, "summary": summ,
                    "content": "".join(lines), "cat": "PDUFA goal date change"})
    key = lambda x: (x["updated"], x["published"], x["id"])   # noqa: E731
    out.sort(key=key, reverse=True)
    ch = [x for x in out if x["cat"] == "PDUFA goal date change"]
    dec = [x for x in out if x["cat"] != "PDUFA goal date change"]
    # every goal-date change stays in the feed (they are few); decisions are cut to the newest N_DEC
    return sorted(dec[:N_DEC] + ch, key=key, reverse=True), len(dec), len(ch)


# --------------------------------------------------------------------------------------------------------- CRLs
def crl_letters(include_rescinded=False, corpus=None):
    raw = json.load(io.open(corpus or CORPUS, encoding="utf-8"))
    recs = raw.get("results") if isinstance(raw, dict) else raw
    last_updated = str((raw.get("meta") or {}).get("last_updated") or "") if isinstance(raw, dict) else ""
    seen, letters, rescinds = set(), [], []
    for r in recs:
        d = iso(r.get("letter_date"))
        typ = str(r.get("letter_type") or "")
        apps = [x for x in (parse_app(a) for a in (r.get("application_number") or [])) if x]
        if d and "RESCIND" in typ.upper():
            rescinds.append({"date": d, "apps": apps, "text": re.sub(r"\s+", " ", str(r.get("text") or ""))})
        if not d or typ != CR:
            continue
        appn = tuple(sorted(str(x).strip() for x in (r.get("application_number") or [])))
        txt = re.sub(r"\s+", " ", str(r.get("text") or "")).strip().lower()
        k = (d, appn, txt)
        if k in seen:                                 # the same repeat rule as /crl
            continue
        seen.add(k)
        fn = str(r.get("file_name") or "").strip()
        nm = re.sub(r"\s+", " ", str(r.get("company_name") or "")).strip()
        letters.append({"date": d, "file": fn, "name": nm, "apps": apps, "app_txt": ", ".join(appn),
                        "key": f"{fn}|{d.isoformat()}|{','.join(appn)}|{hashlib.sha1(txt.encode('utf-8')).hexdigest()[:8]}",
                        "rescinded": False,
                        "url": PDF + _urlq(fn) if fn.lower().endswith(".pdf") else "",
                        "ckey": key_of(nm) if nm and not GARBLED.search(nm) else "",
                        "status": str(r.get("approval_status") or "").strip(), "resc_date": None})
    for R in rescinds:                                # letters the FDA rescinded as issued in error (as /crl/facts)
        m = re.search(r"refer to our letters? dated (.{0,120}?)(?:,? informing|\.)", R["text"], re.I)
        for ds in re.findall(r"(?:" + "|".join(MON[1:]) + r") \d{1,2}, \d{4}", m.group(1) if m else ""):
            vd = dt.datetime.strptime(ds, "%B %d, %Y").date()
            for L in letters:
                if L["date"] == vd and set(L["apps"]) & set(R["apps"]):
                    L["rescinded"], L["resc_date"] = True, R["date"]
    live = [L for L in letters if not L["rescinded"]]
    return (letters if include_rescinded else live), last_updated, len(letters) - len(live)


def crl_entries(today):
    letters, last_updated, n_resc = crl_letters()
    if os.path.exists(LEDGER_CRL):
        led = json.load(io.open(LEDGER_CRL, encoding="utf-8"))
        for L in letters:
            led.setdefault(L["key"], today.isoformat())     # first run that saw this letter in the release
    else:                                                    # starting the ledger: no first-seen claim for these
        led = {L["key"]: None for L in letters}
        led["_started"] = today.isoformat()
    io.open(LEDGER_CRL, "w", encoding="utf-8").write(json.dumps(led, indent=0, sort_keys=True) + "\n")
    ours = {}
    for p in glob.glob(os.path.join(SITE, "fda-decision", "*", "index.html")):
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        if re.search(r'<meta name="robots" content="[^"]*noindex', doc):
            continue
        m = re.search(r'<!--CRLSRC:BEGIN-->.*?href="https://download\.open\.fda\.gov/crl/([^"]+)"', doc, re.S)
        if m:
            ours.setdefault(_uq(m.group(1)), []).append(os.path.basename(os.path.dirname(p)))
    files = collections.Counter(L["file"] for L in letters)
    out = []
    for L in letters:
        fs = led.get(L["key"])
        fsd = fdate(fs) if fs else None
        link, where = f"{BASE}/crl", "/crl"
        if files[L["file"]] == 1 and len(ours.get(L["file"], [])) == 1:
            link, where = f"{BASE}/fda-decision/{ours[L['file']][0]}", "our decision page"
        else:
            slug = slug_of(L["ckey"]) if L["ckey"] else ""
            if slug and os.path.exists(os.path.join(SITE, "crl", "company", slug, "index.html")):
                link, where = f"{BASE}/crl/company/{slug}", "the company's CRL page"
        who = L["name"] if L["name"] and not GARBLED.search(L["name"]) else "company name not printed"
        ttl = f"Complete Response Letter, {L['app_txt'] or 'application not printed'}: {who}, {pretty(L['date'])}"
        summ = (f"The FDA's Complete Response Letter to {who} on {L['app_txt'] or 'an application it did not print'}, "
                f"dated {pretty(L['date'])}, from the FDA's CRL release (openFDA, last updated {last_updated}).")
        lines = [f"<p>{xesc(summ)}</p>"]
        if L["url"]:
            lines.append(f'<p>The letter: <a href="{xesc(L["url"], {chr(34): "&quot;"})}">FDA PDF</a></p>')
        if fsd:
            lines.append(f"<p>First in the release pdufa.bio reads on {xesc(pretty(fsd))} (Eastern date).</p>")
        upd = day_et(fsd) if fsd else day_et(L["date"])
        out.append({"id": f"tag:pdufa.bio,2026:crl/{_urlq(L['key'], safe='')}", "title": ttl, "link": link,
                    "related": L["url"], "published": day_et(L["date"]), "updated": upd, "summary": summ,
                    "content": "".join(lines), "cat": "Complete Response Letter"})
    out.sort(key=lambda x: (x["updated"], x["published"], x["id"]), reverse=True)
    return out[:N_CRL], len(out), last_updated, n_resc, led.get("_started") or today.isoformat()


# --------------------------------------------------------------------------------------------------------- Atom
def atom(name, title, subtitle, entries):
    upd = max((e["updated"] for e in entries), default=dt.datetime.now(UTC))
    q = {'"': "&quot;"}
    x = ['<?xml version="1.0" encoding="utf-8"?>',
         '<feed xmlns="http://www.w3.org/2005/Atom" xml:lang="en">',
         f"<title>{xesc(title)}</title>", f"<subtitle>{xesc(subtitle)}</subtitle>",
         f"<id>{BASE}/feed/{name}.xml</id>",
         f'<link rel="self" type="application/atom+xml" href="{BASE}/feed/{name}.xml"/>',
         f'<link rel="alternate" type="text/html" href="{BASE}/feed"/>',
         f"<updated>{z(upd)}</updated>", "<author><name>pdufa.bio</name><uri>https://www.pdufa.bio</uri></author>",
         "<rights>Facts from FDA and sponsor documents, each linked. Not investment advice.</rights>"]
    for e in entries:
        x += ["<entry>", f"<id>{xesc(e['id'])}</id>", f"<title>{xesc(e['title'])}</title>",
              f'<link rel="alternate" type="text/html" href="{xesc(e["link"], q)}"/>']
        if e.get("related"):
            x.append(f'<link rel="related" type="application/pdf" href="{xesc(e["related"], q)}"/>')
        x += [f"<published>{z(e['published'])}</published>", f"<updated>{z(e['updated'])}</updated>",
              f'<category term="{xesc(e["cat"], q)}"/>']
        x += [f"<summary>{xesc(e['summary'])}</summary>", f'<content type="html">{xesc(e["content"])}</content>',
              "</entry>"]
    x.append("</feed>")
    return "\n".join(x) + "\n"


def alt_links(names):
    t = {"decisions": DEC_TITLE, "crl": CRL_TITLE}
    return AB + "".join(f'<link rel="alternate" type="application/atom+xml" title="{esc(t[n])}" '
                        f'href="{BASE}/feed/{n}.xml">' for n in names) + AE


def inject_alternates():
    n = 0
    for rel, names in ALTS.items():
        p = os.path.join(SITE, rel)
        if not os.path.exists(p):
            continue
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        doc2 = re.sub(re.escape(AB) + ".*?" + re.escape(AE), "", doc, flags=re.S)
        if "</head>" not in doc2:
            continue
        doc2 = doc2.replace("</head>", alt_links(names) + "</head>", 1)
        if doc2 != doc:
            io.open(p, "w", encoding="utf-8").write(doc2)
            n += 1
    return n


def span(k, v):
    return f'<span data-feed="{k}">{esc(str(v))}</span>'


def counts(dec, n_dec, n_ch, crl, n_crl, last_updated, n_resc, started):
    nd = dec[0] if dec else None
    nc = crl[0] if crl else None
    return {"n_dec": n_dec, "n_ch": n_ch, "n_crl": n_crl, "n_crl_all": n_crl + n_resc, "n_resc": n_resc,
            "last_updated": last_updated, "started": pretty(fdate(started)) if fdate(started) else started,
            "newest_dec": nd["title"] if nd else "none", "newest_crl": nc["title"] if nc else "none"}


def page(dec, n_dec, n_ch, crl, n_crl, last_updated, n_resc, started):
    c = counts(dec, n_dec, n_ch, crl, n_crl, last_updated, n_resc, started)
    title = "FDA Decision and CRL Feeds (Atom) | pdufa.bio"
    desc = ("Two free Atom feeds: every sourced FDA decision and PDUFA date change on pdufa.bio, and every Complete "
            "Response Letter the FDA releases.")
    B = ['<h1>Feeds: <span class="g">FDA decisions and CRLs, as they land</span></h1>',
         '<p class="sub">Two Atom feeds, rebuilt with the site on every run. Paste either address into a feed reader. '
         'Each entry restates what the page or the FDA record says, with its source linked. Free, no key, no '
         'sign-up. Facts only: no predictions, no advice.</p>',
         '<table><tr><th>Feed</th><th>What is in it</th><th>Newest entry</th></tr>',
         '<tr><td><a href="/feed/decisions.xml">/feed/decisions.xml</a></td><td>Every FDA decision page whose outcome '
         f'the FDA or the sponsor stated, with its source on the page ({span("n_dec", c["n_dec"])} today; pages whose '
         'outcome is read only from a price move are left out), and every PDUFA goal-date change on '
         f'<a href="/pdufa-date-changes">/pdufa-date-changes</a> ({span("n_ch", c["n_ch"])}). The newest {N_DEC} '
         f'decisions and every date change are in the feed.</td><td>{span("newest_dec", c["newest_dec"])}</td></tr>',
         '<tr><td><a href="/feed/crl.xml">/feed/crl.xml</a></td><td>Complete Response Letters from the FDA\'s CRL '
         f'release (openFDA, last updated {span("last_updated", c["last_updated"])}): it holds '
         f'{span("n_crl_all", c["n_crl_all"])} distinct letters, a repeat counted once, the same letters as '
         f'<a href="/crl">/crl</a>. The feed leaves out the {span("n_resc", c["n_resc"])} the FDA rescinded as issued '
         f'in error, which leaves {span("n_crl", c["n_crl"])}; each entry links the FDA\'s PDF. The newest {N_CRL} '
         f'are in the feed.</td><td>{span("newest_crl", c["newest_crl"])}</td></tr></table>',
         '<h2>How the entries are dated</h2>',
         '<p class="sub">A decision entry is published on its announcement date (or the FDA\'s action date when no '
         'announcement is on record). It is updated at the time the page first entered pdufa.bio\'s public '
         'repository, the time its "first committed" line states; pages that came in with the repository\'s first '
         'import (July 2026) have no such time and are dated by the announcement alone. A goal-date change is dated by '
         'the day pdufa.bio recorded the new date. A CRL entry is published on the letter\'s date; a letter that '
         f'first appears in the FDA\'s release after {span("started", c["started"])} is updated on the day pdufa.bio '
         'first read it there, so a reader that sorts by updated time sees a newly released old letter as new. '
         'Dates with no time of day are written as noon Eastern. Feed times are UTC; dates on this page are '
         'Eastern.</p>',
         '<p class="sub">The same data, whole, is in the <a href="/developers">API</a>, the '
         '<a href="/calendar.ics">calendar file</a> and the <a href="/crl/facts">CRL data download</a>.</p>']
    body = "\n".join(B)
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{esc(title)}</title><meta name="description" content="{esc(desc)}">'
            f'<link rel="canonical" href="{BASE}/feed">'
            f'<meta name="robots" content="index,follow"><style>{CSS}</style></head><body>{NAV}'
            f'<main class="wrap">{body}</main></body></html>\n')


def refresh_counts(c):
    """--xml-only: rewrite only the counted spans on the built /feed page, so every fixer's later work on it stays."""
    p = os.path.join(OUT, "index.html")
    if not os.path.exists(p):
        return False
    doc = io.open(p, encoding="utf-8").read()
    doc2 = doc
    for k, v in c.items():
        doc2 = re.sub(r'(<span data-feed="' + k + r'">).*?(</span>)', lambda m: m.group(1) + esc(str(v)) + m.group(2),
                      doc2, flags=re.S)
    if doc2 != doc:
        io.open(p, "w", encoding="utf-8").write(doc2)
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--xml-only", action="store_true")
    a = ap.parse_args()
    today = dt.datetime.now(ET).date()
    dec, n_dec, n_ch = decision_entries()
    crl, n_crl, last_updated, n_resc, started = crl_entries(today)
    os.makedirs(OUT, exist_ok=True)
    io.open(os.path.join(OUT, "decisions.xml"), "w", encoding="utf-8").write(atom(
        "decisions", DEC_TITLE, "Every FDA decision whose outcome the FDA or the sponsor stated, and every PDUFA goal-"
        "date change pdufa.bio recorded, each with its source.", dec))
    io.open(os.path.join(OUT, "crl.xml"), "w", encoding="utf-8").write(atom(
        "crl", CRL_TITLE, f"Complete Response Letters in the FDA's CRL release (openFDA, last updated {last_updated}), "
        "each linking the FDA's PDF.", crl))
    args = (dec, n_dec, n_ch, crl, n_crl, last_updated, n_resc, started)
    if not a.xml_only or not refresh_counts(counts(*args)):
        io.open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(page(*args))
    n = inject_alternates()
    print(f"  feeds: decisions {len(dec)} of {n_dec} + {n_ch} date changes, crl {len(crl)} of {n_crl}; alternates on {n} pages")


if __name__ == "__main__":
    main()
