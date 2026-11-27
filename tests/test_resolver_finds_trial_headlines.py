"""Guard (2026-11-27): resolve_past_readouts.py must see a sponsor's whole release history for a passed window,
and must recognise a topline headline that names the trial and the disease but not the drug.

Karyopharm announced XPORT-EC-042 topline results on Jul 30, 2026 ("Topline Results from Phase 3 XPORT-EC-042
Trial in Endometrial Cancer"), yet /readouts showed the selinexor endometrial row as "no topline". Two causes:
(1) FMP's press-release search, asked without a date range, returned only the last few months (7 releases);
(2) the headline never names selinexor. This test replays Karyopharm's real 2026 headlines (titles and dates as
FMP lists them), and a Cardiff Oncology colorectal headline against its pancreatic trial, against the matcher and checks the request carries a from-date and pages. No network."""
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import resolve_past_readouts as R  # noqa: E402

PRS = [  # (title, body excerpt, published, url) newest first, as FMP returns them
    ("Karyopharm to Present Selinexor Data in Patients with Myelofibrosis and Multiple Myeloma at the 68th American "
     "Society of Hematology Annual Meeting and Exposition (ASH)", "abstracts evaluating selinexor in myelofibrosis",
     "2026-11-04", "u1"),
    ("Karyopharm Plans to Submit sNDA for Selinexor Plus Ruxolitinib in Myelofibrosis Under Accelerated Approval "
     "Pathway", "selinexor in combination with ruxolitinib", "2026-07-30", "u2"),
    ("Karyopharm Announces Topline Results from Phase 3 XPORT-EC-042 Trial in Endometrial Cancer",
     "topline results from its Phase 3 XPORT-EC-042 trial evaluating selinexor as a maintenance-only therapy "
     "compared to placebo in adult patients with TP53 wild-type advanced or recurrent endometrial cancer",
     "2026-07-30", "u3"),
    ("Karyopharm's Phase 3 SENTRY Trial in Myelofibrosis Met First Co-Primary Endpoint, Demonstrating Statistically "
     "Significant Improvement in Spleen Volume Reduction", "selinexor plus ruxolitinib in JAK inhibitor-naive "
     "myelofibrosis", "2026-03-24", "u4"),
]


def row(nct_title, name="Selinexor"):
    return {"t": "KPTI", "name": name, "type": "Readout", "st": "Estimated",
            "_d": {"nct_id": {"nct": "NCT0", "title": nct_title}}}


EC042 = row("A Phase 3, Randomized, Placebo-Controlled, Double-Blind, Multicenter Trial of Selinexor in Maintenance "
            "Therapy After Systemic Therapy for Patients With p53 Wild-Type, Advanced or Recurrent Endometrial Carcinoma")
SENTRY2 = row("A Phase 2, Randomized, Open-Label, Multicenter Study to Evaluate Safety and Efficacy of Single Agent "
              "Selinexor Versus Treatment of Physician's Choice in Patients With Previously Treated Myelofibrosis")


CRDF_PRS = [("Cardiff Oncology Announces Presentation of Positive Results from its Randomized, Controlled Phase 2 Trial "
             "of Onvansertib in First-Line RAS-Mutated mCRC at the 2026 ASCO Annual Meeting",
             "onvansertib in combination with standard of care in first-line RAS-mutated mCRC", "2026-06-02", "c1")]
CRDF_PANC = row("A Phase 1b/2 Trial of Onvansertib in Combination With NALIRIFOX for First Line Treatment of Advanced "
                "Pancreatic Cancer", name="Onvansertib")


def main():
    bad = []
    hit = R.match_release(CRDF_PANC, CRDF_PRS, R.drug_tokens(CRDF_PANC), "2026-05-17", True)
    if hit:
        bad.append(f"an onvansertib colorectal results headline must not resolve its pancreatic trial: {hit}")
    hit = R.match_release(EC042, PRS, R.drug_tokens(EC042), "2026-03-17", True)
    if not hit or hit[2] != "u3":
        bad.append(f"XPORT-EC-042 row should resolve to the Jul 30 topline release, got {hit}")
    hit = R.match_release(SENTRY2, PRS, R.drug_tokens(SENTRY2), "2026-07-18", True)
    if hit:
        bad.append(f"SENTRY-2 (Phase 2, myelofibrosis) must not take another trial's release: {hit}")
    hit = R.match_release(SENTRY2, PRS, R.drug_tokens(SENTRY2), "2026-01-15", True)
    if hit:
        bad.append(f"a Phase 3 SENTRY headline must not resolve the Phase 2 SENTRY-2 row: {hit}")

    # the fetch asks for a date range and pages until a short page
    seen = []

    class Resp:
        def __init__(self, n):
            self.n = n

        def read(self):
            return json.dumps([{"title": f"t{len(seen)}-{i}", "publishedDate": "2026-05-01", "text": ""}
                               for i in range(self.n)]).encode()

    def fake_open(req, timeout=0):
        seen.append(req.full_url)
        return Resp(100 if len(seen) == 1 else 3)

    orig, R.urllib.request.urlopen = R.urllib.request.urlopen, fake_open
    orig_sleep, R.time.sleep = R.time.sleep, lambda *_: None
    try:
        out = R.fetch_prs("KPTI", "k", since="2026-01-01")
    finally:
        R.urllib.request.urlopen, R.time.sleep = orig, orig_sleep
    if not seen or "from=2026-01-01" not in seen[0]:
        bad.append(f"press-release fetch must pass from=<earliest window - 45 days>: {seen[:1]}")
    if len(seen) != 2 or "page=1" not in seen[-1] or len(out) != 103:
        bad.append(f"press-release fetch must page until a short page: {len(seen)} request(s), {len(out)} release(s)")

    # 2026-11-27: a sponsor that reports BEFORE the registry window (Humacyte V012 at a prespecified interim, Jun 10,
    # 2026; window Jun 2027) must surface as a lead, and the lead pass must never change the row itself.
    import datetime as dt
    huma = {"id": "readout_huma_x", "t": "HUMA", "name": "ATEV (human acellular vessel)", "type": "Readout",
            "st": "Estimated", "d": "2099-06-15", "dm": "2099-06", "dp": "month",
            "_d": {"nct_id": {"nct": "NCT05908084", "title": "A Phase 3 Randomized Study to Compare the Efficacy and "
                              "Safety of the Humacyte Acellular Tissue Engineered Vessel (ATEV) With That of an "
                              "Autogenous Arteriovenous Fistula (AVF) in Female Patients With End-Stage Renal Disease "
                              "Requiring Hemodialysis"}}}
    huma_prs = [("Humacyte ATEV Met Superiority Primary Endpoint Compared to Standard of Care AV Fistula in Interim "
                 "Analysis of V012 Phase 3 Study in Female Dialysis Access Patients",
                 "ATEV compared to autogenous arteriovenous fistula in female patients requiring hemodialysis",
                 "2026-06-10", "h1")]
    before = json.dumps(huma, sort_keys=True)
    orig_out, R.EARLY_LEADS = R.EARLY_LEADS, os.devnull
    orig_sleep, R.time.sleep = R.time.sleep, lambda *_: None
    try:
        leads = R.early_leads([huma], "k", {}, fetch=lambda *a, **k: huma_prs, today=dt.date(2026, 11, 27))
    finally:
        R.EARLY_LEADS, R.time.sleep = orig_out, orig_sleep
    if [x.get("url") for x in leads] != ["h1"]:
        bad.append(f"an early primary-endpoint release must be listed as a lead for its future-window row: {leads}")
    if json.dumps(huma, sort_keys=True) != before:
        bad.append("the early-lead pass must never change a row")

    if bad:
        print("FAIL -- the past-readout resolver would miss or mis-assign a sponsor's results release:")
        for b in bad:
            print("  " + b)
        sys.exit(1)
    print("OK -- resolver sees the whole release history and matches trial-and-disease topline headlines safely.")


if __name__ == "__main__":
    main()
