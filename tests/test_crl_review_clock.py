# -*- coding: utf-8 -*-
"""CI guard: /crl/review-clock and crl-review-clock.csv (build_crl_review_clock.py), checked against the raw release.

Written apart from crl_review_clock.py, so a fault in that reader shows here:

  * the CSV has one row per distinct Complete Response Letter in the newest openFDA snapshot (the /crl repeat rule),
    the letters the FDA rescinded as issued in error left out, recounted here from the raw records;
  * every date the CSV says a letter prints is printed in that letter's text, before "completed our review", next to
    the word the CSV gives ("received", "dated", "submitted"); a response and the earlier letter it answers are both
    printed there, in order before the letter's date; every day count is the difference of its two dates;
  * recall: a letter whose opening prints "received <date>" has a received date in the CSV;
  * a "receipt to letter" row is an original application whose text before "completed our review" names no earlier
    FDA action, that the FDA does not head as a corrected letter or an acknowledgement, and for whose application number
    the release holds no earlier CRL; a counted row is never a supplement;
  * a response row's two dates stand in one sentence that says the response "constituted" a response to (or came
    "after") the earlier letter, whose kind is printed there; recall: a letter not counted, other than a supplement, a
    re-headed letter or one with dates out of order, never prints "<date> ... constituted a ... response to our <date>"
    about anything but a refuse-to-file letter;
  * the goal-date flag, the "earlier letter in the release" and "earlier CRL in the release" columns are recomputed;
  * hand-checked letters (KNOWN) read as a person reads the PDF text;
  * the page: every statistic (median, 25th and 75th percentiles by the inclusive method, shortest, longest, n) is
    recomputed here from the CSV, the lede, the left-out counts, the sentences with counts, every counted row and its
    days; no forecast words in the title, the description or the page's prose (company names in the table excepted).

PLANT=1 makes the shortest receipt-to-letter count a day shorter and must FAIL; PLANT=2 changes one hand-checked date and must FAIL.

    python tests/test_crl_review_clock.py      (fix: python build_crl_review_clock.py)
"""
import csv
import datetime as dt
import glob
import html
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(HERE, "pdufa_site_src", "crl", "review-clock", "index.html")
CSVP = os.path.join(HERE, "pdufa_site_src", "crl", "data", "crl-review-clock.csv")
PLANT = os.environ.get("PLANT", "")
MON = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November",
       "December"]
BAD = re.compile(r"\b(probabilit|odds\b|chances?\b|likel[yi]|predict|forecast|because of|caused?\b|due to|led to"
                 r"|signal|will be approved|delay|how long before)", re.I)
FIRST, RESP = "receipt to letter, no earlier action named", "response to an earlier FDA letter"
# letter date, applications -> (received, response, earlier letter, counted_in prefix), read by hand from the text
KNOWN = {
    ("2020-05-21", "NDA 210852"): ("2017-09-28", "2019-12-04", "2019-11-20", "response"),
    ("2023-01-13", "NDA 204311"): ("2013-12-23", "2022-07-15", "2019-08-06", "response"),
    ("2015-07-30", "NDA 206185"): ("2014-01-31", "2015-04-09", "2014-11-24", "response"),
    ("2013-01-30", "NDA 022517"): ("2009-06-22", "2012-07-30", "2010-04-22", "response"),
    ("2026-06-23", "BLA 761266"): ("2021-08-02", "2025-12-27", "2025-01-03", "response"),
    ("2021-08-18", "BL 125734"): ("2020-05-19", "", "", "receipt"),
    ("2021-06-24", "NDA 215179"): ("2021-08-27", "", "", "not counted: dates out of order"),   # skipped if openFDA drops it
    ("2026-07-09", "NDA 216586"): ("2023-05-16", "2026-01-23", "2025-03-20", "response"),
    ("2019-08-06", "NDA 204311"): ("2013-12-23", "2019-02-06", "2014-10-23", "response"),
    ("2019-01-23", "NDA 202860"): ("2018-07-23", "", "", "not counted: earlier CRL in the release"),
    ("2018-11-30", "NDA 209511"): ("2016-10-31", "", "", "not counted: refuse to file"),
    ("2015-09-23", "NDA 204417"): ("2012-05-29", "", "", "not counted"),
}


def corpus():
    c = sorted(glob.glob(os.path.join(HERE, "CRL_corpus_openFDA_*.json")))
    return c[-1] if c else None


def iso(s):
    m = re.match(r"(\d{2})/(\d{2})/(\d{4})$", str(s or "").strip())
    return f"{m.group(3)}-{m.group(1)}-{m.group(2)}" if m else ""


def printed(d):
    """regex for an ISO date as a letter prints it: "March 10, 2017" (spacing and the comma's spacing loose)"""
    y, m, dd = d.split("-")
    return MON[int(m) - 1] + r"\s+0?" + str(int(dd)) + r"\s*,\s*" + y


def letters():
    raw = json.load(io.open(corpus(), encoding="utf-8"))
    recs = raw["results"]
    seen, out, resc = set(), [], []
    allnum = {}
    for r in recs:
        d, typ = iso(r.get("letter_date")), str(r.get("letter_type") or "")
        apps = sorted(str(x).strip() for x in r.get("application_number") or [])
        txt = re.sub(r"\s+", " ", str(r.get("text") or "")).strip()
        if d and "RESCIND" in typ.upper():
            resc.append((txt, apps))
        if not d or typ != "COMPLETE RESPONSE":
            continue
        for a in apps:
            allnum.setdefault(re.sub(r"\D", "", a.split("/")[0]).lstrip("0"), set()).add(d)
        k = (d, tuple(apps), txt.lower())
        if k in seen:
            continue
        seen.add(k)
        out.append({"date": d, "apps": ", ".join(apps), "nums": {re.sub(r"\D", "", a.split("/")[0]) for a in apps},
                    "text": txt})
    gone = set()
    for txt, apps in resc:
        m = re.search(r"refer to our letters? dated (.{0,120}?)(?:,? informing|\.)", txt, re.I)
        nums = {re.sub(r"\D", "", a.split("/")[0]) for a in apps}
        for mm in re.finditer(r"(" + "|".join(MON) + r") (\d{1,2}), (\d{4})", m.group(1) if m else ""):
            d = f"{mm.group(3)}-{MON.index(mm.group(1)) + 1:02d}-{int(mm.group(2)):02d}"
            for i, L in enumerate(out):
                if L["date"] == d and L["nums"] & nums:
                    gone.add(i)
    return [L for i, L in enumerate(out) if i not in gone], allnum


def pre_text(t):
    i = re.search(r"refer\s+to\s+your", t, re.I)
    if not i:
        return ""
    rest = t[i.start():]
    j = re.search(r"completed\s+(?:our|its|the)\s+review|cannot\s+(?:tentatively\s+)?approve", rest, re.I)
    return rest[:j.start()] if j else rest[:1500]


def q(xs, p):
    """percentile, inclusive method: linear between order statistics at position (n-1)p"""
    xs = sorted(xs)
    pos = (len(xs) - 1) * p
    lo = int(pos)
    return xs[lo] + (xs[min(lo + 1, len(xs) - 1)] - xs[lo]) * (pos - lo)


def g(x):
    return f"{x:g}"


def statcells(xs):
    xs = sorted(xs)
    n = len(xs)
    mid = f"{g(q(xs, .25))} to {g(q(xs, .75))}" if n >= 4 else "too few letters"
    return [str(n), g(q(xs, .5)), mid, str(xs[0]), str(xs[-1])]


def main():
    P = []
    if not corpus() or not os.path.exists(PAGE) or not os.path.exists(CSVP):
        print("FAIL test_crl_review_clock: corpus, page or CSV missing; fix: python build_crl_review_clock.py")
        return 1
    rows = list(csv.DictReader(io.open(CSVP, encoding="utf-8-sig")))
    Ls, allnum = letters()
    # one row per letter
    want = sorted((L["date"], L["apps"]) for L in Ls)
    got = sorted((r["letter_date"], ", ".join(sorted(x.strip() for x in r["applications"].split(",") if x.strip())))
                 for r in rows)
    if want != got:
        P.append(f"CSV rows ({len(got)}) are not the {len(want)} distinct unrescinded CRLs: "
                 f"missing {sorted(set(want) - set(got))[:3]}, extra {sorted(set(got) - set(want))[:3]}")
    texts = {}
    for L in Ls:
        texts.setdefault((L["date"], L["apps"]), []).append(L["text"])
    D = lambda s: dt.date.fromisoformat(s)  # noqa: E731
    for r in rows:
        key = (r["letter_date"], ", ".join(sorted(x.strip() for x in r["applications"].split(",") if x.strip())))
        cands = texts.get(key) or [""]
        pres = [pre_text(t) for t in cands]
        ok = lambda f: any(f(p) for p in pres)   # noqa: E731
        lab = f'{r["applications"]} {r["letter_date"]}'
        rec, word = r["received_date_printed"], r["received_word"]
        wrx = r"(?:received|recieved|feceived)" if word == "received" else word
        if rec and not ok(lambda p: re.search(wrx + r"\W{0,4}(?:and\s+)?(?:on\s+)?" + printed(rec), p, re.I) or (
                word == "dated" and re.search(r"refer\s+to\s+your\s+" + printed(rec) + r"\s*,?\s*(?:new\s+drug|biologics?)",
                                              p, re.I))):
            P.append(f"{lab}: received {rec} ({word}) is not printed so in the letter")
        if not rec and ok(lambda p: re.search(r"refer\s+to\s+your[^.]{0,200}?received\W{0,3}(?:on\s+)?(?:"
                                              + "|".join(MON) + r")\s+\d", p, re.I)):
            P.append(f"{lab}: the opening prints a received date and the CSV has none")
        rs, ea = r["response_dated"], r["earlier_fda_letter_dated"]
        if rs or ea:
            if not (rs and ea and ok(lambda p: re.search(printed(rs), p) and re.search(printed(ea), p))):
                P.append(f"{lab}: response {rs} or earlier letter {ea} is not printed in the letter")
        for col, a, b in (("days_received_to_letter", rec, r["letter_date"]),
                          ("days_response_to_letter", rs, r["letter_date"]),
                          ("days_earlier_letter_to_response", ea, rs)):
            exp = str((D(b) - D(a)).days) if a and b else ""
            if r[col] != exp:
                P.append(f"{lab}: {col} {r[col]!r} != {exp!r}")
        c = r["counted_in"]
        full = " ".join(cands)
        nums = {re.sub(r"\D", "", a.split("/")[0]).lstrip("0") for a in r["applications"].split(",") if a.strip()}
        e_crl = any(x < r["letter_date"] for n in nums for x in allnum.get(n, ()))
        if r["earlier_crl_in_release"] != ("yes" if e_crl else "no"):
            P.append(f"{lab}: earlier_crl_in_release {r['earlier_crl_in_release']!r}, recount {e_crl}")
        if ea and r["earlier_letter_in_release"] != ("yes" if any(ea in allnum.get(n, ()) for n in nums) else "no"):
            P.append(f"{lab}: earlier_letter_in_release {r['earlier_letter_in_release']!r} disagrees with the release")
        gx = re.search(r"(?:major\s+amendment.{0,120}?|submission\s+of\s+which\s+)extended\s+the\s+(?:\w+\s+){0,3}"
                       r"(?:goal\s+date|review\s+clock|action\s+date)", full[:6000], re.I)
        if r["says_goal_date_extended"] != ("yes" if gx else "no"):
            P.append(f"{lab}: says_goal_date_extended {r['says_goal_date_extended']!r}, text {bool(gx)}")
        if c != FIRST and c != RESP and not c.startswith("not counted: "):
            P.append(f"{lab}: counted_in {c!r}")
        if not c.startswith("not counted") and (r["supplement"] != "no" or re.search(r"/\s*S-?\d", r["applications"])):
            P.append(f"{lab}: a supplement is counted")
        if c == FIRST:
            if not rec or int(r["days_received_to_letter"]) < 0:
                P.append(f"{lab}: receipt-to-letter row without a received date in order")
            if e_crl:
                P.append(f"{lab}: receipt-to-letter row, but the release holds an earlier CRL on the application")
            if re.search(r"CORRECTED\s+COMPLETE|ACKNOWLEDGE\s+INCOMPLETE", full[:800]):
                P.append(f"{lab}: receipt-to-letter row on a re-headed letter")
            if ok(lambda p: re.search(r"response\s+to\s+our[^.]{0,80}?(?:action|complete\s+response|tentative|"
                                      r"approvable|refus)\w*\s+letter|refus\w*[\s-]+to[\s-]+file|resubmi|rescind"
                                      r"|tentative(?:ly)?\s+approv|(?<!this )approvable\s+letter"
                                      r"|(?<!this )complete\s+response\s+letter", p, re.I)):
                P.append(f"{lab}: counted receipt to letter but names an earlier FDA action")
        if c == RESP:
            if not (ea and rs and ea <= rs <= r["letter_date"]):
                P.append(f"{lab}: response dates not in order")
            kind = r["earlier_letter_kind"].replace(" ", r"\s+")
            if not kind or not ok(lambda p: any(re.search(printed(rs), sn) and re.search(printed(ea), sn)
                                                and re.search(r"constitut|after\s+our", sn, re.I)
                                                and re.search(kind, sn, re.I) for sn in re.split(r"\.\s", p))):
                P.append(f"{lab}: response {rs}, earlier {r['earlier_letter_kind']} letter {ea} not paired in one sentence")
        if c.startswith("not counted") and not re.search(r"supplement|headed|out of order", c):
            dd = r"(?:" + "|".join(MON) + r")\s+\d{1,2}\s*,\s*(?:19|20)\d\d"
            # both dates printed (a redacted response date is no pairing), and not a refuse-to-file letter answered
            hit = ok(lambda p: any(re.search(dd + r"[^.]{0,120}?constitut\w*\s+(?:a\s+|your\s+)?(?:complete\s+)?responses?"
                                             r"\s+to\s+our\s+" + dd, sn, re.I) and not re.search(r"refus", sn, re.I)
                                   for sn in re.split(r"\.\s", p)))
            if hit:
                P.append(f"{lab}: not counted ({c}) but prints a response to a dated earlier letter")
    by = {}
    for r in rows:    # keyed by the letter date and the first application number, so a reordered list still matches
        by.setdefault((r["letter_date"], re.sub(r"\D", "", r["applications"].split(",")[0].split("/")[0]).lstrip("0")), r)
    for k, (rec, rs, ea, c) in KNOWN.items():
        if PLANT == "2" and k == ("2013-01-30", "NDA 022517"):
            ea = "2010-04-21"
        r = by.get((k[0], re.sub(r"\D", "", k[1]).lstrip("0")))
        if not r:
            if k != ("2021-06-24", "NDA 215179"):
                P.append(f"KNOWN {k}: no CSV row")
            continue
        if (r["received_date_printed"], r["response_dated"], r["earlier_fda_letter_dated"]) != (rec, rs, ea) \
                or not r["counted_in"].startswith(c):
            P.append(f"KNOWN {k}: CSV reads {r['received_date_printed']}, {r['response_dated']}, "
                     f"{r['earlier_fda_letter_dated']}, {r['counted_in']!r}; by hand {rec}, {rs}, {ea}, {c!r}")
    first = [r for r in rows if r["counted_in"] == FIRST]
    resp = [r for r in rows if r["counted_in"] == RESP]
    if len(first) < 200 or len(resp) < 80:
        P.append(f"only {len(first)} receipt-to-letter and {len(resp)} response letters read (floors 200 and 80): the reader "
                 "has stopped reading the letters' dates")
    fd = [int(r["days_received_to_letter"]) for r in first]
    if PLANT == "1":      # the shortest receipt-to-letter count, a day shorter: the page's "shortest" must disagree
        fd[fd.index(min(fd))] -= 1
    rd = [int(r["days_response_to_letter"]) for r in resp]
    gd = [int(r["days_earlier_letter_to_response"]) for r in resp]
    # the page
    doc = io.open(PAGE, encoding="utf-8").read()
    cells = lambda attr: [html.unescape(re.sub(r"<[^>]+>", "", c)).strip() for c in  # noqa: E731
                          re.findall(r"<td[^>]*>(.*?)</td>", (re.search(r'<tr data-clock-row="' + re.escape(attr) + r'">(.*?)</tr>',
                                                                       doc, re.S) or [None, ""])[1], re.S)][1:]
    exp_rows = {"first-all": fd, "resp-letter": rd, "resp-gap": gd}
    secs = {}
    for r, d in zip(first, fd):
        sp = r["statute_section_printed"]
        secs.setdefault("multi" if ";" in sp else (sp or "none"), []).append(d)
    for k, v in secs.items():
        exp_rows[f"sec-{k}"] = v
    years = {"year-2026": (2025, 2026), "year-2024": (2023, 2024), "year-2022": (2020, 2022), "year-2019": (0, 2019)}
    for k, (y0, y1) in years.items():
        v = [d for r, d in zip(first, fd) if y0 <= int(r["letter_date"][:4]) <= y1]
        if v:
            exp_rows[k] = v
    for k, v in exp_rows.items():
        if cells(k) != statcells(v):
            P.append(f"page row {k}: {cells(k)} != {statcells(v)}")
    plain = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", doc.split("<h1>", 1)[-1])))
    plain = re.sub(r"\s+([.,;)])", r"\1", plain)
    s = statcells(fd)
    nd = sum(1 for r in first if r["received_word"] != "received")
    lede = (f"Of the {len(rows)} Complete Response Letters in the FDA's release (rescinded letters left out), "
            f"{len(first)} are on an original application, name no earlier FDA action, and print the date the FDA "
            f"received the application" + (f" (or, for {nd}, only the date it was dated or submitted)" if nd else "")
            + f". From that date to the letter: median {s[1]} calendar days, middle half {s[2]}, shortest {s[3]}, "
            f"longest {s[4]}. {len(resp)} letters answer a response to an earlier FDA letter and print both dates: "
            f"median {statcells(rd)[1]} days from the response to the letter. These are days between printed dates, "
            f"not FDA review time.")
    if lede not in plain:
        P.append("the lede does not match the CSV")
    need = [f"{sum(1 for r in first if r['says_goal_date_extended'] == 'yes')} of these {len(first)} letters say a "
            f"submission extended the goal date",
            f"For {sum(1 for r in resp if r['earlier_letter_in_release'] == 'yes')} of these {len(resp)} letters, the "
            f"release also holds a Complete Response Letter of that earlier date"]
    kinds = {}
    for r in resp:
        kinds[r["earlier_letter_kind"]] = kinds.get(r["earlier_letter_kind"], 0) + 1
    need.append("The earlier letters, as the letters name them: " + "; ".join(
        f"{v} {k} letter{'s' if v != 1 else ''}" for k, v in sorted(kinds.items(), key=lambda kv: (-kv[1], kv[0]))) + ".")
    ndr = [r for r in rows if r["counted_in"] in ("not counted: no date", "not counted: no opening")]
    if ndr:
        st = {}
        for r in ndr:
            st[r["openfda_status"] or "not given"] = st.get(r["openfda_status"] or "not given", 0) + 1
        need.append(f"Of the {len(ndr)} letters with no readable received date, openFDA's approval_status field marks "
                    + "; ".join(f"{v} {k}" for k, v in sorted(st.items(), key=lambda kv: -kv[1])) + ".")
    for x in need:
        if x not in plain:
            P.append(f"text missing: {x!r}")
    head = re.search(r"<title>(.*?)</title>", doc, re.S)
    desc = re.search(r'<meta name="description" content="([^"]*)"', doc)
    ttl, dsc = html.unescape(head.group(1)) if head else "", html.unescape(desc.group(1)) if desc else ""
    if f"{len(rows)} FDA Letters" not in ttl or "Not FDA review time" not in dsc or f"{len(first)} released FDA CRLs" \
            not in dsc or f"(median {s[1]})" not in dsc:
        P.append(f"title or description does not state the counts: {ttl!r} / {dsc!r}")
    for w in (ttl, dsc):
        if BAD.search(w):
            P.append(f"forecast or reason word in the title or description: {BAD.search(w).group(0)!r}")
    left = {}
    for r in rows:
        if r["counted_in"].startswith("not counted: "):
            k = r["counted_in"][len("not counted: "):]
            left[k] = left.get(k, 0) + 1
    for k, v in left.items():
        m = re.search(r'<tr data-clock-left="' + re.escape(html.escape(k)) + r'"><td>.*?</td><td>(\d+)</td>', doc)
        if not m or int(m.group(1)) != v:
            P.append(f"left-out row {k!r}: page {m.group(1) if m else None}, CSV {v}")
    # every counted row on the page, with its days
    trs = re.findall(r'<tr data-clock="[^"]+"><td>(.*?)</td><td>(.*?)</td>.*?<td>([^<]*)</td></tr>', doc, re.S)
    if len(trs) != len(first) + len(resp):
        P.append(f"page lists {len(trs)} counted letters, CSV {len(first) + len(resp)}")
    want_rows = sorted(((r["letter_date"], html.unescape(r["applications"]),
                         r["days_response_to_letter"] if r in resp else r["days_received_to_letter"])
                        for r in first + resp))
    got_rows = []
    for a, b, days in trs:
        m = re.search(r"(" + "|".join(MON) + r") (\d{1,2}), (\d{4})", html.unescape(re.sub(r"<[^>]+>", "", a)))
        d = f"{m.group(3)}-{MON.index(m.group(1)) + 1:02d}-{int(m.group(2)):02d}" if m else ""
        got_rows.append((d, html.unescape(b), days))
    if sorted(got_rows) != want_rows:
        P.append(f"page rows differ from the CSV: {sorted(set(want_rows) ^ set(got_rows))[:3]}")
    body = doc.split("<h1>", 1)[-1].split('<div class="legal"', 1)[0]     # the page's own words, to the legal footer
    prose = re.sub(r'<tr data-clock="[^"]+">.*?</tr>', " ", body, flags=re.S)   # company names (openFDA's) out
    prose = html.unescape(re.sub(r"<[^>]+>", " ", prose))
    if BAD.search(prose):
        P.append(f"forecast or reason word: {BAD.search(prose).group(0)!r}")
    if 'href="/crl/data/crl-review-clock.csv"' not in doc:
        P.append("no link to the CSV")
    if P:
        print(f"FAIL test_crl_review_clock: {len(P)} problem(s); fix: python build_crl_review_clock.py")
        for p in P[:25]:
            print("  " + p)
        return 1
    print(f"ok test_crl_review_clock: {len(rows)} letters, {len(first)} receipt-to-letter and {len(resp)} response letters "
          "checked against the release")
    return 0


if __name__ == "__main__":
    sys.exit(main())
