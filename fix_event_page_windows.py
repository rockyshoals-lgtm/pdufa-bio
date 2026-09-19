# -*- coding: utf-8 -*-
"""Event pages must stop publishing a day the dataset no longer holds. Audit 09-14 ORDER 2.

On 09-10 twelve year-end PDUFA rows lost a manufactured day. The calendar was corrected the same
day. The EVENT PAGES were not, because build_pdufa_event_pages.py never overwrites an existing
page (they carry hand-grown content worth keeping) and refresh_moved_pdufa_pages.py only handles
a day moving to another DAY -- it has no concept of a day being withdrawn to a window. So four
days later they still read "Dec 31 2026" in the <title>, the meta description, the og/twitter
tags, the FAQPage answer, the Event schema startDate, the key-facts row and the body: twelve
occurrences per page, on the two strings a SERP snippet and an AI answer quote.

TWO CLASSES, handled differently, because they are different problems.

  BACKED -- a dataset row exists at month/quarter/year precision, so there is a real window to
  state. The page renders that window (via site_windows, the single owner) and its Event schema
  becomes a SPAN rather than a point.

  UNBACKED -- no dataset row at all and no source at any granularity. A page with nothing behind
  it is not improved by a tidier window, so it says the date is not sourced, drops the date from
  its title rather than leading with a claim it cannot support, stops promising "the primary
  source" in its meta description, and has its Event node REMOVED from the JSON-LD: schema.org
  Event requires a startDate, and we do not have one.

WRITTEN CAREFULLY THE SECOND TIME. The first version ended with a blanket "replace any leftover
occurrence of the old date" and that ran after the structured edits, so it clobbered the Event
span it had just written -- `"startDate":"2026-12-01","endDate":"Dec 2026"` -- put the string
"Date not sourced" in a date field, and mangled an FAQ answer into "...(Novo Nordisk A/S) P26".
This version does structured edits only, rewrites JSON-LD by parsing it rather than by string
surgery, and then REPORTS any remaining occurrence instead of bulldozing it.

    python fix_event_page_windows.py [--dry-run]
"""
import argparse
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from site_windows import (UNSOURCED_LABEL, window_label,  # noqa: E402
                          window_label_long, window_span)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SITE = "pdufa_site_src"
STOP = {"pdufa", "date", "and", "the"}
LD = re.compile(r'(<script type="application/ld\+json">)(.*?)(</script>)', re.S)


def toks(s):
    return {w for w in re.findall(r"[a-z][a-z0-9]{2,}", str(s or "").lower())
            if w not in STOP}


def match_row(slug, rows):
    tk = slug.split("-")[0].upper()
    part = slug[len(tk):].lstrip("-")
    st = toks(part.replace("-", " "))
    cands = [r for r in rows if str(r.get("t") or "").upper() == tk
             and r.get("type") == "PDUFA"
             and str(r.get("st") or "").lower() != "decided"]
    hits = [c for c in cands if (not st) or (st & toks(c.get("name")))]
    return hits[0] if len(hits) == 1 else None


def walk(node, fn):
    if isinstance(node, dict):
        fn(node)
        for v in node.values():
            walk(v, fn)
    elif isinstance(node, list):
        for v in node:
            walk(v, fn)


def rewrite_jsonld(doc, iso, label, span, drop_event, faq_old, faq_new):
    """Parse each JSON-LD block, fix dates/answers structurally, re-serialise."""
    def one(m):
        head, body, tail = m.groups()
        try:
            data = json.loads(body)
        except Exception:  # noqa: BLE001
            return m.group(0)

        def fix(d):
            if d.get("@type") == "Event":
                if span[0]:
                    d["startDate"], d["endDate"] = span
            if d.get("@type") == "Answer" and isinstance(d.get("text"), str):
                d["text"] = d["text"].replace(faq_old, faq_new)
            for k in ("name", "headline", "description"):
                if isinstance(d.get(k), str):
                    d[k] = d[k].replace(f", {pretty_of(iso)} |", f", {label} |") \
                               .replace(pretty_of(iso), label).replace(iso, label)

        walk(data, fix)

        if drop_event:
            def strip(node):
                if isinstance(node, dict):
                    for k, v in list(node.items()):
                        if isinstance(v, list):
                            node[k] = [x for x in v
                                       if not (isinstance(x, dict)
                                               and x.get("@type") == "Event")]
                            for x in node[k]:
                                strip(x)
                        else:
                            strip(v)
                elif isinstance(node, list):
                    for x in node:
                        strip(x)
            if isinstance(data, list):
                data = [x for x in data
                        if not (isinstance(x, dict) and x.get("@type") == "Event")]
            strip(data)
        return head + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + tail
    return LD.sub(one, doc)


MON3 = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def pretty_of(iso):
    """The no-comma form the older template writes ("Dec 31 2026")."""
    try:
        y, m, d = int(iso[:4]), int(iso[5:7]), int(iso[8:10])
        return f"{MON3[m]} {d} {y}"
    except Exception:
        return iso


def pretty_forms(iso):
    """Every rendering of a day the event templates emit. 2026-09-15: REGN-cemdisiran kept
    "Nov 30, 2026" in its title, metas and sub line after the fact was windowed, because only
    the Dec 31 comma form was covered. Any day, both forms, plus the long-month form."""
    try:
        y, m, d = int(iso[:4]), int(iso[5:7]), int(iso[8:10])
    except Exception:
        return [iso]
    full = ["", "January", "February", "March", "April", "May", "June", "July", "August",
            "September", "October", "November", "December"][m]
    return [f"{MON3[m]} {d} {y}", f"{MON3[m]} {d}, {y}", f"{full} {d}, {y}", f"{full} {d} {y}"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    src = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"),
                  encoding="utf-8", errors="replace").read().replace("\x00", "")
    rows, _ = json.JSONDecoder().raw_decode(src[src.find("["):])

    changed = 0
    leftovers = []
    unbacked = []
    for slug in sorted(os.listdir(os.path.join(SITE, "pdufa"))):
        p = os.path.join(SITE, "pdufa", slug, "index.html")
        if not os.path.isfile(p):
            continue
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        # A DECIDED page is not ours. mark_event_pages_decided owns those, and two of the
        # "unbacked" pages turned out to be exactly that: /pdufa/GILD-trodelvy (Trodelvy +
        # Keytruda, approved 2026-06-24) and /pdufa/RHHBY-lunsumio-polivy (approved
        # 2025-12-22) were publishing a Dec 31 2026 PDUFA date for drugs approved months
        # earlier. Rewriting their goal date to "not sourced" buried a bigger finding under a
        # smaller one; the honest fix for them is the decided banner, not a window.
        if "<!--DECIDED:BEGIN-->" in doc or "FDA decision</span>" in doc:
            continue
        m = re.search(r'FDA PDUFA target date</span><b>(\d{4}-\d{2}-\d{2})</b>', doc)
        if not m:
            # 2026-09-15: a page already windowed by an EARLIER pass keeps that pass's label in
            # its title when the row's precision later changes (NVCR: month -> quarter left
            # "November 2026" in <title> beside a "Q4 2026" fact). If the fact is a window
            # label and the row now has a different one, every rendering moves with it.
            w = re.search(r'FDA PDUFA target date</span><b>((?:Q[1-4] \d{4})|(?:[A-Z][a-z]{2,8} \d{4})|(?:\d{4}))</b>', doc)
            row = match_row(slug, rows) if w else None
            if row is not None and str(row.get("dp") or "day") != "day":
                new = window_label(row)
                ti = re.search(r"<title>(.*?)</title>", doc, re.S)
                tl = re.search(r'((?:Q[1-4] \d{4})|(?:[A-Z][a-z]{2,8} \d{4}))', ti.group(1)) if ti else None
                labels = {w.group(1)} | ({tl.group(1)} if tl else set())
                d2 = doc
                # the sentinel day in any rendering (REGN-cemdisiran: fact windowed, title and
                # metas still "Nov 30, 2026")
                for pf in pretty_forms(str(row.get("d") or "")):
                    d2 = d2.replace(f", {pf}", f", {new}").replace(f"target <b>{pf}</b>", f"target <b>{new}</b>") \
                           .replace(f"target is {pf} for", f"decision is expected in {new} for") \
                           .replace(f"date is {pf} for", f"decision is expected in {new} for")
                for old in sorted(labels - {new}):
                    d2 = d2.replace(old, new)
                    long_old = {"Jan": "January", "Feb": "February", "Mar": "March", "Apr": "April",
                                "Jun": "June", "Jul": "July", "Aug": "August", "Sep": "September",
                                "Oct": "October", "Nov": "November", "Dec": "December"}.get(old[:3])
                    if long_old:
                        d2 = d2.replace(f"{long_old} {old[-4:]}", new)
                if d2 != doc:
                    changed += 1
                    print(f"  /pdufa/{slug}: window label {sorted(labels - {new})} -> {new} "
                          f"(row precision {row.get('dp')})")
                    if not a.dry_run:
                        io.open(p, "w", encoding="utf-8").write(d2)
            continue
        iso = m.group(1)
        row = match_row(slug, rows)
        if row is not None and str(row.get("dp") or "day") == "day":
            continue
        if row is None and iso != "2026-12-31":
            continue

        backed = row is not None
        label = window_label(row) if backed else UNSOURCED_LABEL
        longl = window_label_long(row) if backed else "not sourced"
        span = window_span(row) if backed else (None, None)
        pretty = pretty_of(iso)
        orig = doc

        forms = pretty_forms(iso)
        # --- titles / og / twitter -------------------------------------------------
        for sep in ("|", '"', "<"):
            for pf in forms:
                if backed:
                    doc = doc.replace(f", {pf} {sep}", f", {label} {sep}")
                    doc = doc.replace(f", {pf}{sep}", f", {label}{sep}")
                else:
                    doc = doc.replace(f", {pf} {sep}", f" {sep}")
                    doc = doc.replace(f", {pf}{sep}", f"{sep}")

        # --- meta descriptions -----------------------------------------------------
        for pf in forms + [iso]:
            for variant in (f"FDA PDUFA date is {pf} for", f"FDA PDUFA target is {pf} for"):
                doc = doc.replace(
                    variant,
                    f"FDA PDUFA decision is expected in {label} for" if backed
                    else "FDA PDUFA date is not sourced for")
        if not backed or not (row.get("_d") or {}).get("source_url"):
            doc = doc.replace(", and the primary source.", ".")
            doc = doc.replace(" and the primary source.", ".")

        # --- visible facts ---------------------------------------------------------
        doc = doc.replace(f'<span>FDA PDUFA target date</span><b>{iso}</b>',
                          f'<span>FDA PDUFA target date</span><b>{label}</b>')
        doc = doc.replace(f'target <b>{iso}</b>', f'target <b>{label}</b>')
        for pf in forms:
            doc = doc.replace(f'target <b>{pf}</b>', f'target <b>{label}</b>')

        # --- FAQ answer, identical string in the rendered card and the JSON-LD ------
        faq_old = f"is {iso} for"
        faq_new = (f"is expected in {longl} for" if backed else
                   "has not been sourced. We hold no filing or release stating a date for")
        doc = doc.replace(faq_old, faq_new)

        # --- JSON-LD, parsed rather than string-surgered ----------------------------
        doc = rewrite_jsonld(doc, iso, label, span, drop_event=not backed,
                             faq_old=faq_old, faq_new=faq_new)

        n_left = len(re.findall(re.escape(iso) + r"|Dec 31,? 2026", doc))
        if n_left:
            leftovers.append((slug, n_left))
        if doc != orig:
            changed += 1
            if not backed:
                unbacked.append(slug)
            print(f"  /pdufa/{slug:<32} {iso} -> {label}"
                  + ("   [no dataset row]" if not backed else "")
                  + (f"   LEFTOVERS={n_left}" if n_left else ""))
            if not a.dry_run:
                io.open(p, "w", encoding="utf-8").write(doc)

    print(f"\n{changed} event page(s) rewritten; {len(unbacked)} had no dataset row"
          + ("   (--dry-run)" if a.dry_run else ""))
    if leftovers:
        print("  STILL CONTAIN THE OLD DAY (inspect, do not bulldoze): "
              + ", ".join(f"{s}x{n}" for s, n in leftovers))
    return 0


if __name__ == "__main__":
    sys.exit(main())
