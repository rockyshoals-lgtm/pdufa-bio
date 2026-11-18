# -*- coding: utf-8 -*-
"""CI guard: a page's lastmod (and its "Page updated" stamp and dateModified, which read the same state)
moves when the page's own content changes, not when a site-wide statistic or a countdown ticks.

2026-11-18 (Google SEO): between the Nov 12 and Nov 13 refreshes the sitemap re-dated 497 of 1,799 URLs,
and 449 of them had changed only in the run-up study's size ("study of 1,885 FDA decisions" -> 1,886,
"(n=897)" -> 898) or a countdown ("in 17 days" -> 16). Google says it uses lastmod only when it is
consistently accurate; Search Console showed 1,588 URLs discovered and never crawled.

Checks (all planted, nothing read from the network):
  1. a page that differs only in the study size, cohort medians or countdowns hashes the same;
  2. a page that differs in a fact about its subject (a decision date, a new row, a reworded
     sentence, a 13F value) hashes differently;
  3. state written under the previous hash definition migrates without re-dating an unchanged page,
     and still re-dates a page whose content really changed;
  4. advisory: each mask still matches something on the built site (a template reword that orphans a
     mask brings the churn back; it is printed, not failed, because it cannot make a page wrong).

    python tests/test_lastmod_ignores_sitewide_stats.py
"""
import glob
import io
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import build_sitemap as B  # noqa: E402

BASE = ('<html><head><title>CGEM PDUFA</title></head><body><h1>CGEM PDUFA date: CLN-081</h1>'
        '<div class="pill">{bd} business days to decision · 2027-02-27</div>'
        '<div class="kv"><span>PDUFA date</span><b>2027-02-27</b></div>'
        '<div class="kv"><span>Business days away</span><b>{bd}</b></div>'
        '<a class="row" href="/pdufa/X"><span class="t">Nov 30, 2026 <span class="up">in {days} days</span></span></a>'
        '<b>{pct}% median (n={n})</b>'
        '<p>We have no measured history for CGEM itself. Across the whole study of {study} FDA decisions, the median '
        'stock rose {pk}% at its best point in the 120 trading days before the decision, but was only {pre}% higher '
        'the day before.</p>'
        '<p>Historically, small-cap names had a median decision-day move of {pct}% in either direction ({tier} small-cap '
        'decisions in our {study}-decision run-up study, 2020-26).</p>'
        '<div>{el} of 120 sessions elapsed, {left} to go. Cohort context: across {study} past decisions the median peak '
        'from T-120 was {pk}% and the median move to the day before the decision was {pre}%.</div>'
        '<p>See the <a href="/research">run-up study</a>, built on {study} decisions.</p>'
        '<td>RA Capital Management</td><td>{f13}</td>'
        '</body></html>')
A = dict(bd=166, days=17, pct="3.5", n="257", study="1,885", pk="18.0", pre="2.4", tier=122, el=65, left=55,
         f13="$634.8 million")


def page(**kw):
    d = dict(A)
    d.update(kw)
    return BASE.format(**d)


def main():
    fails = []
    h0 = B.content_hash(page())

    # 1. site-wide statistics and countdowns alone
    for kw in (dict(study="1,886"), dict(n="258"), dict(pct="3.6"), dict(pk="18.1", pre="2.5"), dict(tier=123),
               dict(bd=165, days=16, el=66, left=54), dict(days=1),
               dict(study="1,886", n="258", bd=165, days=16, el=66, left=54, tier=123)):
        if B.content_hash(page(**kw)) != h0:
            fails.append(f"hash moved when only site-wide figures changed: {kw}")

    # 2. real content changes must still move the hash
    real = {
        "decision date": page().replace("2027-02-27", "2027-03-27"),
        "13F value": page(f13="$533.6 million"),
        "new row": page().replace("</body>", '<a class="row" href="/fda-decision/CGEM-2026-11-17">Approved</a></body>'),
        "reworded sentence": page().replace("the median stock rose", "the typical stock rose"),
        "drug name": page().replace("CLN-081", "zipalertinib"),
    }
    for what, html in real.items():
        if B.content_hash(html) == h0:
            fails.append(f"hash did NOT move for a real change: {what}")

    # 3. migration from state written under the previous definition
    saved_state, saved_today, saved_head = B._STATE, B.TODAY, B.head_version
    try:
        B.TODAY = "2026-11-18"
        old, new_stats, new_real = page(), page(study="1,886", days=16), page(f13="$533.6 million")
        key = "pdufa_site_src/pdufa/CGEM/index.html"
        B.head_version = lambda k: old            # HEAD holds the last deployed copy
        for html, want, label in ((old, "2026-11-12", "unchanged page"),
                                  (new_stats, "2026-11-12", "stats-only change"),
                                  (new_real, "2026-11-18", "real change")):
            B._STATE = {key: {"hash": B.content_hash_v1(old), "date": "2026-11-12"}}
            got = B.last_changed("pdufa/CGEM/index.html", __file__, html)
            if got != want:
                fails.append(f"migration, {label}: lastmod {got}, expected {want}")
            if B._STATE[key].get("hv") != B.HASH_VERSION:
                fails.append(f"migration, {label}: state not stamped with hash version {B.HASH_VERSION}")
        # after migration, same-definition comparison
        B._STATE = {key: {"hash": B.content_hash(old), "date": "2026-11-12", "hv": B.HASH_VERSION}}
        if B.last_changed("pdufa/CGEM/index.html", __file__, new_stats) != "2026-11-12":
            fails.append("post-migration: a stats-only change re-dated the page")
        if B.last_changed("pdufa/CGEM/index.html", __file__, new_real) != "2026-11-18":
            fails.append("post-migration: a real change did not re-date the page")
    finally:
        B._STATE, B.TODAY, B.head_version = saved_state, saved_today, saved_head

    # 4. advisory: every mask still finds its sentence somewhere on the built site
    site = os.path.join(HERE, "pdufa_site_src")
    pages = [p for p in glob.glob(os.path.join(site, "*", "*", "index.html")) if os.sep + "_" not in p][:2500]
    blob = "".join(io.open(p, encoding="utf-8", errors="replace").read() for p in pages[:2500])
    orphan = [rx.pattern for rx, _ in B.VOLATILE if not rx.search(blob)]
    for o in orphan:
        print(f"  note: mask matches nothing on the built site now (template reworded?): {o}")

    if fails:
        print("FAIL: lastmod must follow the page's own content, not site-wide figures:")
        for f in fails:
            print("   " + f)
        return 1
    print(f"OK -- study size, cohort medians and countdowns leave the hash alone; {len(real)} kinds of real "
          f"change move it; v1 state migrates without re-dating unchanged pages. {len(B.VOLATILE)} masks, "
          f"{len(B.VOLATILE) - len(orphan)} matched on the built site.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
