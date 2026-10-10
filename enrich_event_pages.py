# -*- coding: utf-8 -*-
"""enrich_event_pages.py -- every pending event page gets, from ONE generator: an Event schema that states
the row's date, a link to any sibling application of the same drug, and hand-sourced trial facts.

Audit 2026-10-10 items 2 and 4. Two generators were producing two kinds of page: the hand-grown pages
(60+ on a 2026-09-02 timestamp) had no Event schema and no trial names, while pages regenerated since
09-18 carried startDate and a current stamp. And a drug with two pending applications had pages that
never mentioned each other. This runs after build_pdufa_event_pages.py and before the normalisers, on the
page event_pages.resolve() picks for each pending row (the one that states the row's date):

  EVT   <!--EVT:BEGIN-->...<!--EVT:END-->   Event JSON-LD (startDate at the row's precision) in <head>,
        added only when the page has no Event schema; rewritten when ours is stale.
  SIB   <!--SIB:BEGIN-->...<!--SIB:END-->   "Also under FDA review from {company}: {sibling}, {date}" when
        another pending row of the same ticker names the same drug.
  TRIAL <!--TRIAL:BEGIN-->...<!--TRIAL:END--> the sentence from _event_trial_facts.json, quoted from the
        source it links; and that file's description replaces the meta/og/twitter description (<=158).

Marker-bounded and idempotent. A page's content changes only when a fact changes, so the content-change
date (and with it dateModified / article:modified_time, owned by build_date_modified.py) moves only then.
Facts only; not investment advice.

    python enrich_event_pages.py [--dry-run]
"""
import argparse
import html
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import event_pages as EP  # noqa: E402
from site_windows import window_label  # noqa: E402

SITE = os.path.join(HERE, "pdufa_site_src")
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")
FACTS = os.path.join(HERE, "_event_trial_facts.json")
MON3 = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def esc(s):
    return html.escape(str(s or ""), quote=True)


def pretty(row):
    d = str(row.get("d") or "")[:10]
    if str(row.get("dp") or "day") == "day":
        return f"{MON3[int(d[5:7])]} {int(d[8:10])}, {d[:4]}"
    return window_label(row)


def event_ld(row, url):
    d, dp = str(row.get("d") or "")[:10], str(row.get("dp") or "day")
    drug = EP.drug_of(row)
    start = d if dp == "day" else str(row.get("dm") or d[:7])
    return json.dumps({
        "@context": "https://schema.org", "@type": "Event",
        "name": f"{drug} FDA decision",
        "description": (f"{drug} FDA decision: FDA PDUFA target decision {'date' if dp == 'day' else 'window'}"
                        f" {pretty(row)}. Facts only, not advice."),
        "eventStatus": "https://schema.org/EventScheduled",
        "eventAttendanceMode": "https://schema.org/OnlineEventAttendanceMode",
        "organizer": {"@type": "Organization", "name": "U.S. Food and Drug Administration", "url": "https://www.fda.gov"},
        "location": {"@type": "VirtualLocation", "url": url},
        "url": url, "startDate": start, "endDate": start}, ensure_ascii=False)


def set_meta(doc, desc):
    for pat in (r'(<meta name="description" content=")[^"]*(")',
                r'(<meta property="og:description" content=")[^"]*(")',
                r'(<meta name="twitter:description" content=")[^"]*(")'):
        doc = re.sub(pat, lambda m: m.group(1) + esc(desc) + m.group(2), doc, count=1)
    return doc


def insert_after_sub(doc, block):
    """Place a block after the first <div class="sub">...</div> following <h1>, else after </h1>."""
    h = doc.find("<h1")
    m = re.compile(r'<div class="sub">.*?</div>', re.S).search(doc, h if h >= 0 else 0)
    if m:
        return doc[:m.end()] + block + doc[m.end():]
    e = doc.find("</h1>")
    return doc[:e + 5] + block + doc[e + 5:] if e >= 0 else doc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    src = io.open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
    rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    facts = json.load(io.open(FACTS, encoding="utf-8")) if os.path.exists(FACTS) else {}
    pend = EP.pending_rows(rows)
    groups = {}
    for r in pend:
        groups.setdefault((str(r.get("t") or "").upper(), EP.drug_token(r)), []).append(r)
    n_evt = n_sib = n_trial = n_desc = n_pages = 0
    unresolved = []
    for r in pend:
        url = EP.resolve(r)
        if not url:
            unresolved.append(r["id"])
            continue
        p = os.path.join(SITE, url.strip("/").replace("/", os.sep), "index.html")
        doc = io.open(p, encoding="utf-8").read()
        orig = doc
        full = "https://www.pdufa.bio" + url
        # EVT
        ld = f'<!--EVT:BEGIN--><script type="application/ld+json">{event_ld(r, full)}</script><!--EVT:END-->'
        if "<!--EVT:BEGIN-->" in doc:
            doc2 = re.sub(r"<!--EVT:BEGIN-->.*?<!--EVT:END-->", lambda m: ld, doc, flags=re.S)
            if doc2 != doc:
                doc = doc2; n_evt += 1
        elif '"@type":"Event"' not in doc.replace(" ", "").replace("\n", ""):
            doc = doc.replace("</head>", ld + "</head>", 1); n_evt += 1
        # SIB
        sibs = [x for x in groups[(str(r.get("t") or "").upper(), EP.drug_token(r))] if x["id"] != r["id"]]
        sib_html = ""
        if sibs:
            parts = []
            for x in sorted(sibs, key=lambda x: x.get("d") or ""):
                xu = EP.resolve(x)
                tr = (x.get("_d") or {}).get("trial")
                lab = f"{esc(EP.drug_of(x))}" + (f" ({esc(tr)})" if tr else "") + f", {esc(pretty(x))}"
                parts.append(f'<a href="{esc(xu)}">{lab}</a>' if xu else lab)
            sib_html = ('<!--SIB:BEGIN--><p class="note" style="margin:8px 0">Also under FDA review from '
                        f'{esc(r.get("company") or str(r.get("t") or "").upper())}, as a separate application: '
                        + "; ".join(parts) + ". One application, one page; this page is the "
                        + (f'{esc((r.get("_d") or {}).get("trial"))} ' if (r.get("_d") or {}).get("trial") else "")
                        + f"application with the {esc(pretty(r))} goal date.</p><!--SIB:END-->")
        if "<!--SIB:BEGIN-->" in doc:
            doc2 = re.sub(r"<!--SIB:BEGIN-->.*?<!--SIB:END-->", lambda m: sib_html, doc, flags=re.S)
            if doc2 != doc:
                doc = doc2; n_sib += 1
        elif sib_html:
            doc = insert_after_sub(doc, sib_html); n_sib += 1
        # TRIAL + description
        f = facts.get(r["id"])
        if f:
            sent = str(f.get("sentence") or "").strip()
            tb = ""
            if sent:
                tb = ('<!--TRIAL:BEGIN--><p class="sub" style="margin:10px 0 0">' + esc(sent)
                      + (f' (<a href="{esc(f["source_url"])}" rel="noopener">{esc(f.get("source_label") or "source")}</a>)'
                         if f.get("source_url") else "") + "</p><!--TRIAL:END-->")
            if "<!--TRIAL:BEGIN-->" in doc:
                doc2 = re.sub(r"<!--TRIAL:BEGIN-->.*?<!--TRIAL:END-->", lambda m: tb, doc, flags=re.S)
                if doc2 != doc:
                    doc = doc2; n_trial += 1
            elif tb:
                # after the sibling block when present, else after the sub line
                if "<!--SIB:END-->" in doc:
                    doc = doc.replace("<!--SIB:END-->", "<!--SIB:END-->" + tb, 1)
                else:
                    doc = insert_after_sub(doc, tb)
                n_trial += 1
            desc = str(f.get("description") or "").strip()
            if desc and len(desc) <= 158:
                doc2 = set_meta(doc, desc)
                if doc2 != doc:
                    doc = doc2; n_desc += 1
            elif desc:
                print(f"  {r['id']}: description is {len(desc)} chars (>158), not applied")
        if doc != orig:
            n_pages += 1
            if not a.dry_run:
                io.open(p, "w", encoding="utf-8", newline="\n").write(doc)
    print(f"event pages enriched: {n_pages} page(s) changed; Event schema {n_evt}, sibling links {n_sib}, "
          f"trial facts {n_trial}, descriptions {n_desc}; {len(pend)} pending rows, "
          f"{len(pend) - len(unresolved)} resolve to a page")
    if unresolved:
        print("  no page states the row's date: " + ", ".join(unresolved))
    return 0


if __name__ == "__main__":
    sys.exit(main())
