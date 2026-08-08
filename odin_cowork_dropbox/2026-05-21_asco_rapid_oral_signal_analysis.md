# ASCO Rapid Oral as a Predictive Signal — Honest Assessment

**Run date:** 2026-05-21
**Run type:** model_validation
**Source chat:** cowork_odin_perfection
**Cross-references:** Conference Overlay v1.0 (project CLAUDE.md), IIS v1.0 OCGN postmortem, 2026-05-21_crdf_event_check.md

## Question

"How good are typical ASCO rapid oral session blocks for a stock return? Is there a higher likelihood the readout is going to be GREAT since they have this slot?"

## ✅ VERIFIED FACTS (from project framework)

Conference Overlay v1.0 (deployed in MCP v14.0.0) — based on n≈2,000 readouts:
- Any conference presentation: **90.2% positive rate vs 76.7% baseline** (p = 7.88e-21)
- ASCO subset: **90% positive rate (n=90)**
- AACR 100% (n=16), ASH 95.4% (n=65), ESMO 95.7% (n=69)
- Phase 2 conference effect: **+16.8 percentage points** (largest single-phase gap)
- Crash rate at conference events: **4.9% vs 8.5% non-conference**
- Conference Overlay weighting: Oral +8%, Late-breaking +6%, Multiple +6%, Poster +4%

## 🔎 INFERRED INTERPRETATION

**Rapid oral selection IS a positive signal, but a modest one — effective ~+5-6% in our framework (between Oral +8% and Poster +4%).**

It means:
1. ASCO abstract committee judged the data scientifically interesting enough for podium
2. Sponsor had to clear a data-completeness bar at submission (months earlier)
3. Sponsor was confident enough to submit topline-level numbers (companies that fear bad data submit as posters or withdraw)

It does NOT mean:
1. Rapid oral is below full Oral, well below Late-Breaking Abstract, far below Plenary — TRULY best data lands there
2. The magnitude of the stock move is predicted
3. Consensus beat/miss is predicted — that drives D0 size

## ⚠️ UNRESOLVED GAPS

- No project-validated dataset isolates rapid oral specifically vs general oral vs poster, controlling for phase / indication / mcap
- Most published academic work lumps oral + rapid oral together
- Magnitude of move varies wildly by mcap, IV expansion, consensus beat/miss

## 🔴 RED-TEAM OBJECTIONS

1. **Selection bias** — Companies with rapid oral slots also tend to have better-prepped IR, KOL coverage, sell-side support. Some "rapid oral effect" captures these confounds
2. **Interim-data inflation** — Rapid oral slot doesn't protect against IIS-pattern shrinkage at full data (OCGN: 32.6% interim-to-full)
3. **Pre-disclosure leak** — companies often telegraph quality before ASCO (EOP2 meetings, regimen selections), pre-discounting upside
4. **Cardinal Rule** — rapid oral is NOT a reason to hold through binary. The runup IS the trade.

## Actionable Takeaway

Defensible one-line summary: *"ASCO rapid oral selection raises the probability of a positive-direction readout by a modest amount (estimated +4-6% in our framework), but is not a reliable predictor of stock-return MAGNITUDE — that's still driven by consensus beat/miss and IV crush dynamics."*

For **CRDF specifically**: the rapid oral slot is NOT the strongest bull signal in the file. The May 14 EOP2 success + Phase 3 dose selection is a stronger de-risk, and is already public.

## Implications for Framework

Candidate update for next ODIN/GUNGNIR Kaizen cycle:
- Test **`pres_type_rapid_oral`** as a feature distinct from `pres_type_oral` and `pres_type_poster`
- Test interaction with **`is_phase2_interim`** to capture IIS confounding
- Test interaction with **`pre_disclosure_EOP2_within_30d`** to capture leak/discount

## Sources

- Project memory: Conference Overlay v1.0 (CLAUDE.md), 90.2% vs 76.7% positive rate, n=90 ASCO
- Project memory: IIS v1.0 OCGN postmortem, 32.6% interim shrinkage
- Project memory: BIFROST v4 / Cardinal Rule
