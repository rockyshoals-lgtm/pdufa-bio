# -*- coding: utf-8 -*-
"""apply_1117_acks.py -- watcher leads of Nov 15-16 recorded (published, or not this row's decision). Facts only."""
import io, json, os
H = os.path.dirname(os.path.abspath(__file__))
GIR_FDA = "http://www.fda.gov/drugs/cancer-approvals/fda-approves-giredestrant-combination-everolimus-er-positive-her2-negative-esr1-mutated-locally"
GENE_W = "https://www.gene.com/media/press-releases/15144/2026-11-16/fda-approves-genentechs-wilserdly-girede"
GENE_G = "https://www.gene.com/media/press-releases/15143/2026-11-15/genentechs-gazyva-becomes-the-first-fda-"
def jl(p, d):
    p = os.path.join(H, p); return json.load(io.open(p, encoding="utf-8")) if os.path.exists(p) else d
def js(p, o):
    io.open(os.path.join(H, p), "w", encoding="utf-8").write(json.dumps(o, indent=1, ensure_ascii=False) + "\n")

nw = jl("_newswire_ack.json", {"acked": []})
for k in (f"pdufa_rhhby_2026-11-30|{GENE_W}",      # evERA (Wilserdly) approval; lidERA is a different application, still pending
          f"pdufa_rhhby_2026-12-18|{GENE_W}",      # published: /fda-decision/RHHBY-2026-11-16
          f"pdufa_rhhby_2026-12-31_sle|{GENE_G}"):  # Gazyva pMN (published Nov 13); the SLE sBLA is separate
    if k not in nw["acked"]:
        nw["acked"].append(k)
js("_newswire_ack.json", nw)

ff = jl("_fda_drugs_feed_ack.json", {"acked": [], "reasons": {}})
for k, why in ((f"pdufa_rhhby_2026-11-30|{GIR_FDA}", "evERA (giredestrant + everolimus, Wilserdly) approval Nov 16, 2026; the lidERA row is a different application, goal Nov 30, still pending."),
               (f"pdufa_rhhby_2026-12-18|{GIR_FDA}", "Published 2026-11-17: /fda-decision/RHHBY-2026-11-16.")):
    if k not in ff["acked"]:
        ff["acked"].append(k)
    ff.setdefault("reasons", {})[k] = why
js("_fda_drugs_feed_ack.json", ff)

dw = jl("_drug_watch_ack.json", {"acks": []})
for src, why in (("fda-oncology-notifications", "Published 2026-11-17: Wilserdly (giredestrant) + everolimus approved Nov 16, 2026, /fda-decision/RHHBY-2026-11-16. lidERA (Nov 30) still pending."),
                 ("sponsor:RHHBY:2026-11-16", "Published 2026-11-17: the evERA approval; lidERA still pending.")):
    if not any(a.get("slug") == "giredestrant" and a.get("source") == src for a in dw["acks"]):
        dw["acks"].append({"slug": "giredestrant", "source": src, "reason": why, "acked": "2026-11-17"})
js("_drug_watch_ack.json", dw)

ek = jl("_edgar_8k_ack.json", {"acked": []})
if "pdufa_smmt_2026-11-14|0001599298-26-000092" not in ek["acked"]:
    ek["acked"].append("pdufa_smmt_2026-11-14|0001599298-26-000092")
js("_edgar_8k_ack.json", ek)
print("acks written")
