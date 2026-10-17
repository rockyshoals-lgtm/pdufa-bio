# -*- coding: utf-8 -*-
"""fix_decided_event_meta.py -- a decided /pdufa/ event page introduces itself as decided (audit 2026-10-17, 2a).

mark_event_pages_decided.py banners the page and rewrites the body, but its title/description rewrite only fired
in the same pass that matched a single-ticker "PDUFA date:" title. On 2026-10-17, 10 of 27 decided event pages
still told search engines the decision was pending ("IBRX's FDA PDUFA target is Jan 6, 2027 for ANKTIVA", eleven
days after the approval), the IRD/VTRS partner page kept "IRD / VTRS PDUFA date: ... Oct 17, 2026", and 25 kept a
schema.org Event with eventStatus EventScheduled for a decision that had happened.

For every event page carrying a DECBAN, from the dataset row its banner links:
  * title  -- when it still reads "PDUFA date:", becomes "{tickers} FDA decision: {drug}, {Approved|Approval
    announced|Complete Response Letter} {day}" (the announcement wording when the FDA day is not on record);
  * description (and og:/twitter: copies) -- when it is still in the pending tense, becomes a 120-155 character
    statement of the decision. With an FDA-recorded day: "{drug} was approved by the FDA on {day} ...". Without
    one: "Approval of {drug} ... was announced on {day} ... The FDA's action day is not yet on record." A goal date
    is only stated when it is day-precision and sourced. A CRL is a Complete Response Letter, never a rejection;
  * schema.org Event objects are removed (the EVT block and any Event node in other JSON-LD), as for withdrawn
    pages: a decided goal date is not an upcoming event.
Idempotent; only pages that change are written.

    python fix_decided_event_meta.py [--dry-run]
"""
import argparse
import glob
import html
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
B, E = "<!--DECBAN:BEGIN-->", "<!--DECBAN:END-->"
MON = ["", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
       "November", "December"]
STALE = re.compile(r"PDUFA target is|PDUFA date is|PDUFA date:|goal date [A-Z][a-z]+ \d{1,2}, \d{4} under|"
                   r"due to decide|decision is expected|is expected to make|target decision date|under FDA review",
                   re.I)


def pretty(iso):
    y, m, d = (int(x) for x in str(iso)[:10].split("-"))
    return f"{MON[m]} {d}, {y}"


def short(iso):
    y, m, d = (int(x) for x in str(iso)[:10].split("-"))
    return f"{MON[m][:3]} {d}, {y}"


def strip_events(doc):
    doc = re.sub(r"<!--EVT:BEGIN-->.*?<!--EVT:END-->", "", doc, flags=re.S)

    def one(m):
        head, body, tail = m.group(1), m.group(2), m.group(3)
        try:
            data = json.loads(body)
        except Exception:  # noqa: BLE001
            return m.group(0)
        if isinstance(data, dict) and data.get("@type") == "Event":
            return ""

        def walk(node):
            if isinstance(node, dict):
                for k, v in list(node.items()):
                    if isinstance(v, list):
                        node[k] = [x for x in v if not (isinstance(x, dict) and x.get("@type") == "Event")]
                    walk(node[k])
            elif isinstance(node, list):
                for x in node:
                    walk(x)
        before = json.dumps(data, ensure_ascii=False)
        walk(data)
        after = json.dumps(data, ensure_ascii=False)
        return m.group(0) if after == before else head + after + tail
    return re.sub(r'(<script type="application/ld\+json">)(.*?)(</script>)', one, doc, flags=re.S)


def drug_label(row, title_drug):
    d = row.get("_d") or {}
    brand, inn = str(d.get("brand") or "").strip(), str(d.get("inn") or "").strip()
    if brand and inn and brand.lower() not in inn.lower():
        inn_base = re.sub(r"-[a-z]{4}$", "", inn)
        return f"{brand} ({inn_base})"
    return brand or title_drug


CODE = re.compile(r"^(?=[^a-z]*$)[A-Z0-9][A-Z0-9-]*\d[A-Z0-9-]*\b")


def decision_page_drug(tk, dcd):
    """The decision page names the approved product ("Zanvastro (zilganersen)"); the event page was written
    under a development code ("ION373") before the brand existed. Brand (INN), suffix and trial tags dropped."""
    p = os.path.join(SITE, "fda-decision", f"{tk}-{dcd}", "index.html")
    if not os.path.exists(p):
        return ""
    m = re.search(r"<span>Drug / candidate</span><b>(.*?)</b>", io.open(p, encoding="utf-8", errors="replace").read(), re.S)
    if m:
        s = html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).split(" - ")[0].strip()
    else:   # older decision pages carry the drug only in the title: "Gwyn Lo (...) Approved Jul 29, 2026 | ..."
        tm = re.search(r"<title>(.*?)\s+(?:Approved|Approval Announced|FDA Approval Announced)\b",
                       io.open(p, encoding="utf-8", errors="replace").read(), re.S)
        s = html.unescape(tm.group(1)).strip() if tm else ""
    if not s:
        return ""
    bm = re.match(r"\s*([^()]+?)\s*\(([A-Za-z][a-z-]{3,})", s)
    if bm and not CODE.match(bm.group(1)):
        return f"{bm.group(1).strip()} ({re.sub(r'-[a-z]{4}$', '', bm.group(2))})"
    return "" if CODE.match(s) else s


def describe(row, drug, word, dcd):
    d = row.get("_d") or {}
    unsrc = bool(d.get("decision_date_unsourced"))
    fday = d.get("fda_action_date") or (None if unsrc else dcd)
    ind = str(d.get("indication_short") or d.get("title_indication") or "").strip()
    goal = (row.get("d") if str(row.get("dp") or "day") == "day" and not d.get("goal_unsourced") else None)
    g = f" The PDUFA goal date was {pretty(goal)}." if goal else ""
    f_ind = f" for {ind}" if ind else ""
    if word == "Approved" and fday:
        cands = [f"{drug} was approved by the FDA on {pretty(fday)}{f_ind}.{g} Decision record, source and stock reaction linked.",
                 f"{drug} was approved by the FDA on {pretty(fday)}{f_ind}.{g}",
                 f"{drug} was approved by the FDA on {pretty(fday)}.{g}"]
    elif word == "Approved":
        cands = [f"Approval of {drug}{f_ind} was announced on {pretty(dcd)}.{g} The FDA's action day is not yet on record.",
                 f"Approval of {drug} was announced on {pretty(dcd)}.{g} The FDA's action day is not yet on record.",
                 f"Approval of {drug} was announced on {pretty(dcd)}; the FDA's action day is not yet on record."]
    else:
        when = fday or dcd
        cands = [f"{drug} received a Complete Response Letter from the FDA on {pretty(when)}{f_ind}.{g} Source linked.",
                 f"{drug} received a Complete Response Letter from the FDA on {pretty(when)}.{g}",
                 f"{drug} received a Complete Response Letter from the FDA on {pretty(when)}."]
    for c in cands:
        if 70 <= len(c) <= 155:
            return c
    return cands[-1][:155].rsplit(" ", 1)[0].rstrip(",;") + "."


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    src = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8", errors="replace").read()
    rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    by_url = {str(r.get("url")): r for r in rows if str(r.get("url") or "").startswith("/fda-decision/")}
    by_tkd = {(str(r.get("t") or "").upper(), str(r.get("dcd") or "")[:10]): r for r in rows if r.get("dcd")}
    n_t = n_d = n_e = n_pages = 0
    for p in sorted(glob.glob(os.path.join(SITE, "pdufa", "*", "index.html"))):
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        if B not in doc:
            continue
        ban = doc.split(B, 1)[1].split(E, 1)[0]
        lm = re.search(r'href="/fda-decision/([A-Z]{1,6})-(\d{4}-\d{2}-\d{2})"', ban)
        if not lm:
            # older /pdufa/{TICKER} event pages (ROIV, TAK) banner the decision with no decision page to link;
            # the outcome is still settled, so the Event goes. Title and description stay with their builder.
            doc2 = strip_events(doc)
            if doc2 != doc:
                n_e += 1
                n_pages += 1
                if not a.dry_run:
                    io.open(p, "w", encoding="utf-8").write(doc2)
            continue
        tk, dcd = lm.group(1), lm.group(2)
        row = by_url.get(f"/fda-decision/{tk}-{dcd}") or by_tkd.get((tk, dcd)) or {}
        word = ("Approved" if re.search(r"Approved</b>", ban) else
                "Complete Response Letter" if "Complete Response" in ban or "CRL" in ban else None)
        if not word:
            continue
        orig = doc
        tm = re.search(r"<title>(.*?)</title>", doc, re.S)
        title = html.unescape(tm.group(1)) if tm else ""
        lab_m = re.match(r"\s*([A-Z]{1,6}(?:\s*/\s*[A-Z]{1,6})*)\s", title)
        label = lab_m.group(1) if lab_m else tk
        tdm = re.search(r"(?:PDUFA date|FDA decision):\s*(.+?)(?:,\s*(?:[A-Z][a-z]{2} \d|Q\d|[A-Z][a-z]+ \d{4}|Approv|Complete)|\s*\||$)", title)
        title_drug = (tdm.group(1).strip() if tdm else str(row.get("name") or tk))
        rd = (row.get("_d") or {}) if row else {}
        drug = (drug_label(row, title_drug) if rd.get("brand") else
                decision_page_drug(tk, dcd) or title_drug)
        unsrc = bool(rd.get("decision_date_unsourced"))
        fday = rd.get("fda_action_date") or dcd
        first = title_drug.split(" (")[0].split()[0] if title_drug.split() else ""
        code_led = bool(CODE.match(first)) and drug.split(" (")[0] != title_drug.split(" (")[0]
        # brand-first (audit 2026-10-17, 2b): the decision page names a brand for the same INN the title carries
        dbrand = drug.split(" (")[0]
        code_led = code_led or (dbrand.lower() not in title_drug.lower()
                                and title_drug.split(" (")[0].lower() in drug.lower())
        stale_announced = "Approval announced" in title and rd.get("fda_action_date") and not unsrc
        if tm and (re.search(r"PDUFA date:", title) or code_led or stale_announced):
            verb = ("Approval announced " + pretty(dcd)) if (word == "Approved" and unsrc) else f"{word} {pretty(fday)}"
            new_title = f"{label} FDA decision: {drug}, {verb}"
            if len(new_title) > 90:
                new_title = f"{label} FDA decision: {drug.split(' (')[0]}, {verb}"
            new_title += " | pdufa.bio"
            old_esc = tm.group(1)
            doc = doc.replace(f"<title>{old_esc}</title>", f"<title>{html.escape(new_title, quote=False)}</title>", 1)
            for attr in ('property="og:title"', 'name="twitter:title"'):
                doc = re.sub(r'(<meta ' + attr + r' content=")[^"]*(")',
                             lambda m: m.group(1) + html.escape(new_title, quote=True) + m.group(2), doc, count=1)
            old_name = html.unescape(old_esc).replace(" | pdufa.bio", "")
            doc = doc.replace(json.dumps(old_name, ensure_ascii=False)[1:-1],
                              json.dumps(new_title.replace(" | pdufa.bio", ""), ensure_ascii=False)[1:-1])
            n_t += 1
        dm = re.search(r'<meta name="description" content="([^"]*)"', doc)
        cur = html.unescape(dm.group(1)) if dm else ""
        if dm and (STALE.search(cur) or (code_led and title_drug.split(" (")[0] in cur)):
            nd = describe(row, drug, word, dcd) if row else (
                f"{drug}: {word} on {pretty(dcd)}. The decision record and its source are linked from this page.")
            esc = html.escape(nd, quote=True)
            for attr in ('name="description"', 'property="og:description"', 'name="twitter:description"'):
                doc = re.sub(r'(<meta ' + attr + r' content=")[^"]*(")', lambda m: m.group(1) + esc + m.group(2), doc, count=1)
            n_d += 1
        doc2 = strip_events(doc)
        if doc2 != doc:
            n_e += 1
            doc = doc2
        if doc != orig:
            n_pages += 1
            if not a.dry_run:
                io.open(p, "w", encoding="utf-8").write(doc)
    print(f"decided event pages: {n_pages} updated ({n_t} title(s), {n_d} description(s), {n_e} Event schema(s) removed)"
          + (" [dry run]" if a.dry_run else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
