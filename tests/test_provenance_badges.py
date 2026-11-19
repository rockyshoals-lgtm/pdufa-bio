# -*- coding: utf-8 -*-
"""test_provenance_badges.py -- the site says what it can show, and marks what it cannot, wherever it lists it.

Design red team 2026-11-18 (change 5). The homepage promised "every date links its source" while 107 decision pages
gave an outcome inferred from the stock's move and 17 cited nothing; the lists that link those pages showed them like
any decision read from an FDA letter, and the run-up study, sold as primary-sourced, took 17 of the unsourced
outcomes into its statistics. This fails if:

  1. a link to a decision page whose outcome is inferred (or which cites no source), as page_kind() reads it, does not
     carry the "Inferred" (or "Unsourced") badge inside it, on any page of the site; or a link to a sourced page, or
     anything outside a link, carries one;
  2. badge_decision_provenance.py would change any page (it is not at its badged state);
  3. a page or a builder still makes the old promise ("every date links its source", "every date and outcome links",
     "every date sourced", "each row links its source", "with the source document and the share-price reaction");
  4. the run-up study (pdufa_runup_bifrost_v2.csv) holds an event whose decision page is inferred or unsourced;
  5. the workflow does not run the badge pass after inject_site_links.py and before inject_mobile_polish.py, the
     local chain does not run it, or quarantine_leads.py does not badge the pages it restores.

PLANT=strip drops one badge, PLANT=wrong turns one Inferred badge into Unsourced, PLANT=promise puts the old promise
back on the homepage, PLANT=study treats one study event as inferred, PLANT=leak leaves a badge's word as plain text in
a table cell; each must FAIL.

    python tests/test_provenance_badges.py
"""
import csv
import glob
import io
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
sys.path.insert(0, HERE)
import badge_decision_provenance as bp  # noqa: E402

PROMISE = re.compile(r"every date links its source|every date and outcome links|every date (?:is )?sourced|"
                     r"every date linked to its source|each row links its source|"
                     r"with the source document and the share-price reaction|carrying the source document|"
                     r"each with its source (?:document|and the stock)|each source-linked|CRLs, source-linked|"
                     r"(?:every|each) record below links to its source|each item links to its source", re.I)
# a badge's word left behind as plain text by a script that read a badged row ("<td>price-onlyInferred</td>")
LEAK = re.compile(r">[^<]*[^\s>][ ]?\b(?:Inferred|Unsourced)\s*</")
META = re.compile(r'<meta (?:name="description"|property="og:description"|name="twitter:description") content="([^"]*)"')
WORD = {"inferred": "Inferred", "unsourced": "Unsourced"}


def held_pages():
    """Pages quarantine_leads.py apply restores to their last commit while a lead is held: they keep the wording they
    were committed with (the badges are re-applied), so the promise check skips them, or one held lead would block
    every deploy (tests/test_event_page_currency.py does the same)."""
    try:
        import json
        import quarantine_leads as Q
        st = json.load(open(Q.STATE, encoding="utf-8")) if os.path.exists(Q.STATE) else {}
        ids = {l.get("row_id") for l in st.get("leads") or [] if l.get("row_id")}
        if not ids:
            return set()
        src = open(Q.DATASET, encoding="utf-8", errors="replace").read()
        rows = {r.get("id"): r for r in json.loads(src[src.index("["):src.rindex("]") + 1].replace("\x00", ""))}
        return {os.path.normcase(os.path.abspath(p)) for rid in ids
                for p in Q.held_paths(rows.get(rid) or {}, rid[5:] if rid.startswith("drug:") else None)}
    except Exception as ex:  # noqa: BLE001
        print(f"  note: could not read held leads ({ex.__class__.__name__}); checking every page")
        return set()


def strip_scripts(doc):
    return re.sub(r"<(script|style)\b.*?</\1>", " ", doc, flags=re.S)


def main():
    plant = os.environ.get("PLANT", "")
    kinds = bp.kinds()
    bad, links, badged = [], 0, 0
    planted = False
    held = held_pages()
    for p in bp.pages():
        rel = os.path.relpath(p, SITE).replace(os.sep, "/")
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        if not planted and plant in ("strip", "wrong") and "<!--PV:B-->" in doc:
            if plant == "strip":
                doc = re.sub(r"<!--PV:B-->.*?<!--PV:E-->", "", doc, count=1, flags=re.S)
            elif "pv-inferred" in doc:
                doc = doc.replace("pv-inferred", "pv-unsourced", 1)
            else:
                continue
            planted = True
        if plant == "promise" and rel == "index.html":
            doc = doc.replace("</body>", "<p>Every date links its source.</p></body>", 1)
        if plant == "leak" and rel == "crl/index.html":
            doc = doc.replace("</body>", "<table><tr><td>price-only Inferred</td></tr></table></body>", 1)
        if bp.apply(doc) != doc:
            bad.append(f"/{rel}: badge_decision_provenance.py would change this page")
        body = strip_scripts(doc)
        inside = 0
        for m in bp.LINK.finditer(body):
            slug, inner = m.group(2), m.group(3)
            k = kinds.get(slug)
            got = re.findall(r'<span class="pv pv-([a-z]+)"[^>]*>([A-Za-z]+)</span>', inner)
            inside += len(got)
            links += 1
            if not re.sub(r"<[^>]+>", "", re.sub(r"<!--PV:B-->.*?<!--PV:E-->", "", inner, flags=re.S)).strip():
                continue
            if k in WORD:
                if got != [(k, WORD[k])]:
                    bad.append(f"/{rel}: the link to /fda-decision/{slug} ({k}) shows "
                               + (", ".join(f"{w} (class pv-{c})" for c, w in got) or "no badge")
                               + f"; it should say {WORD[k]} (class pv-{k})")
                else:
                    badged += 1
            elif got:
                bad.append(f"/{rel}: the link to /fda-decision/{slug} ({k or 'no page'}) carries a "
                           f"{got[0][1]} badge")
        if body.count("<!--PV:B-->") != inside:
            bad.append(f"/{rel}: a provenance badge sits outside a link to a decision page")
        bare = re.sub(r"<!--PV:B-->.*?<!--PV:E-->", "", body, flags=re.S)
        lk = LEAK.search(bare)
        if lk:
            bad.append(f"/{rel}: a badge's word sits in the page as plain text ('{bare[max(0, lk.start() - 30):lk.end()]}'"
                       "); a script read a badged row without dropping the badge")
        # visible text, JSON-LD and the page's descriptions
        said = " ".join([re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", doc))] + META.findall(doc))
        pm = PROMISE.search(said)
        if pm and os.path.normcase(os.path.abspath(p)) not in held:
            bad.append(f"/{rel}: still promises '{pm.group(0)}'")
        if rel.startswith("fda-decision/") and kinds.get(rel.split("/")[1]) == "unsourced":
            for d in META.findall(doc):
                if re.search(r"source document|Source and run-up", d):
                    bad.append(f"/{rel}: cites no source, but its description promises one ('{d[-70:]}')")
    if plant in ("strip", "wrong") and not planted:
        bad.append(f"PLANT={plant} found nothing to plant on")
    # 3. the builders
    for b in glob.glob(os.path.join(HERE, "*.py")):
        if os.path.basename(b) == "badge_decision_provenance.py":
            continue
        src = io.open(b, encoding="utf-8", errors="replace").read()
        # docstrings and comments may quote the old promise; a string literal that prints it may not. Adjacent
        # literals are joined first, since a builder wraps a long sentence over several lines.
        src = re.sub(r'"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'', " ", src)
        src = re.sub(r"(?m)^\s*#.*$|\s#\s.*$", " ", src)
        src = re.sub(r"""(["'])\s*\)?\s*\n\s*\+?\s*\(?\s*[rfb]*(["'])""", "", src)
        hit = PROMISE.search(src)
        if hit:
            bad.append(f"{os.path.basename(b)}: still writes '{hit.group(0)}'")
    # 4. the study
    study = os.path.join(HERE, "pdufa_runup_bifrost_v2.csv")
    n_study = n_page = 0
    if os.path.exists(study):
        for r in csv.DictReader(io.open(study, encoding="utf-8", errors="replace")):
            n_study += 1
            slug = f"{(r.get('ticker') or '').upper()}-{(r.get('pdufa_date') or '')[:10]}"
            n_page += slug in kinds
            if kinds.get(slug) in WORD or (plant == "study" and n_page == 1 and slug in kinds):
                bad.append(f"the run-up study holds {slug}, whose decision page is {kinds.get(slug) or 'planted'}")
    if os.path.exists(study) and n_page < 100:
        bad.append(f"only {n_page} study rows map to a decision page; the study check reads the wrong columns")
    # 5. wiring
    wf = io.open(os.path.join(HERE, ".github", "workflows", "pdufa-rebuild.yml"), encoding="utf-8").read()
    a, b, c = (wf.find("python inject_site_links.py"), wf.find("python badge_decision_provenance.py"),
               wf.find("python inject_mobile_polish.py"))
    if not (0 <= a < b < c):
        bad.append("the workflow does not run badge_decision_provenance.py after inject_site_links.py and before "
                   "inject_mobile_polish.py")
    chain = io.open(os.path.join(HERE, "_chain_0919.bat"), encoding="utf-8", errors="replace").read()
    # the same order as the workflow (2026-11-18: change 11's site-type and calendar passes now sit between the two)
    ca, cb, cc = (chain.find(" inject_site_links.py "), chain.find(" badge_decision_provenance.py "),
                  chain.find(" inject_mobile_polish.py "))
    if not (0 <= ca < cb < cc):
        bad.append("_chain_0919.bat does not run badge_decision_provenance.py after inject_site_links.py and before "
                   "inject_mobile_polish.py")
    q = io.open(os.path.join(HERE, "quarantine_leads.py"), encoding="utf-8").read()
    if "badge_decision_provenance.apply(old)" not in q:
        bad.append("quarantine_leads.py restores committed pages without their provenance badges")
    print(f"{links} link(s) to decision pages, {badged} badged ({sum(v == 'inferred' for v in kinds.values())} "
          f"inferred and {sum(v == 'unsourced' for v in kinds.values())} unsourced pages); study {n_study} rows, "
          f"{n_page} with a decision page")
    if bad:
        for x in bad[:30]:
            print("  FAIL " + x)
        if len(bad) > 30:
            print(f"  ... and {len(bad) - 30} more")
        print("  fix: python curate_runup_study.py && python badge_decision_provenance.py")
        sys.exit(1)
    print("  PASS: every inferred or unsourced decision is marked where it is listed, and the study holds none")


if __name__ == "__main__":
    main()
