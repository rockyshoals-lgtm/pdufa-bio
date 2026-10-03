# -*- coding: utf-8 -*-
"""build_decision_lede.py -- the first sentence of every Approved decision page is the fact (audit 2026-10-03).

2.1  The answer box on a new approval goes to whoever publishes one clean, FDA-dated sentence first
     (trialfriend.com took Atebrioz, breakoutbiotechstocks.com took JUVMO). The 09-27 rule fixed the
     <title>/<meta> of FDA-notice pages; the VISIBLE first sentence of 126 approved pages still opened
     "AbbVie Inc., LINZESS (Iinaclotide) · functional constipation (FC) in patients 2 to 5 ye." This
     writes one sentence directly under the APPROVED banner, between markers, every run:
       FDA-dated     "{Drug} was approved by the FDA on {FDA date} for {indication}."
       FDA notice    "On {date}, the FDA announced its approval of {Drug} for {indication}."
       otherwise     "{Drug} was approved by the FDA for {indication}; the approval was announced on {date}."
     The FDA date comes only from an FDA record: the API row's fda_action_date (Drugs@FDA / letter /
     notice), the FDA's Novel Drug Approvals list, or _fda_action_archive.json (Drugs@FDA, unambiguous).
2.2  On a new molecular entity: ", the Nth novel drug approval of 2026 on the FDA's Novel Drug Approvals
     list" with the link, N read from that list (_fda_novel_approvals.json), never counted by us.
4.7  Names and indications go through drug_names.py: a name cut by the archive feed is shortened to
     its last complete unit, a cut indication is dropped, never guessed. The old " · " headline under
     the lede is rewritten with the same cleaned strings.
3.2  Pages without an FDA-record block get a one-line link to /fda-approval-letters by the source.

Facts only; no odds, no margin here (the margin, where allowed, stays in the body). Idempotent.
    python build_decision_lede.py [--dry-run]
"""
import argparse
import datetime as dt
import glob
import html
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from drug_names import clean_company, clean_drug_name, clean_indication, lower_first  # noqa: E402

SITE = os.path.join(HERE, "pdufa_site_src")
B, E = "<!--FACTLEDE:BEGIN-->", "<!--FACTLEDE:END-->"
OLD_B, OLD_E = "<!--LEDE:BEGIN-->", "<!--LEDE:END-->"   # first marker (10-03), collided with the hub-lede guard
LB, LE = "<!--LETTERSLINK:BEGIN-->", "<!--LETTERSLINK:END-->"
MON = ["", "January", "February", "March", "April", "May", "June", "July", "August", "September",
       "October", "November", "December"]
NOVEL_URL = "https://www.fda.gov/drugs/novel-drug-approvals-fda/novel-drug-approvals-2026"


def pretty(iso):
    d = dt.date.fromisoformat(iso)
    return f"{MON[d.month]} {d.day}, {d.year}"


def ordinal(n):
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def load_json(name, default):
    p = os.path.join(HERE, name)
    return json.load(io.open(p, encoding="utf-8")) if os.path.exists(p) else default


def novel_match(name, day, novel):
    """The FDA list row for this page's drug: brand or ingredient token, list date 0-10 days before."""
    toks = {t.lower() for t in re.findall(r"[A-Za-z][A-Za-z-]{4,}", clean_drug_name(name))}
    pd_ = dt.date.fromisoformat(day)
    for r in novel:
        keys = {r["brand"].lower()} | {w.lower() for w in re.findall(r"[A-Za-z][A-Za-z-]{4,}", r["ingredient"])}
        if toks & keys and 0 <= (pd_ - dt.date.fromisoformat(r["date"])).days <= 10:
            return r
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    src = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8", errors="replace").read()
    rows = json.loads(src[src.index("["):src.rindex("]") + 1].replace("\x00", ""))
    byslug = {f"{str(r.get('t') or '').upper()}-{r.get('dcd')}": r for r in rows
              if r.get("type") == "PDUFA" and r.get("st") == "Decided" and r.get("dcd")}
    arch = load_json("_fda_action_archive.json", {})
    novel = load_json("_fda_novel_approvals.json", {}).get("rows", [])
    stats = {"fda_dated": 0, "fda_notice": 0, "announced": 0, "novel": 0, "headline_cleaned": 0, "skipped": 0}
    changed = 0
    for p in sorted(glob.glob(os.path.join(SITE, "fda-decision", "*", "index.html"))):
        slug = os.path.basename(os.path.dirname(p))
        m = re.match(r"([A-Z]{1,6})-(\d{4}-\d{2}-\d{2})$", slug)
        if not m:
            continue
        tk, day = m.group(1), m.group(2)
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        doc = re.sub(re.escape(OLD_B) + r".*?" + re.escape(OLD_E) + r"\s*", "", doc, flags=re.S)   # marker migration
        low = doc.lower()
        _orig = io.open(p, encoding="utf-8", errors="replace").read()
        if doc != _orig and not a.dry_run:
            io.open(p, "w", encoding="utf-8", newline="").write(doc)
        if 'class="ban cr"' in doc:
            # CRL pages get no lede here, but their headline may carry a cut archive name (4.7)
            cm_ = re.search(r'(<div class="ban cr">[^<]*</div>\s*<p class="sub">)(.*?)(</p>)', doc, re.S)
            if cm_ and " · " in html.unescape(cm_.group(2)):
                h_ = html.unescape(cm_.group(2))
                a_, b_ = h_.split(" · ", 1)
                od = re.split(r"[:,] ", a_, 1)[-1]
                comp = clean_company(a_[: len(a_) - len(od)].rstrip(":, "))
                ci = clean_indication(b_.rstrip("."))
                rebuilt = f"{comp}, {clean_drug_name(od)}" + (f" · {ci}." if ci else ".")
                if rebuilt != h_:
                    new = doc[:cm_.start(2)] + html.escape(rebuilt, quote=False) + doc[cm_.end(2):]
                    stats["headline_cleaned"] += 1
                    changed += 1
                    if not a.dry_run:
                        io.open(p, "w", encoding="utf-8", newline="").write(new)
            stats["skipped"] += 1
            continue
        if 'class="ban ap"' not in doc or "price-only" in low or "outcome unverified" in low:
            stats["skipped"] += 1
            continue
        r = byslug.get(slug) or {}
        d = r.get("_d") or {}
        kv = re.search(r"<span>Drug / candidate</span><b>(.*?)</b>", doc)
        kvi = re.search(r"<span>Indication</span><b>(.*?)</b>", doc)
        hm = re.search(r'(<div class="ban ap">[^<]*</div>\s*(?:' + re.escape(B) + r'.*?' + re.escape(E) + r'\s*)?)'
                       r'<p class="sub">(.*?)</p>', doc, re.S)
        if not hm:
            stats["skipped"] += 1
            continue
        head = html.unescape(hm.group(2))
        old_drug = old_ind = None
        if " · " in head:
            a_, b_ = head.split(" · ", 1)
            old_drug = re.split(r"[:,] ", a_, 1)[-1]
            old_ind = b_.rstrip(".")
        else:
            cm = re.match(r"^([^:]{3,80}): ([^:]{3,80})\.$", head)
            if cm and (cm.group(1).count("(") != cm.group(1).count(")") or
                       cm.group(2).count("(") != cm.group(2).count(")") or re.search(r"\s[A-Z]$", cm.group(1))):
                head = f"{cm.group(1)}, {cm.group(2)} · ."
                old_drug, old_ind = cm.group(2), ""
        raw_name = r.get("name") or (html.unescape(kv.group(1)) if kv else "") or old_drug or ""
        name = clean_drug_name(raw_name)
        if d.get("brand") and d["brand"].lower() not in name.lower():
            name = f"{d['brand']} ({name})"
        if not name:
            stats["skipped"] += 1
            continue
        nv = novel_match(raw_name, day, novel)
        # indication: dataset short form > FDA's own approved-use text > cleaned stored text
        ind = d.get("indication_short") or clean_indication(d.get("indication"))
        use = None
        if not ind and nv and nv.get("use"):
            use = re.sub(r"^To\s+", "to ", nv["use"].rstrip("."))
        if not ind and not use:
            ind = clean_indication(html.unescape(kvi.group(1)) if kvi else old_ind)
        what = (f" {use}" if use else f" for {lower_first(ind)}" if ind else "")
        # the FDA's date, only from an FDA record
        fad = d.get("fda_action_date") or (arch.get(slug) or {}).get("date") or (nv or {}).get("date")
        notice_only = bool(d.get("decision_date_unsourced")) and re.match(
            r"https://(www\.)?fda\.gov/", str(d.get("decision_source_url") or ""))
        nv_txt = ""
        if nv:
            nv_txt = (f', the {ordinal(nv["n"])} novel drug approval of 2026 on the FDA\'s '
                      f'<a href="{NOVEL_URL}" rel="noopener" style="color:#e3ba5e">Novel Drug Approvals</a> list')
            stats["novel"] += 1
        en = html.escape(name, quote=False)
        if fad and not notice_only:
            sent = f"{en} was approved by the FDA on {pretty(fad)}{html.escape(what, quote=False)}{nv_txt}."
            stats["fda_dated"] += 1
        elif notice_only:
            sent = f"On {pretty(day)}, the FDA announced its approval of {en}{html.escape(what, quote=False)}{nv_txt}."
            stats["fda_notice"] += 1
        else:
            sent = (f"{en} was approved by the FDA{html.escape(what, quote=False)}{nv_txt}; "
                    f"the approval was announced on {pretty(day)}.")
            stats["announced"] += 1
        block = (f'{B}<p class="sub fact" style="font-size:17px;color:#eef4fc;line-height:1.5">'
                 f'{sent}</p>{E}\n')
        # the headline below: drop a leading sentence the lede now states; clean cut fragments
        newhead = hm.group(2)
        lead = re.match(r"^\s*[^.]{3,160}? was approved by the FDA on [A-Z][a-z]+ \d{1,2}, \d{4}.*?\.\s+(.+)$",
                        html.unescape(newhead), re.S)
        if lead:
            newhead = html.escape(lead.group(1), quote=False)
        elif old_drug is not None:
            a_ = head.split(" · ", 1)[0]
            comp = clean_company(a_[: len(a_) - len(old_drug)].rstrip(":, "))
            ci = clean_indication(old_ind)
            cd = clean_drug_name(old_drug)
            rebuilt = f"{comp}, {cd}" + (f" · {ci}." if ci else ".")
            if rebuilt != head:
                newhead = html.escape(rebuilt, quote=False)
                stats["headline_cleaned"] += 1
        new = doc[:hm.start()] + re.sub(re.escape(B) + r".*?" + re.escape(E) + r"\s*", "", hm.group(1), flags=re.S) \
            + block + f'<p class="sub">{newhead}</p>' + doc[hm.end():]
        if new != doc:
            changed += 1
            if not a.dry_run:
                io.open(p, "w", encoding="utf-8", newline="").write(new)
    # 3.2 (audit 2026-10-03): every decision page, approved or CRL, links the letters hub by its source;
    # pages whose FDA-record block already links it need nothing more.
    nlink = 0
    for p in sorted(glob.glob(os.path.join(SITE, "fda-decision", "*", "index.html"))):
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        new = re.sub(re.escape(LB) + r".*?" + re.escape(LE), "", doc, flags=re.S)
        if "/fda-approval-letters" not in new:
            link = (f'{LB}<p class="sub" style="font-size:13px">Every FDA approval letter and released Complete '
                    f'Response Letter we hold, by FDA action date: <a href="/fda-approval-letters" '
                    f'style="color:#e3ba5e">FDA approval letters</a>.</p>{LE}')
            i = next((new.index(x) for x in ('<!--DFAQ:BEGIN-->', '<div class="legal"', "<footer") if x in new), None)
            if i is not None:
                new = new[:i] + link + new[i:]
        if new != doc:
            nlink += 1
            if not a.dry_run:
                io.open(p, "w", encoding="utf-8", newline="").write(new)
    lp = os.path.join(SITE, "decisions", "index.html")
    if os.path.exists(lp):
        doc = io.open(lp, encoding="utf-8", errors="replace").read()
        new = re.sub(re.escape(LB) + r".*?" + re.escape(LE), "", doc, flags=re.S)
        blk = (f'{LB}<p class="sub" style="font-size:14px">Each decision is dated by the FDA&#x27;s own record where '
               f'we hold it: <a href="/fda-approval-letters" style="color:#e3ba5e">every FDA approval letter, by FDA '
               f'action date</a>.</p>{LE}')
        j = new.find("<!--FRESH:END-->")
        if j > 0:
            new = new[:j + len("<!--FRESH:END-->")] + blk + new[j + len("<!--FRESH:END-->"):]
            if new != doc and not a.dry_run:
                io.open(lp, "w", encoding="utf-8", newline="").write(new)
    print(f"letters-hub links: {nlink} decision page(s) linked; /decisions linked")
    print(f"decision ledes: {changed} page(s) {'would change' if a.dry_run else 'updated'}; "
          + ", ".join(f"{k} {v}" for k, v in stats.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
