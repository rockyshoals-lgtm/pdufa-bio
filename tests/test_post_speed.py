# -*- coding: utf-8 -*-
"""Posting-speed stamps ("Posted N min after the source") recomputed with independent code (2026-11-27).

Fake news is worse than no news: every stamp must rest on a verified source time with its UTC offset and on the
first-parent commit to main that carried the fact. Checks:
  * _source_times.json: every source time carries a numeric offset (RULE 1), an https link and a label;
  * _post_speed.json: full commit ids, times with offsets, and (on a full clone) the commit's own time, reachable
    from main on its first-parent line;
  * each stamp states the EARLIEST source, both times in ET and UTC, and the gap floored to whole minutes;
  * no stamp where an earlier untimed disclosure exists, where the gap is not positive, or on a page with no event;
  * /drug lines, /research/posting-speed (median, table) and /api/v1/post-speed agree with the same records;
  * no "first", "fastest" or "faster than" claim in anything this feature writes;
  * a source time that changes against the last commit needs a dated /corrections entry naming the page;
  * planted failures (a wrong minute, a missing offset, a stamp under an untimed earlier disclosure) are caught.
"""
import datetime as dt
import glob
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
ET, UTC = ZoneInfo("America/New_York"), dt.timezone.utc
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
OFFSET = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d(:\d\d)?([+-]\d\d:\d\d|Z)$")
CLAIM = re.compile(r"\b(first to|first with|fastest|faster than|beat(s|ing)? (the|every|all)|before anyone)\b", re.I)


def _j(p):
    return json.load(io.open(os.path.join(HERE, p), encoding="utf-8"))


def _t(s):
    if not isinstance(s, str) or not OFFSET.match(s):
        return None
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def _dur(m):
    if m < 60:
        return f"{m} min"
    h, mm = divmod(m, 60)
    if h < 48:
        return f"{h} h {mm} min" if mm else f"{h} h"
    d, hh = divmod(h, 24)
    return f"{d} d {hh} h" if hh else f"{d} d"


def _et(t):
    e = t.astimezone(ET)
    return f"{MON[e.month - 1]} {e.day}, {e.year}, {e.hour % 12 or 12}:{e.minute:02d} {'AM' if e.hour < 12 else 'PM'} ET"


def _utc(t):
    u = t.astimezone(UTC)
    day = "" if u.date() == t.astimezone(ET).date() else f", {MON[u.month - 1]} {u.day}"
    return f"{u.hour:02d}:{u.minute:02d} UTC{day}"


def _text(s):
    s = re.sub(r"(?s)<script.*?</script>|<style.*?</style>", " ", s)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def _rows():
    from build_post_speed import load_rows
    return load_rows()


def expected():
    """{page_url: record} for every event that should carry a stamp, computed here from the two ledgers."""
    src, cache, rows = _j("_source_times.json"), _j("_post_speed.json"), _rows()
    out = {}
    for key, ev in (src.get("events") or {}).items():
        r = rows.get(ev.get("row"))
        times = [(_t(s.get("at")), s) for s in ev.get("sources") or []]
        times = [(t, s) for t, s in times if t]
        if not r or not times or ev.get("earlier_untimed") or key not in cache:
            continue
        t0, s0 = min(times, key=lambda x: x[0])
        site = _t(cache[key]["site_at"])
        gap = int((site - t0).total_seconds() // 60)
        if gap <= 0:
            continue
        out[r["url"]] = {"key": key, "source": s0, "source_at": t0, "site_at": site, "commit": cache[key]["commit"],
                         "gap": gap, "kind": ev["kind"], "row": ev["row"], "t": r.get("t")}
    return out


def check_stamp(doc, rec):
    """Problems with one page's stamp against its record (empty list = right)."""
    m = re.search(r"<!--POSTSPEED:BEGIN-->(.*?)<!--POSTSPEED:END-->", doc, re.S)
    if not m:
        return ["no stamp"]
    raw, txt, bad = m.group(1), _text(m.group(1)), []
    if f"Posted {_dur(rec['gap'])} after the source." not in txt:
        bad.append(f"gap: want 'Posted {_dur(rec['gap'])} after the source.' in {txt[:90]!r}")
    if f"{_et(rec['source_at'])} ({_utc(rec['source_at'])})" not in txt:
        bad.append(f"source time: want {_et(rec['source_at'])} ({_utc(rec['source_at'])})")
    if f"{_et(rec['site_at'])} ({_utc(rec['site_at'])})" not in txt:
        bad.append(f"site time: want {_et(rec['site_at'])} ({_utc(rec['site_at'])})")
    if f'href="{html.escape(rec["source"]["url"], quote=True)}"' not in raw and f'href="{rec["source"]["url"]}"' not in raw:
        bad.append("does not link the earliest source")
    if f"/commit/{rec['commit']}" not in raw:
        bad.append("does not link the commit")
    if CLAIM.search(txt):
        bad.append("claims priority over others")
    return bad


def test_source_ledger_times_carry_offsets():
    src = _j("_source_times.json")
    n = 0
    for key, ev in src["events"].items():
        assert ev.get("kind") in ("decision", "date_change"), key
        if ev["kind"] == "date_change":
            assert re.match(r"^\d{4}-\d\d-\d\d$", ev.get("new_date") or ""), f"{key}: date change without new_date"
        for s in ev.get("sources") or []:
            n += 1
            assert _t(s.get("at")), f"{key}: source time {s.get('at')!r} has no UTC offset (RULE 1)"
            assert (s.get("url") or "").startswith("https://"), f"{key}: source without an https link"
            assert s.get("label") and s.get("kind") in ("wire", "sec", "fda"), f"{key}: source label/kind"
            assert re.match(r"^\d{4}-\d\d-\d\d$", s.get("checked") or ""), f"{key}: source never re-read"
            assert s.get("printed"), f"{key}: what the source itself prints must be recorded"
    assert n >= 15


def test_cache_commits_are_main_first_parent():
    cache = _j("_post_speed.json")
    have_git = subprocess.run(["git", "rev-parse", "--is-shallow-repository"], cwd=HERE, capture_output=True,
                              text=True).stdout.strip() == "false"
    fp = set()
    if have_git:
        fp = set(subprocess.run(["git", "log", "--first-parent", "--format=%H", "HEAD"], cwd=HERE,
                                capture_output=True, text=True).stdout.split())
    for key, c in cache.items():
        assert re.match(r"^[0-9a-f]{40}$", c.get("commit") or ""), f"{key}: commit id"
        assert _t(c.get("site_at")), f"{key}: site time without offset"
        if have_git:
            ci = subprocess.run(["git", "show", "-s", "--format=%cI", c["commit"]], cwd=HERE, capture_output=True,
                                text=True).stdout.strip()
            assert ci and _t(ci) == _t(c["site_at"]), f"{key}: cached {c['site_at']} but the commit says {ci}"
            assert c["commit"] in fp, f"{key}: {c['commit'][:7]} is not on main's first-parent line"


def test_every_stamp_matches_its_record():
    exp = expected()
    assert len(exp) >= 10, len(exp)
    bad = []
    for url, rec in exp.items():
        p = os.path.join(SITE, url.strip("/"), "index.html")
        if not os.path.exists(p):
            bad.append(f"{url}: page missing")
            continue
        bad += [f"{url}: {b}" for b in check_stamp(io.open(p, encoding="utf-8").read(), rec)]
    assert not bad, "\n".join(bad)


def test_no_stamp_without_a_record():
    want = {os.path.join(SITE, u.strip("/"), "index.html") for u in expected()}
    stray = []
    for p in glob.glob(os.path.join(SITE, "**", "index.html"), recursive=True):
        d = io.open(p, encoding="utf-8", errors="replace").read()
        if ("<!--POSTSPEED:BEGIN-->" in d or "<!--POSTSPEEDLD:BEGIN-->" in d) and p not in want:
            stray.append(os.path.relpath(p, SITE))
    assert not stray, f"stamp with no verified record (untimed earlier disclosure or no source): {stray}"


def test_jsonld_matches_record():
    for url, rec in expected().items():
        d = io.open(os.path.join(SITE, url.strip("/"), "index.html"), encoding="utf-8").read()
        m = re.search(r"<!--POSTSPEEDLD:BEGIN--><script type=\"application/ld\+json\">(.*?)</script>", d, re.S)
        assert m, f"{url}: no structured data"
        ld = json.loads(m.group(1).replace("<\\/", "</"))
        assert _t(ld["datePublished"]) == rec["site_at"], url
        assert _t(ld["isBasedOn"]["datePublished"]) == rec["source_at"], url
        assert ld["isBasedOn"]["url"] == rec["source"]["url"], url


def test_drug_lines_agree():
    exp = expected()
    n = 0
    for p in glob.glob(os.path.join(SITE, "drug", "*", "index.html")):
        d = io.open(p, encoding="utf-8", errors="replace").read()
        m = re.search(r"<!--POSTSPEEDDRUG:BEGIN-->(.*?)<!--POSTSPEEDDRUG:END-->", d, re.S)
        if not m:
            continue
        n += 1
        assert not CLAIM.search(_text(m.group(1))), p
        for href, gap in re.findall(r'<a href="([^"#]+)#posted"[^>]*>[^<]*</a>: posted ([^<]+?) after ', m.group(1)):
            assert href in exp, f"{p}: links {href}, which has no stamp"
            assert gap == _dur(exp[href]["gap"]), f"{p}: {href} says {gap}, record says {_dur(exp[href]['gap'])}"
    assert n >= 10, n


def test_research_page_and_api_agree():
    exp = expected()
    gaps = sorted(r["gap"] for r in exp.values())
    k = len(gaps)
    med = gaps[k // 2] if k % 2 else (gaps[k // 2 - 1] + gaps[k // 2]) // 2
    page = io.open(os.path.join(SITE, "research", "posting-speed", "index.html"), encoding="utf-8").read()
    txt = _text(page)
    assert f"median {_dur(med)} after that source" in txt, f"median {_dur(med)} not stated"
    assert f"shortest gap was {_dur(gaps[0])} and the longest {_dur(gaps[-1])}" in txt
    assert not CLAIM.search(txt), "the method page claims priority over others"
    hub = _text(io.open(os.path.join(SITE, "research", "index.html"), encoding="utf-8").read())
    assert f"median {_dur(med)}, from {_dur(gaps[0])} to {_dur(gaps[-1])}" in hub, "/research card out of date"
    api = io.open(os.path.join(SITE, "api", "v1", "post_speed_data.mjs"), encoding="utf-8").read()
    data = json.loads(api[api.index("export default ") + len("export default "):].rstrip().rstrip(";"))
    assert len(data) == k, f"API has {len(data)} rows, {k} events are stamped"
    by_row = {r["row"]: r for r in exp.values()}
    for d in data:
        r = by_row[d["id"]]
        assert d["minutes_after_source"] == r["gap"], d["id"]
        assert _t(d["source_published_at"]) == r["source_at"] and _t(d["site_published_at"]) == r["site_at"], d["id"]
        assert d["site_commit"] == r["commit"] and d["source_url"] == r["source"]["url"], d["id"]
    assert os.path.exists(os.path.join(SITE, "api", "v1", "post-speed.mjs"))


def test_changed_source_time_has_a_correction():
    old = subprocess.run(["git", "show", "HEAD:_source_times.json"], cwd=HERE, capture_output=True, text=True)
    if old.returncode != 0:
        print("  SKIP no committed ledger to compare")
        return
    was, now = json.loads(old.stdout).get("events", {}), _j("_source_times.json")["events"]
    corr = _j("_corrections.json")["entries"]
    rows = _rows()
    for key, ev in was.items():
        a = sorted((s.get("url"), s.get("at")) for s in ev.get("sources") or [])
        b = sorted((s.get("url"), s.get("at")) for s in (now.get(key) or {}).get("sources") or [])
        if a and a != b:
            page = (rows.get(ev["row"]) or {}).get("url")
            assert any(c.get("page") == page for c in corr), f"{key}: source time changed with no /corrections entry for {page}"


def test_planted_failures_are_caught():
    exp = expected()
    url, rec = next((u, r) for u, r in sorted(exp.items()) if r["gap"] < 48 * 60)   # shown to the minute
    doc = io.open(os.path.join(SITE, url.strip("/"), "index.html"), encoding="utf-8").read()
    assert not check_stamp(doc, rec)
    wrong = dict(rec, gap=rec["gap"] + 1)
    assert check_stamp(doc, wrong), "a stamp one minute off was not caught"
    later = dict(rec, source_at=rec["source_at"] - dt.timedelta(minutes=7))
    assert check_stamp(doc, later), "a stamp that skipped an earlier source time was not caught"
    assert _t("2026-11-18T18:03:00") is None, "a time with no offset was accepted"
    bragging = doc.replace("after the source.</b>", "after the source, faster than anyone.</b>")
    assert check_stamp(bragging, rec), "a priority claim was not caught"
    # an event with an earlier untimed disclosure must not count, even with a cached commit
    src = _j("_source_times.json")
    untimed = [k for k, e in src["events"].items() if e.get("earlier_untimed")]
    assert untimed and not any(r["key"] in untimed for r in exp.values())


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
    print(f"PASS test_post_speed: {len(tests)} checks, {len(expected())} stamps recomputed from the ledgers")
    return 0


if __name__ == "__main__":
    sys.exit(main())
