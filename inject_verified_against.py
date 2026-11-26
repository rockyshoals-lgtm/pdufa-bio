# -*- coding: utf-8 -*-
"""inject_verified_against.py -- one "Verified against" line on every decision page (audit 2026-10-18, order 1).

Three dates, three sources, one sentence, placed right under the decision banner so it is the line an answer
engine lifts when it wants to be right about "October 15 or 16":

  Verified against: FDA action day October 14, 2026 (FDA approval notification) · Announcement October 14, 2026
  (ImmunityBio 8-K) · Goal date January 6, 2027 (ImmunityBio 8-K, August 4, 2026).

Each part states only what the row holds:
  * FDA action day: _d.fda_action_date with its record (_d.fda_action_record / fda_action_source_url). When the
    row's decision date is only an announcement (decision_date_unsourced, no fda_action_date): "FDA action day:
    not yet posted on Drugs@FDA".
  * Announcement: dcd with the announcing party and its URL (_d.announcement / announcement_url, else
    decision_source). A second dateline (_d.announcement_2, e.g. Roche's Basel release the day after Genentech's)
    is named too, so the reader sees why two dates circulate.
  * Goal date: the row's d with _d.source (and source_url); only when day-precision and not goal_unsourced,
    otherwise "Goal date: none sourced".
Marker-bounded (<!--VERIFIED:BEGIN-->...<!--VERIFIED:END-->), idempotent. Only /fda-decision/{T}-{dcd} pages that
a dataset row points at are written.

    python inject_verified_against.py [--dry-run]
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
SITE = os.path.join(HERE, "pdufa_site_src")
B, E = "<!--VERIFIED:BEGIN-->", "<!--VERIFIED:END-->"
MON = ["", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
       "November", "December"]


def pretty(iso):
    try:
        y, m, d = (int(x) for x in str(iso)[:10].split("-"))
        return f"{MON[m]} {d}, {y}"
    except Exception:  # noqa: BLE001
        return str(iso)


def esc(s):
    return html.escape(str(s or ""), quote=True)


def link(label, url):
    return f'<a href="{esc(url)}" rel="noopener" style="color:#e3ba5e">{esc(label)}</a>' if url else esc(label)


def short_source(s):
    """The source's name only; its date is stated once, before the parenthesis."""
    s = re.sub(r"\s*\(.*?\)\s*", " ", str(s or "")).strip()
    s = re.sub(r",?\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)"
               r" \d{1,2},? \d{4}.*$", "", s)
    s = re.sub(r",?\s+\d{4}-\d{2}-\d{2}.*$", "", s)
    s = re.sub(r"\s+filed$", "", s.strip(" ,"))   # 2026-11-17: "8-K filed" next to a release's own date read as the filing date
    return s.strip(" ,")[:70]


def line(r):
    d = r.get("_d") or {}
    parts = []
    fad = d.get("fda_action_date")
    if fad:
        rec = d.get("fda_action_record") or "FDA record"
        parts.append(f"FDA action day {pretty(fad)} ({link(short_source(rec), d.get('fda_action_source_url'))})")
    elif d.get("decision_date_unsourced"):
        parts.append("FDA action day not found in a public FDA record")   # 2026-11-17: was "not yet posted on Drugs@FDA", wrong for devices and CRLs
    dcd = r.get("dcd")
    if dcd:
        who = d.get("announcement") or d.get("decision_source") or "sponsor announcement"
        url = d.get("announcement_url") or d.get("decision_source_url")
        a = f"Announcement {pretty(dcd)} ({link(short_source(who), url)})"
        a2 = d.get("announcement_2") or {}
        if a2.get("date") and a2.get("who"):
            a += f"; also {link(esc(a2['who']), a2.get('url'))}, dated {pretty(a2['date'])}"
        parts.append(a)
    goal = r.get("d")
    if goal and str(r.get("dp") or "day") == "day" and not d.get("goal_unsourced") and (d.get("source") or d.get("source_url")):
        parts.append(f"Goal date {pretty(goal)} ({link(short_source(d.get('source') or 'sponsor filing'), d.get('source_url'))})")
    elif goal and str(r.get("dp") or "day") == "day" and not d.get("goal_unsourced"):
        parts.append(f"Goal date {pretty(goal)} (source not recorded on this row)")
    elif (goal and str(r.get("dp")) == "month" and not d.get("goal_unsourced") and (d.get("source") or d.get("source_url"))
          and d.get("source_url") not in (d.get("decision_source_url"), d.get("fda_action_source_url"))
          and not re.search(r"never sourced|not sourced|no .* states (?:it|a goal)", str(d.get("date_note") or ""), re.I)):
        # 2026-10-19 (Jemperli LARC): GSK stated the goal as "February 2027". A sourced month is a fact worth
        # naming; it is still not a day, so no margin is computed anywhere and this line says "month". A row
        # whose `source` is its own decision letter (HYRNUO: date_note "never sourced") does not qualify.
        y, m = (int(x) for x in str(goal)[:7].split("-"))
        parts.append(f"Goal month {MON[m]} {y}, no day stated ({link(short_source(d.get('source') or 'sponsor filing'), d.get('source_url'))})")
    else:
        parts.append("Goal date: none on record")
    return (f'{B}<p class="note" style="margin:6px 0 10px;font-size:12.5px;color:#a7bcd9">'
            f'<b style="color:#cfe0f5">Verified against:</b> ' + " &middot; ".join(parts) + f'.</p>{E}')


MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
FDAREC = re.compile(r'<!--FDAREC:BEGIN-->.*?<b>FDA record of the action:</b> the FDA [a-z ]+? on <b>((?:' + MONTHS +
                    r') \d{1,2}, \d{4})</b>, per <a href="([^"]+)"[^>]*>([^<]+)</a>', re.S)
CRLSRC = re.compile(r"<!--CRLSRC:BEGIN-->(.*?)<!--CRLSRC:END-->", re.S)
KV = r'<div class="kv"><span>{}</span><b>(.*?)</b></div>'
DAF = re.compile(r"Drugs@FDA, application (NDA|BLA|ANDA)\s?(\d+), action date (\d{4}-\d{2}-\d{2})")
LETTER = re.compile(r"FDA approval letter, ((?:NDA|BLA|ANDA) \d+(?: S-\d+)?), ((?:" + MONTHS + r") \d{1,2}, \d{4})")
FDA_ANN = re.compile(r"FDA announcement, ((?:" + MONTHS + r") \d{1,2}, \d{4})")
SEC = re.compile(r"SEC filing (\d{10}-\d{2}-\d{6}) of (\d{4}-\d{2}-\d{2})")
GENERIC = re.compile(r"^(?:View (?:filing|source|release)|Source|Link)\b", re.I)


def iso_long(text):
    import datetime as dt
    return dt.datetime.strptime(text, "%B %d, %Y").date().isoformat()


def _kv(doc, name):
    m = re.search(KV.format(re.escape(name)), doc, re.S)
    return html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip() if m else None


def _named(label, url):
    """A citation's own words, without its date (stated once, outside) or our bookkeeping in brackets."""
    t = html.unescape(re.sub(r"<[^>]+>", "", label)).strip()
    t = re.sub(r"\s*\((?:FDA notice|letter not yet on Drugs@FDA)\)", "", t)
    t = re.sub(r"\s+(?:of \d{4}-\d{2}-\d{2}|containing\b).*$", "", t)
    # a citation's own date is stated outside ("Novocure 8-K exhibit, February 11, 2026; ..."); a date the citation
    # is ABOUT stays (FBIO: "FDA approval letter for NDA 211241 (January 2026), citing the CRL of September 30, 2025"
    # lost its date and read "citing the CRL of").
    t = re.sub(r",\s+(?:" + MONTHS + r") \d{1,2},? \d{4}.*$", "", t).strip(" ,")
    if not t or GENERIC.match(t):
        host = re.sub(r"^https?://(?:www\.)?", "", url or "").split("/")[0]
        t = "SEC filing" if host.endswith("sec.gov") else ("FDA document" if host.endswith("fda.gov") else
                                                          "sponsor release")
    # FBIO's "... citing the CRL of September 30, 2025" ran past 80 characters and was cut to "September 3"
    return t if len(t) <= 110 else t[:110].rsplit(" ", 1)[0] + "\u2026"


NO_FDA = "No FDA record of the action day on this page"


def page_line(doc, day=None, slug=None):
    """2026-11-18 (design red team, change 10): the same line for a decision page no dataset row points at (417 of
    483), built only from the sources the page itself holds, and saying plainly when it holds none. day is the page's
    own day (its URL's); a Drugs@FDA validation date is called the FDA's day only when it is that day."""
    val = _kv(doc, "Validation") or ""
    ps = (re.search(r'<div class="kv"><span>Primary source</span><b>(.*?)</b></div>', doc, re.S)
          or re.search(r'>Primary source: (.*?)</p>', doc, re.S))
    cites = re.findall(r'<a href="(https?://[^"]+)"[^>]*>(.*?)</a>', ps.group(1), re.S) if ps else []
    # red team: CORT-2025-12-31 shows the FDA's own CRL card and ALVO-2025-11-02 an SEC filing, yet both were told
    # "not taken from an FDA record or a company filing". The inferred wording is for a page that cites nothing.
    if val.startswith("Outcome consistent with price") and not (FDAREC.search(doc) or CRLSRC.search(doc) or cites
                                                                or SEC.search(val)):
        return (f'{B}<p class="note" style="margin:6px 0 10px;font-size:12.5px;color:#a7bcd9"><b style="color:#cfe0f5">'
                "Verified against:</b> no primary source yet. The outcome shown is inferred from the stock&#x27;s price "
                f"move, not taken from an FDA record or a company filing.</p>{E}")
    parts = []
    rec, crl = FDAREC.search(doc), CRLSRC.search(doc)
    daf, letter, fann = DAF.search(val), LETTER.search(val), FDA_ANN.search(val)
    if rec:
        parts.append(f"FDA action day {rec.group(1)} ({link(_named(rec.group(3), rec.group(2)), html.unescape(rec.group(2)))})")
    elif crl:
        card = re.sub(r"<[^>]+>", "", crl.group(1))
        acted = (re.search(r"the FDA acted on ((?:" + MONTHS + r") \d{1,2}, \d{4})", card)
                 or re.search(r"dated ((?:" + MONTHS + r") \d{1,2}, \d{4})", card))
        url = re.search(r'href="([^"]+)"', crl.group(1))
        if acted:
            parts.append(f"FDA action day {acted.group(1)} ({link('the FDA&#x27;s Complete Response Letter', None) if not url else link('FDA Complete Response Letter', html.unescape(url.group(1)))})")
    elif daf:
        url = f"https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm?event=overview.process&ApplNo={daf.group(2)}"
        if day and daf.group(3) == day:
            parts.append(f"FDA action day {pretty(daf.group(3))} ({link(f'Drugs@FDA, {daf.group(1)} {daf.group(2)}', url)})")
        else:
            # The validation names the application and an action date on it, not which supplement. On 72 of 165 pages
            # that date is not the page's day: after it on 5 (AMRX-2025-01-23: Jan 28), or up to 10 days before
            # (MRK-2026-02-20, Keytruda BLA 125514: Feb 10), and a large application carries many actions. So the
            # application is cited, and its date is not called this decision's FDA day.
            # Red team: some of these dates are right (CSLLY-2025-06-17: BLA 761367 has one action, Jun 16) and some
            # are another supplement (JNJ-2025-03-20: Mar 25 is a manufacturing change; the new indication is Mar 20).
            # Say what the record lists, and that it is not matched to this decision.
            parts.append(f"FDA record: {link(f'{daf.group(1)} {daf.group(2)} on Drugs@FDA', url)}, which lists an "
                         f"action on {pretty(daf.group(3))}, not matched to this decision")
    elif letter:
        parts.append(f"FDA action day {letter.group(2)} (FDA approval letter, {esc(letter.group(1))})")
    elif fann:
        parts.append(f"FDA announcement {fann.group(1)}")
    # the page's primary source (read above): a key-facts row, or (older template) a "Primary source:" paragraph.
    # Red team: reading only the row, 14 pages that cite an FDA letter, an FDA press release or a sponsor release
    # were told "no source".
    fda_cites = [c for c in cites if re.search(r"//(?:www\.)?(?:accessdata\.)?fda\.gov/|open\.fda\.gov/", c[0])]
    other = [c for c in cites if c not in fda_cites]
    if not parts and fda_cites:
        u, lab = fda_cites[0]
        parts.append(f"FDA record: {link(_named(lab, html.unescape(u)), html.unescape(u))}")
    if not parts:
        # NVCR-2026-02-11 links the FDA's PMA record in its narrative, not in the primary-source line
        body = re.sub(r"<!--(DFAQ|F13|FIRSTREC|VERIFIED):BEGIN-->.*?<!--\1:END-->", "", doc, flags=re.S)
        own = re.search(r'<a href="(https://www\.accessdata\.fda\.gov/(?:scripts/cdrh/cfdocs/cfpma/pma\.cfm\?id=P\d+|'
                        r'drugsatfda_docs/appletter/[^"]+))"[^>]*>(.*?)</a>', body, re.S)
        if own:
            u = html.unescape(own.group(1))
            pma = re.search(r"pma\.cfm\?id=(P\d+)", u)
            parts.append("FDA record: " + link(f"FDA PMA record {pma.group(1)}" if pma else _named(own.group(2), u), u))
    if not parts:
        parts.append(NO_FDA)
    ann = _kv(doc, "Announced")
    src = None
    if other:
        src = ", ".join(link(_named(lab, html.unescape(u)), html.unescape(u)) for u, lab in other[:2])
        if not ann:
            # NVCR: "Novocure 8-K exhibit, February 11, 2026" carries the day key facts do not state
            dm = re.search(r",\s+((?:" + MONTHS + r") \d{1,2}, \d{4})", html.unescape(re.sub(r"<[^>]+>", "", other[0][1])))
            if dm:
                ann = iso_long(dm.group(1))
    elif SEC.search(val):
        sm = SEC.search(val)
        src = f"SEC filing {sm.group(1)}, filed {pretty(sm.group(2))}"
    elif val.startswith("Verified") and not (daf or letter or fann) and not (
            crl and "FDA Complete Response Letter" in val):
        # 2026-11-22 (CRL red team): a page verified against the FDA's own CRL already shows the FDA's day from the
        # letter card; the same letter is not the company's announcement, so it is not listed again as one.
        m = re.match(r"Verified \d{4}-\d{2}-\d{2}: (.+)$", val)
        if m:
            src = esc(_named(m.group(1), None))
    if ann and re.match(r"\d{4}-\d{2}-\d{2}", ann):
        note = ann[10:].strip(" ,;")
        parts.append(f"Announcement {pretty(ann[:10])}" + (f", {esc(note)}" if note and len(note) < 40 else "")
                     + (f" ({src})" if src else ""))
    elif src:
        parts.append(f"Announcement, date not stated on this page ({src})")
    if parts == [NO_FDA]:
        return (f'{B}<p class="note" style="margin:6px 0 10px;font-size:12.5px;color:#a7bcd9"><b style="color:#cfe0f5">'
                f"Verified against:</b> no source for this decision is cited on this page yet.</p>{E}")
    parts.append(census_goal(slug))
    return (f'{B}<p class="note" style="margin:6px 0 10px;font-size:12.5px;color:#a7bcd9">'
            f'<b style="color:#cfe0f5">Verified against:</b> ' + " &middot; ".join(parts) + f'.</p>{E}')


_GOALS = None


def census_goal(slug):
    """2026-11-26: a 2024-2025 page the decision-timing census matched (_decision_goal_dates.json, written by
    build_decision_timing_since_2024.py) names the goal date that census sourced, with the dated document that states
    it. Every other archive page still says it holds none."""
    global _GOALS
    if _GOALS is None:
        p = os.path.join(HERE, "_decision_goal_dates.json")
        _GOALS = json.load(io.open(p, encoding="utf-8")) if os.path.exists(p) else {}
    g = _GOALS.get(slug or "")
    if not (g and g.get("goal") and g.get("source_url") and g.get("doc_date")):
        return "Goal date: none on record"
    u = g["source_url"]
    who = "SEC filing" if "sec.gov/" in u else "sponsor document"
    s = f"Goal date {pretty(g['goal'])}"
    if g.get("extended") and g.get("goal_original"):
        s += f", extended from {pretty(g['goal_original'])}"
    label = who + ", " + pretty(g["doc_date"])
    return s + f" ({link(label, u)})"


def place(doc, block):
    """Under the banner and its fact-first lede; on the older template (no banner), under the page's freshness line."""
    doc0 = re.sub(re.escape(B) + ".*?" + re.escape(E) + r"\s*", "", doc, flags=re.S)
    m = re.search(r'<div class="ban (?:ap|cr|wd)[^"]*">.*?</div>\s*(?:<!--FACTLEDE:BEGIN-->.*?<!--FACTLEDE:END-->)?', doc0, re.S)
    if not m:
        m = re.search(r"<!--FRESH:END-->", doc0) or re.search(r"</h1>", doc0)
    if not m:
        return None
    return doc0[:m.end()] + block + doc0[m.end():]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    src = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8", errors="replace").read()
    rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    n = changed = 0
    for r in rows:
        if r.get("type") != "PDUFA" or str(r.get("st")) != "Decided" or not r.get("dcd"):
            continue
        slug = f"{str(r.get('t') or '').upper()}-{str(r['dcd'])[:10]}"
        p = os.path.join(SITE, "fda-decision", slug, "index.html")
        if not os.path.exists(p):
            continue
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        block = line(r)
        # strip any earlier placement, then insert after the fact-first lede when one is present (the lede must sit
        # directly under the banner for test_decision_lede_fact_first), else directly after the banner.
        doc0 = re.sub(re.escape(B) + ".*?" + re.escape(E) + r"\s*", "", doc, flags=re.S)   # 2026-10-24: and the whitespace after it (newlines were accumulating, one per run, against build_decision_lede)
        m = re.search(r'<div class="ban (?:ap|cr|wd)[^"]*">.*?</div>\s*(?:<!--FACTLEDE:BEGIN-->.*?<!--FACTLEDE:END-->)?', doc0, re.S)
        if not m:
            continue
        new = doc0[:m.end()] + block + doc0[m.end():]
        n += 1
        if new != doc:
            changed += 1
            if not a.dry_run:
                io.open(p, "w", encoding="utf-8").write(new)
    # every other decision page: the line from the page's own sources
    import glob
    owned = {f"{str(r.get('t') or '').upper()}-{str(r['dcd'])[:10]}" for r in rows
             if r.get("type") == "PDUFA" and str(r.get("st")) == "Decided" and r.get("dcd")}
    m2 = 0
    for p in sorted(glob.glob(os.path.join(SITE, "fda-decision", "*", "index.html"))):
        slug = os.path.basename(os.path.dirname(p))
        if slug in owned and B in io.open(p, encoding="utf-8", errors="replace").read():
            continue
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        new = place(doc, page_line(doc, slug[-10:], slug))
        if new is None:
            continue
        m2 += 1
        if new != doc:
            changed += 1
            if not a.dry_run:
                io.open(p, "w", encoding="utf-8").write(new)
    print(f"verified-against line: {n} decision page(s) carry it from the dataset, {m2} from their own sources, "
          f"{changed} written" + (" [dry run]" if a.dry_run else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
