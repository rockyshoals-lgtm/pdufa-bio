# -*- coding: utf-8 -*-
"""mark_event_pages_decided.py -- a per-event PDUFA page must not present a decided
event as pending.

THE GAP (re-audit 2026-09-01b, root cause #2): build_pdufa_event_pages deliberately never
overwrites existing pages -- they carry hand-grown story cards a rebuild would flatten --
so nothing ever told /pdufa/REGN-garetosmab that garetosmab had been APPROVED. The page
sat 25 days stale saying "target 2026-08-31" on a query converting at 33% CTR at position
2, and its dateModified argued against its own freshness. Same for LNTH-florquinitau and
every other decided event's page.

This injector completes the write-once design instead of fighting it: when a page's event
is Decided in the dataset, a marker-based outcome banner (DECBAN) goes in right after the
freshness stamp, linking the decision page that carries the source. Idempotent; re-runs
update the banner in place; nothing else on the page is touched, so the hand-grown
content survives. Runs daily in CI after refresh_moved_pdufa_pages -- moves handled
there, outcomes here, and build_date_modified then stamps the real change honestly.

Matching is conservative, single-candidate-or-skip, same discipline as
refresh_moved_pdufa_pages: slug ticker must match, slug drug tokens (if any) must
intersect the event name, and multiple candidates mean a skip with a loud line.
"""
import datetime as dt
import glob
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
B, E = "<!--DECBAN:BEGIN-->", "<!--DECBAN:END-->"
MON = ["", "January", "February", "March", "April", "May", "June", "July", "August",
       "September", "October", "November", "December"]


def pretty(iso):
    try:
        d = dt.date.fromisoformat(str(iso)[:10])
        return f"{MON[d.month]} {d.day}, {d.year}"
    except Exception:
        return str(iso or "")


def toks(s):
    return set(re.findall(r"[a-z0-9]{4,}", str(s or "").lower()))


# Audit 2026-09-05 (0800 slot) P0-1: /pdufa/AZN-camizestrant said "under FDA review, target
# 2026-12-31" two days after the FDA approved camizestrant, while /fda-decision/AZN-2026-09-04
# and /drug/camizestrant both said approved. ROOT CAUSE: this injector read ONLY dataset rows
# with st=Decided. Camizestrant never had a dataset PDUFA row (its goal date was extended and
# never re-disclosed, so the slug page and the calendar's "Q4 2026 (est.)" row were the only
# places it existed) -- so the one surface that knew (the decisions ARCHIVE, where the
# drug-page watcher published the approval) was never consulted. The fallback below reads the
# archive for any slug page the dataset cannot resolve. Archive decisions carry no goal date,
# so pages resolved this way drop their estimated target date instead of comparing against it.
ARCHIVE_EARLY_WINDOW = 180      # same bound as mark_calendar_decided.EARLY_WINDOW, same reason


def load_archive():
    """ticker -> [(decision_date, 'ap'|'crl', drug_text)] from /decisions (the published,
    sourced decision pages). Same parse as mark_calendar_decided.load_decisions."""
    try:
        html = io.open(os.path.join(SITE, "decisions", "index.html"), encoding="utf-8",
                       errors="replace").read()
    except OSError:
        return {}
    by_tk, seen = {}, set()
    for m in re.finditer(r'href="/fda-decision/([A-Z]{1,6})-(\d{4}-\d{2}-\d{2})"', html):
        tk, date = m.group(1), m.group(2)
        if (tk, date) in seen:
            continue
        seen.add((tk, date))
        seg = html[m.end():m.end() + 400].split("</a>", 1)[0]
        low = seg.lower()
        outcome = "crl" if ("crl" in low or "complete response" in low) else "ap"
        drug = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", seg))
        drug = re.split(r"(?:Approved|CRL)\s*:?\s*", drug, maxsplit=1)[-1].strip()
        by_tk.setdefault(tk, []).append((date, outcome, drug[:90]))
    return by_tk


def archive_candidates(archive, tk, drug_part, doc0):
    """Decisions in the archive that name this slug's drug, dated on or before today and no
    earlier than ARCHIVE_EARLY_WINDOW days before the page's stated target (if it states one).
    Name overlap is REQUIRED here (there is no goal date to anchor on), and CRLs never carry
    forward onto a page that still shows a later target -- a CRL is why a later date exists."""
    if not drug_part:
        return []
    dtoks = toks(drug_part)
    tm = re.search(r"<title[^>]*>[A-Z]{1,6} PDUFA date:\s*(.+?),\s*[A-Z][a-z]{2}", doc0)
    ttoks = toks(tm.group(1)) if tm else set()
    gm = re.search(r'<div class="kv"><span>FDA PDUFA target date</span><b>(\d{4}-\d{2}-\d{2})</b>',
                   doc0)
    goal = dt.date.fromisoformat(gm.group(1)) if gm else None
    today = dt.date.today()
    out = []
    for date, outcome, drug in archive.get(tk, []):
        dd = dt.date.fromisoformat(date)
        if dd > today or outcome == "crl":
            continue
        if goal is not None and not (-ARCHIVE_EARLY_WINDOW <= (dd - goal).days <= 14):
            continue
        if not ((dtoks | ttoks) & toks(drug)):
            continue
        out.append({"t": tk, "name": drug, "oc": "Approved", "dcd": date, "d": None,
                    "_archive": True})
    return out


def decided_language(doc, tk, drug, word, dcd, goal, archive_only):
    """Rewrite the machine-written PENDING phrasing on an event page whose event has decided.

    The banner alone left every decided page still saying "is under FDA review", "FDA PDUFA
    target date", and answering "When is the PDUFA date?" with a target the FDA had already
    acted on (24 pages on 2026-09-06, the AZN-camizestrant P0 among them). Every phrase
    rewritten here is a template phrase build_pdufa_event_pages writes; hand-grown story
    text is not touched. A page resolved from the ARCHIVE has no disclosed goal date, so its
    estimated target is removed rather than restated."""
    P = pretty(dcd)
    ok = word == "Approved"
    verb_story = (f"was approved by the FDA on {P} to treat" if ok else
                  f"received a Complete Response Letter from the FDA on {P} for")
    verb_faq = (f"drug, approved by the FDA on {P} for" if ok else
                f"candidate that received a Complete Response Letter from the FDA on {P} for")
    goal_kv = (f'<div class="kv"><span>FDA goal date</span><b>{goal}</b></div>'
               if goal and not archive_only else "")
    goal_sent = (f" The FDA goal date for this application was {goal}." if goal and not archive_only
                 else " pdufa.bio does not hold a sponsor-disclosed goal date for this application.")

    # 1. story line
    doc = doc.replace(" is under FDA review to treat", f" {verb_story}")
    doc = doc.replace(" is under FDA review for", f" {verb_story.replace(' to treat', ' for')}")
    # 2. sub line under the h1
    doc = re.sub(r'<div class="sub">FDA decision \(PDUFA\) target <b>[^<]{6,24}</b>',
                 f'<div class="sub">FDA decision <b>{_html.escape(word)} {P}</b>', doc)
    # 3. key facts
    doc = re.sub(r'<div class="kv"><span>FDA PDUFA target date</span><b>\d{4}-\d{2}-\d{2}</b></div>',
                 f'<div class="kv"><span>FDA decision</span><b>{_html.escape(word)} {P}</b></div>'
                 + goal_kv, doc)
    # 4. FAQ question + answer (HTML and JSON-LD carry the same strings)
    doc = doc.replace(f"When is the {tk} PDUFA date?", f"What did the FDA decide on {tk}'s {drug}?")
    # company names nest parentheses (Takeda's ADS description) and drug names carry
    # "vs." -- both sides are lazy, anchored on the fixed template words around them
    doc = re.sub(r"The FDA PDUFA target date for " + re.escape(tk) + r" \((.*?)\) is \d{4}-\d{2}-\d{2} "
                 r"for (.*?)\. Dates are company/FDA-sourced and can slip\. Verify against primary filings\.",
                 lambda m: (f"The FDA decided {tk}'s ({m.group(1)}) application for {m.group(2)} on "
                            f"{P}: {word}.{goal_sent} Verify against the linked primary source."),
                 doc)
    doc = doc.replace("candidate under FDA review for", verb_faq)
    doc = doc.replace("candidate under FDA review", verb_faq[: -len(" for")])
    # 5. Event schema: the decision, not the target
    doc = doc.replace('"description":"' + _html.escape(drug) + ' FDA decision: FDA PDUFA target decision date. Facts only, not advice."',
                      '"description":"' + _html.escape(drug) + f' FDA decision: {word} on {P}. Facts only, not advice."')
    doc = re.sub(r'"startDate":"\d{4}-\d{2}-\d{2}","endDate":"\d{4}-\d{2}-\d{2}"',
                 f'"startDate":"{dcd}","endDate":"{dcd}"', doc)
    # 6. title / og:title / WebPage name / descriptions (one string, several carriers)
    tm = re.search(r"<title>([A-Z]{1,6} PDUFA date: (.+?), ([A-Z][a-z]{2} \d{1,2},? \d{4})) \| pdufa\.bio</title>", doc)
    if tm:
        old_title, tdrug = tm.group(1), tm.group(2)
        new_title = f"{tk} FDA decision: {tdrug}, {word} {P}"
        doc = doc.replace(old_title, new_title)
        doc = re.sub(r"(&#x27;s|'s) FDA PDUFA date is [A-Z][a-z]{2} \d{1,2},? \d{4} for " + re.escape(tdrug),
                     rf"\1 {tdrug} was {'approved by the FDA' if ok else 'issued a Complete Response Letter by the FDA'} on {P}", doc)
    return doc


def main():
    src = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8",
                  errors="replace").read().replace("\x00", "")
    rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    decided = [r for r in rows if r.get("type") == "PDUFA"
               and str(r.get("st", "")).lower() == "decided" and r.get("dcd")]
    archive = load_archive()

    changed = skipped = 0
    for p in sorted(glob.glob(os.path.join(SITE, "pdufa", "*", "index.html"))):
        slug = os.path.basename(os.path.dirname(p))
        m = re.match(r"([A-Z]{1,6})(?:-(.+))?$", slug)
        if not m:
            continue
        tk, drug_part = m.group(1), (m.group(2) or "").replace("-", " ")
        tk_cands = [r for r in decided if str(r.get("t", "")).upper() == tk]
        if not tk_cands and tk not in archive:
            continue
        doc0 = io.open(p, encoding="utf-8", errors="replace").read()
        # Already bannered: the page has named its decision. Re-validate THAT decision only
        # (dataset first, archive second) so a re-run is idempotent -- the rewrites below
        # change the title and remove the target-date fact the first-pass matching reads.
        bm = re.search(re.escape(B) + r'.*?href="/fda-decision/' + tk + r'-(\d{4}-\d{2}-\d{2})"',
                       doc0, re.S)
        if bm:
            want = bm.group(1)
            cands = [r for r in tk_cands if str(r.get("dcd")) == want]
            if not cands:
                cands = [{"t": tk, "name": g, "oc": "Approved" if o == "ap" else "CRL",
                          "dcd": d, "d": None, "_archive": True}
                         for d, o, g in archive.get(tk, []) if d == want]
            if not cands:
                continue
        elif drug_part:
            dtoks = toks(drug_part)
            cands = [r for r in tk_cands if dtoks & toks(r.get("name"))]
            if not cands:
                # Alias gap: slug carries the generic (florquinitau), the dataset the
                # code name (MK-6240). The page TITLE is machine-written from the
                # dataset name at creation, so match event-name tokens against it.
                tm = re.search(r"<title[^>]*>[A-Z]{1,6} PDUFA date:\s*(.+?),"
                               r"\s*[A-Z][a-z]{2}", doc0)
                ttoks = toks(tm.group(1)) if tm else set()
                cands = [r for r in tk_cands if ttoks & toks(r.get("name"))]
            if not cands:
                # Archive fallback (2026-09-06): the dataset never held this event.
                cands = archive_candidates(archive, tk, drug_part, doc0)
                if cands and len(cands) == 1:
                    print(f"  /pdufa/{slug}: no dataset row; resolved from the decisions "
                          f"archive ({cands[0]['dcd']})")
        else:
            # Bare-ticker event pages (re-audit 2026-09-02: /pdufa/JAZZ said "target
            # 2026-08-25" for a drug approved ON that date, 8 days on). These carry the
            # same machine-written title plus an explicit target date, so the match is
            # DOUBLE-anchored: the event's goal date must equal the page's stated
            # target AND the title drug tokens must intersect the event name.
            gm = re.search(r"target date for [A-Z]{1,6} [^<]{0,200}?is (\d{4}-\d{2}-\d{2})",
                           doc0)
            tm = re.search(r"<title[^>]*>[A-Z]{1,6} PDUFA(?: date)?:\s*(.+?)(?:,\s*[A-Z][a-z]{2}| \|)",
                           doc0)
            if not (gm and tm):
                continue
            ttoks = toks(tm.group(1))
            cands = [r for r in tk_cands if str(r.get("d"))[:10] == gm.group(1)
                     and ttoks & toks(r.get("name"))]
        if not cands:
            continue
        if len(cands) > 1:
            print(f"  SKIP /pdufa/{slug}: {len(cands)} decided events match; a wrong "
                  f"banner is worse than none -- resolve by hand")
            skipped += 1
            continue
        r = cands[0]
        oc = str(r.get("oc") or "Decided")
        archive_only = bool(r.get("_archive"))
        dcd, goal = str(r.get("dcd")), (str(r.get("d")) if r.get("d") else "")
        try:
            delta = (dt.date.fromisoformat(dcd) - dt.date.fromisoformat(goal)).days
        except Exception:
            delta = None
        timing = ("" if delta is None else
                  " on its goal date" if delta == 0 else
                  f", {-delta} days before its {pretty(goal)} goal date" if delta < 0 else
                  f", {delta} days after its {pretty(goal)} goal date")
        ok = oc == "Approved"
        col = "#46d17f" if ok else "#ff8f6b"
        word = "Approved" if ok else ("Complete Response Letter" if oc == "CRL" else oc)
        dec_url = f"/fda-decision/{tk}-{dcd}"
        has_dec_page = os.path.exists(os.path.join(SITE, "fda-decision", f"{tk}-{dcd}",
                                                   "index.html"))
        link = (f' <a href="{dec_url}" style="color:#9ec5ff">Decision page with the '
                f'source and measured reaction</a>.' if has_dec_page else "")
        banner = (f'{B}<div style="background:#0c1d38;border:1px solid {col};'
                  f'border-radius:10px;padding:11px 14px;margin:10px 0 14px;'
                  f'font-size:14.5px"><b style="color:{col}">{"&#10003;" if ok else "&#10007;"} '
                  f'{_html.escape(word)}</b> &middot; the FDA decided this application on '
                  f'<b>{pretty(dcd)}</b>{_html.escape(timing)}.{link}</div>{E}')

        doc = io.open(p, encoding="utf-8", errors="replace").read()
        if B in doc:
            new = doc.split(B, 1)[0] + banner + doc.split(E, 1)[1]
        else:
            anchor = "<!--FRESH:END-->" if "<!--FRESH:END-->" in doc else "</h1>"
            if anchor not in doc:
                print(f"  SKIP /pdufa/{slug}: no insertion anchor")
                skipped += 1
                continue
            i = doc.index(anchor) + len(anchor)
            new = doc[:i] + banner + doc[i:]
        # The pending template phrasing must go with the banner, every run (idempotent:
        # each rewrite matches only the pending form). Drug name for the FAQ question comes
        # from the h1's highlighted span, which is what the page itself calls the drug.
        hm = re.search(r'<h1>[A-Z]{1,6} PDUFA Date: <span class="g">(.+?)</span></h1>', new)
        page_drug = _html.unescape(hm.group(1)) if hm else str(r.get("name") or "")
        new = decided_language(new, tk, page_drug, word, dcd, goal, archive_only)
        if new != doc:
            io.open(p, "w", encoding="utf-8").write(new)
            changed += 1
            print(f"  /pdufa/{slug}: {word} {dcd}{timing}")
    print(f"decided banners: {changed} page(s) updated, {skipped} skipped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
