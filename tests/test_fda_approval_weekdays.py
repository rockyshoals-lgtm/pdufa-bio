# -*- coding: utf-8 -*-
"""CI guard: /research/fda-approval-weekdays (build_fda_approval_weekdays.py) counts dates on FDA records, rightly.

  * Drugs@FDA: recounted here from _fda_approvals_months.json (originals and efficacy supplements, one per application
    and submission, medical gases set apart by class or an MG letter): the weekday table (every cell), the lede, the
    weekend and holiday sentence, the medical-gas line, the CSV row by row, title and description.
  * Orange Book: recounted from the raw products file with csv ("~"): every NDA with no undated product at its
    earliest Approval_Date; the weekday table, the lede, the left-out, mixed and not-first-product counts, the
    weekend list, the CSV row by row, and the cross-check against Drugs@FDA (which NDAs carry a later date).
  * US federal holidays are worked out here from hand-written rules, spot-checked against known observed dates.
  * The weekend/holiday goal-date table is recounted from the decision-timing study's own CSV
    (fda-decision-timing-2026.csv): the rows, in order, each with its link, dates, weekdays, days, outcome and the kind
    of FDA record (classified here from the record's address); the counts in its sentence.
  * The /research card, the line on /research/fda-decision-timing and the JSON-LD carry the same numbers.
  * No forecast or tendency words in the page's own text (title, description and body; the sitewide footer is not
    this page's text).

PLANT=1 drops one NDA from the recount and must FAIL; PLANT=2 moves one holiday and must FAIL; PLANT=3 counts a
medical gas as an original approval and must FAIL.

    python tests/test_fda_approval_weekdays.py      (fix: python build_fda_approval_weekdays.py)
"""
import calendar
import csv
import datetime as dt
import html
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
ROOT = os.path.join(SITE, "research", "fda-approval-weekdays")
PAGE = os.path.join(ROOT, "index.html")
DAF_CSV = os.path.join(ROOT, "data", "drugs-at-fda-approval-dates.csv")
OB_CSV = os.path.join(ROOT, "data", "orange-book-nda-dates.csv")
STATS = os.path.join(HERE, "_fda_approval_weekdays.json")
PRODUCTS = os.path.join(HERE, "_orange_book", "products.txt")
DAF = os.path.join(HERE, "_fda_approvals_months.json")
TIMING = os.path.join(SITE, "research", "fda-decision-timing", "fda-decision-timing-2026.csv")
WD = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MONTHS = ["", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]
BAD = re.compile(r"\b(probabilit|odds\b|chances?\b|likel[yi]|predict|forecast|expect|tends?\b|usually|typically"
                 r"|often|generally|rarely|mostly|almost always|will be approved|will act)", re.I)
PLANT = os.environ.get("PLANT")


def holidays(year):
    """Hand-written rules for 5 U.S.C. 6103(a), observed dates labelled as such."""
    out = {}

    def fixed(month, day, name):
        d = dt.date(year, month, day)
        if PLANT == "2" and year == 1992 and name == "Independence Day":
            d += dt.timedelta(days=1)
        if d.weekday() == 5:
            out[d - dt.timedelta(days=1)] = name + " (observed)"
        elif d.weekday() == 6:
            out[d + dt.timedelta(days=1)] = name + " (observed)"
        else:
            out[d] = name

    def nth(month, weekday, n):
        days = [d for d in range(1, calendar.monthrange(year, month)[1] + 1)
                if dt.date(year, month, d).weekday() == weekday]
        return dt.date(year, month, days[n])

    fixed(1, 1, "New Year's Day")
    if year >= 1986:
        out[nth(1, 0, 2)] = "Martin Luther King Jr. Day"
    out[nth(2, 0, 2)] = "Washington's Birthday"
    out[nth(5, 0, -1)] = "Memorial Day"
    if year >= 2021:
        fixed(6, 19, "Juneteenth")
    fixed(7, 4, "Independence Day")
    out[nth(9, 0, 0)] = "Labor Day"
    out[nth(10, 0, 1)] = "Columbus Day"
    fixed(11, 11, "Veterans Day")
    out[nth(11, 3, 3)] = "Thanksgiving Day"
    fixed(12, 25, "Christmas Day")
    return out


def hol(d):
    return holidays(d.year).get(d) or holidays(d.year + 1).get(d) or ""


def pretty(d):
    return f"{MONTHS[d.month]} {d.day}, {d.year}"


def pct(a, b):
    """Halves round up, in integer arithmetic."""
    if 0 < a * 100 < b:
        t = (a * 2000 + b) // (2 * b)                       # tenths of a percent
        return f"{t // 10}.{t % 10}%"
    return f"{(a * 200 + b) // (2 * b)}%"


def num(n, zero="none"):
    return zero if n == 0 else f"{n:,}"


def plain(h):
    h = re.sub(r"<script.*?</script>|<style.*?</style>", " ", h, flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", h))).strip()


def table(h, name):
    m = re.search(r'<table data-weekdays="' + name + r'">(.*?)</table>', h, re.S)
    if not m:
        return None
    return [re.findall(r"<t[dh]>(.*?)</t[dh]>", tr, re.S) for tr in re.findall(r"<tr>(.*?)</tr>", m.group(1), re.S)]


def para(h, name):
    m = re.search(r'<p class="sub" data-weekdays="' + name + r'">(.*?)</p>', h, re.S)
    return plain(m.group(1)) if m else None


def kind_of(url):
    if url.startswith("https://download.open.fda.gov/crl/"):
        return "complete response letter"
    if "/appletter/" in url:
        return "corrected approval letter" if "correctedltr" in url.lower() else "approval letter"
    if url.startswith("https://www.fda.gov/media/"):
        return "approval letter"
    if "/scripts/cder/daf/" in url:
        return "Drugs@FDA action date"
    if "fda.gov" in url:
        return "FDA web notice"
    return "FDA record"


def counts(days):
    return [sum(1 for d in days if d.weekday() == i) for i in range(7)]


def main():
    fails = []
    for d, name in [(dt.date(1993, 12, 31), "New Year's Day (observed)"), (dt.date(2021, 6, 18), "Juneteenth (observed)"),
                    (dt.date(2026, 11, 26), "Thanksgiving Day"), (dt.date(2026, 7, 3), "Independence Day (observed)"),
                    (dt.date(2026, 5, 25), "Memorial Day"), (dt.date(2026, 1, 19), "Martin Luther King Jr. Day"),
                    (dt.date(2026, 10, 12), "Columbus Day"), (dt.date(2023, 11, 10), "Veterans Day (observed)"),
                    (dt.date(2026, 2, 16), "Washington's Birthday"), (dt.date(2022, 12, 26), "Christmas Day (observed)"),
                    (dt.date(2025, 9, 1), "Labor Day")]:
        if hol(d) != name:
            fails.append(f"holiday rule: {d} should be {name}, got {hol(d)!r}")
    if hol(dt.date(1985, 1, 21)) or hol(dt.date(2020, 6, 19)) or hol(dt.date(2025, 1, 20)) != "Martin Luther King Jr. Day":
        fails.append("holiday rule: MLK Day from 1986 only, Juneteenth from 2021 only")

    # ---- Drugs@FDA recount ----
    raw = json.load(io.open(DAF, encoding="utf-8"))
    orig, supp, gas, seen, readm = [], [], [], set(), {}
    for m in sorted(raw):
        for it in raw[m]["items"]:
            if (it["app"], it["sub"]) in seen:
                continue
            seen.add((it["app"], it["sub"]))
            readm[(it["app"], it["sub"])] = (raw[m].get("fetched") or "")[:10]
            g = it.get("class") == "Medical Gas" or re.search(r"MG[lL]tr\.pdf$", it.get("letter") or "")
            if it["kind"] == "new application":
                (orig if (not g or PLANT == "3") else gas).append(it)
            elif it["kind"] == "efficacy supplement":
                supp.append(it)
    day = lambda it: dt.date.fromisoformat(it["date"])  # noqa: E731
    lo = dt.date.fromisoformat(sorted(raw)[0] + "-01")
    hi = max(day(x) for x in orig + supp)
    co, cs = counts([day(x) for x in orig]), counts([day(x) for x in supp])
    no, ns = len(orig), len(supp)
    reads = sorted({(raw[m].get("fetched") or "")[:10] for m in raw} - {""})
    read_txt = f"read {reads[0]}" if len(reads) == 1 else f"read {reads[0]} to {reads[-1]}, the latest months last"

    h = io.open(PAGE, encoding="utf-8").read()
    lede = (f"Of the {no} original NDA and BLA approvals in Drugs@FDA (medical gases aside) from {pretty(lo)} to {pretty(hi)}, {co[4]} "
            f"({pct(co[4], no)}) carry a Friday action date and {num(co[5] + co[6])} a Saturday or Sunday date. Of the "
            f"{ns} efficacy supplement approvals, {cs[4]} ({pct(cs[4], ns)}) are Fridays and {num(cs[5] + cs[6])} fall "
            "on a weekend.")
    if f"read through openFDA ({read_txt})." not in (para(h, "sub") or ""):
        fails.append(f"read dates differ: want {read_txt!r}")
    if para(h, "lede") != lede:
        fails.append(f"lede differs:\n    page {para(h, 'lede')!r}\n    want {lede!r}")
    title = f"FDA Approval Dates by Day of the Week: {no + ns:,} Actions Counted | pdufa.bio"
    if f"<title>{html.escape(title)}</title>" not in h:
        fails.append("title differs")
    desc = (f"{co[4]} of {no} original FDA drug approvals since {lo.year} are dated on a Friday. Weekday counts from "
            "Drugs@FDA and the Orange Book, with every record as data.")
    if f'name="description" content="{html.escape(desc)}"' not in h or len(desc) > 155:
        fails.append(f"description differs or is over 155 characters ({len(desc)})")
    t = table(h, "daf")
    cc = [counts([day(x) for x in orig if x["app"].startswith("NDA")]),
          counts([day(x) for x in orig if x["app"].startswith("BLA")]), cs]
    exp = [["Weekday", "Original NDA", "Original BLA", "Efficacy supplement"]]
    exp += [[WD[i]] + [f"{c[i]:,} ({pct(c[i], sum(c))})" for c in cc] for i in range(7)]
    exp += [["Approvals"] + [f"{sum(c):,}" for c in cc]]
    if t != exp:
        fails.append("Drugs@FDA weekday table differs from recount")
    we = sorted([x for x in orig + supp if day(x).weekday() >= 5], key=lambda x: (day(x), x["app"]))
    hd = sorted([x for x in orig + supp if day(x).weekday() < 5 and hol(day(x))], key=lambda x: (day(x), x["app"]))
    gw = sum(1 for x in gas if day(x).weekday() >= 5)
    s = para(h, "daf-weekend") or ""
    want = [f"{len(we)} of these {no + ns:,} approvals are dated on a Saturday or Sunday",
            f"Drugs@FDA also lists {len(gas)} medical gas approvals in these months (letters marked MG), counted apart "
            f"from the table; {num(gw)} of them are dated on a Saturday or Sunday."]
    lab = lambda x: f"{x['brand'] or x['app']} {x['sub']}, {pretty(day(x))} ({WD[day(x).weekday()]}" + \
        (f", {hol(day(x))})" if hol(day(x)) else ")")  # noqa: E731
    full = (f"{len(we)} of these {no + ns:,} approvals are dated on a Saturday or Sunday"
            + (": " + "; ".join(lab(x) for x in we) + ". " if we else ". ")
            + ("None is dated on a weekday that was a US federal holiday. " if not hd else
               f"{len(hd)} are dated on a weekday that was a US federal holiday: " + "; ".join(lab(x) for x in hd) + ". ")
            + want[1] + " Approvals dated in the days just before a read may not have reached openFDA by then.")
    if s != full:
        fails.append(f"weekend/holiday paragraph differs:\n    page {s!r}\n    want {full!r}")

    rows = list(csv.DictReader(io.open(DAF_CSV, encoding="utf-8", newline="")))
    allx = sorted(orig + supp + gas, key=lambda x: (day(x), x["app"], x["sub"]))
    if len(rows) != len(allx):
        fails.append(f"Drugs@FDA CSV has {len(rows)} rows, recount {len(allx)}")
    for r, x in zip(rows, allx):
        k = "original" if x["kind"] == "new application" else "efficacy supplement"
        got = (r["application"], r["submission"], r["kind"], r["brand"], r["sponsor"], r["fda_action_date"], r["weekday"],
               r["federal_holiday"], r["medical_gas"] == "yes", r["letter"], r["source"])
        exp = (x["app"], x["sub"], k, x.get("brand") or "", x.get("sponsor") or "", x["date"], WD[day(x).weekday()],
               hol(day(x)), x in gas, x.get("letter") or "", f"openFDA drugsfda, read {readm[(x['app'], x['sub'])]}")
        if got != exp:
            fails.append(f"Drugs@FDA CSV row {got} != {exp}")
            break

    # ---- Orange Book recount ----
    prods, undated = {}, set()
    with io.open(PRODUCTS, encoding="utf-8", errors="replace", newline="") as fh:
        rd = csv.reader(fh, delimiter="~", quoting=csv.QUOTE_NONE)
        head = next(rd)
        ia, ino, ip, idt, itn = (head.index(c) for c in ("Appl_Type", "Appl_No", "Product_No", "Approval_Date",
                                                          "Trade_Name"))
        for f in rd:
            if len(f) <= idt or f[ia].strip() != "N":
                continue
            n = int(f[ino])
            if f[idt].strip() == "Approved Prior to Jan 1, 1982":
                undated.add(n)
                continue
            prods.setdefault(n, []).append((dt.datetime.strptime(f[idt].strip(), "%b %d, %Y").date(), f[ip].strip(),
                                            f[itn].strip(), f[head.index("Type")].strip(),
                                            f[head.index("Applicant_Full_Name")].strip() or f[head.index("Applicant")].strip()))
    first = {n: min(v) for n, v in prods.items() if n not in undated}
    if PLANT == "1":
        first.pop(sorted(first)[len(first) // 2])
    N = len(first)
    obd = [v[0] for v in first.values()]
    olo, ohi = min(obd), max(obd)
    cb = counts(obd)
    periods = [(1982, 1999), (2000, 2014), (2015, ohi.year)]
    pc = [counts([d for d in obd if a <= d.year <= b]) for a, b in periods]
    obl = (f"For NDAs since 1982, the Orange Book, the FDA's list of approved drug products, gives a longer record. Of "
           f"the {N:,} NDAs with an approval date on every product they list, from {pretty(olo)} to {pretty(ohi)}, the "
           f"earliest date listed is a Friday for {cb[4]:,} ({pct(cb[4], N)}) and a Saturday or Sunday for "
           f"{cb[5] + cb[6]}.")
    if para(h, "ob-lede") != obl:
        fails.append(f"Orange Book lede differs:\n    page {para(h, 'ob-lede')!r}\n    want {obl!r}")
    t = table(h, "by-day")
    exp = [["Weekday", "1982 to 1999", "2000 to 2014", f"2015 to {pretty(ohi)}", "All"]]
    exp += [[WD[i]] + [f"{c[i]:,} ({pct(c[i], sum(c))})" for c in pc] + [f"{cb[i]:,} ({pct(cb[i], N)})"]
            for i in range(7)]
    exp += [["NDAs"] + [f"{sum(c):,}" for c in pc] + [f"{N:,}"]]
    if t != exp:
        fails.append("Orange Book weekday table differs from recount")
    lim = para(h, "ob-limits") or ""
    not001 = sum(1 for v in first.values() if v[1] != "001")
    mixed = sum(1 for n in undated if n in prods)
    no001 = sum(1 for n, v in first.items() if v[1] != "001" and all(p[1] != "001" for p in prods[n]))
    ob_as_of_txt = io.open(os.path.join(HERE, "_orange_book", "_as_of.txt"), encoding="utf-8").read().split()[0]
    earliest = {}                                            # one per NDA: its earliest Drugs@FDA original approval
    for x in orig:
        if x["app"].startswith("NDA") and int(x["app"][3:]) in first:
            if x["app"] not in earliest or day(x) < day(earliest[x["app"]]):
                earliest[x["app"]] = x
    both = list(earliest.values())
    later = sorted([x for x in both if first[int(x["app"][3:])][0] > day(x)], key=day)
    for w in [f"{not001} of the {N:,} NDAs are dated by a product other than product 001 ({no001} of them list no "
              "product 001)", "An NDA no longer listed in the file, for any reason, is not counted.",
              f"The FDA files are dated {ob_as_of_txt};",
              f"{len(undated):,} NDAs with any product listed as \"Approved Prior to Jan 1, 1982\" are left out, "
              f"{mixed} of them with other products that are dated",
              f"For the {len(both)} NDAs with an original approval in Drugs@FDA since {lo.year} that are also in the "
              f"Orange Book, the Orange Book date is later than the Drugs@FDA action date for {len(later)}",
              f"the newest approval date in them is {pretty(ohi)}"] + \
            [f"{x['brand'] or x['app']}: {pretty(day(x))} and {pretty(first[int(x['app'][3:])][0])}" for x in later]:
        if w not in lim:
            fails.append(f"Orange Book limits lack {w!r}")
    obw = sorted((v[0], n, v[2]) for n, v in first.items() if v[0].weekday() >= 5)
    s = para(h, "ob-weekend") or ""
    if s != (f"The {len(obw)} NDAs whose earliest Orange Book date falls on a Saturday or Sunday, as the file prints "
             "them: " + "; ".join(f"{n:06d} {tn}, {pretty(d)} ({WD[d.weekday()]})" for d, n, tn in obw) + "."):
        fails.append("Orange Book weekend list differs")
    rows = list(csv.DictReader(io.open(OB_CSV, encoding="utf-8", newline="")))
    want = sorted(first.items(), key=lambda kv: (kv[1][0], kv[0]))
    if len(rows) != len(want):
        fails.append(f"Orange Book CSV has {len(rows)} rows, recount {len(want)}")
    for r, (n, (d, pno, tn, _t, ap)) in zip(rows, want):
        got = (r["nda"], r["earliest_orange_book_date"], r["weekday"], r["federal_holiday"], r["earliest_product_no"],
               r["trade_name"], r["product_types"], r["applicant"], r["orange_book_files_dated"])
        exp = (f"{n:06d}", d.isoformat(), WD[d.weekday()], hol(d), pno, tn,
               "/".join(sorted({p[3] for p in prods[n]})), ap, ob_as_of_txt)
        if got != exp:
            fails.append(f"Orange Book CSV row {got} != {exp}")
            break

    # ---- goal dates on weekends or holidays, from the timing study's CSV ----
    trows = list(csv.DictReader(io.open(TIMING, encoding="utf-8", newline="")))
    goal = []
    for r in trows:
        g, a = dt.date.fromisoformat(r["goal_date"]), dt.date.fromisoformat(r["fda_action_date"])
        if g.weekday() >= 5 or hol(g):
            goal.append((g, r["ticker"], r["decision_page"].rstrip("/").rsplit("/", 1)[-1], a, r["outcome"],
                         r["fda_record_url"], r["drug"], r["fda_record"]))
    goal.sort(key=lambda x: (x[0], x[1]))
    t = table(h, "goal-dates") or [[]]
    got = []
    for row in t[1:]:
        sl = re.search(r'href="/fda-decision/([^"]+)"', row[0])
        oc = re.search(r"\(([^()]*)\)\s*$", plain(row[0]))
        kd = re.search(r"\(([^()]*)\)\s*$", plain(row[4]))
        tk = re.search(r'">([^<]*?) &middot; ([^<]*)</a>', row[0])
        rh = re.search(r'<a href="([^"]+)">([^<]*)</a>', row[4])
        got.append((sl and sl.group(1), tk and html.unescape(tk.group(1)), plain(row[1]), plain(row[2]), plain(row[3]),
                    oc and oc.group(1), kd and kd.group(1), tk and html.unescape(tk.group(2)),
                    rh and html.unescape(rh.group(1)), rh and html.unescape(rh.group(2))))
    exp = []
    for g, tk, sl, a, oc, url, drug, rec in goal:
        dd = (a - g).days
        days = "on the goal date" if dd == 0 else f"{abs(dd)} {'day' if abs(dd) == 1 else 'days'} " \
                                                   f"{'before' if dd < 0 else 'after'}"
        dl = drug.replace(" - (", " (").replace(" - ", ", ")
        rl = rec[len("CRL letter "):] if kind_of(url) == "complete response letter" and rec.startswith("CRL letter ") \
            else rec
        exp.append((sl, tk, f"{pretty(g)} ({hol(g) or WD[g.weekday()]})", f"{pretty(a)} ({WD[a.weekday()]})", days,
                    oc, kind_of(url), dl, url, rl))
    if got != exp:
        fails.append(f"goal-date table differs: {[x for x in zip(got, exp) if x[0] != x[1]][:3]}")
    b = sum(1 for g, *_r in goal if _r[2] < g)
    near = sum(1 for g, *_r in goal if -3 <= (_r[2] - g).days < 0)
    o = sum(1 for g, *_r in goal if _r[2] == g)
    af = sum(1 for g, *_r in goal if _r[2] > g)
    fb = sum(1 for g, *_r in goal if _r[2].weekday() == 4 and 0 < (g - _r[2]).days <= 3)
    sent = (f"Of the {len(trows)} sourced 2026 decisions in our timing study, {len(goal)} had a goal date on a "
            f"Saturday, Sunday or federal holiday. The FDA record is dated before the goal date in {b} of them ({near} "
            f"within 3 days before, {fb} of those on the Friday just before), on the goal date in {o} and after it in "
            f"{af}.")
    if goal and not any(hol(x[0]) for x in goal):
        sent += " None of these goal dates fell on a federal holiday."
    ak = [kind_of(x[5]) for x in goal if x[3] > x[0]]
    if len(ak) == 1:
        sent += f" The record dated after the goal date is {'an' if ak[0][0] in 'aeiouAEIOUFN' else 'a'} {ak[0]}."
    elif ak:
        sent += " The records dated after the goal date are: " + "; ".join(ak) + "."
    hd2 = "weekend or holiday" if any(hol(x[0]) for x in goal) else "weekend"
    if goal and f"<h2>2026 decisions with a {hd2} goal date</h2>" not in h:
        fails.append("goal section heading differs")
    if goal and sent not in (para(h, "goal-lede") or ""):
        fails.append(f"goal sentence differs; want {sent!r}")

    # ---- card, timing line, JSON-LD ----
    hub = io.open(os.path.join(SITE, "research", "index.html"), encoding="utf-8").read()
    if (f"{co[4]} of {no} original FDA drug approvals since {lo.year} carry a Friday action date"
            not in html.unescape(hub)) or hub.count("<!--WEEKDAYS-CARD:BEGIN-->") != 1:
        fails.append("/research card missing or stale")
    tim = io.open(os.path.join(SITE, "research", "fda-decision-timing", "index.html"), encoding="utf-8").read()
    if goal and (f"{len(goal)} of these decisions had a goal date on a weekend or federal holiday" not in tim
                 or tim.count("<!--WEEKDAYS-LINK:BEGIN-->") != 1):
        fails.append("timing page line missing or stale")
    m = re.search(r'<script type="application/ld\+json">(\{"@context":"https://schema.org","@type":"Dataset".*?)</script>',
                  h, re.S)
    ld = json.loads(m.group(1)) if m else {}
    if ld.get("temporalCoverage") != f"{olo.isoformat()}/{hi.isoformat()}" or \
            f"{no + ns:,} original and efficacy supplement approval action dates" not in ld.get("description", "") or \
            f"of {N:,} NDAs" not in ld.get("description", "") or len(ld.get("distribution", [])) != 2:
        fails.append("JSON-LD Dataset differs from the recount")
    st = json.load(io.open(STATS, encoding="utf-8"))
    if (st["daf"]["n_orig"], st["daf"]["n_supp"], st["orange_book"]["n"]) != (no, ns, N):
        fails.append("guard file counts differ from the recount")

    # ---- the page's own words ----
    i, j = h.find("<h1"), h.find('<script type="application/ld+json">{"@context":"https://schema.org","@type":"Dataset"')
    own = plain(h[i:j]) + " " + title + " " + desc
    m = BAD.search(own)
    if m:
        fails.append(f"forecast or tendency word on the page: {m.group(0)!r}")

    if fails:
        print(f"FAIL test_fda_approval_weekdays: {len(fails)} problem(s); fix: python build_fda_approval_weekdays.py")
        for f in fails[:20]:
            print("  " + f)
        return 1
    print(f"PASS test_fda_approval_weekdays: Drugs@FDA {no} originals and {ns} supplements, Orange Book {N:,} NDAs, "
          f"{len(goal)} weekend or holiday goal dates of {len(trows)}: all recounted")
    return 0


if __name__ == "__main__":
    sys.exit(main())
