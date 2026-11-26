# -*- coding: utf-8 -*-
"""build_decision_timing_since_2024.py -- early, on the goal date, or late: FDA decisions since January 2024.

2026-11-26. The 2026 page (/research/fda-decision-timing, build_early_decisions.py) counts one calendar year. This
page counts every FDA action dated from January 1, 2024 that we could source to the day on both ends:

    * 2024 and 2025 from decision_timing_2024_2025.json, a census researched and red-teamed on 2026-11-26.
      Candidates were every PDUFA decision on the pdufa.bio tracked list for those years plus every complete
      response letter the FDA has released that is dated in those years. Each counted action has a goal date
      stated to the day in a sponsor or partner document dated before the action, and an action date from an FDA
      record or from a sponsor document that states the day the FDA acted. Rows that fail either test are counted
      and listed by reason, never guessed.
    * 2026 from build_early_decisions.collect(2026), the same rows the 2026 page counts, so the two pages cannot
      disagree on a 2026 decision.

Buckets are measured against the goal date in effect when the FDA acted (after any extension). Extended cases are
also shown against their original goal date. Goal dates on a weekend or US federal holiday are flagged.

The "do late decisions end in a CRL" table uses only the candidate sets that were not chosen by outcome (the tracked
list and the 2026 calendar). The released-CRL candidates were added because they are CRLs, so counting them in a
CRL rate would inflate it; they appear in the timing counts and the full list, not in the rate.

Facts only: counts with their denominators. No causal claim, no prediction, not investment advice.

    python build_decision_timing_since_2024.py [--dry-run]
tests/test_decision_timing_since_2024.py recounts the page from the JSON with its own code.
"""
import argparse, csv, datetime as dt, html, io, json, os, re, shutil, glob, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
sys.path.insert(0, HERE)
from build_early_decisions import collect  # noqa: E402  -- the 2026 rows, exactly as the 2026 page counts them
from build_fda_approval_weekdays import holiday_of  # noqa: E402  -- one owner of the US federal holiday rules

DATA = os.path.join(HERE, "decision_timing_2024_2025.json")
REL = "research/fda-decision-timing/since-2024"
OUT = os.path.join(SITE, REL)
URL = "https://www.pdufa.bio/" + REL
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
EXCL_LABEL = {
    "no_sourced_goal_day": "no sponsor or partner document found that states the goal date to the day",
    "goal_month_or_quarter": "the sponsor stated the goal only as a month, quarter or half-year",
    "not_pdufa": "not a PDUFA efficacy decision (biosimilar under BsUFA, generic under GDUFA, a strain update or manufacturing-only supplement, or not a complete response)",
    "not_researched": "not researched (mostly private or foreign sponsors that publish no goal dates, or a product the FDA letter redacts)",
    "action_day_not_established": "the day the FDA acted is not established by a document",
    "duplicate": "the same FDA action as another candidate",
}


def esc(s):
    return html.escape(str(s if s is not None else ""), quote=True)


def pretty(iso):
    d = dt.date.fromisoformat(iso)
    return f"{MON[d.month - 1]} {d.day}, {d.year}"


def short(s, k):
    s = str(s or "")
    return s if len(s) <= k else s[:k].rsplit(" ", 1)[0].rstrip(",;:-(") + "\u2026"


def bucket(n):
    return "early" if n < 0 else ("on" if n == 0 else "late")


def dw(n):
    return "day" if abs(n) == 1 else "days"


def pct(a, b):
    if not b:
        return "n/a"
    v = 100 * a / b
    return f"{int(v + 0.5)}%"


def median(xs):
    xs = sorted(xs)
    if not xs:
        return None
    k = len(xs)
    return xs[k // 2] if k % 2 else (xs[k // 2 - 1] + xs[k // 2]) / 2


def fmt_med(m):
    if m is None:
        return "n/a"
    t = f"{abs(m):.1f}".rstrip("0").rstrip(".")
    if m == 0:
        return "0 (on the goal date)"
    return f"{t} {'day' if abs(m) == 1 else 'days'} {'before' if m < 0 else 'after'}"


def goal_flag(iso):
    d = dt.date.fromisoformat(iso)
    h = holiday_of(d)
    if d.weekday() >= 5:
        return DAYS[d.weekday()]
    return h or ""


def next_business_day(d):
    d = d + dt.timedelta(days=1)
    while d.weekday() >= 5 or holiday_of(d):
        d += dt.timedelta(days=1)
    return d


def prev_business_day(d):
    d = d - dt.timedelta(days=1)
    while d.weekday() >= 5 or holiday_of(d):
        d -= dt.timedelta(days=1)
    return d


def _page_index():
    idx = {}
    base = os.path.join(SITE, "fda-decision")
    for p in os.listdir(base) if os.path.isdir(base) else []:
        m = re.match(r"^([A-Z0-9.]+)-(\d{4}-\d{2}-\d{2})$", p)
        if m and os.path.exists(os.path.join(base, p, "index.html")):
            idx.setdefault(m.group(1), []).append(m.group(2))
    return idx


def match_page(idx, tickers, action):
    """The decision page for this action: same ticker, page date within 4 days of the FDA action, and only one such
    page across the row's tickers' dates (two candidate dates = ambiguous, so no link)."""
    ad = dt.date.fromisoformat(action)
    hits = set()
    for tk in tickers:
        for d in idx.get(tk.upper(), []):
            if abs((dt.date.fromisoformat(d) - ad).days) <= 4:
                hits.add((tk.upper(), d))
    dates = {d for _, d in hits}
    if len(dates) != 1:
        return ""
    tk, d = sorted(hits)[0]
    return f"/fda-decision/{tk}-{d}"


def load_2024_2025():
    doc = json.load(io.open(DATA, encoding="utf-8"))
    pidx = _page_index()
    rows, dropped = [], []
    for a in doc["actions"]:
        if a.get("excluded"):
            dropped.append(a)
            continue
        g, ad = a["goal_in_effect"], a["action_date"]
        orig = a.get("goal_date_original") if a.get("extended") else None
        rows.append({
            "year": ad[:4], "drug": a["drug"], "sponsor": a.get("sponsor") or "",
            "tickers": "/".join(a.get("tickers") or []), "application": a.get("application") or "",
            "goal": g, "action": ad, "delta": (dt.date.fromisoformat(ad) - dt.date.fromisoformat(g)).days,
            "outcome": a["outcome"], "origin": a["origin"],
            "extended": bool(a.get("extended")), "goal_original": orig,
            "goal_url": (a.get("goal_extended_url") if a.get("extended") else a.get("goal_original_url")) or "",
            "goal_doc_date": (a.get("goal_extended_doc_date") if a.get("extended") else a.get("goal_original_doc_date")) or "",
            "goal_original_url": a.get("goal_original_url") or "",
            "action_url": a.get("action_url") or "", "action_basis": a.get("action_basis") or "",
            "extension_reason": a.get("extension_reason") or "", "scope_note": a.get("scope_note") or "",
            "red_team": a.get("red_team") or "", "page": match_page(pidx, a.get("tickers") or [], ad),
            "cid": a.get("cid") or "",
        })
    return doc, rows, dropped


GOAL_LEDGER = os.path.join(HERE, "_decision_goal_dates.json")


def write_goal_ledger(rows):
    """2026-11-26: the goal date this census sourced, keyed by the 2024-2025 decision page it matched, so that
    page's Verified line (inject_verified_against.py) names the goal date and its source instead of "Goal date: none
    on record". Only the goal in effect, the dated document that states it, and the original goal when it was
    extended. Sorted, so a rebuild with no change rewrites nothing."""
    led = {}
    for x in rows:
        if not (x.get("page") and x.get("goal_url") and x.get("goal_doc_date")):
            continue
        led[x["page"].rsplit("/", 1)[-1]] = {
            "cid": x.get("cid") or "", "goal": x["goal"], "source_url": x["goal_url"], "doc_date": x["goal_doc_date"],
            "extended": x["extended"], "goal_original": x.get("goal_original") or None,
            "action": x["action"], "outcome": x["outcome"]}
    io.open(GOAL_LEDGER, "w", encoding="utf-8", newline="\n").write(
        json.dumps(dict(sorted(led.items())), indent=1, ensure_ascii=False) + "\n")


def load_2026():
    src = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8", errors="replace").read()
    ds = json.loads(src[src.index("["):src.rindex("]") + 1])
    by = {f"{str(x.get('t') or '').upper()}-{str(x.get('dcd') or '')[:10]}": x for x in ds if x.get("dcd")}
    out = []
    for r in collect(2026):
        rr = by.get(r["slug"]) or {}
        d = rr.get("_d") or {}
        orig = None
        # an extension counts only where the row's own date history records the FDA moving the goal
        for h in d.get("date_history") or []:
            why = str(h.get("why") or "").lower()
            if "extend" in why and d.get("prior_pdufa_date") and str(d["prior_pdufa_date"]) < r["goal"]:
                orig = str(d["prior_pdufa_date"])[:10]
        oc = r["outcome"]
        out.append({
            "year": r["actual"][:4], "drug": r["drug"], "sponsor": "", "tickers": r["ticker"],
            "application": r.get("fda_record") or "", "goal": r["goal"], "action": r["actual"], "delta": r["delta"],
            "outcome": "CRL" if oc == "CRL" else ("Approved" if oc == "Approved" else oc), "origin": "calendar_2026",
            "extended": bool(orig), "goal_original": orig, "goal_url": d.get("source_url") or "",
            "goal_doc_date": "", "goal_original_url": "", "action_url": r.get("fda_url") or "",
            "action_basis": "fda_record" if "fda.gov" in (r.get("fda_url") or "") else "",
            "extension_reason": "", "scope_note": "", "red_team": "", "page": "/fda-decision/" + r["slug"],
        })
    return out


CARD_BEGIN, CARD_END = "<!--TIMING2024-CARD:BEGIN-->", "<!--TIMING2024-CARD:END-->"
LINK_BEGIN, LINK_END = "<!--TIMING2024-LINK:BEGIN-->", "<!--TIMING2024-LINK:END-->"
ORIGIN = {"tracked": "tracked list", "crl_letter": "FDA-released CRL", "calendar_2026": "2026 calendar"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    doc, r45, dropped = load_2024_2025()
    r26 = load_2026()
    rows = sorted(r45 + r26, key=lambda x: (x["action"], x["drug"]))
    n = len(rows)
    years = ["2024", "2025", "2026"]
    for x in rows:
        x["bucket"] = bucket(x["delta"])
        x["goal_flag"] = goal_flag(x["goal"])

    def counts(rs):
        return (sum(1 for x in rs if x["bucket"] == "early"), sum(1 for x in rs if x["bucket"] == "on"),
                sum(1 for x in rs if x["bucket"] == "late"))

    E, O, L = counts(rows)
    last = max(x["action"] for x in rows)

    # ---- by year -------------------------------------------------------------------------------------------
    yr_rows = []
    for y in years + ["all"]:
        rs = rows if y == "all" else [x for x in rows if x["year"] == y]
        e, o, l = counts(rs)
        m = median([x["delta"] for x in rs])
        lab = "Total" if y == "all" else (f"{y} (through {pretty(last)})" if y == "2026" else y)
        yr_rows.append(f'<tr{" class=tot" if y == "all" else ""}><td>{lab}</td><td>{len(rs)}</td>'
                       f'<td>{e} <span class=p>({pct(e, len(rs))})</span></td><td>{o} <span class=p>({pct(o, len(rs))})</span></td>'
                       f'<td>{l} <span class=p>({pct(l, len(rs))})</span></td><td>{esc(fmt_med(m))}</td></tr>')
    yr_table = ('<table><tr><th>FDA action year</th><th>Decisions</th><th>Early</th><th>On the goal date</th>'
                '<th>Late</th><th>Median</th></tr>' + "".join(yr_rows) + '</table>')

    # ---- distribution --------------------------------------------------------------------------------------
    bins = [("More than 30 days early", lambda d: d < -30), ("8 to 30 days early", lambda d: -30 <= d <= -8),
            ("2 to 7 days early", lambda d: -7 <= d <= -2), ("1 day early", lambda d: d == -1),
            ("On the goal date", lambda d: d == 0), ("1 to 7 days late", lambda d: 1 <= d <= 7),
            ("8 to 30 days late", lambda d: 8 <= d <= 30), ("More than 30 days late", lambda d: d > 30)]
    dist = '<table><tr><th>Days from goal date</th><th>Decisions</th><th>Share</th></tr>' + "".join(
        f'<tr><td>{lab}</td><td>{sum(1 for x in rows if f(x["delta"]))}</td>'
        f'<td>{pct(sum(1 for x in rows if f(x["delta"])), n)}</td></tr>' for lab, f in bins) + '</table>'
    earliest = min(rows, key=lambda x: x["delta"])
    latest = max(rows, key=lambda x: x["delta"])

    # ---- outcome by bucket (outcome-blind candidates only) -------------------------------------------------
    blind = [x for x in rows if x["origin"] in ("tracked", "calendar_2026")]
    letters = [x for x in rows if x["origin"] == "crl_letter"]
    ob = []
    for b, lab in (("early", "Early"), ("on", "On the goal date"), ("late", "Late")):
        rs = [x for x in blind if x["bucket"] == b]
        c = sum(1 for x in rs if x["outcome"] == "CRL")
        s = sum(1 for x in rs if x["outcome"] == "Split")
        ap_ = sum(1 for x in rs if x["outcome"] == "Approved")
        ob.append((lab, len(rs), ap_, c, s))
    nb = len(blind)
    cb = sum(1 for x in blind if x["outcome"] == "CRL")
    sb = sum(1 for x in blind if x["outcome"] == "Split")
    out_table = ('<table><tr><th>Timing</th><th>Decisions</th><th>Approved</th><th>CRL</th><th>Split</th>'
                 '<th>CRL share</th></tr>' + "".join(
                     f'<tr><td>{lab}</td><td>{k}</td><td>{ap_}</td><td>{c}</td><td>{s}</td><td>{c} of {k} ({pct(c, k)})</td></tr>'
                     for lab, k, ap_, c, s in ob)
                 + f'<tr class=tot><td>All</td><td>{nb}</td><td>{nb - cb - sb}</td><td>{cb}</td><td>{sb}</td>'
                   f'<td>{cb} of {nb} ({pct(cb, nb)})</td></tr></table>')
    all_crl = [x for x in rows if x["outcome"] in ("CRL", "Split")]
    ce, co, cl = counts(all_crl)
    late_rows = [x for x in rows if x["bucket"] == "late"]
    late_crl = [x for x in late_rows if x["outcome"] != "Approved"]
    late_blind = [x for x in blind if x["bucket"] == "late"]

    # ---- extensions ----------------------------------------------------------------------------------------
    ext = [x for x in rows if x["extended"]]
    ext_known = [x for x in ext if x["goal_original"]]
    vs_orig = [(dt.date.fromisoformat(x["action"]) - dt.date.fromisoformat(x["goal_original"])).days for x in ext_known]
    oe = sum(1 for d in vs_orig if d < 0)
    oo = sum(1 for d in vs_orig if d == 0)
    ol = sum(1 for d in vs_orig if d > 0)
    ee, eo, el = counts(ext)
    ext_list = "".join(
        f'<tr><td>{esc(short(x["drug"], 60))}</td><td>{esc(pretty(x["goal_original"])) if x["goal_original"] else "not sourced"}</td>'
        f'<td>{esc(pretty(x["goal"]))}</td><td>{esc(pretty(x["action"]))}</td>'
        f'<td>{x["delta"]:+d}</td><td>{esc(x["outcome"])}</td></tr>' for x in sorted(ext, key=lambda x: x["action"]))

    # ---- weekend / holiday goals ---------------------------------------------------------------------------
    wk = [x for x in rows if x["goal_flag"]]
    wk_prev = [x for x in wk if dt.date.fromisoformat(x["action"]) == prev_business_day(dt.date.fromisoformat(x["goal"]))]
    wk_next = [x for x in wk if dt.date.fromisoformat(x["action"]) == next_business_day(dt.date.fromisoformat(x["goal"]))]
    we, wo, wl = counts(wk)
    late_next = [x for x in late_rows if x["goal_flag"] and
                 dt.date.fromisoformat(x["action"]) == next_business_day(dt.date.fromisoformat(x["goal"]))]

    # ---- exclusions ----------------------------------------------------------------------------------------
    from collections import Counter
    exc = Counter(e["category"] for e in doc["excluded_rows"])
    cand = doc["candidates"]["tracked"] + doc["candidates"]["crl_letter"]
    n_dropped = len(dropped)
    excl_items = "".join(f'<tr><td>{esc(EXCL_LABEL.get(k, k))}</td><td>{v}</td></tr>' for k, v in exc.most_common())
    excl_items += (f'<tr><td>merged into another candidate: the same FDA action listed twice (for example a tracked '
                   f'row and the FDA&rsquo;s own letter)</td><td>{doc["merged_duplicate_rows"]}</td></tr>')
    if n_dropped:
        excl_items += (f'<tr><td>left out at review ('
                       + "; ".join(esc(d["drug"].split(" (")[0].split(" - ")[0]) + ": " + esc(d["excluded"]) for d in dropped)
                       + f')</td><td>{n_dropped}</td></tr>')
    n45 = len(r45)
    n_rt = sum(1 for x in json.load(io.open(DATA, encoding="utf-8"))["actions"] if x.get("red_team"))
    n_p3 = sum(1 for x in json.load(io.open(DATA, encoding="utf-8"))["actions"]
               if str(x.get("notes") or "").startswith("Pass 3") and not x.get("excluded"))

    # ---- full list -----------------------------------------------------------------------------------------
    def row_html(x):
        flag = f' <span class=w>goal on a {esc(x["goal_flag"])}</span>' if x["goal_flag"] in DAYS else (
            f' <span class=w>goal on {esc(x["goal_flag"])}</span>' if x["goal_flag"] else "")
        ext_ = (f'<br><span class=p>extended from {esc(pretty(x["goal_original"]))}</span>' if x["goal_original"]
                else ('<br><span class=p>extended; original date not sourced</span>' if x["extended"] else ""))
        gsrc = f'<a href="{esc(x["goal_url"])}" rel="nofollow noopener">goal source</a>' if x["goal_url"] else ""
        asrc = f'<a href="{esc(x["action_url"])}" rel="nofollow noopener">action source</a>' if x["action_url"] else ""
        pd_ = x["page"][-10:] if x["page"] else ""
        pg = (f' &middot; <a href="{esc(x["page"])}">decision page</a>'
              + (f' <span class=p>(filed under {esc(pretty(pd_))})</span>' if pd_ and pd_ != x["action"] else "")
              if x["page"] else "")
        basis = "" if x["action_basis"] == "fda_record" else ' <span class=p>(sponsor states the day)</span>'
        col = "#46d17f" if x["delta"] < 0 else ("#f0c86a" if x["delta"] > 0 else "#9db3d4")
        name = esc(short(x["drug"], 70)) + (f' <span class=p>{esc(x["tickers"])}</span>' if x["tickers"] else "") + (
            f'<br><span class=p>{esc(x["scope_note"])}</span>' if x["scope_note"] else "")
        return (f'<tr><td>{name}<br><span class=p>{esc(ORIGIN[x["origin"]])}</span></td>'
                f'<td>{esc(pretty(x["goal"]))}{flag}{ext_}</td><td>{esc(pretty(x["action"]))}{basis}</td>'
                f'<td style="color:{col};white-space:nowrap"><b>{x["delta"]:+d}</b></td><td>{esc(x["outcome"])}</td>'
                f'<td class=s>{gsrc}{" &middot; " if gsrc and asrc else ""}{asrc}{pg}</td></tr>')

    full = ('<div class=tw><table class=full><tr><th>Decision</th><th>Goal date in effect</th><th>FDA action</th>'
            '<th>Days</th><th>Outcome</th><th>Sources</th></tr>' + "".join(row_html(x) for x in rows) + '</table></div>')

    # ---- CSV (CC BY 4.0), versioned by row count -----------------------------------------------------------
    ver = f"v{n}"
    csv_rel = f"pdufa-decision-timing-2024-present-{ver}.csv"
    alias_rel = "pdufa-decision-timing-2024-present.csv"
    if not a.dry_run:
        os.makedirs(OUT, exist_ok=True)
        with io.open(os.path.join(OUT, csv_rel), "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["fda_action_year", "drug", "sponsor", "tickers", "application_or_fda_record", "outcome", "goal_date_in_effect",
                        "fda_action_date", "days_from_goal", "timing", "extended", "original_goal_date",
                        "goal_weekend_or_holiday", "goal_source_url", "goal_source_date", "original_goal_source_url",
                        "action_source_url", "action_date_basis",
                        "candidate_set", "decision_page", "license"])
            for x in rows:
                w.writerow([x["year"], x["drug"], x["sponsor"], x["tickers"], x["application"], x["outcome"], x["goal"],
                            x["action"], x["delta"], {"early": "early", "on": "on goal date", "late": "late"}[x["bucket"]],
                            "yes" if x["extended"] else "", x["goal_original"] or "", x["goal_flag"], x["goal_url"],
                            x["goal_doc_date"], x["goal_original_url"] if x["goal_original"] else "", x["action_url"], x["action_basis"] or "sponsor_states_day", ORIGIN[x["origin"]],
                            ("https://www.pdufa.bio" + x["page"]) if x["page"] else "", "CC BY 4.0 https://pdufa.bio"])
        shutil.copyfile(os.path.join(OUT, csv_rel), os.path.join(OUT, alias_rel))
    vintages = sorted((os.path.basename(p) for p in glob.glob(os.path.join(OUT, "pdufa-decision-timing-2024-present-v*.csv"))),
                      key=lambda s: int(re.search(r"-v(\d+)\.csv$", s).group(1)))
    older = [v for v in vintages if v != csv_rel]

    # ---- text ----------------------------------------------------------------------------------------------
    lede = (f"Of <b>{n}</b> FDA decisions dated January 1, 2024 through {pretty(last)} whose goal date and action date "
            f"we could each tie to a document, <b>{E}</b> came before the PDUFA goal date, <b>{O}</b> on it and "
            f"<b>{L}</b> after it.")
    ans_crl = (f"In the candidate sets not chosen by outcome ({nb} decisions), {ob[2][3]} of the {ob[2][1]} late "
               f"decisions ended in a complete response letter ({pct(ob[2][3], ob[2][1])}), against {ob[0][3]} of "
               f"{ob[0][1]} early ({pct(ob[0][3], ob[0][1])}) and {ob[1][3]} of {ob[1][1]} on the goal date "
               f"({pct(ob[1][3], ob[1][1])}).")
    title = f"Are FDA decisions early, on time or late? {n} sourced PDUFA decisions since 2024 | pdufa.bio"
    desc = (f"{n} FDA decisions since Jan 2024, each with a sourced goal date and action date: {E} early, {O} on the "
            f"goal date, {L} late. CRL counts by timing, extensions, CSV.")
    if len(desc) > 158:
        desc = desc[:158].rsplit(" ", 1)[0].rstrip(",;:") + "."
    qa = [("How many FDA decisions since 2024 came early, on the goal date, or late?",
           f"In this census of {n} sourced decisions dated January 1, 2024 through {pretty(last)}, {E} came before "
           f"the PDUFA goal date in effect, {O} on it and {L} after it. Each decision's goal date comes from a "
           f"sponsor or partner document published before the action and its action date from an FDA record or a "
           f"sponsor document that states the day. Some candidates were not yet researched, so this is not every "
           f"FDA decision in the period."),
          ("Do late FDA decisions end in more complete response letters?",
           ans_crl + f" The late group is small, so these are counts, not a measured effect. Across every CRL or "
           f"split action in the census ({len(all_crl)}), including FDA-released letters, {ce} came early, {co} on the "
           f"goal date and {cl} late."),
          ("How did the extended goal dates in this census turn out?",
           f"{len(ext)} decisions in the census had a goal date the FDA extended before acting. Measured against the "
           f"extended date, {ee} came early, {eo} on it and {el} late. Where the original date is sourced "
           f"({len(ext_known)}), {oe} came before the original date, {oo} on it and {ol} after it."),
          ("Which decisions are left out?",
           f"Of {cand} candidate rows for 2024 and 2025, {n45} FDA actions are counted. Every other row is listed by "
           f"reason on this page: no document stating the goal date to the day, a goal given only as a month or "
           f"quarter, not a PDUFA action, not yet researched, the day the FDA acted not established, the same action "
           f"listed twice, or left out at review. Nothing is estimated.")]

    jsonld = json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": re.sub(r"<[^>]+>", "", t)}}
        for q, t in qa]}, ensure_ascii=False)
    ds_ld = json.dumps({
        "@context": "https://schema.org", "@type": "Dataset",
        "name": f"PDUFA decision timing 2024 to present: goal date vs FDA action date ({ver})",
        "description": (f"{n} FDA decisions dated {pretty('2024-01-01')} through {pretty(last)} with a sourced PDUFA "
                        f"goal date and action date: {E} early, {O} on the goal date, {L} late. Outcome, extensions, "
                        f"weekend and holiday goal dates, and the source URL behind each date."),
        "url": URL, "version": ver, "license": "https://creativecommons.org/licenses/by/4.0/",
        "isAccessibleForFree": True,
        "creator": {"@type": "Organization", "name": "pdufa.bio", "url": "https://www.pdufa.bio/"},
        "temporalCoverage": f"2024-01-01/{last}",
        "variableMeasured": ["goal_date_in_effect", "fda_action_date", "days_from_goal", "outcome", "original_goal_date"],
        "distribution": [{"@type": "DataDownload", "encodingFormat": "text/csv", "name": f"latest ({ver})",
                          "contentUrl": f"{URL}/{alias_rel}"},
                         {"@type": "DataDownload", "encodingFormat": "text/csv", "name": ver,
                          "contentUrl": f"{URL}/{csv_rel}"}]}, ensure_ascii=False)
    faq = "".join(f'<div class=q><b>{esc(q)}</b><div>{esc(t)}</div></div>' for q, t in qa)

    late_next_txt = "; ".join(esc(x["drug"].split(" (")[0]) + " " + format(x["delta"], "+d") for x in late_next)
    wk_line = (f'{len(wk)} of the {n} goal dates fell on a Saturday, Sunday or US federal holiday. Of those, '
               f'{len(wk_prev)} were decided on the last business day before the goal date and {len(wk_next)} on the '
               f'first business day after it; overall {we} came early, {wo} on the goal date itself and {wl} late.'
               + (f' {len(late_next)} of the {L} late decisions came on the first business day after a weekend or '
                  f'holiday goal date ({late_next_txt}).'
                  if late_next else ""))

    css = ("*{box-sizing:border-box}body{margin:0;background:#02060d;color:#f2f6fc;font-family:-apple-system,BlinkMacSystemFont,"
           "'Segoe UI',Roboto,Helvetica,Arial,sans-serif;line-height:1.5}a{color:#6fb6ff;text-decoration:none}a:hover{text-decoration:underline}"
           ".wrap{max-width:920px;margin:0 auto;padding:22px 18px 60px}.top{display:flex;align-items:center;justify-content:space-between;"
           "border-bottom:1px solid #1a3358;padding-bottom:12px}.brand{font-size:19px;font-weight:800;color:#f2f6fc}.brand b{color:#e3ba5e}"
           ".nav a{color:#a7bcd9;font-size:13px;margin-left:14px}h1{font-size:27px;line-height:1.18;margin:10px 0 6px}"
           "h2{font-size:18px;color:#e3ba5e;margin:28px 0 8px}.bc{font-size:12px;color:#94a9c9;margin:16px 0 4px}.bc a{color:#94a9c9}"
           ".sub{color:#cfe0f5;font-size:15.5px}.note{font-size:13px;color:#9db3d4;line-height:1.65}"
           "table{border-collapse:collapse;width:100%;font-size:13.5px;margin:6px 0}th,td{border-bottom:1px solid #1a3358;padding:7px 8px;"
           "text-align:left;vertical-align:top}th{color:#a7bcd9;font-weight:600}tr.tot td{font-weight:700;color:#eef4fc}"
           ".p{color:#94a9c9;font-size:12px}.w{color:#f0c86a;font-size:11.5px;white-space:nowrap}.s{font-size:12px}"
           ".tw{overflow-x:auto}.full td{font-size:12.5px}.box{background:#0c1d38;border:1px solid #1e3a63;border-radius:12px;"
           "padding:13px 15px;margin:12px 0}.q{background:#0c1d38;border:1px solid #1e3a63;border-radius:12px;padding:13px 15px;"
           "margin:10px 0}.q div{color:#9db3d4;font-size:14px;margin-top:6px}footer{border-top:1px solid #1a3358;margin-top:34px;"
           "padding-top:16px;font-size:11.5px;color:#94a9c9;line-height:1.6}footer b{color:#a7bcd9}")

    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><title>{esc(title)}</title><meta name="description" content="{esc(desc)}"><link rel="canonical" href="{URL}"><meta name="robots" content="index,follow,max-image-preview:large"><meta name="theme-color" content="#02060d"><link rel="icon" type="image/svg+xml" href="/favicon.svg"><meta property="og:type" content="article"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}"><meta property="og:url" content="{URL}"><style>{css}</style><script type="application/ld+json">{jsonld}</script><script type="application/ld+json">{ds_ld}</script></head><body><div class="wrap"><div class="top"><a class="brand" href="/">pdufa<b>.bio</b></a><div class="nav"><a href="/calendar">Calendar</a><a href="/decisions">Decisions</a><a href="/readouts">Readouts</a><a href="/research">Research</a></div></div><div class="bc"><a href="/">Home</a> &rsaquo; <a href="/research">Research</a> &rsaquo; <a href="/research/fda-decision-timing">Decision timing</a> &rsaquo; Since 2024</div><h1>Early, on the goal date, or late: FDA decisions since January 2024</h1><div class="sub">{lede} The median decision came {esc(fmt_med(median([x["delta"] for x in rows])))} the goal date.</div>
<div class="box note"><b style="color:#e3ba5e">Definitions.</b> <b>Goal date in effect</b>: the PDUFA goal (target action) date that applied on the day the FDA acted, after any extension. <b>Early</b>: the FDA acted on a calendar day before that date. <b>On the goal date</b>: the same calendar day. <b>Late</b>: a calendar day after it. <b>CRL</b>: a complete response letter. <b>Split</b>: one action that approved part of an application and issued a CRL on another part the same day. Days are calendar days. A decision is counted in the year the FDA acted.</div>
<h2>By year</h2>{yr_table}
<h2>How far from the goal date</h2>{dist}<p class="note">Earliest: {esc(short(earliest["drug"], 70))}, {abs(earliest["delta"])} {dw(earliest["delta"])} before its goal date of {esc(pretty(earliest["goal"]))}. Latest: {esc(short(latest["drug"], 70))}, {latest["delta"]} {dw(latest["delta"])} after its goal date of {esc(pretty(latest["goal"]))}.</p>
<h2>CRLs by timing in this census</h2><div class="sub" style="font-size:14.5px">{ans_crl}</div>{out_table}<p class="note">This table counts only the candidates that were not picked by outcome: decisions on the pdufa.bio tracked list (2024 and 2025) and the 2026 calendar. The {len(letters)} decisions that entered the census because the FDA released their complete response letter are left out of it, because adding letters adds only CRLs or split actions and would inflate the share. Across every CRL or split action in the census, including those letters ({len(all_crl)}), {ce} came early, {co} on the goal date and {cl} late. Of the {L} late decisions, {len(late_crl)} ended in a CRL or split action. These are counts of what happened; the late group is small, and the page does not claim that timing causes an outcome.</p>
<h2>Extended goal dates</h2><p class="note">{len(ext)} decisions had a goal date the FDA extended before it acted. Against the extended date in effect, {ee} came early, {eo} on it and {el} late. Where the original date is sourced ({len(ext_known)} of {len(ext)}), {oe} came before the original date, {oo} on it and {ol} after it. Each case is shown against both dates where the original date is sourced.</p><div class=tw><table><tr><th>Decision</th><th>Original goal</th><th>Extended goal</th><th>FDA action</th><th>Days vs extended</th><th>Outcome</th></tr>{ext_list}</table></div>
<h2>Goal dates on a weekend or holiday</h2><p class="note">{wk_line} Holidays here are the annual US federal holidays in statute; one-off closures by executive order are not treated as holidays. The FDA&rsquo;s goal date can fall on a non-business day; an action on the business day before it counts here as early and an action on the business day after it counts as late, and each such row is flagged in the list below.</p>
<h2>What is counted, and what is left out</h2><div class="note"><p>For 2024 and 2025 the candidates were {doc["candidates"]["tracked"]} PDUFA decisions on the pdufa.bio tracked list and {doc["candidates"]["crl_letter"]} complete response letters the FDA has released that are dated in those years ({cand} in all). The tracked list is not every FDA action: it leans toward companies that publish their goal dates, mostly listed biotech and pharmaceutical companies. A decision is counted only when a sponsor or partner document dated before the action (a press release or an SEC filing) states its goal date to the day, and an FDA record (Drugs@FDA, a CBER approval letter or summary, or the released CRL) or a sponsor document states the day the FDA acted. 2026 rows are the sourced decisions on <a href="/research/fda-decision-timing">the 2026 decision-timing page</a> and follow its rules. Counted: {n45} actions in 2024 and 2025 and {len(r26)} in 2026.</p><p>A separate review on November 26, 2026 re-checked {n_rt} of the 2024 and 2025 actions against their documents (every one that was late, ended in a CRL, had an extension or rested on a search result, plus a random sample of the others) and the 2026 late and CRL rows. That review changed no goal or action date; it replaced some sources with the original filing, and the rows it left out are named below. Two further actions were changed to split decisions after the review, from the FDA&rsquo;s own records. A third search pass later that day, through SEC full-text search, added {n_p3} actions; a separate check read each one&rsquo;s goal document and the FDA&rsquo;s record of the action before it was counted.</p></div><table><tr><th>Candidates for 2024 and 2025 not counted</th><th>Rows</th></tr>{excl_items}</table>
<h2>Every counted decision</h2><p class="note">Sorted by FDA action date. Days are the FDA action date minus the goal date in effect; negative is early. &ldquo;Sponsor states the day&rdquo; marks an action date taken from a company document that names the day, not from an FDA record. Where this site&rsquo;s decision page for the same action is filed under a different day, the row names that day; the count uses the FDA action date shown here.</p>{full}
<div class="box note"><b style="color:#e3ba5e">Download ({ver}, CSV, CC BY 4.0):</b> <a href="/{REL}/{csv_rel}">{csv_rel}</a>, or the always-current <a href="/{REL}/{alias_rel}">{alias_rel}</a>. One row per decision: goal date in effect, original goal date, FDA action date, days, timing, outcome, weekend or holiday flag, and the source URL behind each date. Cite as &ldquo;pdufa.bio, PDUFA decision timing 2024 to present ({ver}), {URL}&rdquo;. The version is the row count; earlier versions stay at their own addresses{": " + ", ".join(f'<a href="/{REL}/{v}">{re.search(r"-(v[0-9]+)[.]csv$", v).group(1)}</a>' for v in older) if older else ""}.</div>
<h2>Related</h2><p class="note"><a href="/research/fda-decision-timing">2026 decisions, goal date vs actual</a> &middot; <a href="/crl/review-clock">CRL review clock</a> &middot; <a href="/crl">FDA complete response letters</a> &middot; <a href="/pdufa-date-changes">PDUFA date changes</a> &middot; <a href="/research/fda-approval-weekdays">Approval weekdays</a> &middot; <a href="/changes">Dataset changes</a></p>
<h2>Questions</h2>{faq}<p class="note">A historical record of specific decisions, each linked to its sources. Not a prediction about any pending application, and not investment advice.</p><footer><b>Not affiliated with or endorsed by the FDA.</b> pdufa.bio is an independent publication with no affiliation with, endorsement by, sponsorship by, or connection to the U.S. Food and Drug Administration. <b>Informational and educational purposes only. Not investment advice.</b> Verify every date and outcome against primary FDA, SEC or company filings.<br><br>&copy; 2026 pdufa.bio. All rights reserved.</footer></div><script src="/cmdk.js" defer></script></body></html>"""

    print(f"since-2024: n={n} early={E} on={O} late={L} | 2024-25 {n45}, 2026 {len(r26)} | "
          f"blind n={nb} crl={cb} split={sb} | ext={len(ext)} | weekend/holiday goals={len(wk)}")
    for lab, k, ap_, c, s in ob:
        print(f"   {lab:<18} n={k:<4} approved={ap_:<4} crl={c:<3} split={s}")
    if a.dry_run:
        return 0
    io.open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(page)
    write_goal_ledger(r45)
    # the /research card and the line on the 2026 page carry this page's own numbers, rewritten every build
    card = (f"{CARD_BEGIN}<a class='row' href='/{REL}'><div class='t'>Early, on the goal date, or late: FDA decisions "
            f"since 2024</div><div class='d'>{n} sourced FDA decisions since January 2024: {E} came before the PDUFA "
            f"goal date, {O} on it and {L} after it, with CRL counts by timing and extended goal dates shown against "
            f"the original date where it is sourced.</div></a>{CARD_END}")
    link = (f'{LINK_BEGIN}<p class="sub" data-timing="since-2024">Since January 2024: {E} of {n} sourced decisions '
            f'came before the goal date, {O} on it and {L} after it. <a href="/{REL}">Every decision since 2024, by '
            f'year, with CRL counts by timing</a>.</p>{LINK_END}')
    for path, block, anchor in ((os.path.join(SITE, "research", "index.html"), card, "<div class='grid'>"),
                                (os.path.join(SITE, "research", "fda-decision-timing", "index.html"), link,
                                 "<h2>Every 2026 sourced decision")):
        if not os.path.exists(path):
            continue
        t = io.open(path, encoding="utf-8", errors="replace").read()
        b, e = (CARD_BEGIN, CARD_END) if block is card else (LINK_BEGIN, LINK_END)
        if b in t:
            t2 = re.sub(re.escape(b) + ".*?" + re.escape(e), lambda m: block, t, flags=re.S)
        elif anchor in t:
            t2 = t.replace(anchor, (anchor + block) if block is card else (block + anchor), 1)
        else:
            t2 = t
        if t2 != t:
            io.open(path, "w", encoding="utf-8").write(t2)
    print(f"wrote /{REL} and {csv_rel}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
