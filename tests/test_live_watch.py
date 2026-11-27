# -*- coding: utf-8 -*-
"""The every-minute news watch (api/cron/news-watch.mjs) posts only what its primary source says.

Covers: the JS auto-check suite (tests/live_watch.test.mjs, needs node), the armed list it listens for,
the kill switch, the public feed's cache bound, the Just in banner tag, the record sync with its
/corrections entry, and the posting-speed stamp's use of a confirmed live post time.
"""
import datetime as dt
import importlib
import io
import json
import os
import re
import shutil
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
sys.path.insert(0, HERE)


def _node():
    return shutil.which("node")


@pytest.mark.skipif(not _node(), reason="node is not installed")
def test_auto_check_suite():
    r = subprocess.run([_node(), "--test", os.path.join(HERE, "tests", "live_watch.test.mjs")],
                       cwd=HERE, capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-2000:]


@pytest.mark.skipif(not _node(), reason="node is not installed")
def test_armed_list_parses_and_obeys_the_switch():
    js = ("import('./pdufa_site_src/api/_watch_armed.mjs').then(m=>{const a=m.default;"
          "process.stdout.write(JSON.stringify({p:a.publish,r:a.retract,rows:a.rows,st:Object.keys(a.status).length}))})")
    r = subprocess.run([_node(), "--input-type=module", "-e", js], cwd=HERE, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    a = json.loads(r.stdout)
    lane = json.load(io.open(os.path.join(HERE, "_fast_lane.json"), encoding="utf-8"))
    assert a["p"] == bool(lane.get("publish")), "_watch_armed.mjs is stale: rerun build_watch_armed.py"
    assert a["r"] == (lane.get("retract") or {})
    assert a["st"] > 0
    ids = set()
    for row in a["rows"]:
        assert row["id"] not in ids
        ids.add(row["id"])
        assert row["terms"], f"{row['id']}: no strong match term"
        for t in row["terms"]:
            assert len(re.findall(r"[A-Za-z]", t)) >= 2, (row["id"], t)
            assert len(t) >= 5 or (re.search(r"\d", t) and len(t) >= 4), (row["id"], t)
        assert row["url"].startswith("/"), row["id"]
        for f in row.get("feeds") or []:
            assert f.startswith("https://"), (row["id"], f)
    # only the hand-reviewed fast-lane list is armed, each row by exactly one entry, on that entry's own terms
    lane = lane.get("fast_lane") or []
    for row in a["rows"]:
        es = [e for e in lane if e["t"] == row["t"] and e["match"].lower() in row["name"].lower()]
        assert len(es) == 1, row["id"]
        assert row["terms"] == es[0]["terms"] and row["need"] == es[0].get("need", []), row["id"]
        assert row["need"], f"{row['id']}: every armed row needs its indication words (red team #2)"
        assert row.get("avoid", []) == es[0].get("avoid", []), row["id"]
        assert row.get("phrases") and row["phrases"] == es[0].get("phrases"), \
            f"{row['id']}: every armed row needs its exact indication phrases (red team 4)"
        for k in ("tok", "partners", "forms", "aliases", "cls", "paren"):
            assert row.get(k, []) == es[0].get(k, []), (row["id"], k)


def test_marketed_drug_needs_need_words():
    """A term that already names a U.S.-approved product arms its row only with need words (red team #1)."""
    b = importlib.import_module("build_watch_armed")
    rows = [{"id": "p1", "type": "PDUFA", "t": "AGIO", "name": "Mitapivat (PYRUKYND) - sickle cell", "st": "Upcoming", "d": "2026-12-20"},
            {"id": "p0", "type": "PDUFA", "t": "AGIO", "name": "PYRUKYND (mitapivat) - thalassemia", "st": "Decided", "oc": "Approved"}]
    hits = b.marketed_hits(["mitapivat"], [rows[1]], {})
    assert hits, "an approved row with the same drug must count as marketed"
    appr = {"2026-01": {"items": [{"app": "NDA1", "brand": "Wakix", "generic": "pitolisant"}]}}
    assert b.marketed_hits(["pitolisant"], [], appr)
    assert not b.marketed_hits(["lorundrostat"], rows, appr)


def test_cron_fails_closed_and_runs_once_at_a_time():
    src = io.open(os.path.join(SITE, "api", "cron", "news-watch.mjs"), encoding="utf-8").read()
    assert "if (!secret) return res.status(503)" in src, "with CRON_SECRET unset nothing runs"
    assert "'live:lock'" in src and "'NX'" in src, "one run at a time"
    last = src[src.rindex("return res.status(200)"):]
    assert "beat" not in last and "held" not in last, "the cron's response never carries held or shadow items"
    assert "channel: 'fda'" not in src, "the FDA press feed is not a posting channel (red team #6)"
    assert "'live:control'" in src and "control.publish === undefined || control.publish === true" in src, "the owner's emergency stop works without a deploy; anything but a plain object stops posting"
    assert "wireItems" not in src and "FMP_API_KEY" not in src, "a newswire release alone is never posted (red team 3)"
    assert "stopped[item.url]" in src and "stopped, stopAt: stopAt0, done }" in src and "stopAt, done, rss: rssOut" in src, "a source first seen or published while posting was stopped, or posted once, never posts on its own (red team 4, 6)"
    assert "kv('EVAL', READ_LUA" in src and "kv('MGET'" not in src, "the store is read with GET, so a key of another type stops the watch (red team 6)"
    assert "corrections(item, armed, pub)" in src, "the sponsor's own correction withdraws a live post (red team 6)"
    assert "fresh: rss.urls[i.url].f > 0" in src, "a feed item in the first read of its feed never posts (red team 4)"
    assert "readState(v)" in src and "readControl(c)" in src


def test_live_feed_honours_the_hide_switch():
    src = io.open(os.path.join(SITE, "api", "v1", "live.mjs"), encoding="utf-8").read()
    assert "'live:control'" in src and "pub: {}" in src
    assert "kv('EVAL', READ_LUA" in src and "kv('MGET'" not in src and "rk.some(k => !ids.has(k))" in src, "GET read; a retract applies at once, and a retract typo hides every post (red team 6)"


def test_live_feed_never_exposes_held_or_shadow_items():
    src = io.open(os.path.join(SITE, "api", "v1", "live.mjs"), encoding="utf-8").read()
    code = re.sub(r"//.*", "", re.sub(r"/\*.*?\*/", "", src, flags=re.S))
    assert "held" not in code and "shadow" not in code


def test_cron_is_scheduled_every_minute():
    vj = json.load(io.open(os.path.join(SITE, "vercel.json"), encoding="utf-8"))
    crons = {c["path"]: c["schedule"] for c in vj.get("crons") or []}
    assert crons.get("/api/cron/news-watch") == "* * * * *"
    assert os.path.exists(os.path.join(SITE, "api", "cron", "news-watch.mjs"))


def test_banner_tag_on_home_page():
    html = io.open(os.path.join(SITE, "index.html"), encoding="utf-8").read()
    assert html.count('<script src="/lib/live-banner.js" defer></script>') == 1
    js = io.open(os.path.join(SITE, "lib", "live-banner.js"), encoding="utf-8").read()
    assert "innerHTML" not in js, "the banner sets text with textContent only"


def _post(**k):
    p = {"id": "pdufa_x_2026-12-22", "ticker": "X", "kind": "approval", "text": "X's news release says the FDA approved Y.",
         "source": {"label": "X news release", "url": "https://www.sec.gov/a", "published_at": "2026-12-01T16:05:00-05:00"},
         "posted_at": "2026-12-01T16:06:10-05:00", "minutes_after_source": 1, "page": "/pdufa/X-y", "status": "posted"}
    p.update(k)
    return p


def test_sync_merge_is_append_only_and_retraction_is_final():
    s = importlib.import_module("sync_live_log")
    log, newly = s.merge({"posts": []}, [_post()])
    assert len(log["posts"]) == 1 and not newly
    log, newly = s.merge(log, [_post(status="retracted", retracted_at="2026-12-02T09:00:00-05:00", retract_reason="The FDA record says otherwise.")])
    assert log["posts"][0]["status"] == "retracted" and len(newly) == 1
    e = s.correction(newly[0])
    assert e["date"] == "2026-12-02" and e["page"] == "/pdufa/X-y"
    assert e["was"].startswith("An automatic post said: X's news release")
    assert e["now"].startswith("Retracted.") and "https://www.sec.gov/a" in e["source"]
    log2, newly = s.merge(log, [_post(status="confirmed")])
    assert log2["posts"][0]["status"] == "retracted" and not newly, "a retraction is final"
    # a later post on the same row is a new entry; it never rewrites the old one (red team #16)
    log3, _ = s.merge(log, [_post(status="posted", posted_at="2026-12-03T10:00:00-05:00", kind="crl", text="Other.")])
    assert len(log3["posts"]) == 2 and log3["posts"][0]["text"].startswith("X's news release")
    c, _ = s.merge({"posts": []}, [_post(status="confirmed")])
    c2, newly = s.merge(c, [_post(status="posted")])
    assert c2["posts"][0]["status"] == "confirmed" and not newly, "status only moves forward"
    c3, newly = s.merge(c, [_post(status="retracted", kind="crl", text="Changed.")])
    assert c3["posts"][0]["status"] == "confirmed" and not newly, "a feed entry that says something else is not this post"
    c4, newly = s.merge(c, [_post(status="retracted", retract_reason="hold")])
    assert c4["posts"][0]["status"] == "confirmed" and not newly, "a retraction the watch has not recorded (no time) waits (red team 7)"


def test_post_speed_takes_an_earlier_confirmed_live_time():
    b = importlib.import_module("build_post_speed")
    src = {"events": {"k": {"row": "pdufa_x_2026-12-22", "kind": "decision", "event": "FDA decision: approved",
                            "sources": [{"at": "2026-12-01T16:05:00-05:00", "url": "https://www.sec.gov/a", "label": "X 8-K"}]}}}
    rows = {"pdufa_x_2026-12-22": {"t": "X", "name": "Y", "url": "/pdufa/X-y"}}
    cache = {"k": {"site_at": "2026-12-01T18:00:00-05:00", "commit": "abc"}}
    live = {"pdufa_x_2026-12-22": _post(status="confirmed")}
    out, _ = b.compute(rows, src, dict(cache), [], "2026-12-02T00:00:00Z", live)
    assert out[0].get("via") == "news_watch" and out[0]["gap_min"] == 1 and out[0]["commit"] is None
    out, _ = b.compute(rows, src, dict(cache), [], "2026-12-02T00:00:00Z", {})
    assert out[0].get("via") is None and out[0]["gap_min"] == 115
    late = {"pdufa_x_2026-12-22": _post(status="confirmed", posted_at="2026-12-01T19:00:00-05:00")}
    out, _ = b.compute(rows, src, dict(cache), [], "2026-12-02T00:00:00Z", late)
    assert out[0].get("via") is None, "a later live time never replaces an earlier site time"
