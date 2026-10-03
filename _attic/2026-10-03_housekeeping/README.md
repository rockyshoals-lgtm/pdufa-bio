# Housekeeping, audit 2026-10-03 item 4.8 (moved here, not deleted)

Checked 2026-10-03 (Pacific). None of these files is read by the CI workflow, `_chain_0919.bat`, or any script either of them runs.

| File | Was at | Problem found | Action |
|---|---|---|---|
| `ctgov_t1_raw_studies.json` | repo root | 0 bytes: an interrupted run of `ctgov_t1_dataset_builder.py`, which rewrites it when it runs | moved here |
| `smart_money_v2_cache.json` | `Odin Perfection/` | 109,834,240 bytes, not valid JSON: it ends mid-record ("Unterminated string ... char 109834237") | moved here |
| `fda_adcom_federal_register.json` | `Odin Perfection/` | 20 Federal Register documents, none of them FDA (FEMA review council, locomotive engineer certification, track surface rule, fisheries, CJIS board) | moved here; `/adcomm` history now reads the Federal Register API filtered to FDA (`build_adcomm_history.py`) |

Also confirmed:

- `Odin Perfection/adcom_baserate_v1.json` (hand-typed `yes_rate` values) is referenced by no script in the repo root or in `Odin Perfection/`, and by nothing in the workflow or the local chain. It is left in place and is out of every build path.
- No build script or workflow step references DrugBank's `full database.xml` (CC BY-NC; a commercial licence is required). Searched `*.py`, `*.mjs`, `*.js`, `*.yml` and `*.bat`.

To restore any of these files, move it back to the path in the table.
