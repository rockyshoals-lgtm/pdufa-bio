# -*- coding: utf-8 -*-
"""/readouts/oncology and /readouts/rare-disease. Audit 09-14 ORDER item 7 (promoted).

WHY THESE TWO AND NOT ANY OTHERS. They are the only two the evidence names. In the six days to
2026-09-13 the auditor measured:

    "major upcoming Phase 3 oncology trial readouts next 12 months key companies"
        28 -> 77 citations,  65.12% -> 66.38% share   (the highest share we hold anywhere)
    "upcoming clinical trial readouts rare disease specialty pharma 2025 2026"
        75 -> 102 citations, 31.25% -> 32.59% share

Both rose in citations AND in share, and both were being answered off the generic /readouts hub
with no dedicated page. Meanwhile share on our two flagship queries FELL while volume grew. So
this is the one place where the evidence says a new page is worth more than a fix.

WHAT THESE PAGES WILL NOT DO. No approval odds, no probability, no "key companies to watch", no
ranking by market cap. The queries invite exactly that and it is not what this site is. Each page
states an n, says plainly what is counted and what is not, renders every row at the precision the
registry or the company actually gave (via site_windows, the single owner, so these hubs cannot
become another disagreeing surface), and links each row to its own source.

SELECTION, and every rule here is a lesson already paid for elsewhere in this codebase:
  * Readout rows only. A PDUFA is a regulatory decision, not a readout.
  * st in (Guided, Estimated). A Reported row has already happened.
  * Nothing past-dated on a page headed "upcoming".
  * The therapeutic area comes from the row's own `ta` field. No keyword guessing from the drug
    name -- that is the custirsen failure (build_condition_pages, 08-29) and it is not worth
    repeating for a bigger row count.

    python build_readout_ta_hubs.py [--dry-run]
"""
import argparse
import datetime as dt
import html
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from build_condition_pages import FOOTER, NAV, shell, faq_jsonld  # noqa: E402
from site_dates import eastern_today as _today                    # noqa: E402
from site_windows import window_label, window_label_long          # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SITE = os.path.join(HERE, "pdufa_site_src")
MON = ["", "January", "February", "March", "April", "May", "June", "July",
       "August", "September", "October", "November", "December"]

HUBS = [
    {
        "slug": "oncology",
        "ta": {"oncology"},
        "h1": "Upcoming oncology clinical trial readouts",
        "word": "oncology",
        "title": "Upcoming Oncology Clinical Trial Readouts ({year}) | pdufa.bio",
        "desc": ("Upcoming oncology clinical-trial readouts: company, drug, indication and the "
                 "registered trial for each. Dates are estimated primary-completion windows or "
                 "company guidance, shown at the precision the source gave."),
    },
    {
        "slug": "rare-disease",
        "ta": {"rare disease", "rare"},
        "h1": "Upcoming rare disease clinical trial readouts",
        "word": "rare disease",
        "title": "Upcoming Rare Disease Clinical Trial Readouts ({year}) | pdufa.bio",
        "desc": ("Upcoming rare-disease clinical-trial readouts: company, drug, indication and "
                 "the registered trial for each. Dates are estimated primary-completion windows "
                 "or company guidance, shown at the precision the source gave."),
    },
]


def esc(s):
    return html.escape(str(s or ""), quote=True)


def load():
    src = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"),
                  encoding="utf-8", errors="replace").read().replace("\x00", "")
    rows, _ = json.JSONDecoder().raw_decode(src[src.find("["):])
    return rows


def source_for(r):
    """(href, label) for this row's own source. Never a shared or inferred link."""
    u = str(r.get("url") or "")
    if u.startswith("http"):
        return u, "company release"
    raw = (r.get("_d") or {}).get("nct_id")
    nct = raw.get("nct") if isinstance(raw, dict) else (raw if isinstance(raw, str) else None)
    if nct and str(nct).upper().startswith("NCT"):
        return f"https://clinicaltrials.gov/study/{nct}", str(nct)
    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    rows = load()
    today = _today().isoformat()
    year = _today().year
    wrote = 0

    # Coverage denominator, so each page can say what it is NOT counting. 58% of forward
    # readouts carried no therapeutic area or only "Other" when these pages were built; a page
    # that prints "37 oncology readouts" without saying that reads as a complete census of the
    # field and is not one.
    all_fwd = [r for r in rows if r.get("type") == "Readout"
               and str(r.get("st") or "") in ("Guided", "Estimated")
               and str(r.get("d") or "") >= today]
    total_fwd = len(all_fwd)
    untagged = sum(1 for r in all_fwd
                   if str(r.get("ta") or "").strip().lower() in ("", "other"))

    for hub in HUBS:
        sel = []
        for r in rows:
            if r.get("type") != "Readout":
                continue
            if str(r.get("st") or "") not in ("Guided", "Estimated"):
                continue
            if str(r.get("ta") or "").strip().lower() not in hub["ta"]:
                continue
            d = str(r.get("d") or "")
            if not d or d < today:
                continue
            sel.append(r)
        sel.sort(key=lambda r: (str(r.get("d")), str(r.get("t"))))

        n = len(sel)
        n_src = sum(1 for r in sel if source_for(r)[0])
        n_guided = sum(1 for r in sel if str(r.get("st")) == "Guided")
        n_est = n - n_guided
        span = ""
        if sel:
            a_, b_ = str(sel[0].get("d"))[:7], str(sel[-1].get("d"))[:7]
            span = (f"{MON[int(a_[5:7])]} {a_[:4]}" if a_ == b_ else
                    f"{MON[int(a_[5:7])]} {a_[:4]} to {MON[int(b_[5:7])]} {b_[:4]}")

        body_rows = []
        for r in sel:
            href, label = source_for(r)
            dd = r.get("_d") or {}
            ind = str(dd.get("indication") or "").strip()
            when = window_label(r)
            est = " (est.)" if str(r.get("st")) == "Estimated" else ""
            line = (f'<div class="t">{esc(r.get("t"))} &middot; {esc(when)}{est}</div>'
                    f'<div class="d">{esc(str(r.get("name"))[:120])}'
                    + (f": {esc(ind[:110])}" if ind else "")
                    + (f' <span style="color:#94a9c9">&middot; {esc(label)}</span>'
                       if label else
                       ' <span style="color:#94a9c9">&middot; no trial record on file</span>')
                    + "</div>")
            if href:
                body_rows.append(f'<a class="row" href="{esc(href)}" rel="nofollow" '
                                 f'target="_blank">{line}</a>')
            else:
                body_rows.append(f'<a class="row" href="/ticker/{esc(r.get("t"))}">{line}</a>')

        counted = (
            f'<div class="note" style="font-size:12px;color:#94a9c9;line-height:1.6;'
            f'margin-top:12px"><b>What is counted:</b> every {esc(hub["word"])} readout in this '
            f'dataset whose date has not yet passed, taken from the row\'s own therapeutic-area '
            f'field rather than guessed from the drug name. {n_guided} of these {n} dates come '
            f'from company guidance and {n_est} are estimated primary-completion windows from '
            f'ClinicalTrials.gov, which shift; each row shows the precision its source actually '
            f'gave, so a row reading a month or a quarter is one where nobody published a day. '
            f'{n_src} of {n} link a trial record or company release. This is a list of dates and '
            f'sources: it carries no approval odds, no probability of success and no ranking.'
            f'<br><br><b>This is a floor, not a complete census.</b> {untagged} of the '
            f'{total_fwd} upcoming readouts we track ({untagged / max(1, total_fwd):.0%}) carry '
            f'no therapeutic area, or are tagged only &ldquo;Other&rdquo;, and are therefore not '
            f'counted on this page. Some of them are almost certainly {esc(hub["word"])}. We '
            f'would rather under-count against a field we can check than pad the number by '
            f'guessing a therapeutic area from a drug name, which is how this site once '
            f'published a discontinued 2017 compound as an upcoming event.</div>')

        faq = [
            (f"How many {hub['word']} readouts are expected?",
             f"This page lists {n} upcoming {hub['word']} clinical-trial readouts"
             + (f", covering {span}" if span else "")
             + f". {n_guided} of the dates are company-guided and {n_est} are estimated "
               f"primary-completion windows from ClinicalTrials.gov. That number is a floor: "
               f"{untagged} of the {total_fwd} upcoming readouts we track carry no therapeutic "
               f"area or are tagged only “Other”, and are not counted here."),
            (f"Are these {hub['word']} readout dates exact?",
             "Mostly no, and the page says which are which. A company-guided date is what the "
             "sponsor stated. An estimated date is the trial's primary-completion window from "
             "ClinicalTrials.gov, which is an estimate that moves. Where a source gave only a "
             "month or a quarter, this page shows a month or a quarter rather than inventing a "
             "day."),
            ("Does this page predict which readouts will be positive?",
             "No. pdufa.bio publishes dates, sources and historical statistics. It does not "
             "publish approval odds or probability of success, and nothing here is investment "
             "advice."),
        ]

        other = "rare-disease" if hub["slug"] == "oncology" else "oncology"
        other_word = "rare disease" if hub["slug"] == "oncology" else "oncology"
        body = (
            f'<div class="bc"><a href="/">Home</a> &rsaquo; <a href="/readouts">Readouts</a> '
            f'&rsaquo; {esc(hub["word"].title())}</div>'
            f'<h1>{esc(hub["h1"])}</h1>'
            f'<div class="sub">{n} upcoming {esc(hub["word"])} readout'
            f'{"s" if n != 1 else ""}'
            + (f", {esc(span)}" if span else "")
            + f". Each row links its own trial record or company release. Dates shown at the "
              f"precision the source gave.</div>"
            f'<div class="grid" style="margin-top:12px">{"".join(body_rows)}</div>'
            + counted
            + f'<p class="sub" style="margin-top:16px">See also '
              f'<a href="/readouts/{other}">upcoming {esc(other_word)} readouts</a>, the full '
              f'<a href="/readouts">clinical trial readout calendar</a>, and the '
              f'<a href="/calendar">FDA decision calendar</a>.</p>'
            f'<h2>Questions</h2>'
            + "".join(f'<div class="card"><b>{esc(q)}</b>'
                      f'<div class="sub" style="margin-top:6px">{esc(ans)}</div></div>'
                      for q, ans in faq)
            + FOOTER)

        url = f"https://www.pdufa.bio/readouts/{hub['slug']}"
        doc = shell(hub["title"].format(year=year), hub["desc"], url, body, faq_jsonld(faq))

        out = os.path.join(SITE, "readouts", hub["slug"], "index.html")
        print(f"  /readouts/{hub['slug']:<14} n={n:<3} guided={n_guided} est={n_est} "
              f"sourced={n_src}  {span}")
        if not a.dry_run:
            os.makedirs(os.path.dirname(out), exist_ok=True)
            io.open(out, "w", encoding="utf-8").write(doc)
            wrote += 1

    # /readouts links to both
    hub_index = os.path.join(SITE, "readouts", "index.html")
    if os.path.exists(hub_index) and not a.dry_run:
        d = io.open(hub_index, encoding="utf-8", errors="replace").read()
        link = ('<!--TAHUBS--><p class="sub" style="margin-top:10px">By therapeutic area: '
                '<a href="/readouts/oncology">oncology readouts</a> &middot; '
                '<a href="/readouts/rare-disease">rare disease readouts</a></p><!--/TAHUBS-->')
        if "<!--TAHUBS-->" in d:
            d = re.sub(r"<!--TAHUBS-->.*?<!--/TAHUBS-->", link, d, flags=re.S)
        else:
            d = d.replace("</h1>", "</h1>" + link, 1)
        io.open(hub_index, "w", encoding="utf-8").write(d)
        print("  /readouts now links both hubs")

    print(f"\n{wrote} readout hub(s) written"
          + ("   (--dry-run)" if a.dry_run else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
