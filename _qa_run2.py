"""QA the 17:04 run — precision columns now populated at source. Did the fix land?"""
import csv, os, sys, collections, datetime, re

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
TODAY = "2026-08-22"


def load(p):
    fp = os.path.join(HERE, p)
    return list(csv.DictReader(open(fp, encoding="utf-8-sig", errors="replace"))) \
        if os.path.exists(fp) else []


F, C, G = load("readout_forward.csv"), load("readout_calendar.csv"), load("ctgov_readouts.csv")
print(f"forward {len(F)} | calendar {len(C)} | ctgov {len(G)}")
print("   (prev run 16:47 was 278 / 329 / 221)\n")

print("=" * 92)
print("  PRECISION AS RECORDED BY THE SCANNER ITSELF (no more guessing from shape)")
print("=" * 92)
for lab, rows, col in (("forward.window", F, "window_precision"),
                       ("forward.window_alt", F, "window_alt_precision"),
                       ("ctgov.pcd", G, "pcd_precision")):
    c = collections.Counter((r.get(col) or "(blank)") for r in rows)
    print(f"  {lab:<22} {dict(sorted(c.items(), key=lambda x: -x[1]))}")

# the honest publishable set
day_rows = []
for r in F:
    if (r.get("window_precision") or "") == "DAY":
        day_rows.append((r.get("window"), r["ticker"], "EDGAR-stated"))
    elif (r.get("window_alt_precision") or "") == "DAY":
        day_rows.append((r.get("window_alt"), r["ticker"], "armed(real)"))
for r in G:
    if (r.get("pcd_precision") or "") == "DAY" and not _ph(r.get("pcd")) \
            if False else False:
        pass
ct_day = [(r.get("pcd"), r.get("ticker"), "CTgov") for r in G
          if (r.get("pcd_precision") or "") == "DAY"]
print(f"\n  DAY-precision rows: forward {len(day_rows)}, ctgov {len(ct_day)}")

# MONTH? = shape says placeholder, no tag to confirm -> the honest unknown bucket
q = sum(1 for r in F if (r.get("window_alt_precision") or "") == "MONTH?")
print(f"  'MONTH?' (shape says placeholder, untagged — flagged not trusted): {q}")

print("\n" + "=" * 92)
print("  FORWARD DAY-PRECISE, next 90 days")
print("=" * 92)


def iso(s):
    s = (s or "").strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        return s
    try:
        return datetime.datetime.strptime(s.replace(",", ""), "%B %d %Y").strftime("%Y-%m-%d")
    except Exception:
        return None


allday = {}
for d, tk, src in day_rows + ct_day:
    i = iso(d)
    if i and i >= TODAY and tk:
        if tk not in allday or src == "EDGAR-stated":
            allday[tk] = (i, src)
for tk, (d, src) in sorted(allday.items(), key=lambda x: x[1][0])[:30]:
    print(f"  {d}  {tk:<7}{src}")
print(f"  ... {len(allday)} total forward day-precise")

# armed names still vague — the remaining work
print("\n" + "=" * 92)
print("  ARMED NAMES STILL WITHOUT A DAY — the sharpening backlog")
print("=" * 92)
vague = [(r["ticker"], r.get("window") or r.get("window_alt"),
          r.get("window_precision") or r.get("window_alt_precision"), r.get("armed_lane"))
         for r in F if r.get("armed_lane")
         and (r.get("window_precision") or "") != "DAY"
         and (r.get("window_alt_precision") or "") != "DAY"]
seen, out = set(), []
for tk, w, p, lane in vague:
    if tk not in seen:
        seen.add(tk)
        out.append((tk, w, p, lane))
print(f"  {len(out)} armed tickers without a hard date")
for tk, w, p, lane in out[:20]:
    print(f"    {tk:<7}{str(w)[:14]:<16}{str(p):<9}{lane}")
