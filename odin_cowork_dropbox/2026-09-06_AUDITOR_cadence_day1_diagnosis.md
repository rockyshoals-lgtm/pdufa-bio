# Cadence day 1 — what fired, what filed, what changed
*2026-09-06 11:45 Pacific (14:45 Eastern). Live build checked at 11:40 PT. Facts and build mechanics only — not investment advice.*

## What the scheduler says vs what the dropbox holds

| Slot (PT) | Task | Fired? (scheduler `lastRunAt`) | Filed? | Notes |
|---|---|---|---|---|
| 08:00 auditor | `pdufa-audit-0800-morning` | ✅ 08:02 | ❌ **no `2026-09-06_audit_0800.md`** | Ran, left nothing. Cause unverifiable from this evidence — no run log is exposed. Most likely a stall (permission prompt or the heavy approval-hunt) before step 7. |
| 08:20 builder | `builder-0820` | ✅ 08:21 | ✅ `_BUILDER_ACK_0820.md` at **08:55** | Worked yesterday's `2026-09-05_audit_0800.md` (correct fallback). **34 minutes** for 10 items; ack landed after the 08:40 auditor had started. |
| 08:40 auditor | `pdufa-reaudit-0840` | ✅ 08:49 | ✅ at 09:00 | Full re-grade against the 08:50 deploy: **8 of 10 PASS**, 5 NEW findings, 9-item ORDER for 09:00. |
| 09:00 builder | `builder-0900` | ✅ 09:07 | ❌ **no `_BUILDER_ACK_0900.md`** | Ran, left nothing. Same shape as the 08:00 auditor. |
| 09:20 auditor | `pdufa-reaudit-0920` | ✅ 09:29 | ✅ at 09:35 | Recorded 0 of 9 shipped; every 08:40 finding still live. |

**Live build has not moved since 08:50 PT** (`built` 2026-09-06T15:50:30Z at 11:40 PT). Nothing the 09:00 slot might have done reached the site. Currency gates green: `as_of` 2026-09-06, 0 past-goal day PDUFAs undecided, 0 past Guided readouts. Still live at 11:40: `/pdufa/MRK-keytruda`, `/pdufa/BIIB`, `/pdufa/ONC`, `/pdufa/NRXP` each say "under FDA review" ×2 past their goal dates; `/drug/asundexian` 404; `/pdufa-date-changes` 404.

## What I changed on my side (effective tomorrow 08:00)

1. **Stub-first.** Every auditor run's first tool call now writes its output file with a `RUN STARTED HH:MM` header, then overwrites it at the end. A stalled run is visible instead of silent, and the next slot is told what to do when it sees a stub.
2. **ORDER capped at five items per slot**, P0s first, the rest to CARRY-FORWARD. Ten items took 34 minutes today.
3. **08:00 time-budgeted.** Currency sweep, approval hunt, readout hunt and the write-up always; SERP only if time remains.
4. **Every "cannot fail today" check is recorded as not credited** (the Eastern-date test on a same-day build, `as_of` when all zones agree).

## Two asks for David on the builder tasks (I did not edit another agent's prompt)

- **Stub-first there too**: first tool call writes `_BUILDER_ACK_<slot>.md` with `RUN STARTED`, overwritten at the end.
- **Widen the gap or hold the cap**: either move builder slots to 08:25 / 09:05 and auditor re-checks to 08:50 / 09:30, or keep 20-minute gaps and rely on the five-item cap. Today's 08:20 slot could not finish ten items in twenty minutes.

## Standing from the 08:40 / 09:20 notes — the builder's next worklist, unchanged

NEW-2 four stale slug pages + `test_no_past_target_pending_pages.py` · NEW-1 calendar ItemList == unique row URL set · asundexian with `dp:"undisclosed"` · NEW-3 zilurgisertib one row/one count + OBS-1 month-count definition · SRRK caveat rendered · `commit` field in build-info · `/pdufa-date-changes`.

*Informational and educational only; not investment advice. Auditor.*
