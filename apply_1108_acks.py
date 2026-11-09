# -*- coding: utf-8 -*-
"""apply_1108_acks.py -- held leads #61, #64-#66, #68 (2026-11-08), each checked against the primary source.

#61 COGT 8-K Nov 5: restates the Nov 30 (GIST) and Dec 30 (NonAdvSM) PDUFA dates and adds AdvSM June 29, 2027
    (now a row); not an approval.
#68 MLYS 8-K Nov 4: restates the Dec 22 lorundrostat PDUFA date ("ahead of PDUFA target date"); not an approval.
#64 FDA Nov 6: atezolizumab and hyaluronidase-tqjs (Roche) matched JAZZ's capsule NDA on the word "formulation".
#65 FDA Nov 6: isatuximab-irfc + VRd (Sanofi) matched BMY's mezigdomide row on "dexamethasone".
#66 FDA Nov 6: belantamab mafodotin-blmf (GSK) matched BMY's mezigdomide row on "dexamethasone".
"""
import io, json
A = "_fda_watch_ack.json"
f = json.load(io.open(A, encoding="utf-8"))
for tk, k, why in (
        ("COGT", "edgar:https://www.sec.gov/Archives/edgar/data/1622229/000119312526449926/cogt-ex99_1.htm",
         "Q3 2026 results restate the GIST (Nov 30, 2026) and NonAdvSM (Dec 30, 2026) PDUFA dates and add AdvSM (Jun 29, 2027); no approval."),
        ("MLYS", "edgar:https://www.sec.gov/Archives/edgar/data/1933414/000193341426000142/mlys2026q38kex991.htm",
         "Q3 2026 results restate the Dec 22, 2026 lorundrostat PDUFA date; no approval.")):
    if not any(a["ticker"] == tk and a["ap_date"] == k for a in f["acks"]):
        f["acks"].append({"ticker": tk, "ap_date": k, "reason": why})
io.open(A, "w", encoding="utf-8").write(json.dumps(f, indent=1, ensure_ascii=False) + "\n")

B = "_fda_drugs_feed_ack.json"
g = json.load(io.open(B, encoding="utf-8"))
reasons = g.setdefault("reasons", {})
for k, why in (
        ("pdufa_jazz_2027-04-16|http://www.fda.gov/drugs/cancer-approvals/fda-approves-atezolizumab-and-hyaluronidase-tqjs-subcutaneous-injection",
         "Roche's subcutaneous atezolizumab, matched on 'formulation'; JAZZ's cannabidiol capsule NDA (Apr 16, 2027) is unrelated and pending."),
        ("pdufa_bmy_2027-05-13|http://www.fda.gov/drugs/cancer-approvals/fda-approves-isatuximab-irfc-bortezomib-lenalidomide-and-dexamethasone-newly-diagnosed-multiple",
         "Sanofi's isatuximab regimen, matched on 'dexamethasone'; BMY's mezigdomide NDA (May 13, 2027) is unrelated and pending."),
        ("pdufa_bmy_2027-05-13|http://www.fda.gov/drugs/cancer-approvals/fda-approves-belantamab-mafodotin-blmf-relapsed-or-refractory-multiple-myeloma",
         "GSK's belantamab mafodotin, matched on 'dexamethasone'; BMY's mezigdomide NDA (May 13, 2027) is unrelated and pending.")):
    if k not in g["acked"]:
        g["acked"].append(k)
    reasons[k] = why
io.open(B, "w", encoding="utf-8").write(json.dumps(g, indent=1, ensure_ascii=False) + "\n")
print("acked #61 #64 #65 #66 #68")
