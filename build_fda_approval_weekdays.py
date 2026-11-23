# -*- coding: utf-8 -*-
"""/research/fda-approval-weekdays: on what weekday FDA drug approvals are dated, counted from FDA records.

Audit 2026-11-17, moat move 8 ("more sourced base-rate tables ... weekend goal dates, each with n, as-of date
and method, and never as a per-drug probability").

Three counts, all of dated FDA records:

1. Drugs@FDA action dates (openFDA drugsfda, cached month by month in _fda_approvals_months.json by
   build_fda_approvals_months.py, which runs earlier in CI): original NDA and BLA approvals (ORIG) and efficacy
   supplement approvals, January 2025 on, by weekday and US federal holiday. Medical gas approvals (letters marked
   MG, or class "Medical Gas") are counted on their own line, not in the tables.
2. This site's 2026 decision-timing study (build_early_decisions.collect, the rows of
   /research/fda-decision-timing): each decision whose company-stated goal date fell on a Saturday, Sunday or federal
   holiday, with the date of the FDA record linked on that row and what kind of record it is.
3. The longer record, labelled as the Orange Book's dates and not as action dates: for every NDA in the Orange Book
   products file whose every product is dated, the earliest Approval_Date listed. The page says where those dates
   are known to differ from Drugs@FDA's, with the count measured on the NDAs in both files.

Red team 2026-11-23 (16 items): the first draft called the Orange Book date "the FDA's approval date". For 2025-2026
NDAs in both files it is later than the Drugs@FDA action date for some (SIMTRIYO: Drugs@FDA July 24, Orange Book
Oct 30, 2026), and an NDA whose prescription products left the file is dated by a later product (an OTC switch,
for example). So the FDA's own action dates lead, and the Orange Book section carries those limits with numbers.

Counts only: nothing here says when a pending application will be acted on. Writes the page, two CSVs,
_fda_approval_weekdays.json for the guard, a card on /research and a line on /research/fda-decision-timing.
tests/test_fda_approval_weekdays.py recounts from the raw files with its own parser and holiday rules.
"""
import collections
import csv
import decimal
import datetime as dt
import io
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
SITE = os.path.join(HERE, "pdufa_site_src")
OB_DIR = os.path.join(HERE, "_orange_book")
DAF = os.path.join(HERE, "_fda_approvals_months.json")
SLUG = "/research/fda-approval-weekdays"
ROOT = os.path.join(SITE, "research", "fda-approval-weekdays")
INDEX = os.path.join(ROOT, "index.html")
DAF_CSV = "data/drugs-at-fda-approval-dates.csv"
OB_CSV = "data/orange-book-nda-dates.csv"
STATS = os.path.join(HERE, "_fda_approval_weekdays.json")
BASE = "https://www.pdufa.bio"
OB_URL = "https://www.fda.gov/drugs/drug-approvals-and-databases/orange-book-data-files"
DAF_URL = "https://open.fda.gov/apis/drug/drugsfda/"
UNDATED = "Approved Prior to Jan 1, 1982"

from build_crl_companies import page  # noqa: E402
from build_crl_facts import esc  # noqa: E402

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]
CARD_BEGIN, CARD_END = "<!--WEEKDAYS-CARD:BEGIN-->", "<!--WEEKDAYS-CARD:END-->"
LINK_BEGIN, LINK_END = "<!--WEEKDAYS-LINK:BEGIN-->", "<!--WEEKDAYS-LINK:END-->"


def pretty(d):
    return f"{MONTHS[d.month - 1]} {d.day}, {d.year}"


def nth_weekday(y, m, wd, n):
    """n-th (1-based) weekday wd (0 = Monday) of month m; n = -1 for the last."""
    if n > 0:
        d = dt.date(y, m, 1)
        d += dt.timedelta(days=(wd - d.weekday()) % 7)
        return d + dt.timedelta(weeks=n - 1)
    d = dt.date(y + (m == 12), m % 12 + 1, 1) - dt.timedelta(days=1)
    return d - dt.timedelta(days=(d.weekday() - wd) % 7)


def federal_holidays(y):
    """The annual US federal holidays of 5 U.S.C. 6103(a) for year y, at their observed dates (Saturday -> Friday
    before, Sunday -> Monday after; an observed date is labelled "(observed)"). Martin Luther King Jr. Day from 1986,
    Juneteenth from 2021. Inauguration Day (6103(c), Washington area only) and one-off closures by executive order
    are not included."""
    fixed = [(1, 1, "New Year's Day"), (7, 4, "Independence Day"), (11, 11, "Veterans Day"),
             (12, 25, "Christmas Day")]
    if y >= 2021:
        fixed.append((6, 19, "Juneteenth"))
    out = {}
    for m, d, name in fixed:
        day = dt.date(y, m, d)
        if day.weekday() == 5:
            out[day - dt.timedelta(days=1)] = name + " (observed)"
        elif day.weekday() == 6:
            out[day + dt.timedelta(days=1)] = name + " (observed)"
        else:
            out[day] = name
    floating = [(1, 0, 3, "Martin Luther King Jr. Day"), (2, 0, 3, "Washington's Birthday"),
                (5, 0, -1, "Memorial Day"), (9, 0, 1, "Labor Day"), (10, 0, 2, "Columbus Day"),
                (11, 3, 4, "Thanksgiving Day")]
    for m, wd, n, name in floating:
        if name.startswith("Martin") and y < 1986:
            continue
        out[nth_weekday(y, m, wd, n)] = name
    return out


def holiday_of(d):
    # New Year's Day on a Saturday is observed on December 31 of the year before
    return federal_holidays(d.year).get(d) or federal_holidays(d.year + 1).get(d) or ""


def pct(a, b):
    if not b:
        return ""
    v = 100 * a / b                                    # halves round up (decimal arithmetic, not banker's)
    q = decimal.Decimal(a * 100) / decimal.Decimal(b)
    if 0 < v < 1:
        return f"{q.quantize(decimal.Decimal('0.1'), rounding=decimal.ROUND_HALF_UP)}%"
    return f"{q.quantize(decimal.Decimal('1'), rounding=decimal.ROUND_HALF_UP)}%"


def is_gas(it):
    return str(it.get("class") or "") == "Medical Gas" or bool(re.search(r"MG[lL]tr\.pdf$", str(it.get("letter") or "")))


def read_daf():
    """Drugs@FDA approvals from the cache: (originals, supplements, gases, months covered, fetched)."""
    if not os.path.exists(DAF):
        return [], [], [], [], {}
    d = json.load(io.open(DAF, encoding="utf-8"))
    orig, supp, gas, fetched = [], [], [], {}
    seen = set()
    for month in sorted(d):
        fetched[month] = str(d[month].get("fetched") or "")[:10]
        for it in d[month].get("items") or []:
            k = (it.get("app"), it.get("sub"))
            if k in seen:
                continue
            seen.add(k)
            x = dict(it, day=dt.date.fromisoformat(it["date"]), read=fetched[month])
            if it.get("kind") == "new application":
                (gas if is_gas(it) else orig).append(x)
            elif it.get("kind") == "efficacy supplement":
                supp.append(x)
    key = lambda x: (x["day"], x["app"], x["sub"])  # noqa: E731
    return sorted(orig, key=key), sorted(supp, key=key), sorted(gas, key=key), sorted(d), fetched


def read_orange_book():
    """NDA number -> (earliest Approval_Date, product number, trade name, product type(s), applicant) for NDAs whose
    every product is dated. Raises on a date string that is neither a date nor the file's undated marker."""
    p = os.path.join(OB_DIR, "products.txt")
    prods, undated = collections.defaultdict(list), set()
    for line in io.open(p, encoding="utf-8", errors="replace").read().splitlines()[1:]:
        f = line.split("~")
        if len(f) < 14 or f[5].strip() != "N":
            continue
        n = int(f[6])
        raw = f[9].strip()
        if raw == UNDATED:
            undated.add(n)
            continue
        d = dt.datetime.strptime(raw, "%b %d, %Y").date()       # anything else is an error, not "undated"
        prods[n].append((d, f[7].strip(), f[2].strip(), f[12].strip(), f[13].strip() or f[3].strip()))
    first, has001 = {}, {}
    for n, ps in prods.items():
        if n in undated:
            continue
        d, pno, tn, _, ap = min(ps)
        types = "/".join(sorted({p[3] for p in ps}))
        first[n] = (d, pno, tn, types, ap)
        has001[n] = any(p[1] == "001" for p in ps)
    as_of = ""
    ap = os.path.join(OB_DIR, "_as_of.txt")
    if os.path.exists(ap):
        parts = io.open(ap, encoding="utf-8").read().split()
        as_of = parts[0] if parts else ""
    return first, len(undated), len([n for n in undated if n in prods]), as_of, has001


def num(n, zero):
    return zero if n == 0 else f"{n:,}"


def counts(days):
    c = collections.Counter(d.weekday() for d in days)
    return [c[i] for i in range(7)]


def source_kind(url):
    u = str(url or "")
    if "download.open.fda.gov/crl" in u:
        return "complete response letter"
    if "appletter" in u and "corrected" in u.lower():
        return "corrected approval letter"
    if "appletter" in u or "fda.gov/media/" in u:
        return "approval letter"
    if "scripts/cder/daf" in u:
        return "Drugs@FDA action date"
    if "fda.gov" in u:
        return "FDA web notice"
    return "FDA record"


def weekend_goal_rows():
    from build_early_decisions import collect
    allr = collect(2026)
    rows = []
    for r in allr:
        g, a = dt.date.fromisoformat(r["goal"]), dt.date.fromisoformat(r["actual"])
        hol = holiday_of(g)
        if g.weekday() < 5 and not hol:
            continue
        rows.append({"ticker": r["ticker"], "drug": r["drug"], "goal": g, "goal_holiday": hol,
                     "actual": a, "delta": (a - g).days, "outcome": r["outcome"], "slug": r["slug"],
                     "record": r["fda_record"], "url": r["fda_url"], "kind": source_kind(r["fda_url"])})
    rows.sort(key=lambda x: (x["goal"], x["ticker"]))
    return rows, len(allr)


def art(kind):
    return ("an " if kind[0] in "aeiouAEIOU" or kind.startswith(("FDA", "NDA")) else "a ") + kind


def record_label(rec, kind):
    """The timing study's record label, without repeating the kind ("CRL letter CRL_NDA..." -> "CRL_NDA...")."""
    rec = str(rec or "FDA record")
    if kind == "complete response letter":
        rec = re.sub(r"^CRL letter\s+", "", rec)
    return rec


def drug_label(drug):
    """The timing study's drug name, with its spaced hyphens written as commas ("X - (TRIAL)" -> "X (TRIAL)")."""
    return re.sub(r"\s+-\s+(?=\()", " ", re.sub(r"\s+-\s+(?!\()", ", ", str(drug)))


def days_text(n):
    if n == 0:
        return "on the goal date"
    w = "day" if abs(n) == 1 else "days"
    return f"{abs(n)} {w} {'before' if n < 0 else 'after'}"


def day_label(d):
    h = holiday_of(d)
    return f"{pretty(d)} ({DAYS[d.weekday()]}{', ' + h if h else ''})"


def letter_link(it, label):
    u = str(it.get("letter") or "").strip()
    if not re.match(r"^https://www\.accessdata\.fda\.gov/[^\s;]+\.pdf$", u):   # one letter, nothing else
        return esc(label)
    return f'<a href="{esc(u)}">{esc(label)}</a>'


def main():
    orig, supp, gas, months, fetched = read_daf()
    first, n_undated, n_mixed, ob_as_of, has001 = read_orange_book()
    reads = sorted(set(fetched.values()) - {""})
    read_lo, read_hi = (reads[0], reads[-1]) if reads else ("", "")
    read_txt = (f"read {read_hi}" if read_lo == read_hi else
                f"read {read_lo} to {read_hi}, the latest months last")
    if not orig or not first:
        print("fda-approval-weekdays: Drugs@FDA cache or Orange Book file missing; page left as it was")
        return 0

    # ---- 1. Drugs@FDA ----
    lo = dt.date.fromisoformat(months[0] + "-01")         # the first month asked of openFDA
    hi = max(orig[-1]["day"], supp[-1]["day"] if supp else orig[-1]["day"])
    cols = [("Original NDA", [x["day"] for x in orig if x["app"].startswith("NDA")]),
            ("Original BLA", [x["day"] for x in orig if x["app"].startswith("BLA")]),
            ("Efficacy supplement", [x["day"] for x in supp])]
    co = counts([x["day"] for x in orig])
    cs = counts([x["day"] for x in supp])
    no, ns = len(orig), len(supp)
    daf_weekend = [x for x in orig + supp if x["day"].weekday() >= 5]
    daf_weekend.sort(key=lambda x: (x["day"], x["app"]))
    daf_hol = sorted([x for x in orig + supp if x["day"].weekday() < 5 and holiday_of(x["day"])],
                     key=lambda x: (x["day"], x["app"]))
    gas_we = sum(1 for x in gas if x["day"].weekday() >= 5)

    # ---- 2. goal dates ----
    goal_rows, n_study = weekend_goal_rows()
    before = sum(1 for x in goal_rows if x["delta"] < 0)
    near = sum(1 for x in goal_rows if -3 <= x["delta"] < 0)
    on = sum(1 for x in goal_rows if x["delta"] == 0)
    after = sum(1 for x in goal_rows if x["delta"] > 0)
    goal_hol = sum(1 for x in goal_rows if x["goal_holiday"])
    fri_before = sum(1 for x in goal_rows
                     if x["actual"].weekday() == 4 and 0 < (x["goal"] - x["actual"]).days <= 3)

    # ---- 3. Orange Book ----
    obd = sorted(v[0] for v in first.values())
    ob_lo, ob_hi = obd[0], obd[-1]
    N = len(first)
    periods = [(1982, 1999), (2000, 2014), (2015, ob_hi.year)]
    pc = [counts([d for d in obd if a <= d.year <= b]) for a, b in periods]
    cb = counts(obd)
    ob_weekend = sorted(((v[0], n, v[2]) for n, v in first.items() if v[0].weekday() >= 5))
    not001 = sum(1 for v in first.values() if v[1] != "001")
    no001 = sum(1 for n, v in first.items() if v[1] != "001" and not has001[n])
    # the NDAs in both files: Drugs@FDA's original approvals from January 2025 on, against the Orange Book's date
    both, later, earlier = [], [], []
    for x in orig:                                         # orig is sorted by date: keep each NDA's earliest
        if not x["app"].startswith("NDA"):
            continue
        n = int(x["app"][3:])
        if n in first and all(y["app"] != x["app"] for y in both):
            both.append(x)
            if first[n][0] > x["day"]:
                later.append((x, first[n]))
            elif first[n][0] < x["day"]:
                earlier.append((x, first[n]))
    later.sort(key=lambda p: p[0]["day"])

    # ---- CSVs ----
    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
    with io.open(os.path.join(ROOT, *DAF_CSV.split("/")), "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["application", "submission", "kind", "brand", "sponsor", "fda_action_date", "weekday",
                    "federal_holiday", "medical_gas", "letter", "source", "license"])
        for x in sorted(orig + supp + gas, key=lambda x: (x["day"], x["app"], x["sub"])):
            w.writerow([x["app"], x["sub"], "original" if x["kind"] == "new application" else "efficacy supplement",
                        x.get("brand") or "", x.get("sponsor") or "", x["day"].isoformat(), DAYS[x["day"].weekday()],
                        holiday_of(x["day"]), "yes" if is_gas(x) else "", x.get("letter") or "",
                        f"openFDA drugsfda, read {x['read']}", "CC BY 4.0 https://pdufa.bio"])
    with io.open(os.path.join(ROOT, *OB_CSV.split("/")), "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["nda", "earliest_orange_book_date", "weekday", "federal_holiday", "earliest_product_no",
                    "trade_name", "product_types", "applicant", "orange_book_files_dated", "license"])
        for n in sorted(first, key=lambda k: (first[k][0], k)):
            d, pno, tn, types, ap = first[n]
            w.writerow([f"{n:06d}", d.isoformat(), DAYS[d.weekday()], holiday_of(d), pno, tn, types, ap, ob_as_of,
                        "CC BY 4.0 https://pdufa.bio"])

    # ---- page ----
    lede = (f"Of the {no} original NDA and BLA approvals in Drugs@FDA (medical gases aside) from {pretty(lo)} to {pretty(hi)}, "
            f"{co[4]} ({pct(co[4], no)}) carry a Friday action date and {num(co[5] + co[6], 'none')} a Saturday or "
            f"Sunday date. Of the {ns} efficacy supplement approvals, {cs[4]} ({pct(cs[4], ns)}) are Fridays and "
            f"{num(cs[5] + cs[6], 'none')} fall on a weekend.")
    title = f"FDA Approval Dates by Day of the Week: {no + ns:,} Actions Counted | pdufa.bio"
    desc = (f"{co[4]} of {no} original FDA drug approvals since {lo.year} are dated on a Friday. Weekday counts "
            "from Drugs@FDA and the Orange Book, with every record as data.")
    goal_lede = ""
    if goal_rows:
        goal_lede = (f"Of the {n_study} sourced 2026 decisions in our timing study, {len(goal_rows)} had a goal "
                     f"date on a Saturday, Sunday or federal holiday. The FDA record is dated before the goal date "
                     f"in {before} of them ({near} within 3 days before, {fri_before} of those on the Friday just "
                     f"before), on the goal date in {on} and after it in {after}.")
        if not goal_hol:
            goal_lede += " None of these goal dates fell on a federal holiday."
        ak = [x["kind"] for x in goal_rows if x["delta"] > 0]
        if ak:
            goal_lede += (f" The record dated after the goal date is {art(ak[0])}." if len(ak) == 1 else
                          " The records dated after the goal date are: " + "; ".join(ak) + ".")
    B = ['<h1>On what weekday <span class="g">FDA approvals are dated</span></h1>',
         f'<p class="sub" data-weekdays="lede">{esc(lede)}</p>',
         f'<p class="sub" data-weekdays="sub">An action date is the date the FDA gives its decision in Drugs@FDA, '
         f'its public database of approved drugs, read through <a href="{DAF_URL}">openFDA</a> ({esc(read_txt)}). '
         'An NDA is a new drug application and a BLA a biologics license application; an efficacy supplement changes '
         'the approved use of a drug, such as a new indication, patient group or dose. These are counts of dates on past FDA records: they do not say when any '
         'pending application will be acted on.</p>',
         f'<h2>FDA action dates by weekday, {esc(pretty(lo))} to {esc(pretty(hi))}</h2>',
         '<table data-weekdays="daf"><tr><th>Weekday</th>' + "".join(f'<th>{esc(c)}</th>' for c, _ in cols)
         + '</tr>']
    cc = [counts(ds) for _, ds in cols]
    for i, name in enumerate(DAYS):
        B.append(f'<tr><td>{name}</td>'
                 + "".join(f'<td>{c[i]:,} ({pct(c[i], sum(c))})</td>' for c in cc) + '</tr>')
    B.append('<tr><td>Approvals</td>' + "".join(f'<td>{sum(c):,}</td>' for c in cc) + '</tr></table>')
    wtxt = (f"{len(daf_weekend)} of these {no + ns:,} approvals are dated on a Saturday or Sunday"
            + (":" if daf_weekend else "."))
    B.append(f'<p class="sub" data-weekdays="daf-weekend">{esc(wtxt)} '
             + "; ".join(f'{letter_link(x, (x.get("brand") or x["app"]) + " " + x["sub"])}, {esc(day_label(x["day"]))}'
                         for x in daf_weekend)
             + (". " if daf_weekend else " ")
             + esc((f"{len(daf_hol)} are" if daf_hol else "None is") + " dated on a weekday that was a US federal holiday"
                   + (": " if daf_hol else "."))
             + "; ".join(f'{letter_link(x, (x.get("brand") or x["app"]) + " " + x["sub"])}, {esc(day_label(x["day"]))}'
                         for x in daf_hol)
             + ("." if daf_hol else "") + " "
             + esc(f"Drugs@FDA also lists {len(gas)} medical gas approvals in these months (letters marked MG), "
                   f"counted apart from the table; {num(gas_we, 'none')} of them are dated on a Saturday or Sunday. "
                   "Approvals dated in the days just before a read may not have reached openFDA by then.")
             + '</p>')

    if goal_rows:
        B.append('<h2>2026 decisions with a ' + ('weekend or holiday' if goal_hol else 'weekend') + ' goal date</h2>')
        B.append(f'<p class="sub" data-weekdays="goal-lede">{esc(goal_lede)} The table covers approvals and complete '
                 'response letters for NDAs and BLAs, as in <a href="/research/fda-decision-timing">the decision '
                 'timing study</a>. '
                 'The goal date is the one the company stated; the FDA date is the date of the record linked on each '
                 'row, and the last column says what kind of record it is.</p>')
        B.append('<table data-weekdays="goal-dates"><tr><th>Decision</th><th>Goal date</th>'
                 '<th>FDA record dated</th><th>Days</th><th>FDA record</th></tr>')
        for x in goal_rows:
            g = f'{pretty(x["goal"])} ({x["goal_holiday"] or DAYS[x["goal"].weekday()]})'
            a = f'{pretty(x["actual"])} ({DAYS[x["actual"].weekday()]})'
            rl = record_label(x["record"], x["kind"])
            rec = f'<a href="{esc(x["url"])}">{esc(rl)}</a>' if x["url"] else esc(rl)
            B.append(f'<tr><td><a href="/fda-decision/{esc(x["slug"])}">{esc(x["ticker"])} &middot; '
                     f'{esc(drug_label(x["drug"]))}</a> ({esc(x["outcome"])})</td><td>{esc(g)}</td><td>{esc(a)}</td>'
                     f'<td>{esc(days_text(x["delta"]))}</td><td>{rec} ({esc(x["kind"])})</td></tr>')
        B.append('</table>')

    ob_lede = (f"For NDAs since 1982, the Orange Book, the FDA's list of approved drug products, gives a longer record. "
               f"Of the {N:,} NDAs with an approval date on every product they list, from {pretty(ob_lo)} to "
               f"{pretty(ob_hi)}, the earliest date listed is a Friday for {cb[4]:,} ({pct(cb[4], N)}) and a "
               f"Saturday or Sunday for {cb[5] + cb[6]}.")
    later_txt = ""
    if both:
        later_txt = (f"For the {len(both)} NDAs with an original approval in Drugs@FDA since {lo.year} that are also in "
                     f"the Orange Book, the Orange Book date is later than the Drugs@FDA action date for "
                     f"{len(later)}" + (" (" + "; ".join(f"{x.get('brand') or x['app']}: {pretty(x['day'])} and "
                                                         f"{pretty(v[0])}" for x, v in later) + ")" if later else "")
                     + (f" and earlier for {len(earlier)}" if earlier else "") + ".")
    B.append(f'<h2>The longer record: dates in the Orange Book, {ob_lo.year} to {esc(pretty(ob_hi))}</h2>')
    B.append(f'<p class="sub" data-weekdays="ob-lede">{esc(ob_lede)}</p>')
    B.append('<table data-weekdays="by-day"><tr><th>Weekday</th>'
             + "".join(f'<th>{a} to {esc(pretty(ob_hi)) if b == ob_hi.year else b}</th>' for a, b in periods)
             + f'<th>All</th></tr>')
    for i, name in enumerate(DAYS):
        B.append(f'<tr><td>{name}</td>' + "".join(f'<td>{c[i]:,} ({pct(c[i], sum(c))})</td>' for c in pc)
                 + f'<td>{cb[i]:,} ({pct(cb[i], N)})</td></tr>')
    B.append('<tr><td>NDAs</td>' + "".join(f'<td>{sum(c):,}</td>' for c in pc) + f'<td>{N:,}</td></tr></table>')
    B.append(f'<p class="sub" data-weekdays="ob-limits">These are the dates the Orange Book lists, not always the '
             f'FDA\'s action date. {esc(later_txt)} The Orange Book lists products, not applications: '
             f'{not001} of the {N:,} NDAs are dated by a product other than product 001 ({no001} of them list no '
             'product 001), and an NDA whose prescription products have left the list (after a switch to over-the-counter sale, for example) is '
             f'dated by a later product. {n_undated:,} NDAs with any product listed as "{UNDATED}" are left out, '
             f'{n_mixed} of them with other products that are dated. Insulins and other protein products approved as '
             'NDAs moved to biologics licenses in March 2020 and are no longer in the file, and BLAs never were. An '
             'NDA no longer listed in the file, for any reason, is not counted. '
             f'The FDA files are dated {esc(ob_as_of)}; the newest approval date in them is {esc(pretty(ob_hi))}.</p>')
    B.append(f'<p class="sub" data-weekdays="ob-weekend">The {len(ob_weekend)} NDAs whose earliest Orange Book date '
             'falls on a Saturday or Sunday, as the file prints them: '
             + "; ".join(f'{n:06d} {esc(tn)}, {esc(pretty(d))} ({DAYS[d.weekday()]})' for d, n, tn in ob_weekend)
             + '.</p>')

    B.append('<h2>Method</h2>')
    B.append('<p class="sub" data-weekdays="method">Drugs@FDA: every original NDA or BLA (submission ORIG) and every '
             'efficacy supplement with status approved and an action date in the month, as openFDA returns them; '
             'generics (ANDAs) are out of scope, and one application and submission counts once. Orange Book: rows of '
             'the products file with application type N, grouped on the application number, each NDA taking the '
             'earliest approval date among its products. Weekdays are read from the date as printed. Holidays are '
             'the annual federal holidays of 5 U.S.C. 6103(a) at their observed dates (Martin Luther King Jr. Day '
             'from 1986, Juneteenth from 2021); Inauguration Day, which is a holiday only in the Washington area, and '
             'one-off closures by executive order, national days of mourning included, are not counted. An accelerated '
             'approval in the goal-date table is conditional: the FDA can withdraw it if the confirmatory trial does '
             'not verify the clinical benefit.</p>')
    B.append(f'<p class="sub">Every record counted, as data: <a href="{SLUG}/{DAF_CSV}">Drugs@FDA approvals</a> '
             f'({len(orig) + len(supp) + len(gas):,} rows, medical gases flagged) &middot; '
             f'<a href="{SLUG}/{OB_CSV}">Orange Book NDA dates</a> ({N:,} rows). The FDA\'s data is in the US public '
             'domain; these files are free under CC BY 4.0: cite pdufa.bio and link this page. &middot; '
             '<a href="/research/fda-decision-timing">Decision timing study</a> &middot; '
             '<a href="/fda-approvals">FDA approvals by month</a> &middot; <a href="/research">All research</a></p>')
    ld = {"@context": "https://schema.org", "@type": "Dataset",
          "name": "FDA drug approval dates by weekday: Drugs@FDA action dates and Orange Book NDA dates (pdufa.bio)",
          "description": (f"{no + ns:,} original and efficacy supplement approval action dates from Drugs@FDA "
                          f"({lo.isoformat()} to {hi.isoformat()}) and the earliest Orange Book approval date of "
                          f"{N:,} NDAs ({ob_lo.isoformat()} to {ob_hi.isoformat()}), each with its weekday and any "
                          "US federal holiday. The underlying FDA data is in the US public domain."),
          "url": BASE + SLUG, "license": "https://creativecommons.org/licenses/by/4.0/",
          "isAccessibleForFree": True, "creator": {"@type": "Organization", "name": "pdufa.bio", "url": BASE + "/"},
          "isBasedOn": [DAF_URL, OB_URL], "temporalCoverage": f"{ob_lo.isoformat()}/{hi.isoformat()}",
          "dateModified": read_hi,
          "distribution": [{"@type": "DataDownload", "encodingFormat": "text/csv", "contentUrl": f"{BASE}{SLUG}/{DAF_CSV}"},
                           {"@type": "DataDownload", "encodingFormat": "text/csv", "contentUrl": f"{BASE}{SLUG}/{OB_CSV}"}]}
    B.append('<script type="application/ld+json">' + json.dumps(ld, separators=(",", ":")) + '</script>')
    io.open(INDEX, "w", encoding="utf-8").write(page(title, desc, SLUG, B))

    stats = {"daf": {"first": lo.isoformat(), "last": hi.isoformat(), "fetched": read_hi, "read_first": read_lo, "n_orig": no, "n_supp": ns,
                     "orig_by_weekday": co, "supp_by_weekday": cs, "n_gas": len(gas), "gas_weekend": gas_we,
                     "weekend": [[x["app"], x["sub"], x["day"].isoformat()] for x in daf_weekend],
                     "holidays": [[x["app"], x["sub"], x["day"].isoformat()] for x in daf_hol]},
             "orange_book": {"n": N, "n_undated_left_out": n_undated, "n_mixed": n_mixed, "not_001": not001,
                             "first": ob_lo.isoformat(), "last": ob_hi.isoformat(), "files_dated": ob_as_of,
                             "by_weekday": cb, "weekend": [[n, d.isoformat()] for d, n, _ in ob_weekend],
                             "both": len(both), "later": [[x["app"], x["day"].isoformat(), v[0].isoformat()]
                                                          for x, v in later], "earlier": len(earlier)},
             "study_n": n_study,
             "goal_rows": [{"slug": x["slug"], "goal": x["goal"].isoformat(), "actual": x["actual"].isoformat(),
                            "kind": x["kind"]} for x in goal_rows],
             "lede": lede, "goal_lede": goal_lede, "ob_lede": ob_lede, "title": title, "desc": desc}
    io.open(STATS, "w", encoding="utf-8").write(json.dumps(stats, indent=1) + "\n")

    card = (f"{CARD_BEGIN}<a class='row' href='{SLUG}'><div class='t'>On what weekday FDA approvals are dated</div>"
            f"<div class='d'>{co[4]} of {no} original FDA drug approvals since {lo.year} carry a Friday action date "
            f"(Drugs@FDA), with the Orange Book's NDA dates since {ob_lo.year} and the 2026 decisions whose goal date "
            f"fell on a weekend or holiday.</div></a>{CARD_END}")
    hub = os.path.join(SITE, "research", "index.html")
    if os.path.exists(hub):
        t = io.open(hub, encoding="utf-8", errors="replace").read()
        if CARD_BEGIN in t:
            t2 = re.sub(re.escape(CARD_BEGIN) + ".*?" + re.escape(CARD_END), lambda m: card, t, flags=re.S)
        else:
            t2 = t.replace("<div class='grid'>", "<div class='grid'>" + card, 1)
        if t2 != t:
            io.open(hub, "w", encoding="utf-8").write(t2)
    timing = os.path.join(SITE, "research", "fda-decision-timing", "index.html")
    if os.path.exists(timing) and goal_rows:
        link = (f'{LINK_BEGIN}<p class="sub" data-weekdays="timing-link">{len(goal_rows)} of these decisions had a '
                f'goal date on a weekend or federal holiday: <a href="{SLUG}">the day of the FDA record for each, and '
                f'on what weekday FDA approvals are dated</a>.</p>{LINK_END}')
        t = io.open(timing, encoding="utf-8", errors="replace").read()
        if LINK_BEGIN in t:
            t2 = re.sub(re.escape(LINK_BEGIN) + ".*?" + re.escape(LINK_END), lambda m: link, t, flags=re.S)
        else:
            m = re.search(r'<p class="note">.*?</p>', t, re.S)
            t2 = t[:m.end()] + link + t[m.end():] if m else t
        if t2 != t:
            io.open(timing, "w", encoding="utf-8").write(t2)
    print(f"{SLUG}: Drugs@FDA {no} originals (Friday {co[4]}, weekend {co[5] + co[6]}), {ns} supplements (Friday "
          f"{cs[4]}), {len(gas)} gases; Orange Book {N:,} NDAs (Friday {cb[4]:,}); {len(later)} of {len(both)} later "
          f"in the Orange Book; {len(goal_rows)} of {n_study} 2026 decisions with weekend/holiday goal")
    return 0


if __name__ == "__main__":
    sys.exit(main())
