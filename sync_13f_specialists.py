# -*- coding: utf-8 -*-
"""sync_13f_specialists.py -- latest 13F holdings of ten specialist biotech funds, from EDGAR (audit 10-03, 4.1).

The order pointed at Odin Perfection/v382_checkpoints/phase1_god_tier_holdings.json (48,361 records) and
said: open it and confirm the as-of dates before writing a sentence. Opened 2026-10-03: its latest quarter
is 2026-03-31 (filed by 2026-05-15), one quarter stale, and THREE of its six fund CIKs are wrong:
"venBio Select Advisor" 0001603466 holds NVDA/AMZN/SPY (3,704 positions), "Perceptive Advisors"
0001224608 is CNO Financial Group (bond ETFs), "Foresite Capital" 0001540531 holds SHAK/RBLX. Nothing from
that file is published. This reads each fund's latest 13F-HR straight from EDGAR instead, with every CIK
checked against the filer name EDGAR returns (a mismatch is skipped and reported, never published):

  Baker Bros. Advisors 1263508 · RA Capital Management 1346824 · Perceptive Advisors 1224962 ·
  OrbiMed Advisors 1055951 · Avoro Capital Advisors (formerly venBio Select Advisor) 1633313 ·
  RTW Investments 1493215 · EcoR1 Capital 1587114 · BVF Inc 1056807 · Redmile Group 1425738 ·
  Cormorant Asset Management 1583977

CUSIP -> ticker comes from the CUSIP/symbol pairs in the old file (the symbols there are FMP's and were
not the problem; the fund CIKs were), then from an exact issuer-name match in sec_company_tickers.json.
Writes _13f_specialists.json. Long equity positions only (put/call rows are excluded). Facts only.

    python sync_13f_specialists.py
"""
import datetime as dt
import io
import json
import os
import re
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "_13f_specialists.json")
OLD = os.path.join(HERE, "Odin Perfection", "v382_checkpoints", "phase1_god_tier_holdings.json")
UA = {"User-Agent": "pdufa.bio watcher rockyshoals@gmail.com"}
FUNDS = [("Baker Bros. Advisors", 1263508, "BAKER BROS"), ("RA Capital Management", 1346824, "RA CAPITAL"),
         ("Perceptive Advisors", 1224962, "PERCEPTIVE"), ("OrbiMed Advisors", 1055951, "ORBIMED"),
         ("Avoro Capital Advisors", 1633313, "AVORO"), ("RTW Investments", 1493215, "RTW"),
         ("EcoR1 Capital", 1587114, "ECOR1"), ("BVF Inc.", 1056807, "BVF"),
         ("Redmile Group", 1425738, "REDMILE"), ("Cormorant Asset Management", 1583977, "CORMORANT")]


def get(url, limit=8_000_000):
    for _ in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
                return r.read(limit).decode("utf-8", "replace")
        except Exception:
            time.sleep(1.5)
    return None


def norm(s):
    s = re.sub(r"[^a-z0-9 ]", " ", str(s or "").lower())
    s = re.sub(r"\b(inc|corp|corporation|co|ltd|plc|holdings?|the|company|n v|nv|sa|ag|limited|llc|lp|class [a-z]|com|common)\b", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def main():
    cus2sym = {}
    cmap = os.path.join(HERE, "_cusip_symbol_map.json")      # committed: the old file is local-only
    if os.path.exists(OLD):
        for x in json.load(io.open(OLD, encoding="utf-8")):
            if x.get("securityCusip") and x.get("symbol"):
                cus2sym.setdefault(x["securityCusip"].upper(), x["symbol"].upper())
        io.open(cmap, "w", encoding="utf-8", newline="\n").write(json.dumps(cus2sym, sort_keys=True) + "\n")
    elif os.path.exists(cmap):
        cus2sym = json.load(io.open(cmap, encoding="utf-8"))
    tk = json.load(io.open(os.path.join(HERE, "sec_company_tickers.json"), encoding="utf-8"))
    name2tk = {}
    for v in tk.values():
        name2tk.setdefault(norm(v["title"]), v["ticker"].upper())
    funds, by_ticker, problems = {}, {}, []
    for label, cik, must in FUNDS:
        sub = get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json")
        if not sub:
            problems.append(f"{label}: EDGAR submissions unreadable this run")
            continue
        j = json.loads(sub)
        if must not in j.get("name", "").upper():
            problems.append(f"{label}: CIK {cik} files as {j.get('name')!r}; skipped")
            continue
        r = j["filings"]["recent"]
        idx = next((i for i, f in enumerate(r["form"]) if f in ("13F-HR", "13F-HR/A") and r["form"][i] == "13F-HR"), None)
        if idx is None:
            problems.append(f"{label}: no 13F-HR in recent filings")
            continue
        acc, filed, period = r["accessionNumber"][idx], r["filingDate"][idx], r["reportDate"][idx]
        base = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc.replace('-', '')}"
        ix = get(base + "/index.json")
        xml = None
        if ix:
            for it in json.loads(ix).get("directory", {}).get("item", []):
                n = it["name"]
                if n.lower().endswith(".xml") and "primary_doc" not in n.lower():
                    xml = get(f"{base}/{n}")
                    if xml and "infoTable" in xml:
                        break
                    xml = None
        time.sleep(0.2)
        if not xml:
            problems.append(f"{label}: information table not found in {acc}")
            continue
        hold = {}
        for blk in re.findall(r"<(?:\w+:)?infoTable>(.*?)</(?:\w+:)?infoTable>", xml, re.S):
            def tag(t):
                m = re.search(rf"<(?:\w+:)?{t}>(.*?)</(?:\w+:)?{t}>", blk, re.S)
                return m.group(1).strip() if m else ""
            if tag("putCall"):
                continue
            if tag("sshPrnamtType").upper() not in ("SH", ""):
                continue
            cus = tag("cusip").upper()
            h = hold.setdefault(cus, {"issuer": tag("nameOfIssuer"), "shares": 0, "value": 0})
            h["shares"] += int(float(tag("sshPrnamt") or 0))
            h["value"] += int(float(tag("value") or 0))
        url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc.replace('-', '')}/{acc}-index.htm"
        funds[label] = {"cik": cik, "edgar_name": j.get("name"), "period": period, "filed": filed,
                        "accession": acc, "url": url, "positions": len(hold)}
        unmapped = 0
        for cus, h in hold.items():
            # an issuer-name match only for a common-stock CUSIP (issue number "10"): Perceptive's
            # 76155X118 (Revolution Medicines warrants) otherwise became a second "RVMD" line
            sym = cus2sym.get(cus) or (name2tk.get(norm(h["issuer"])) if cus[6:8] == "10" else None)
            if not sym:
                unmapped += 1
                continue
            by_ticker.setdefault(sym, []).append({"fund": label, "shares": h["shares"], "value_usd": h["value"],
                                                  "period": period, "filed": filed, "url": url,
                                                  "issuer": h["issuer"], "cusip": cus})
        # one line per fund per ticker: if two CUSIPs still map to one ticker, keep the common stock
        for sym, hs in list(by_ticker.items()):
            mine = [h for h in hs if h["fund"] == label]
            if len(mine) > 1:
                keep = next((h for h in mine if h["cusip"][6:8] == "10"), max(mine, key=lambda h: h["value_usd"]))
                by_ticker[sym] = [h for h in hs if h["fund"] != label] + [keep]
        funds[label]["unmapped_positions"] = unmapped
        print(f"  {label}: 13F-HR {acc} for {period}, filed {filed}: {len(hold)} long positions "
              f"({unmapped} without a ticker mapping)")
    data = {"read_at": dt.date.today().isoformat(),
            "note": ("Latest 13F-HR per fund from EDGAR, CIK checked against the EDGAR filer name. Long equity positions "
                     "at quarter end only; 13F filings are due 45 days after the quarter and show no shorts or "
                     "current positions."),
            "funds": funds, "by_ticker": by_ticker, "problems": problems,
            "rejected_source": ("Odin Perfection/v382_checkpoints/phase1_god_tier_holdings.json: latest quarter 2026-03-31; "
                                "CIKs for venBio 0001603466, Perceptive 0001224608 and Foresite 0001540531 belong to other "
                                "filers. Not published.")}
    if not funds:
        print("13F: no fund read this run; keeping the previous file")
        return 0
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
    print(f"13F specialists: {len(funds)} fund(s) read, {len(by_ticker)} tickers held"
          + (f"; problems: {problems}" if problems else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
