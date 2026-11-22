# -*- coding: utf-8 -*-
"""build_crl_capricor.py -- /crl/capricor-deramiocel: Capricor's two Complete Response Letters, from primary sources.

David, 2026-11-22: "Do a deep dive of the CAPR CRL." The FDA released the first letter (BL 125842, dated
July 9, 2025); the second was announced by Capricor on November 20, 2026 and, when this was written, was not in
the FDA's release. This page puts the FDA's own words next to the company's, dates every step in Eastern time
with its source, and lists the daily closes around each disclosure.

Inputs: _crl_capricor_case.json (hand-gathered sources, read 2026-11-21/22) and the newest FDA CRL corpus
snapshot. Every quote attributed to the FDA letter is re-checked against the FDA's released text on each build
and DROPPED if it no longer matches (printed as a warning). Whether the FDA has released a second letter for
the BLA is read from the corpus on each build, so the page updates itself when it does.

FACTS ONLY: what the documents say, when, and the recorded closes. No view on any outcome, no odds, no advice.

    python build_crl_capricor.py
"""
import datetime as dt
import html as _html
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
sys.path.insert(0, HERE)
from capture_crl_corpus import newest_corpus  # noqa: E402
from build_crl_facts import CSS, NAV  # noqa: E402

CASE = os.path.join(HERE, "_crl_capricor_case.json")
BASE = "https://www.pdufa.bio"
SLUG = "capricor-deramiocel"
MON = ["", "January", "February", "March", "April", "May", "June", "July", "August",
       "September", "October", "November", "December"]


def esc(s):
    return _html.escape(str(s or "").strip())


def pretty(iso):
    d = dt.date.fromisoformat(iso)
    return f"{MON[d.month]} {d.day}, {d.year}"


def norm(s):
    s = str(s or "").replace("’", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"\s+", " ", s).strip().lower()


def main():
    case = json.load(io.open(CASE, encoding="utf-8"))
    corpus_p = newest_corpus() or os.path.join(HERE, "CRL_corpus_openFDA_2026-08-29.json")
    raw = json.load(io.open(corpus_p, encoding="utf-8"))
    recs = raw.get("results") if isinstance(raw, dict) else raw
    snap = (re.search(r"(\d{4}-\d{2}-\d{2})", os.path.basename(corpus_p)) or [None, ""])[1]
    app_no = re.sub(r"\D", "", case["application"])
    mine = [r for r in recs if any(re.sub(r"\D", "", a.split("/")[0]) == app_no
                                   for a in (r.get("application_number") or []))]
    first = next((r for r in mine if r.get("file_name") == case["letter_file"]), None)
    if not first:
        print(f"capricor page: the FDA letter {case['letter_file']} is not in {os.path.basename(corpus_p)}; page not built")
        return 0
    text = norm(first.get("text"))
    quotes, dropped = [], 0
    for q in case["letter_quotes"]:
        if norm(q["q"]) in text:
            quotes.append(q)
        else:
            dropped += 1
            print(f"  WARN quote not found in the FDA's released text, dropped: {q['q'][:70]}")
    heads = [h for h in case["letter_headings_present"] if norm(h) in text]
    later = sorted((r for r in mine if r is not first and str(r.get("letter_type")) == "COMPLETE RESPONSE"),
                   key=lambda r: r.get("letter_date", "")[-4:] + r.get("letter_date", ""))
    second_released = later[-1] if later else None

    pdf = "https://download.open.fda.gov/crl/" + case["letter_file"]
    title = "Capricor Deramiocel CRLs: FDA Letter vs. Company Statements | pdufa.bio"
    desc = ("Capricor's two Complete Response Letters for deramiocel (BLA 125842): the FDA's own words, the "
            "company's statements, a dated timeline in ET, and closes around each step.")
    B = []
    B.append('<h1>Capricor and deramiocel: <span class="g">two Complete Response Letters</span></h1>')
    B.append(f'<p class="sub">{esc(case["company"])} applied for approval of {esc(case["drug"])} for '
             f'{esc(case["indication"])} under {esc(case["application"])}. The FDA issued a Complete Response '
             f'Letter dated {pretty(case["letter_date"])}, and Capricor announced a second one on November 20, '
             f'2026. This page sets the FDA\'s released letter beside the company\'s statements. Times are '
             f'Eastern. Sources read {esc(case["read"])}. Facts only; no view on any outcome.</p>')

    B.append('<h2>Where things stand</h2><table>')
    rows = [("Application", esc(case["application"])),
            ("First CRL", f'dated {pretty(case["letter_date"])}; <a href="{esc(pdf)}" rel="noopener">the FDA\'s letter (PDF)</a>'),
            ("Resubmission", "Class 2; PDUFA date August 22, 2026, moved to November 22, 2026 (Capricor)"),
            ("Advisory committee", 'July 29, 2026: 3 for, 9 against, 0 abstain (Capricor); '
                                   f'<a href="{esc(case["pages"]["adcomm"])}">meeting page</a>'),
            ("Second CRL", "announced by Capricor November 20, 2026, 7:55 p.m. ET, after the market close"),
            ("Second letter's text", (f'in the FDA\'s release: <a href="https://download.open.fda.gov/crl/'
                                      f'{esc(second_released.get("file_name"))}" rel="noopener">letter dated '
                                      f'{esc(second_released.get("letter_date"))} (PDF)</a>') if second_released
             else f"not in the FDA's CRL release as of the snapshot read for this page ({esc(snap)})")]
    for k, v in rows:
        B.append(f'<tr><td class="dt">{esc(k)}</td><td>{v}</td></tr>')
    B.append('</table>')

    B.append(f'<h2>What the FDA\'s July 9, 2025 letter says</h2><p class="sub">Quoted from the FDA\'s released '
             f'letter (<a href="{esc(pdf)}" rel="noopener">PDF</a>); each quote is checked against the text of the '
             f'letter in the FDA\'s own release (openFDA transparency/crl) every time this page is built.</p><table><tr><th>Topic</th><th>The letter</th></tr>')
    for q in quotes:
        B.append(f'<tr><td class="dt">{esc(q["topic"])}</td><td>&ldquo;{esc(q["q"])}&rdquo;</td></tr>')
    B.append('</table>')
    if heads:
        B.append('<p class="sub">The letter also has sections headed ' + " and ".join(
            f'&ldquo;{esc(h)}&rdquo;' for h in heads) + '. The released version shows no text under either '
            'heading, so what the FDA wrote about manufacturing is not public.</p>')

    B.append('<h2>The letter and the company, side by side</h2><table><tr><th>Topic</th><th>FDA letter, '
             'July 9, 2025</th><th>Capricor</th></tr>')
    for s in case["side_by_side"]:
        B.append(f'<tr><td class="dt">{esc(s["topic"])}</td><td>{esc(s["fda"])}</td><td>{esc(s["co"])}</td></tr>')
    B.append('</table>')

    B.append('<h2>Timeline</h2><table><tr><th>Date (ET)</th><th>Who</th><th>What the source says</th>'
             '<th>Source</th></tr>')
    for e in case["events"]:
        when = pretty(e["date"]) + (f', {esc(e["time"])}' if e.get("time") else "")
        B.append(f'<tr><td class="dt">{when}</td><td>{esc(e["who"])}</td><td>{esc(e["what"])}</td>'
                 f'<td><a href="{esc(e["url"])}" rel="noopener">{esc(e["src"])}</a></td></tr>')
    B.append('</table>')

    B.append('<h2>Closes around each disclosure</h2><p class="sub">CAPR daily closes (FMP end-of-day, '
             'split-adjusted, read November 22, 2026), the last close before each disclosure against the first close '
             'after it. Recorded history, not a forecast.</p><table><tr><th>Disclosure</th><th>When (ET)</th>'
             '<th>Close before</th><th>Close after</th><th>Change</th></tr>')
    for m in case["moves"]:
        b_d, b_c = m["before"]
        if m.get("after"):
            a_d, a_c = m["after"]
            chg = (a_c / b_c - 1) * 100
            after = f'${a_c:.2f} ({esc(pretty(a_d)[:-6])})'
            change = f'{chg:+.1f}%'
        else:
            after, change = "first session after: November 23, 2026", "not yet traded"
        B.append(f'<tr><td class="dt">{esc(m["what"])}</td><td>{esc(m["when"])}</td>'
                 f'<td>${b_c:.2f} ({esc(pretty(b_d)[:-6])})</td><td>{after}</td><td>{change}</td></tr>')
    B.append('</table>')

    B.append(f'<p class="sub">Decision pages: <a href="{esc(case["pages"]["first"])}">July 2025 CRL</a> &middot; '
             f'<a href="{esc(case["pages"]["second"])}">November 2026 CRL</a> &middot; '
             '<a href="/crl/facts">facts from all released CRLs</a> &middot; <a href="/crl">every released CRL</a>.</p>')

    doc = (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
           f'<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
           f'<title>{esc(title)}</title><meta name="description" content="{esc(desc)}">'
           f'<link rel="canonical" href="{BASE}/crl/{SLUG}">'
           f'<meta name="robots" content="index,follow,max-image-preview:large">'
           f'<meta name="theme-color" content="#02060d"><meta property="og:type" content="article">'
           f'<meta property="og:site_name" content="pdufa.bio"><meta property="og:url" content="{BASE}/crl/{SLUG}">'
           f'<meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}">'
           f'<style>{CSS}</style></head><body><div class="wrap">{NAV}' + "".join(B) + "</div></body></html>")
    # the two decision pages point here, marker-bounded (idempotent)
    CB, CE = "<!--CRLCASE:BEGIN-->", "<!--CRLCASE:END-->"
    blk = (f'{CB}<p class="sub" style="font-size:13.5px"><b style="color:#e3ba5e">Both Capricor CRLs, from the '
           f'primary sources:</b> <a href="/crl/{SLUG}">the FDA\'s letter beside the company\'s statements, with a '
           f'dated timeline</a>.</p>{CE}')
    for pg in (case["pages"]["first"], case["pages"]["second"]):
        pp = os.path.join(SITE, pg.strip("/"), "index.html")
        if not os.path.exists(pp):
            continue
        d_ = io.open(pp, encoding="utf-8", errors="replace").read()
        if CB in d_:
            n_ = d_.split(CB, 1)[0] + blk + d_.split(CE, 1)[1]
        else:
            anchor = next((a for a in ("<!--CRLSRC:END-->", "<!--FRESH:END-->", "</h1>") if a in d_), None)
            if not anchor:
                continue
            i = d_.index(anchor) + len(anchor)
            n_ = d_[:i] + blk + d_[i:]
        if n_ != d_:
            io.open(pp, "w", encoding="utf-8").write(n_)
    out = os.path.join(SITE, "crl", SLUG, "index.html")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    io.open(out, "w", encoding="utf-8").write(doc)
    print(f"/crl/{SLUG}: {len(quotes)} letter quote(s) checked ({dropped} dropped), {len(heads)} heading(s), "
          f"{len(case['events'])} timeline rows; second letter {'released' if second_released else 'not in the release'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
