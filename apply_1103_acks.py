# -*- coding: utf-8 -*-
"""apply_1103_acks.py -- held lead #58 (2026-11-03): not an approval."""
import io, json
p = "_fda_watch_ack.json"
f = json.load(io.open(p, encoding="utf-8"))
k = "edgar:https://www.sec.gov/Archives/edgar/data/875320/000087532026000287/ex-991_q32026.htm"
if not any(a["ap_date"] == k for a in f["acks"]):
    f["acks"].append({"ticker": "VRTX", "ap_date": k, "reason": (
        "Vertex Q3 2026 results (8-K 2026-11-02) restate the pending povetacicept PDUFA date of November 30, 2026 "
        "('potential povetacicept approval in IgAN coming later this month'); not an approval.")})
# #60: openFDA AP 2026-10-14 on clesrovimab, BLA 761432 S-3. The FDA's letter (761432Orig1s003ltr.pdf) says the
# supplement updates injection-site erythema/swelling rates in Adverse Reactions; it is not the second-season sBLA
# (Merck 8-K 2026-10-29: PDUFA March 22, 2027), which stays pending.
if not any(a["ticker"] == "MRK" and a["ap_date"] == "2026-10-14" for a in f["acks"]):
    f["acks"].append({"ticker": "MRK", "ap_date": "2026-10-14", "reason": (
        "ENFLONSIA BLA 761432 S-3 (FDA letter 2026-10-14): safety labeling update (injection-site reaction rates), "
        "not the second-RSV-season sBLA, whose PDUFA date is March 22, 2027 (Merck 8-K 2026-10-29).")})
io.open(p, "w", encoding="utf-8").write(json.dumps(f, indent=1, ensure_ascii=False) + "\n")
print("acked #58, #60")
