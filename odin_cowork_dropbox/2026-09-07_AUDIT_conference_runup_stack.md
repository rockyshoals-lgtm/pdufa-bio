# Audit note — conference runup stack

**Date:** 2026-09-07 · **For:** audit team
**Scope:** `conference_torque.html` and the conference runup evidence base in `9realms`
**Prepared by:** Cowork session, from files on disk only. Every figure below was read directly from the named file.

---

## Finding 1 — CRITICAL: the shipped playbook contradicts our own research

`conference_torque.html` (built 2026-08-04) prints these numbers in its Playbook panel:

> Nano/micro: **D-30 → D-1, median +4.88% (58.5% win)**. Small: D-5 → D-1, **+3.02% (66.7%)**.

Three separate datasets on disk disagree, and two of them are dated **before** the page was built.

**`CONFERENCE_RUNUP_STUDY_FINAL_2017_2026.md`** — built 2026-07-11, n=1,401 presentations, 393 tickers, 2017–2026, prices from FMP EOD. Its own headline is *"there is no reliable conference run-up."*

| Cap tier | n | 30-day median |
|---|---|---|
| nano | 42 | **−9.84%** |
| micro | 135 | +2.14% |
| small | 129 | +3.28% |
| mid | 121 | −1.15% |
| large | 414 | +0.23% |

**`CONFERENCE_RUNUP_STUDY_2022_2026.md`** — built 2026-07-11, n=220 conference-presenter events against a 1,531-event non-conference baseline. 30-day runup median **−0.79%** for presenters vs 0.00% for baseline, **Mann-Whitney p = 0.924** — statistically indistinguishable. The document states in its own words that it *"contradicts the internal Conference Overlay v1.0 numbers"* and lists *"Reconcile the +4.88% discrepancy with Conference Overlay v1.0"* as an open action item.

**`_conference_runup_stats.json`** — modified 2026-08-29, the newest artifact, n=1,425, sourced from `conf_study/conference_runup_PUBLISHED.csv`:

| Cap tier | n | 30-day median | 30-day pct_up | 5-day median | 5-day pct_up |
|---|---|---|---|---|---|
| nano | 108 | **−7.86%** | **38.9%** | +1.06% | 55.6% |
| micro | 260 | **−1.95%** | **46.5%** | −0.57% | 46.5% |
| small | 298 | +2.75% | 52.7% | +0.58% | 53.0% |
| mid | 116 | **+3.45%** | **55.2%** | +0.45% | 53.4% |
| large | 323 | −0.19% | 48.9% | −0.25% | 46.4% |
| **overall** | **1,425** | **−0.03%** | **49.8%** | −0.06% | 48.6% |

**The severity.** This is not drift, it is a sign flip on the exact cell the strategy targets. The page claims nano/micro D-30 returns +4.88% at a 58.5% win rate. The largest study on disk puts nano at −7.86% / 38.9% and micro at −1.95% / 46.5%. The page's headline trade is, on this evidence, the worst cell in the table. Meanwhile mid-cap — which the page's Execution card tells users to avoid — is the best 30-day cell at +3.45% / 55.2%.

The overall 30-day median across 1,425 events is **−0.03% at 49.8% positive**. A coin flip.

**Provenance of the +4.88% is unestablished.** It traces to Conference Overlay v1.0, and no file in the tree reproduces it. The July study already flagged it as needing reconciliation; the August page shipped it anyway.

**Recommended action:** treat every Playbook number in the HTML as unsourced until reconciled. Do not publish the page externally in its current state.

---

## Finding 2 — separate the outcome claim from the runup claim

These are two different claims and only one is in dispute. Keeping them apart matters.

The **conference signal** finding — presenters read out positive 90.2% of the time vs a 76.7% base rate, p=7.88e-21, crash rate 4.9% vs 8.5% — is a claim about *clinical and regulatory outcomes*. Nothing reviewed here contradicts it.

The **runup** claim — that you can capture a tradeable price move by buying before the presentation — is a claim about *market behaviour in advance of that outcome*. Three datasets say it does not hold on the median.

Both can be true simultaneously: presenters may genuinely have better data, and the market may still not pay you in advance for knowing it. The error in the current page is treating the first as though it licenses the second. Any public claim must state which one it is making.

---

## Finding 3 — the mean/median gap is the actual mechanism

Every study agrees the positive *mean* is a right-tail artifact:

- FINAL study: mean +5.41% vs median −0.35%, **σ = 33.6%**. 15.6% of presenters run ≥25%; 6.3% run ≥50%.
- 2022–2026 study: mean +5.56% vs median −0.79%, σ = 31.8%, range −81.1% to +228.2%.
- Retail zone (nano+micro+small, n=306): 19.6% ran ≥25%, **9.5% fell ≥25%**.

So the trade is a lottery with roughly a 1-in-5 win, a 1-in-10 severe loss, and a middle half spanning −12% to +20%. That may still be a legitimate positive-expectancy bet with correct sizing — but it must be presented as tail-chasing, not as a 58.5% win rate. The current sizing guidance (equity ALPHA 5%) was calibrated against the disputed win rate, so it needs re-derivation from the tail distribution.

The FINAL study also isolates a plausible origin of the myth: **2020 posted a +17.27% median (n=47), 5× any other year**, against −3.33% / −2.86% / −1.74% for 2022 / 2023 / 2024. Anything calibrated on 2020–21 inherits a bubble artifact.

---

## Finding 4 — post-event decay is well supported

The one directional claim that survives cleanly. From `_conference_runup_stats.json` (n=1,425): event day median **−0.56%** (44.3% up), D+5 **−1.59%** (39.4% up), D+10 **−1.93%** (39.9% up). The FINAL study agrees at −0.48% / −1.55% / −1.92%.

The "never hold through the event" rule is the best-evidenced thing in the stack. Keep it and say why.

---

## Finding 5 — methodological gaps both studies self-report

Carry these forward; they are the authors' own caveats, not mine.

1. **Anchor is the conference start date, not the abstract/title-drop date.** Both studies name this as the single biggest gap. The true catalyst likely sits weeks earlier, which means the D-30 window may be measuring the wrong interval entirely. A dual-anchor rebuild is the top-priority remediation and could materially change the result in either direction.
2. **Selection bias.** The universe is "readout events whose data was presented at a conference" — conditioned on the data being newsworthy — not "all companies that presented."
3. **Presentation type unusable in the study data.** 215 of 220 events came back `unspecified`, so oral vs poster vs late-breaker was never tested. The Conference Overlay pays oral +8% and poster +4%; that differential is unvalidated here.
4. **Thin per-conference cells.** `_min_n` is 12 and the FINAL study warns cells with n<25 are noise-dominated. Several per-conference slices in the JSON fall below that.

---

## Finding 6 — presenter data verification is thin and one seed set is wrong

| File | Rows | Note |
|---|---|---|
| `catalysts_out/conference_presenters_mined.csv` | 174 | EDGAR-mined, each with filing URL and matched sentence |
| `catalysts_out/conference_presenters_VERIFIED_2026-08-12.csv` | 10 | human-reviewed subset |
| `catalysts_out/conference_presentations_history.csv` | 754 | historical |

**10 verified out of 174 mined — 5.7%.** Mined rows are traceable rather than invented, which is the right architecture, but traceable is not checked. At least one confirmed false positive: the NewAmsterdam row matches on a sentence describing ESC **2025**, i.e. last year's presentation. Stale-year matching is the expected failure mode for this crawler and it is present in the data.

**The page's seeded watchlist misrepresents its own provenance.** A source comment claims the three seeds are "mined + verified presenters (INBX/TENX confirmed via PR; MBX EASD-thematic watch)". Checked against the mined file: **INBX appears zero times. MBX appears zero times. TENX appears once, tagged AHA — the page assigns it ESC.** None appear in the verified file. Three tickers are presented to a user as evidence-backed when two have no evidence in the tree and the third is attached to the wrong conference.

Also note `pres_type` distribution in the mined set: 136 of 174 are the generic `presentation`, only 21 `oral/late-breaker` and 17 `poster` — the same granularity problem as Finding 5 item 3.

---

## Finding 7 — calendar hygiene

`conferences.json` was modified **2026-09-05** and now holds **42** conferences (was 41), the addition being AACR-PANC (2026-09-25, San Diego). Three issues, all minor but all trust-relevant:

- **`_verified_on` still reads `2026-08-03`** — not bumped when the row was added. The file's own integrity stamp is stale, which defeats its purpose.
- **Rows are no longer chronologically sorted** — AACR-PANC is appended at the end, after ADA 2027-06-18.
- **City format inconsistent** — AACR-PANC uses `"San Diego, CA (Hilton San Diego Bayfront)"` against the `"City, CC"` convention everywhere else.

To the file's credit: all 42 rows carry a `source` URL, and the `_unannounced` block correctly withholds JPM 2027 rather than repeating unverified third-party dates. That discipline is right and worth preserving. `tests/test_no_fabricated_conferences.py` exists and should be extended to cover the sort order and the `_verified_on` bump.

---

## Finding 8 — inherited audit findings that bear on runup sizing

From the April 2026 red team, still open and still relevant because BIFROST feeds runup position sizing:

- **BIFROST Explosion Detector v5.0–v5.5** selects features by greedy forward selection **directly on the test set**. Reported AUCs (0.9487 for v5.5) are optimistic; true generalization was estimated at 0.85–0.90. Relative version rankings remain informative; absolute numbers should not be quoted externally.
- **Short interest lookahead** — `short_interest_snapshot.json` is a single April 2026 snapshot applied retroactively across 1,704 events from 2020–2026. Every SI-derived feature is contaminated for the historical portion.
- **`v5_score` provenance unverified** — it is unknown whether the ODIN v5 score in `pdufa_runup_bifrost.csv` was computed walk-forward or in-sample. If in-sample, BIFROST backtests are inflated.
- **Regularization trending the wrong way** — ODIN C moved 0.025→0.10, BIFROST 0.10→0.30, both while adding features.

---

## Priority queue

1. **Reconcile or retract the +4.88% / 58.5% figures.** Nothing ships externally until this closes. (Finding 1)
2. **Dual-anchor rebuild** on abstract-drop date alongside conference start. Both studies name it as the highest-value fix and it gates the validity of everything else. (Finding 5.1)
3. **Fix the seeded watchlist** in the HTML — remove INBX and MBX, correct TENX to AHA. (Finding 6)
4. **Re-derive position sizing** from the tail distribution rather than the disputed win rate. (Finding 3)
5. **Raise verified presenter coverage** above 5.7%, prioritising conferences with open windows. (Finding 6)
6. **Bump `_verified_on`, re-sort, normalise city format**, and extend the fabrication test. (Finding 7)
7. **Close the inherited BIFROST items** before any runup sizing claim is published. (Finding 8)

---

*Informational and educational only. Not investment advice.*
