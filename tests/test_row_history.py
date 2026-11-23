# -*- coding: utf-8 -*-
"""CI guard: /changes and _row_history.json (build_row_history.py) say what the public commits say.

  * The ledger starts at the dataset's first commit (pinned here with its time and row count), is current (its last
    commit is the newest dataset commit on this branch's first-parent line; a short lag is a note, three days
    blocks), and only grows: the ledger committed at HEAD is a prefix of the one on disk, unless a new rebuild is
    recorded and the full history is here to check it.
  * Every commit the ledger names is on the first-parent line, in order, one run of entries per commit (all of them
    with the full history; the reachable ones in a shallow CI checkout).
  * For every pair of consecutive dataset commits reachable here (at least one pair), the ledger's entries for the
    later commit are exactly a diff computed here, independently and in the builder's order: id, field, old, new,
    ticker, name, the row's status in both versions, and the commit's time in US Eastern.
  * /changes: title, description, lede and the method's numbers are the ledger's; every cell of the record table is
    the ledger's newest shown entries ("(est.)" exactly where the row was Estimated); the CSV and JSON hold every
    entry, value for value; no forecast or reason word in the page's own words (everything outside the record
    table, whose Was and Now cells are dataset values quoted as committed).

PLANT=1 drops one checked ledger entry and must FAIL; PLANT=2 alters one checked old value and must FAIL.

    python tests/test_row_history.py      (fix: python build_row_history.py)
"""
import csv
import datetime as dt
import html
import io
import json
import os
import re
import subprocess
import sys
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
SITE = os.path.join(HERE, "pdufa_site_src")
DATASET = "pdufa_site_src/api/v1/dataset.mjs"
REPO = "https://github.com/rockyshoals-lgtm/pdufa-bio"
FIRST = ("07d961e5090acccc097cb2ee38eb9c9af384c5ba", "2026-07-26 00:07 ET", 388)   # written by hand, from git
TOP = ["t", "company", "d", "dp", "name", "type", "ta", "st", "oc", "dcd", "url"]
ALL = TOP + ["source_url"]
NAMES = {"t": "ticker", "company": "company", "d": "date", "dp": "date precision", "name": "name", "type": "type",
         "ta": "therapeutic area", "st": "status", "oc": "outcome", "dcd": "decided date", "url": "link",
         "source_url": "source address", "row": "row"}
TABLE = {"d", "dp", "st", "oc", "dcd", "company", "name", "t", "type", "row"}
BAD = re.compile(r"\b(probabilit|odds\b|chances?\b|likel[yi]|predict|forecast|expect|because|caused?\b|due to"
                 r"|led to|reject|refus|denial|denied|reason|signal|will be approved)", re.I)
ET = ZoneInfo("America/New_York")


def git(*a, ok=False):
    r = subprocess.run(["git", *a], cwd=HERE, capture_output=True, text=True)
    if r.returncode and not ok:
        raise SystemExit(f"git {' '.join(a)}: {r.stderr.strip()[:200]}")
    return r.stdout if not r.returncode else None


def load(sha):
    s = git("show", f"{sha}:{DATASET}")
    return {r["id"]: r for r in json.loads(s[s.index("["):s.rindex("]") + 1]) if isinstance(r, dict) and r.get("id")}


def s_(v):
    return "" if v is None else str(v)


def own_diff(a, b):
    """[(id, field, old, new, ticker, name, st_was, st_now)] in the builder's order, written here."""
    out = []
    for k in sorted(set(a) | set(b)):
        sw, sn = (s_(a[k].get("st")) if k in a else ""), (s_(b[k].get("st")) if k in b else "")
        if k not in a:
            out.append((k, "row", "", "entered", s_(b[k].get("t")), s_(b[k].get("name")), sw, sn))
        elif k not in b:
            out.append((k, "row", "", "left", s_(a[k].get("t")), s_(a[k].get("name")), sw, sn))
        else:
            for f in ALL:
                x = s_((a[k].get("_d") or {}).get("source_url") if f == "source_url" else a[k].get(f))
                y = s_((b[k].get("_d") or {}).get("source_url") if f == "source_url" else b[k].get(f))
                if x != y:
                    out.append((k, f, x, y, s_(b[k].get("t")), s_(b[k].get("name")), sw, sn))
    return out


def text_of(fragment):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def cell(c, which):
    v = c[which]
    if c["field"] == "row":
        return "" if which == "old" else {"entered": "entered the dataset", "left": "left the dataset"}[v]
    if v == "":
        return "(blank)"
    st = c["st_was"] if which == "old" else c["st_now"]
    return v + " (est.)" if c["field"] in ("d", "dp") and st == "Estimated" else v


def main():
    fails = []
    led_p = os.path.join(HERE, "_row_history.json")
    if not os.path.exists(led_p):
        print("FAIL test_row_history: _row_history.json is missing; fix: python build_row_history.py")
        return 1
    led = json.load(io.open(led_p, encoding="utf-8"))
    full = led["changes"]
    plant = os.environ.get("PLANT")
    is_shallow = (git("rev-parse", "--is-shallow-repository") or "").strip() == "true"
    log = [x.split(" ", 1) for x in (git("log", "--first-parent", "--format=%H %cI", "HEAD", "--", DATASET) or "")
           .split("\n") if x.strip()]                       # newest first
    order = {sha: i for i, (sha, _) in enumerate(reversed(log))}

    # where the ledger starts, and that it is current
    if (led["first_sha"], led["first_ts"], led["first_rows"]) != FIRST:
        fails.append(f"the ledger starts at {led['first_sha'][:10]} {led['first_ts']} ({led['first_rows']} rows), "
                     f"not the dataset's first commit {FIRST[0][:10]} {FIRST[1]} ({FIRST[2]} rows)")
    if not log:
        fails.append("no dataset commit is reachable from HEAD")
    elif log[0][0] != led["last_sha"]:
        age = dt.datetime.now(ET) - dt.datetime.strptime(led["last_ts"], "%Y-%m-%d %H:%M ET").replace(tzinfo=ET)
        msg = (f"the ledger ends at {led['last_sha'][:10]}, the newest dataset commit here is {log[0][0][:10]}"
               + (" (shallow checkout)" if is_shallow else ""))
        if led["last_sha"] not in order and not is_shallow:
            fails.append(msg + ": the ledger's last commit is not on main's first-parent history (main was "
                         "rewritten); recover with python build_row_history.py --rebuild on a full clone")
        elif age > dt.timedelta(days=3):
            fails.append(msg + ", more than three days behind")
        else:
            print("  NOTE: " + msg)

    # append-only against the ledger committed at HEAD, unless a new rebuild is recorded
    old = git("show", "HEAD:_row_history.json", ok=True)
    if old:
        o = json.loads(old)
        if full[:len(o["changes"])] != o["changes"]:
            if len(led.get("rebuilds", [])) > len(o.get("rebuilds", [])) and not is_shallow:
                print("  NOTE: the ledger was rebuilt (recorded); every reachable pair is re-checked below")
            else:
                fails.append("the ledger is not append-only: the committed entries changed")
        if led.get("rebuilds", [])[:len(o.get("rebuilds", []))] != o.get("rebuilds", []):
            fails.append("the ledger's rebuild record changed")

    # every named commit is a first-parent dataset commit, in order, one run each
    runs = []
    for c in full:
        if not runs or runs[-1] != c["sha"]:
            runs.append(c["sha"])
    if len(runs) != len(set(runs)):
        fails.append("a commit's entries are split into more than one run in the ledger")
    known = [order[s] for s in runs if s in order]
    if known != sorted(known):
        fails.append("the ledger's commits are not in first-parent order")
    if not is_shallow:
        stray = [s for s in runs if s not in order]
        if stray:
            fails.append(f"{len(stray)} ledger commit(s) are not dataset commits on main's first-parent line "
                         f"({stray[0][:10]})")
        if led["versions"] != len(log):
            fails.append(f"the ledger counts {led['versions']} versions, the history {len(log)}")
        if FIRST[0] not in order or order[FIRST[0]] != 0:
            fails.append(f"{FIRST[0][:10]} is not the dataset's first commit here")
    if any(c["sha"] == led["first_sha"] for c in full):
        fails.append("the first version carries entries (it has nothing before it to compare)")

    # independent diffs for the reachable pairs
    pairs, checked = [], []
    for (sha, iso), (psha, _) in zip(log, log[1:]):
        try:
            a, b = load(psha), load(sha)
        except SystemExit:
            break
        pairs.append((sha, iso, a, b))
        if len(pairs) >= int(os.environ.get("ROW_HISTORY_PAIRS", "100000")):
            break
    checked = {p[0] for p in pairs}
    ch = list(full)
    if plant in ("1", "2"):
        i = max((n for n, c in enumerate(ch) if c["sha"] in checked), default=None)
        if i is None:
            print("FAIL test_row_history: PLANT found no checked entry to change")
            return 1
        if plant == "1":
            del ch[i]
        else:
            ch[i] = dict(ch[i], old=ch[i]["old"] + "x")
    by_sha = {}
    for c in ch:
        by_sha.setdefault(c["sha"], []).append(c)
    for sha, iso, a, b in pairs:
        want = own_diff(a, b)
        got = by_sha.get(sha, [])
        mine = [(c["id"], c["field"], c["old"], c["new"], c["t"], c["name"], c["st_was"], c["st_now"]) for c in got]
        if mine != want:
            diff = [x for x in want if x not in mine][:2] + [x for x in mine if x not in want][:2]
            fails.append(f"commit {sha[:10]}: the ledger's entries are not the diff of its dataset ({diff or 'order'})")
        ts = dt.datetime.fromisoformat(iso).astimezone(ET).strftime("%Y-%m-%d %H:%M ET")
        if any(c["ts"] != ts for c in got):
            fails.append(f"commit {sha[:10]}: an entry's time is not the commit's time in Eastern ({ts})")
    if not pairs and len(log) > 1:
        fails.append("no pair of dataset commits could be read; fetch more history")
    if plant and fails:
        print(f"FAIL test_row_history (PLANT={plant}): {fails[0]}")
        return 1

    # the page
    p = os.path.join(SITE, "changes", "index.html")
    doc = io.open(p, encoding="utf-8").read() if os.path.exists(p) else ""
    if not doc:
        fails.append("/changes is missing")
    n_ids = len({c["id"] for c in full})
    by = {}
    for c in full:
        by[c["field"]] = by.get(c["field"], 0) + 1
    first_day = led["first_ts"][:10]
    want_title = f"Dataset Change History: {len(full):,} Changes Since {first_day} | pdufa.bio"
    title = text_of((re.search(r"<title>(.*?)</title>", doc, re.S) or [None, ""])[1]) if doc else ""
    if title != want_title:
        fails.append(f"/changes: the title {title!r} is not {want_title!r}")
    desc = html.unescape((re.search(r'<meta name="description" content="([^"]*)"', doc) or [None, ""])[1])
    if not (desc.startswith("Changes to 12 fields of each row of pdufa.bio's") and f"since {first_day}" in desc
            and f"{led['versions']} " in desc):
        fails.append(f"/changes: the description {desc!r} is not the ledger's")
    m = re.search(r'<script type="application/ld\+json">(\{"@context":"https://schema.org","@type":"Dataset".*?)'
                  r'</script>', doc, re.S)
    ld = json.loads(m.group(1)) if m else {}
    if not (ld.get("description", "").startswith(
            f"{len(full):,} changes to 12 fields of each row of pdufa.bio's published PDUFA dataset, read from "
            f"{led['versions']:,} versions in the public repository between {led['first_ts']} and {led['last_ts']},")
            and ld.get("temporalCoverage") == f"{first_day}/{led['last_ts'][:10]}"
            and ld.get("dateModified") == led["last_ts"][:10]
            and sorted(d.get("contentUrl") for d in ld.get("distribution", [])) ==
            ["https://www.pdufa.bio/changes/data/row-history.csv", "https://www.pdufa.bio/changes/data/row-history.json"]):
        fails.append("/changes: the Dataset schema is missing or not the ledger's")
    lede = text_of((re.search(r'data-changes="lede">(.*?)</p>', doc, re.S) or [None, ""])[1])
    want_lede = (f"{len(full):,} changes to 12 fields across {n_ids:,} row ids of pdufa.bio's published dataset, "
                 f"read from {led['versions']:,} versions committed to the public repository between "
                 f"{led['first_ts']} and {led['last_ts']}.")
    if lede != want_lede:
        fails.append(f"/changes: the lede {lede[:90]!r} is not the ledger's")
    method = text_of((re.search(r'data-changes="method">(.*?)</p>', doc, re.S) or [None, ""])[1])
    counts = ", ".join(f"{NAMES[f]} {n:,}" for f, n in sorted(by.items(), key=lambda x: (-x[1], x[0])))
    fields = ", ".join(NAMES[f] for f in TOP) + " and source address"
    for need in (f"The fields compared are {fields}, plus a row entering or leaving the dataset;",
                 f"The first version ({led['first_ts']}) held {led['first_rows']:,} rows.", f"By field: {counts}.",
                 "The time shown is when the commit was made; it is not when the FDA or a company acted.",
                 "Times are each commit's own time in US Eastern Time."):
        if need not in method:
            fails.append(f"/changes: the method does not say {need[:70]!r}")
    for r in led.get("rebuilds", []):
        if f"read again from the first version on {r['time_et']}" not in method:
            fails.append(f"/changes: the rebuild of {r['time_et']} is not stated")

    exp = list(reversed([c for c in full if c["field"] in TABLE]))[:250]
    if f"The table shows the newest {len(exp)} changes" not in text_of(doc):
        fails.append(f"/changes: the page does not say the table shows the newest {len(exp)} changes")
    t = re.search(r'<table data-changes="recent" data-verbatim="record">(.*?)</table>', doc, re.S)
    trs = re.findall(r"<tr>(.*?)</tr>", t.group(1) if t else "", re.S)
    head = [text_of(x) for x in re.findall(r"<th>(.*?)</th>", trs[0] if trs else "", re.S)]
    if head != ["Committed (ET)", "Row", "Field", "Was", "Now", "Commit"]:
        fails.append(f"/changes: the table's header is {head}")
    rows = [r for r in trs if "<td" in r]
    if len(rows) != len(exp):
        fails.append(f"/changes: the table has {len(rows)} rows, the ledger's newest {len(exp)}")
    for r, c in zip(rows, exp):
        cells = [text_of(x) for x in re.findall(r"<td[^>]*>(.*?)</td>", r, re.S)]
        who = f"{c['t']} · {c['name']}" if c["name"] else c["t"]
        want = [c["ts"], f"{who} {c['id']}".strip(), NAMES[c["field"]], cell(c, "old"), cell(c, "new"), c["sha"][:10]]
        hrefs = re.findall(r'href="([^"]*)"', r)
        if cells != want or hrefs != [f"{REPO}/commit/{c['sha']}"]:
            fails.append(f"/changes: a table row reads {cells[:4]}, the ledger's entry is {want[:4]}")
            break
    own = doc[doc.find("<h1"):(doc.find('<div class="legal"') if '<div class="legal"' in doc else None)]
    own = text_of(re.sub(r'<table data-changes="recent" data-verbatim="record">.*?</table>', " ", own, flags=re.S))
    if BAD.search(own):
        fails.append(f"/changes: the page's own words carry {BAD.search(own).group(0)!r}")
    if doc.count('data-verbatim="record"') != 1:
        fails.append("/changes: the record table is not on the page exactly once")

    # the downloads, entry by entry
    from build_row_history import CSV_HEAD, csv_row
    cp = os.path.join(SITE, "changes", "data", "row-history.csv")
    jp = os.path.join(SITE, "changes", "data", "row-history.json")
    got_csv = list(csv.reader(io.open(cp, encoding="utf-8", newline=""))) if os.path.exists(cp) else []
    if got_csv[:1] != [CSV_HEAD] or got_csv[1:] != [csv_row(c) for c in full]:
        fails.append(f"/changes CSV is not the ledger ({max(len(got_csv) - 1, 0)} rows, the ledger {len(full)})")
    j = json.load(io.open(jp, encoding="utf-8")) if os.path.exists(jp) else {}
    meta = {"first_commit": led["first_sha"], "first_time_et": led["first_ts"], "last_commit": led["last_sha"],
            "last_time_et": led["last_ts"], "versions": led["versions"], "repository": REPO}
    if j.get("changes") != full or any(j.get(k) != v for k, v in meta.items()) \
            or j.get("rebuilds", []) != led.get("rebuilds", []) or set(j.get("fields", {})) != set(ALL) | {"row"}:
        fails.append("/changes JSON is not the ledger")

    if fails:
        print(f"FAIL test_row_history: {len(fails)} problem(s); fix: python build_row_history.py")
        for f in fails[:20]:
            print("  " + f)
        return 1
    print(f"PASS test_row_history: {len(full):,} entries; {len(pairs)} commit pairs re-diffed independently; page, "
          "table and downloads agree")
    return 0


if __name__ == "__main__":
    sys.exit(main())
