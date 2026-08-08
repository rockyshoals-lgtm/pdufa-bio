"""readout_grade.py — HOW GOOD IS THIS READOUT, versus every readout we have?

David, 2026-07-20: "is there any way to tell HOW good a readout is... when the news hits the wire,
can you analyze exactly how it compares to other readouts?"

Yes — because gungnir_readout_analysis.csv is 1,752 phase-readout events carrying BOTH the quality
flags (met_primary / stat_sig / topline / failed_primary / crl) AND the real stock returns
(ret_0d/1d/5d). That is the full event set, not a winners-only surge list, so it gives a HONEST
base rate in both directions.

The grade is not an opinion about the science. It is: "readouts that LOOKED like this one, in this
phase and therapeutic area, historically did X." Detection and comparison — never prediction.
"""
import csv
import os
import re
import statistics as st
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "gungnir_readout_analysis.csv")


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _b(x):
    return str(x).strip().lower() in ("1", "true", "yes", "t")


def load():
    rows = []
    for r in csv.DictReader(open(SRC, encoding="utf-8-sig")):
        r["_ret1"] = _f(r.get("ret_1d"))
        r["_ret0"] = _f(r.get("ret_0d"))
        r["_ret5"] = _f(r.get("ret_5d"))
        for k in ("met_primary", "failed_primary", "stat_sig", "topline", "fda_approval", "crl"):
            r["_" + k] = _b(r.get(k))
        rows.append(r)
    return [r for r in rows if r["_ret1"] is not None]


def stats(rows, label):
    n = len(rows)
    if n < 8:
        return f"  {label:<44}n={n:<5} (too few to read)"
    rets = [r["_ret1"] for r in rows]
    med = st.median(rets)
    pop = sum(1 for x in rets if x >= 15) / n * 100
    big = sum(1 for x in rets if x >= 30) / n * 100
    crash = sum(1 for x in rets if x <= -15) / n * 100
    up = sum(1 for x in rets if x > 0) / n * 100
    return (f"  {label:<44}n={n:<5} med {med:>+6.1f}%   up {up:>4.0f}%   "
            f"≥15% {pop:>4.0f}%   ≥30% {big:>4.0f}%   ≤-15% {crash:>4.0f}%")


def grade_headline(title, phase_hint=None, ta_hint=None):
    """Extract the same quality features from a live headline that the dataset carries."""
    t = (title or "").lower()
    f = {
        "met_primary": bool(re.search(r"met\b[^.]{0,25}\bprimary|achieved[^.]{0,20}primary", t)),
        "stat_sig": bool(re.search(r"statistically significant|p\s*[=<]\s*0?\.\d|hazard ratio|hr=", t)),
        "topline": bool(re.search(r"topline|top-line", t)),
        "positive": bool(re.search(r"\bpositive\b", t)),
        "updated": bool(re.search(r"\bupdated\b|\binterim\b|\badditional\b", t)),
        "failed": bool(re.search(r"did not meet|failed to meet|missed[^.]{0,15}endpoint", t)),
        "numbers": bool(re.search(r"\d{1,3}\s?%|\bmonths\b|\borr\b|\bpfs\b|\bos\b", t)),
    }
    ph = phase_hint or ("3" if re.search(r"phase 3|phase iii", t) else
                        "2" if re.search(r"phase 2|phase ii\b", t) else
                        "1" if re.search(r"phase 1|phase i\b", t) else None)
    return f, ph


def main():
    rows = load()
    print(f"corpus: {len(rows):,} readout events with real 1-day returns\n")
    print("=" * 100)
    print("  THE LADDER — what a readout's CLAIMS were historically worth (1-day return)")
    print("=" * 100)
    print(stats(rows, "ALL readouts (the base rate)"))
    print(stats([r for r in rows if r["_met_primary"] and r["_stat_sig"]],
                "met primary + statistically significant"))
    print(stats([r for r in rows if r["_met_primary"]], "met primary endpoint (claimed)"))
    print(stats([r for r in rows if r["_stat_sig"]], "statistically significant (claimed)"))
    print(stats([r for r in rows if r["_topline"]], "topline"))
    print(stats([r for r in rows if r["_topline"] and not r["_met_primary"]],
                "topline WITHOUT a met-primary claim"))
    print(stats([r for r in rows if not any((r["_met_primary"], r["_stat_sig"], r["_topline"]))],
                "no endpoint / no stat / no topline claim"))
    print(stats([r for r in rows if r["_failed_primary"]], "FAILED primary"))
    print(stats([r for r in rows if r["_crl"]], "CRL"))

    print("\n" + "=" * 100)
    print("  BY PHASE")
    print("=" * 100)
    for p in ("1", "2", "3"):
        sub = [r for r in rows if str(r.get("phase", "")).strip() == p]
        print(stats(sub, f"Phase {p}"))
        print(stats([r for r in sub if r["_met_primary"] and r["_stat_sig"]],
                    f"   Phase {p} + met primary + stat sig"))

    if len(sys.argv) > 1:
        title = " ".join(sys.argv[1:])
        f, ph = grade_headline(title)
        print("\n" + "=" * 100)
        print("  GRADING THE LIVE HEADLINE")
        print("=" * 100)
        print(f"  {title[:96]}")
        print(f"  extracted -> phase={ph}  " + "  ".join(f"{k}={'Y' if v else '-'}" for k, v in f.items()))
        sub = rows
        if ph:
            sub = [r for r in sub if str(r.get("phase", "")).strip() == ph]
        if f["met_primary"]:
            sub = [r for r in sub if r["_met_primary"]]
        elif f["topline"] or f["positive"]:
            sub = [r for r in sub if r["_topline"] and not r["_met_primary"]]
        print("\n  CLOSEST HISTORICAL COHORT:")
        print(stats(sub, f"phase={ph or 'any'} matched on claim profile"))
        if len(sub) >= 8:
            rets = sorted(r["_ret1"] for r in sub)
            q = lambda p: rets[int(len(rets) * p)]
            print(f"  distribution: p10 {q(.10):+.1f}%   p25 {q(.25):+.1f}%   "
                  f"median {q(.50):+.1f}%   p75 {q(.75):+.1f}%   p90 {q(.90):+.1f}%")
    print("\n  Base rates from OUR OWN event set. Historical comparison, NOT a prediction of this")
    print("  event. Not investment advice.")


if __name__ == "__main__":
    main()
