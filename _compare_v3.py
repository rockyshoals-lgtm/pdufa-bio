"""Before/after: readout_forward.csv (old) vs readout_forward_v3.csv (improved)."""
import csv
import collections
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))


def load(p):
    return list(csv.DictReader(open(os.path.join(HERE, p), encoding="utf-8-sig")))


old = load("readout_forward.csv")
new = load("readout_forward_v3.csv")


def stats(rows, label):
    win = [r for r in rows if (r.get("window") or "").strip()]
    tk = collections.Counter(r.get("ticker", "") for r in rows)
    dups = {k: v for k, v in tk.items() if v > 1}
    print(f"  {label}: {len(rows)} rows, {len(win)} with window "
          f"({len(win)/max(len(rows),1)*100:.0f}%), "
          f"{len(set(tk))} unique tickers, {len(dups)} duplicated tickers")
    return win, dups


print("=" * 90)
print("  BEFORE vs AFTER")
print("=" * 90)
owin, odup = stats(old, "OLD ")
nwin, ndup = stats(new, "NEW ")

print("\n  duplicate tickers OLD:", dict(odup))
print("  duplicate tickers NEW:", dict(ndup))

# GLMD false positive gone?
og = [r["window"] for r in old if r["ticker"] == "GLMD"]
ng = [r["window"] for r in new if r["ticker"] == "GLMD"]
print("\n" + "=" * 90)
print("  THE GLMD FALSE POSITIVE")
print("=" * 90)
print(f"  OLD GLMD windows: {og}")
print(f"  NEW GLMD windows: {ng}   <- 'December 31, 2026' fiscal ref should be gone/blank")

# recovered windows: tickers that had blank before, window now
old_win_tk = {r["ticker"] for r in old if (r.get("window") or "").strip()}
new_win_tk = {r["ticker"] for r in new if (r.get("window") or "").strip()}
print("\n" + "=" * 90)
print("  RECALL — windows recovered (blank before, dated now)")
print("=" * 90)
recovered = new_win_tk - old_win_tk
lost = old_win_tk - new_win_tk
print(f"  newly dated tickers: {sorted(recovered)}")
print(f"  no longer dated    : {sorted(lost)}  (GLMD here = the fix working)")

print("\n" + "=" * 90)
print("  THE NEW LIST — one row per ticker, nearest-forward window")
print("=" * 90)
print(f"  {'tkr':<6} {'filed':<11} {'n':<3} {'window':<22} company")
for r in sorted([r for r in new if (r.get('window') or '').strip()],
                key=lambda r: r.get("filed", ""), reverse=True):
    print(f"  {r.get('ticker',''):<6} {r.get('filed',''):<11} {r.get('n_filings','1'):<3} "
          f"{(r.get('window') or '')[:20]:<22} {(r.get('company') or '')[:30]}")
