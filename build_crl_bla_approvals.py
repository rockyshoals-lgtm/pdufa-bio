# -*- coding: utf-8 -*-
"""build_crl_bla_approvals.py -- /crl/facts: BLAs from the last released CRL to a Drugs@FDA approval.

David, 2026-11-22: "continue to build the moat, row the boat." /crl/facts counts the days from the last released
Complete Response Letter to approval for NDAs only, because it reads approvals from the Orange Book, and the Orange
Book leaves out BLAs. Drugs@FDA lists BLA approvals, and this site already reads every Drugs@FDA original approval
since January 2025 into _fda_approvals_months.json (build_fda_approvals_months.py). This script joins the two FDA
files for BLAs and writes one section into /crl/facts, between <!--BLAAPPR:BEGIN--> and <!--BLAAPPR:END-->, right
after the NDA section:

  * every original BLA with a Complete Response Letter in the release (rescinded letters left out) whose first
    Drugs@FDA original approval since January 1, 2025 is dated after the last such letter, on the same application
    number: product, sponsor, released letters, the last letter (PDF), openFDA's status, the approval (FDA letter), days
  * the median, shortest and longest of those days, with n, and the window stated (only approvals since January 2025)

It runs after build_fda_approvals_months.py refreshes the cache, in the same workflow step, so the section and
tests/test_crl_bla_approvals.py read one cache. build_crl_facts.py writes the page earlier in the run; this script
only adds its section.

FACTS ONLY: dates and counts from two FDA files. No rates, no view on any application.

    python build_crl_bla_approvals.py
"""
import datetime as dt
import html
import io
import json
import os
import re
import statistics
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from build_crl_facts import is_supplement, load_letters, pretty  # noqa: E402

CACHE = os.path.join(HERE, "_fda_approvals_months.json")
FACTS = os.path.join(HERE, "pdufa_site_src", "crl", "facts", "index.html")
BS, BE = "<!--BLAAPPR:BEGIN-->", "<!--BLAAPPR:END-->"
NDA_H2 = "<h2>From the last released CRL to approval (NDAs)</h2>"
NEW = "new application"
CITED = os.path.join(HERE, "_crl_bla_cited_letters.json")   # hand-checked: the action letter each approval answers
esc = lambda s: html.escape(str(s or ""), quote=True)  # noqa: E731


def approvals():
    """BLA number -> every original approval Drugs@FDA lists since January 2025 (date order); and the read dates."""
    d = json.load(io.open(CACHE, encoding="utf-8"))
    out, reads = {}, set()
    for month in sorted(d):
        reads.add(str(d[month].get("fetched") or "")[:10])
        for it in d[month].get("items") or []:
            m = re.match(r"BLA0*(\d+)$", str(it.get("app") or ""))
            if not m or it.get("kind") != NEW or not it.get("date"):
                continue
            out.setdefault(int(m.group(1)), []).append(dict(it, day=dt.date.fromisoformat(it["date"])))
    for v in out.values():
        v.sort(key=lambda x: x["day"])
    return out, sorted(r for r in reads if r), min(d) if d else ""


def rows():
    """(rows, facts): one row per original BLA with a released CRL and a later Drugs@FDA original approval."""
    R = load_letters()
    by_bla = {}
    for L in R["counted"]:
        for t, n, sfx in L["apps"]:
            if t == "BLA" and not is_supplement(sfx) and L not in by_bla.setdefault(n, []):
                by_bla[n].append(L)
    appr, reads, first_month = approvals()
    out, before, later_orig = [], 0, 0
    for n, ls in sorted(by_bla.items()):
        hits = appr.get(n) or []
        if not hits:
            continue
        # a letter naming only a second or later original submission ("BLA 761xxx/Original 2") is about another
        # submission than the first original's approval, so it is not this row's letter
        ls = [L for L in ls if any(t == "BLA" and m == n and not re.match(r"Original\s*[2-9]", s_, re.I)
                                   for t, m, s_ in L["apps"])]
        if not ls:
            continue
        last = max(ls, key=lambda x: x["date"])
        if hits[0]["day"] <= last["date"]:
            before += 1   # Drugs@FDA lists an original approval on this BLA on or before the letter
            continue
        a = hits[0]
        if a.get("sub") != "ORIG-1":
            # red team 2026-11-23: BLA 761338's approval here is ORIG-2 (April 2025); its first original may have been
            # approved before January 2025, which this cache does not read, so the days would not be letter-to-approval
            later_orig += 1
            continue
        out.append({"bla": n, "letters": len(ls), "last": last, "appr": a, "days": (a["day"] - last["date"]).days})
    out.sort(key=lambda r: (r["appr"]["day"], r["bla"]))
    voided_bla = any(t == "BLA" for L in R["crl"] if id(L) in R["voided"] for t, _, _ in L["apps"])
    return out, {"n_bla": len(by_bla), "before": before, "later_orig": later_orig, "reads": reads,
                 "first_month": first_month, "last_updated": R["last_updated"], "voided": voided_bla}


def cited():
    """BLA -> date of the action letter its approval letter answers (None = not read); and the day it was read."""
    if not os.path.exists(CITED):
        return {}, ""
    d = json.load(io.open(CITED, encoding="utf-8"))
    return ({int(k): (dt.date.fromisoformat(v) if v else None) for k, v in (d.get("letters") or {}).items()},
            str(d.get("read_on") or ""))


def section(out, f):
    cit, cit_on = cited()
    read = [r for r in out if cit.get(r["bla"])]
    same = [r for r in read if cit[r["bla"]] == r["last"]["date"]]
    other = [r for r in read if cit[r["bla"]] != r["last"]["date"]]
    days = sorted(r["days"] for r in out)
    med = statistics.median(days)
    lu = f["last_updated"]
    stale = [r for r in out if r["last"]["status"] == "Unapproved" and lu and r["appr"]["day"].isoformat() < lu]
    reads = " and ".join(f["reads"])
    B = [BS, '<h2>From the last released CRL to approval (BLAs approved since January 2025)</h2>',
         f'<p class="sub">The Orange Book leaves out BLAs, so the NDA count above has none. Drugs@FDA (openFDA drugsfda, '
         f'read {esc(reads)}) lists the approval of the first original submission (ORIG-1), dated January 1, 2025 or later, for '
         f'<b>{len(out)}</b> BLAs that have a Complete Response Letter in the release dated before it, on the same '
         f'application number'
         + (' (rescinded letters left out)' if f["voided"] else '') +
         f'. Days from the last such letter to that approval: median <b>{med:g}</b>, shortest {days[0]}, longest '
         f'{days[-1]}.</p>',
         f'<p class="sub">Only approvals since January 2025 are read, so this lists those {len(out)} BLAs; it is not a '
         f'count of how long every released BLA letter took to end in an approval. The release holds original-application '
         f'CRLs for {f["n_bla"]} BLAs.'
         + (f' {f["before"]} more BLA{"s" if f["before"] != 1 else ""} with a Drugs@FDA original approval dated on or '
            f'before the last letter {"are" if f["before"] != 1 else "is"} left out.' if f["before"] else '')
         + (f' {f["later_orig"]} more {"are" if f["later_orig"] != 1 else "is"} left out because the approval read is a '
            f'second original submission (ORIG-2 or later), and the first may have been approved before January 2025.'
            if f["later_orig"] else '')
         + (f' openFDA\'s approval_status field labels {len(stale)} of these {len(out)} letters "Unapproved"; Drugs@FDA '
            f'dates each of those approvals before openFDA\'s last update ({esc(lu)}).' if stale else '') + '</p>',
         '<table><tr><th>BLA</th><th>Product (Drugs@FDA)</th><th>Sponsor</th><th>Released CRLs</th><th>Last CRL</th>'
         '<th>openFDA status</th><th>Approved</th><th>Approval answers the FDA letter of</th><th>Days</th></tr>']
    for r in out:
        L, a = r["last"], r["appr"]
        last = (f'<a href="{esc(L["url"])}" rel="noopener">{esc(pretty(L["date"]))}</a>' if L["url"]
                else esc(pretty(L["date"])))
        appd = (f'<a href="{esc(a["letter"])}" rel="noopener">{esc(pretty(a["day"]))}</a>' if a.get("letter")
                else esc(pretty(a["day"])))
        c = cit.get(r["bla"])
        B.append(f'<tr data-bla="{r["bla"]}"><td class="dt">{r["bla"]:06d}</td><td>{esc(a.get("brand") or "")}</td>'
                 f'<td>{esc(a.get("sponsor") or "")}</td><td>{r["letters"]}</td><td>{last}</td>'
                 f'<td>{esc(L["status"])}</td><td>{appd}</td><td>{esc(pretty(c)) if c else "not read"}</td>'
                 f'<td>{r["days"]}</td></tr>')
    note = ""
    if read:
        note = (f' The approval letter names the FDA action letter that the resubmission answered: {len(read)} of these '
                f'{len(out)} approval letters were read on {esc(cit_on)}, and for {len(same)} of them the letter named is '
                f'the last one in the release.')
        for r in other:
            note += (f' BLA {r["bla"]:06d} ({esc(r["appr"].get("brand") or "")}) answers a letter dated '
                     f'{esc(pretty(cit[r["bla"]]))}, which is not in the release, so its {r["days"]} days run from an '
                     f'earlier released letter.')
    B.append('</table><p class="sub">Each date links the FDA\'s own document: the letter in the CRL release, and the '
             'approval letter Drugs@FDA lists.' + note + ' Product and sponsor names are in Drugs@FDA\'s spelling, in '
             'title case.</p>' + BE)
    return "".join(B)


def main():
    if not os.path.exists(FACTS) or not os.path.exists(CACHE):
        print("crl bla approvals: /crl/facts or the Drugs@FDA cache is missing; nothing written")
        return 0
    out, f = rows()
    doc = io.open(FACTS, encoding="utf-8", errors="replace").read()
    doc2 = re.sub(re.escape(BS) + ".*?" + re.escape(BE), "", doc, flags=re.S)
    i = doc2.find(NDA_H2)
    if i < 0 or not out:
        print("crl bla approvals: no NDA section on /crl/facts or no rows; nothing written")
        return 1
    j = doc2.find("<h2>", i + len(NDA_H2))
    if j < 0:
        print("crl bla approvals: nothing after the NDA section to anchor on; nothing written")
        return 1
    doc2 = doc2[:j] + section(out, f) + doc2[j:]
    if doc2 != doc:
        io.open(FACTS, "w", encoding="utf-8").write(doc2)
    days = sorted(r["days"] for r in out)
    print(f"crl bla approvals: {len(out)} BLAs (median {statistics.median(days):g} days) of {f['n_bla']} with a released "
          f"original CRL; {f['before']} with an earlier approval left out")
    return 0


if __name__ == "__main__":
    sys.exit(main())
