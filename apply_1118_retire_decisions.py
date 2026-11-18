# -*- coding: utf-8 -*-
"""apply_1118_retire_decisions.py -- 20 decision pages retired: 17 record an FDA action that
did not happen or duplicate another page, 3 were dated on a day nothing happened and move to the announcement day.

2026-11-18 (David, 2026-11-17 Eastern: "Red team the readout and pdufa dates again, let's build our moat here too
as the most accurate"). verify_decisions.py (2026-08-12) labelled a page "verified" when ANY 8-K/6-K filed within
14 days contained "approval of", "FDA approval" or "complete response letter". The run-up thread re-read those
filings on 2026-11-18 and 35 did not support the page; each of the 46 flagged pages was then checked against
primary sources (FDA letters, Drugs@FDA, openFDA CRL files, company releases). 15 record no FDA action at all and
2 are a second page for an FDA action that already has one:

  no FDA action (301 to the company's ticker page, or to the real decision's page)
    BCAB-2025-11-07  mecbotamab vedotin: Phase 2 data; cited filing is a financing agreement
    IRON-2025-01-21  bitopertin: Type C meeting outcome; not approved (CRL Feb 13, 2026, its own page)
    IRWD-2025-04-14  apraglutide: FDA said a confirmatory Phase 3 is needed; no filing
    KZIA-2025-01-02  paxalisib: cited filing is a prefunded warrant
    LEXX-2025-01-15  DehydraTECH-liraglutide: cited 8-K is shareholder vote results
    NVS-2025-01-29   no drug named; no Novartis FDA action near the date in its FY2024 release
    RNAZ-2025-02-06  TTX-MC138: stockholder meeting adjournment
    RNAZ-2025-03-13  TTX-MC138: cited filing is a warrant
    WVE-2025-03-26   WVE-N531: Phase 2 data, NDA planned for 2026
    XRTX-2025-04-30  XRx-026: Type B meeting responses, no NDA filed
    IBRX-2025-02-19  ANKTIVA: approved Apr 22, 2024; Feb 2025 was expanded access to another BCG source + RMAT
    INVA-2026-02-17  earnings release recapping the Dec 2025 NUZOLVENCE approval (its own page)
    REGN-2025-10-17  solnerstotug: no BLA; that day was an EU CHMP opinion for Libtayo
    OTLK-2026-03-05  LYTENAVA: Type A meeting about the Dec 30, 2025 CRL
    OTLK-2026-04-07  LYTENAVA: formal dispute filing about the Dec 30, 2025 CRL
  second page for one FDA action
    RGNX-2026-02-08  same CRL as RGNX-2026-02-09 (letter Feb 7, announced Feb 9)
    IRON-2026-02-15  same CRL as IRON-2026-02-13 (letter Feb 13)
  wrong day (301 to the page dated the day the action was announced; built from decision_pages_2026_11_18.json)
    SNY-2025-06-02   Dupixent bullous pemphigoid: FDA approved June 18, Sanofi announced June 20
    REGN-2025-06-02  the same approval, Regeneron's page
    SNY-2025-12-28   tolebrutinib: CRL dated Dec 23, announced Dec 24 (Dec 28 was the target date)

What this does, for each slug: deletes the page, adds a permanent redirect, removes every link to it from every
page (HTML rows and lists, JSON-LD ItemLists, sitemap.xml), marks its _decision_verification.json entry
"retracted" with the reason, prunes it from the decision ledgers, and adds a /corrections entry. The slugs join
RETRACTED in tests/test_no_retracted_claims.py so no later build can republish them. Idempotent.
Facts only, not investment advice.

    python apply_1118_retire_decisions.py [--dry-run]
"""
import argparse
import io
import json
import os
import re
import shutil
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
TODAY = "2026-11-18"

# slug -> (redirect destination, one-line reason, source)
RETIRE = {
    "BCAB-2025-11-07": ("/ticker/BCAB", "BioAtla reported Phase 2 survival data for mecbotamab vedotin that day; the drug is not approved. The cited filing is a financing agreement.", "BioAtla release of November 7, 2025"),
    "IRON-2025-01-21": ("/ticker/IRON", "Disc Medicine announced a Type C meeting outcome and an NDA plan. Bitopertin was not approved; it received a Complete Response Letter on February 13, 2026.", "Disc Medicine 8-K exhibit 99.1 of January 21, 2025"),
    "IRWD-2025-04-14": ("/ticker/IRWD", "Ironwood said the FDA wants a confirmatory Phase 3 trial before apraglutide is filed. No approval or CRL.", "Ironwood 8-K exhibit 99.1 of April 14, 2025"),
    "KZIA-2025-01-02": ("/ticker/KZIA", "The cited filing is a prefunded warrant. Paxalisib is not FDA approved.", "Kazia SEC filing 0001193125-25-005004"),
    "LEXX-2025-01-15": ("/ticker/LEXX", "The cited 8-K reports shareholder vote results from Lexaria's annual meeting. No FDA action.", "Lexaria 8-K of January 15, 2025"),
    "NVS-2025-01-29": ("/ticker/NVS", "The page named no drug, and Novartis's full-year 2024 release lists no FDA approval or CRL near that date.", "Novartis Q4 and full-year 2024 release, January 31, 2025"),
    "RNAZ-2025-02-06": ("/ticker/RNAZ", "TransCode announced the adjournment of a stockholder meeting. TTX-MC138 is clinical-stage; no FDA action.", "TransCode 8-K exhibit 99.1 of February 4, 2025"),
    "RNAZ-2025-03-13": ("/ticker/RNAZ", "The cited filing is a common stock purchase warrant. No FDA action.", "TransCode SEC filing 0001104659-25-027565"),
    "WVE-2025-03-26": ("/ticker/WVE", "Wave reported Phase 2 data for WVE-N531 and said it plans to file in 2026. No approval.", "Wave 8-K exhibit 99.1 of March 26, 2025"),
    "XRTX-2025-04-30": ("/ticker/XRTX", "XORTX reported FDA responses to a Type B meeting request. No NDA had been filed; no approval.", "XORTX exhibit 99.1 of April 30, 2025"),
    "IBRX-2025-02-19": ("/ticker/IBRX", "ANKTIVA was approved on April 22, 2024. In February 2025 the FDA authorized expanded access to another BCG source and granted an RMAT designation, which are not approvals.", "ImmunityBio 8-K exhibit 99.1, February 2025"),
    "INVA-2026-02-17": ("/fda-decision/INVA-2025-12-15", "The cited release is an earnings report that recaps the December 2025 NUZOLVENCE approval, which has its own page. No FDA action near February 17, 2026.", "Innoviva 8-K exhibit 99.1 of February 25, 2026"),
    "REGN-2025-10-17": ("/ticker/REGN", "Solnerstotug has no BLA and received no CRL. That day Regeneron announced a positive EU CHMP opinion for adjuvant Libtayo.", "Regeneron release of October 17, 2025"),
    "OTLK-2026-03-05": ("/ticker/OTLK", "Outlook reported a Type A meeting with the FDA about the existing December 30, 2025 CRL. No new FDA action.", "Outlook Therapeutics 8-K of March 5, 2026"),
    "OTLK-2026-04-07": ("/ticker/OTLK", "Outlook reported filing a formal dispute resolution request about the December 30, 2025 CRL. No new FDA action.", "Outlook Therapeutics 8-K of April 7, 2026"),
    "RGNX-2026-02-08": ("/fda-decision/RGNX-2026-02-09", "A second page for the RGX-121 Complete Response Letter, dated February 7, 2026 and announced February 9. Nothing happened on February 8.", "FDA CRL file for BLA 125840, dated February 7, 2026"),
    "IRON-2026-02-15": ("/fda-decision/IRON-2026-02-13", "A second page for the bitopertin Complete Response Letter of February 13, 2026. Nothing happened on February 15.", "FDA CRL file for NDA 220707, dated February 13, 2026"),
    # 2026-11-18, second pass: three pages dated to a day nothing happened, for an FDA action that did happen.
    # Each gets a new page on the day the action became public, built from price data by build_decision_page.py
    # (decision_pages_2026_11_18.json), and the old address redirects there.
    "SNY-2025-06-02": ("/fda-decision/SNY-2025-06-20", "The FDA approved Dupixent for bullous pemphigoid on June 18, 2025 and Sanofi announced it on June 20. Nothing happened on June 2, and the SEC filing the page cited does not mention the approval. The decision now has its page at the June 20 announcement.", "FDA approval letter for BLA 761055 S-070, June 18, 2025", "A Sanofi FDA decision page dated 2025-06-02 for the Dupixent bullous pemphigoid approval, labelled as verified from an SEC filing."),
    "REGN-2025-06-02": ("/fda-decision/REGN-2025-06-20", "The FDA approved Dupixent for bullous pemphigoid on June 18, 2025 and Regeneron and Sanofi announced it on June 20. Nothing happened on June 2. The decision now has its page at the June 20 announcement.", "FDA approval letter for BLA 761055 S-070, June 18, 2025", "A Regeneron FDA decision page dated 2025-06-02 for the Dupixent bullous pemphigoid approval, marked as inferred from the share price."),
    "SNY-2025-12-28": ("/fda-decision/SNY-2025-12-24", "The FDA's Complete Response Letter for tolebrutinib is dated December 23, 2025 and Sanofi announced it on December 24. December 28 was the review's target date, not the day of the letter. The decision now has its page at the December 24 announcement.", "FDA CRL file for NDA 219624, dated December 23, 2025", "A Sanofi FDA decision page dated 2025-12-28 for the tolebrutinib Complete Response Letter, labelled as verified from an SEC filing."),
}
SKIP_FILES = {os.path.join("corrections", "index.html"), os.path.join("changelog", "index.html")}


def jload(p):
    return json.load(io.open(os.path.join(HERE, p), encoding="utf-8"))


def jsave(p, d, indent=1):
    io.open(os.path.join(HERE, p), "w", encoding="utf-8", newline="").write(
        json.dumps(d, indent=indent, ensure_ascii=False) + "\n")


def _prune_items(node, gone_urls):
    """Drop ListItems that point at a retired page from any itemListElement; renumber positions."""
    changed = False
    if isinstance(node, dict):
        for k, v in list(node.items()):
            if k == "itemListElement" and isinstance(v, list):
                keep = []
                for it in v:
                    u = ""
                    if isinstance(it, dict):
                        u = str(it.get("url") or it.get("item") or "")
                        if isinstance(it.get("item"), dict):
                            u = str(it["item"].get("@id") or it["item"].get("url") or "")
                    if any(u.endswith(g) for g in gone_urls):
                        changed = True
                        continue
                    keep.append(it)
                if changed:
                    for i, it in enumerate(keep, 1):
                        if isinstance(it, dict) and "position" in it:
                            it["position"] = i
                    node[k] = keep
            if _prune_items(v, gone_urls):
                changed = True
    elif isinstance(node, list):
        for v in node:
            if _prune_items(v, gone_urls):
                changed = True
    return changed


def unlink(doc, slug):
    href = re.escape(f"/fda-decision/{slug}")
    pats = [
        rf'<a class="row" href="{href}"[^>]*>(?:(?!<a\b).)*?</a>',
        rf'<li[^>]*>\s*<a [^>]*href="{href}"[^>]*>[^<]*</a>\s*</li>',
        rf'\s*&middot;\s*<a [^>]*href="{href}"[^>]*>[^<]*</a>',
        rf'<a [^>]*href="{href}"[^>]*>[^<]*</a>\s*&middot;\s*',
        rf'\s*·\s*<a [^>]*href="{href}"[^>]*>[^<]*</a>',
        rf'<a [^>]*href="{href}"[^>]*>[^<]*</a>\s*·\s*',
        rf'<url>\s*<loc>https://www\.pdufa\.bio{href}/?</loc>.*?</url>\s*',
        rf'<tr[^>]*>(?:(?!</tr>).)*?href="{href}".*?</tr>',
    ]
    for p in pats:
        doc = re.sub(p, "", doc, flags=re.S)
    return doc


def fix_jsonld(doc, gone_urls):
    def rep(m):
        body = m.group(2)
        if not any(g in body for g in gone_urls):
            return m.group(0)
        try:
            j = json.loads(body)
        except Exception:  # noqa: BLE001
            return m.group(0)
        if _prune_items(j, gone_urls):
            return m.group(1) + json.dumps(j, ensure_ascii=False) + m.group(3)
        return m.group(0)
    return re.sub(r'(<script type="application/ld\+json">)(.*?)(</script>)', rep, doc, flags=re.S)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    gone_urls = [f"/fda-decision/{s}" for s in RETIRE]

    # 1. pages
    deleted = [s for s in RETIRE if os.path.isdir(os.path.join(SITE, "fda-decision", s))]
    for s in deleted:
        if not a.dry_run:
            shutil.rmtree(os.path.join(SITE, "fda-decision", s))
    print(f"pages deleted: {len(deleted)}")

    # 2. redirects (and repoint any older redirect that landed on a retired page)
    vp = os.path.join(SITE, "vercel.json")
    v = json.load(io.open(vp, encoding="utf-8"))
    reds = v.setdefault("redirects", [])
    have = {r["source"] for r in reds}
    for r in reds:
        for s, (dst, *_r) in RETIRE.items():
            if r["destination"].rstrip("/") == f"/fda-decision/{s}":
                r["destination"] = dst
    added = 0
    for s, (dst, *_r) in RETIRE.items():
        if f"/fda-decision/{s}" not in have:
            reds.append({"source": f"/fda-decision/{s}", "destination": dst, "permanent": True})
            added += 1
    if not a.dry_run:
        io.open(vp, "w", encoding="utf-8").write(json.dumps(v, indent=1, ensure_ascii=False) + "\n")
    print(f"redirects added: {added}")

    # 3. every link, every surface
    touched, left = 0, []
    for root, _, files in os.walk(SITE):
        for fn in files:
            if not fn.endswith((".html", ".xml", ".json", ".js", ".mjs")):
                continue
            p = os.path.join(root, fn)
            rel = os.path.relpath(p, SITE)
            if rel in SKIP_FILES or rel == "vercel.json":
                continue
            doc = io.open(p, encoding="utf-8", errors="replace").read()
            if "/fda-decision/" not in doc or not any(g in doc for g in gone_urls):
                continue
            new = doc
            for s in RETIRE:
                if s in new:
                    new = unlink(new, s)
            new = fix_jsonld(new, gone_urls)
            if new != doc:
                touched += 1
                if not a.dry_run:
                    io.open(p, "w", encoding="utf-8", newline="").write(new)
            for g in gone_urls:
                if re.search(re.escape(g) + r'(?![\w-])', new):
                    left.append(f"{rel}: {g}")
    print(f"files unlinked: {touched}")
    for x in left:
        print("   STILL LINKED", x)

    if a.dry_run:
        return

    # 4. ledgers
    ver = jload("_decision_verification.json")
    for s, (_, why, src, *_r) in RETIRE.items():
        e = ver["results"].get(s)
        if e and e.get("status") != "retracted":
            e["status_before_retraction"] = e.get("status")
            e["status"] = "retracted"
            e["retracted"] = {"date": TODAY, "why": why, "source": src}
    jsave("_decision_verification.json", ver)
    for f in ("_decision_published.json", "_decision_first_recorded.json", "_fda_action_archive.json"):
        p = os.path.join(HERE, f)
        if not os.path.exists(p):
            continue
        j = jload(f)
        n = 0
        if isinstance(j, dict):
            for s in RETIRE:
                for k in (s, f"/fda-decision/{s}", f"fda-decision/{s}", f"https://www.pdufa.bio/fda-decision/{s}"):
                    if k in j:
                        j.pop(k)
                        n += 1
            for k in list(j):
                if isinstance(j[k], dict):
                    for s in RETIRE:
                        for kk in (s, f"/fda-decision/{s}", f"fda-decision/{s}"):
                            if kk in j[k]:
                                j[k].pop(kk)
                                n += 1
        if n:
            jsave(f, j)
        print(f"{f}: {n} entr(ies) pruned")
    lp = os.path.join(HERE, "_sitemap_lastmod.json")
    raw = io.open(lp, encoding="utf-8").read()
    lm = json.loads(raw)
    n = sum(1 for s in RETIRE if lm.pop(f"pdufa_site_src/fda-decision/{s}/index.html", None) is not None)
    if n:
        io.open(lp, "w", encoding="utf-8", newline="").write(
            json.dumps(lm, indent=0, ensure_ascii=False) + ("\n" if raw.endswith("\n") else ""))
    print(f"_sitemap_lastmod.json: {n} entr(ies) pruned")
    ev = jload("_chart2026_events.json")
    keep = [e for e in ev if f"{e.get('ticker')}-{e.get('date')}" not in RETIRE]
    if len(keep) != len(ev):
        io.open(os.path.join(HERE, "_chart2026_events.json"), "w", encoding="utf-8").write(
            json.dumps(keep, indent=0, ensure_ascii=False))
    print(f"_chart2026_events.json: {len(ev) - len(keep)} removed")

    # 5. /corrections
    cor = jload("_corrections.json")
    pages = {e.get("page") for e in cor["entries"] if e.get("date") == TODAY}
    n = 0
    for e in cor["entries"]:                      # first pass wrote "A IRON FDA decision page ..."
        m = re.match(r"A ([A-Z]{1,6}) FDA decision page dated (\d{4}-\d{2}-\d{2}), labelled", e.get("was") or "")
        if e.get("date") == TODAY and m:
            e["was"] = f"A decision page for {m.group(1)} dated {m.group(2)}, labelled" + e["was"][m.end():]
    for s, (dst, why, src, *was) in RETIRE.items():
        page = f"/fda-decision/{s}"
        if page in pages:
            continue
        tk, d = s.split("-", 1)
        cor["entries"].append({"date": TODAY, "page": page,
                               "was": was[0] if was else f"A decision page for {tk} dated {d}, labelled as verified from an SEC filing.",
                               "now": why + " The page is retired and redirects to " + dst + ".",
                               "source": src})
        n += 1
    jsave("_corrections.json", cor)
    print(f"/corrections: {n} entr(ies) added")


if __name__ == "__main__":
    main()
