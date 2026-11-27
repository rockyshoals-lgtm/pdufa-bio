# -*- coding: utf-8 -*-
"""inject_first_recorded.py -- every decision page says when pdufa.bio first recorded it
(2026-11-17 currency audit, moat move 1: show our own latency, verifiably).

Competitors publish a decision with no time on it. pdufa.bio's repository is public, so the moment a decision page
first entered it is a checkable fact. Under the Verified-against line each /fda-decision page gets:
    "This page entered pdufa.bio's records on Nov 17, 2026, 1:24 AM ET."
(2026-11-27: the repository went private, so the line no longer links or names the commit.)
(written once in Eastern; RULE 1: commit timestamps carry their own offset and are converted with zoneinfo, never
assumed). Pages that came in with the repository's first import (2026-07-25/26) predate the repository: their
line says so and names the import commit, never claiming the import time as when we first recorded the decision
(2026-11-18, change 10: the line is on every decision page).

Ledger: _decision_first_recorded.json {slug: {"ts": ISO with offset, "commit": sha or null}}. A page missing from the
ledger is looked up with `git log --diff-filter=A` (works on a full clone; CI's shallow checkout usually finds
nothing) and otherwise recorded as first seen NOW with no commit -- this run's own commit publishes it, so the line
reads "by" that time. The ledger is append-only: an entry is never moved later. --backfill rebuilds missing entries
from full git history (run locally after `git fetch --unshallow`). Idempotent. Facts only; not investment advice.
"""
import argparse
import datetime as dt
import glob
import io
import json
import os
import re
import subprocess
import sys
from zoneinfo import ZoneInfo

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
LEDGER = os.path.join(HERE, "_decision_first_recorded.json")
ET = ZoneInfo("America/New_York")
IMPORT_CUTOFF = dt.datetime(2026, 7, 27, tzinfo=ET)      # the repository's first import ran 2026-07-25 21:07 PT
B, E = "<!--FIRSTREC:BEGIN-->", "<!--FIRSTREC:END-->"
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def git_first_adds():
    try:
        out = subprocess.run(["git", "log", "--diff-filter=A", "--format=C %H %cI", "--name-only", "--",
                              "pdufa_site_src/fda-decision/*/index.html"], cwd=HERE, capture_output=True,
                             text=True, timeout=120).stdout
    except Exception:
        return {}
    first, cur = {}, None
    for ln in out.splitlines():
        if ln.startswith("C "):
            cur = ln.split()[1:3]
            continue
        m = re.match(r"pdufa_site_src/fda-decision/([^/]+)/index\.html$", ln.strip())
        if m and cur:
            first[m.group(1)] = {"ts": cur[1], "commit": cur[0]}    # newest-first log: last write = oldest add
    return first


def fmt_et(iso):
    t = dt.datetime.fromisoformat(iso).astimezone(ET)
    h = t.hour % 12 or 12
    return f"{MON[t.month - 1]} {t.day}, {t.year}, {h}:{t.minute:02d} {'AM' if t.hour < 12 else 'PM'} ET"


def import_block(entry):
    """2026-11-18 (design red team, change 10: the line on every decision page). A page that came in with the
    repository's first import has no first-recorded time of its own; it says that.
    2026-11-27 (David: the repository goes private): no commit link and no "public repository"; the time stays."""
    return (f'{B}<p class="note" style="margin:0 0 10px;font-size:12px;color:#94a9c9">This page has been in pdufa.bio&#x27;s '
            f"records since they began on {fmt_et(entry['ts'])}, so they do not show when we first recorded this "
            f"decision. Dates on this page are the FDA&#x27;s and the sponsor&#x27;s; this line is ours.</p>{E}")


def block(entry, now_run):
    # 2026-11-27 (David: the repository goes private): the time stays, the commit link goes. "by" still marks an
    # entry with no commit of its own, recorded as first seen in this run.
    when = fmt_et(entry["ts"])
    lead = "This page entered pdufa.bio&#x27;s records " + ("on" if entry.get("commit") else "by")
    return (f'{B}<p class="note" style="margin:0 0 10px;font-size:12px;color:#94a9c9">{lead} {when}. '
            f'Dates on this page are the FDA&#x27;s and the sponsor&#x27;s; this line is ours.</p>{E}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backfill", action="store_true")
    a = ap.parse_args()
    led = json.load(io.open(LEDGER, encoding="utf-8")) if os.path.exists(LEDGER) else {}
    pages = sorted(glob.glob(os.path.join(SITE, "fda-decision", "*", "index.html")))
    slugs = [os.path.basename(os.path.dirname(p)) for p in pages]
    missing = [s for s in slugs if s not in led]
    adds = git_first_adds() if (missing or a.backfill) else {}
    now = dt.datetime.now(ET).replace(microsecond=0).isoformat()
    added = 0
    for s in missing:
        led[s] = adds.get(s) or {"ts": now, "commit": None}
        added += 1
    if added:
        io.open(LEDGER, "w", encoding="utf-8", newline="\n").write(json.dumps(dict(sorted(led.items())), indent=0) + "\n")
    n = w = 0
    for p, s in zip(pages, slugs):
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        base = re.sub(re.escape(B) + ".*?" + re.escape(E), "", doc, flags=re.S)
        e = led.get(s)
        new = base
        if e and "<!--VERIFIED:END-->" in base:
            post = dt.datetime.fromisoformat(e["ts"]).astimezone(ET) >= IMPORT_CUTOFF
            new = base.replace("<!--VERIFIED:END-->", "<!--VERIFIED:END-->" + (block(e, now) if post else import_block(e)), 1)
            n += 1
        if new != doc:
            io.open(p, "w", encoding="utf-8", newline="").write(new)
            w += 1
    print(f"first-recorded line: {n} decision page(s) carry it, {w} written; ledger +{added} ({len(led)} entries)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
