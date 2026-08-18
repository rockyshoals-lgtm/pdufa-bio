# Builder response — 2026-08-18 audit (verified-file regression)

All three ordered items are done, plus one incident you'll want on the record.

## §2 Regression — the 9 hand-verified presenters
Root cause exactly as you diagnosed: `.gitignore:35 *.csv`, file untracked, CI never saw it.
- Re-include line added beside its siblings; `git add -f` done. 14 presenter rows (9 verified + 5 history) now survive deploy, and the API passes them through.
- Bonus defect found while verifying live: `shape()` in `_lib.mjs` whitelisted fields and silently DROPPED `presenters` — the dataset carried 8 conferences with entries while the API served none. Fixed (public-page rule: rendered → free in the API), guarded, proven against a planted failure.

## §2 Recommendation — minimum-row guard
`tests/test_data_sources_present.py`: every required builder input must EXIST, be **GIT-TRACKED**, and clear a row floor. Tracked-ness is the check that matters — on the workstation everything exists, so `os.path.exists` passes here and dies in CI; `git ls-files` is what CI will actually see. Proven the natural way: it FAILED on the untracked verified CSV before the fix, passes after. Floors are deliberate under-counts; raising one requires a reviewed commit, same contract as the flags file. This closes the class (73faf74f, 6bf22f9b, today).

## §3 Calendar — you were right, and the guard found real events
`tests/test_calendar_two_sources.py` reconciles FORWARD events between data.js and dataset.mjs every run (past events legitimately diverge: page shows FDA action dates, dataset keeps goal dates beside outcomes — that's honesty, not drift).

First run found three forward events only the slate knew. All externally verified before touching anything:
- **GILD 2026-12-23 anito-cel** — REAL. BLA accepted, PDUFA stated in Gilead's own Arcellx-acquisition release. Added to dataset; calendar row inserted.
- **IRD 2026-10-17** — real date, WRONG DRUG. Slate said "OPGx-RDH12"; the actual event is the phentolamine 0.75% presbyopia sNDA. Corrected. And VTRS's bare "MR-141" row on the same date IS the same program (Viatris co-develops) — named properly so clustering sees one dual-listed event.
- **NVCR 2026-11-15** — real but it's a device **PMA guided to Q4 2026**, not a day-precision PDUFA. Stored at quarter precision; the bare day was invented precision.

## Incident you didn't see: this morning's scheduled run FAILED
`mark_calendar_decided` died on three rows dated 2026-08-17 with no outcome: **HOOK, CRBP, NCNA**. External check: none of the three has an application on file (CRBP's own Q2 update starts its registrational study in September; NCNA is IND-stage). All three carried identical copied text ("Pembrolizumab combination"), dead `#` links, present since the initial site commit, in NO data source — fossils that detonated when their date passed. Removed.

Two guard holes they exposed, both closed:
1. The calendar guard's row regex was anchored on `href="/pdufa/"` — `#`-linked rows were structurally invisible.
2. The same-date partner allowance let ANY ticker ride on any real same-date event (they rode on BMY's 08-17). Partner rows must now share a drug token with the event they claim to be. Proven with a planted row.

Also: BMY's goal date passed with no FDA action; the board correctly leads with it as Awaiting, but the freshness badge skipped past-dated events and said "next: CAPR 08-22" — mismatch guard caught it. Awaiting events ≤7 days past now count as the next expected decision.

## AMLX (owner-reported, same day)
Avexitide Phase 3 LUCIDITY confirmed positive (55% reduction, p=0.000003) and published to /readouts with the BusinessWire source. Day-of close renders "pending" until the ET close because Polygon serves the in-progress bar intraday — the first render showed +55.2% under a "close reaction" label and that was a lie by 2.5 hours. Self-heals after the close. Miner postmortem: EDGAR pass missed it (guidance older than the scan window — deep-pass added, DAYS 45→90), CT.gov pass dropped the trial (PCD ~140d overdue vs a 120-day cutoff — widened to 180).

Still David-gated: legal pages, email capture, /compare, per-event URLs.

*Facts and historical statistics only — not investment advice.*
