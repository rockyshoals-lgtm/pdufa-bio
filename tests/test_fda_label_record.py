# -*- coding: utf-8 -*-
"""CI guard: the "FDA label record (Drugs@FDA)" block on each /fda-decision page is the FDA's own record of that action.

WHY (2026-11-27, David: "get 90% of all AI citations"): on single-drug approval queries Copilot cited the FDA press
release and trade press, which carry the application, the dosage form and the label; our approval pages did not.
link_fda_label_record.py now writes those facts from the Drugs@FDA month cache (_fda_approvals_months.json). A wrong
application on a decision page is worse than none, so this test holds every block to the cache:

  1. every page's block is exactly what link_fda_label_record.py writes from the current files (no stale block, no
     block on a CRL page, none missing where a match exists);
  2. independently of that code: each application in a block has an approval in the cache within three days of the
     page's date, and its approval letter and label links are the ones Drugs@FDA attaches to that approval;
  3. no block on a page whose outcome is not an approval.

Plants (each must FAIL): PLANT=app (a block's application number is changed), PLANT=letter (a block links another
application's letter), PLANT=crl (a block is put on a CRL page).

    python tests/test_fda_label_record.py
"""
import datetime as dt
import glob
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import link_fda_label_record as L  # noqa: E402

RE_BLOCK = re.compile(re.escape(L.B) + r".*?" + re.escape(L.E), re.S)


def pages():
    out = {}
    for p in sorted(glob.glob(os.path.join(L.SITE, "fda-decision", "*", "index.html"))):
        out[os.path.basename(os.path.dirname(p))] = io.open(p, encoding="utf-8", errors="replace").read()
    plant = os.environ.get("PLANT", "")
    if plant:
        with_block = [s for s, d in out.items() if L.B in d]
        s = with_block[0]
        if plant == "app":
            out[s] = re.sub(r"(Application</span><b[^>]*>(?:NDA|BLA) )(\d{6})", lambda m: m.group(1) + "999999", out[s], 1)
        elif plant == "letter":
            out[s] = re.sub(r"(appletter/\d{4}/)(\d{6})", lambda m: m.group(1) + "123456", out[s], 1)
        elif plant == "crl":
            crl = next(k for k, d in out.items() if L.B not in d and "CRL" in d and "Approved" not in d)
            out[crl] = out[crl].replace(L.ANCHOR, RE_BLOCK.search(out[s]).group(0) + L.ANCHOR, 1)
    return out


def test_fda_label_record():
    rows = L.load_rows()
    byurl = {}
    for r in rows:
        u = str(r.get("url") or "")
        if u.startswith("/fda-decision/"):
            byurl.setdefault(u.rsplit("/", 1)[-1], []).append(r)
    items, fetched = L.load_items()
    by_app = {}
    for x in items:
        by_app.setdefault(re.sub(r"\D", "", x["app"]), []).append(x)
    bad, n = [], 0
    for slug, doc in pages().items():
        got = RE_BLOCK.findall(doc)
        bare = RE_BLOCK.sub("", doc)
        r, num = L.page_row(slug, rows, byurl), None
        if not r:
            r, num = L.page_fallback(bare, slug)
        apps = L.matches(r, slug, items) if r else []
        if num:
            apps = [x for x in apps if re.sub(r"\D", "", x["app"]) == num]
        want = [L.block(apps, fetched, L.name_words(r))] if apps and L.ANCHOR in bare else []
        if got != want:
            bad.append(f"{slug}: block differs from link_fda_label_record.py's ({len(got)} on page, {len(want)} expected)")
            continue
        if not got:
            continue
        n += 1
        if not r or r.get("oc") != "Approved":
            bad.append(f"{slug}: block on a page that is not an approval")
        m = re.search(r"-(\d{4}-\d{2}-\d{2})$", slug)
        day = L.decision_day(r, slug) if r else dt.date.fromisoformat(m.group(1))
        for grp in re.split(r'<div style="height:10px"></div>', got[0]):
            a = re.search(r"Application</span><b[^>]*>(?:NDA|BLA) (\d{6})", grp)
            if not a:
                bad.append(f"{slug}: a block group names no application")
                continue
            appno = a.group(1)
            near = [x for x in by_app.get(appno, [])
                    if abs((dt.date.fromisoformat(x["date"]) - day).days) <= L.WINDOW_DAYS]
            if not near:
                bad.append(f"{slug}: application {appno} has no Drugs@FDA approval within {L.WINDOW_DAYS} days of {day}")
            # The FDA sometimes files one letter for several applications under the lead one (Mavyret's NDA 215110
            # letter is 209394's file), so a link is checked against the letter Drugs@FDA attaches to THIS
            # application's approval, not against the number in its file name.
            for kind, rx, key in (("letter", r'href="([^"]*/appletter/[^"]+)"', "letter"),
                                  ("label", r'href="([^"]*/label/[^"]+)"', "label")):
                for hit in re.findall(rx, grp):
                    if hit not in {L.https(x.get(key)) for x in near}:
                        bad.append(f"{slug}: {kind} link {hit} is not the one Drugs@FDA attaches to {appno}'s approval")
    assert n >= 50, f"only {n} approval pages carry the FDA label record; expected 50 or more"
    assert not bad, "FDA label record blocks disagree with Drugs@FDA:\n  " + "\n  ".join(bad[:40])


if __name__ == "__main__":
    test_fda_label_record()
    print("OK")
