# Bing console read — 2026-08-29
**Read live after sign-in. Companion to the Google read in `2026-08-29_audit_and_seo.md`.**
*Facts and historical statistics only — not investment advice.*

---

# 1. THE HEADLINE: AI citations are compounding hard

| | Aug 12 | Aug 18 | **Aug 26** |
|---|---:|---:|---:|
| **Total citations** | 115 | 413 | **1,600** |
| Avg cited pages | 7 | 8 | **12** |
| **Grounding queries** | 1 | 5 | **16** |

**Daily citations, last nine days:** 115 · 99 · 25 · 16 · **174 · 191 · 289**

**August 26 alone produced 289 citations** — more than the entire first week combined, and roughly 2.5× the previous single-day peak. This is not a plateau; it's still accelerating.

## Search performance, same window

| | Aug 18 | **Aug 26** |
|---|---:|---:|
| Clicks (3 mo) | 66 | **195** |
| Impressions | 2.7K | **6.4K** |
| CTR | 2.47% | **3.04%** |
| Keywords ranked | — | **321** |

Recent daily clicks: **22 · 20 · 14**, on ~430 impressions/day. Against Google's 53 clicks over 90 days, **Bing is running roughly 17× Google's daily rate.**

---

# 2. 🟢 THE INSIGHT THAT CHANGES THE STRATEGY

I've spent three audits calling the head terms dead weight because they produce no clicks. **That was only half the picture.**

| Query | Web impressions | Web clicks | Web CTR | **AI citations** | **Citation share** |
|---|---:|---:|---:|---:|---:|
| **pdufa date** | 199 | 3 | 1.51% | **91** | **19.08%** |
| **fda calendar 2026** | — | — | — | **49** | **20.16%** |
| **pdufa dates** | 6 | 0 | 0.00% | **12** | **35.29%** |
| pdufa | 615 | 2 | 0.33% | — | — |

**The head terms convert through AI, not through clicks.** "pdufa date" earns 3 web clicks and **91 AI citations**. "pdufa dates" earns zero clicks and holds **35% citation share**.

So the correct read is not "abandon the head terms." It's: **the head terms are already working — in the channel that's growing 4× a week — and the click number was measuring the wrong thing.**

## The entity long tail wins on both

| Query | Position | Web CTR | AI share |
|---|---:|---:|---:|
| **zanidatamab pdufa date** | — | — | **100.00%** |
| garetosmab pdufa | 2.00 | **33.33%** | — |
| pdufa calendar | 2.05 | **30.00%** | — |
| sabirnetug | 2.53 | **33.33%** | — |
| fda pdufa calendar | 3.69 | **38.46%** | — |
| camizestrant pdufa date | — | — | 37.50% |
| asundexian pdufa date | — | — | 29.09% |

**`zanidatamab pdufa date` sits at 100% citation share — we are the only source the engine cites.** That's the ceiling, and proof the format works.

**Nine of the sixteen grounding queries follow `{drug} pdufa date`** — rusfertide, asundexian, daraonrasib, camizestrant, povetacicept, zanidatamab, daraxonrasib, neladalkib, savara. The strategy is confirmed by the data rather than by argument.

---

# 3. 🔴 DARAXONRASIB — the problem isn't spelling, and I had it wrong

The alt-spelling fix shipped. The data now shows the real issue:

| | Web impressions | Position | Web clicks | AI citations | AI share |
|---|---:|---:|---:|---:|---:|
| `pdufa date for daraonrasib in usa` | 47 | 7.26 | **0** | 14 | **8.43%** |
| `daraxonrasib pdufa date` | 7 | 7.57 | **0** | 6 | **7.23%** |

**Both spellings now surface as their own queries — and both are the two lowest citation shares in the entire list (8.43% and 7.23%), against camizestrant at 37.5% and zanidatamab at 100%.** Both sit at position ~7.3–7.6 with zero web clicks.

**So this is a page-authority problem on that specific drug, not a spelling problem.** My 08-24 recommendation treated it as a lookup miss; the alt-spelling was worth adding, but it didn't move the needle because the page isn't competing. Worth comparing `/drug/daraxonrasib` against `/drug/camizestrant` and `/drug/zanidatamab` to find what those two have that it doesn't.

---

# 4. NOTED, NOT ACTIONABLE

Bing's AI-generated topic labels are misclassifying us:

- `pdufa date` → **"Holidays & Observances"**
- `rusfertide pdufa date` → **"ETFs & Retail Investing Products"**
- `pdufa date for daraonrasib in usa` → **"Hunting, Firearms & Ammunition"**

Only `zanidatamab pdufa date` → "Medications & Prescriptions" and `fda calendar 2026` → "Food & Drug Safety Regulations" are right. These are Bing's labels, not ours, and there's no documented lever to correct them — but if topic classification feeds citation eligibility, being filed under "Hunting, Firearms & Ammunition" is not helping. Worth watching, not chasing.

---

# 5. WHERE THIS LEAVES THE STRATEGY

| Channel | Status | Constraint |
|---|---|---|
| **Bing AI citations** | **1,600 and accelerating** | none visible — keep feeding it |
| Bing web | 195 clicks, 3.04% CTR | position: 33–38% CTR at position 2, ~0% at position 6–7 |
| Google web | 53 clicks, +56% | **authority — indexed frozen at 57 for 11 days** |

**Three things follow:**

1. **The citation surface is the product.** 1,600 citations from ~1,270 pages, 16 grounding queries, one at 100% share. Every new `{drug} pdufa date` page is a candidate grounding query.
2. **Don't judge head terms by clicks.** They're producing the largest citation blocks on the site.
3. **Google still needs authority, not pages** — unchanged from this morning's read.

---

# 6. BOTTOM LINE

**AI citations went 115 → 413 → 1,600, and August 26 alone was 289.** Grounding queries went 1 → 5 → 16. That is the fastest-compounding thing on this property by a wide margin, and it is the channel the site's structure was built for.

**The finding that changes my prior advice:** head terms produce almost no clicks but the *largest* citation counts — "pdufa date" earns 3 clicks and 91 citations. I'd been reading the click number as the whole story for three audits. It wasn't.

**And I had daraxonrasib wrong.** The alt-spelling was worth adding, but both spellings now sit at ~7.5 position with zero clicks and the two lowest citation shares on the board. That's authority on that page, not a lookup miss.

`zanidatamab pdufa date` at **100% citation share** shows what the ceiling looks like when a page does compete.

---
*Bing Webmaster Tools read live 2026-08-29 for the window Aug 8–26. Not investment advice.*
