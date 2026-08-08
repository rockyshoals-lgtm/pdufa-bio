# Pre-Flight Action Items 1–5 — Completed 2026-05-22

**Operator:** David direct instruction following autonomous Friday Pre-flight scheduled task
**Compliance:** Amendment 027 (Real Data Only) — output separates VERIFIED / INFERRED / UNRESOLVED / RED-TEAM throughout
**Companion file:** `weekly_preflight_2026-05-22.md`

---

## ✅ ACTION 1 — Canonical calendar fully patched

**File:** `CANONICAL_CATALYST_CALENDAR_2026-04-24.csv`
**Backup:** `CANONICAL_CATALYST_CALENDAR_2026-04-24_PRE_2026-05-22_PATCH.csv`
**Total patches applied:** 21 corrections (no rows added/removed; 778 row count preserved)

| # | Ticker / Drug | Old | New | Reason |
|---|---------------|-----|-----|--------|
| 1 | UNCY Oxylanthanum Carbonate | 2026-06-27 | **2026-06-29** | CEO direct quote May 12 Q1 PR (4th day flagged) |
| 2 | MNKD Afrezza (INHALE-1) | text said "May 29, 2025" | "May 29, 2026 (Afrezza pediatric sBLA, ages 4-17)" | Year typo + added drug context |
| 3 | ARQT ZORYVE Cream 0.3% | text said "June 29, 2025" | "June 29, 2026" + pediatric ages 2-5 context | Year typo |
| 4 | ZBIO INDIGO | 2026-06-30 Phase 3 readout | BLA Submission stage; primary already MET Jan 5, 2026 | Phantom Jun 30 — INDIGO Phase 3 already delivered Jan 5 (HR 0.44, p=0.0005) |
| 5 | ZBIO SunStone | 2026-08-31 | **2026-12-31** (Q4 2026 SLE topline) | Per Q4'25 Mar 16 8-K |
| 6 | AVBP FURVENT | 2026-04-30 | **2026-08-15** (mid-2026 placeholder) | Guidance slipped "early 2026" → "mid-2026" per May 11 Q1 PR |
| 7 | ARVN Vepdegestrant (VERITAC-2) | 2026-06-05 PDUFA | **2026-05-01 APPROVED** | VEPPANU approved 35d early; first FDA-approved PROTAC |
| 8 | CADL CAN-2409 (ULYSSES) | 2026-06-30 | **2026-05-15 FIRED GOOD** | PrTK03 Phase 3 prostate extended FU delivered at AUA Plenary |
| 9 | AVTX AVTX-009 (LOTUS) | 2026-06-30 | **2026-05-05 FIRED GOOD** | HiSCR75 42.2%/42.9% vs 25.6% placebo; advancing to P3 + $431M raise |
| 10 | MIRM Volixibat (VISTAS) | 2026-06-30 | **2026-05-04 FIRED GOOD** | VISTAS Phase 2b PSC primary endpoint MET |
| 11 | TRDA ENTR-601-44 (ELEVATE-44 Phase 1b) | 2026-06-30 | **2026-05-07 FIRED DATA_GOOD_MARKET_BAD** | Cohort 1 data positive, market -48 to -57% (Roth PT $19→$10) |
| 12 | TRDA ELEVATE-44-201 (duplicate row) | 2026-06-30 | **2026-05-07 FIRED** | Duplicate of #11 |
| 13 | TRDA ENTR-601-45 (ELEVATE-45-201) | 2026-08-31 | **2026-12-31** (late 2026) | Per Q1 2026 commentary: ENTR-601-45 Cohort 2/45 ~late 2026 |
| 14 | AXSM AXS-05 (ACCORD-2) | 2026-04-30 PDUFA | **APPROVED 2026-04-30** | Auvelity AD agitation sNDA approved on PDUFA day |
| 15 | AXSM Reboxetine (AXS-12 ENCORE) | 2026-04-30 submission | **2026-06-30** (Q2 2026 NDA submission) | Per Q1 2026 commentary |
| 16 | WVE WVE-006 (RestorAATion-2) | 2026-05-18 (already correct date) | Status: **FIRED GOOD** (sell-the-news -5.47%) | Z-AAT -71%, MZ-like phenotype both dosing schedules; positive data + negative price reaction = v15 kaizen anchor |
| 17 | ALXO Zanidatamab + Evorpacept | 2026-05-07 (already correct date) | Status: **RESOLVED** (position closed pre-event +$1,888) | ESMO Breast May 7 |
| 18 | CABA RESET-SLE | 2026-06-30 | **2026-06-04** (EULAR poster 9:30 AM BST) | Firm session date |
| 19 | CABA RESET-SSc | 2026-06-30 | **2026-06-04** (EULAR satellite 5:30 PM BST) | Firm session date |
| 20 | NMRA Navacaprant | Drug labelled "KOASTAL-1" | Drug relabelled "KOASTAL-2 + KOASTAL-3 joint topline" | KOASTAL-1 already failed; current catalyst is KOASTAL-2/3 joint |
| 21 | IRON Bitopertin (APOLLO) | text didn't note CRL | Added: ⚠️ CNPV STRIPPED — bitopertin EPP CRL 2026-02-13 (first CNPV failure per Amendment 035) | Compliance carryover |

**Downstream exit-trigger recomputation:**

| Ticker | Old hard stop | New hard stop | T-7 calc |
|--------|---------------|---------------|----------|
| UNCY | 2026-06-15 (T-7 vs 6/27) | **2026-06-17** (T-7 vs 6/29) | Tue 6/17 close | Already used in portfolio lock |
| ARQT | n/a | 2026-06-19 (T-7 vs 6/29) | Watch candidate |
| VRDN | 2026-06-20 (T-7 vs 6/30) | unchanged | Watch candidate |
| VERA | 2026-06-27 (T-7 vs 7/7) | unchanged | Watch candidate |
| CAPR | **2026-08-12** (T-7 vs 8/22, AdCom-pending) | unchanged | Used in portfolio lock |
| MNKD | 2026-05-22 (T-5 vs 5/29) = today | unchanged | No position (informational) |

**Verification:** UNCY row spot-checked — Catalyst Date now `2026-06-29`, text says "PDUFA date June 29, 2026". All 21 patches confirmed in diff against backup.

---

## ✅ ACTION 2 — ACHV BLOCK reinforced

**File:** `ACHV_BLOCK_REINFORCED_2026-05-22.md`

**Three stacked red signals justifying hard block on any new ACHV entry pre-2026-06-20 PDUFA:**

1. **Apr 15 PR (Achieve verbatim):** "Achieve expects to receive a Complete Response Letter from the FDA on or before its June 20, 2026 PDUFA goal date." — rarest, highest-signal pre-event admission a sponsor can make.
2. **Manufacturing OAI:** Named cytisinicline manufacturer (Sopharma) classified Official Action Indicated by FDA. Launch officially pushed to H1 2027. Tech transfer to Adare Pharma in progress but not yet validated.
3. **NEW 5/22:** Q1 2026 8-K disclosed **two Form 483 observations during recent cGMP inspection** at named manufacturer (solid oral dose manufacturing). Adds fresh CMC risk 5–7 weeks pre-PDUFA = textbook Class 2 CMC CRL setup.

**ODIN v14 features that fire heavily negative:** `mfg_risk_bin`, `pw_double_crl_bin_x_resub_class_2` (-0.173), `pw_orphan_drug_bin_x_resub_class_2` (-0.139), `sponsor_naive × resub_class_2`. No oncology mitigator applies (smoking cessation).

**CNPV does NOT save this** — per Amendment 035, IRON/bitopertin EPP CRL 2026-02-13 is the FIRST DOCUMENTED CNPV APPROVAL FAILURE. CNPV addresses review timing, not facility cGMP. **CNPV +22% boost STRIPPED for ACHV until manufacturer transition is validated.**

**Operational protocol:** Any framework auto-screen surfacing ACHV at T1/T2 → automatic OVERRIDE to NO ENTRY. Logged in OVERRIDE_LOG with rationale pointer to `ACHV_BLOCK_REINFORCED_2026-05-22.md`. Override only by explicit "Override the ACHV BLOCK because {reason}" + ⚠️ DEVIATION flag.

---

## ✅ ACTION 3 — CAPR FDA AdCom verification — **MATERIAL FINDING**

**Status changed: UNRESOLVED → INTENT STATED, DATE TBD.**

### What I verified

- **CGTlive (post-2026-03-10 BLA resubmission cycle):** "FDA States Advisory Committee Meeting Will be Held for Capricor's BLA for DMD Cardiomyopathy Cell Therapy Deramiocel." [Source](https://www.cgtlive.com/view/fda-states-advisory-committee-meeting-held-capricor-bla-dmd-cardiomyopathy-cell-therapy-deramiocel)
- **CEO Linda Marbán quote:** AdCom is one of "major milestones on the path towards approval of deramiocel" — meaning AdCom is part of the upcoming review process leading to the Aug 22, 2026 PDUFA.
- **No date on FDA Advisory Committee Calendar yet** (verified by direct calendar search and news search 2026-05-22 PM).
- **No AdCom found for VRDN veligrotug** — clean.

### Interpretation

- AdCom intent is CONFIRMED for the 2026 Class II resubmission cycle (not just a 2025-cycle leftover).
- Date TBD = elevated date-load-bearing risk for the locked CAPR position.
- Cell therapy AdComs typically fall 4–8 weeks before PDUFA — that puts a likely window of **late June through early August 2026**.
- If AdCom is scheduled BEFORE the portfolio's pre-authorized 8/12 hard stop, the AdCom IS the de facto binary catalyst (not the 8/22 PDUFA).

### Position impact

- **Locked CAPR 535 sh @ $14,555 cost / +$890 unrealized (+6.12%)** — no change to position size.
- **Cardinal Rule re-application:** When AdCom is announced, recompute hard stop to T-7 of AdCom date (NOT 8/22). If AdCom lands within current hard-stop window (8/7–8/12), exit window narrows.
- **Sizing review (per Amendment 031):** AdCom intent + May 7 NS Pharma lawsuit + May 1 Krasney $793K sale = three stacked execution-risk signals. NO scaling above current 22% concentration without explicit override.

### Open thread

- Monitor FDA AdCom calendar daily (build into next daily scan): https://www.fda.gov/advisory-committees/advisory-committee-calendar
- Watch for 8-K filing from CAPR disclosing AdCom date — this WILL be 8-K material.

---

## ✅ ACTION 4 — CRDF Abstract #3510 pulled — **DATA POSITIVE**

### What the abstract shows (verified from ASCO.org content distribution + CancerNetwork coverage)

**Abstract title:** "Onvansertib plus standard-of-care chemotherapy plus bevacizumab in first-line RAS-mutated metastatic colorectal cancer (mCRC): Interim results from the phase 2 randomized CRDF-004 trial"

**Session:** Gastrointestinal Cancer—Colorectal and Anal Rapid Oral, **June 2, 2026, 8:00–9:30 AM CDT**

**Key headline numbers (data cutoff Jan 22, 2026):**

| Metric | Onvansertib 30mg + FOLFIRI/bev | Combined Standard of Care | Δ |
|--------|-------------------------------|---------------------------|---|
| Confirmed ORR | **72.2%** | 43.2% | +29.0 pp |
| PFS | HR 0.37 | reference | **p < 0.05 (significant)** |
| Safety | Well tolerated, no unexpected toxicities | — | — |

### Comparison to April 2025 baseline

- April 2025 baseline was ORR 17.1% onvansertib (different combo) vs paclitaxel 5.3% (different comparator). Not directly comparable.
- The 72.2% / 43.2% / HR 0.37 numbers were **previously released January 27, 2026** in Cardiff's PR — meaning the abstract content is the PRIOR data already in the stock.
- Per IRON-style ASCO practice: "abstract will contain previously presented data; new data reserved for oral." **Expect the June 2 oral to show ADDITIONAL FOLLOW-UP beyond the Jan 22 cutoff.**

### Position-decision read

- **The data going into the catalyst is GENUINELY POSITIVE** — 72.2% ORR is well above SoC and well above prior baselines. PFS HR 0.37 with p<0.05 in a randomized P2 is a strong signal.
- **Asymmetry for the oral:** confirmation/extension of these numbers → modest positive (already priced); regression or new safety signal → significant negative.
- **40-call salvage position (recommendation):** **Hold to T-3 (Thursday May 28) per pre-authorized exit window 5/26–6/1.** Do NOT scratch on the abstract — the underlying data is strong enough to support the runup.
- **Cardinal Rule:** Hard stop **2026-06-01 (Mon, D-1 ASCO)**. No exception — even on strong data we do not hold through the oral.

### Red-team caveats

- Abstract content being previously-released means there is LITTLE positive surprise left in the abstract itself. The trade thesis depends on the additional follow-up at the oral being directionally consistent.
- "Interim results" framing in the abstract title is consistent with smaller patient n than a final P2 readout — durability and OS data still pending.
- The bigger pre-oral risk is competitive sector flow (XBI, GI cancer landscape) and any pre-conference biotech rotation, not the data itself.

---

## ✅ ACTION 5 — MNKD T-5 status (informational only)

**Position:** None per Amendment 031 portfolio lock (UNCY + CAPR + CRDF only).
**Today (5/22) = T-5 trading days to 5/29 PDUFA = BIFROST v4 forced-exit signal for small-cap PDUFA setups.**
**Action:** None required. Logged for completeness.

**Forward note:** MNKD has a SECOND PDUFA — Furoscix ReadyFlow autoinjector on **2026-07-26** (corrected canonical calendar reflects this). If David later considers a tactical entry post-5/29 outcome, recycle in only after refreshed ODIN/GUNGNIR scoring + UOA overlay.

---

## CONSOLIDATED VERIFIED FACTS (new today)

1. **UNCY PDUFA = 2026-06-29** — CEO Shalabh Gupta verbatim quote May 12 Q1 PR. Canonical calendar now reflects.
2. **CAPR FDA AdCom INTENT CONFIRMED** for 2026 BLA cycle (Class II resub, 8/22 PDUFA). Date TBD. CGTlive primary source.
3. **CRDF abstract #3510 is live with 72.2% ORR, PFS HR 0.37 p<0.05** — previously released Jan 27, 2026; June 2 oral expected to show additional follow-up.
4. **ACHV Q1 2026 8-K** confirms two Form 483 observations at named cytisinicline manufacturer — Pre-Investment Discovery BLOCK reinforced.
5. **All 21 canonical calendar patches** verified in CSV diff against backup; row count and headers preserved.

## CONSOLIDATED INFERRED INTERPRETATIONS

1. **CAPR AdCom likely falls late June through early August** based on historical cell-therapy AdCom timing relative to PDUFA. If within 8/7–8/12 portfolio exit window, AdCom IS the de facto binary.
2. **CRDF 72.2% ORR is strong but already priced** — the June 2 oral's incremental signal is durability/follow-up consistency, not first-look data.
3. **ACHV remains a forced PRE-DECLARED CRL** — no probability path supports framework re-entry pre-PDUFA.

## CONSOLIDATED UNRESOLVED GAPS

1. **CAPR AdCom date** — not yet announced. Verify FDA AdCom calendar daily.
2. **CRDF additional follow-up content** — the June 2 oral specifics are not public yet; trade decision pre-empts the data.
3. **MNKD outcome** — 5/29 binary not yet resolved.

## CONSOLIDATED RED-TEAM OBJECTIONS

1. **CAPR AdCom verification source** is CGTlive, a specialist trade publication — should be cross-verified against an SEC 8-K from CAPR confirming AdCom intent. If no 8-K materializes confirming this, downgrade to UNRESOLVED.
2. **CRDF abstract content being previously released** means the trade is more dependent on follow-up consistency than on the abstract itself — that is a thinner thesis than typical pre-readout setups.
3. **Calendar patching policy** — 21 in-place edits is a lot; the backup ensures recoverability, but the diff should be human-reviewed Tuesday 5/26 to confirm no formatting damage was introduced.

---

## RECOMMENDED NEXT MOVES

1. **(CAPR)** Watch for SEC 8-K confirming AdCom date. Set up daily FDA AdCom calendar JSON pull (automation candidate for v15 daily scan).
2. **(CRDF)** Stage exit 5/26–6/1; hard stop 6/1 close. Do not scratch on abstract; do not hold through oral.
3. **(UNCY)** Portfolio lock exit dates already use corrected 6/29 PDUFA. No change.
4. **(ACHV)** Block in force. Daily scan + screen overrides must pass through `ACHV_BLOCK_REINFORCED_2026-05-22.md` rationale.
5. **(KAIZEN_LOG)** Append today's session deltas (CAPR AdCom intent confirmation, CRDF abstract content, ACHV CMC observations) when running next kaizen iteration.

---

## COMPLIANCE ATTESTATION

- **Amendment 027 (Real Data Only):** ✓ Every claim sourced; output separates VERIFIED / INFERRED / UNRESOLVED / RED-TEAM.
- **Amendment 028 (Panel Integrity):** N/A (per-ticker actions).
- **Amendment 031 (Concentrated Regime):** ✓ Portfolio lock unchanged; CAPR sizing held at 22.3%.
- **Amendment 032 (Universal Prediction Hash):** No new V-IDs opened. Existing V-006 (UNCY), V-047 (CAPR), V-048 (CRDF) all referenced consistently.
- **Amendment 033 (Cowork Dropbox):** ✓ This file + ACHV_BLOCK doc mirrored to `/9realms/odin_cowork_dropbox/`.
- **Amendment 034 (Daily Autoscan Persistence):** ✓ Mirrored to `/Odin Perfection/DAILY_AUTOSCAN_REPORTS/`.
- **Daily Scan Mirror:** ✓ Mirrored byte-identical to `/9realms/daily_scans/`.

---

**End of report.**
