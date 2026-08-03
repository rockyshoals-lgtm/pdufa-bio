# -*- coding: utf-8 -*-
"""verify_readouts.py -- re-check every mined readout against the filing it came from.

The miner already applied its rules once. This does not trust that. It re-fetches each row's
filing_url, re-reads the document, and independently confirms four things:

  1. the stored sentence is actually present in that filing (catches a bad snippet or a wrong URL)
  2. the guidance phrase and the date re-parse to the SAME date the row claims
  3. the program re-extracts under the CURRENT rules (the first pass labelled five rows with a
     biological target like "IL-17" instead of the drug)
  4. the date is still in the future

Anything that fails any check is written to a rejects file and never reaches the site. This exists
because "the script said so" is not verification, and the whole point of the site is that a row can
be traced back to a document a human can open.

    python verify_readouts.py --in readout_runs/readout_miner_deep.csv
"""
import argparse, csv, importlib.util, json, os, re, sys, time
import datetime as dt
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("rm", os.path.join(HERE, "readout_miner.py"))
rm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rm)

UA = {"User-Agent": os.environ.get("SEC_USER_AGENT", "pdufa.bio research contact@pdufa.bio")}
CACHE = os.path.join(HERE, "bpc_data", "_verify_doc_cache.json")


def norm(s):
    return re.sub(r"[^a-z0-9 ]+", " ", (s or "").lower())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="src", default="readout_runs/readout_miner_deep.csv")
    ap.add_argument("--out", default="readout_runs/readout_verified.csv")
    ap.add_argument("--rejects", default="readout_runs/readout_rejected.csv")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    rows = list(csv.DictReader(open(os.path.join(HERE, a.src), encoding="utf-8-sig",
                                    errors="replace")))
    if a.limit:
        rows = rows[:a.limit]
    cache = {}
    if os.path.exists(CACHE):
        try:
            cache = json.load(open(CACHE, encoding="utf-8"))
        except Exception:
            cache = {}

    today = dt.date.today().isoformat()
    ok, bad = [], []
    for n, r in enumerate(rows, 1):
        url = (r.get("filing_url") or "").strip()
        why = []
        if not url.startswith("https://www.sec.gov/"):
            why.append("no SEC filing_url")
            bad.append({**r, "reject_reason": "; ".join(why)}); continue

        txt = cache.get(url)
        if txt is None:
            try:
                raw = urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                             timeout=25).read()
                txt = rm._doc_text.__globals__["re"].sub(r"<[^>]+>", " ", raw.decode("utf-8", "replace"))
                txt = re.sub(r"\s+", " ", txt)
            except Exception as e:
                txt = ""
            cache[url] = txt
            time.sleep(0.12)
            if n % 10 == 0:
                json.dump(cache, open(CACHE + ".tmp", "w", encoding="utf-8"))
                os.replace(CACHE + ".tmp", CACHE)

        if not txt:
            why.append("filing could not be re-fetched")
        else:
            # 1. the sentence really is in that document
            probe = norm(r.get("matched_sentence", ""))[:120].strip()
            if probe and probe not in norm(txt):
                why.append("stored sentence not found in the filing")
            # 2. the date re-parses to the same value
            d2, prec2 = rm.parse_guided_date(r.get("matched_sentence", ""))
            if d2 != r.get("guided_date"):
                why.append(f"date re-parses to {d2 or 'nothing'}, row says {r.get('guided_date')}")
            if prec2 != r.get("guided_precision"):
                why.append(f"precision re-parses to {prec2}, row says {r.get('guided_precision')}")
            # 3. the program survives the current rules.
            # Keep the row's own program when it is still legitimate. The stored sentence is capped
            # at 400 chars, so re-extracting from it blindly can land on a WORSE token than the
            # miner found in the full snippet: RGNX's "RGX-314" degraded to "subretinal" that way.
            # Only replace a program that the current rules actually reject.
            prog = (r.get("program") or "").strip()
            head = re.split(r"[-\d]", prog)[0].upper()
            still_valid = bool(prog) and (r.get("program_kind") == "nct"
                                          or (head not in rm._STOP
                                              and prog.lower() not in rm._GENERIC))
            if not still_valid:
                p2, k2 = rm.extract_program(r.get("matched_sentence", ""))
                if not p2:
                    why.append(f"program {prog!r} rejected by current rules and no valid "
                               f"replacement in the sentence")
                else:
                    r["program_was"], r["program"], r["program_kind"] = prog, p2, k2
        # 4. still forward-dated
        if (r.get("best_date") or "") < today:
            why.append("date is in the past")

        (bad if why else ok).append({**r, "reject_reason": "; ".join(why)} if why else r)
        if n % 15 == 0:
            print(f"  {n}/{len(rows)} checked  ({len(ok)} pass, {len(bad)} reject)")

    json.dump(cache, open(CACHE + ".tmp", "w", encoding="utf-8"))
    os.replace(CACHE + ".tmp", CACHE)

    cols = list(rows[0].keys()) + ["program_was"]
    with open(os.path.join(HERE, a.out), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore"); w.writeheader(); w.writerows(ok)
    with open(os.path.join(HERE, a.rejects), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols + ["reject_reason"], extrasaction="ignore")
        w.writeheader(); w.writerows(bad)

    print(f"\nVERIFIED {len(ok)} / {len(rows)}   rejected {len(bad)}")
    changed = [r for r in ok if r.get("program_was")]
    if changed:
        print(f"\n{len(changed)} program label(s) corrected on re-extraction:")
        for r in changed:
            print(f"   {r['ticker']:<6} {r['program_was']!r} -> {r['program']!r}")
    if bad:
        print(f"\nrejected:")
        for r in bad[:20]:
            print(f"   {r['ticker']:<6} {r.get('best_date','')}  {r['reject_reason'][:90]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
