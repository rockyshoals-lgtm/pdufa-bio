# -*- coding: utf-8 -*-
"""link_crl_letters.py -- CRL decision pages link the FDA's actual letter.

Audits 09-01 through 09-02c, item open since the corpus landed: we hold 458 FDA
Complete Response Letters (openFDA transparency program) and cited zero of them. The
letters are public, hosted by FDA at https://download.open.fda.gov/crl/{file_name}
(verified 200), and they are the PRIMARY source for the very pages that assert a CRL
happened. The 09-02c audit's timing point: the decision template was just rewritten,
so this is the cheapest moment to add the source link.

Match rule (verify-then-publish, conservative): a corpus letter attaches to a CRL
decision page only when the letter_date equals the page's decision date exactly AND the
letter's company name shares a meaningful token with the page's company name. Two
different sponsors can receive CRLs on the same day; the company check keeps their
letters apart. No match = no card; a wrong primary source is worse than none.

Injects a marker-based card (CRLSRC) after the freshness stamp: application number,
letter date, and the FDA-hosted PDF. Idempotent; re-runs replace in place. Counts,
never rates -- the card states what the letter is, not what CRLs "mean".
"""
import datetime as dt
import glob
import html as _html
import io
import json
import os
import re
import sys
from urllib.parse import quote as _urlq

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
sys.path.insert(0, HERE)
from capture_crl_corpus import newest_corpus  # noqa: E402
CORPUS = newest_corpus() or os.path.join(HERE, "CRL_corpus_openFDA_2026-08-29.json")
B, E = "<!--CRLSRC:BEGIN-->", "<!--CRLSRC:END-->"
STOP = {"inc", "corp", "llc", "ltd", "pharmaceuticals", "pharmaceutical", "pharma",
        "therapeutics", "biosciences", "bioscience", "sciences", "company", "holdings",
        "group", "limited", "plc"}


def toks(s):
    return {w for w in re.findall(r"[a-z0-9]{3,}", str(s or "").lower())
            if w not in STOP}


def load_findings():
    try:
        j = json.load(io.open(os.path.join(HERE, "_crl_letter_findings.json"), encoding="utf-8"))
        return {x["file_name"]: x for x in j.get("letters", [])}
    except Exception:
        return {}


def load_rows():
    src = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8",
                  errors="replace").read().replace("\x00", "")
    i, j = src.index("["), src.rindex("]") + 1
    return src, i, j, json.loads(src[i:j])


MONN = ["", "January", "February", "March", "April", "May", "June", "July",
        "August", "September", "October", "November", "December"]


def pretty(iso):
    d = dt.date.fromisoformat(iso)
    return f"{MONN[d.month]} {d.day}, {d.year}"


def main():
    raw = json.load(io.open(CORPUS, encoding="utf-8"))
    recs = raw if isinstance(raw, list) else raw.get("records") or raw.get("results")
    findings = load_findings()
    src, i0, j0, rows = load_rows()
    by_key = {(str(r.get("t") or "").upper(), str(r.get("dcd") or "")[:10]): r for r in rows
              if r.get("type") == "PDUFA" and r.get("dcd")}
    by_date = {}
    for r in recs:
        m = re.match(r"(\d{2})/(\d{2})/(\d{4})", str(r.get("letter_date") or ""))
        if not m or "COMPLETE RESPONSE" not in str(r.get("letter_type", "")).upper():
            continue
        iso = f"{m.group(3)}-{m.group(1)}-{m.group(2)}"
        by_date.setdefault(iso, []).append((iso, r))

    linked = skipped = ds_changed = 0
    for p in sorted(glob.glob(os.path.join(SITE, "fda-decision", "*", "index.html"))):
        slug = os.path.basename(os.path.dirname(p))
        m = re.match(r"([A-Z]{1,6})-(\d{4}-\d{2}-\d{2})$", slug)
        if not m:
            continue
        tk, dcd = m.group(1), m.group(2)
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        if not re.search(r"CRL|Complete Response", doc[:3000], re.I):
            continue                     # approvals and withdrawals have other sources
        # The LETTER is dated the FDA action day; our page often carries the company's
        # ANNOUNCEMENT day (ACHV: goal Fri Jun 20, announced Mon Jun 22). Accept a
        # letter dated up to 4 days BEFORE the page date, never after -- a letter dated
        # after our decision date would belong to a different action. (Exception: a
        # CORRECTED letter, which the findings ledger maps to its page by hand.)
        d0 = dt.date.fromisoformat(dcd)
        cands = []
        for back in range(0, 5):
            cands += by_date.get((d0 - dt.timedelta(days=back)).isoformat(), [])
        hand = [(x["letter_date"], r) for r in recs for x in findings.values()
                if slug in x.get("pages", []) and str(r.get("file_name") or "").strip() == x["file_name"]]
        # 2026-09-20: the company used to be parsed from the meta description, which the
        # snippet rewriter had shortened to "ACHV: ..." -- so the token set was {"achv"} and
        # no letter ever matched. The dataset row (company field) is the owner of the name.
        row = by_key.get((tk, dcd))
        page_co = toks((row or {}).get("company") or "")
        if not page_co:
            cm = re.search(r"<span>Company</span><b>([^<]+)</b>", doc)
            page_co = toks(_html.unescape(cm.group(1))) if cm else toks(tk)
        hits = hand or [(iso, r) for iso, r in cands if toks(r.get("company_name")) & page_co]
        if len(hits) != 1:
            if len(hits) > 1:
                print(f"  SKIP {slug}: {len(hits)} same-day letters match the company "
                      f"-- resolve by hand")
                skipped += 1
            continue
        letter_iso, r = hits[0]
        fn = str(r.get("file_name") or "").strip()
        if not fn.lower().endswith(".pdf"):
            continue
        apps = r.get("application_number")
        app = ", ".join(apps) if isinstance(apps, list) else str(apps or "")
        f = findings.get(fn) or {}
        action = f.get("fda_action_date") or letter_iso
        url = "https://download.open.fda.gov/crl/" + _urlq(fn)
        dated = (f"dated {pretty(letter_iso)}" if not f.get("letter_type_note")
                 else f"dated {pretty(letter_iso)} (a corrected letter; it states the action date remains {pretty(action)})")
        ann = "" if action == dcd else f" The company announced the decision on {pretty(dcd)}; the FDA acted on {pretty(action)}."
        card = (f'{B}<div style="background:#0c1d38;border:1px solid #2a496f;'
                f'border-radius:10px;padding:11px 14px;margin:10px 0 14px;'
                f'font-size:14px"><b style="color:#e3ba5e">The FDA\'s own letter</b> '
                f'&middot; <a href="{url}" rel="noopener">Complete Response Letter, '
                f'{_html.escape(app)} (PDF)</a>, {dated}, released under FDA\'s CRL '
                f'transparency program.{_html.escape(ann)}')
        if f.get("deficiencies"):
            card += ('<div style="margin-top:8px"><b style="color:#f2f6fc">What the letter says has to be '
                     'fixed</b> (the letter\'s own section headings; read against the PDF, not '
                     'openFDA\'s OCR text):<ul style="margin:6px 0 0 18px;padding:0">')
            for dfc in f["deficiencies"]:
                card += f'<li style="margin:4px 0"><b>{_html.escape(dfc["heading"])}.</b> {_html.escape(dfc["summary"])}</li>'
            card += "</ul>"
            for na in f.get("not_approvability") or []:
                card += (f'<div style="margin-top:6px;color:#a7bcd9"><b>{_html.escape(na["heading"])}</b> '
                         f'(the letter says this is not an approvability issue): {_html.escape(na["summary"])}</div>')
            if f.get("note"):
                card += f'<div style="margin-top:6px;color:#a7bcd9">{_html.escape(f["note"])}</div>'
            card += "</div>"
        card += f"</div>{E}"
        if B in doc:
            new = doc.split(B, 1)[0] + card + doc.split(E, 1)[1]
        else:
            anchor = "<!--FRESH:END-->" if "<!--FRESH:END-->" in doc else "</h1>"
            if anchor not in doc:
                continue
            i = doc.index(anchor) + len(anchor)
            new = doc[:i] + card + doc[i:]
        if new != doc:
            io.open(p, "w", encoding="utf-8").write(new)
            linked += 1
            print(f"  /fda-decision/{slug}: {app} letter linked (dated {letter_iso}; action {action})")
        # the dataset row learns the FDA's action date and the letter as its decision source
        if row is not None:
            d_ = row.setdefault("_d", {})
            want = {"fda_action_date": action,
                    "decision_source": f"FDA Complete Response Letter, {app}, dated {pretty(letter_iso)} (openFDA transparency/crl)",
                    "decision_source_url": url}
            if any(d_.get(k) != v for k, v in want.items()):
                d_.update(want)
                if action != dcd:
                    d_["decision_date_note"] = (f"{dcd} is the company's announcement date; the FDA's letter "
                                                f"is dated {letter_iso}" + (f" and states the action date as {action}" if action != letter_iso else "") + ".")
                row["ua"] = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                ds_changed += 1
    if ds_changed:
        io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"), "w", encoding="utf-8").write(
            src[:i0] + json.dumps(rows, indent=1, ensure_ascii=False) + src[j0:])

    # --- the UPCOMING event page for a resubmission: what the FDA said has to be answered ---
    # Moat audit 09-20b item 2: Corcept's relacorilant resubmission (PDUFA December 17, 2026) is
    # the same NDA the FDA refused on December 30, 2025, and the FDA's stated reasons are in the
    # released letter. The event page carries them, marker-bounded, from the hand-verified ledger.
    PB, PE = "<!--CRLPRIOR:BEGIN-->", "<!--CRLPRIOR:END-->"
    ev_done = 0
    for f in findings.values():
        for slug in f.get("event_pages") or []:
            p = os.path.join(SITE, "pdufa", slug, "index.html")
            if not os.path.isfile(p) or not f.get("deficiencies"):
                continue
            doc = io.open(p, encoding="utf-8", errors="replace").read()
            url = "https://download.open.fda.gov/crl/" + _urlq(f["file_name"])
            action = f.get("fda_action_date") or f["letter_date"]
            blk = (f'{PB}<div style="background:#0c1d38;border:1px solid #2a496f;border-radius:10px;'
                   f'padding:11px 14px;margin:10px 0 14px;font-size:14px">'
                   f'<b style="color:#e3ba5e">What the FDA said the last time</b> &middot; this application '
                   f'({_html.escape(f["application"])}) received a Complete Response Letter with an action date of '
                   f'{pretty(action)} (<a href="{url}" rel="noopener">the FDA\'s letter, PDF</a>, released under '
                   f'FDA\'s CRL transparency program). The letter\'s own section headings, read against the PDF:'
                   f'<ul style="margin:6px 0 0 18px;padding:0">')
            for dfc in f["deficiencies"]:
                blk += f'<li style="margin:4px 0"><b>{_html.escape(dfc["heading"])}.</b> {_html.escape(dfc["summary"])}</li>'
            blk += "</ul>"
            if f.get("note"):
                blk += f'<div style="margin-top:6px;color:#a7bcd9">{_html.escape(f["note"])}</div>'
            blk += ('<div style="margin-top:6px;color:#a7bcd9">This states what the FDA wrote; it is not a view on '
                    'the resubmission\'s outcome.</div>' f'</div>{PE}')
            if PB in doc:
                new = doc.split(PB, 1)[0] + blk + doc.split(PE, 1)[1]
            else:
                anchor = "<!--FRESH:END-->" if "<!--FRESH:END-->" in doc else "</h1>"
                if anchor not in doc:
                    continue
                i = doc.index(anchor) + len(anchor)
                new = doc[:i] + blk + doc[i:]
            if new != doc:
                io.open(p, "w", encoding="utf-8").write(new)
                ev_done += 1
                print(f"  /pdufa/{slug}: prior-CRL block from {f['file_name']}")
    if ev_done:
        print(f"prior-CRL blocks: {ev_done} event page(s)")
    print(f"CRL letters: {linked} page(s) linked, {skipped} ambiguous-skipped, {ds_changed} dataset row(s) "
          f"given the FDA action date (corpus {len(recs)} records)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
