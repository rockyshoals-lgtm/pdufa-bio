# IMMUTABLE DIRECTIVE — Amendment 029 — Cross-Chat Publication

**Established:** 2026-05-17 (Sunday Kaizen autonomous session)
**Author of directive:** David
**Scope:** Permanent project rule. Applies to every chat in the Odin Catalyst / 9realms ecosystem.
**Companion to:** Amendment 027 (Real Data Only), Amendment 028 (Panel Integrity).

---

## DIRECTIVE TEXT

Every material output produced in any Odin Catalyst chat — daily scan, weekly kaizen, formal prediction, postmortem, model retraining note, immutable amendment, calendar correction, position close, red-team audit, or research deliverable — MUST be published to the cross-chat inbox at:

```
C:\Users\dcmoo\Documents\Python\9realms\ODIN_INBOX\
```

**Three hard rules:**

1. **Per-day folder.** On the day an output is produced, write or copy the file to `/9realms/ODIN_INBOX/YYYY-MM-DD/`. Create the folder if it does not exist. Use the same filename as the canonical copy in `/Odin Perfection/` (do not rename).
2. **Master index.** Add a one-line entry to `/9realms/ODIN_INBOX/INBOX_INDEX.md` with the format below. Newest at the top. Do not exceed 200 characters per entry. Do not put content in the index — only pointers.
3. **Append-only.** Never overwrite, never delete prior entries. If a previously published file is corrected, write the corrected version with a `_v2` (or `_vN`) suffix and add a new INBOX_INDEX line that points to the correction. The original stays.

**Index line format:**

```
- YYYY-MM-DD | [TYPE] | [Title](2026-05-17/filename.md) — one-line hook (≤120 chars)
```

Where `[TYPE]` is one of: `DAILY_SCAN`, `KAIZEN_WEEKLY`, `PREDICTION`, `POSTMORTEM`, `AMENDMENT`, `CALENDAR_FIX`, `POSITION_CLOSE`, `MODEL_NOTE`, `RED_TEAM_AUDIT`, `RESEARCH`.

## WHY

The framework spans multiple Claude chats and multiple cowork sessions. The main Odin Catalyst chat needs to see *every* output from *every* sub-chat (scheduled scans, kaizen runs, red-team audits) to continuously improve ODIN and prediction calibration. Without a single publication point, scans get marooned inside the session that produced them, and the main chat rebuilds context from memory rather than from authoritative files.

The cross-chat inbox solves this:
- Main chat reads `INBOX_INDEX.md` at the start of every session and ingests new outputs.
- ODIN/GUNGNIR/BIFROST kaizen cycles pull historical prediction calibration data from the inbox to train new features (the `earnings_proximity` feature for ODIN v36 is a canonical use case).
- Red-team audits have a single source of truth to grep across.
- Forward-prediction calibration is auditable across chats and across time.

## HOW TO APPLY

**Every chat, every output:**

1. Write or save the canonical copy to its normal location (e.g., `/Odin Perfection/daily_news_scan_YYYY-MM-DD.md` or `/Odin Perfection/kaizen_weekly_YYYY-MM-DD.md`).
2. Immediately copy the same file to `/9realms/ODIN_INBOX/YYYY-MM-DD/`.
3. Append one INBOX_INDEX line.
4. Confirm in the chat output: "Published to ODIN_INBOX: [filename]"

**For autonomous scheduled tasks (daily scan, weekly kaizen):**

The scheduled task SKILL.md or task file MUST include the publication step in its output procedure. If the publication step is missing, the task is non-compliant and Claude must add it before completing.

## OVERRIDE PROTOCOL

The only legal override is the explicit phrase:

```
Override the cross-chat publication directive because {reason}
```

Spoken or written by David in the chat that is producing the output. Every override:
- Must include a reason (e.g., "this is PII", "this is an experiment not for the main chat").
- Must add a `⚠️ NOT_PUBLISHED` flag to the canonical file's front matter or first line.
- Must be logged in `/9realms/ODIN_INBOX/INBOX_INDEX.md` as a `[NOT_PUBLISHED]` entry with the reason — so the main chat knows something exists but is deliberately withheld.

Silent non-publication is not allowed. If Claude forgets to publish, the next chat that detects the gap MUST publish retroactively with a `_retropublished_YYYY-MM-DD` suffix.

## ENFORCEMENT

Future kaizen cycles MUST include a "cross-chat publication audit" step:
1. List every output produced in `/Odin Perfection/` in the coverage window.
2. Cross-check against `/9realms/ODIN_INBOX/INBOX_INDEX.md`.
3. Flag any missing entries.
4. Retro-publish them.

A kaizen report that does not include this audit is non-compliant.

## INTEGRATION WITH PRIOR AMENDMENTS

- **Amendment 027 (Real Data Only)** — published files must follow the VERIFIED FACTS / INFERRED / UNRESOLVED / RED-TEAM output format. Index hooks are summary only, not new claims.
- **Amendment 028 (Panel Integrity)** — any published file that contains a panel-conditional rate must have been validated by `catalyst_panel_validator_v1.py` before publication.
- **Amendment 025 (TRUE Odin Ledger)** — position closes get a `POSITION_CLOSE` index entry with realized P&L. The main chat reads these to keep the ledger live.
- **Amendment 031 (Concentrated Regime)** — sizing decisions and overrides must be published so the main chat can confirm position-cap compliance across sessions.
- **Amendment 032 (Universal Prediction Hash Ledger)** — every prediction file added to the inbox must include the SHA-256 hash chain entry.

## CHAIN HASH

This amendment is appended to the master chain. Pre-chain hash (from Amendment 028): `4eada98aa06af23597a02924532505c0c5c12a2d9f5f4f2006a44a1a464b6b0f`. New post-amendment chain hash will be computed when the next session reads this file and confirms ratification.

## TESTABILITY

The first compliance test is: by 2026-05-18 09:00 ET, the main Odin Catalyst chat should be able to read `/9realms/ODIN_INBOX/INBOX_INDEX.md` and see at least 1 entry (today's kaizen weekly). If the main chat reports "inbox not found" or "empty", Amendment 029 is failing and must be debugged.

## CANONICAL PATH

```
C:\Users\dcmoo\Documents\Python\9realms\ODIN_INBOX\
├── IMMUTABLE_DIRECTIVE_CROSS_CHAT_PUBLICATION.md   (this file)
├── INBOX_INDEX.md                                   (master index)
├── 2026-05-17/                                      (per-day folder)
│   ├── kaizen_weekly_2026-05-17.md
│   ├── kaizen_log_append_2026-05-17.md
│   └── master_log_session_2026-05-17.md
├── 2026-05-18/                                      (created tomorrow)
└── ...
```

---

*Codified in `/9realms/ODIN_INBOX/IMMUTABLE_DIRECTIVE_CROSS_CHAT_PUBLICATION.md`, memory, and master log. No model retrain triggered. Operational rule, permanent.*
