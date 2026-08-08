# ODIN Conversation Migration Packet (through 2026-01-28)

This file is a **handoff bundle** you can paste into another chat/AI so it can continue *exactly where we left off*.

---

## 0) One-paragraph state summary

You provided a production-ready **ODIN Multi‑AI Orchestrator** (biotech trading/catalyst analysis) codebase + documentation and asked for (1) a **thorough production audit** (code quality, architecture, docs, business logic, missing features, integration, deployment risks) with special focus on **cost controller loopholes** and **async/await safety**, (2) **actionable research instructions for Claude** (agentic research workflow), (3) a **cost-control mode** that can cap **API spend by dollars** and be changed dynamically (run 24/7 or only certain hours), (4) **up‑to‑date Q1 catalysts research** and a **tiered $40k deployment plan**, and (5) performance review of a **GPU optimization script** with an **auto‑RAM/VRAM** tuned version.

---

## 1) Hard constraints / user preferences to preserve

- **NO “API Tool” calls**: “Currently there are no APIs available through API Tool. Refrain from using API Tool until APIs are enabled by the user.”
- User wants **current / up‑to‑date catalyst info** (prior plan is explicitly called outdated).
- Emphasis: **Cost controller must be enforceable**, no loopholes; and **async correctness** (no blocking calls in async, clean shutdown).

---

## 2) Repository & artifacts (what files exist in this chat)

### Core orchestrator + cost control
- `odin_multi_ai_orchestrator.py` – legacy/original “multi-ai orchestrator” implementation.
- `odin_orchestrator.py` – main orchestrator entrypoint (autonomous loops, routing).
- `odin_ai_workers.py` – worker implementations (Claude/OpenAI/Gemini/Perplexity).
- `odin_shared_context.py` – shared memory / inter-AI context.
- `odin_data_pipelines.py` – data sources.
- `odin_cost_control.py` – cost controller (budgets, logging, enforcement).
- `odin_cost_dashboard.py` – dashboard UI.

### Config, tests, docs
- `odin_budget_config.json` – budget tiers, per‑AI limits, task priorities.
- `watchlist.json` – monitored tickers.
- `test_odin.py` – tests.
- `requirements.txt` + `.env.example`.
- `README.md`, `SETUP_DEPLOYMENT_GUIDE.md`, `API_INTEGRATION_GUIDE.md`, `COST_CONTROL_GUIDE.md`.

### ODIN model/config research artifacts
- `ODIN_ENRICHED_PDUFA_1349_v2.csv` + `.md`
- `ODIN_v88_UNIFIED_CONFIG.json`
- `ODIN_v89_MCP_CONFIG.json`
- `ODIN_v810_ICEV2_CHAMPION_CONFIG.json`
- `ODIN_ICEV2_CONDENSED_AUDIT_RUN.json`
- `ODIN_MCP_SESSION_HANDOFF_2026-01-19.md`
- `ODIN_MCP_KEY_FINDINGS_2026-01-19.md`
- `ODIN_MCP_BACKTEST_REPORT_2026-01-19.md`
- `odin_mcp_backtest_results.json`
- `Enhancing ODIN’s Predictive Accuracy with Six Data Feeds.pdf`

### Generated in this chat
- `audit_report.md` – production audit findings + fixes.
- `catalyst_plan.md` – Q1 2026 catalyst plan + $40k tiered plan (but later flagged as outdated).
- `odin_v92_gpu_optimizer_autoram.py` – improved optimizer script (auto RAM/VRAM & faster).

---

## 3) What was delivered / decided in this chat

### 3.1 Production audit (delivered)
A detailed audit was produced as **`audit_report.md`**.

**Top audit priorities (carry forward):**
1. **Daily/weekly/monthly spend counters never reset** and aren’t reconciled to DB → budgets can become permanently blocked or wrong.
2. **Budget summary relies on in-memory counters** instead of DB sums → restarts produce wrong remaining budget.
3. **Config mismatch**: `task_priority` key mismatch for thesis updates → priority system not applied as documented.
4. **Enabled AI settings ignored** in routing → disabled AIs can still receive tasks.
5. **Token/cost estimation logged, but not reconciled to actual usage** → under/over-charging; budget loopholes.
6. **Blocking SQLite calls inside async** → event loop stalls under load.
7. **Missing retries/circuit breaker**, **print-based logging**, **no graceful shutdown**, and dashboard `debug=True`.

### 3.2 Cost control requirement (requested)
You asked for a cost control design where you can:
- cap spending by **dollar amount**,
- change limits **whenever you want** (no redeploy),
- run **24/7** or **only certain hours**.

**Direction implied by the audit:**
- implement **budget holds / reservation** (pre-call) and **post-call reconciliation** (actual usage).
- enforce a **time-window schedule** (local timezone) and a **daily/monthly envelope**.

### 3.3 Q1 catalysts & investment plan (delivered but then marked outdated)
A Q1 2026 catalyst list + a hypothetical tiered $40k plan was produced as **`catalyst_plan.md`**, but you later said it contains **old info** and requested **current updates**.

You specifically noted:
- **FBIO** was approved early.
- **ATRA** was delayed.
- and you want the research refreshed to match the current reality.

### 3.4 FBIO PRV question (pending)
You asked whether **FBIO receiving a PRV** is a significant rerating event, noting:
- a recent PRV sale by **Jazz** reportedly around **$200M**.

This requires **current verification** (news + terms) and tying the economics back to **who owns the voucher proceeds** (FBIO vs Cyprium vs partner) and timing.

### 3.5 GPU optimizer (delivered)
You shared `odin_v92_gpu_optimizer.py` for review. A faster, safer variant was produced:

**`odin_v92_gpu_optimizer_autoram.py` adds:**
- avoids allocating huge intermediate arrays,
- auto-tunes batch size from free VRAM (GPU) or available RAM (CPU),
- precomputes event coefficient matrix,
- generates random params directly on GPU when available,
- checkpointing robust to batch-size changes.

---

## 4) What remains to do (next steps, in priority order)

### Priority 1 — Cost controller: enforceable spend caps + dynamic schedule
Implement a version of the cost controller with:
- **Hard dollar cap(s):** `max_daily_spend_usd`, `max_weekly_spend_usd`, `max_monthly_spend_usd`.
- **Active window(s):** e.g. `{ "timezone": "America/Los_Angeles", "windows": [ {"start":"06:00","end":"14:00"}, ... ] }` and “24/7 mode”.
- **Hot reload:** watch `odin_budget_config.json` (or a new `odin_runtime_budget.json`) and reload without restart.
- **Reservation model:** before an API call, create a **pending hold** for estimated max cost; after call, reconcile to actual usage.
- **Atomicity:** ensure a task cannot “slip through” without being charged (transactional logging).

### Priority 2 — Refresh Q1 catalysts using current sources
Re-do the Q1 list using **current, verified dates**:
- PDUFA/action dates, CRL/approval outcomes, delays, AdCom info.
- Update watchlist and catalyst schedule accordingly.

### Priority 3 — Re-evaluate FBIO vs alternatives (with live PRV comps)
- Confirm the PRV was received and the exact type (Rare Pediatric Disease PRV etc).
- Confirm recent PRV sale comps, including the Jazz sale you referenced.
- Map **who captures the voucher economics** (deal terms / royalty / milestone split).
- Produce a refreshed, tiered deployment plan for an additional $40k (explicitly hypothetical/not advice).

### Priority 4 — Production hardening
- Replace blocking sqlite calls in async contexts (use `aiosqlite` or `asyncio.to_thread`).
- Add structured logging + correlation IDs for tasks.
- Add retries + exponential backoff + circuit breaker.
- Add graceful shutdown (cancel loops, close DB).
- Fix doc/code mismatches in `API_INTEGRATION_GUIDE.md` and README.

---

## 5) Copy/paste prompt for your next chat/AI

Paste the block below into the new chat (and attach the repo files / this migration packet if possible):

---

**PROMPT START**

You are taking over an ODIN Multi‑AI Orchestrator production audit + biotech catalyst research thread.

### What ODIN is
ODIN is a production-ready autonomous orchestrator coordinating Claude/OpenAI/Gemini/Perplexity to generate biotech trading signals around PDUFAs and other catalysts. It includes a cost controller + dashboard.

### Hard constraints
- Do NOT use any “API Tool” integrations (they are disabled). If you need live data, use web browsing.
- All catalyst information must be up-to-date and verified.

### Current objectives
1) Implement/describe a **cost control mode** that caps API usage by **dollar amount**, supports **scheduling** (24/7 vs X hours/day), and can be changed dynamically (hot reload) without restart. Ensure no loopholes: tasks cannot run without being charged; token estimates should be reconciled to actual usage.

2) Re-research **Q1 catalysts** with current dates/outcomes, because prior list was outdated (FBIO approval happened early; ATRA delayed, etc).

3) Reassess whether **FBIO** is the best opportunity vs better alternatives. User also noted FBIO received a PRV and that a Jazz PRV sale around $200M occurred recently; verify and assess rerating implications, including economics/ownership.

4) Production harden orchestrator: fix audit findings (counter resets, async sqlite blocking, enabled AI routing, retry/circuit breaker, debug dashboard, doc mismatch).

### Artifacts available
- audit_report.md (audit findings)
- catalyst_plan.md (old; must refresh)
- odin_v92_gpu_optimizer_autoram.py (auto RAM/VRAM optimized)
- ODIN configs: v8.8 unified, v8.9 MCP, v8.10 ICEv2 champion; MCP handoffs.

Deliverables should be actionable: exact code edits, config schema, and a prioritized fix plan.

**PROMPT END**

---

## 6) Links to the key files in this chat

### Must-read
- `audit_report.md`
- `odin_cost_control.py`
- `odin_multi_ai_orchestrator.py` and/or `odin_orchestrator.py`
- `API_INTEGRATION_GUIDE.md`, `SETUP_DEPLOYMENT_GUIDE.md`, `COST_CONTROL_GUIDE.md`
- `catalyst_plan.md` (as baseline, but must be refreshed)

### ODIN research configs / MCP handoffs
- `ODIN_MCP_SESSION_HANDOFF_2026-01-19.md`
- `ODIN_MCP_KEY_FINDINGS_2026-01-19.md`
- `ODIN_MCP_BACKTEST_REPORT_2026-01-19.md`
- `ODIN_v89_MCP_CONFIG.json`
- `ODIN_v810_ICEV2_CHAMPION_CONFIG.json`

---

## 7) Quick reproducibility notes

- Install: `pip install -r requirements.txt`
- Configure keys: `.env.example` → `.env` (do not commit)
- Tests: `python test_odin.py --mode mock`

---

