# -*- coding: utf-8 -*-
"""CI guard: the BLA section of /crl/facts (build_crl_bla_approvals.py), recounted here from the two FDA files.

  * Letters: read here from the raw CRL corpus (openFDA transparency/crl), Complete Response Letters only, one per
    distinct (date, type, application numbers, text); suffixes "/S-nnn" are supplements and are not counted; a letter
    naming only "Original 2" or later is not the first original's letter. No rescission in the release may name a BLA
    (if one ever does, this guard fails and must learn the rescission rule before the page can count it).
  * Approvals: _fda_approvals_months.json (openFDA drugsfda), "new application" rows on BLAs; a row is listed only
    when the BLA's earliest original approval in the cache is ORIG-1 and is dated after the last letter.
  * The page: one row per BLA, keyed by data-bla, no unknown or missing rows; each row's product, sponsor, letter
    count, last letter date and PDF, openFDA status, approval date and FDA letter, days; the n, median, shortest and
    longest; the BLA count in the release; the two left-out counts; the "Unapproved" count; no forecast words.

PLANT=1 drops one approval from the recount and must FAIL; PLANT=2 moves one letter a day later and must FAIL.

    python tests/test_crl_bla_approvals.py      (fix: python build_crl_facts.py, then build_crl_bla_approvals.py)
"""
import datetime as dt
import glob
import html
import io
import json
import os
import re
import statistics
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FACTS = os.path.join(HERE, "pdufa_site_src", "crl", "facts", "index.html")
CACHE = os.path.join(HERE, "_fda_approvals_months.json")
CITED = os.path.join(HERE, "_crl_bla_cited_letters.json")
MONTHS = ["", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]
BAD = re.compile(r"\b(probabilit|odds\b|chances?\b|likel[yi]|predict|forecast|because of|caused?\b|due to|led to"
                 r"|reject|reason|fail|deficien|signal|will be approved)", re.I)
PLANT = os.environ.get("PLANT", "")


def corpus_path():
    c = sorted(glob.glob(os.path.join(HERE, "CRL_corpus_openFDA_*.json")))
    return c[-1] if c else None


def day(s):
    m = re.match(r"(\d{2})/(\d{2})/(\d{4})$", str(s or "").strip())
    return dt.date(int(m.group(3)), int(m.group(1)), int(m.group(2))) if m else None


def pretty(d):
    return f"{MONTHS[d.month]} {d.day}, {d.year}"


def expected():
    raw = json.load(io.open(corpus_path(), encoding="utf-8"))
    recs, last_updated = raw["results"], raw["meta"]["last_updated"]
    probs = []
    for r in recs:
        if "RESCIND" in str(r.get("letter_type") or "").upper() and any(
                re.match(r"\s*BLA?\s", a) for a in r.get("application_number") or []):
            probs.append(f"a rescission names a BLA ({r.get('application_number')}); teach this guard the rule first")
    seen, by = set(), {}
    for r in recs:
        d = day(r.get("letter_date"))
        if not d or r.get("letter_type") != "COMPLETE RESPONSE":
            continue
        k = (d, tuple(sorted(str(x).strip() for x in r.get("application_number") or [])),
             re.sub(r"\s+", " ", str(r.get("text") or "")).strip().lower())
        if k in seen:
            continue
        seen.add(k)
        firsts, any_orig = set(), set()
        for a in r.get("application_number") or []:
            m = re.match(r"\s*BLA?\s*0*(\d+)\s*(?:/\s*(.*))?$", a)
            if not m:
                continue
            sfx = (m.group(2) or "").strip()
            if re.match(r"S-?\d", sfx):
                continue
            n = int(m.group(1))
            any_orig.add(n)
            if not re.match(r"Original\s*[2-9]", sfx, re.I):
                firsts.add(n)
        fn = str(r.get("file_name") or "").strip()
        for n in any_orig:
            by.setdefault(n, {"all": 0, "first": []})
            by[n]["all"] += 1
            if n in firsts:
                by[n]["first"].append({"date": d, "file": fn, "status": str(r.get("approval_status") or "")})
    cache = json.load(io.open(CACHE, encoding="utf-8"))
    reads = sorted({str(v.get("fetched") or "")[:10] for v in cache.values()} - {""})
    appr = {}
    for month in sorted(cache):
        for it in cache[month].get("items") or []:
            m = re.match(r"BLA0*(\d+)$", str(it.get("app") or ""))
            if m and it.get("kind") == "new application" and it.get("date"):
                appr.setdefault(int(m.group(1)), []).append(it)
    for v in appr.values():
        v.sort(key=lambda x: x["date"])
    if PLANT == "2":   # a listed BLA: one whose first original approval in the cache is ORIG-1
        n0 = next(n for n in sorted(by) if n in appr and by[n]["first"] and appr[n][0].get("sub") == "ORIG-1")
        for L in by[n0]["first"]:
            L["date"] += dt.timedelta(days=1)
    if PLANT == "1":
        appr.pop(sorted(appr)[0], None)
        for n in list(appr):
            if n in by:
                appr.pop(n)
                break
    rows, before, later = {}, 0, 0
    for n, v in by.items():
        if n not in appr or not v["first"]:
            continue
        last = max(v["first"], key=lambda x: x["date"])
        a = appr[n][0]
        ad = dt.date.fromisoformat(a["date"])
        if ad <= last["date"]:
            before += 1
            continue
        if a.get("sub") != "ORIG-1":
            later += 1
            continue
        rows[n] = {"product": a.get("brand") or "", "sponsor": a.get("sponsor") or "", "letters": len(v["first"]),
                   "last": pretty(last["date"]), "pdf": "https://download.open.fda.gov/crl/" + fn_q(last["file"]),
                   "status": last["status"], "appr": pretty(ad), "letter": a.get("letter") or "",
                   "days": (ad - last["date"]).days, "ad": ad}
    return rows, {"n_bla": len(by), "before": before, "later": later, "reads": reads, "lu": last_updated}, probs


def fn_q(fn):
    from urllib.parse import quote
    return quote(fn, safe="/-_.~")


def main():
    probs = []
    if not corpus_path() or not os.path.exists(FACTS) or not os.path.exists(CACHE):
        print("FAIL test_crl_bla_approvals: corpus, cache or /crl/facts missing")
        return 1
    rows, f, p0 = expected()
    probs += p0
    doc = io.open(FACTS, encoding="utf-8").read()
    m = re.search(r"<!--BLAAPPR:BEGIN-->(.*?)<!--BLAAPPR:END-->", doc, re.S)
    if not m:
        print("FAIL test_crl_bla_approvals: no BLA section on /crl/facts; fix: python build_crl_bla_approvals.py")
        return 1
    sec = m.group(1)
    # it sits right after the NDA section
    nda = doc.find("<h2>From the last released CRL to approval (NDAs)</h2>")
    if not (0 <= nda < m.start()) or "<h2>" in re.sub(r"<!--BLAAPPR.*", "", doc[nda + 10:m.start()], flags=re.S):
        probs.append("the BLA section is not directly after the NDA section")
    got = {}
    for tr in re.findall(r'<tr data-bla="(\d+)">(.*?)</tr>', sec, re.S):
        tds = re.findall(r"<td[^>]*>(.*?)</td>", tr[1], re.S)
        if len(tds) != 9:
            probs.append(f"BLA {tr[0]}: {len(tds)} cells")
            continue
        n = int(tr[0])
        if n in got:
            probs.append(f"BLA {n} listed twice")
        txt = lambda s: html.unescape(re.sub(r"<[^>]+>", "", s)).strip()  # noqa: E731
        href = lambda s: html.unescape((re.search(r'href="([^"]+)"', s) or [None, ""])[1])  # noqa: E731
        got[n] = {"num": txt(tds[0]), "product": txt(tds[1]), "sponsor": txt(tds[2]), "letters": txt(tds[3]),
                  "last": txt(tds[4]), "pdf": href(tds[4]), "status": txt(tds[5]), "appr": txt(tds[6]),
                  "letter": href(tds[6]), "cited": txt(tds[7]), "days": txt(tds[8])}
    for n in sorted(set(rows) - set(got)):
        probs.append(f"BLA {n} missing from the page ({rows[n]['product']})")
    for n in sorted(set(got) - set(rows)):
        probs.append(f"BLA {n} on the page but not in the recount")
    cj = json.load(io.open(CITED, encoding="utf-8")) if os.path.exists(CITED) else {"letters": {}}
    cit = {int(k): (dt.date.fromisoformat(v) if v else None) for k, v in cj["letters"].items()}
    for n in sorted(set(rows) & set(got)):
        e, g = rows[n], got[n]
        want = {"num": f"{n:06d}", "product": e["product"], "sponsor": e["sponsor"], "letters": str(e["letters"]),
                "last": e["last"], "pdf": e["pdf"], "status": e["status"], "appr": e["appr"], "letter": e["letter"],
                "cited": pretty(cit[n]) if cit.get(n) else "not read", "days": str(e["days"])}
        for k, v in want.items():
            if g[k] != v:
                probs.append(f"BLA {n} {k}: page {g[k]!r} != {v!r}")
    order = [int(x) for x in re.findall(r'<tr data-bla="(\d+)">', sec)]
    if order != [n for n in sorted(rows, key=lambda n: (rows[n]["ad"], n))]:
        probs.append("rows are not in approval-date order")
    if rows:
        days = sorted(r["days"] for r in rows.values())
        plain = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", sec)))
        need = [f"for {len(rows)} BLAs that have a Complete Response Letter in the release dated before it",
                f"median {statistics.median(days):g}, shortest {days[0]}, longest {days[-1]}.",
                f"read {' and '.join(f['reads'])})",
                f"The release holds original-application CRLs for {f['n_bla']} BLAs."]
        if f["before"]:
            need.append(f" {f['before']} more BLA{'s' if f['before'] != 1 else ''} with a Drugs@FDA original approval dated on or before")
        if f["later"]:
            need.append(f" {f['later']} more {'are' if f['later'] != 1 else 'is'} left out because the approval read is a second original")
        stale = sum(1 for r in rows.values() if r["status"] == "Unapproved" and r["ad"].isoformat() < f["lu"])
        if stale:
            need.append(f'labels {stale} of these {len(rows)} letters "Unapproved"; Drugs@FDA dates each of those '
                        f"approvals before openFDA's last update ({f['lu']}).")
        read = [n for n in rows if cit.get(n)]
        same = [n for n in read if pretty(cit[n]) == rows[n]["last"]]
        if read:
            need.append(f"{len(read)} of these {len(rows)} approval letters were read on {cj['read_on']}, and for "
                        f"{len(same)} of them the letter named is the last one in the release.")
        for n in sorted(set(read) - set(same)):
            need.append(f"BLA {n:06d} ({rows[n]['product']}) answers a letter dated {pretty(cit[n])}, which is not in the "
                        f"release, so its {rows[n]['days']} days run from an earlier released letter.")
        for s in need:
            if s not in plain:
                probs.append(f"text missing: {s!r}")
        if BAD.search(plain):
            probs.append(f"forecast or reason word: {BAD.search(plain).group(0)!r}")
    if probs:
        print(f"FAIL test_crl_bla_approvals: {len(probs)} problem(s); fix: python build_crl_facts.py && "
              f"python build_crl_bla_approvals.py")
        for p in probs[:25]:
            print("  " + p)
        return 1
    print(f"ok test_crl_bla_approvals: {len(rows)} BLAs recounted from the CRL release and Drugs@FDA")
    return 0


if __name__ == "__main__":
    sys.exit(main())
