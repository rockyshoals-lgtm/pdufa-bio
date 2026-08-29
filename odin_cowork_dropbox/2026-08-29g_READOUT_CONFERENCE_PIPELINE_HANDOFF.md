# 2026-08-29f — Readout + Conference Pipeline Handoff (research assistant → builder)

**Classification: BUILD PACK + DATA DROP.** From the trading-side research assistant. Everything
here is generated locally on David's machine by the readout research chain and is intended for
pdufa.bio to action. Data files are in `data_2026-08-29/`. This doc explains what each file is,
how it was produced, the rendering rules that are NON-NEGOTIABLE, and the preloaded catalyst
list so we always know *why* a name is running when it runs.

---

## 1. What is in `data_2026-08-29/`

| file | rows | what it is |
|---|---|---|
| `readout_gold_dates.csv` | 533 | **THE PUBLISHABLE SET.** Every forward catalyst date we have, graded for honesty. One row per ticker+event: `date, ticker, precision, confidence, source, event, drug, conflict, note`. This is the file the site should ingest. |
| `conference_presenters.csv` | 9 | **NEW SOURCE (first run 2026-08-29).** Our own EDGAR conference-presenter miner: who *said in an SEC filing* they will present at a dated congress. Fresh every run — no longer dependent on the hand-downloaded BPC export. |
| `readout_calendar.csv` | 327 | The merged working view (EDGAR + CT.gov + smart-money columns), sorted by imminence. Superset context; the gold file is the graded distillation. |
| `readout_forward.csv` | 279 | Raw EDGAR pass: companies that SAID a readout is coming, with the guided `window`, canonicalized `window_norm`, and `window_precision`. |
| `ctgov_readouts.csv` | 219 | ClinicalTrials.gov primary-completion dates for watchlist + discovered names, with `raw_pcd` and `pcd_precision`. |
| `conf_registry.json` | 51 congresses | Observed congress start dates by year (29 have a 2026 date). This is where conference DATES come from — the filings almost never state them. |

## 2. The rendering rules (these are the product)

The entire value of this dataset over BPC/competitors is **precision honesty**. The failure mode
we engineered out: a vendor stores "Q4 2026" as `2026-12-31` and a naive site renders "December
31, 2026" as if the FDA said so. BPC's own export parks **553 of its 735 forward rows on New
Year's Eve**; **87% of CT.gov primary-completion dates sit on the 1st, the 15th, or a month end**
(the registry's placeholder convention). We manufacture none of that; we grade it.

- `precision`: `DAY` | `MONTH` | `QUARTER` | `HALF`. **Never render anything below DAY as a
  calendar day.** MONTH renders "September 2026", QUARTER "Q4 2026", HALF "2H 2026".
- `confidence`:
  - **GOLD** — externally checkable: a published congress agenda date, or an FDA-assigned PDUFA
    date. Safe to publish as a hard date and to preload against.
  - **FIRM** — the company itself stated the day in an SEC filing. Publish with attribution.
  - **SOFT** — a bucket. Render as the bucket. Never as a day.
- `conflict` non-empty = two sources date the SAME drug differently. **Surface, never silently
  resolve.** 8 rows are currently flagged (list below) — a human looks before these go live.
- Only ~6 of 194 EDGAR guidance windows earn DAY precision. That is not a pipeline failure —
  companies file "2H 2026", so the honest label is "2H 2026". Hard dates come from congress
  agendas and the FDA, not from guidance prose. Design the UI around that truth.
- All catalyst content carries the standing disclaimer: informational/educational only, not
  investment advice.

## 3. How this is produced (so you can reason about freshness)

One double-click on David's desktop (`READOUT_RESEARCH.bat`) runs a 7-step chain, ~10-15 min:

1. **EDGAR forward scan** (`readout_scan.py`) — "who SAID a readout is coming", 90d lookback,
   7d slices, deep pass into armed names' 10-K/10-Q/8-Ks. Canonicalizes windows ("fourth
   quarter of 2026" → "Q4 2026") and grades `window_precision`.
2. **CT.gov readouts** (`ctgov_readouts.py`) — primary completion dates ("data locks on X"),
   with `pcd_precision` read off the RAW registry string before any day is synthesized.
3. **Conference presenters** (`conference_miner.py`) — NEW 2026-08-29. EDGAR FTS for
   presentation announcements; congress date resolved from `conf_registry.json`; oral/poster
   and abstract number extracted. First run: 232 candidate filings → 9 upcoming events, all
   day-precision observed-agenda dates.
4. **Smart money** — options flow + dark pool columns per catalyst (positioning read, not signal).
5. **Merge** → `readout_calendar.csv`.
6. **Gold dates** (`readout_gold_dates.py`) → `readout_gold_dates.csv`, the graded set.
7. Historical research (base rates, frequency).

Cadence: David runs it every few days. The files in this drop are from the 2026-08-28/29 runs.
Committed at `0c4afff6b` on the trading repo — the 8/22 precision work was silently lost to a
rollback once; it is now under version control and unit-tested (20/20 + 8/8 test cases).

## 4. Known issues / asks

- **BPC export is stale (2026-08-22).** GOLD conference rows sourced `BPC/conference:*` are a
  week old. Our own miner (`EDGAR/conference:*`) is fresh and already found 5 presenters BPC's
  file lacks: **EIKN, ZLAB, MOLN, CRVO, CADL**. If the site shows presenter lists, prefer union
  of both, dedup on ticker+conference.
- **8 conflict rows** need a human eye before publishing (table below). Pattern to know: ESMO
  poster-session dates legitimately span 10/23–10/26, so a 10/23-vs-10/26 "conflict" is usually
  both-true (different presentations). ZLAB 2026 vs CT.gov 2027 is a real discrepancy.
- The SMMT page reportedly still shows a stale 2026-07 readout item; SMMT's PDUFA is
  **2026-11-14** (verified against Summit's own press release) — worth a spot-check.
- ESMO 2026-10-23 is a **14+ name cluster** — the single densest catalyst day in the next 90
  days. A dedicated ESMO 2026 page (all presenters, one URL) is an obvious SEO + product win.

## 5. PRELOAD — why a name is running (next 90 days, GOLD + FIRM only)

When one of these tickers moves, this is the first place to look for *why*. Dates below are
externally checkable (congress agenda / FDA-assigned / company-stated day).

### GOLD + FIRM, next 90 days
| date | ticker | event | drug/detail | source |
|---|---|---|---|---|
| 2026-08-29 | CYTK | Phase 3 | Aficamten - (ACACIA-HCM) | BPC/conference:International Congress of the |
| 2026-08-30 | BAYRY | Phase 3 | KERENDIA (finerenone) - (FIND-CKD) | BPC/conference:European Society of Cardiolog |
| 2026-08-31 | AZN | Phase 3 | Wainua (eplontersen) - (CARDIO-TTRansf | BPC/conference:European Society of Cardiolog |
| 2026-08-31 | IONS | Phase 3 | Wainua (eplontersen) - (CARDIO-TTRansf | BPC/conference:European Society of Cardiolog |
| 2026-09-08 | BEAM | Phase 1/2 | BEAM-302 | BPC/conference:European Respiratory Society  |
| 2026-09-11 | TLX | PDUFA | TLX101-Px | BPC/PDUFA |
| 2026-09-15 | ABBV | Phase 1b | ABBV-1480 (RC148) | BPC/conference:IASLC World Conference on Lun |
| 2026-09-18 | IRD | Phase 1/2 | OPGx-BEST1 - (BIRD-1) | BPC/conference:EURETINA Congress |
| 2026-09-19 | ABEO | PDUFA | UX111 - (ABO-102) | BPC/PDUFA |
| 2026-09-19 | RARE | PDUFA | UX111 - (ABO-102) | BPC/PDUFA |
| 2026-09-21 | MRK | PDUFA | WINREVAIR (sotatercept-csrk) - (HYPERI | BPC/PDUFA |
| 2026-09-22 | IONS | PDUFA | Zilganersen (ION373) | BPC/PDUFA |
| 2026-09-23 | EYPT | Phase 2 | DURAVYU (EYP-1901) - (LUGANO) | BPC/conference:Annual Retina Society Scienti |
| 2026-09-26 | CADL | unspecified | Candel Therapeutics, Inc. | EDGAR/conference:ASTRO |
| 2026-09-26 | INCY | PDUFA | Zilurgisertib (INCB000928) - (PROGRESS | BPC/PDUFA |
| 2026-09-26 | MIRM | PDUFA | Zilurgisertib (INCB000928) - (PROGRESS | BPC/PDUFA |
| 2026-09-28 | BFRI | PDUFA | Ameluz (aminolevulinic acid hydrochlor | BPC/PDUFA |
| 2026-10-01 | LLY | Phase 3 | Rezpegaldesleukin (LY3471851) - (REZOL | BPC/conference:European Academy of Dermatolo |
| 2026-10-01 | LLY | Phase 2b | Rezpegaldesleukin (LY3471851) - (REZOL | BPC/conference:European Academy of Dermatolo |
| 2026-10-01 | NKTR | Phase 3 | Rezpegaldesleukin (LY3471851) - (REZOL | BPC/conference:European Academy of Dermatolo |
| 2026-10-01 | NKTR | Phase 2b | Rezpegaldesleukin (LY3471851) - (REZOL | BPC/conference:European Academy of Dermatolo |
| 2026-10-02 | SANA | Phase 1 | UP421 | BPC/conference:European Association for the  |
| 2026-10-04 | MRK | PDUFA | WELIREG (belzutifan)  and LENVIMA (len | BPC/PDUFA |
| 2026-10-09 | ENTX | Phase 3 | EB613 | BPC/conference:American Society for Bone and |
| 2026-10-09 | RHHBY | PDUFA priority rev | Tecentriq (atezolizumab) and Tecentriq | BPC/PDUFA |
| 2026-10-10 | MRK | PDUFA priority rev | Ifinatamab deruxtecan (DS-7300) - (IDe | BPC/PDUFA |
| 2026-10-17 | IRD | PDUFA | MR-141 (phentolamine ophthalmic soluti | BPC/PDUFA |
| 2026-10-17 | VTRS | PDUFA | MR-141 (phentolamine ophthalmic soluti | BPC/PDUFA |
| 2026-10-19 | IMMP | Phase 2 | Eftilagimod alpha with pembrolizumab a | BPC/conference:European Society for Medical  |
| 2026-10-23 | BHVN | Phase 1 | BHV-1530 | BPC/conference:European Society for Medical  |
| 2026-10-23 | CANF | Phase 2b | Namodenoson - (CF102-222PC) | BPC/conference:European Society for Medical  |
| 2026-10-23 | CANF | unspecified | Can-Fite BioPharma Ltd. | EDGAR/conference:ESMO |
| 2026-10-23 | CATX | Phase 1 | [212Pb]VMT-α-NET | BPC/conference:European Society for Medical  |
| 2026-10-23 | EIKN | unspecified | Eikon Therapeutics, Inc. | EDGAR/conference:ESMO |
| 2026-10-23 | IDYA | Phase 2 | Darovasertib (IDE196) and XALKORI (cri | BPC/conference:European Society for Medical  |
| 2026-10-23 | IDYA | Phase 3 | Darovasertib - (IDE196-009) - (OptimUM | BPC/conference:European Society for Medical  |
| 2026-10-23 | IDYA | Phase 1 | IDE849 (SHR-4849) | BPC/conference:European Society for Medical  |
| 2026-10-23 | IDYA | NDA Filing | Darovasertib with crizotinib - (OptimU | BPC/conference:European Society for Medical  |
| 2026-10-23 | INCY | Phase 1 | INCB123667 (CDK2 Inhibition) with Beva | BPC/conference:European Society for Medical  |
| 2026-10-23 | KTTA | Phase 1 | PAS-004 | BPC/conference:European Society for Medical  |
| 2026-10-23 | MGNX | Phase 1 | MGC026 | BPC/conference:European Society for Medical  |
| 2026-10-23 | MGNX | poster | MACROGENICS INC | EDGAR/conference:ESMO |
| 2026-10-23 | MOLN | poster | MOLECULAR PARTNERS AG | EDGAR/conference:ESMO |
| 2026-10-23 | NVCT | Phase 1b | NXP200 | BPC/conference:European Society for Medical  |
| 2026-10-23 | ORIC | unspecified | Oric Pharmaceuticals, Inc. | EDGAR/conference:ESMO |
| 2026-10-23 | RVMD | Phase 1/2 | vopimetostat (TNG462) in combination w | BPC/conference:European Society for Medical  |
| 2026-10-23 | TNGX | Phase 1/2 | vopimetostat (TNG462) in combination w | BPC/conference:European Society for Medical  |
| 2026-10-23 | TNGX | unspecified | Tango Therapeutics, Inc. | EDGAR/conference:ESMO |
| 2026-10-23 | XNCR | Phase 1 | XmAb819 | BPC/conference:European Society for Medical  |
| 2026-10-23 | ZLAB | unspecified | Zai Lab Ltd | EDGAR/conference:ESMO |
| 2026-10-23 | ZNTL | Phase 2 | Azenosertib (ZN-c3) + ZEJULA (Nirapari | BPC/conference:European Society for Medical  |
| 2026-10-24 | CMPX | Phase 2/3 | CTX-009 (DLL4 X VEGF-A bispecific) - ( | BPC/conference:European Society for Medical  |
| 2026-10-24 | IMTX | Phase 1b | Anzu-cel (anzutresgene autoleucel, IMA | BPC/conference:European Society for Medical  |
| 2026-10-24 | IMTX | Phase 1/2 | IMA402 | BPC/conference:European Society for Medical  |
| 2026-10-24 | IMTX | Phase 1a | IMA203CD8 - (GEN2) | BPC/conference:European Society for Medical  |
| 2026-10-24 | INCY | Phase 3 | INCA33890 in combination of bevacizuma | BPC/conference:European Society for Medical  |
| 2026-10-24 | INCY | Phase 3 | INCB161734 - (DAWN-303) | BPC/conference:European Society for Medical  |
| 2026-10-24 | PHAR | PDUFA | Leniolisib - (pediactric) | BPC/PDUFA |
| 2026-10-25 | AGEN | Phase 2 | Neoadjuvant BOT/BAL - (NEOASIS) | BPC/conference:European Society for Medical  |
| 2026-10-25 | INCY | Phase 1 | INCB161734 with Cetuximab (Cetux) | BPC/conference:European Society for Medical  |
| 2026-10-25 | NBP | Phase 2 | Givastomig (CLDN18.2 x 4-1BB bispecifi | BPC/conference:European Society for Medical  |
| 2026-10-26 | INCY | Phase 3 | INCB123667 (CDK2) with Bevacizumab Ver | BPC/conference:European Society for Medical  |
| 2026-10-26 | IONS | readout guidance | data anticipated in / on track to deli | EDGAR/company-stated |
| 2026-10-26 | MGNX | Phase 2 | Lorigerlimab - (LINNET) | BPC/conference:European Society for Medical  |
| 2026-10-26 | ORIC | Phase 1b | Enozertinib (ORIC-114) | BPC/conference:European Society for Medical  |
| 2026-10-26 | RHHBY | PDUFA priority rev | ENSPRYNG (satralizumab) - (SatraGO) | BPC/PDUFA |
| 2026-10-27 | EVAX | Phase 2b | EVX-01 + KEYTRUDA (pembrolizumab) / OP | BPC/conference:European Society for Medical  |
| 2026-10-27 | MRK | Phase 2b | EVX-01 + KEYTRUDA (pembrolizumab) / OP | BPC/conference:European Society for Medical  |
| 2026-10-30 | INO | PDUFA | INO-3107 | BPC/conference:American Society of Clinical  |
| 2026-11-14 | BTAI | PDUFA | IGALMI® (dexmedetomidine) - (SERENITY  | BPC/PDUFA |
| 2026-11-14 | SMMT | PDUFA | Ivonescimab plus platinum-doublet chem | BPC/PDUFA |
| 2026-11-16 | CRVO | unspecified | CervoMed Inc. | EDGAR/conference:CTAD |
| 2026-11-18 | ALZN | Phase 1/2 | AL001-BD01 - (Lithium in Brain) | BPC/conference:Neuroscience by the Society f |
| 2026-11-22 | SVRA | PDUFA | MOLBREEVI (Molgradex) - (IMPALA-2) | BPC/PDUFA |
| 2026-11-27 | BBIO | PDUFA priority rev | BBP-418 - (FORTIFY) | BPC/PDUFA |
| 2026-11-27 | BBIO | readout guidance | data anticipated in | EDGAR/company-stated |
| 2026-11-27 | NUVL | PDUFA priority rev | Neladalkib (NVL-655) - (ALKove-1) | BPC/PDUFA |

77 rows.

### Conflicts needing human review (two sources date the SAME drug differently)
| date | ticker | drug | other date(s) | source |
|---|---|---|---|---|
| 2026-05-29 | MOLN |  | 2026-10-23 | CTgov/MED |
| 2026-10-23 | INCY | INCB123667 (CDK2 Inhibition) w | 2026-10-26 | BPC/conference:European Society for Medi |
| 2026-10-23 | MOLN |  | 2026-05-29 | EDGAR/conference:ESMO |
| 2026-10-23 | ORIC |  | 2026-10-26 | EDGAR/conference:ESMO |
| 2026-10-23 | ZLAB |  | 2027-05-30 | EDGAR/conference:ESMO |
| 2026-10-26 | INCY | INCB123667 (CDK2) with Bevaciz | 2026-10-23 | BPC/conference:European Society for Medi |
| 2026-10-26 | ORIC | Enozertinib (ORIC-114) | 2026-10-23 | BPC/conference:European Society for Medi |
| 2027-05-30 | ZLAB |  | 2026-10-23 | CTgov/LOW |

### Census of the full gold file
- 533 rows total. confidence: {'SOFT': 439, 'FIRM': 6, 'GOLD': 88}. precision: {'HALF': 98, 'DAY': 123, 'MONTH': 222, 'QUARTER': 90}.
- 9 rows from OUR conference miner (source EDGAR/conference:*): CADL@ASTRO 2026-09-26, CANF@ESMO 2026-10-23, EIKN@ESMO 2026-10-23, MGNX@ESMO 2026-10-23, MOLN@ESMO 2026-10-23, ORIC@ESMO 2026-10-23, TNGX@ESMO 2026-10-23, ZLAB@ESMO 2026-10-23, CRVO@CTAD 2026-11-16


---
*Sources: SEC EDGAR full-text search (8-K/6-K), ClinicalTrials.gov API v2, BiopharmaCatalyst
export 2026-08-22, conf_registry.json (observed congress dates, 1,425-event history).
Informational and educational only — not investment advice.*
