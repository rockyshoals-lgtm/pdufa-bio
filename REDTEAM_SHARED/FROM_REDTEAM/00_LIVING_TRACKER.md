# pdufa.bio — LIVING TRACKER (single source of truth)
_Last updated: 2026-06-28 · Pass 19 · maintained by the Red Team chat_

**This is the one doc to check.** I re-verify and update it every audit pass. Detailed findings live in the dated `passN_*.md` files; this stays current. Legend: ✅ done · ⚠️ partial · ❌ open · ⏳ delivered, awaiting build.

---

## 🎯 Do next (in priority order)
1. **🔴 Fix indexing — only 11 of 170 indexed (GSC, snapshot Jun 11 — predates the Jun-25 sitemap, so partly lag).** Root cause CORRECTED (Pass 19b, direct-tested): **both apex + www serve 200, neither redirects**; canonical/sitemap/robots all = apex. **Builder fix:** `301 www→apex`, root-relative internal links, drop the stale 35-page www sitemap, 410 the 3 ghosts, dedupe `/pricing.html`; then re-submit + request-index. Full spec → ticket **`pass19b`**. *(GSC ghost removals already done.)* Also: zero backlinks = slow crawl, so this is hygiene, not an overnight switch.
2. **🔴 Gate `/api/data`** (auth, or free/pro split) + remove the `/api/data.js` alias + rate-limit. *The only true blocker before charging for Pro.*
2. **PDUFA-recall gap — DONE except the crawl run:** seed expanded + transcript miner + self-completing `seed_candidates.csv` (Pass 17); seed now **25 rows, 100% source-URL verified** (Pass 18 — 3 wrong/stale links fixed). **Only step left: re-run `run_crawler_full.bat`** so the mega-caps merge into `catalysts_public.csv` and go live.
3. **Add the conversion CTAs each cohort is missing:** email/alert capture (retail) · public depth teaser (trader) · documented API + Enterprise tier + "request access" CTA (institution).
4. **Build on-site `/readout/[id]` pages** so readout/condition rows stop leaking to ClinicalTrials.gov.
5. **GSC Removals of old ODIN ghosts — ✅ DONE (Pass 19).** Durable 410/301 on the 3 ghosts still pending (builder). Plus: freshen the per-event chart + deepen the per-event story.
6. **When ready:** implement the light-teal redesign (tokens in `pass10b`).
7. **Ongoing (owner):** the backlink / digital-PR push (kit in `pass10a`) — the only thing that wins the head terms.

---

## 🟢 Recently shipped (verified live)
- **Pass 19 audit (usability · moat · SEO · indexing):** builder shipped good on-charter content (`/decisions` archive + 20 `/fda-decision/*` outcome pages, `/devices`, `/clinical-trial-success-rates`, `/fda-approval-rate`, `/methodology`, `/pricing` — Pro $29). Mobile homepage clean (hero-card P0 stays fixed). **But GSC shows only 11/170 indexed** — root-caused to the apex-canonical/redirect bug. **I submitted GSC temporary-removals for the 3 ODIN ghost URLs** (kills the "93.6% approval" snippets). Detail in `pass19`.
- **Seed source-URLs verified (Pass 18):** all 25 mega-cap seed rows fetch-checked against drug + PDUFA date. 3 fixed (LNTH stale pre-extension date → extension PR; MRK + ALPMY were pointing at the wrong bladder-cancer sub-indication → Astellas Apr-21 perioperative PR). 2 "unverifiable" flags (BIIB, NVO) confirmed real. **Seed is now 100% sourced** — safe to republish. Detail in `pass18`.
- **Crawler fixes implemented (Pass 17):** `bigpharma_pdufa_seed.csv` expanded (every missed mega-cap PDUFA), `qa_diff` drug-recall metric, opt-in `--transcripts` earnings-transcript miner, self-completing `seed_candidates.csv`. Compile-verified; backed up. Recall simulation 46%→100% (month). Needs the crawl run to go live.
- Per-event JSON-LD fixed → `BreadcrumbList + FAQPage + Event`; titles/metas shortened sitewide; per-event ↔ condition/month bidirectional links; homepage now links /learn /research /readouts.
- Month + condition + readout-month pages live and clean (on-site links, schema, mis-tags removed, title-escape bug fixed).
- `/why-no-approval-probability`, `/coverage`, `/sources`, `/research`, `/learn` (7) live. Sitemap 170 URLs.
- Security headers, CORS scoping, `security.txt`. Old ODIN Vercel project deleted; cache purge; `—` + hero-card mobile bugs fixed; `loa`/`pop` PoA stripped from the API.

---

## 📋 Full status by area

### 🔒 Security
| Item | Status |
|---|---|
| Security headers (CSP-RO, X-Frame DENY, nosniff, Referrer, Permissions) | ✅ |
| CORS scoped to own origin · `security.txt` · no client secrets / no exposed files | ✅ |
| **`/api/data` auth-gated** | ❌ still public (200, full data, no creds) |
| `/api/data.js` removed + rate-limiting | ❌ still live |
| `.html` aliases 301'd | ❌ minor |

### 🔧 SEO — technical
| Item | Status |
|---|---|
| Per-event JSON-LD (`@type`) · titles ≤60 · metas ≤155 | ✅ |
| Homepage title · Organization+WebSite schema | ✅ |
| Homepage `SearchAction` | ❌ |
| `/coverage` `Dataset` schema | ❌ |
| Month-page `ItemList`/`BreadcrumbList` | ⚠️ FAQ only |
| Sitemap (170 URLs) · page speed (~300 ms TTFB) | ⚠️ 2 sitemaps (stale www 35-pg + apex 170) |
| **Google indexing (GSC)** | 🔴 **11 of 170 indexed** (Jun-11 snapshot; partly lag — see `pass19b`) |
| One canonical host | 🔴 apex+www **both serve 200, no redirect** → add 301 www→apex |
| New-page schema: `/devices` `/readouts` `/pricing` | ❌ none (add ItemList / Product+Offer) |

### 🗺️ SEO — pages & internal linking
| Item | Status |
|---|---|
| Month / condition / readout-month pages | ✅ |
| Homepage → hub links · per-event bidirectional links | ✅ |
| **On-site `/readout/[id]` pages** | ❌ rows still leak to CT.gov |
| Old ODIN ghosts (`/pdufa-calendar`, `/pdufa-dates-2026`, `/biotech-catalyst-calendar`) | ⚠️ GSC removals submitted (Pass 19); 410/301 still needed |
| New content: `/decisions` + 20 `/fda-decision/*` + `/devices` + 2 SEO-content pages | ✅ live, on-charter |
| New surfaces: `/this-week`, AdCom calendar, `/calendar/2027` | ❌ not built |

### 👥 Cohort conversion
| Item | Status |
|---|---|
| Retail: email/alert capture + weekly digest | ❌ #1 retail gap |
| Trader: public teaser of options/run-up depth | ❌ |
| Institution: API + Enterprise tier + request-CTA | ❌ |
| `/coverage` integrity page | ✅ best-in-class |

### 🧪 Data quality & coverage
| Item | Status |
|---|---|
| `loa`/`pop` stripped (guardrail) · condition mis-tags cleaned | ✅ |
| Per-event chart freshness | ❌ stale (2026-06-19) |
| Per-event story depth (~433 words) | ⚠️ partial |
| **~46% PDUFA recall** · mega-cap gap | ⏳ FIXED, awaiting crawl run (Pass 17–18): seed = 25 mega-cap rows, **100% source-URL verified**; sim recall 46%→100% (month). Run `run_crawler_full.bat` to go live. You already **beat** BPC on readouts (1,000 vs ~444). |
| VRDN dup / GSK tebipenem double | ⚠️ recheck |

### 🎨 Design
| Item | Status |
|---|---|
| Light-teal design system (tokens `pass10b`) | ⏳ delivered, not implemented (still dark navy) |

### 🔗 Off-page / growth
| Item | Status |
|---|---|
| Digital-PR / backlink push (kit `pass10a`) | ❌ owner action — start this week |
| Recurring monthly `/research` data drop | ❌ |

---

## 🗂️ Pass history (where the detail lives)
- **Pass 1** — full Section-4 audit (competitors, cohorts, SEO IA, web/mobile UX, top-10)
- **Pass 2 / 2b** — CDN cache bug + data-freshness/infra
- **Pass 3 / 3b** — verification + first live gated QA
- **Pass 4** — competitive battle plan (live competitor teardown)
- **Pass 5** — live re-audit
- **Pass 6 / 6b** — retail + SEO-placement + the page-1 action plan
- **Pass 7 / 8** — verify + next (month/condition pages shipped)
- **Pass 9** — strategy (cohort truths, differentiation, design direction, July-1 reality)
- **Pass 10a / 10b** — digital-PR kit · light-teal design tokens
- **Pass 11 / 12** — security audit + re-audit
- **Pass 13** — re-audit + new SEO opportunities
- **Pass 14** — cohort appeal + technical SEO (with concrete specs)
- **Pass 15** — master scorecard (folded into this tracker)
- **Pass 16** — crawler-vs-BPC coverage audit (the 46% gap root-caused)
- **Pass 17** — crawler fixes *implemented* (seed 4→44, transcript miner, self-completing loop; recall 46%→100% simulated)
- **Pass 18** — seed source-URL verification (all 25 fetch-checked; 3 wrong/stale links fixed; seed now 100% sourced)
- **Pass 19** — usability · moat · SEO + indexing audit (GSC: 11/170 indexed; submitted removals for 3 ODIN ghosts; new builder content reviewed)
- **Pass 19b** — builder ticket: one canonical host. Direct-tested + **corrected** the Pass-19 host claim (both apex+www serve 200, no redirect → add 301 www→apex; apex stays canonical)

---

## ℹ️ How this stays current
Each pass I: re-verify the live site, flip statuses here, move newly-shipped items into "Recently shipped," add any new findings to "Do next," and bump the date + pass number at the top. For big new analyses I'll still drop a dated `passN_*.md` for depth and link it above — but **this file is always the current picture.** You're one person doing a lot; the deal is you never have to reconstruct where things stand — just open this.

*Builder: this is the canonical status. Your detailed action items are still in the dated files; this is the at-a-glance.*
