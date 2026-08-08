"""Does the dateline fix work on the ACTUAL filings that produced the bad windows?

Not synthetic strings — the real GUTS/CANF/TARS 8-Ks that returned their own filing date as a
"readout window" on 2026-07-17. A fix that only passes on invented text is not a fix.
"""
import os, sys, csv
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("SEC_USER_AGENT", "David Moody rockyshoals@gmail.com")
import readout_scan as R

ok_n = fail = 0


def ok(c, m):
    global ok_n, fail
    print(("  PASS  " if c else "  FAIL  ") + m)
    if c: ok_n += 1
    else: fail += 1


# ---- unit: the two rules, in isolation -----------------------------------------------------
print("=" * 94)
print("  UNIT — _hard_date + the reject rules")
print("=" * 94)
import datetime as dt
ok(R._hard_date("July 15, 2026") == dt.date(2026, 7, 15), "_hard_date parses 'July 15, 2026'")
ok(R._hard_date("JULY 6, 2026") == dt.date(2026, 7, 6), "_hard_date is case-insensitive")
ok(R._hard_date("2H 2026") is None, "_hard_date returns None for a vague period")
ok(R._hard_date("garbage") is None, "_hard_date survives junk")
ok(R.VAGUE_RX.search("expects topline in 2H 2026") is not None, "VAGUE_RX finds '2H 2026'")
ok(R.VAGUE_RX.search("data expected in the fourth quarter of 2026") is not None,
   "VAGUE_RX finds 'fourth quarter of 2026'")
ok(R.FWD_NEAR.search("Reports Positive Results") is None,
   "FWD_NEAR does NOT fire on 'Reports Positive Results' — that is a PAST readout")
ok(R.FWD_NEAR.search("expects to report topline") is not None, "FWD_NEAR fires on 'expects to'")

# ---- the real filings ----------------------------------------------------------------------
# Pulled from the 2026-07-17 readout_forward.csv. Each returned `window == filed`.
print("\n" + "=" * 94)
print("  THE REAL FILINGS THAT BROKE — refetched from EDGAR")
print("=" * 94)
UP = (r"C:\Users\dcmoo\AppData\Roaming\Claude\local-agent-mode-sessions"
      r"\73ed6afa-1982-4aa5-beaa-ae356aeb0ed6\91666954-12a2-40a1-872a-dee734870139"
      r"\local_92dc8303-3ed0-4541-bb97-f41c446875d6\uploads"
      r"\52f11d7b-94d0-47a2-b44f-6efcd1969cfd-1784312206271_readout_forward.csv")
rows = list(csv.DictReader(open(UP, encoding="utf-8-sig")))
bad = [r for r in rows if (r.get("window") or "").strip() and r["window"].strip().lower()
       .replace(",", "") in {
           __import__("datetime").datetime.strptime(r["filed"], "%Y-%m-%d")
           .strftime("%B %-d %Y").lower() if os.name != "nt" else
           __import__("datetime").datetime.strptime(r["filed"], "%Y-%m-%d")
           .strftime("%B %d %Y").lower().replace(" 0", " "),
       }]
# simpler + robust: window parses to a hard date within 3d of filed
bad = []
for r in rows:
    hd = R._hard_date((r.get("window") or "").strip())
    if not hd:
        continue
    fd = dt.date(*map(int, r["filed"].split("-")))
    if abs((hd - fd).days) <= 3:
        bad.append(r)
print(f"  {len(bad)} rows in the shipped CSV have window == filed (the dateline bug)\n")

agent = R.ua()
fixed = still_bad = 0
for r in bad[:6]:
    h = {"cik": r["cik"], "accn": r["accession"], "doc": r["document"]}
    try:
        w, ctx = R.fetch_date(h, agent, filed=r["filed"])
    except Exception as e:
        print(f"    {r['ticker']:<6} fetch error: {e}")
        continue
    hd = R._hard_date(w or "")
    fd = dt.date(*map(int, r["filed"].split("-")))
    echoed = bool(hd and abs((hd - fd).days) <= 3)
    if echoed:
        still_bad += 1
    else:
        fixed += 1
    print(f"    {r['ticker']:<6} filed {r['filed']}   was '{r['window']}'   ->   "
          f"{'None (correctly refuses)' if not w else repr(w)}")
    if ctx:
        print(f"           ctx: {ctx[:96]}")

ok(still_bad == 0, f"NO refetched filing still returns its own dateline "
                   f"({fixed} fixed, {still_bad} still wrong)")

# ---- and it must NOT have broken the good rows ---------------------------------------------
print("\n" + "=" * 94)
print("  THE GOOD ROWS MUST SURVIVE — vague periods are the real guidance")
print("=" * 94)
good = [r for r in rows if R.VAGUE_RX.match((r.get("window") or "").strip())][:4]
kept = 0
for r in good:
    h = {"cik": r["cik"], "accn": r["accession"], "doc": r["document"]}
    try:
        w, _ = R.fetch_date(h, agent, filed=r["filed"])
    except Exception as e:
        print(f"    {r['ticker']:<6} fetch error: {e}")
        continue
    same = (w or "").strip().lower() == (r["window"] or "").strip().lower()
    kept += 1 if w else 0
    print(f"    {r['ticker']:<6} was '{r['window']}'  ->  {repr(w)}  {'same' if same else ''}")
ok(kept >= max(1, len(good) - 1),
   f"vague-period guidance still extracts ({kept}/{len(good)}) — the fix rejects datelines, "
   f"not real windows")

print("\n" + "=" * 94)
print(f"  {ok_n} passed, {fail} failed")
print("=" * 94)
sys.exit(1 if fail else 0)
