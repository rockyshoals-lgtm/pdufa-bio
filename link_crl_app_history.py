# -*- coding: utf-8 -*-
"""link_crl_app_history.py -- each decision page lists the other FDA actions on its own application number.

2026-11-25 (David: "mine for more ... past CRLs ... red team everything, check for currency"). A CRL decision page and
the later approval of the same application did not know about each other: /fda-decision/AZN-2026-04-27 (Saphnelo
for subcutaneous use, BLA 761451, approved April 24, 2026) never said the FDA had sent a Complete Response Letter on
that BLA on October 10, 2025, and /fda-decision/TEVA-2026-03-30 (Ponlimsi, BLA 761385) never said the FDA's July 30,
2025 letter existed. Both facts sit in FDA files this site already reads.

For every /fda-decision page whose own FDA record names an application number (the FDA letter its "FDA record of the
action" line or its FDA-letter card links), this writes one block, <!--APPHIST:BEGIN--> ... <!--APPHIST:END-->, after
that line, listing in date order:

  * every Complete Response Letter on that application number in the FDA's CRL release (rescinded letters left out),
    with its date (and, for a corrected letter, the action date the letter says stands), the PDF, its /crl/letter page
    and the decision page that cites it, where one does;
  * every approval Drugs@FDA lists on that application number since January 1, 2025 (originals and efficacy
    supplements, from _fda_approvals_months.json), with the FDA's letter and the decision page that cites it;
  * the page's own action, marked "this page".

A block is written only where the application has at least one released CRL and at least one action besides the
page's own. A page whose record names no application, or names one with no released CRL, gets no block (and any old
block is removed). Matching is by the six-digit application number, which the FDA does not reuse between NDAs and
BLAs. Facts only: dates, record names and links. No reading of why, no rate, no view on any application.

    python link_crl_app_history.py          (tests/test_crl_app_history.py checks every block against the files)
"""
import datetime as dt
import glob
import html
import io
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
sys.path.insert(0, HERE)
B, E = "<!--APPHIST:BEGIN-->", "<!--APPHIST:END-->"
APPR = os.path.join(HERE, "_fda_approvals_months.json")
MON = ["", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
       "November", "December"]
LINK = 'style="color:#e3ba5e"'


def pretty(d):
    d = dt.date.fromisoformat(d) if isinstance(d, str) else d
    return f"{MON[d.month]} {d.day}, {d.year}"


def esc(s):
    return html.escape(str(s or ""), quote=True)


def letters():
    """[{num, label, date, action, pdf, file, slug}] for every released CRL (rescinded left out)."""
    from build_feeds import crl_letters
    from build_crl_letters import corrected_action, slugs
    Ls = crl_letters(include_rescinded=False)[0]
    sl = slugs(crl_letters(include_rescinded=True)[0])
    out = []
    for L in Ls:
        ca = corrected_action(L)
        act = dt.datetime.strptime(ca, "%B %d, %Y").date() if ca else L["date"]
        for kind, num, sfx in L.get("apps") or []:
            sfx = re.sub(r"^[\s/]+", "", str(sfx or "")).strip()
            out.append({"num": f"{int(num):06d}", "label": f"{kind} {int(num):06d}" + (f"/{sfx}" if sfx else ""),
                        "date": L["date"], "action": act, "pdf": L["url"], "file": L["file"],
                        "slug": sl.get(L["key"]), "corrected": bool(ca)})
    return out


def approvals():
    """[{num, label, date, letter}] from the Drugs@FDA month cache (every approval since January 2025)."""
    try:
        cache = json.load(io.open(APPR, encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return []
    out = []
    for v in cache.values():
        for x in (v.get("items") if isinstance(v, dict) else None) or []:
            m = re.match(r"([A-Z]+)(\d{6})$", str(x.get("app") or ""))
            if not m or not x.get("date"):
                continue
            sub = str(x.get("sub") or "")
            out.append({"num": m.group(2), "label": f"{m.group(1)} {m.group(2)} {sub}".strip(),
                        "date": dt.date.fromisoformat(x["date"]), "letter": str(x.get("letter") or ""),
                        "kind": "approval" if sub.startswith("ORIG") else "supplement approval"})
    return out


RE_APPL = re.compile(r'href="(https://www\.accessdata\.fda\.gov/drugsatfda_docs/appletter/\d{4}/(\d{6})[^"]*\.pdf)"')
RE_CRL = re.compile(r'href="(https://download\.open\.fda\.gov/crl/([^"]+\.pdf))"')


def own_record(doc):
    """(application number, FDA record URL) from the page's own FDA record: its "FDA record of the action" line,
    else its FDA-letter card, else its Verified line. The first FDA link in that block is the page's record."""
    for tag in ("FDAREC", "CRLSRC", "VERIFIED"):
        m = re.search(rf"<!--{tag}:BEGIN-->(.*?)<!--{tag}:END-->", doc, re.S)
        if not m:
            continue
        blk = m.group(1)
        hits = sorted([(x.start(), "appl", x) for x in RE_APPL.finditer(blk)]
                      + [(x.start(), "crl", x) for x in RE_CRL.finditer(blk)], key=lambda t: t[0])
        if not hits:
            continue
        _, kind, x = hits[0]
        if kind == "appl":
            return x.group(2), x.group(1)
        mm = re.search(r"(?:NDA|BLA|BL)(\d{6})", x.group(2))
        if mm:
            return mm.group(1), x.group(1)
    return None, None


RE_OVERVIEW = re.compile(r'href="https://www\.accessdata\.fda\.gov/scripts/cder/daf/index\.cfm\?event=overview\.process'
                         r'&(?:amp;)?ApplNo=(\d{6})"')


def overview_record(doc, slug, appr):
    """2026-11-26: a page whose Verified line cites only the Drugs@FDA overview for its application (GSK-2025-10-23,
    Blenrep, BLA 761440) named no record, so the FDA's same-day Complete Response Letter on BLA 761440/Original 2 never
    showed on it. Fall back to that application number, but only when exactly one approval Drugs@FDA lists on it falls
    0 to 4 days before the page's date: that approval's letter is then the page's own record ("this page"). Anything
    less certain gets no block, because a wrong "this page" is worse than none."""
    m = re.search(r"<!--VERIFIED:BEGIN-->(.*?)<!--VERIFIED:END-->", doc, re.S)
    o = RE_OVERVIEW.search(m.group(1)) if m else None
    d = re.search(r"-(\d{4}-\d{2}-\d{2})$", slug)
    if not (o and d):
        return None, None
    day = dt.date.fromisoformat(d.group(1))
    hits = [a for a in appr if a["num"] == o.group(1) and a["letter"] and 0 <= (day - a["date"]).days <= 4]
    if len(hits) != 1:
        return None, None
    return o.group(1), hits[0]["letter"]


def pages():
    out = {}
    appr = approvals()
    for p in sorted(glob.glob(os.path.join(SITE, "fda-decision", "*", "index.html"))):
        slug = os.path.basename(os.path.dirname(p))
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        num, rec = own_record(doc)
        if not num:
            num, rec = overview_record(doc, slug, appr)
        out[slug] = {"path": p, "doc": doc, "num": num, "rec": rec}
    return out


def block(slug, num, rec, crls, apprs, cites):
    rows = []
    for c in crls:
        bits = [f'<a href="{esc(c["pdf"])}" rel="noopener" {LINK}>letter (PDF)</a>']
        if c["slug"]:
            bits.append(f'<a href="/crl/letter/{esc(c["slug"])}" {LINK}>its text</a>')
        dp = cites.get(c["pdf"])
        mine = c["pdf"] == rec
        if dp and dp != slug:
            bits.append(f'<a href="/fda-decision/{esc(dp)}" {LINK}>decision page</a>')
        when = (f'{pretty(c["action"])} (corrected letter dated {pretty(c["date"])})' if c["corrected"]
                else pretty(c["date"]))
        rows.append((c["action"], f'<li style="margin:3px 0"><b>{when}</b>: Complete Response Letter, '
                                  f'{esc(c["label"])} &middot; ' + " &middot; ".join(bits)
                     + (' &middot; <b>this page</b>' if mine else "") + "</li>"))
    for a in apprs:
        bits = [f'<a href="{esc(a["letter"])}" rel="noopener" {LINK}>FDA letter</a>'] if a["letter"] else []
        dp = cites.get(a["letter"])
        mine = a["letter"] and a["letter"] == rec
        if dp and dp != slug:
            bits.append(f'<a href="/fda-decision/{esc(dp)}" {LINK}>decision page</a>')
        rows.append((a["date"], f'<li style="margin:3px 0"><b>{pretty(a["date"])}</b>: {a["kind"]}, '
                                f'{esc(a["label"])}' + (" &middot; " + " &middot; ".join(bits) if bits else "")
                     + (' &middot; <b>this page</b>' if mine else "") + "</li>"))
    rows.sort(key=lambda t: t[0])
    app = crls[0]["label"].split("/")[0]
    return (f'{B}<div data-apphist="{num}" style="background:#0c1d38;border:1px solid #2a496f;border-radius:10px;'
            f'padding:10px 14px;margin:10px 0 14px;font-size:13.5px;color:#cfe0f5"><b style="color:#e3ba5e">FDA actions '
            f'on {esc(app)}</b>, the application this decision belongs to, by date:'
            f'<ul style="margin:6px 0 4px 18px;padding:0">' + "".join(r for _, r in rows) + '</ul>'
            f'<span style="color:#a7bcd9;font-size:12.5px">From the FDA\'s released Complete Response Letters '
            f'(<a href="/crl" {LINK}>every released letter</a>) and the approvals Drugs@FDA lists since January 1, '
            f'2025. A letter the FDA has not released, or an approval before 2025, is not listed.</span></div>{E}')


def main():
    L, A, P = letters(), approvals(), pages()
    by_num = {}
    for c in L:
        by_num.setdefault(c["num"], {"crl": [], "appr": []})["crl"].append(c)
    for a in A:
        if a["num"] in by_num:
            by_num[a["num"]]["appr"].append(a)
    cites = {}                                       # FDA record URL -> the one decision page whose record it is
    dup = set()
    for slug, pg in P.items():
        if pg["rec"]:
            if pg["rec"] in cites:
                dup.add(pg["rec"])
            cites[pg["rec"]] = slug
    for u in dup:                                    # two pages on one record: link neither (a wrong link is worse)
        cites.pop(u, None)
    n_w = n_rm = 0
    for slug, pg in P.items():
        doc = pg["doc"]
        new = re.sub(re.escape(B) + r".*?" + re.escape(E), "", doc, flags=re.S)
        g = by_num.get(pg["num"]) if pg["num"] else None
        if g:
            # one row per letter file: the FDA's release lists a split letter under both "BLA 761440/Original 2" and
            # "BLA 761440"; keep the more specific label (2026-11-26, GSK-2025-10-23 showed the same letter twice)
            one = {}
            for c in g["crl"]:
                k = (c["pdf"], c["date"])
                if k not in one or len(c["label"]) > len(one[k]["label"]):
                    one[k] = c
            crls = sorted(one.values(), key=lambda c: c["action"])
            apprs = sorted(g["appr"], key=lambda a: a["date"])
            others = [c for c in crls if c["pdf"] != pg["rec"]] + [a for a in apprs if a["letter"] != pg["rec"]]
            if others:
                blk = block(slug, pg["num"], pg["rec"], crls, apprs, cites)
                for tag in ("FDAREC", "CRLSRC", "VERIFIED"):
                    end = f"<!--{tag}:END-->"
                    if end in new:
                        i = new.index(end) + len(end)
                        new = new[:i] + blk + new[i:]
                        break
        if new != doc:
            io.open(pg["path"], "w", encoding="utf-8").write(new)
            if B in new:
                n_w += 1
                print(f"  /fda-decision/{slug}: FDA actions on application {pg['num']}")
            else:
                n_rm += 1
    have = sum(1 for pg in P.values() if B in io.open(pg["path"], encoding="utf-8").read())
    print(f"application history: {have} decision page(s) carry the block ({n_w} written or changed, {n_rm} removed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
