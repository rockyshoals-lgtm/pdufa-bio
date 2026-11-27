# -*- coding: utf-8 -*-
"""link_fda_label_record.py -- every FDA approval page carries the FDA's own record of the approved product.

2026-11-27 (David: "optimize everything search related to get to number 1 on Bing and get 90% of all AI citations").
On single-drug approval queries ("asundexian approval", "neladalkib fda", "Jemperli approval") Copilot cites the FDA
press release and trade press, which carry the label facts: the brand, the application, the dosage form and
strength, the approval letter and the label. Our /fda-decision pages had the date and the indication but, for most
approvals, no application number, no dosage form and no link to the approval letter or the label.

All of it is already in a file this site reads: _fda_approvals_months.json, the Drugs@FDA month cache that
build_fda_approvals_months.py refreshes every run (application, brand, generic, submission, classification, action
day, approval letter and, since 2026-11-27, the approved label, review priority and the products Drugs@FDA lists on
the application). This writes one block, <!--LABELREC:BEGIN--> ... <!--LABELREC:END-->, at the end of the main
content of each approval page (before the site links), with one row group per application:

  * the application number, brand and generic, as Drugs@FDA prints them;
  * the action: approved on the FDA's date, original application (with its NDA classification) or efficacy
    supplement, and the review priority;
  * the products Drugs@FDA lists as marketed on the application (dosage form, route, strength, in the FDA's words);
  * the approval letter, the approved label and the Drugs@FDA entry for the application.

MATCHING. A page is an approval page when its dataset row (by URL, else by ticker and decision day) is Approved. An
application is the page's when Drugs@FDA records an approval on it within three days of the page's decision day AND
its brand or generic contains a name word (five letters or more) from the row's brand, generic or event name. Up to
four applications are listed (a combination approval, e.g. Inluriyo with Verzenio, is two). No match, no block: CBER
products (vaccines, gene therapies) are not in Drugs@FDA, and the newest approvals reach openFDA days later; the
block appears on the first run after they do. Facts only: the FDA's own record, copied. No reading of the label.

    python link_fda_label_record.py        (tests/test_fda_label_record.py recomputes every block from the files)
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
APPR = os.path.join(HERE, "_fda_approvals_months.json")
B, E = "<!--LABELREC:BEGIN-->", "<!--LABELREC:END-->"
ANCHOR = "<!--SITELINKS:BEGIN-->"
WINDOW_DAYS = 3
MAX_APPS = 4
MON = ["", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
       "November", "December"]
LINK = 'style="color:#e3ba5e"'
STOP = {"with", "plus", "tablet", "tablets", "injection", "capsule", "capsules", "solution", "cream", "combination",
        "therapy", "patients", "adult", "adults", "children", "pediatric", "paediatric", "extended", "release",
        "delayed", "sodium", "hydrochloride", "disease", "cancer", "treatment", "phase", "study", "trial", "chronic",
        "first", "line", "previously", "untreated", "advanced", "metastatic", "positive", "negative", "mutant",
        "weekly", "daily", "dose", "doses", "acute", "severe", "primary", "secondary", "prevention", "infection",
        "infections", "syndrome", "ophthalmic", "topical", "subcutaneous", "intravenous", "autoinjector"}


def esc(s):
    return html.escape(str(s or ""), quote=True)


def pretty(d):
    d = dt.date.fromisoformat(d) if isinstance(d, str) else d
    return f"{MON[d.month]} {d.day}, {d.year}"


def https(u):
    return re.sub(r"^http://", "https://", str(u or ""))


def load_rows():
    s = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8", errors="replace").read()
    return json.loads(s[s.index("["):s.rindex("]") + 1])


def load_items():
    if not os.path.exists(APPR):
        return [], ""
    c = json.load(io.open(APPR, encoding="utf-8"))
    items = [x for v in c.values() for x in (v.get("items") or [])]
    fetched = max((v.get("fetched") or "" for v in c.values()), default="")
    return items, fetched


def page_row(slug, rows, byurl):
    """The Approved dataset row a /fda-decision page stands for, or None."""
    rs = [r for r in byurl.get(slug, []) if r.get("oc") == "Approved"]
    if rs:
        return rs[0]
    m = re.match(r"(.+)-(\d{4}-\d{2}-\d{2})$", slug)
    if not m:
        return None
    rs = [r for r in rows if r.get("oc") == "Approved" and r.get("t") == m.group(1)
          and m.group(2) in (str(r.get("dcd") or ""), str(r.get("d") or ""))]
    return rs[0] if rs else None


RE_DRUG_KV = re.compile(r'<div class="kv"><span>Drug(?: / candidate)?</span><b>([^<]{3,160})</b>')
RE_APPNO = re.compile(r"(?:ApplNo=|appletter/\d{4}/)(\d{6})")


def page_fallback(doc, slug):
    """For a page with no dataset row (the 2025 archive): an approval page states it in its own Outcome row or h1,
    names its drug in its Drug row, and its Verified line usually names the application. Returns (row, app number)."""
    m = re.search(r"-(\d{4}-\d{2}-\d{2})$", slug)
    approved = ('class="g">Approved</span>' in doc or
                re.search(r"Outcome</span><b><span class=\"badge app\">&#10003; Approved", doc) is not None)
    dm = RE_DRUG_KV.search(doc)
    if not (m and approved and dm):
        return None, None
    v = re.search(r"<!--VERIFIED:BEGIN-->(.*?)<!--VERIFIED:END-->", doc, re.S)
    nums = sorted(set(RE_APPNO.findall(v.group(1)))) if v else []
    return {"name": html.unescape(dm.group(1)), "_d": {}, "dcd": m.group(1), "oc": "Approved"}, (
        nums[0] if len(nums) == 1 else None)


def name_words(r):
    d = r.get("_d") or {}
    t = " ".join(str(x) for x in (d.get("brand"), d.get("inn"), re.split(r" - ", str(r.get("name") or ""))[0]) if x)
    return {w.lower() for w in re.findall(r"[A-Za-z][A-Za-z\-]{4,}", t)} - STOP


def decision_day(r, slug):
    for v in (r.get("dcd"), r.get("d")):
        try:
            return dt.date.fromisoformat(str(v)[:10])
        except ValueError:
            continue
    m = re.search(r"(\d{4}-\d{2}-\d{2})$", slug)
    return dt.date.fromisoformat(m.group(1)) if m else None


def matches(r, slug, items):
    """Drugs@FDA approvals that are this page's: within WINDOW_DAYS of its decision day and sharing a name word."""
    day, words = decision_day(r, slug), name_words(r)
    if not day or not words:
        return []
    out, seen = [], set()
    for x in sorted(items, key=lambda x: (x["date"], x["app"], x["sub"])):
        if abs((dt.date.fromisoformat(x["date"]) - day).days) > WINDOW_DAYS:
            continue
        hay = f'{x.get("brand", "")} {x.get("generic", "")}'.lower()
        if not any(w in hay for w in words):
            continue
        key = (x["app"], x["sub"])
        if key not in seen:
            seen.add(key)
            out.append(x)
    # Only the approvals nearest the page's day: BMY-2025-04-08 and BMY-2025-04-11 are two Opdivo supplements three
    # days apart, and each page is one of them, not both.
    if out:
        near = min(abs((dt.date.fromisoformat(x["date"]) - day).days) for x in out)
        out = [x for x in out if abs((dt.date.fromisoformat(x["date"]) - day).days) == near]
    return out[:MAX_APPS]


def app_label(app):
    m = re.match(r"(NDA|BLA)(\d{6})$", app)
    return f"{m.group(1)} {m.group(2)}" if m else app


def overview(app):
    n = re.sub(r"\D", "", app)
    return f"https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm?event=overview.process&amp;ApplNo={n}"


def products_text(prods):
    bits = []
    for p in prods or []:
        b = ", ".join(x for x in (p.get("form", "").lower(), p.get("route", "").lower(), p.get("strength", "")) if x)
        if b:
            bits.append(b)
    return "; ".join(bits)


def shown_brand(x, words):
    """Drugs@FDA's brand for the application. For an original application it is that application's own product. For a
    supplement it is shown only when every word of it is one of the page's own name words. openFDA
    labels an application with the first brand on its listing, which can be another product (NDA 213051, the
    Rybelsus application, is listed as Ozempic; NDA 212097, Gvoke VialDx's, as Gvoke Hypopen): the application number
    and generic then stand alone."""
    b = str(x.get("brand") or "")
    bw = set(re.findall(r"[a-z][a-z\-]{3,}", b.lower()))
    if x.get("kind") == "new application":
        return b                      # an original application's own product: the brand is the new one
    return b if bw and bw <= set(words) else ""


def block(apps, fetched, words=frozenset()):
    groups = []
    for x in apps:
        kind = (f'original application ({esc(x["class"])})' if x["kind"] == "new application" and x.get("class")
                else ("original application" if x["kind"] == "new application" else "efficacy supplement (a new use)"))
        pr = str(x.get("priority") or "").lower()
        act = f'Approved {pretty(x["date"])}, {kind}' + (f", {esc(pr)} review" if pr in ("priority", "standard") else "")
        docs = []
        if x.get("letter"):
            docs.append(f'<a href="{esc(https(x["letter"]))}" rel="noopener" {LINK}>approval letter (PDF)</a>')
        if x.get("label"):
            docs.append(f'<a href="{esc(https(x["label"]))}" rel="noopener" {LINK}>approved label (PDF)</a>')
        docs.append(f'<a href="{overview(x["app"])}" rel="noopener" {LINK}>Drugs@FDA entry</a>')
        b = shown_brand(x, words)
        nm = (esc(b) + (f' ({esc(x["generic"])})' if x.get("generic") else "")) if b else esc(x.get("generic") or "")
        rows_ = [("Application", app_label(x["app"]) + (f", {nm}" if nm else "")), ("FDA action", act)]
        pt = products_text(x.get("products"))
        if pt:
            rows_.append(("Products listed", esc(pt)))
        rows_.append(("FDA documents", " &middot; ".join(docs)))
        groups.append("".join(f'<div class="kv" style="display:flex;justify-content:space-between;gap:12px;'
                              f'font-size:14px;padding:7px 0;border-bottom:1px solid #112b48"><span style="color:#a7bcd9">'
                              f'{k}</span><b style="text-align:right">{v}</b></div>' for k, v in rows_))
    asof = f", read {pretty(fetched)}" if re.match(r"\d{4}-\d{2}-\d{2}$", fetched or "") else ""
    return (B + '<div class="card" data-labelrec style="background:#0c1d38;border:1px solid #1a3358;border-radius:12px;'
            'padding:14px 16px;margin:18px 0"><h2 style="font-size:17px;margin:0 0 6px;color:#e3ba5e">FDA label record '
            '(Drugs@FDA)</h2>' + '<div style="height:10px"></div>'.join(groups)
            + f'<p class="note" style="font-size:12px;color:#94a9c9;margin:8px 0 0">From Drugs@FDA, the FDA&#x27;s database '
            f'of approved drugs{asof}. The approved label is the full prescribing information: indication, dosing and '
            f'warnings.' + (' Products are those Drugs@FDA lists as marketed on the application.'
                            if any(x.get("products") for x in apps) else '') + '</p></div>' + E)


def main():
    rows = load_rows()
    byurl = {}
    for r in rows:
        u = str(r.get("url") or "")
        if u.startswith("/fda-decision/"):
            byurl.setdefault(u.rsplit("/", 1)[-1], []).append(r)
    items, fetched = load_items()
    wrote = removed = 0
    for p in sorted(glob.glob(os.path.join(SITE, "fda-decision", "*", "index.html"))):
        slug = os.path.basename(os.path.dirname(p))
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        new = re.sub(re.escape(B) + r".*?" + re.escape(E), "", doc, flags=re.S)
        r, num = page_row(slug, rows, byurl), None
        if not r:
            r, num = page_fallback(new, slug)
        apps = matches(r, slug, items) if r else []
        if num:
            # the page names its own application: only that application's approvals are its own
            apps = [x for x in apps if re.sub(r"\D", "", x["app"]) == num]
        if apps and ANCHOR in new:
            new = new.replace(ANCHOR, block(apps, fetched, name_words(r)) + ANCHOR, 1)
            wrote += 1
        elif new != doc:
            removed += 1
        if new != doc:
            io.open(p, "w", encoding="utf-8").write(new)
    print(f"FDA label record: {wrote} approval page(s) carry it" + (f", {removed} stale block(s) removed" if removed else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
