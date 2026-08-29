# 2026-08-29h — DATE DRIFT ALERT + data refresh (supersedes parts of 2026-08-29g's preload)

**Classification: CORRECTION + DATA REFRESH.** From the trading-side research assistant.
A fresh BiopharmaCatalyst export (2026-08-29) arrived hours after the 29g handoff was filed.
All files in `data_2026-08-29/` are refreshed from the 12:44 pipeline run against it, and a
new artifact exists: `readout_date_drift.csv` — the pipeline now diffs the two newest BPC
exports on every run and flags every moved future date.

## 1. Thirteen future dates MOVED between the 8/22 and 8/29 exports

Ten of thirteen were **pulled forward** — the dangerous direction: the catalyst arrives
EARLIER than the calendar we shipped. If any of these are live on the site, update them.

| ticker | old → new | moved | event |
|---|---|---|---|
| BAYRY | 2026-12-31 → **2026-08-30** | EARLIER | Phase 3 KERENDIA (FIND-CKD) — ESC, this weekend |
| XENE | 2026-09-30 → **2026-09-07** | EARLIER | Phase 3 azetukalner (X-TOLE) — 9 days out |
| DFTX | 2026-09-30 → **2026-09-23** | EARLIER | Phase 3 MM120 |
| MLTX | 2026-11-30/12-31 → **2026-09-30** | EARLIER | sonelokimab BLA filings (3 rows) |
| ACET | 2026-12-31 → **2026-09-30** | EARLIER | Phase 2 prula-cel |
| REGN | 2026-12-31 → **2026-11-30** | EARLIER | PDUFA priority review, C5 combo |
| HUMA | 2026-12-31 → **2026-11-30** | EARLIER | ATEV V012 BLA |
| PRAX | 2026-12-31 → **2026-12-27** | EARLIER | PDUFA relutrigine |
| CAPR | 2026-08-22 → 2026-11-22 | later | PDUFA deramiocel — matches our 8-K read (3-mo extension, major amendment) |
| CYTK | 2026-08-29 → 2026-12-31 | later | reclassified to sNDA **Filing** — REMOVE the 29g preload row showing CYTK today |
| SYRE | 2026-09-30 → 2026-12-31 | later | Phase 2 SPY072 |

Caveat on the pulled-forward NYE rows: `2026-12-31` is BPC's *placeholder* for "2026", so
BAYRY/ACET/REGN/HUMA/PRAX are largely *bucket → real date* refinements, not reschedules.
XENE and DFTX were real dates that genuinely moved earlier.

## 2. Miner resilience upgrades shipped today (commits `dd258b271`, drift detector follows)

- **Alias gap-fill:** ESC and EASD had observed 2026 dates in the registry but zero aliases —
  the extractor could not NAME them, which is how we missed AZN/IONS/ALNY/BAYRY/EWTX
  presenting at ESC the weekend it ran. Fixed, plus EADV / EURETINA / ASBMR / Retina Society /
  ERS added to the registry (dates from published agendas via BPC's conference column).
- **Immediate payoff:** the very next run found **11 presenter events (was 9)** — new:
  **IBIO @ EASD 2026-09-28** and **IPSC @ EASD 2026-09-28 (ORAL)**, both small caps, neither
  in BPC's fresh file as conference rows.
- **Drift detector:** every gold-pass run now writes `readout_date_drift.csv` and prints any
  moved future date, tagged EARLIER/LATER. Staleness now announces itself.
- Unit coverage: 14/14 extraction cases, 20/20 window-precision cases.

## 3. Refreshed numbers (files in `data_2026-08-29/` are current as of 12:56)

535 gold rows (GOLD 90 / FIRM 6 / SOFT 439). Conflicts for human review: **10** (was 8; the
two new ones are EASD-cluster overlaps). Our-miner-only edge now 7 names BPC lacks
conference rows for: EIKN, ZLAB, MOLN, CRVO, CADL, IBIO, IPSC.

Known residual gap, by design: mega-caps (ABBV, LLY, AZN) often announce presentations via
newswire without an 8-K, so an EDGAR-only miner will not see them — BPC still adds value
there. Our edge is small/mid caps, which file everything.

*Informational and educational only — not investment advice.*
