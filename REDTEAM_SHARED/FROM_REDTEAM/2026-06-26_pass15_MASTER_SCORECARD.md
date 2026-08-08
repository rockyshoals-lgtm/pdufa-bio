# pdufa.bio — MASTER STATUS SCORECARD · 2026-06-26 (Pass 15)

You've run ~14 audit passes — here's everything in one place, verified live today. ✅ done · ⚠️ partial · ❌ open. Skim the **"What still matters"** at the bottom if that's all you read.

## 🔒 Security
| Item | Status |
|---|---|
| Security headers (CSP report-only, X-Frame DENY, nosniff, Referrer-Policy, Permissions-Policy) | ✅ shipped |
| CORS scoped to own origin (was `*`) | ✅ |
| `security.txt` added | ✅ |
| No secrets in client / no exposed `.env`/`.git`/source | ✅ verified clean |
| **`/api/data` auth-gated** (the Pro data) | ❌ **STILL PUBLIC** — 200, full dataset, no creds |
| `/api/data.js` alias removed + rate-limiting | ❌ still live (200) |
| `.html` aliases 301'd (`/today.html`, `/app.html`) | ❌ still 200 (minor) |

## 🔧 SEO — technical
| Item | Status |
|---|---|
| Per-event JSON-LD (`@type`) | ✅ **FIXED** — now `BreadcrumbList + FAQPage + Event` |
| Per-event title length | ✅ FIXED (83 → **46**) |
| Per-event meta description | ✅ FIXED (232 → **154**) |
| Homepage title length | ✅ FIXED (95 → ~58, keyword-led) |
| Homepage Organization + WebSite schema | ✅ present |
| Homepage `SearchAction` (sitelinks search box) | ❌ missing |
| `/coverage` `Dataset` schema | ❌ none |
| Month-page `ItemList`/`BreadcrumbList` | ⚠️ FAQPage only (conditions have ItemList) |
| Sitemap coverage (170 URLs, all page types) | ✅ |
| Page speed (TTFB ~300 ms) | ✅ fast |

## 🗺️ SEO — pages & internal linking
| Item | Status |
|---|---|
| Month pages `/calendar/2026/[month]` (on-site links, FAQ, title) | ✅ |
| Condition pages `/condition/[slug]` (ItemList+FAQ, mis-tags cleaned) | ✅ |
| Readout-month pages `/readouts/2026/[month]` | ✅ exist |
| `/why-no-approval-probability` wedge page | ✅ |
| `/coverage` · `/sources` · `/research` · `/learn` (7 explainers) | ✅ |
| Homepage links to `/learn` `/research` `/readouts` | ✅ **FIXED** |
| Per-event bidirectional links (→ condition + month) | ✅ **FIXED** |
| **On-site `/readout/[id]` detail pages** | ❌ open — readout/condition rows still leak to CT.gov |
| Old ODIN ghost de-indexed (`Runup Heatmap`, `89.7%`, 4.8★) | ❌ still indexed — needs **GSC Removals** |
| New surfaces: `/this-week`, AdCom calendar, `/calendar/2027` | ❌ not built (P2) |

## 👥 Cohort conversion (the funnel each one is missing)
| Item | Status |
|---|---|
| **Retail:** email / "notify me" capture + weekly digest | ❌ **still none** — #1 retail gap |
| **Trader:** public teaser of the options/run-up depth | ❌ depth still hidden behind the gate |
| **Institution:** documented API + Enterprise tier + "request access" CTA on `/coverage` | ❌ API "on roadmap"; no enterprise tier/CTA |
| `/coverage` integrity page (counts, 98% sourced, limitations) | ✅ best-in-class |

## 🧪 Data quality & coverage
| Item | Status |
|---|---|
| `loa`/`pop` per-drug PoA stripped from API (guardrail) | ✅ |
| Condition mis-tags (eye-drops under Obesity, "disease disease") | ✅ cleaned |
| Per-event chart freshness | ❌ still dated **2026-06-19** (7 days stale) |
| Per-event story depth | ⚠️ ~433 words — partial; fuller story would help |
| **PDUFA recall (only ~46% of real PDUFAs captured)** | ❌ open — your page-count + completeness ceiling |
| 268 rows missing drug names | ❌ dropped, not backfilled |
| VRDN dup / GSK tebipenem double on calendar | ⚠️ unverified this pass (was open) |

## 🎨 Design
| Item | Status |
|---|---|
| Light-teal design system (tokens delivered Pass 10b) | ❌ not implemented — site still dark navy/gold |

---

## What still matters (the short list)
The builder has crushed the SEO **technical + structural** work — schema, titles, the new page types, internal linking are all done well. What's left is the **strategic, higher-effort** stuff:

1. **[P0] Gate `/api/data`** + remove the `.js` alias. The only true blocker before charging for Pro. (Open across 5 checks.)
2. **[P1] Close the 46% PDUFA-recall gap** + backfill the 268 missing drug names. This is your single biggest lever — it's simultaneously more indexable pages (SEO), a more complete product (institutions), and a better calendar (everyone).
3. **[P1] Conversion CTAs** — email/alert capture (retail), a public depth teaser (trader), a documented API + Enterprise tier + request-CTA (institution). All three cohorts still hit a dead end.
4. **[P1] On-site `/readout/[id]` pages** — stop leaking readout link-equity to CT.gov.
5. **[P2] Freshen the per-event chart**, deepen the story block, add `SearchAction`/`Dataset` schema, GSC-Remove the ODIN ghost, and build `/this-week` + AdCom + 2027 pages.
6. **[when ready] Implement the light-teal redesign** — the tokens are waiting; the site is still the dark terminal.
7. **[off-page, ongoing] The backlink/PR push** — still the only thing that takes the competitive head terms (Pass 10a kit).

**Bottom line:** the foundation is genuinely strong now and the SEO mechanics are largely done. You're down to **one security blocker, the coverage gap, the conversion CTAs, and the redesign** — that's the whole game from here. Nice work keeping the builder moving.

*— Red Team Pass 15 (consolidated verification + scorecard; live via Chrome).*
