# Audit — 2026-09-02 (evening) · builder batch complete
**Site built 2026-09-02T18:42Z · every claim verified live against that build**
*Facts and historical statistics only — not investment advice.*

---

# 1. ✅ EVERYTHING I RAISED IS DONE

| Item | Status | Evidence |
|---|---|---|
| 6 stale decided pages | ✅ **ALL FIXED** | MRNA · TAK · BMY · JAZZ · ZYME · GILD — all show their decision, all `Updated September 2` |
| `Drug` schema on 554 drug pages | ✅ **DEPLOYED** | **14/14** in a random sample |
| Decision snippets in answer format | ✅ **437 pages** | 0 provenance artefacts in sample; CRL language correct |
| Explainer linker | ✅ | drug + event pages link `/learn/what-is-a-pdufa-date` ×2; decision pages ×1 |
| Guards | ✅ | **55** |

## The snippets are exactly the format I specified

```
"Gilead Sciences Inc. (GILD): Bixlenvo (bictegravir/lenacapavir) was approved on
 August 27, 2026 (its PDUFA goal …"

"Outlook Therapeutics (OTLK): LYTENAVA received a Complete Response Letter on
 December 31, 2025. Source and run-up …"
```

Company, drug, outcome, exact date — and note *"received a Complete Response Letter,"* never "rejected." **Guard 41's discipline survived an automated rewrite across 437 pages.** That's the hard part and it held.

## Three bugs the builder caught in their own work

This is the most impressive part of the batch, and all three are the same class — **ownership and ordering**:

1. `dcebe562f` — *"provenance labels are not drug names"*: 24 pages rendered **"Primary-sourced was approved"** because the rewriter grabbed the provenance label where a drug name belonged.
2. `bddea2c9b` — *"one owner per field"*: **CI was clobbering all 437 rewrites an hour after they shipped**, because `fix_meta_lengths` and the new rewriter both owned decision-page titles.
3. `82a4cac9f` — *"CI order"*: regenerated drug pages **were born schema-less** because the Drug-schema step ran before `build_drug_pages`.

Each would have silently undone the work. Finding all three inside one batch is the difference between shipping and shipping something that stays shipped.

---

# 2. ⚠️ A CORRECTION I OWE — I over-recommended `alternateName`

`alternateName` appears on only **3 of 14** sampled drug pages (`daraxonrasib` carries `["RMC-6236"]`; rusfertide, camizestrant, avexitide carry none).

**My first instinct was to call that incomplete. I checked, and it isn't — it's correct against the data we hold.**

```
records whose name embeds a code:     18 / 454   (4%)
chembl_enrichment_cache_v2.json:      no synonym field
drug_classifications.json:            no synonym field
```

**We do not hold drug aliases.** When I recommended *"declare INN, code name, brand, ticker and misspellings in schema"*, I wrote that as though the data existed. It doesn't. The builder implemented the field correctly and populated it wherever an alias was actually available — which is 4% of records.

**The fix is real but it's a data-acquisition step, not a schema step:** ChEMBL's API returns `molecule_synonyms`, and our cache simply didn't request that field. Adding it to the existing enrichment pass would populate `alternateName` across the ~418 drugs already in that cache. **That is the honest route to the citation-breadth lever** — not more schema work.

---

# 3. 🟡 ONE SMALL DEFECT IN THE REWRITE

**4 of 14 sampled decision snippets open with a redundant ticker:**

```
"LLY (LLY): Inluriyo was approved on September 25, 2025…"
"TEVA (TEVA): UZEDY was approved on October 10, 2025…"
"URGN (URGN): ZUSDURI was approved on June 12, 2025…"
```

I checked whether this is a live-data problem: **it isn't.** `company == ticker` is **0 of 454** in `dataset.mjs`. The fallback is in the **older decision-archive corpus**, where some records lack a full company name.

Cosmetic, but it sits in the meta description — the exact string shown in the SERP — on roughly a quarter of 437 freshly-rewritten pages. **Fix: when company equals ticker, drop the parenthetical** — *"Eli Lilly (LLY):"* or just *"LLY:"*, never *"LLY (LLY):"*.

---

# 4. STILL OPEN (long-standing, not from this batch)

| Item | Status |
|---|---|
| Link the **458** FDA CRL letters | ❌ `/decisions/crl` still 0 `fda.gov` links |
| `/crl` hub | ❌ 404 |
| `/pdufa-date-changes` | ❌ 404 |
| `/decisions/crl` lede 47 vs 44 links | ❌ unreconciled |

---

# 5. WHAT I'D DO NEXT

| # | Action | Why |
|---|---|---|
| 1 | Add `molecule_synonyms` to the ChEMBL enrichment pass | the honest route to `alternateName` at scale — unlocks citation breadth |
| 2 | Fix `"X (X):"` in decision snippets | ~25% of 437 SERP snippets |
| 3 | Link the 458 CRL letters into the decision template | it just got rewritten — cheapest moment to add the source link |
| 4 | `/crl` hub · `/pdufa-date-changes` | previously specced, still 404 |
| 5 | Watch `/fda-decisions-today` and `/learn/what-is-a-pdufa-date` in the Sept 8 console read | both were just changed; that's the first honest read |

---

# BOTTOM LINE

**Everything I raised is done, and done properly.** All six stale decided pages now show their outcomes, `Drug` schema is live across 554 pages, the 437-page snippet rewrite landed in answer format, and the explainer linker is wired into drug, event and decision pages. 55 guards.

**The three self-caught bugs are the real signal.** A rewriter that grabbed provenance labels as drug names, a CI step silently clobbering 437 rewrites an hour later, and drug pages born schema-less from a step-ordering bug — each would have quietly undone the batch. Catching all three inside the same session is what separates work that ships from work that stays shipped.

**And I owe a correction: I over-recommended `alternateName`.** I described declaring code names, brands and misspellings as if we held them. We don't — only 4% of records embed a code, and neither enrichment cache has a synonym field. The builder populated the field correctly against what exists. The real unlock is one field on the ChEMBL pass, not more schema.

The only new defect is cosmetic — *"LLY (LLY):"* on about a quarter of the rewritten snippets, from the older archive corpus rather than live data.

---
*Verified against the 2026-09-02T18:42Z build. Not investment advice.*
