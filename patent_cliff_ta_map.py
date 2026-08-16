# -*- coding: utf-8 -*-
"""patent_cliff_ta_map.py -- add a therapeutic family to each Orange Book cliff.

THE GAP THIS CLOSES
-------------------
The Orange Book has no therapeutic-area field, so "which companies have patents falling
off, and in what family (cancer, diabetes)" cannot be answered from it alone. This joins
each brand's active ingredient to the WHO ATC classification via the free NIH RxClass API
and rolls the ATC anatomical main group up to a plain-English family.

WHY ATC AND NOT OUR OWN TAGS
----------------------------
Our catalyst TA tags only cover drugs that have had a catalyst on our calendar. The cliff
list is 427 mostly-older brands, so coverage would be poor. ATC is the WHO standard, it is
free, and RxNav is an NIH service -- a citable authority rather than our own judgement.

Rows RxClass cannot classify are labelled "Unclassified" and are NOT guessed. A gap is
better than a wrong therapeutic area on a page that names a company.

    python patent_cliff_ta_map.py [--in patent_cliff_2026_2031.csv] [--out ...]
"""
import argparse, csv, json, os, re, sys, time, urllib.parse, urllib.request

CACHE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_atc_cache.json")
API = "https://rxnav.nlm.nih.gov/REST/rxclass/class/byDrugName.json"

# ATC anatomical main group -> the family a reader would recognise
FAMILY = {
    "A": "Metabolism & digestive",   "B": "Blood",
    "C": "Cardiovascular",           "D": "Dermatology",
    "G": "Genitourinary & hormones", "H": "Hormonal",
    "J": "Infectious disease",       "L": "Cancer & immunology",
    "M": "Musculoskeletal",          "N": "Neurology & psychiatry",
    "P": "Antiparasitic",            "R": "Respiratory",
    "S": "Eye & ear",                "V": "Various",
}
# ATC level-2 refinements worth splitting out, because "Cancer & immunology" is too coarse
REFINE = {"L01": "Cancer", "L02": "Cancer", "L03": "Immunology", "L04": "Immunology",
          "A10": "Diabetes", "N05": "Psychiatry", "N06": "Neurology & psychiatry",
          "N03": "Epilepsy", "N04": "Parkinson's", "N02": "Pain"}


def load_cache():
    if os.path.exists(CACHE_PATH):
        return json.load(open(CACHE_PATH, encoding="utf-8"))
    return {}


def atc_for(name, cache, pause=0.08):
    key = name.lower().strip()
    if key in cache:
        return cache[key]
    url = f"{API}?drugName={urllib.parse.quote(key)}&relaSource=ATC"
    codes = []
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "pdufa.bio patent-cliff/1.0"})
        with urllib.request.urlopen(req, timeout=25) as r:
            data = json.load(r)
        for it in data.get("rxclassDrugInfoList", {}).get("rxclassDrugInfo", []):
            cid = (it.get("rxclassMinConceptItem") or {}).get("classId")
            if cid:
                codes.append(cid)
    except Exception:
        codes = []
    time.sleep(pause)                       # RxNav asks for <=20 req/s; we are far under
    cache[key] = codes
    return codes


def family(codes):
    """Pick the family by FREQUENCY, not by first match.

    Why: ethinyl estradiol returns 16 ATC codes -- 15 are G03* (sex hormones /
    contraceptives) and exactly one is L02AA (estrogens used in oncology). Scanning for
    the first REFINE hit let that single minority code classify a contraceptive as
    "Cancer". Take the modal anatomical group first, then refine only inside it.
    """
    if not codes:
        return "Unclassified", ""
    import collections
    groups = collections.Counter(c[0] for c in codes)
    top = groups.most_common(1)[0][0]                       # dominant anatomical group
    inner = [c for c in codes if c[0] == top]
    lvl2 = collections.Counter(c[:3] for c in inner)
    for code3, _ in lvl2.most_common():                     # refine within that group only
        if code3 in REFINE:
            return REFINE[code3], sorted(c for c in inner if c.startswith(code3))[0]
    return FAMILY.get(top, "Unclassified"), sorted(inner)[0]


SALT = (r"hydrochloride|hydrobromide|sodium|potassium|calcium|magnesium|maleate|meglumine|"
        r"succinate|sulfate|phosphate|besylate|mesylate|tartrate|acetate|citrate|fumarate|"
        r"hemifumarate|diaspartate|mepesuccinate|malate|kamedoxomil|medoxomil|synthetic|"
        r"lactate|bitartrate|dihydrate|monohydrate|anhydrous|recombinant|carboxymaltose|"
        r"pyrophosphate|hyclate|xinafoate|propionate|furoate|valerate|dipropionate")


def candidates(s):
    """Every string worth asking RxClass about, best first.

    A single guess is why carbidopa/levodopa, exenatide synthetic and azilsartan
    kamedoxomil all came back unclassified -- each was queryable under a different form.
    """
    raw = (s or "").strip().lower()
    out = []
    for part in re.split(r"[;,]", raw):                     # every component of a combo
        part = part.strip()
        if not part:
            continue
        out.append(part)                                    # full form, salts included
        stripped = re.sub(r"\s+", " ", re.sub(rf"\b({SALT})\b", "", part)).strip()
        if stripped and stripped != part:
            out.append(stripped)
    seen, uniq = set(), []
    for c in out:
        if c not in seen:
            seen.add(c); uniq.append(c)
    return uniq


def codes_for_row(ingredient, cache):
    """Union the ATC codes across every candidate form, so combos classify."""
    all_codes = []
    for cand in candidates(ingredient):
        all_codes.extend(atc_for(cand, cache))
    return all_codes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="src", default="patent_cliff_2026_2031.csv")
    ap.add_argument("--out", dest="dst", default="patent_cliff_2026_2031_TA.csv")
    a = ap.parse_args()

    rows = list(csv.DictReader(open(a.src, encoding="utf-8")))
    cache = load_cache()
    uniq = sorted({c for r in rows for c in candidates(r.get("ingredient", ""))})
    print(f"{len(rows)} cliffs, {len(uniq)} candidate ingredient forms to classify")

    for i, ing in enumerate(uniq, 1):
        atc_for(ing, cache)
        if i % 50 == 0:
            print(f"  {i}/{len(uniq)}")
            json.dump(cache, open(CACHE_PATH, "w", encoding="utf-8"))
    json.dump(cache, open(CACHE_PATH, "w", encoding="utf-8"))

    hit = 0
    for r in rows:
        fam, code = family(codes_for_row(r.get("ingredient", ""), cache))
        r["therapeutic_family"] = fam
        r["atc_code"] = code
        if fam != "Unclassified":
            hit += 1

    with open(a.dst, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)

    print(f"\nclassified {hit}/{len(rows)}  ({100*hit/len(rows):.0f}%)  -> {a.dst}")
    import collections
    for fam, n in collections.Counter(r["therapeutic_family"] for r in rows).most_common():
        print(f"   {n:4}  {fam}")


if __name__ == "__main__":
    sys.exit(main())
