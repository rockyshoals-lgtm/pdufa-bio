# -*- coding: utf-8 -*-
"""CI guard: indexing is automatic, exact and single-sourced (2026-11-20, indexing round 3).

Found on Nov 20: build_sitemap.py ran twice in pdufa-rebuild.yml and BOTH runs saved _sitemap_lastmod.json. A page
regenerated early in the run hashes one way before the link and badge passes and another way after them, so each run
saw "changed" twice and re-dated it: /conference/AACR and /patent-cliff/2026 differed from the day before only in their
own date stamps, yet carried a new lastmod, and 387 URLs claimed a change that morning (1,299 on Nov 18). Google's crawl
stats show 95% of its ~25 fetches a day spent re-fetching known pages ("Refresh"), 5% discovering new ones, with 1,612
pages discovered and never crawled. A sitemap that says everything changed buys exactly that.

Checks:
  1. only the LAST build_sitemap.py call in pdufa-rebuild.yml saves lastmod state; every earlier one has --no-state
     (plant: PLANT_TWO_WRITERS=1 drops the flag in memory and must FAIL);
  2. the ping step submits the pages changed since the tag indexed-ok, is not continue-on-error (a page no engine was
     told about fails the run), and moves the tag only after it succeeds;
  3. changed_since() picks exactly the pages whose hash or date moved or that entered the sitemap (planted states);
  4. the section sitemaps, where built, list every sitemap.xml URL exactly once, and the index names each of them.

    python tests/test_indexing_pipeline.py
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
sys.path.insert(0, HERE)
_argv, sys.argv = sys.argv, sys.argv[:1]
import ping_search_engines as P  # noqa: E402
sys.argv = _argv


def main():
    fails = []
    wf = open(os.path.join(HERE, ".github", "workflows", "pdufa-rebuild.yml"), encoding="utf-8").read()
    if os.environ.get("PLANT_TWO_WRITERS") == "1":
        wf = wf.replace("build_sitemap.py --no-state", "build_sitemap.py")

    # 1. one writer of the lastmod state, and it is the last sitemap pass
    calls = re.findall(r"^\s*run:.*?python build_sitemap\.py([^\n]*)$", wf, re.M)
    if not calls:
        fails.append("pdufa-rebuild.yml no longer runs build_sitemap.py")
    else:
        writers = [i for i, rest in enumerate(calls) if "--no-state" not in rest]
        if writers != [len(calls) - 1]:
            fails.append(f"build_sitemap.py runs {len(calls)} time(s); state-saving runs at positions {writers}, "
                         f"expected only the last ({len(calls) - 1}). Every earlier pass needs --no-state, or each "
                         f"rebuild re-dates every page the later passes touch.")

    # 2. the ping step: exact set, loud, tag moved only on success
    m = re.search(r"- name: Ping search engines.*?(?=\n      - name:|\Z)", wf, re.S)
    step = m.group(0) if m else ""
    if "ping_search_engines.py --since" not in step:
        fails.append("ping step does not pass --since (the base commit of the last successful submission)")
    if re.search(r"continue-on-error:\s*true", step):
        fails.append("ping step is continue-on-error: a failed submission would pass silently")
    if "HEAD:refs/tags/indexed-ok" not in step or \
            step.find("HEAD:refs/tags/indexed-ok") < step.find("python ping_search_engines.py"):
        fails.append("ping step does not move the tag indexed-ok after the submission")

    # 3. the changed set, on planted states
    U = "https://www.pdufa.bio/"
    old = {"pdufa_site_src/index.html": {"hash": "a", "date": "2026-11-19"},
           "pdufa_site_src/pdufa/CAPR/index.html": {"hash": "b", "date": "2026-11-18"},
           "pdufa_site_src/drug/x/index.html": {"hash": "c", "date": "2026-11-01"},
           "pdufa_site_src/drug/hidden/index.html": {"hash": "h", "date": "2026-11-01"}}
    new = dict(old)
    new["pdufa_site_src/pdufa/CAPR/index.html"] = {"hash": "B", "date": "2026-11-20"}       # real change
    new["pdufa_site_src/fda-decision/X-2026-11-19/index.html"] = {"hash": "n", "date": "2026-11-20"}  # new page
    new["pdufa_site_src/drug/hidden/index.html"] = {"hash": "H", "date": "2026-11-20"}       # changed but noindex
    sm_old = "".join(f"<url><loc>{U}{p}</loc></url>" for p in ("", "pdufa/CAPR", "drug/x"))
    sm_new = "".join(f"<url><loc>{U}{p}</loc></url>" for p in ("", "pdufa/CAPR", "drug/x", "fda-decision/X-2026-11-19",
                                                                 "calendar"))
    got = P.changed_since(old, new, sm_old, sm_new)
    want = {U + "pdufa/CAPR", U + "fda-decision/X-2026-11-19", U + "calendar"}
    if got != want:
        fails.append(f"changed_since picked {sorted(got)}, expected {sorted(want)}")
    if P.changed_since(old, old, sm_old, sm_old):
        fails.append("changed_since found changes between identical states")
    if P.key_to_url("pdufa_site_src/index.html") != U or P.key_to_url("pdufa_site_src/about/index.html") != U + "about":
        fails.append("key_to_url maps state keys to the wrong URLs")

    # 4. section sitemaps cover sitemap.xml exactly once
    idx = os.path.join(SITE, "sitemap_index.xml")
    if os.path.exists(idx):
        full = P.sitemap_urls(open(os.path.join(SITE, "sitemap.xml"), encoding="utf-8").read())
        seen, parts = [], re.findall(r"<loc>https://www\.pdufa\.bio/(sitemap-[a-z]+\.xml)</loc>",
                                     open(idx, encoding="utf-8").read())
        for part in parts:
            f = os.path.join(SITE, part)
            if not os.path.exists(f):
                fails.append(f"sitemap_index.xml names {part}, which was not built")
                continue
            seen += re.findall(r"<loc>([^<]+)</loc>", open(f, encoding="utf-8").read())
        if sorted(seen) != sorted(full):
            fails.append(f"section sitemaps list {len(seen)} URL(s) ({len(set(seen))} distinct) for "
                         f"{len(full)} in sitemap.xml")

    if fails:
        print("FAIL: indexing pipeline")
        for f in fails:
            print("   " + f)
        return 1
    print("OK -- one lastmod writer (the last sitemap pass); submissions are the exact changed set, loud on failure, "
          "tag moved after success; section sitemaps cover sitemap.xml once.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
