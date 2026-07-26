#!/usr/bin/env python3
"""
build_slate_from_crawl.py  --  bridge the fresh crawl into the pdufa.bio calendar.

The calendar (api/data.js) is driven by a `const SLATE={...}` catalyst list that the
serverless function enriches live with ORATS/FMP/CT.gov. This script MERGES the fresh
mine (catalysts_out/catalysts_public.csv) into that SLATE:

  * ADD newly-discovered forward PDUFAs from the crawl.
  * KEEP every curated entry that overlaps (same ticker+date) — your hand-written drug
    names / indications win; only the live-ish market fields (price/mcap/adv/cash) refresh.
  * PRESERVE the curated OUT (decided outcomes) and REG (NCT tracking) blocks untouched.
  * UNION opt_tickers.

Safe: backs up api/data.js before writing; supports --dry-run.

Usage:
  python build_slate_from_crawl.py [--csv ../catalysts_out/catalysts_public.csv]
                                   [--api api/data.js] [--dry-run]
"""
import os, re, csv, json, sys, argparse, datetime, shutil

HERE = os.path.dirname(os.path.abspath(__file__))

# crawl catalyst_type values that belong on a PDUFA calendar (regulatory decisions)
PDUFA_TYPES = ("pdufa", "bla", "nda", "snda", "sbla", "gdufa", "adcom",
               "advisory committee", "resubmission", "crl", "fda decision", "approval")

def _f(x):
    try: return float(str(x).replace(",", ""))
    except Exception: return None

def cap_bucket(mc):
    if mc is None: return None
    if mc < 50e6: return "Nano"
    if mc < 300e6: return "Micro"
    if mc < 2e9: return "Small"
    if mc < 10e9: return "Mid"
    return "Large"

def t_minus(date_str, today):
    try:
        p = date_str.split("-"); p = (p + ["01", "01"])[:3]
        return round((datetime.date(int(p[0]), int(p[1]), int(p[2])) - today).days)
    except Exception:
        return None

def is_forward_pdufa(row, today_iso):
    ct = (row.get("catalyst_type") or "").lower()
    if not any(t in ct for t in PDUFA_TYPES):
        return False
    d = (row.get("catalyst_date") or "").strip()
    if len(d) < 7 or d < today_iso:            # forward-dated only (past = handled by OUT)
        return False
    rd = str(row.get("redistribute", "")).strip().lower()
    if rd in ("false", "0", "no"):             # only republishable rows
        return False
    return True

def crawl_to_cat(row, today):
    d = (row.get("catalyst_date") or "").strip()
    mc = _f(row.get("market_cap"))
    return {
        "ticker": (row.get("ticker") or "").strip().upper(),
        "name": (row.get("company") or row.get("ticker") or "").strip(),
        "date": d, "t_minus": t_minus(d, today),
        "drug": (row.get("drug") or "").strip(),
        "indication": (row.get("indication") or "").strip(),
        "price": _f(row.get("price")), "mcap": mc, "cap": cap_bucket(mc),
        "adv": _f(row.get("avg_volume")), "cash_months": _f(row.get("cash_runway_months")),
    }


def load_decided(site_dir):
    """(ticker, normalized-drug) -> (date, outcome) for every event already in the decisions archive.
    An FDA approval can land EARLY (CORT/relacorilant approved 2026-03-25 vs a 2026-07-11 PDUFA),
    so a forward-dated PDUFA is NOT proof the decision is still pending."""
    import glob, html as _html
    dec = {}
    for p in glob.glob(os.path.join(site_dir, 'decisions', 'index.html')):
        h = open(p, encoding='utf-8').read()
        for tk, d, body in re.findall(
                r'<a class="row" href="/fda-decision/([A-Z]+)-(\d{4}-\d{2}-\d{2})"[^>]*>(.*?)</a>', h, re.S):
            txt = _html.unescape(re.sub('<[^>]+>', ' ', body))
            outc = 'Approved' if 'Approved' in txt else ('CRL' if 'CRL' in txt else '?')
            drug = txt.split('\u2014', 1)[1].strip() if '\u2014' in txt else ''
            dec.setdefault((tk, norm_drug(drug)), []).append((d, outc))
    return dec

def norm_drug(s):
    s = (s or '').lower()
    # KEEP THE PARENTHETICAL CONTENTS. This line used to be re.sub(r'\(.*?\)', '', s), which
    # DELETED them — and that silently broke the whole early-approval guard.
    #
    # A drug is renamed when it is approved. The archive logs the BRAND name with the generic
    # in parentheses ("Lifyorli (relacorilant)"); the forward calendar still carries the GENERIC
    # ("Relacorilant + nab-paclitaxel"). Strip the parenthetical and the archive row becomes
    # just "lifyorli" — which shares nothing with "relacorilant nab paclitaxel", because a brand
    # name and its generic have no letters in common. sim=0.29, shared={} -> no match -> the
    # approved drug sat on the forward calendar as pending for ~4 months.
    #
    # The generic inside those parentheses is the ONLY token that can bridge the two. Keep it.
    s = re.sub(r'[()]', ' ', s)
    s = re.sub(r'[^a-z0-9 ]', ' ', s)
    stop = {'the','and','with','plus','in','for','a','of','combination',
            # formulation/route noise — two different drugs from one sponsor can share these,
            # and `shared` fires on ANY common word >5 chars, so they must not count as evidence.
            'tablet','tablets','capsule','capsules','injection','solution','cream','foam',
            'ointment','placebo','controlled','extended','release','oral','topical','inhaled',
            'subcutaneous','intravenous','autoinjector','prefilled','syringe','suspension'}
    return ' '.join(w for w in s.split() if w not in stop)[:60]

def already_decided(cat, dec):
    """The decision for THIS event if it already happened, else None.

    PRECISION MATTERS MORE THAN RECALL HERE. A missed phantom is an embarrassing stale row; a
    FALSE match silently DELETES a live catalyst from a public calendar. So this is deliberately
    conservative and refuses to guess.

    The trap is platform drugs. KEYTRUDA is approved in dozens of indications, so
    "MRK has an approval mentioning pembrolizumab" is NOT evidence that MRK's pending
    KEYTRUDA+Padcev bladder-cancer PDUFA was decided — it matches the unrelated KEYTRUDA QLEX
    subcutaneous approval. Rule: if the drug tokens match MORE THAN ONE distinct archive entry,
    the evidence is ambiguous and we leave the catalyst alone rather than delete it.
    """
    import difflib
    tk = cat.get('ticker'); fd = cat.get('date') or '9999'
    fdrug = norm_drug(cat.get('drug'))
    if not fdrug:
        return None

    def terminal(d, o):
        """Does decision (d, o) actually END the event listed for `fd`?

        AN APPROVAL IS TERMINAL. Once approved, a still-pending PDUFA for the same drug is a
        phantom no matter how large the gap (CORT was approved 108 days before its goal date).

        A CRL IS NOT TERMINAL. It starts the next cycle: the sponsor resubmits and the FDA
        issues a NEW PDUFA date. So a CRL only resolves the event it belongs to — one landing
        near the listed date. A CRL long BEFORE a later PDUFA is the previous round, and that
        later date is a real, live catalyst.

        This is not hypothetical: OTLK was CRL'd, resubmitted 2026-06-01, and the FDA set a
        Class 1 PDUFA of 2026-07-29. Treating the old CRL as terminal would have deleted a live
        catalyst 14 days before its decision.
        """
        if o == 'Approved':
            return True
        if o == 'CRL':
            try:
                gap = (datetime.date.fromisoformat(fd) - datetime.date.fromisoformat(d)).days
            except Exception:
                return False
            return gap <= 45      # same review cycle, not a resubmission
        return False

    hits = []
    for (dtk, ddrug), events in dec.items():
        if dtk != tk or not ddrug:
            continue
        sim = difflib.SequenceMatcher(None, fdrug, ddrug).ratio()
        shared = {w for w in set(fdrug.split()) & set(ddrug.split()) if len(w) > 5}
        if sim > 0.55 or shared:
            prior = [(d, o) for d, o in events if d <= fd and terminal(d, o)]
            if prior:
                hits.append((ddrug, sim, sorted(prior)[-1]))
    if not hits:
        return None
    if len(hits) > 1:
        # Same sponsor, several archive decisions match the drug text -> platform drug (KEYTRUDA,
        # ZORYVE...). Cannot tell WHICH approval this PDUFA was. Do not delete a live catalyst on
        # a coin flip; unless one candidate is a near-exact textual match, stand down.
        strong = [h for h in hits if h[1] > 0.80]
        if len(strong) != 1:
            return None
        return strong[0][2]
    return hits[0][2]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=os.path.join(HERE, "..", "catalysts_out", "catalysts_public.csv"))
    ap.add_argument("--api", default=os.path.join(HERE, "api", "data.js"))
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    today = datetime.date.today(); today_iso = today.isoformat()

    if not os.path.exists(a.csv): sys.exit(f"crawl CSV not found: {a.csv} (run the crawler first)")
    if not os.path.exists(a.api): sys.exit(f"api/data.js not found: {a.api}")

    # 1) current SLATE out of api/data.js
    src = open(a.api, encoding="utf-8").read()
    m = re.search(r"const SLATE=(\{.*?\});\s*const HIST", src, re.S)
    if not m: sys.exit("could not locate `const SLATE={...}; const HIST` in api/data.js")
    slate = json.loads(m.group(1))
    existing = {(c["ticker"], c["date"]): c for c in slate["catalysts"]}

    # 2) fresh forward PDUFAs from the crawl
    rows = list(csv.DictReader(open(a.csv, encoding="utf-8")))
    fresh = [crawl_to_cat(r, today) for r in rows if is_forward_pdufa(r, today_iso)]
    # de-dupe crawl by (ticker,date), keep the richest (has drug+indication)
    fresh_by_key = {}
    for c in fresh:
        if not c["ticker"] or not c["date"]: continue
        k = (c["ticker"], c["date"])
        if k not in fresh_by_key or (len(c["drug"]) + len(c["indication"]) >
                                     len(fresh_by_key[k]["drug"]) + len(fresh_by_key[k]["indication"])):
            fresh_by_key[k] = c

    # 3) MERGE — keep curated on overlap (refresh market fields only), add new
    DECIDED = load_decided(HERE)
    added, refreshed, dropped = [], [], []
    for k, c in fresh_by_key.items():
        if k in existing:
            cur = existing[k]
            for fld in ("price", "mcap", "adv", "cash_months"):
                if c.get(fld) is not None: cur[fld] = c[fld]
            if c.get("mcap") is not None: cur["cap"] = cap_bucket(c["mcap"])
            if not cur.get("drug") and c.get("drug"): cur["drug"] = c["drug"]
            if not cur.get("indication") and c.get("indication"): cur["indication"] = c["indication"]
            refreshed.append(k)
        else:
            hit = already_decided(c, DECIDED)
            if hit:
                dropped.append((k, hit))
                continue
            existing[k] = c; added.append(k)

    # 3b) SWEEP THE WHOLE FORWARD SLATE against the decisions archive — not just new arrivals.
    #
    # already_decided() was consulted ONLY in the `else` branch above, i.e. only for catalysts
    # arriving fresh from the crawl. A catalyst that was ALREADY on the slate when its decision
    # landed was never re-examined; it just had its price refreshed, forever. A gate on entry is
    # not enough, because the decision arrives AFTER the catalyst is already on the board — which
    # is the normal case, not the edge case.
    #
    # That is how CORT/relacorilant sat on the public calendar as "pending" for ~4 months after
    # the FDA approved it on 2026-03-25, and how CELC showed as pending the day after approval.
    swept = []
    for k in list(existing.keys()):
        hit = already_decided(existing[k], DECIDED)
        if hit:
            swept.append((k, hit))
            existing.pop(k)

    merged = sorted(existing.values(), key=lambda c: (c.get("date") or "9999", c.get("ticker") or ""))
    for c in merged: c["t_minus"] = t_minus(c.get("date", ""), today)  # refresh cosmetically
    slate["catalysts"] = merged
    slate["opt_tickers"] = sorted({c["ticker"] for c in merged if c.get("ticker")})
    slate["as_of"] = today_iso

    print(f"SLATE merge: {len(existing)-len(added)} kept/curated  +  {len(added)} NEW from crawl  "
          f"=  {len(merged)} total forward catalysts  (refreshed market fields on {len(refreshed)})")
    if added:
        print("  new names:", ", ".join(f"{t}({d})" for t, d in sorted(added)[:25]) + (" ..." if len(added) > 25 else ""))
    if dropped:
        print(f"  DROPPED {len(dropped)} incoming catalyst(s) already decided (early FDA action):")
        for (tk, d), (dd, o) in dropped:
            print(f"    {tk} {d} -> already {o} on {dd}")
    if swept:
        print(f"  SWEPT {len(swept)} catalyst(s) OFF the forward calendar — already decided:")
        for (tk, d), (dd, o) in swept:
            print(f"    {tk} listed {d} -> actually {o} on {dd}")
    print(f"  OUT (decided outcomes) preserved: {len(slate.get('OUT', {})) if 'OUT' in slate else 'in api (untouched)'}")

    if a.dry_run:
        print("\n--dry-run: no files written."); return

    # 4) write back — replace ONLY the SLATE literal, leave HIST/OUT/REG/handler intact
    new_lit = "const SLATE=" + json.dumps(slate, separators=(",", ":")) + "; const HIST"
    out = src[:m.start()] + new_lit + src[m.end():]
    shutil.copy2(a.api, a.api + ".bak_" + today_iso)
    open(a.api, "w", encoding="utf-8").write(out)
    print(f"\nwrote {a.api}  (backup: {os.path.basename(a.api)}.bak_{today_iso})")

if __name__ == "__main__":
    main()
