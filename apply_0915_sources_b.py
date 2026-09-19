# -*- coding: utf-8 -*-
"""Task #77 EDGAR/press pass, second batch -- every quote below was read from the document
before it was written here.

RHHBY x4 (Roche is not an SEC registrant; Genentech press releases are the sponsor's own statements):
  Tecentriq adjuvant dMMR/MSI-H colon      gene.com 2026-06-10  "expected to make a decision on the approval by October 9, 2026"
  Enspryng TED                             gene.com 2026-06-29  "expected to make a decision on approval by October 15, 2026"
  Giredestrant adjuvant (lidERA)           gene.com 2026-06-01  "expected to make a decision on the approval by November 30, 2026"
  Giredestrant + everolimus (evERA)        gene.com 2026-02-19  "expected to make a decision on the approval by December 18, 2026"
GSK bepirovirsen  Ionis (licensor) 8-K 2026-07-29: "Granted Priority Review in the U.S. and PDUFA target action date of October 26, 2026"
REGN cemdisiran   Regeneron 8-K 2026-07-30 (Q2 release): "target action date in November 2026, following use of a
                  Priority Review Voucher" -- a MONTH. The row carried day precision on November 30: a manufactured
                  month-end day of exactly the class the 09-10 P0 found. Downgraded to month, date_history records it.
                  The accepted NDA is cemdisiran (C5 RNAi) monotherapy for gMG; the row is renamed accordingly.
NUVL neladalkib   GSK completed its acquisition of Nuvalent in July 2026 (Nuvalent 8-K 2026-07-15, merger completion;
                  tender at $124/share commenced June 24). NUVL no longer trades. The row moves to ticker GSK with the
                  former ticker recorded; the PDUFA date is sourced to Royalty Pharma's 8-K of 2026-08-05, which quotes
                  Nuvalent's May 2026 announcement ("Priority Review with a PDUFA date of November 27, 2026") -- the
                  sponsor's own May release is not in EDGAR full-text under that phrasing.
"""
import io, json, os, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
DATASET = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")
G = "https://www.gene.com/media/press-releases/"
S = {
 "pdufa_rhhby_2026-10-09": ("Genentech press release 2026-06-10", G + "15116/2026-06-10/fda-grants-priority-review-for-genentech",
     "The FDA has granted Priority Review and is expected to make a decision on the approval by October 9, 2026."),
 "pdufa_rhhby_2026-10-15": ("Genentech press release 2026-06-29", G + "15118/2026-06-29/fda-grants-priority-review-to-genentechs",
     "The FDA is expected to make a decision on approval by October 15, 2026."),
 "pdufa_rhhby_2026-11-30": ("Genentech press release 2026-06-01", G + "15115/2026-06-01/fda-accepts-new-drug-application-for-gen",
     "The FDA is expected to make a decision on the approval by November 30, 2026."),
 "pdufa_rhhby_2026-12-18": ("Genentech press release 2026-02-19", G + "15100/2026-02-19/fda-accepts-new-drug-application-for-gen",
     "The FDA is expected to make a decision on the approval by December 18, 2026."),
 "pdufa_gsk_2026-10-26": ("Ionis (licensor) 8-K 2026-07-29 (EX-99.1)",
     "https://www.sec.gov/Archives/edgar/data/874015/000114036126029960/ef20078953_ex99-1.htm",
     "Granted Priority Review in the U.S. and PDUFA target action date of October 26, 2026"),
}
src = io.open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
i, j = src.index("["), src.rindex("]") + 1
rows = json.loads(src[i:j])
n = 0
for r in rows:
    dd = r.setdefault("_d", {})
    if r["id"] in S:
        label, url, quote = S[r["id"]]
        dd["source"], dd["source_url"], dd["source_quote"] = label, url, quote
        n += 1; print(f"  {r['id']}: {label}")
    elif r["id"] == "pdufa_regn_2026-11-30":
        assert r["d"] == "2026-11-30" and r["dp"] == "day"
        r["dp"] = "month"; r["dm"] = "2026-11"
        r["name"] = "Cemdisiran (C5 RNAi) - (NIMBLE)"
        dd["indication"] = "Generalized myasthenia gravis (gMG), anti-AChR antibody-positive"
        dd["source"] = "Regeneron 8-K 2026-07-30 (EX-99.1, Q2 2026 results)"
        dd["source_url"] = "https://www.sec.gov/Archives/edgar/data/872589/000087258926000023/exhibit991q22026.htm"
        dd["source_quote"] = ("The FDA will review the New Drug Application (NDA) under priority review with a target "
                              "action date in November 2026, following use of a Priority Review Voucher.")
        dd["date_note"] = ("Regeneron states the target action date as November 2026, a month. The November 30 day this "
                           "row carried was a month-end sentinel no filing states; precision downgraded to month 2026-09-15.")
        dd["date_history"] = [{"date": "2026-11-30", "note": "day the row was keyed on; a month-end sentinel, not a stated day"},
                              {"date": "2026-11-30", "changed": "2026-09-15", "url": dd["source_url"],
                               "why": "Precision downgraded from day to month: Regeneron's 8-K of 2026-07-30 states 'a target action date in November 2026' and no filing states a day."}]
        n += 1; print(f"  {r['id']}: day -> month, renamed, sourced")
    elif r["id"] == "pdufa_nuvl_2026-11-27":
        assert r["t"] == "NUVL"
        r["t"] = "GSK"; r["company"] = "GSK plc (acquired Nuvalent, July 2026)"
        r["cap"] = "Large"
        dd["former_ticker"] = "NUVL"
        dd["acquisition"] = {"acquirer": "GSK plc", "completed": "2026-07", "price_per_share_usd": 124.0,
                             "source_url": "https://www.sec.gov/Archives/edgar/data/1861560/000119312526304126/d52896d8k.htm",
                             "note": "Nuvalent 8-K 2026-07-15 (merger completion); tender offer commenced 2026-06-24 at $124.00 per share. NUVL no longer trades."}
        dd["source"] = "Royalty Pharma 8-K 2026-08-05 (EX-99.1), quoting Nuvalent's May 2026 NDA-acceptance announcement"
        dd["source_url"] = "https://www.sec.gov/Archives/edgar/data/1802768/000180276826000014/rprx-20260630rpplcpressxre.htm"
        dd["source_quote"] = ("In May 2026, Nuvalent announced the FDA accepted its NDA for neladalkib for filing and granted the "
                              "application Priority Review with a Prescription Drug User Fee Act (PDUFA) date of November 27, 2026.")
        n += 1; print(f"  {r['id']}: NUVL -> GSK (acquired), sourced")
io.open(DATASET, "w", encoding="utf-8").write(src[:i] + json.dumps(rows, indent=1, ensure_ascii=False) + src[j:])
print(f"{n} row(s)")
