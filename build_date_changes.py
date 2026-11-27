# -*- coding: utf-8 -*-
"""/pdufa-date-changes -- every PDUFA goal date we have seen move, with its source.

Asked in four consecutive audits (09-06 ORDER 7; BPIQ's changelog shape, our sourcing).
Built from `_d.prior_pdufa_date`, which the ingest scripts set when a sponsor discloses a
new action date, plus `_d.date_provenance` / the row's own source link. One dated line per
change, newest first, each linking the document that announced it.

Discipline, stated on the page: this lists changes THIS ARCHIVE RECORDED, not every change
the FDA made. A goal date that moved before we tracked the application, or that moved
without a public announcement, is not here -- and the page says so rather than implying a
census. No forward-looking verb appears: a date that moved once is not a prediction that it
will move again.
"""
import datetime as dt
import html
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
SITE = os.path.join(HERE, "pdufa_site_src")
OUT = os.path.join(SITE, "pdufa-date-changes")
MON = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MONL = ["", "January", "February", "March", "April", "May", "June", "July", "August",
        "September", "October", "November", "December"]


def esc(s):
    return html.escape(str(s), quote=False)


def pretty(iso):
    d = dt.date.fromisoformat(iso)
    return f"{MON[d.month]} {d.day}, {d.year}"


def collect_changes():
    """Every recorded goal-date change, newest first (also read by build_feeds.py)."""
    src = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8",
                  errors="replace").read().replace("\x00", "")
    rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    changes = []
    for r in rows:
        d = r.get("_d") or {}
        prior = str(d.get("prior_pdufa_date") or "")[:10]
        now = str(r.get("d") or "")[:10]
        url = str(d.get("date_provenance") or d.get("source_url_2") or r.get("url") or "")
        # 2026-09-15: `date_history` (audit 09-15 ORDER 2/4) is the row-level record of every
        # date a row has held. A SOURCED entry (it carries the announcing document's url) on a
        # day-precision PDUFA row is a goal-date change this archive recorded, whether or not the
        # ingest script also set prior_pdufa_date.
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", prior) and r.get("type") == "PDUFA" \
                and r.get("dp") == "day":
            hist = [h for h in (d.get("date_history") or []) if isinstance(h, dict)]
            if len(hist) >= 2 and hist[-1].get("url") and hist[-1].get("date") == now:
                prior = str(hist[0].get("date") or "")[:10]
                url = str(hist[-1]["url"])
        if not (re.match(r"^\d{4}-\d{2}-\d{2}$", prior) and
                re.match(r"^\d{4}-\d{2}-\d{2}$", now) and prior != now):
            continue
        changes.append({
            "t": str(r.get("t") or "").upper(),
            "name": str(r.get("name") or ""),
            "company": str(r.get("company") or ""),
            "prior": prior, "now": now,
            "days": (dt.date.fromisoformat(now) - dt.date.fromisoformat(prior)).days,
            "url": url if url.startswith("http") else "",
            "st": str(r.get("st") or ""),
            "ua": str(r.get("ua") or "")[:10],
            "changed": next((str(h.get("changed") or "")[:10] for h in (d.get("date_history") or [])
                             if isinstance(h, dict) and h.get("date") == now and h.get("changed")), ""),
        })
    changes.sort(key=lambda c: c["now"], reverse=True)
    return changes


CENSUS = os.path.join(HERE, "decision_timing_2024_2025.json")
EXTRA = os.path.join(HERE, "pdufa_extensions_sourced.json")
CSV_NAME = "pdufa-goal-date-extensions.csv"
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def short_drug(s):
    return str(s or "").split(" (")[0].split(" - ")[0].strip()


def collect_extensions():
    """Every goal-date extension with BOTH dates read from a document, newest extended date first.

    2026-11-27 (OMW, date-change history): /pdufa-date-changes listed only the 4 changes the live dataset rows carry.
    The 2024-2025 decision-timing census (decision_timing_2024_2025.json, four research passes, red-teamed 2026-11-26)
    holds every extension it found with the sponsor's quote for the original date and for the extended date, the
    stated reason and the FDA action. pdufa_extensions_sourced.json holds the ones found for 2026 the same way. A row
    is listed only when both the original and the extended date are quoted from a document; an extension known only
    from its new date is counted on the timing page, not here, because it cannot say what the date moved from.
    """
    out = []
    srcs = []
    try:
        srcs += [(a, "census") for a in json.load(io.open(CENSUS, encoding="utf-8"))["actions"]]
    except Exception:
        pass
    reasons = {}
    try:
        extra = json.load(io.open(EXTRA, encoding="utf-8"))
        reasons = extra.get("reasons") or {}
        srcs += [(a, "2026") for a in extra.get("rows") or []]
    except Exception:
        pass
    for a, origin in srcs:
        if not a.get("extended"):
            continue
        old, new = str(a.get("goal_date_original") or ""), str(a.get("goal_date_extended") or "")
        if not (ISO.match(old) and ISO.match(new) and new != old):
            continue
        if not (str(a.get("goal_original_url") or "").startswith("http")
                and str(a.get("goal_extended_url") or "").startswith("http")
                and a.get("goal_original_quote") and a.get("goal_extended_quote")):
            continue
        tk = a.get("tickers") if isinstance(a.get("tickers"), list) else ([a["ticker"]] if a.get("ticker") else [])
        act = str(a.get("action_date") or "")
        outcome = str(a.get("outcome") or a.get("action_outcome") or "").strip()
        tku = (tk[0] if tk else "").upper()
        out.append({
            "public_reason": reasons.get(str(a.get("cid") or "")) or reasons.get(f"{tku}|{new}") or "",
            "sponsor_short": re.split(r" \(|;| / ", str(a.get("sponsor") or a.get("company") or ""))[0].strip().rstrip(","),
            "fda_doc": "fda.gov" in str(a.get("goal_extended_url") or ""),
            "t": tku, "drug": short_drug(a.get("drug") or a.get("name")),
            "drug_full": str(a.get("drug") or a.get("name") or ""),
            "application": str(a.get("application") or ""), "sponsor": str(a.get("sponsor") or a.get("company") or ""),
            "old": old, "old_url": a["goal_original_url"], "old_doc": str(a.get("goal_original_doc_date") or "")[:10],
            "old_quote": a["goal_original_quote"],
            "new": new, "new_url": a["goal_extended_url"], "new_doc": str(a.get("goal_extended_doc_date") or "")[:10],
            "new_quote": a["goal_extended_quote"],
            "reason": str(a.get("extension_reason") or "").strip(),
            "act": act if ISO.match(act) else "",
            "basis": str(a.get("action_basis") or ("fda_record" if "fda.gov" in str(a.get("action_url") or "") else "")),
            "outcome": outcome, "act_url": str(a.get("action_url") or ""),
            "days": (dt.date.fromisoformat(new) - dt.date.fromisoformat(old)).days, "origin": origin,
        })
    seen, uniq = set(), []
    for x in sorted(out, key=lambda x: (x["new"], x["t"]), reverse=True):
        k = (x["t"] or x["drug"].lower(), x["new"])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(x)
    return uniq


def outcome_word(o):
    o = o.lower()
    return ("approved" if o.startswith("approv") else "issued a Complete Response Letter" if o.startswith("crl")
            else "approved part of the application and issued a Complete Response Letter for the rest" if o == "split"
            else "")


def main():
    changes = collect_changes()
    exts = collect_extensions()
    ext_keys = {(x["t"], x["new"]) for x in exts}
    others = [c for c in changes if (c["t"], c["now"]) not in ext_keys]

    today = dt.date.today()
    stamp = f"{MONL[today.month]} {today.day}, {today.year}"
    n_ext = len(exts)
    n = n_ext + len(others)

    def dec_link(x):
        if x["t"] and x["act"] and os.path.isdir(os.path.join(SITE, "fda-decision", f'{x["t"]}-{x["act"]}')):
            return f' <a class="lit" href="/fda-decision/{esc(x["t"])}-{esc(x["act"])}">Decision page</a>.'
        if x["t"] and os.path.isdir(os.path.join(SITE, "ticker", x["t"])):
            return f' <a class="lit" href="/ticker/{esc(x["t"])}">{esc(x["t"])} hub</a>.'
        return ""

    def ext_row(x):
        head = (f'<b>{esc(x["t"])}</b> &middot; ' if x["t"] else "") + esc(x["drug"][:70])
        am = re.search(r"\b(?:s?NDA|s?BLA|BL)\s*\d{5,6}(?:/S-?\d+)?", x["application"])
        app = f' ({esc(am.group(0))})' if am else ""
        line = (f'Goal date extended from <b>{esc(pretty(x["old"]))}</b> to <b>{esc(pretty(x["new"]))}</b>, '
                f'{x["days"]} days later' + (", as recorded in the FDA's own review" if x["fda_doc"] else
                                             f', per {esc(x["sponsor_short"])}{"\'" if x["sponsor_short"].endswith("s") else "\'s"} document dated {esc(pretty(x["new_doc"]))}'
                                             if ISO.match(x["new_doc"]) else "") + ".")
        reason = (f' <span class="q">Reason stated: {esc(x["public_reason"])}</span>' if x["public_reason"]
                  else ' <span class="q">No reason stated in the documents read.</span>')
        res = ""
        w = outcome_word(x["outcome"])
        if x["act"] and w:
            rel = (dt.date.fromisoformat(x["act"]) - dt.date.fromisoformat(x["new"])).days
            when = ("on the extended date" if rel == 0 else
                    f'{-rel} day{"" if rel == -1 else "s"} before the extended date' if rel < 0 else
                    f'{rel} day{"" if rel == 1 else "s"} after the extended date')
            if x["basis"] == "fda_record":
                res = f' The FDA {w} on {esc(pretty(x["act"]))}, {when}.'
            else:
                res = f' The sponsor announced on {esc(pretty(x["act"]))} that the FDA {w}.'
        elif x["outcome"].lower() in ("pending", "") and x["new"] >= today.isoformat():
            res = " No FDA action on record yet."
        src = (f' Sources: <a class="lit" href="{esc(x["old_url"])}" rel="nofollow noopener">original date</a>'
               f' &middot; <a class="lit" href="{esc(x["new_url"])}" rel="nofollow noopener">extension</a>'
               + (f' &middot; <a class="lit" href="{esc(x["act_url"])}" rel="nofollow noopener">'
                  f'{"FDA action" if x["basis"] == "fda_record" else "action announcement"}</a>'
                  if x["act_url"].startswith("http") and res else "") + ".")
        return (f'<div class="row"><div class="t">{head}{app}</div><div class="d">{line}{reason}{res}{src}'
                f'{dec_link(x)}</div></div>')

    ext_html = "".join(ext_row(x) for x in exts) or "<p>No sourced extension is on record yet.</p>"
    other_html = "".join(
        f'<div class="row"><div class="t"><b>{esc(c["t"])}</b> &middot; '
        f'{esc(c["name"][:64])}</div><div class="d">Goal date moved from '
        f'<b>{esc(pretty(c["prior"]))}</b> to <b>{esc(pretty(c["now"]))}</b>, '
        f'{abs(c["days"])} day{"" if abs(c["days"]) == 1 else "s"} {"later" if c["days"] > 0 else "earlier"}'
        + (f', announced by {esc(c["company"].rstrip("."))}' if c["company"] else "")
        + (f'. <a class="lit" href="{esc(c["url"])}" rel="nofollow">Source</a>.'
           if c["url"] else ".")
        + f' <a class="lit" href="/pdufa/{esc(c["t"])}">{esc(c["t"])} events</a>.'
        + "</div></div>"
        for c in others)

    # Facts across the extensions, each a count of rows shown on this page.
    acted = [x for x in exts if x["act"] and outcome_word(x["outcome"])]
    fda_acted = [x for x in acted if x["basis"] == "fda_record"]
    n_app = sum(1 for x in acted if x["outcome"].lower().startswith("approv"))
    n_crl = sum(1 for x in acted if x["outcome"].lower().startswith("crl"))
    n_split = sum(1 for x in acted if x["outcome"].lower() == "split")
    rel = [(dt.date.fromisoformat(x["act"]) - dt.date.fromisoformat(x["new"])).days for x in fda_acted]
    r_e, r_o, r_l = sum(1 for d in rel if d < 0), sum(1 for d in rel if d == 0), sum(1 for d in rel if d > 0)
    lens = sorted(x["days"] for x in exts)
    n90 = sum(1 for d in lens if 89 <= d <= 92)
    pending = sum(1 for x in exts if not x["act"])
    facts = (f'<div class="card"><b>{n_ext} sourced extension{"s" if n_ext != 1 else ""}.</b> '
             f'{n90} of them moved the goal date by about three months (89 to 92 days), the length the FDA applies after a major amendment. '
             + (f'Ending in an FDA action: {len(acted)} ({n_app} approved, {n_crl} Complete Response Letter{"s" if n_crl != 1 else ""}'
                + (f', {n_split} split action' if n_split else "") + '). ' if acted else "")
             + (f'Where an FDA record gives the action day ({len(fda_acted)}), the FDA acted before the extended date {r_e} times, '
                f'on it {r_o} times and after it {r_l} time{"" if r_l == 1 else "s"}. ' if fda_acted else "")
             + (f'{pending} {"have" if pending != 1 else "has"} no FDA action on record yet. ' if pending else "")
             + 'Counts of the rows below, not a prediction for any pending application.</div>')

    # CSV of every extension row, with its quotes and sources.
    import csv as _csv
    os.makedirs(OUT, exist_ok=True)
    with io.open(os.path.join(OUT, CSV_NAME), "w", encoding="utf-8", newline="") as fh:
        w = _csv.writer(fh)
        w.writerow(["ticker", "drug", "application", "sponsor", "original_goal_date", "original_source_url",
                    "original_source_date", "original_quote", "extended_goal_date", "extension_source_url",
                    "extension_source_date", "extension_quote", "extension_days", "reason_stated", "fda_action",
                    "action_date", "action_date_basis", "action_source_url"])
        for x in exts:
            w.writerow([x["t"], x["drug_full"], x["application"], x["sponsor"], x["old"], x["old_url"], x["old_doc"],
                        x["old_quote"], x["new"], x["new_url"], x["new_doc"], x["new_quote"], x["days"], x["public_reason"],
                        x["outcome"], x["act"], x["basis"], x["act_url"]])

    title = f"PDUFA Date Changes: {n} FDA Goal Date Extensions, Each Sourced | pdufa.bio"
    desc = (f"{n} PDUFA goal date changes, each with the old date, the new date, the reason stated and "
            f"the FDA's final action, linked to the filings. Updated {stamp}.")
    if len(desc) > 158:
        desc = desc[:158].rsplit(" ", 1)[0].rstrip(",;:") + "."

    qa = [("Why do PDUFA dates change?",
           "The FDA can extend a goal date, most often by three months, when the sponsor "
           "submits a major amendment to the application during review. Sponsors have also reported "
           "extensions for other stated reasons, such as resource constraints at the agency. "
           "A sponsor may also withdraw and resubmit, which starts a new review clock. The agency does not "
           "publish these changes as a list; each one here comes from the company's own documents."),
          ("Does an extended PDUFA date mean the FDA will reject the drug?",
           (f"No such rule exists. Of the {len(acted)} extended reviews on this page that ended in an FDA action, "
            f"{n_app} ended in approval and {n_crl} in a Complete Response Letter"
            + (f", and {n_split} in a split action" if n_split else "") + ". These are counts of past cases, not a "
            "prediction for any pending application.") if acted else
           "This page lists past cases only and makes no prediction for any pending application."),
          ("Is this every PDUFA date change?",
           f"No. It is every change this archive has sourced, currently {n}. A goal date that "
           f"moved without a public announcement, or an extension known only from its new date, is not listed. "
           f"We would rather show a short sourced list than imply a complete one."),
          ("Where do the dates come from?",
           "Company press releases and SEC filings for the goal dates, quoted and linked on every row, and FDA records "
           "for the action dates where the FDA publishes them. pdufa.bio is never cited as its own source.")]
    jsonld = json.dumps({"@context": "https://schema.org", "@type": "FAQPage",
                         "mainEntity": [{"@type": "Question", "name": q,
                                         "acceptedAnswer": {"@type": "Answer", "text": a}}
                                        for q, a in qa]}, ensure_ascii=False)
    dsld = json.dumps({"@context": "https://schema.org", "@type": "Dataset",
                       "name": "PDUFA goal date extensions, sourced",
                       "description": f"{n_ext} FDA PDUFA goal date extensions with the original and extended dates quoted "
                                      "from sponsor documents or FDA records, the reason stated, and the FDA action.",
                       "url": "https://www.pdufa.bio/pdufa-date-changes", "isAccessibleForFree": True,
                       "creator": {"@type": "Organization", "name": "pdufa.bio", "url": "https://www.pdufa.bio/"},
                       "distribution": [{"@type": "DataDownload", "encodingFormat": "text/csv",
                                         "contentUrl": f"https://www.pdufa.bio/pdufa-date-changes/{CSV_NAME}"}]},
                      ensure_ascii=False)
    faq = "".join(
        f'<div style="background:#0c1d38;border:1px solid #1e3a63;border-radius:12px;'
        f'padding:14px 16px;margin:12px 0"><b>{esc(q)}</b>'
        f'<div style="color:#9db3d4;font-size:14px;margin-top:6px">{esc(a)}</div></div>'
        for q, a in qa)
    others_block = (f'<h2>Other recorded changes</h2><div class="sub" style="font-size:14px">Goal-date changes recorded on '
                    f'this site\'s live calendar rows, each linked to the announcement.</div>{other_html}') if others else ""

    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><title>{esc(title)}</title><meta name="description" content="{esc(desc)}"><link rel="canonical" href="https://www.pdufa.bio/pdufa-date-changes"><meta name="robots" content="index,follow,max-image-preview:large"><meta name="theme-color" content="#02060d"><link rel="icon" type="image/svg+xml" href="/favicon.svg"><meta property="og:type" content="article"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}"><meta property="og:url" content="https://www.pdufa.bio/pdufa-date-changes"><style>*{{box-sizing:border-box}}body{{margin:0;background:#02060d;color:#f2f6fc;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;line-height:1.6}}a{{color:#6fb6ff;text-decoration:none}}a:hover{{text-decoration:underline}}.wrap{{max-width:820px;margin:0 auto;padding:22px 18px 60px}}.top{{display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #1a3358;padding-bottom:12px}}.brand{{font-size:19px;font-weight:800}}.brand b{{color:#e3ba5e}}.nav a{{color:#a7bcd9;font-size:13px;margin-left:14px}}h1{{font-size:26px;line-height:1.2;margin:10px 0 6px}}h2{{font-size:18px;color:#e3ba5e;margin:26px 0 8px}}.bc{{font-size:12px;color:#94a9c9;margin:16px 0 4px}}.bc a{{color:#94a9c9}}.sub{{color:#a7bcd9;font-size:15px}}p{{max-width:78ch}}.card{{background:#0c1d38;border:1px solid #1e3a63;border-radius:12px;padding:14px 16px;margin:14px 0;color:#cfe0f5;font-size:14.5px}}.row{{background:#0c1d38;border:1px solid #1e3a63;border-radius:10px;padding:11px 13px;margin:8px 0}}.row .t{{font-size:14.5px}}.row .d{{color:#9db3d4;font-size:13.5px;margin-top:3px}}.row .q{{color:#cfe0f5}}.note{{font-size:12px;color:#94a9c9;line-height:1.6}}footer{{border-top:1px solid #1a3358;margin-top:34px;padding-top:16px;font-size:11.5px;color:#94a9c9;line-height:1.6}}footer b{{color:#a7bcd9}}</style><script type="application/ld+json">{jsonld}</script><script type="application/ld+json">{dsld}</script></head><body><div class="wrap"><div class="top"><a class="brand" href="/">pdufa<b>.bio</b></a><div class="nav"><a href="/calendar">Calendar</a><a href="/decisions">Decisions</a><a href="/readouts">Readouts</a><a href="/research">Research</a></div></div><div class="bc"><a href="/">Home</a> &rsaquo; PDUFA date changes</div><h1>PDUFA date changes</h1><div class="sub">{n} FDA goal date change{'s' if n != 1 else ''} on record, each with the date it moved from and the date it moved to, both quoted from the sponsor's documents or the FDA's own records, the reason stated, and what the FDA did next. A PDUFA date is the FDA's target for completing review, and the agency can extend it, most often by three months after a major amendment.</div>{facts}<h2>Goal date extensions</h2><div class="sub" style="font-size:14px">Newest extended date first. Download every row with its quotes and links: <a href="/pdufa-date-changes/{CSV_NAME}">{CSV_NAME}</a>. Whether each FDA decision since 2024 came early, on the goal date or late is on the <a href="/research/fda-decision-timing/since-2024">decision timing page</a>.</div>{ext_html}{others_block}<div class="note" style="margin-top:10px"><b>What this list is:</b> every goal-date change this archive has sourced, not every change the FDA made. A change that was never announced publicly, or an extension known only from its new date, is absent. Days are counted between the two quoted dates. Updated {esc(stamp)}. New changes are also in the <a href="/feed">decisions feed</a>. Changes to the site's dataset field by field, each linked to its commit, are in <a href="/changes">the dataset change history</a>.</div><h2>Questions</h2>{faq}<p class="note">Historical record of specific date changes, each linked to its source. Not a prediction about any pending application, and not investment advice.</p><footer><b>Not affiliated with or endorsed by the FDA.</b> pdufa.bio is an independent publication with no affiliation with, endorsement by, sponsorship by, or connection to the U.S. Food and Drug Administration. <b>Informational and educational purposes only. Not investment advice.</b> Verify every date against primary FDA, SEC or company filings.<br><br>&copy; {today.year} pdufa.bio. All rights reserved.</footer></div><script src="/cmdk.js" defer></script></body></html>"""

    io.open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(page)
    print(f"wrote /pdufa-date-changes ({n_ext} sourced extension(s), {len(others)} other change(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
