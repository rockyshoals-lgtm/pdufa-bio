# -*- coding: utf-8 -*-
"""CI guard: /crl/offices (build_crl_offices.py) states what the released letters' signature blocks print.

  * Every status row and every year row, every column, equals a recount from the letters (build_feeds.crl_letters
    and build_feeds.signature), the "All letters" row equals the distinct CRLs in the release (the /crl rule), and
    named + Center only + neither = letters in each row.
  * Every office and division row's count equals the letters whose signature block names it, and the tables hold
    every name the letters print.
  * The lede and the centers sentence say exactly what a recount says, and every Approved letter counted as naming
    no unit is listed by name.
  * No forecast words (probability, odds, chance, likely, predict, forecast) and no words that give a reason for
    what the letters print (to hide, because, stopped naming, policy).

PLANT=1 recounts with one letter's office removed and must FAIL; PLANT=2 flips one letter's (b) (4) flag and must
FAIL; PLANT=3 flips one letter's center and must FAIL.

    python tests/test_crl_offices.py      (fix: python build_crl_offices.py)
"""
import collections
import html
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
P = os.path.join(HERE, "pdufa_site_src", "crl", "offices", "index.html")


def cells(row):
    return [html.unescape(re.sub(r"<[^>]+>", "", c)).strip() for c in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)]


def section(doc, h2):
    i = doc.find(f"<h2>{h2}</h2>")
    if i < 0:
        return []
    j = doc.find("</table>", i)
    return [cells(r) for r in re.findall(r"<tr>(.*?)</tr>", doc[i:j], re.S) if "<td" in r]


def span(doc, key, tag="p"):
    m = re.search(rf'data-crl-offices="{key}">(.*?)</{tag}>', doc, re.S)
    return html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip() if m else None


def main():
    import build_crl_offices as O
    from build_feeds import crl_letters
    if not os.path.exists(P):
        print("FAIL test_crl_offices: /crl/offices missing; fix: python build_crl_offices.py")
        return 1
    doc = io.open(P, encoding="utf-8", errors="replace").read()
    letters, _, _ = crl_letters(include_rescinded=True)
    plant = os.environ.get("PLANT")
    if plant == "1":
        x = next(L for L in letters if L["sig"]["office"])
        x["sig"] = dict(x["sig"], office="")
    elif plant == "2":
        x = letters[0]
        x["sig"] = dict(x["sig"], withheld=not x["sig"]["withheld"])
    elif plant == "3":
        x = next(L for L in letters if L["sig"]["center"] == "CDER")
        x["sig"] = dict(x["sig"], center="CBER")
    fails = []

    want_status = collections.defaultdict(list)
    want_year = collections.defaultdict(list)
    for L in letters:
        want_status[L["status"] or "not given"].append(L)
        want_year[str(L["date"].year)].append(L)
    for h2, want in (("By openFDA approval status", want_status), ("By letter year", want_year)):
        got = {r[0]: r for r in section(doc, h2) if r and r[0] != "All letters"}
        if set(got) != set(want):
            fails.append(f"{h2}: rows {sorted(got)} are not {sorted(want)}")
        for k, ls in want.items():
            exp = [str(v) for v in O.tally(ls)]
            if k in got and got[k][1:6] != exp:
                fails.append(f"{h2}, row {k}: {got[k][1:6]} is not the recount {exp}")
        for r in got.values():
            n, u, c, no = (int(v) for v in r[1:5])
            if u + c + no != n:
                fails.append(f"{h2}, row {r[0]}: {u} + {c} + {no} is not {n}")
    allrow = next((r for r in section(doc, "By openFDA approval status") if r and r[0] == "All letters"), None)
    if not allrow or allrow[1:6] != [str(v) for v in O.tally(letters)]:
        fails.append(f"All letters row {allrow[1:6] if allrow else None} is not the recount "
                     f"{[str(v) for v in O.tally(letters)]}")

    for key, h2 in (("office", "Every office named"), ("division", "Every division named")):
        want = collections.Counter(L["sig"][key] for L in letters if L["sig"][key])
        got = {r[0]: int(r[1]) for r in section(doc, h2)}
        if got != dict(want):
            diff = sorted(set(want) ^ set(got)) or [k for k in want if want[k] != got.get(k)]
            fails.append(f"{h2}: the table does not match the letters ({diff[:3]})")

    f, status = O.figures(letters)
    if span(doc, "lede") != O.lede_text(f):
        fails.append(f"the lede does not say the recount: {span(doc, 'lede')!r}")
    if span(doc, "centers", "span") != O.centers_text(f):
        fails.append(f"the centers sentence does not say the recount: {span(doc, 'centers', 'span')!r}")
    unread = [L for L in status.get("Approved", []) if O.kind(L) != "unit"]
    ul = span(doc, "unread") or ""
    for L in unread:
        if L["app_txt"] not in ul:
            fails.append(f"Approved letter {L['app_txt']} {L['date']} counted as naming no unit is not listed")

    end = doc.find('<div class="legal"')  # the site's legal footer is not this page's own text
    body = html.unescape(re.sub(r"<[^>]+>", " ", doc[doc.find("<h1"):end if end > 0 else None]))
    if re.search(r"\b(probabilit|odds\b|chances?\b|likel[yi]|predict|forecast)", body, re.I):
        fails.append("the page carries a forecast word")
    if re.search(r"\b(to hide|because the FDA|stopped naming|policy|in order to)\b", body, re.I):
        fails.append("the page gives a reason for what the letters print")
    if fails:
        print(f"FAIL test_crl_offices: {len(fails)} problem(s); fix: python build_crl_offices.py")
        for x in fails[:20]:
            print("  " + x)
        return 1
    print(f"PASS test_crl_offices: {len(letters)} letters, {len(section(doc, 'Every office named'))} offices")
    return 0


if __name__ == "__main__":
    sys.exit(main())
