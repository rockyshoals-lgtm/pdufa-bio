"""Guard (2026-11-27 ET): a renamed company's catalysts live on ONE hub, under its current ticker.

Quince Therapeutics became IRulya Therapeutics (Nasdaq: IRLA, from Oct 12, 2026). Two LAM-001 readouts were on
/ticker/IRLA while the nearest (BOS, Q1 2027) stayed on /ticker/QNCX, so the IRLA page called a Q1 2028 readout the
company's next catalyst. Rule: when a row's company says "formerly <name>, <OLD>", no row may remain keyed <OLD>,
and /ticker/<OLD> must redirect permanently to /ticker/<current>.
"""
import io, json, os, re, sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    src = io.open(os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs"), encoding="utf-8").read()
    rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    cfg = json.load(io.open(os.path.join(HERE, "pdufa_site_src", "vercel.json"), encoding="utf-8"))
    red = {r.get("source"): r for r in cfg.get("redirects", [])}
    by_t = {}
    for r in rows:
        by_t.setdefault(r["t"], []).append(r["id"])
    bad, pairs = [], set()
    for r in rows:
        m = re.search(r"formerly [^)]*?,\s*([A-Z]{2,5})\)", str(r.get("company") or ""))
        if m and m.group(1) != r["t"]:
            pairs.add((m.group(1), r["t"]))
    for old, cur in sorted(pairs):
        if by_t.get(old):
            bad.append(f"{old} still has rows {by_t[old]} though {cur} is its current ticker")
        rr = red.get(f"/ticker/{old}")
        if not rr or rr.get("destination") != f"/ticker/{cur}" or not rr.get("permanent"):
            bad.append(f"/ticker/{old} does not redirect permanently to /ticker/{cur}")
    assert ("QNCX", "IRLA") in pairs, "the IRulya rename should be on file"
    if bad:
        print("FAIL --", *bad, sep="\n  ")
        return 1
    print(f"OK -- {len(pairs)} renamed ticker(s), each on one hub with a permanent redirect.")
    return 0


def test_renamed_ticker_one_hub():
    assert main() == 0


if __name__ == "__main__":
    sys.exit(main())
