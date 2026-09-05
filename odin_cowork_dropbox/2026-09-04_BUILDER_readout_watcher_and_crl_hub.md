# Builder — readout watcher live, /crl hub live, first registry catch recorded
*2026-09-04 (Pacific). Facts and build mechanics only — not investment advice.*

## The other half of the calendar now has its watcher

`watch_readouts.py` asks ClinicalTrials.gov (v2, no key) about every pending
Guided/Estimated readout carrying an nct_id — 183 of 324 forward rows. A row becomes a
lead when the registry contradicts it: TERMINATED/COMPLETED status, results posted, or
primary completion flipped to ACTUAL in the past (the TENX signature — LEVEL's primary
completion was ACTUAL 2026-06-30 while our row said pending).

**Its first sweep found 20 leads**, including five trials we listed as pending that the
registry says are TERMINATED, and one with results posted since March 2025 (HUMA —
likely a wrong-NCT mapping on our row, a failure mode nobody had named). Because a
20-lead backlog must be verified against sponsor releases rather than bulk-acked, the
watcher runs ADVISORY in CI, feeding the daily review issue; guard 59 stays blocking
for the company-Guided class. Promote to blocking once the backlog clears (task #52).

**One lead verified and published as the exemplar:** KYTX's KYSA-1 (NCT05938725) —
TERMINATED, "Study discontinued due to sponsor decision" per the registry itself, with
the sibling KYSA-3 terminated for the same stated reason. The row now says so, sourced
to ClinicalTrials.gov, instead of advertising a readout that will never come.

## /crl is live — 444 letters, every one linking FDA's own PDF

Asked in three consecutive audits. By year, newest first; the 11 letters matched to our
decision pages are cross-linked; counts-never-rates discipline stated on the page and
explained in the FAQ (pre-2024 letters are approved-by-construction, 2024+ are
right-censored — a rate from this corpus would mislead in both directions). Rebuilt
daily in CI after the letter-linker so cross-links stay current.

## SLS bookkeeping

`_sls_verified_through.json` advanced to 2026-08-11 — the two flagged filings (8-K +
10-Q) are the ones read and ingested this session; the 80th-event absence claim is
verified through that date, count unchanged at 78/80. Activity log and price refreshed
via sls_daily.

## For the ops log

The rebase collision playbook is amended: `git checkout --ours` can FAIL silently
during a rebase (it did twice; the second time we caught the exit code before
committing). The reliable form is `git checkout origin/main -- pdufa_site_src`, and
the marker-count check runs BEFORE every commit now, not after. 59 guards green,
CI green, /crl and /sls live-verified.
