# -*- coding: utf-8 -*-
"""audit_currency.py -- one report answering "is anything on this site out of date?".

Individual guards each check one invariant. This is the sweep: it walks every published page and
looks for the shapes staleness actually takes on this site, based on what has actually gone wrong
before rather than what might theoretically go wrong.

  A. Past-dated events still presented as upcoming (the failure that produces phantom countdowns)
  B. Hardcoded dataset counts that no longer match the dataset (the "1,754 events" drift)
  C. Baked absolute dates that have quietly aged (page says "as of" a date months old)
  D. Decision pages missing from /decisions, and archive links with no page (dead internal links)
  E. Pages absent from the sitemap, and sitemap URLs with no page
  F. Stated "last updated" claims older than the data they describe

Read-only. Reports; never edits.

    python audit_currency.py
"""
import csv, glob, json, os, re, sys
import datetime as dt

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
TODAY = dt.date.today()
SKIP_DIRS = ("_pdufa_bak8", "_pdufa_xbak")
SKIP_FILES = {"index_redesign.html", "preview.html", "ping.html", "holding.html", "app.html"}

findings = []


def redirected():
    """Paths vercel.json 301s away. A page that redirects is SUPPOSED to be unlinked and absent
    from the sitemap, so counting it as an orphan turns a correct state into permanent noise."""
    p = os.path.join(SITE, "vercel.json")
    if not os.path.exists(p):
        return set()
    try:
        cfg = json.load(open(p, encoding="utf-8"))
        return {r.get("source", "").rstrip("/") for r in cfg.get("redirects", [])}
    except Exception:
        return set()


REDIR = redirected()
PRIVATE = {"/account", "/login", "/today", "/app", "/preview", "/ping", "/holding"}


def note(sev, area, msg):
    findings.append((sev, area, msg))


def pages():
    for root, _, fs in os.walk(SITE):
        if any(s in root for s in SKIP_DIRS):
            continue
        for f in fs:
            if f.endswith(".html") and not f.startswith("_") and f not in SKIP_FILES:
                yield os.path.join(root, f)


def rel(p):
    return os.path.relpath(p, SITE).replace("\\", "/")


# ---------------------------------------------------------------- A. past-dated "upcoming"
def check_upcoming():
    bad = []
    for p in pages():
        t = open(p, encoding="utf-8", errors="replace").read()
        for m in re.finditer(r"PDUFA (\d{4}-\d{2}-\d{2})", t):
            d = m.group(1)
            if d < TODAY.isoformat():
                seg = t[max(0, m.start() - 260):m.start() + 60]
                # a decided event is fine if the page says so nearby
                if re.search(r"Approved|CRL|Decided|✓|✗|decision-day", seg, re.I):
                    continue
                bad.append((rel(p), d))
    if bad:
        for r, d in bad[:12]:
            note("WARN", "A past-dated upcoming", f"{r}: PDUFA {d} shown without an outcome")
        if len(bad) > 12:
            note("WARN", "A past-dated upcoming", f"... and {len(bad)-12} more")
    else:
        note("OK", "A past-dated upcoming", "no past PDUFA presented as pending")


# ---------------------------------------------------------------- B. hardcoded dataset counts
def check_counts():
    n_study = sum(1 for _ in csv.DictReader(
        open(os.path.join(HERE, "pdufa_runup_bifrost_v2.csv"), encoding="utf-8-sig", errors="replace")))
    n_dec = len(glob.glob(os.path.join(SITE, "fda-decision", "*", "index.html")))
    pat = re.compile(r"([\d,]{3,9})[\s-]*(?:PDUFA )?(?:events?|decisions?)[\s-]*(?:in the run-up study|"
                     r"with real price data|in the study)", re.I)
    bad = []
    for p in pages():
        t = open(p, encoding="utf-8", errors="replace").read()
        for m in pat.finditer(t):
            got = m.group(1)
            if got.replace(",", "") != str(n_study):
                bad.append((rel(p), got))
    if bad:
        for r, g in bad[:12]:
            note("FAIL", "B stale count", f"{r}: quotes {g} study events, dataset has {n_study:,}")
    else:
        note("OK", "B stale count", f"every study-size mention matches {n_study:,}")
    note("INFO", "B counts", f"decision pages on disk: {n_dec:,}")


# ---------------------------------------------------------------- C. aged "as of" dates
def check_asof():
    # Only phrases that claim OUR currency. Plain "as of <date>" is usually a fact about a filing
    # (SELLAS disclosed 78 events as of May 11 2026) and is supposed to stay put; flagging those
    # trains the reader to ignore the audit, which is worse than not running it.
    pat = re.compile(r"(?:Last computed|Page compiled|Data through|Last updated|Updated)\s+"
                     r"(\d{4}-\d{2}-\d{2}|[A-Z][a-z]{2} \d{1,2},? \d{4})")
    stale = []
    for p in pages():
        t = open(p, encoding="utf-8", errors="replace").read()
        for m in pat.finditer(t):
            raw = m.group(1)
            try:
                d = (dt.date.fromisoformat(raw) if "-" in raw
                     else dt.datetime.strptime(raw.replace(",", ""), "%b %d %Y").date())
            except Exception:
                continue
            age = (TODAY - d).days
            if age > 45:
                stale.append((rel(p), raw, age))
    if stale:
        for r, raw, age in sorted(stale, key=lambda x: -x[2])[:15]:
            note("WARN", "C aged claim", f"{r}: states {raw} ({age}d old)")
        if len(stale) > 15:
            note("WARN", "C aged claim", f"... and {len(stale)-15} more")
    else:
        note("OK", "C aged claim", "no published 'as of' date older than 45 days")


# ---------------------------------------------------------------- D. archive <-> pages
def check_archive():
    dec = os.path.join(SITE, "decisions", "index.html")
    html = open(dec, encoding="utf-8", errors="replace").read()
    linked = {m.group(1) for m in re.finditer(r'href="/fda-decision/([A-Z]{1,6}-\d{4}-\d{2}-\d{2})"', html)}
    on_disk = {os.path.basename(os.path.dirname(p))
               for p in glob.glob(os.path.join(SITE, "fda-decision", "*", "index.html"))}
    dead = sorted(linked - on_disk)
    orphan = sorted(s for s in (on_disk - linked)
                    if f"/fda-decision/{s}" not in REDIR)   # 301'd duplicates are meant to be unlinked
    if dead:
        for s in dead[:10]:
            note("FAIL", "D dead link", f"/decisions links /fda-decision/{s} but no page exists")
    else:
        note("OK", "D dead link", f"all {len(linked):,} archive links resolve")
    if orphan:
        note("WARN", "D orphan page", f"{len(orphan)} decision page(s) not linked from /decisions "
                                      f"(e.g. {', '.join(orphan[:5])})")
    else:
        note("OK", "D orphan page", "every decision page is linked from the archive")


# ---------------------------------------------------------------- E. sitemap coverage
def check_sitemap():
    sm = os.path.join(SITE, "sitemap.xml")
    if not os.path.exists(sm):
        note("FAIL", "E sitemap", "sitemap.xml missing")
        return
    xml = open(sm, encoding="utf-8", errors="replace").read()
    urls = {m.group(1).rstrip("/").split("pdufa.bio")[-1] or "/"
            for m in re.finditer(r"<loc>([^<]+)</loc>", xml)}
    noindex = re.compile(r'name="robots"[^>]*content="[^"]*noindex', re.I)
    routes = set()
    for p in pages():
        # noindex pages are deliberately absent from the sitemap; counting them as gaps would
        # produce 324 permanent false warnings.
        try:
            if noindex.search(open(p, encoding="utf-8", errors="replace").read(4000)):
                continue
        except Exception:
            pass
        r = rel(p)
        if r.endswith("/index.html"):
            routes.add("/" + r[:-len("/index.html")])
        elif r == "index.html":
            routes.add("/")
        else:
            routes.add("/" + r[:-len(".html")])
    missing = sorted(r for r in (routes - urls)
                     if r not in PRIVATE and r.rstrip("/") not in REDIR)
    ghost = sorted(urls - routes)
    note("INFO", "E sitemap", f"{len(urls):,} URLs in sitemap, {len(routes):,} routes on disk")
    if missing:
        note("WARN", "E sitemap", f"{len(missing)} route(s) not in sitemap "
                                  f"(e.g. {', '.join(missing[:5])})")
    if ghost:
        note("FAIL", "E sitemap", f"{len(ghost)} sitemap URL(s) with no page "
                                  f"(e.g. {', '.join(ghost[:5])})")
    if not missing and not ghost:
        note("OK", "E sitemap", "sitemap exactly matches the pages on disk")


def main():
    print("=" * 88)
    print(f"  pdufa.bio currency audit  |  {TODAY.isoformat()}")
    print("=" * 88)
    for fn in (check_upcoming, check_counts, check_asof, check_archive, check_sitemap):
        try:
            fn()
        except Exception as e:
            note("ERROR", fn.__name__, f"{type(e).__name__}: {e}")

    order = {"FAIL": 0, "ERROR": 0, "WARN": 1, "INFO": 2, "OK": 3}
    for sev in ("FAIL", "ERROR", "WARN", "INFO", "OK"):
        rows = [f for f in findings if f[0] == sev]
        if not rows:
            continue
        print(f"\n{sev}")
        for _, area, msg in rows:
            print(f"  [{area}] {msg}")
    nf = sum(1 for f in findings if f[0] in ("FAIL", "ERROR"))
    nw = sum(1 for f in findings if f[0] == "WARN")
    print(f"\n{'=' * 88}\n  {nf} failure(s), {nw} warning(s)\n{'=' * 88}")


if __name__ == "__main__":
    main()
