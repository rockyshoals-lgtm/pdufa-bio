# BUILDER → RED TEAM, 2026-09-14

**The autonomous run had been failing for three days. It was not broken — it was refusing to
publish past four unverified FDA approvals.** Shipped as `39ccedf76`, live-verified, 81 guards
pass, CI unblocked.

---

## 1. Why the site went stale

Seven consecutive CI runs failed from 2026-09-11 22:54, every one stuck on the same SHA, so
nothing rebuilt for three days. The failing step was:

```
EARLY-APPROVAL WATCH: 2 unreviewed FDA-feed approval(s) on armed events
##[error]Process completed with exit code 1
```

That is `watch_fda_approvals.py` doing exactly what it was built to do — exiting 1 so a human
verifies a lead before anything is published. **The watcher was right. Nobody came.** Every
stale surface David saw was downstream of that one honest refusal: conference statuses never
rolled, the SLS collector went 8 days without running, prices went 10 days stale, and four FDA
decisions went unpublished.

Worth saying plainly: a blocking guard with nobody watching it converts one unverified lead
into a site-wide staleness outage. The guard is still right to block. The gap is that nothing
escalates when it blocks repeatedly.

---

## 2. The four decisions, each verified first-hand

**SRRK apitegromab → ISEMBYLD, SMA, approved September 11.** Scholar Rock 8-K 2026-09-14,
accession `0001104659-26-107273`: *"Scholar Rock Announces FDA Approval of ISEMBYLD™
(apitegromab-mstn), the First and Only Muscle-Targeted Treatment for Children and Adults with
Spinal Muscular Atrophy (SMA) … September 11, 2026."* Its goal date was September 30 and **is**
sourced — I sourced it myself on 09-10 — so the 19-day gap is a real measurement and enters the
timing statistic legitimately. Pleasing symmetry: four days ago I proved that Sept 30 was a
genuine sponsor-stated day rather than a quarter-end placeholder, and the drug then approved
early against it.

**PHAR leniolisib → Joenja for children with APDS, approved September 11.** Pharming 6-K
2026-09-11. Goal October 24, sourced to Pharming's 6-K of 2026-06-04: *"The FDA has assigned a
Prescription Drug User Fee Act (PDUFA) target action date of October 24, 2026."* A resubmission
covering patients ≥27 kg. 43 days early.

**BFRI Ameluz PDT → superficial basal cell carcinoma. Two dates, five days apart.** openFDA
records NDA 208081 SUPPL-40 as approved **2026-09-09**; Biofrontera did not announce until
**2026-09-14**. `dcd` is the FDA's action date, but the decision page says both, because no
share-price move before the 14th can be a reaction to an approval nobody knew about. Goal
September 28, sourced to Biofrontera's 8-K of 2026-05-14.

**BAYRY sevabertinib → HYRNUO, HER2-mutant NSCLC, accelerated approval September 9.** Read in
the FDA's own letter for NDA 219972/S-001: *"This 'Prior Approval' sNDA provides for the use of
Hyrnuo (sevabertinib) for … locally advanced or metastatic non-squamous NSCLC whose tumors have
HER2 (ERBB2) tyrosine kinase domain (TKD) activating mutations."* Two things follow. First, the
original NDA was approved 2025-11-19, so this expands a marketed drug. Second, **our goal date
of November 30 was never sourced** — no Bayer filing states it, Bayer is not an SEC registrant,
and the only EDGAR hits for "sevabertinib" + "target action date" are *Nuvalent's*, discussing
a competitor. The FDA letter shows the sNDA was received March 16, which under priority review
lands in September, not November. So the day is withdrawn and the page **states no earliness
figure at all**. Same rule as 09-10: no sourced goal, no earliness claim.

**Two acked as non-events.** `check_pdufa_decided` matches a ticker's approval release against
that ticker's forward rows, which reaches across applications: GILD 2027-02-02 is once-weekly
oral Yeztugo (the Aug 27 Bixlenvo approval is already published), ARQT 2027-02-23 is ZORYVE
0.05% for infants (the Jun 29 approval was 0.3% paediatric psoriasis). Arcutis' own 8-K names
both separately.

---

## 3. Readouts: 50 rows past their date

33 `Estimated` windows were re-synced to ClinicalTrials.gov, 22 primary-completion dates are now
ACTUAL rather than estimated, and 4 terminated or withdrawn trials are annotated. One row had
been advertising a **September 2027** readout for a trial whose primary completion was
**September 2023** and whose results were posted in March 2025.

The justification is narrow and I want it on the record: /readouts says in its own words that
these dates are *"estimated primary-completion windows from ClinicalTrials.gov"*. The date **is**
the registry's field, so re-syncing it keeps a field equal to its own definition rather than
making a new editorial claim.

**No outcome was set anywhere.** A registry status of COMPLETED means the trial finished, not
that the sponsor has said what happened. All 22 remain leads for the company's own release
(task 52, now 22 not 19). Terminated ones first: CALC CM4620, SNGX hypericin, JSPR briquilimab,
IMMP eftilagimod alfa.

### I got this wrong on the first pass

My script skipped only `Reported` rows, so it also rewrote company-**Guided** dates — replacing
SELLAS's own REGAL Phase 3 guidance with NCT04229979's registry number, and doing the same to
CRIS. That is precisely backwards: a sourced company statement overwritten by a number the
company never gave. `test_guided_readouts_current` caught it. Both restored from HEAD, and the
script is now gated on `st == "Estimated"`. An Estimated row's date is the registry's; a Guided
row's date is the company's, and the registry has no authority over it.

---

## 4. TLX: a countdown that ran out

The PDUFA goal date for TLX101-Px (Pixclara) passed on September 11 with no decision disclosed.
`/api/v1` already handled this — `_lib.mjs` relabels a past-dated Upcoming PDUFA as "Awaiting" —
but **the calendar did not**, so the busiest page on the site showed `TLX · 2026-09-11` looking
exactly like a live date. Two surfaces, one truth, again.

Fixed generally rather than for TLX: `mark_calendar_awaiting.py` applies the API's own rule to
every calendar page, `tests/test_awaiting_marked_on_calendar.py` enforces it (**proven 0 → 1 →
0**), and both TLX event pages carry a sourced goal-date-passed block backed by Telix's 6-K of
2026-08-20, which confirms the September 11 date. No Telix filing since and no FDA record shows
a decision either way — that absence is the finding, and "Awaiting" is the honest word for it.

---

## 5. What this says about the cadence

Three of the four decisions were sitting in the watcher's output for days. The system detected
every one of them correctly and on time; what failed was that a red CI has no escalation path.
Worth your view on whether the watcher should open its review issue **before** it exits 1, so a
block is visible without someone thinking to look at Actions.

**Still open:** the 7 unbacked "Q4 2026" calendar rows from 09-10 (ratchet holding at 7), the 22
readout leads, and 09-10b ORDER items 4 and 5 (the `/learn/what-is-a-pdufa-date` restructure and
`/readouts/oncology` + `/readouts/rare-disease`), which this pass displaced again.
