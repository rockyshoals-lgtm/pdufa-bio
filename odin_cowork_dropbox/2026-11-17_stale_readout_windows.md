# Stale readout windows corrected, 2026-11-17

David, 2026-11-17: "Please correct any dates that are old or stale for readout window". Pipeline note for the
pdufa builder; data and spec in `2026-11-17_stale_readout_windows.json`, applied by `apply_1117_stale_readouts.py`.
Dates are calendar dates (Eastern, from company releases). Facts only, not investment advice.

Scope: every company-guided readout row whose window had passed, plus rows whose source was wrong.
29 rows checked against the company release, SEC filing or ClinicalTrials.gov record; the 15 that change
what the site shows were re-opened by an independent red-team pass (14 confirmed, 1 headline fixed, none dropped).

## Changes
- Re-guided to the company's current words: VKTX VANQUISH-1/-2 (2027, the old Q3 2026 was the maintenance
  study), MLTX VELA-TEEN final results (Q1 2027), MSLE BASECAMP (Q1 2027), BSEM VLU study (early December 2026).
- Re-sourced to a current filing: CMPX CTX-10726 ("later this year"), LSTA (Q4 2027, S-3 of 2026-11-12).
- Outcome corrected to the right release: BMRN CANOPY-HCH-3 topline 2026-05-20 (was the NEJM publication
  release); MANE Study 207 2026-07-15 (was the Study 304 call notice).
- No topline yet (wrong release had been matched): IVVD DECLARATION, BOLT BDC-4182.
- New state "Stopped per company <date>": AARD HERO (10-23), ALEC PROGRESS-AD (04-29), SNGX FLASH2 (04-28),
  CALC KOURAGE (11-10). Their registry note no longer says we have seen no sponsor statement.
- Removed: PPBT IM1305 readout (no company basis; IM1305 is preclinical per the 2026-11-17 release).
- Checked and kept: 6 sponsor-release outcomes, 5 still-current windows, 3 registry-terminated rows.

## Pipeline changes
- `resolve_past_readouts.py` skips any resolution carrying `reviewed: <date>` (hand-checked, never re-matched
  by headline; three of the wrong outcomes above came from headline matching).
- `_lib.mjs`, `build_readout_results.py`: render `company_stopped` as "Stopped per company <date>"; tests and
  the lede regex accept it.
- `refresh_readout_registry.py`: the terminated-trial note names the company's statement when one is recorded.
