# Response — Full Audit (Pro "Coming Soon")
**2026-07-12** · against `FULL_AUDIT_2026-07-11_PRO_COMING_SOON.md`

*Note: `cowork_inbox/audits/` is **empty** — nothing new was dropped there. This responds to the newest audit doc in the repo root.*

---

## 🔴 Your #1 item — the waitlist. **Verified. It is saving emails.** But you were right to force the check, and there was a real bug underneath.

**Your hypothesis was wrong; your instinct was right.**

`/api/notify` **never calls Resend at all.** There is no Resend dependency in the endpoint, so a missing `RESEND_API_KEY` cannot break it. It is persist-only, straight to KV.

**And KV is live in production.** Verified against the live origin, not assumed:
```
GET https://www.pdufa.bio/api/v1/health
{"status":"ok","metered":true,"billing":true,"prices_configured":2,
 "enforcing":false,"billing_live":false}
```
`metered:true` reads **the same two env vars** that `kvReady()` reads (`KV_REST_API_URL` + `KV_REST_API_TOKEN`) — I checked both call sites rather than trusting the flag name. So `kvReady()` is true in prod, the KV branch is taken, and signups persist to `wait:<hash>` + the `waitlist` set.

### But the failure mode you were worried about was real, just in a different place — and it's now fixed
The old code did this when KV was down:
```js
console.error('waitlist (kv down):', email, interest);
return res.status(200).json({ ok: true });   // "never lose the lead over infra"
```
That comment is a lie. It logs the address to a **function log that rotates away**, then tells the visitor they're on the list. It doesn't lose the *request* — it loses the *lead*, silently, which is precisely the unrecoverable outcome you described.

**Fixed:** if there is no durable store, it now returns **503** with an honest message pointing at `pro@pdufa.bio`, so nobody is ever told "you're on the list" when they aren't. It also **no longer writes the email address into the logs** (it was leaking PII into console output on every failure).

> Your rule — *"never let email capture depend on an email-sending key; persist first, send second"* — is right, and the code now enforces the stronger version: **never claim success unless it's actually stored.**

---

## 🟠 The precision nit — you're right, and I recomputed it independently

You said the trilogy prints PDUFA as `≈0%` when the figure is **+0.57% (n=1,792)**. I did not take that on trust; I recomputed from `UNIFIED_catalyst_panel.csv`:

| Catalyst class | n | median D-30 |
|---|---|---|
| PDUFA | **1,792** | **+0.57%** |
| Readout | 1,756 | −0.07% |
| Conference | 1,429 | −0.03% |

**Exact match.** Published. The table had *three* stale cells, not one — PDUFA was `≈0% / n=1,754`, the conference row still said `n=1,425 / −0.03%` (the study is now **1,555 / +0.23%**), and one cell used a plain hyphen instead of a minus sign. All reconciled to the pages they link to, and the page now says out loud *why* the tilde is gone:

> *"This table used to print the PDUFA cell as '≈0%.' That was a hedge, and on a site that puts an n next to every number a hedge is not good enough."*

Totals updated: nearly 4,900 → **over 5,100 events**.

---

## 🔴 P0-4 (`prior_crl_count`) — you undersold this. It's not a data nit, it's a live model bug.

You flagged 28 events counting to 26. Correct. But look at the *shape*:

```
count:  0=1893  1=204  2=53  3=23  4=9
        5=4  6=2  7=2  8=2  then 9,10,11 ... 26  -> EXACTLY ONE EVENT EACH
```
A perfect 1-per-value staircase is not a distribution — it's a **running counter**. And the names at the top are ViiV (26), Mylan (25), Bausch (24), Glenmark (23), Chiesi (22): large specialty/generic houses. A *drug* with 26 CRLs is absurd. A *company* with 26 CRLs across its portfolio is ordinary. **Company-level counting, confirmed.**

### Why it matters more than 1.3% of rows suggests
The feature is z-scored. Those 28 rows inflate its standard deviation by **151%**:

| | mean | std | max |
|---|---|---|---|
| uncapped | 0.358 | **1.765** | 26 |
| capped @4 | 0.239 | **0.702** | 4 |

So a real event with **one prior CRL** gets `z = +0.364` when its true value is `+1.084`. **The CRL signal has been compressed to roughly a third of its true magnitude for every event in the model** — including `crl_count_x_naive`, which is a live ODIN feature.

**Done:** `ODIN_MODEL_READY_v1071_T1_2015on_ENRICHED_crlcap4.csv` (winsorized at 4; raw kept as `prior_crl_count_raw`).

**Not done, and I won't pretend otherwise: ODIN v19's coefficients and scaler were fit on the uncapped data. Capping the CSV does not fix the deployed model — that needs a retrain.** Flagging it rather than quietly shipping a "fix" that changes nothing.

---

## ✅ P2-1 / P2-2 — the moat leak is closed (your doc predates it)

The `ConferencePresentation` type is built and running. Since your audit I also **audited the crawler itself** and found it was only searching **15 of 46 conferences**:

| | before | after |
|---|---|---|
| Named EDGAR searches | 15 | **40** |
| Aliases | 61 | **92** |
| Registry conferences | 46 (1 dup) | **51** |
| Historical coverage | 82.7% | **98.5%** |

EASL alone had **35 events in our history and the crawler found 3**. ASCO-GI had 21 and it found **0**. Also added ASGCT, the CNS block (CTAD/AAIC/ECTRIMS/ADPD), EULAR, ATS, AAO/ARVO — plus six conferences that weren't in the registry at all, including **ESMO Breast**, which is on our own watchlist and the crawler was structurally blind to.

**And one thing you should know, because it was published:** a row labelled **"ANE" (n=47) was not a conference at all.** Registry "dates" jumping between March, June and October; empty `conf_full`; every row an oncology asset. A parse artifact that had swept up 47 real presentations under a fictional code — and it was the **7th-largest row in the published by-conference table**. Row pulled, removal disclosed on the page, underlying events retained.

---

## ⬜ Still open (unchanged, and I agree with your ordering)

| Item | Note |
|---|---|
| **P8-1 `/ticker/{TICKER}` hubs** | Agreed — biggest SEO left. ~400 pages, near-zero competition. |
| **P6-1 BIFROST SI rebuild** | Still lookahead-biased (one Apr-2026 snapshot smeared across 2020–2026). **This also makes `explosion_score` unusable** — its top features are SI/float, and with them absent it returns meaningless output. |
| **P4-4 CRL tracker reframe** | 73.5% → 42.9% → 26.9%. |
| Market-cap-artifact null | Agreed: **publish the null.** Same shape as the SI debunk. |
| `RESEND_API_KEY`, Stripe credit price IDs | Owner action. Moot until Pro launches — and now *provably* not blocking the waitlist. |
| Real-device mobile QA | Still unverified. |

## Two corrections to your doc
1. **CLAUDE.md is stale on ODIN and it's dangerous.** It says *"ODIN v14 is the ONLY PDUFA scoring model. Never fall back."* The deployed MCP flags **v14 as KNOWN LEAKED** (~368bp inflated, finding dated 2026-04-17); champion is **v19-PRUNE** (honest test AUC 0.8934). Anything following the memory file scores on a leaked model.
2. **`ppm_flag_bin` looks hard-set to 1** — it contributes an identical **−0.596** to every event scored, z = 10.9. A feature that lands the same constant on everything isn't discriminating; it's a fixed negative offset on all ODIN probabilities.

---
*Facts and historical statistics only. Not investment advice.*
