# -*- coding: utf-8 -*-
"""test_accessibility.py -- a keyboard, a screen reader and weak eyesight can use every page, and the heavy pages
stay light.

Design red team 2026-11-18 (change 12, "Accessibility and speed"). There was no skip link in front of a 30-plus link
header; about 970 charts were role="img" with no name; sparklines showed up or down by colour alone; the screener's
result count changed silently; FAQ disclosure markers were hidden; text fields drew their border at 2.17:1; the
run-up study was all tables; /readouts carried 39KB of JSON-LD marking trial readouts up as attended Events; the
homepage fetched every row of the events API (limit 3000) to print one date. This fails if:

  1. a public page is not at inject_a11y.py's state (the pass would change it);
  2. a page with the site header has no "Skip to content" link ahead of the header's links, or no target after them;
  3. an <svg role="img"> has no name, or a sparkline (64x20 or 72x20) is neither named nor hidden from screen readers;
     or the sparkline and chart builders stop naming what they draw;
  4. a <summary> hides its disclosure marker (list-style:none, or a ::-webkit-details-marker / ::marker rule that
     hides it);
  5. the field-border colour is under 3:1 against a field (#081426) or a card (#0e1c33), or a page with a text field
     lacks the rule that applies it;
  6. the screener's count line is not a live region;
  7. /readouts carries the Event ItemList again, or more than 4KB of JSON-LD;
  8. /runup-by-year has no chart of the run-up by market-cap tier, or its chart differs from the study's medians;
  9. the homepage fetches the events API again, or build-info.json's calendar_updates differs from the dataset;
 10. the workflow does not run inject_a11y.py before inject_mobile_polish.py, the local chain does not run it, or
     quarantine_leads.py does not apply it to the pages it restores.

PLANT=skip drops one skip link, PLANT=chart strips one chart's name, PLANT=marker hides one FAQ marker, PLANT=count
drops the screener's live region, PLANT=ld puts an Event ItemList back on /readouts, PLANT=fetch puts the API fetch back
on the homepage; each must FAIL.

    python tests/test_accessibility.py
"""
import csv
import io
import json
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
import inject_a11y as A  # noqa: E402

SCRIPT = re.compile(r"<script\b.*?</script>", re.S)


def lum(h):
    h = h.lstrip("#")
    f = (lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    r, g, b = (f(int(h[i:i + 2], 16) / 255) for i in (0, 2, 4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    x, y = sorted((lum(a), lum(b)))
    return (y + 0.05) / (x + 0.05)


def main():
    plant = os.environ.get("PLANT", "")
    bad = []
    planted = set()
    n_pages = n_skip = n_named = 0
    for p in A.pages():
        rel = os.path.relpath(p, SITE).replace(os.sep, "/")
        doc = io.open(p, encoding="utf-8", errors="replace", newline="").read()
        if "</head>" not in doc:
            continue
        if plant == "skip" and "skip" not in planted and A.SKIP_LINK in doc:
            doc = doc.replace(A.SKIP_LINK, "", 1)
            planted.add("skip")
        if plant == "chart" and "chart" not in planted and re.search(r'<svg\b[^>]*role="img" aria-label="', doc):
            doc = re.sub(r'(<svg\b[^>]*role="img") aria-label="[^"]*"', r"\1", doc, count=1)
            planted.add("chart")
        if plant == "marker" and "marker" not in planted and "<summary " in doc:
            doc = doc.replace("<summary ", '<summary style="list-style:none" ', 1)
            planted.add("marker")
        if plant == "count" and rel == "screener/index.html":
            doc = doc.replace(A.METER_LIVE, A.METER)
            planted.add("count")
        if plant == "ld" and rel == "readouts/index.html":
            doc = doc.replace("</head>", '<script type="application/ld+json">{"@context":"https://schema.org",'
                              '"@type":"ItemList","name":"Clinical Trial Readout Calendar","itemListElement":[{"@type":'
                              '"ListItem","position":1,"item":{"@type":"Event","name":"X"}}]}</script></head>', 1)
            planted.add("ld")
        if plant == "fetch" and rel == "index.html":
            doc = doc.replace("</body>", "<script>fetch('/api/v1/events?limit=3000')</script></body>", 1)
            planted.add("fetch")
        n_pages += 1
        # 1. at the pass's state (a planted page is not: that is the point of the plant, and the checks below name it)
        if A.apply(doc) != doc and not planted:
            bad.append(f"/{rel}: inject_a11y.py would change this page")
        body = SCRIPT.sub(" ", doc)
        # 2. skip link
        if "<!--NAVC:END-->" in body:
            k, end = body.find(A.SKIP_LINK), body.find("<!--NAVC:END-->")
            first = body.find("<!--NAVC:BEGIN-->")
            t = body.find(A.TARGET)
            if k < 0 or k > first or body.count('class="pd-skip"') != 1:
                bad.append(f"/{rel}: no 'Skip to content' link ahead of the header's links")
            elif t < end or body.count('id="main-content"') != 1:
                bad.append(f"/{rel}: the skip link has no single target after the header's links")
            else:
                n_skip += 1
        # 3. charts and sparklines
        for m in A.SVG_OPEN.finditer(body):
            tag = m.group(0)
            if 'aria-hidden="true"' in tag:
                continue
            named = re.search(r'aria-label="([^"]+)"|aria-labelledby="[^"]+"', tag)
            if 'role="img"' in tag:
                if not named or (named.group(1) or "x").strip(" .") in ("", "Chart"):
                    bad.append(f"/{rel}: a chart (role=img) has no name: {tag[:90]}")
                else:
                    n_named += 1
            elif re.search(r'\bheight="20"', tag) and re.search(r'viewBox="0 0 (?:64|72) 20"', tag):
                bad.append(f"/{rel}: a sparkline has no name and is not hidden: {tag[:90]}")
        # 4. FAQ markers
        for m in re.finditer(r"<summary\b[^>]*>", body):
            if re.search(r"list-style:\s*none", m.group(0)):
                bad.append(f"/{rel}: a <summary> hides its disclosure marker")
                break
        for st in re.findall(r"<style\b[^>]*>(.*?)</style>", doc, re.S):
            if re.search(r"summary[^{}]*\{[^}]*list-style:\s*none|details-marker\s*\{[^}]*display:\s*none|"
                         r"summary::marker\s*\{[^}]*(?:content:\s*(?:''|\"\")|display:\s*none)", st):
                bad.append(f"/{rel}: a style rule hides the FAQ disclosure marker")
                break
        # 5. field borders
        if re.search(r"<(?:input|select|textarea)\b", body) and A.CSS not in doc:
            bad.append(f"/{rel}: has a form field but not the 3:1 field-border rule")
        # 6.
        if rel == "screener/index.html" and A.METER_LIVE not in doc:
            bad.append("/screener: the result count is not a live region (role=status aria-live=polite)")
        # 7.
        if rel == "readouts/index.html":
            lds = re.findall(r'<script type="application/ld\+json"[^>]*>(.*?)</script>', doc, re.S)
            if any('"ItemList"' in x and '"Event"' in x for x in lds):
                bad.append("/readouts: the Event ItemList is back in its JSON-LD")
            if sum(len(x) for x in lds) > 4096:
                bad.append(f"/readouts: {sum(len(x) for x in lds):,} bytes of JSON-LD (limit 4,096)")
        # 9.
        if rel == "index.html" and re.search(r"fetch\(\s*['\"]/api/v1/events", doc):
            bad.append("home: a script fetches the events API again on every load")
    for want in ("skip", "chart", "marker", "count", "ld", "fetch"):
        if plant == want and want not in planted:
            bad.append(f"PLANT={plant} found nothing to plant on")
    # 3b. the builders name what they draw
    try:
        import build_home_board as H
        import build_readout_results as R
        for svg in (H.sparkline([10, 11, 12, 9]), H.sparkline_reaction([("2026-01-0%d" % i, c) for i, c in
                                                                         enumerate([10, 11, 12, 9], 1)], "2026-01-03")[0],
                    R.spark([10, 11, 12, 9])[0]):
            if not re.search(r'<svg\b[^>]*role="img"[^>]*aria-label="Share price[^"]*(?:up|down|flat)', svg):
                bad.append(f"a sparkline builder draws an unnamed sparkline: {svg[:100]}")
        import build_decision_page as D
        s, _n, _r = D.svg([10, 12, 11, 9, 10, 13, 12], ["2025-01-0%d" % i for i in range(1, 8)], 4, "2025-01-05",
                          "Approved")
        if 'aria-label="Price into the decision (T-120). Daily close' not in s:
            bad.append("build_decision_page.py draws its chart with no name")
    except Exception as ex:  # noqa: BLE001
        bad.append(f"could not exercise the chart builders ({ex.__class__.__name__}: {ex})")
    # 5b. the colour itself
    for bg in ("#081426", "#0e1c33"):
        if contrast(A.FIELD_BORDER, bg) < 3:
            bad.append(f"field border {A.FIELD_BORDER} is {contrast(A.FIELD_BORDER, bg):.2f}:1 on {bg}, under 3:1")
    # 8. the run-up study's chart against the study
    import build_runup_by_year as B
    study = os.path.join(HERE, "pdufa_runup_bifrost_v2.csv")
    page = io.open(os.path.join(SITE, "runup-by-year", "index.html"), encoding="utf-8", errors="replace").read()
    order = ["Nano (<$50M)", "Micro ($50M-$300M)", "Small ($300M-$2B)", "Mid ($2B-$10B)", "Large (>$10B)"]
    want = B.tier_runup_chart(list(csv.DictReader(io.open(study, encoding="utf-8-sig", errors="replace"))), order)
    if not want or want.count('class="rc-r"') < 4:
        bad.append("/runup-by-year: the study yields no run-up-by-tier chart")
    elif want not in page:
        bad.append("/runup-by-year: no chart of the run-up by market-cap tier, or it differs from the study's medians "
                   "(python build_runup_by_year.py)")
    # 9b. build-info carries what the home eyebrow reads
    import build_freshness_stamp as F
    bi = json.load(io.open(os.path.join(SITE, "build-info.json"), encoding="utf-8"))
    if bi.get("calendar_updates") != F.calendar_updates():
        bad.append("build-info.json: calendar_updates is missing or differs from the dataset "
                   "(python build_freshness_stamp.py)")
    # 10. wiring
    wf = io.open(os.path.join(HERE, ".github", "workflows", "pdufa-rebuild.yml"), encoding="utf-8").read()
    a, c = wf.find("python inject_a11y.py"), wf.find("python inject_mobile_polish.py")
    if not (0 <= a < c):
        bad.append("the workflow does not run inject_a11y.py before inject_mobile_polish.py")
    chain = io.open(os.path.join(HERE, "_chain_0919.bat"), encoding="utf-8", errors="replace").read()
    if not re.search(r" inject_a11y\.py (?:\S+\.py )*?inject_mobile_polish\.py ", chain):
        bad.append("_chain_0919.bat does not run inject_a11y.py before inject_mobile_polish.py")
    q = io.open(os.path.join(HERE, "quarantine_leads.py"), encoding="utf-8").read()
    if "inject_a11y.apply(old)" not in q:
        bad.append("quarantine_leads.py restores committed pages without the accessibility pass")
    print(f"{n_pages} page(s): {n_skip} with a skip link, {n_named} named chart(s)")
    if bad:
        for x in bad[:30]:
            print("  FAIL " + x)
        if len(bad) > 30:
            print(f"  ... and {len(bad) - 30} more")
        print("  fix: python inject_a11y.py && python inject_mobile_polish.py")
        sys.exit(1)
    print("  PASS: skip links, named charts and sparklines, FAQ markers, 3:1 field borders, a live screener count, "
          "a light /readouts and homepage, and the run-up chart")


if __name__ == "__main__":
    main()
