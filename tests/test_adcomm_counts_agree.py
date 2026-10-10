# -*- coding: utf-8 -*-
"""CI guard: /adcomm states one count of meetings, everywhere it states one (audit 2026-10-04 UX P1).

The lede said "2 FDA advisory committee meetings", the FAQ "2 ... documented", and a section below the FAQ
listed 187 Federal Register notices including the same two meetings, unjoined. Fails, on the rendered page,
when: the lede's notice count, the FAQ's notice count, the history heading's count and the title's count
differ; the voted-meeting count in the lede/FAQ/title differs from the number of vote cards; the history
sits below the FAQ; or a vote card lacks its FR notice link.

    python tests/test_adcomm_counts_agree.py
"""
import html
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(HERE, "pdufa_site_src", "adcomm", "index.html")


def main():
    doc = io.open(P, encoding="utf-8", errors="replace").read()
    t = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>|<style.*?</style>", "", doc, flags=re.S))))
    fails = []
    title = re.search(r"<title>(.*?)</title>", doc, re.S).group(1)
    t_n = re.search(r"(\d+) Federal Register Notices, (\d+) Votes", title)
    lede = re.search(r"every one of the (\d+) drug and biologic advisory committee meetings the FDA announced", t)
    lede_v = re.search(r"This page lists (\d+) FDA advisory committee meetings? with a hand-sourced vote", t)
    hist = re.search(r"FDA advisory committee meetings, 2020 to \d{4}: (\d+) Federal Register notices", t)
    faq = re.search(r"(\d+) FDA advisory committee meetings announced in the Federal Register since January 2020 are listed[^.]*; (\d+) of them are documented", t)
    cards = re.findall(r'<a class="row" href="/adcomm/([A-Z]{1,6})-(\d{4}-\d{2}-\d{2})"', doc)
    nums = {"title": t_n and t_n.group(1), "lede": lede and lede.group(1), "history": hist and hist.group(1), "faq": faq and faq.group(1)}
    if len({v for v in nums.values()}) != 1 or None in nums.values():
        fails.append(f"notice counts disagree: {nums}")
    votes = {"title": t_n and t_n.group(2), "lede": lede_v and lede_v.group(1), "faq": faq and faq.group(2), "cards": str(len(cards))}
    if len({v for v in votes.values()}) != 1 or None in votes.values():
        fails.append(f"vote counts disagree: {votes}")
    a, b = doc.find("<!--ADCH:BEGIN-->"), doc.find("<!--HUBFAQ:BEGIN-->")
    if a < 0 or b < 0 or a > b:
        fails.append(f"history block is not above the FAQ (ADCH at {a}, HUBFAQ at {b})")
    for tk, d in cards:
        m = re.search(r'<a class="row" href="/adcomm/' + tk + "-" + d + r'".*?</a>', doc, re.S)
        if not m or "federalregister.gov" not in m.group(0):
            fails.append(f"vote card {tk} {d} does not link its Federal Register notice")
    if fails:
        print("FAIL: /adcomm disagrees with itself:")
        for f in fails:
            print("   " + f)
        return 1
    print(f"OK -- /adcomm: {nums['lede']} notices and {votes['cards']} votes stated consistently in title, lede, history and FAQ; "
          f"history above the FAQ; every vote card links its notice.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
