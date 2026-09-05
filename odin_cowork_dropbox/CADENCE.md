# Daily audit ↔ build cadence (Pacific, every day)
*Set 2026-09-05 by David. Facts and build mechanics only — not investment advice.*

| Slot (PT) | Who | Writes | Reads first |
|---|---|---|---|
| **08:00** | Auditor | `YYYY-MM-DD_audit_0800.md` — currency sweep, missed approvals/readouts (primary-sourced), calendar-vs-API, light SERP/AI snapshot, **ORDER list with an acceptance check per item** | INDEX.md, builder files from last 24h |
| **08:20** | Builder | `YYYY-MM-DD_BUILDER_ACK_0820.md` — what shipped, what pushed back and why | the 08:00 audit's ORDER list |
| **08:40** | Auditor | `YYYY-MM-DD_AUDITOR_to_BUILDER_0840.md` — PASS/FAIL per acceptance check, live; next ORDER | builder's 08:20 ack |
| **09:00** | Builder | `YYYY-MM-DD_BUILDER_ACK_0900.md` | the 08:40 note's ORDER |
| **09:20** | Auditor | `YYYY-MM-DD_AUDITOR_to_BUILDER_0920.md` — scorecard + CARRY-FORWARD for tomorrow's 08:00 | builder's 09:00 ack |

Rules of the channel: every claim carries a check the other side can run (URL + the sentence or number that must appear). Audits run against the **live build** only. Disagreements go in writing with the check that would settle them; test the other side's claim before defending your own. Both sides prepend one line to `INDEX.md` per file. Scheduler jitter: auditor runs actually fire ~08:01 / 08:49 / 09:28.

Goal: be more current and more accurate than every competitor, every day — that is the moat, and it is what earns AI citations, Bing impressions and Google authority.
