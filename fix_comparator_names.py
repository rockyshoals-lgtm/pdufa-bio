# -*- coding: utf-8 -*-
"""fix_comparator_names.py -- stop publishing the comparator arm as the company's drug.

The red team found Bristol-Myers Squibb's ticker page titled:

    Bristol-Myers Squibb Company (BMY) FDA Catalysts: Bevacizumab

BMY does not make bevacizumab. That is Roche's Avastin, and Outlook's LYTENAVA. The record came
from a ClinicalTrials.gov ingest that captured whichever intervention it saw first, which in a
controlled trial is frequently the comparator or the backbone regimen rather than the sponsor's own
asset. Seventeen readout records carry a name like this. Four say "Standard of Care Treatment",
which is not a drug at all.

Two things make this worth fixing properly rather than patching the one title:

  * The entity-title work PROMOTED the defect. It used to sit in a thin, unindexed readout row;
    it now leads the <title> and meta description, which are the exact fields that bind the company
    to its assets in search. A good SEO fix amplified a data bug.
  * It is checkable. The trial record says which arm is EXPERIMENTAL and which is
    ACTIVE_COMPARATOR or PLACEBO_COMPARATOR, and it names the lead sponsor. So the sponsor's own
    intervention can be derived rather than guessed.

So this resolves each affected record against ClinicalTrials.gov live, takes the intervention from
an experimental arm, and prefers one that is not a well-known backbone agent. Where a record has no
NCT to check, nothing is invented: it is reported for manual review and its name is suppressed from
the fields that bind the entity.

It also reports trials whose lead sponsor is NOT the company we have attached the catalyst to.
Two of these are investigator-initiated (a named academic and Memorial Sloan Kettering), which is a
different and quieter attribution problem: a company's stock does not have a catalyst just because
someone else is studying its drug.

    python fix_comparator_names.py [--dry-run]
"""
import argparse, json, os, re, sys, time, urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")
CACHE = os.path.join(HERE, "_ctgov_intervention_cache.json")
UA = {"User-Agent": "pdufa.bio data-quality (rockyshoals@gmail.com)"}

# Not drugs. A record whose asset is one of these is describing the control arm.
NOT_A_DRUG = re.compile(
    r"^\s*(standard of care\b.*|placebo\b.*|best supportive care|investigator'?s choice|"
    r"observation|no intervention|control|usual care)\s*$", re.I)

# Common backbone / comparator agents. Being on this list does not condemn a record: it is only
# used to DEMOTE a candidate when the trial offers something better. Sponsors who genuinely own
# these (Merck with pembrolizumab, BMS with nivolumab, Outlook with bevacizumab) keep them.
BACKBONE = {"rituximab", "gemcitabine", "dexamethasone", "cisplatin", "carboplatin", "docetaxel",
            "paclitaxel", "cyclophosphamide", "fludarabine", "pembrolizumab", "nivolumab",
            "bevacizumab", "anti-pd-1", "prednisone", "methotrexate", "lenalidomide"}

# Sponsors who own the agent above, so their record is correct as-is.
OWNS = {"MRK": {"pembrolizumab"}, "BMY": {"nivolumab"}, "OTLK": {"bevacizumab"},
        "RHHBY": {"bevacizumab"}, "AZN": {"durvalumab"}}


def load_cache():
    try:
        return json.load(open(CACHE, encoding="utf-8"))
    except Exception:
        return {}


def ctgov(nct, cache):
    if nct in cache:
        return cache[nct]
    u = (f"https://clinicaltrials.gov/api/v2/studies/{nct}"
         f"?fields=protocolSection.sponsorCollaboratorsModule,"
         f"protocolSection.armsInterventionsModule")
    try:
        d = json.loads(urllib.request.urlopen(
            urllib.request.Request(u, headers=UA), timeout=25).read())
    except Exception:
        cache[nct] = None
        return None
    ps = d.get("protocolSection", {})
    arms = ps.get("armsInterventionsModule", {}) or {}
    out = {
        "sponsor": (ps.get("sponsorCollaboratorsModule", {})
                    .get("leadSponsor", {}).get("name", "")),
        "arms": [{"type": a.get("type"), "names": a.get("interventionNames") or []}
                 for a in (arms.get("armGroups") or [])],
    }
    cache[nct] = out
    time.sleep(0.3)
    return out


_SEC = None


def company_for(tk):
    """Registrant name for a ticker, from SEC's own file, so the sponsor check has something real
    to compare against."""
    global _SEC
    if _SEC is None:
        _SEC = {}
        for p in ("sec_company_tickers.json", "sec_ticker_cik.json"):
            f = os.path.join(HERE, p)
            if not os.path.exists(f):
                continue
            try:
                raw = json.load(open(f, encoding="utf-8"))
            except Exception:
                continue
            items = raw.values() if isinstance(raw, dict) else raw
            for it in items:
                if isinstance(it, dict) and it.get("ticker"):
                    _SEC[str(it["ticker"]).upper()] = str(it.get("title") or "")
    return _SEC.get(tk.upper(), "")


def sponsor_matches(sponsor, tk, company):
    """True when the trial's lead sponsor plausibly IS the company we attribute the catalyst to."""
    def toks(s):
        s = re.sub(r"\b(inc|corp|corporation|company|co|ltd|limited|plc|llc|sa|ag|nv|holdings|"
                   r"pharmaceuticals?|pharma|therapeutics?|biosciences?|bio|group|the)\b", " ",
                   (s or "").lower())
        return {w for w in re.findall(r"[a-z]{3,}", s)}
    sp = toks(sponsor)
    for cand in (company, company_for(tk)):
        c = toks(cand)
        if c and sp & c:
            return True
    return False


def sponsor_asset(info):
    """The sponsor's own intervention: from an EXPERIMENTAL arm, preferring a non-backbone agent."""
    if not info:
        return None
    cands = []
    for a in info["arms"]:
        if (a["type"] or "").upper() != "EXPERIMENTAL":
            continue
        for raw in a["names"]:
            # "Biological: KYV-101 anti-CD19 CAR-T cell therapy" -> "KYV-101 anti-CD19 CAR-T cell..."
            nm = re.sub(r"^(Drug|Biological|Device|Procedure|Radiation|Other|Genetic|"
                        r"Dietary Supplement|Combination Product|Diagnostic Test)\s*:\s*", "",
                        raw).strip()
            nm = re.sub(r"\s*\((combination|continuous) therapy\)", "", nm, flags=re.I).strip()
            if not nm or NOT_A_DRUG.match(nm):
                continue
            if re.match(r"^(placebo|standard|matching)", nm, re.I):
                continue
            base = nm.split()[0].lower().strip(",")
            cands.append((base in BACKBONE, len(nm), nm))
    if not cands:
        return None
    cands.sort()                       # non-backbone first, then shortest
    return cands[0][2]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    src = open(DATASET, encoding="utf-8", errors="replace").read()
    m = re.search(r"export default (\[.*\])", src, re.S)
    rows = json.loads(m.group(1))
    cache = load_cache()

    suspect = []
    for r in rows:
        name = (r.get("name") or "").strip()
        tk = (r.get("t") or "").upper()
        if not name:
            continue
        head = name.split()[0].lower().strip(",+")
        owned = head in OWNS.get(tk, set())
        if NOT_A_DRUG.match(name) or (head in BACKBONE and not owned):
            suspect.append(r)

    print(f"{len(suspect)} record(s) whose stored asset looks like a comparator or is not a drug\n")

    fixed = unresolved = mismatched = 0
    for r in suspect:
        nct = (r.get("_d") or {}).get("nct_id")
        tk, old = (r.get("t") or "").upper(), r.get("name")
        if not nct:
            unresolved += 1
            print(f"  UNRESOLVED  {tk:<6} {r.get('d')}  {old!r}")
            print(f"              no NCT to check. Not guessing; flagged for manual review.")
            r["_needs_review"] = "asset name looks like a comparator and no trial id is recorded"
            continue
        info = ctgov(nct, cache)
        new = sponsor_asset(info)
        if not new:
            unresolved += 1
            print(f"  UNRESOLVED  {tk:<6} {r.get('d')}  {old!r}  ({nct}: no experimental arm found)")
            r["_needs_review"] = "could not derive the sponsor's own asset from the trial record"
            continue
        r["name"] = new
        fixed += 1
        print(f"  FIXED       {tk:<6} {r.get('d')}  {old!r} -> {new!r}   ({nct})")
        # Is the trial actually run by the company we have attached this catalyst to?
        #
        # Comparing the sponsor string against the TICKER letters does not work: "Kyverna
        # Therapeutics" contains no "KYTX", so the first version flagged every correct row and
        # buried the three that matter. Compare against the company NAME instead, which makes the
        # warning mean something: what is left is David Porter, Memorial Sloan Kettering and
        # Charite Berlin, i.e. investigator-initiated studies. A company's stock does not have a
        # catalyst merely because an academic centre is studying its drug on its own timetable.
        spon = (info or {}).get("sponsor", "")
        if spon and not sponsor_matches(spon, tk, r.get("company") or ""):
            mismatched += 1
            r["_sponsor_note"] = f"Trial lead sponsor is {spon}"
            print(f"              SPONSOR: {spon!r} is not {tk}. Investigator-initiated, so this "
                  f"is not a company-run catalyst; the timing is not the company's to guide.")

    if not a.dry_run:
        json.dump(cache, open(CACHE, "w", encoding="utf-8"), indent=0)
        body = json.dumps(rows, separators=(",", ":"), ensure_ascii=False)
        open(DATASET, "w", encoding="utf-8").write(
            src[:m.start(1)] + body + src[m.end(1):])

    print(f"\n{fixed} corrected from the trial record, {unresolved} left for manual review, "
          f"{mismatched} with a sponsor that is not the attributed company"
          + (" [dry run, nothing written]" if a.dry_run else ""))


if __name__ == "__main__":
    main()
