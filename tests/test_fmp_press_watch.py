# -*- coding: utf-8 -*-
"""test_fmp_press_watch.py -- the 15-minute press-release watcher hears the decisions the rebuild heard late or never.

Audit 2026-11-26 (news speed). The fixtures are the sponsors' own releases as FMP's press-release feed carried
them (publishedDate is Eastern), replayed against each row as it stood BEFORE its decision: status Upcoming and
no brand name yet (a brand is usually first made public in the approval release itself).

Must raise a lead (each was late or missed on the site):
  CAPR  "Provides Regulatory Update on Deramiocel BLA" (Nov 20, 7:55 PM ET): no decision word in the headline;
        the CRL is in the first sentence. No watcher raised it; the site showed it 13 h later.
  COGT  "Announces FDA Approval and Launch of EKITNA (bezuclastinib)" (Nov 24, 9:27 AM ET)
  PYPD  "FDA Approval of BACFENSSI (D-PLEX<subscript 100>)" (Nov 24, 3:50 PM ET): subscript digits
  BBIO  "Welgemda (BBP-418, Ribitol) Receives Traditional Approval" (Nov 23, 4:20 PM ET): no "FDA" in the headline
  RHHBY "FDA Approves Genentech's WILSERDLY (giredestrant)" (Nov 23, 12:00 PM ET); on site 35 h later
  REGN  "Livsayis (cemdisiran) Approved by the FDA" (Nov 18, 6:03 PM ET)
Must NOT raise a lead:
  product boilerplate naming an approved drug ("EKITNA (bezuclastinib) is approved by the FDA ...") against
  Cogent's next armed goal; an acceptance release with a PDUFA target date; a European approval headline;
  an acquisition; an acked lead.
PLANT=headline drops the sentence rule (CAPR must then be missed, so the test FAILS); PLANT=boiler drops the
news-verb guard (the boilerplate must then raise a lead, so the test FAILS); PLANT=narrow drops the
same-drug narrowing (the GIST approval must then lead on the mastocytosis row, so the test FAILS).

    python tests/test_fmp_press_watch.py
"""
import copy
import io
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import watch_fmp_press as F  # noqa: E402

GNW = "https://www.globenewswire.com/news-release/"
ITEMS = [
    {"symbol": "CAPR", "publishedDate": "2026-11-20 19:55:00", "publisher": "GlobeNewsWire",
     "title": "Capricor Therapeutics Provides Regulatory Update on Deramiocel BLA for Duchenne Muscular Dystrophy",
     "text": "SAN DIEGO, Nov. 20, 2026 (GLOBE NEWSWIRE) -- Capricor Therapeutics (NASDAQ: CAPR), a biotechnology company "
             "developing transformative cell and exosome-based therapeutics for rare diseases, today announced that it "
             "received a Complete Response Letter (CRL) from the U.S. Food and Drug Administration (FDA) for its "
             "resubmitted Biologics License Application (BLA) for Deramiocel, its investigational cell therapy for "
             "Duchenne muscular dystrophy (DMD). The CRL states that the FDA does not consider the data sufficient.",
     "url": GNW + "2026/11/21/3407877/0/en/capricor.html"},
    {"symbol": "COGT", "publishedDate": "2026-11-24 09:27:00", "publisher": "GlobeNewsWire",
     "title": "Cogent Biosciences Announces FDA Approval and Launch of EKITNA™ (bezuclastinib) for the Treatment of "
              "Patients with Gastrointestinal Stromal Tumors (GIST) Who Have Received Prior Treatment with Imatinib",
     "text": "FDA approval based on results from pivotal Phase 3 PEAK trial",
     "url": GNW + "2026/11/24/3409390/0/en/cogent.html"},
    {"symbol": "PYPD", "publishedDate": "2026-11-24 15:50:00", "publisher": "GlobeNewsWire",
     "title": "PolyPid Announces FDA Approval of BACFENSSI® (D-PLEX₁₀₀) to Reduce the Occurrence of "
              "Surgical Site Infections in Patients Undergoing Colorectal Surgery",
     "text": "BACFENSSI is the first FDA-approved locally applied, extended-release antibiotic indicated to reduce the "
             "occurrence of surgical site infections in colorectal surgery",
     "url": GNW + "2026/11/24/3409851/0/en/polypid.html"},
    {"symbol": "BBIO", "publishedDate": "2026-11-23 16:20:00", "publisher": "GlobeNewsWire",
     "title": "Welgemda™ (BBP-418, Ribitol) Receives Traditional Approval as the First and Only Treatment for "
              "Individuals Living with LGMD2I/R9",
     "text": "- Welgemda is the first and only FDA-approved therapy for individuals living with LGMD2I/R9 (FKRP-related)",
     "url": GNW + "2026/11/23/3408902/0/en/welgemda.html"},
    {"symbol": "RHHBY", "publishedDate": "2026-11-23 12:00:00", "publisher": "Business Wire",
     "title": "FDA Approves Genentech's WILSERDLY (giredestrant) for Early-Stage ER-Positive Breast Cancer, Making it "
              "the First New Endocrine Therapy in This Setting in Over 20 Years",
     "text": "WILSERDLY (giredestrant), is now the first and only oral SERD approved by the FDA for ER-positive, "
             "HER2-negative early-stage breast cancer.",
     "url": "https://www.businesswire.com/news/home/20261120512315/en/wilserdly"},
    {"symbol": "REGN", "publishedDate": "2026-11-18 18:03:00", "publisher": "GlobeNewsWire",
     "title": "Livsayis™ (cemdisiran) Approved by the FDA as First and Only siRNA Therapy in Generalized Myasthenia "
              "Gravis and Only Treatment with Four-Times-a-Year Subcutaneous Dosing",
     "text": "Approval based on Phase 3 NIMBLE results",
     "url": GNW + "2026/11/18/3406224/0/en/livsayis.html"},
    # ---- must not raise a lead ----
    {"symbol": "COGT", "publishedDate": "2026-11-25 08:00:00", "publisher": "GlobeNewsWire",
     "title": "Cogent Biosciences to Present at the Piper Sandler Healthcare Conference",
     "text": "EKITNA (bezuclastinib) is approved by the FDA for adults with GIST after imatinib. Bezuclastinib is also "
             "under FDA review for systemic mastocytosis.",
     "url": GNW + "2026/11/25/0000001/0/en/cogent-piper.html"},
    {"symbol": "VRTX", "publishedDate": "2026-07-01 07:00:00", "publisher": "Business Wire",
     "title": "Vertex Announces FDA Acceptance of BLA for Povetacicept for Priority Review",
     "text": "Vertex today announced that the FDA has accepted for priority review the BLA seeking approval of "
             "povetacicept, with a PDUFA target action date of November 30, 2026. If approved, povetacicept would be "
             "the first therapy of its kind.",
     "url": "https://www.businesswire.com/news/home/0000002/en/vertex-acceptance"},
    {"symbol": "VRTX", "publishedDate": "2026-11-20 07:00:00", "publisher": "Business Wire",
     "title": "Povetacicept Receives European Commission Approval for IgA Nephropathy",
     "text": "Vertex today announced the European Commission granted approval for povetacicept.",
     "url": "https://www.businesswire.com/news/home/0000003/en/vertex-ec"},
    {"symbol": "SNY", "publishedDate": "2026-11-24 01:30:00", "publisher": "PRNewsWire",
     "title": "Sanofi to Acquire Insmed in Strategic Step that Strengthens Long-Term Future",
     "text": "Sanofi will pay $175 per share, for a total consideration of $41.0 billion in cash.",
     "url": "https://www.prnewswire.com/news-releases/sanofi-insmed.html"},
]
MUST = {"pdufa_capr_2026-08-22", "pdufa_cogt_2026-11-30", "pdufa_pypd_2026-11-28", "pdufa_bbio_2026-11-27",
        "pdufa_rhhby_2026-11-30", "pdufa_regn_2026-11-30"}
QUIET = {"pdufa_cogt_2026-12-30", "pdufa_vrtx_2026-11-30"}


def armed_before_decision():
    rows = {r["id"]: r for r in F.load_rows()}
    out = []
    for rid in sorted(MUST | QUIET):
        r = copy.deepcopy(rows[rid])
        r["st"] = "Upcoming"
        r.setdefault("_d", {})
        (r["_d"] or {}).pop("brand", None)      # the brand is usually first public in the approval release
        out.append(r)
    by_tk = {}
    for r in out:
        by_tk.setdefault(str(r["t"]).upper(), []).append(r)
    return by_tk


def main():
    plant = os.environ.get("PLANT", "")
    if plant == "headline":
        F.sentence_hits = lambda text, rows: []
    if plant == "narrow":
        F.narrow = lambda found, text, siblings: found
    if plant == "boiler":
        F.NEWS = __import__("re").compile(r".")
    bad = []
    by_tk = armed_before_decision()
    leads = F.leads_for(ITEMS, by_tk, ack=[])
    hit = {}
    for r, t, it, why, key in leads:
        hit.setdefault(r["id"], []).append((it["symbol"], it["title"][:60], why[:60]))
    for rid in sorted(MUST):
        if rid not in hit:
            bad.append(f"MISSED: {rid} -- the sponsor's release did not raise a lead")
    for rid in sorted(QUIET):
        if rid in hit:
            bad.append(f"FALSE LEAD: {rid} <- {hit[rid]}")
    acked = [k for r, t, it, why, k in leads if r["id"] == "pdufa_capr_2026-08-22"]
    if acked and any(r["id"] == "pdufa_capr_2026-08-22" for r, *_ in F.leads_for(ITEMS, by_tk, ack=acked)):
        bad.append("an acked lead was raised again")
    # the live case: Cogent's GIST row is already Decided, only the systemic mastocytosis row is armed. The
    # GIST approval release must not raise a lead on the mastocytosis row through the shared drug name.
    rows = {r["id"]: r for r in F.load_rows()}
    gist = copy.deepcopy(rows["pdufa_cogt_2026-11-30"]); gist["st"] = "Decided"
    sm = [r for r in by_tk["COGT"] if r["id"] == "pdufa_cogt_2026-12-30"]
    live = F.leads_for([ITEMS[1]], {"COGT": sm}, ack=[], all_by_tk={"COGT": sm + [gist]})
    if live:
        bad.append(f"FALSE LEAD (live): the GIST approval raised a lead on {[l[0]['id'] for l in live]}")
    # every lead must carry the release's Eastern timestamp and its link for the reviewer
    for r, t, it, why, key in leads:
        if not it.get("url") or it["url"] not in key:
            bad.append(f"{r['id']}: lead key does not carry the release link")
    print(f"{len(ITEMS)} releases replayed against {sum(len(v) for v in by_tk.values())} armed rows; "
          f"{len(leads)} lead(s) on {len(hit)} row(s)")
    if bad:
        print("FAIL")
        for b in bad:
            print("  " + b)
        return 1
    print("  PASS: all six late or missed decisions raise a lead within one run; boilerplate, acceptance, "
          "EU approval and acquisition releases do not")
    return 0


if __name__ == "__main__":
    sys.exit(main())
