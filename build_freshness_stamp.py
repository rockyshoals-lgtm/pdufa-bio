# -*- coding: utf-8 -*-
"""build_freshness_stamp.py -- make our freshness visible, because theirs is a week old.

The competitive teardown found one weakness worth more than any structural fix: the category leader
ships a badge reading "Synced 1w ago". We rebuild daily and publish decisions the same week they
happen, and nowhere on the site does a reader learn that. Freshness only beats a competitor if the
visitor can see it without opening a second tab.

So every page gets one line above the fold: when this page's data was last rebuilt, and when the
next FDA decision is.

Two things make it honest rather than decorative:

  * IT SELF-UPDATES. The stamp carries an ISO timestamp and a tiny script renders it as relative
    time at VIEW time. A baked "Updated 4 hours ago" becomes a lie the moment the page is cached,
    and a stale freshness claim is worse than none: it is a claim about honesty that is itself
    untrue. If the script does not run, the reader sees the absolute date, which cannot rot.
  * IT COUNTS FROM REAL DATA. The next-decision figure comes from the dataset's own day-precision
    catalysts, not from a hand-edited string.

    python build_freshness_stamp.py [--dry-run]
"""
import argparse, datetime as dt, glob, json, os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")
B, E = "<!--FRESH:BEGIN-->", "<!--FRESH:END-->"

SKIP = re.compile(r"(_bak|_xbak|/_|\\_|app\.html|holding\.html|preview\.html|ping\.html"
                  r"|today\.html|index_redesign)", re.I)

# The stamp's HTML is CONSTANT. Only /build-info.json carries the changing timestamp, and a script
# fetches it at view time.
#
# The first version baked the build time into all 850 pages. Two costs, and the second is worse
# than the first. Every page's content hash changed on every build, so the sitemap went straight
# back to claiming 100% of URLs changed today, which is the exact signal the lastmod work exists to
# remove. And it would have committed 850 modified files to git every single day, forever, for a
# string nobody diffs.
#
# The static fallback still has to be true on its own, because a crawler or a reader without JS
# sees only that. "Rebuilt daily" is a claim about the schedule, which is verifiable and does not
# rot; "Updated 4 hours ago" baked into a cached page becomes a lie about honesty, which is the
# worst kind to publish on a site whose whole pitch is provenance.
SCRIPT = """<script>
(function(){var e=document.querySelector('[data-fresh]');if(!e)return;
fetch('/build-info.json',{cache:'no-store'}).then(function(r){return r.json()}).then(function(j){
var d=e.querySelector('[data-fresh-next]');
var n=j.next_days;if(j.next_date){var td=new Date();var t0=Date.UTC(td.getFullYear(),td.getMonth(),td.getDate());var p=j.next_date.split('-');n=Math.round((Date.UTC(+p[0],+p[1]-1,+p[2])-t0)/86400000);}
if(d&&n!=null)d.textContent=n<=0?'today':(n===1?'tomorrow':'in '+n+' days');
var k=e.querySelector('[data-fresh-tk]');if(k&&j.next_ticker){k.textContent=j.next_ticker;k.setAttribute('href','/ticker/'+j.next_ticker)}
}).catch(function(){});})();
</script>"""


def next_decision():
    """(date, ticker, days) for the nearest day-precision PDUFA still LIVE.

    2026-08-18: BMY's goal date passed yesterday with no FDA action yet -- the board rightly
    kept it as the first tile (Awaiting; the agency can act any moment), but this function
    skipped anything past-dated, so build-info said next=CAPR 08-22 while the board led with
    BMY 08-17 and the board guard failed on the mismatch. An Awaiting event IS the next
    expected decision. Recently past-dated undecided events (<=7 days; older ones are stale
    limbo, not imminent) now count, and the badge renders 'today' for them."""
    if not os.path.exists(DATASET):
        return None
    m = re.search(r"export default (\[.*\])",
                  open(DATASET, encoding="utf-8", errors="replace").read(), re.S)
    if not m:
        return None
    today = dt.date.today()
    best = None
    for r in json.loads(m.group(1)):
        if r.get("type") != "PDUFA" or r.get("dp") != "day":
            continue
        if str(r.get("st") or "").lower() == "decided":
            continue
        d = str(r.get("d") or "")
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", d):
            continue
        dd = dt.date.fromisoformat(d)
        if dd < today - dt.timedelta(days=7):
            continue
        if best is None or dd < best[0]:
            best = (dd, (r.get("t") or "").upper())
    if not best:
        return None
    return best[0], best[1], (best[0] - today).days


LASTMOD_STATE = os.path.join(HERE, "_sitemap_lastmod.json")
MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]
_STATE = None


def content_dates():
    """page -> the date its CONTENT last changed, as computed by build_sitemap.py.

    Not the build time. A page rebuilt today whose data has not moved since Tuesday should say
    Tuesday, and a stamp that says otherwise is a false claim about the one thing this site sells.
    Using the same state file the sitemap uses also means the visible date and the <lastmod> we
    hand Google can never disagree.
    """
    global _STATE
    if _STATE is None:
        try:
            _STATE = {k: v.get("date") for k, v in
                      json.load(open(LASTMOD_STATE, encoding="utf-8")).items()}
        except Exception:
            _STATE = {}
    return _STATE


def human(iso):
    y, m, d = int(iso[:4]), int(iso[5:7]), int(iso[8:10])
    return f"{MONTHS[m - 1]} {d}, {y}"


def block(date_iso):
    """Per-page markup. The date is baked because a crawler has to see it.

    The earlier version rendered the time client-side, which was fine for humans and useless for
    the search engine we are actually winning on: Bing shows recency in the result, and the site
    that just took #1 leads with an hour stamp while ours showed nothing at all. A crawler does not
    run our fetch().

    Baking it is only safe because the date comes from the content-change state rather than the
    clock, so an unchanged page emits identical bytes on every build. That is what keeps this from
    reintroducing the churn that broke lastmod twice already.
    """
    when = (f'Updated <time datetime="{date_iso}" style="color:#eef4fc">{human(date_iso)}</time>'
            if date_iso else '<span style="color:#eef4fc">Rebuilt daily</span>')
    return (
        f'{B}<div data-fresh style="display:flex;flex-wrap:wrap;gap:6px;'
        f'align-items:center;font-size:12.5px;color:var(--mut2);margin:0 0 10px">'
        f'<span style="display:inline-flex;width:7px;height:7px;border-radius:50%;'
        f'background:#46d17f"></span>'
        f'<span>{when}</span>'
        f'<span style="color:var(--mut2)">·</span>'
        f'<span>next FDA decision <b data-fresh-next style="color:#eef4fc">on the calendar</b> '
        f'<a data-fresh-tk href="/calendar" style="color:var(--mut2)"></a></span>'
        f'</div>{SCRIPT}{E}')


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    now_iso = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    nxt = next_decision()
    dates = content_dates()

    # The ONE file that changes each build. Everything dynamic lives here.
    info = {"built": now_iso,
            "next_date": nxt[0].isoformat() if nxt else None,
            "next_ticker": nxt[1] if nxt else None,
            "next_days": nxt[2] if nxt else None}
    if not a.dry_run:
        json.dump(info, open(os.path.join(SITE, "build-info.json"), "w", encoding="utf-8"), indent=1)
    if nxt:
        print(f"next FDA decision: {nxt[1]} on {nxt[0]} ({nxt[2]} days)")

    done = 0
    for p in sorted(glob.glob(os.path.join(SITE, "**", "*.html"), recursive=True)):
        if SKIP.search(p):
            continue
        rel = os.path.relpath(p, SITE).replace("\\", "/")
        blk = block(dates.get("pdufa_site_src/" + rel))
        doc = open(p, encoding="utf-8", errors="replace").read()
        if B in doc:
            doc = doc.split(B, 1)[0] + blk + doc.split(E, 1)[1]
        else:
            # Directly under the page heading: the first thing after "what is this page".
            m = re.search(r"</h1>", doc)
            if not m:
                continue
            doc = doc[:m.end()] + blk + doc[m.end():]
        if not a.dry_run:
            open(p, "w", encoding="utf-8").write(doc)
        done += 1

    print(f"freshness stamp on {done} page(s)" + (" [dry run]" if a.dry_run else ""))


if __name__ == "__main__":
    main()
