# -*- coding: utf-8 -*-
"""build_row_history.py -- /changes: the changes to 12 fields of each row of pdufa.bio's published dataset, from its
commits (2026-11-27: the repository is to go private, so the page names no commit or repository).

pdufa.bio's dataset (pdufa_site_src/api/v1/dataset.mjs, served at /api/v1) is committed to the repository on
every rebuild. This reads each committed version in the order main received them (first parent), compares it with
the version before, and keeps one ledger entry per change to one of the 12 fields in FIELDS (+ source_url): the row's
id, the field, the old value, the new value, the row's status in both versions, the commit that made the change and
that commit's time. A row that first appears, or that leaves the dataset, is an entry too. Other fields (prices,
market caps, run-up figures, ...) are not compared, and the page says so. The ledger, _row_history.json, is committed and only grows; each run adds the commits since the last one it read.

What the page says is a fact about this site's records, checkable against the repository: on <time>, commit <sha>
changed <field> of <row> from <old> to <new>. It is not a record of what the FDA or a company did. A row id carries
the date the row was keyed on, so a row whose id changed shows as one row leaving and one entering.

Times are the commit's own time, converted to US Eastern (CLAUDE.md rule 1: git gives an offset, often Pacific or UTC).

A date on a row whose status was the site's own "Estimated" in that version is shown with "(est.)", as /screener does.

The ledger is never started from a shallow checkout (it would name the shallow cut-off as the first version). If
main's history is rewritten so the ledger's last commit is gone, the run stops with the recovery: run --rebuild on a
full clone and commit; the rebuild is recorded in the ledger (rebuilds) and stated on the page, and the guard accepts
a non-append change only alongside a new rebuild record.

    python build_row_history.py            (add new commits to the ledger, then write /changes)
    python build_row_history.py --rebuild  (read every commit again from the start; needs the full history)
"""
import argparse
import collections
import datetime as dt
import io
import json
import os
import subprocess
import sys
from zoneinfo import ZoneInfo

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from build_crl_facts import esc  # noqa: E402
from build_crl_companies import page  # noqa: E402

SITE = os.path.join(HERE, "pdufa_site_src")
DATASET = "pdufa_site_src/api/v1/dataset.mjs"
LEDGER = os.path.join(HERE, "_row_history.json")
OUT = os.path.join(SITE, "changes", "index.html")
DATA_JSON = os.path.join(SITE, "changes", "data", "row-history.json")
DATA_CSV = os.path.join(SITE, "changes", "data", "row-history.csv")
ET = ZoneInfo("America/New_York")
# the fields compared, as the dataset names them (top level), plus the row's source address (inside _d)
FIELDS = ["t", "company", "d", "dp", "name", "type", "ta", "st", "oc", "dcd", "url"]
LABEL = {"t": "ticker", "company": "company", "d": "date", "dp": "date precision", "name": "name", "type": "type",
         "ta": "therapeutic area", "st": "status", "oc": "outcome", "dcd": "decided date", "url": "link",
         "source_url": "source address", "row": "row"}
SHOWN = ["d", "dp", "st", "oc", "dcd", "company", "name", "t", "type"]      # the page's table; the files hold all
EST_FIELDS = ("d", "dp")      # shown with "(est.)" when the row's status in that version is the site's own Estimated
RECENT = 250
FIRST_SHA = "07d961e5090acccc097cb2ee38eb9c9af384c5ba"   # the dataset's first commit (2026-07-25 21:07 PDT)


def git(*a):
    r = subprocess.run(["git", *a], cwd=HERE, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"git {' '.join(a)} failed: {r.stderr.strip()[:300]}")
    return r.stdout


def rows_at(sha):
    s = git("show", f"{sha}:{DATASET}")
    j = json.loads(s[s.index("["):s.rindex("]") + 1])
    return {r["id"]: r for r in j if isinstance(r, dict) and r.get("id")}


def val(r, f):
    v = (r.get("_d") or {}).get("source_url") if f == "source_url" else r.get(f)
    return "" if v is None else str(v)


def et_time(iso):
    return dt.datetime.fromisoformat(iso).astimezone(ET).strftime("%Y-%m-%d %H:%M ET")


def diff(prev, cur, sha, iso):
    out, ts = [], et_time(iso)

    def e(k, field, old, new, src):
        return {"sha": sha, "ts": ts, "id": k, "field": field, "old": old, "new": new, "t": val(src, "t"),
                "name": val(src, "name"), "st_was": val(prev[k], "st") if k in prev else "",
                "st_now": val(cur[k], "st") if k in cur else ""}
    for k in sorted(set(prev) | set(cur)):
        if k not in prev:
            out.append(e(k, "row", "", "entered", cur[k]))
        elif k not in cur:
            out.append(e(k, "row", "", "left", prev[k]))
        else:
            for f in FIELDS + ["source_url"]:
                a, b = val(prev[k], f), val(cur[k], f)
                if a != b:
                    out.append(e(k, f, a, b, cur[k]))
    return out


def commits(ref):
    lines = git("log", "--first-parent", "--reverse", "--format=%H %cI", ref, "--", DATASET).split("\n")
    return [tuple(x.split(" ", 1)) for x in lines if x.strip()]


def shallow():
    return git("rev-parse", "--is-shallow-repository").strip() == "true"


def update(rebuild=False, ref="HEAD"):
    old = json.load(io.open(LEDGER, encoding="utf-8")) if os.path.exists(LEDGER) else None
    led = None if rebuild else old
    cs = commits(ref)
    if not cs:
        raise SystemExit("no commits of the dataset are reachable; fetch the history first")
    if led is None:
        if shallow() or cs[0][0] != FIRST_SHA:
            raise SystemExit("a new ledger needs the full history from the dataset's first commit "
                             f"{FIRST_SHA[:10]} (git fetch --unshallow origin); not started")
        first, fts = cs[0]
        led = {"first_sha": first, "first_ts": et_time(fts), "first_rows": len(rows_at(first)), "versions": 1,
               "last_sha": first, "last_ts": et_time(fts), "rebuilds": list((old or {}).get("rebuilds", [])),
               "changes": []}
        if old and rebuild:
            led["rebuilds"].append({"time_et": dt.datetime.now(ET).strftime("%Y-%m-%d %H:%M ET"),
                                    "previous_last_commit": old["last_sha"]})
        todo = cs[1:]
    else:
        shas = [c[0] for c in cs]
        if led["last_sha"] not in shas:
            if shallow():
                raise SystemExit(f"the ledger's last commit {led['last_sha'][:10]} is older than this shallow "
                                 "checkout; fetch more history (git fetch --shallow-since) and run again")
            raise SystemExit(f"the ledger's last commit {led['last_sha'][:10]} is not on main's first-parent history: "
                             "main was rewritten. Recover on a full clone: python build_row_history.py --rebuild, "
                             "then commit _row_history.json (the rebuild is recorded and stated on /changes)")
        todo = cs[shas.index(led["last_sha"]) + 1:]
    prev = rows_at(led["last_sha"]) if todo else None
    for sha, iso in todo:
        cur = rows_at(sha)
        led["changes"].extend(diff(prev, cur, sha, iso))
        led["versions"] += 1
        led["last_sha"], led["last_ts"] = sha, et_time(iso)
        prev = cur
    io.open(LEDGER, "w", encoding="utf-8").write(json.dumps(led, ensure_ascii=False, indent=0) + "\n")
    return led, len(todo)


def shown_value(c, which):
    v = c[which]
    if c["field"] == "row":
        return "" if which == "old" else ("entered the dataset" if v == "entered" else "left the dataset")
    if v == "":
        return "(blank)"
    st = c.get("st_was" if which == "old" else "st_now")
    return v + " (est.)" if c["field"] in EST_FIELDS and st == "Estimated" else v


def texts(led):
    """The page's title, description, lede and method, from the ledger (tests/test_row_history.py rebuilds these
    sentences' numbers on its own)."""
    ch = led["changes"]
    n_ids = len({c["id"] for c in ch})
    by = collections.Counter(c["field"] for c in ch)
    first_day = led["first_ts"][:10]
    title = f"Dataset Change History: {len(ch):,} Changes Since {first_day} | pdufa.bio"
    # 2026-11-27 (David: the repository goes private): no commit links and no "public repository" on /changes.
    desc = (f"Changes to 12 fields of each row of pdufa.bio's published dataset since {first_day}, read from "
            f"{led['versions']} recorded versions, each with its old value, new value and time.")
    if len(desc) > 158:
        desc = f"Changes to 12 fields of each row of pdufa.bio's dataset since {first_day}, from {led['versions']} versions."
    lede = (f"{len(ch):,} changes to 12 fields across {n_ids:,} row ids of pdufa.bio's published dataset, read from "
            f"{led['versions']:,} recorded versions between {led['first_ts']} and "
            f"{led['last_ts']}.")
    counts = ", ".join(f"{LABEL[f]} {n:,}" for f, n in sorted(by.items(), key=lambda x: (-x[1], x[0])))
    fields = ", ".join(LABEL[f] for f in FIELDS) + " and source address"
    return title, desc, lede, counts, fields


def write_page(led):
    ch = led["changes"]
    shown = [c for c in ch if c["field"] in SHOWN or c["field"] == "row"]
    recent = list(reversed(shown))[:RECENT]
    title, desc, lede, counts, fields = texts(led)
    rebuilt = "".join(f' The ledger was read again from the first version on {esc(r["time_et"])}, after the main '
                      "branch's history was rewritten." for r in led.get("rebuilds", []))
    B = ['<h1>What changed in <span class="g">our dataset</span>, and when</h1>',
         f'<p class="sub" data-changes="lede">{esc(lede)}</p>',
         f'<p class="sub" data-changes="method">Each version of the dataset served at <a href="/developers">'
         f'/api/v1</a> is recorded in pdufa.bio&#x27;s version history. Each entry below compares one recorded '
         'version with the one before it, in the order they were recorded. '
         f'The fields compared are {esc(fields)}, plus a row entering or '
         'leaving the dataset; other fields, such as prices and market caps, are not compared here. These are '
         "changes to this site's records, not FDA or company actions. The time shown is when the version was recorded; "
         "it is not when the FDA or a company acted. A row's id carries the date the row was keyed on, so a row "
         'whose id changed shows as one id leaving and one entering. A date marked (est.) is on a row whose status '
         "was the site's own Estimated in that version. Times are each version's own time in US Eastern Time. The "
         f'first version ({esc(led["first_ts"])}) held {led["first_rows"]:,} rows. By field: {esc(counts)}.'
         f'{rebuilt}</p>',
         f'<p class="sub">The full record, every compared field: <a href="/changes/data/row-history.csv">CSV</a> '
         f'&middot; <a href="/changes/data/row-history.json">JSON</a>, free under CC BY 4.0 like the dataset itself: '
         f'cite pdufa.bio and link this page. The table shows the newest {len(recent)} '
         'changes to date, date precision, status, outcome, decided date, company, name, ticker or type, and rows '
         'entering or leaving.</p>',
         '<table data-changes="recent" data-verbatim="record"><tr><th>Recorded (ET)</th><th>Row</th><th>Field</th>'
         '<th>Was</th><th>Now</th></tr>']
    for c in recent:
        row = f'{esc(c["t"])} &middot; {esc(c["name"])}' if c["name"] else esc(c["t"])
        B.append(f'<tr><td class="dt">{esc(c["ts"])}</td><td>{row}<br><span style="font-size:11.5px;color:#8aa0bf">'
                 f'{esc(c["id"])}</span></td><td>{esc(LABEL[c["field"]])}</td><td>{esc(shown_value(c, "old"))}</td>'
                 f'<td>{esc(shown_value(c, "new"))}</td></tr>')
    B.append('</table>')
    B.append('<p class="sub"><a href="/pdufa-date-changes">Goal-date changes, each with its source</a> &middot; '
             '<a href="/feed">feeds</a> &middot; <a href="/developers">the API</a> &middot; <a href="/corrections">'
             'corrections</a></p>')
    ld = {"@context": "https://schema.org", "@type": "Dataset",
          "name": "pdufa.bio dataset change history",
          "description": (f"{len(ch):,} changes to 12 fields of each row of pdufa.bio's published PDUFA dataset, read "
                          f"from {led['versions']:,} recorded versions between {led['first_ts']} and "
                          f"{led['last_ts']}, each with its old value, new value and time. Changes to this "
                          "site's records, not FDA or company actions."),
          "url": "https://www.pdufa.bio/changes", "license": "https://creativecommons.org/licenses/by/4.0/",
          "isAccessibleForFree": True,
          "creator": {"@type": "Organization", "name": "pdufa.bio", "url": "https://www.pdufa.bio/"},
          "temporalCoverage": f"{led['first_ts'][:10]}/{led['last_ts'][:10]}",
          "dateModified": led["last_ts"][:10],
          "distribution": [{"@type": "DataDownload", "encodingFormat": "text/csv",
                            "contentUrl": "https://www.pdufa.bio/changes/data/row-history.csv"},
                           {"@type": "DataDownload", "encodingFormat": "application/json",
                            "contentUrl": "https://www.pdufa.bio/changes/data/row-history.json"}]}
    B.append('<script type="application/ld+json">' + json.dumps(ld, ensure_ascii=False, separators=(",", ":"))
             + '</script>')
    os.makedirs(os.path.dirname(DATA_JSON), exist_ok=True)
    io.open(OUT, "w", encoding="utf-8").write(page(title, desc, "/changes", B))
    io.open(DATA_JSON, "w", encoding="utf-8").write(json.dumps(
        {"about": "Changes to 12 fields (listed under fields) of each row of pdufa.bio's published dataset (/api/v1), "
                  "read from the site's recorded versions (commit and first_commit/last_commit are each version's "
                  "id). Times are each version's time in US Eastern. Changes "
                  "to this site's records, not FDA or company actions. st_was and st_now are the row's status in "
                  "the earlier and the later version.",
         "first_commit": led["first_sha"], "first_time_et": led["first_ts"],
         "last_commit": led["last_sha"], "last_time_et": led["last_ts"], "versions": led["versions"],
         "rebuilds": led.get("rebuilds", []),
         "fields": {f: LABEL[f] for f in FIELDS + ["source_url", "row"]}, "changes": ch},
        ensure_ascii=False, indent=1) + "\n")
    import csv
    with io.open(DATA_CSV, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(CSV_HEAD)
        for c in ch:
            w.writerow(csv_row(c))


CSV_HEAD = ["time_et", "commit", "row_id", "ticker", "name", "field", "old", "new", "status_was", "status_now"]


def csv_row(c):
    return [c["ts"], c["sha"], c["id"], c["t"], c["name"], c["field"], c["old"], c["new"], c["st_was"], c["st_now"]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rebuild", action="store_true")
    ap.add_argument("--ref", default="HEAD")
    ap.add_argument("--page-only", action="store_true")
    a = ap.parse_args()
    if a.page_only:
        led, n = json.load(io.open(LEDGER, encoding="utf-8")), 0
    else:
        led, n = update(a.rebuild, a.ref)
    write_page(led)
    print(f"/changes: {len(led['changes']):,} changes over {led['versions']} versions ({n} new), "
          f"{led['first_ts']} to {led['last_ts']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
