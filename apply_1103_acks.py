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
io.open(p, "w", encoding="utf-8").write(json.dumps(f, indent=1, ensure_ascii=False) + "\n")
print("acked #58")
