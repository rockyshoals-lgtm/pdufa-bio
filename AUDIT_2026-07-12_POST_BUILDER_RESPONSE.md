# Audit — after the builder's response
**2026-07-12** · Read: `AUDIT_RESPONSE_2026-07-12.md`, `CONFERENCE_CRAWLER_AUDIT_2026-07-12.md`

---

# 0. Two of the bugs they found are mine. Owning them.

### 🔴 `ANE` was my parse artifact — and it reached a published table.
The conference regex I wrote included `'ANE': r'AACR-NCI-EORTC'`. It swept **47 real presentations** under a code that doesn't map to a single real meeting — registry dates jumping March/June/October, empty `conf_full`. It became **the 7th-largest row in the published by-conference table** on `/research/conference-runup`.

**`PRE-RELEA` was mine too** — my `shortconf()` truncated to 9 characters and emitted a junk code (n=2).

The builder caught both, pulled the row, and **disclosed the removal on the page**. That is precisely the right handling. But I generated a fabricated category and shipped it into a research page whose entire selling point is that the numbers are real. **My conference-name extraction needs a whitelist, not a regex.**

### 🔴 My CLAUDE.md is telling me to use a leaked model.
The builder's correction #1 is right, and I verified it against the **live MCP tool descriptions**, not the docs:

> `odin_score` → *"**LEGACY ODIN v14 scorer — KNOWN LEAKED** per ODIN_v14_LEAKAGE_FINDING.txt (2026-04-17). Reported HO AUC 0.9363 is **inflated ~368 bp**."*
> `odin_score_v19` → *"**CURRENT CHAMPION.** Honest test AUC **0.8934**, Brier 0.1173, 45 features."*

Meanwhile **CLAUDE.md** says: *"ODIN v14 is the ONLY PDUFA scoring model. Never fall back."* and quotes **HO AUC 0.9363** as fact.

**Every ODIN statement I've made in this engagement was anchored on a leaked model's inflated metrics.** The v14 tool is now disabled at the connector level (good), but the memory file is the source of truth for every future session.

> **🔧 OWNER ACTION: update CLAUDE.md.** Replace the ODIN v14 champion block with **v19-PRUNE (YGGDRASIL_PRUNE), honest test AUC 0.8934, Brier 0.1173, 45 features**, and mark v14 **KNOWN LEAKED — do not use**. Until that edit lands, anyone reading the memory file scores on a leaked model.

---

# 1. Verified: the builder's `prior_crl_count` finding. I undersold it.

I called it a data nit (28 rows, 1.3%). It's a **live model bug**, and their diagnosis is exactly right:

```
counts >= 9  →  18 distinct values, EXACTLY ONE EVENT EACH  →  a running counter, not a distribution
```

| | mean | std | max |
|---|---|---|---|
| uncapped | 0.358 | **1.765** | 26 |
| capped @4 | 0.238 | **0.702** | 4 |

**Std inflated 151%.** So an event with **one prior CRL** is z-scored at **0.364** when its true value is **1.084** — **the CRL signal is compressed to roughly a third of its true magnitude for every event in the model.** Confirmed independently.

Their honesty about the limit of the fix is the right call: **capping the CSV does not fix a deployed model whose coefficients were fit on uncapped data. That needs a retrain.** Don't ship a "fix" that changes nothing.

### On `ppm_flag` — partially confirmed, needs one more check
In the **training data** it is *not* constant: `False 2183 / True 27` (1.2% positive). The encoder defaults it to 0 (`signals.get("ppm_flag", False)`), and **v19 appears to have pruned it** (absent from the returned feature contributions). So the constant `−0.596 / z=10.9` is likely a **v14 scoring-path** artifact, not a data one. Given v14 is leaked and disabled, this may be moot — but worth confirming which call site produces the constant before closing it.

---

# 2. 🔴 NEW — the fabrication is still in the crawler output, and `/llms.txt` is now LIVE

## The 5 fabricated events are unfixed
Re-ran my test against the newest file (`conference_presentations_history_FRESH.csv`, 980 rows — **the crawler has not been re-run yet**):

| Ticker | Assigned | Conf | Source text says |
|---|---|---|---|
| AUTL | 2026-12-12 | ASH | **2025** |
| COGT | 2026-12-12 | ASH | **2025** |
| CRBP | 2026-10-23 | ESMO | **2025** |
| CTMX | 2026-11-04 | SITC | **2025** |
| CELC | 2026-12-08 | SABCS | **2025** |

Plus **32 duplicates** and **3 residual ANE rows** in the file.

## And `/llms.txt` shipped (200)
I advised holding it until the crawler was verified clean. It's live.

**Right now this is safe** — I checked: `/api/v1/events?type=Conference` returns **14 events, none fabricated**. The crawler output has not been published to the site. So `llms.txt` currently points at clean data.

**The danger is the *next* publish.** The moment `/research/conference-runup` and the conference calendar are rebuilt from the deepened crawler set, those 5 phantom conferences go live — **into a site that is now explicitly inviting ChatGPT, Perplexity and Gemini to quote it.**

> **The fabrication guard must land BEFORE the next conference publish. Not after.**
> A wrong date on the site is a wrong date. A wrong date behind `llms.txt` is a wrong date that an AI repeats with total confidence, and that you cannot claw back.

CI guard is in `CRAWLER_REDTEAM_2026-07-12.md` — the rule is: **a stated year always wins; past-tense verbs can never produce a future date; never fall back to a conference start date.**

---

# 3. ✅ Verified shipped this pass

| | |
|---|---|
| **Homepage responsive fix** | ✅ `navddm` now present on `/` — the overflow bug is fixed |
| **`/about`** | ✅ 200 |
| **`/corrections`** | ✅ 200 — *the page no competitor would publish* |
| **`/llms.txt`** | ✅ 200 (see §2 for the caveat) |
| **Trilogy precision** | ✅ PDUFA now prints **+0.57%**, tilde gone, totals **"over 5,100"** |
| **ANE removal** | ✅ disclosed on the page |
| **Waitlist** | ✅ persist-only, KV live; the silent-lead-loss path now returns **503** instead of a false "you're on the list" — and stopped logging PII |
| **Crawler coverage** | ✅ 15 → **40** named searches; historical coverage 82.7% → **98.5%** |

**The waitlist finding is the one I'd highlight:** my hypothesis (Resend dependency) was **wrong**, but forcing the check surfaced a worse bug — the old code returned `200 {ok:true}` when KV was down, logging the address to a rotating function log. It didn't lose the request; **it lost the lead, silently, while telling the visitor they were signed up.** Exactly the unrecoverable failure. Now fixed, and PII no longer hits the logs.

---

# 4. ⭐ The single most important open question — and the builder framed it perfectly

> *"'98.5% coverage' means 98.5% of the **conferences we know about** — **not** 98.5% of presenters. Those are different claims and the page should not conflate them."*

**This is the real ceiling on the entire conference dataset.** The crawler only sees companies that **filed** about a presentation (8-K / PR on EDGAR). A company that presents quietly is structurally invisible, and no number of search phrases fixes that.

**We do not currently know what fraction of actual presenters we catch — and until we do, no coverage claim belongs on the page.**

Their proposed method is the correct one: pull a published abstract list (ASCO and AACR both expose searchable abstract databases), intersect against US-listed tickers, compute recall.

**I'll take this next if you want it.** It's the highest-value data job on the board now — it's the difference between "our conference data is comprehensive" (unproven) and "we catch X% of listed presenters, here's the number, here's what we miss" (defensible, and publishable as its own limitation).

---

# 5. ⬜ Still open

| Item | Note |
|---|---|
| 🔴 **Fabrication guard + re-run crawler** | 5 phantom events, 32 dupes, 3 ANE rows. **Must precede the next publish** — `llms.txt` is live. |
| 🔴 **Update CLAUDE.md** (ODIN v14 → v19-PRUNE) | Owner action. The memory file currently mandates a leaked model. |
| 🟠 **Measure presenter recall** against a real abstract list | The real coverage ceiling. Offered above. |
| 🟠 **P8-1 `/ticker/{TICKER}` hubs** | Still **404**. Biggest SEO left — ~400 pages, near-zero competition, and still absent from top 10 for the head term. |
| 🟠 **P6-1 BIFROST SI rebuild** | Still lookahead-biased. Also makes `explosion_score` unusable (SI/float are its top features). |
| 🟠 **ODIN retrain** on capped `prior_crl_count` | Capping the CSV alone changes nothing deployed. |
| 🟡 P4-4 CRL tracker reframe · market-cap null · real-device mobile QA | |

---
*Facts and historical statistics only. Not investment advice.*
