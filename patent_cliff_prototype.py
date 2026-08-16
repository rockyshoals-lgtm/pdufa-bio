# -*- coding: utf-8 -*-
"""patent_cliff_prototype.py -- loss-of-exclusivity aggregation from the FDA Orange Book.

Built and verified 2026-08-12. Produces: which companies have drugs losing exclusivity,
which drugs, and when -- from a free, authoritative, citable source.

WHY THE ORANGE BOOK AND NOT PATENTSVIEW
---------------------------------------
PatentsView tells you about patents. It does NOT tell you which patent covers which drug.
Inferring drug<->patent linkage from assignee names or titles produces wrong cliffs, and a
wrong exclusivity claim is materially worse than a wrong date. The FDA Orange Book IS the
statutory drug<->patent linkage (small molecules); the Purple Book is its biologics
counterpart. Use PatentsView as an ENRICHMENT layer (claims, family, continuations), never
as the spine.

WHAT THIS COMPUTES, PRECISELY
-----------------------------
    LOE = max(last unexpired listed patent, last regulatory exclusivity)

That is the "earliest date on which no listed patent or exclusivity blocks generic entry."
It is NOT "the day the drug goes generic." Deliberately NOT modelled, and which must be
disclosed on-page rather than guessed:

  * Patent term extension / Hatch-Waxman restoration
  * Paragraph IV litigation and settlements (often the real entry date; not in this file)
  * Authorised generics and at-risk launches
  * Biologics -- those live in the Purple Book, not here

Delisted patents are excluded. Brand (Appl_Type == 'N') applications only.

DATA
----
    https://www.fda.gov/media/76860/download?attachment   (~1 MB zip, refreshed monthly)
    patent.txt       Appl_No, Patent_No, Patent_Expire_Date_Text, Drug_Substance_Flag,
                     Patent_Use_Code, Delist_Flag
    exclusivity.txt  Appl_No, Exclusivity_Code, Exclusivity_Date
    products.txt     Ingredient, Trade_Name, Applicant_Full_Name, Approval_Date, TE_Code
    Join key: Appl_Type + Appl_No + Product_No.   Delimiter is '~'.

KNOWN GAP
---------
The Orange Book has NO therapeutic-area field. For the "what family (cancer, diabetes)"
cut, join ingredient -> our own TA tags, or use ATC via the free RxNorm/RxClass API.

    python patent_cliff_prototype.py [--through 2031] [--csv out.csv]
"""
import argparse, collections, csv, datetime as dt, io, os, sys, urllib.request, zipfile

OB_URL = "https://www.fda.gov/media/76860/download?attachment"
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_orange_book")


def fetch(refresh=False):
    """Download + unzip the Orange Book, cached locally."""
    need = refresh or not all(
        os.path.exists(os.path.join(CACHE, f))
        for f in ("patent.txt", "exclusivity.txt", "products.txt"))
    if need:
        os.makedirs(CACHE, exist_ok=True)
        req = urllib.request.Request(OB_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=120) as r:
            blob = r.read()
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            z.extractall(CACHE)
        print(f"  downloaded Orange Book -> {CACHE}")
    return CACHE


def load(name):
    with open(os.path.join(CACHE, name), encoding="utf-8", errors="replace") as f:
        return list(csv.DictReader(f, delimiter="~"))


def parse_date(s):
    s = (s or "").strip()
    for fmt in ("%b %d, %Y", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None


def build(through_year):
    patents, excl_rows, products = load("patent.txt"), load("exclusivity.txt"), load("products.txt")

    prod_by_key = {(r["Appl_Type"], r["Appl_No"], r["Product_No"]): r for r in products}

    # latest unexpired listed patent per brand application
    latest = {}
    for r in patents:
        if r["Appl_Type"] != "N":
            continue
        if (r.get("Delist_Flag") or "").strip():          # delisted -> not blocking
            continue
        d = parse_date(r["Patent_Expire_Date_Text"])
        if not d:
            continue
        k = (r["Appl_Type"], r["Appl_No"])
        e = latest.setdefault(k, {"last": d, "n": 0, "substance": False})
        e["n"] += 1
        if d > e["last"]:
            e["last"] = d
        if (r.get("Drug_Substance_Flag") or "").strip() == "Y":
            e["substance"] = True

    exclusivity = collections.defaultdict(list)
    for r in excl_rows:
        d = parse_date(r["Exclusivity_Date"])
        if d:
            exclusivity[(r["Appl_Type"], r["Appl_No"])].append(d)

    out = []
    for k, v in latest.items():
        p = prod_by_key.get((k[0], k[1], "001")) or next(
            (prod_by_key[x] for x in prod_by_key if x[0] == k[0] and x[1] == k[1]), None)
        if not p:
            continue
        loe = max([v["last"]] + exclusivity.get(k, []))
        out.append({
            "loe": loe,
            "brand": (p.get("Trade_Name") or "").strip(),
            "ingredient": (p.get("Ingredient") or "").strip(),
            "company": (p.get("Applicant_Full_Name") or p.get("Applicant") or "").strip(),
            "appl_no": k[1],
            "n_patents": v["n"],
            "substance_patent": v["substance"],
            "approval_date": (p.get("Approval_Date") or "").strip(),
        })
    out.sort(key=lambda r: r["loe"])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--through", type=int, default=2031)
    ap.add_argument("--csv")
    ap.add_argument("--refresh", action="store_true")
    a = ap.parse_args()

    fetch(a.refresh)
    rows = build(a.through)
    today = dt.date.today()
    window = [r for r in rows if today <= r["loe"] <= dt.date(a.through, 12, 31)]

    print(f"\nBrand NDAs with unexpired listed patents : {len(rows)}")
    print(f"Losing exclusivity {today.year}-{a.through}            : {len(window)}\n")

    print("CLIFFS BY YEAR")
    by_year = collections.Counter(r["loe"].year for r in window)
    for y in sorted(by_year):
        print(f"   {y}: {by_year[y]:4}")

    print("\nTOP COMPANIES")
    for c, n in collections.Counter(r["company"] for r in window).most_common(15):
        print(f"   {n:3}  {c[:60]}")

    print("\nNEAREST CLIFFS")
    print(f"   {'LOE':<13}{'Brand':<22}{'Ingredient':<30}{'Company':<32}#pat")
    for r in window[:20]:
        print(f"   {r['loe'].isoformat():<13}{r['brand'][:20]:<22}"
              f"{r['ingredient'][:28]:<30}{r['company'][:30]:<32}{r['n_patents']}")

    if a.csv:
        with open(a.csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(window[0].keys()))
            w.writeheader()
            w.writerows(window)
        print(f"\nwrote {len(window)} rows -> {a.csv}")

    print("\nNOTE: LOE = max(last listed patent, last exclusivity). This is the earliest date")
    print("no listed patent or exclusivity blocks generic entry -- NOT the date a generic")
    print("launches. PTE, Paragraph IV settlements and authorised generics are not modelled")
    print("and must be disclosed as such on any published page.")


if __name__ == "__main__":
    sys.exit(main())
