# Patent cliff — build pack (data delivered) + email capture spec
**2026-08-12 · the data is built, verified and ready to publish**
*Facts and historical statistics only — not investment advice.*

---

# 0. WHAT'S DONE IN THIS SESSION

| | |
|---|---|
| **973 URLs pushed to IndexNow** | HTTP 200, both endpoints. Everything the builder shipped today is now queued at Bing, Yandex, Seznam, Naver. |
| **427-row patent cliff dataset** | `patent_cliff_2026_2031_TA.csv` — brand, ingredient, company, LOE, patent count, **therapeutic family** |
| **Therapeutic-area gap closed** | **97% classified** (415/427) via WHO ATC through the NIH RxClass API |
| **Classifier red-teamed and fixed** | 2 defect classes found in my own output and corrected — see §4 |

**Decisions taken:** new content surfaces as the growth channel; start an email list now.

---

# 1. THE DATA

`patent_cliff_2026_2031_TA.csv` — **427 brand NDAs losing exclusivity 2026–2031.**

Columns: `loe · brand · ingredient · company · appl_no · n_patents · substance_patent · approval_date · therapeutic_family · atc_code`

### By year
| 2026 | 2027 | 2028 | 2029 | 2030 | 2031 |
|---:|---:|---:|---:|---:|---:|
| 19 | 64 | 80 | 87 | 75 | **102** |

### Top companies
AbbVie **14** · Novartis 11 · Takeda 11 · Merck 10 · Bayer 10 · Azurity 8 · ViiV 8 · Boehringer 7 · Salix 6 · AstraZeneca 6

### By therapeutic family
Infectious disease 41 · **Cancer 40** · Metabolism & digestive 37 · Respiratory 34 · Genitourinary & hormones 32 · Cardiovascular 29 · Dermatology 27 · Pain 24 · Eye & ear 24 · Neurology & psychiatry 23 · **Diabetes 22** · Psychiatry 16 · Musculoskeletal 16 · Blood 14 · Various 13 · Hormonal 6 · Epilepsy 6 · Parkinson's 5 · Immunology 5 · Antiparasitic 1 · **Unclassified 12**

### The nearest cliffs — your launch hook
| LOE | Brand | Ingredient | Company | Patents |
|---|---|---|---|---:|
| **2026-08-13** | NUEDEXTA | dextromethorphan/quinidine | Otsuka | 1 |
| 2026-08-19 | TEKTURNA | aliskiren | LXO Ireland | 4 |
| 2026-08-24 | DYMISTA | azelastine/fluticasone | Mylan Specialty | 2 |
| 2026-09-22 | SENSIPAR | cinacalcet | Amgen | 6 |
| **2026-09-28** | **SPRYCEL** | **dasatinib** | **Bristol Myers Squibb** | **12** |
| 2026-10-06 | SAPHRIS | asenapine | AbbVie | 21 |
| 2026-10-12 | ANDROGEL | testosterone | Besins | 24 |
| 2026-12-07 | PROTONIX | pantoprazole | Wyeth | 2 |
| 2026-12-12 | CORLANOR | ivabradine | Amgen | 4 |

**NUEDEXTA's last patent expires tomorrow.** That's a live news hook for launch day.

---

# 2. PAGE STRUCTURE

```
/patent-cliff                      hub — by year · by company · by family
/patent-cliff/2027                 64 drugs
/patent-cliff/2028                 80 · /2029 87 · /2030 75 · /2031 102
/patent-cliff/company/abbvie       14 · novartis 11 · takeda 11 · merck 10 · bayer 10
/patent-cliff/cancer               40 · /diabetes 22 · /infectious-disease 41 · …
/drug/{name}  →  "Patent protection" module on the 310 existing pages
```

**~30 new indexable pages** from one dataset, each targeting a query family we currently rank for nowhere: *"when does SPRYCEL go generic"*, *"2027 patent cliff"*, *"AbbVie patent expirations"*.

**The `/drug/` module is the higher-value half** — it deepens pages that already rank and already get cited, and creates internal links into the new hub.

---

# 3. COPY — written to the plain-language spec

## 3.1 The disclosure that goes on every cliff page, non-negotiable

> **This is the earliest date a generic could enter — not a guarantee one will.**
> We calculate it as the later of the last patent the company listed with the FDA and the last regulatory exclusivity. Companies often settle with generic makers for a different date, and those agreements are not public in this data.

Guard 41 already has the LOE claim dormant-armed. **Arm it.**

## 3.2 Hub page

> # Patent Cliff Tracker
> **427 brand-name drugs lose their patent protection between 2026 and 2031.** When protection ends, generic manufacturers can apply to sell the same medicine — usually at a much lower price, and usually taking most of the sales.
>
> This tracks which drugs, which companies, and when — from the FDA's own Orange Book, the official record of which patents cover which approved drug.
>
> *[disclosure block]*

**Plain-language notes:** "patent cliff" stays in the title because it's the query. "Loss of exclusivity" never appears without being explained. No claim about what any company will *do*.

## 3.3 Year page

> # 2027 Patent Cliff
> **64 drugs lose patent protection in 2027.** The biggest single group is [family], with [n] drugs.
>
> Losing protection doesn't mean a drug disappears. It means other manufacturers can apply to sell the same medicine, and the original maker usually loses most of the sales within a year or two.

## 3.4 Company page

> # AbbVie Patent Expirations
> **AbbVie has 14 drugs losing patent protection between 2026 and 2031** — more than any other company in this data.
> The nearest is SAPHRIS (asenapine) on October 6, 2026. AbbVie listed **21 patents** on it with the FDA; that's the last one to expire.

**Stop there.** State the facts; don't write "AbbVie needs to acquire." That's a prediction and it breaks the rule that makes us citable.

## 3.5 `/drug/` module

> ### Patent protection
> **SPRYCEL's last listed patent expires September 28, 2026.** Bristol Myers Squibb listed 12 patents on it with the FDA.
> This is the earliest date a generic could enter — not a guarantee one will. *[link to /patent-cliff/2026]*

## 3.6 FAQ — the citation unit (`FAQPage` on every cliff page)

| Question | Answer |
|---|---|
| When does SPRYCEL go generic? | "SPRYCEL's last listed patent expires September 28, 2026. That's the earliest a generic could enter; settlements can change the actual date." |
| How many drugs lose patent protection in 2027? | "64 brand-name drugs lose patent protection in 2027." |
| Which company has the most patent expirations? | "AbbVie, with 14 drugs losing protection between 2026 and 2031." |
| What is a patent cliff? | "The point when a drug's patent protection ends and generic manufacturers can sell the same medicine, usually taking most of the sales." |
| Where does this data come from? | "The FDA Orange Book, the official record of which patents cover which approved drug. Updated monthly." |

One declarative sentence, a number and a date. That's the unit an engine lifts.

---

# 4. RED TEAM — on my own classifier

I found and fixed two defect classes in my own output before handing it over.

**Defect 1 — a single minority code hijacked the family.**
`ethinyl estradiol` returns 16 ATC codes: 15 are `G03*` (sex hormones/contraceptives) and exactly **one** is `L02AA` (estrogens used in oncology). My first version scanned for the first refinement match and classified **BALCOLTRA, a contraceptive, as "Cancer"** — on a page that would have named Avion Pharmaceuticals.

Fixed by selecting the **modal** anatomical group first, then refining only inside it. **This moved the Cancer count from 48 to 40 — eight drugs were wrongly labelled cancer drugs.**

**Defect 2 — single-guess lookups produced false "Unclassified".**
`carbidopa; levodopa`, `exenatide synthetic` and `azilsartan kamedoxomil` all came back empty because each was only queryable under a different form. Now every combo component and every salt-stripped variant is tried, and the codes are unioned. Coverage went 95% → **97%**, and Rytary→Parkinson's, Bydureon→Diabetes, Edarbi→Cardiovascular all resolved correctly.

**The 12 that remain unclassified are genuine edge cases** — three Technetium Tc-99m radiopharmaceutical kits, three iron products, topical menthol, and four others. **They are labelled "Unclassified" and not guessed.** A gap is better than a wrong therapeutic area on a page that names a company.

## Known limitation to disclose
ATC classifies **tafamidis (VYNDAQEL)** as `N07XX` — nervous system — though it's best known for ATTR cardiomyopathy. ATC reflects the WHO's classification, not the commercial indication. Where family and common understanding diverge, **the drug page should lead with the indication and let the family be a filter**, not a claim.

---

# 5. EMAIL CAPTURE

You chose to start a list. Three things have to move together.

## 5.1 The pricing-page line must change first
Currently live:
> *"Pro isn't taking payments or sign-ups. … **We're not collecting emails in the meantime.**"*

Replace with something that stays true:
> *"Pro isn't taking payments yet. It opens when we're satisfied with the product, not before. You can get a heads-up when a date on the calendar moves — and we'll tell you when Pro opens."*

**And delete the 7-day free-trial FAQ in the same commit.** Shipping an email form while a page advertises a trial that doesn't exist is the worst possible combination.

## 5.2 What to offer — value first, not a waitlist
A "tell me when Pro launches" box converts badly because it asks for something and gives nothing. Offer the thing people already want:

> **Get notified when an FDA date moves.**
> We track 427 catalysts. When a PDUFA date shifts, slips, or a decision lands, you hear about it. Free, no account.
> `[ your@email ]  [ Notify me ]`
> One email per change, unsubscribe in one click. We don't sell or share your address.

Two checkbox options at signup — *date changes* and *tell me when Pro opens* — and you get both lists from one form.

## 5.3 Placement
| Where | Why |
|---|---|
| Below the fold on `/calendar` | highest-traffic page, #1 on Bing — **do not touch the top of this page** |
| Bottom of every `/drug/` page | 310 pages, high intent |
| `/decisions`, `/readouts` | after the content |
| `/patent-cliff` at launch | new surface, no ranking to protect |

**Not** an interstitial or exit popup. Those hurt mobile rankings and they'd contradict everything the brand says about itself.

## 5.4 Requirements before the form goes live
- **Privacy policy** — legally required the moment you collect an address. You need it for Stripe anyway (see the readiness file).
- **One-click unsubscribe** in every email.
- Double opt-in — protects deliverability, and the confirm click is proof of consent.
- `RESEND_API_KEY` verified end to end. **It's already the only login path and it's unverified.**

## 5.5 Why this matters more than it looks
The alerts engine is unbuilt and is the one thing gating a Pro launch. **A free date-change alert list is the same engine.** Build it once: diff today's slate against yesterday's, send to subscribers. Free tier gets date changes; Pro gets run-up-window entry, cap-tier filtering and same-day decisions.

**So the email list isn't a detour from the paywall — it's the first half of the feature you have to build anyway.**

---

# 6. ORDER

| # | Item | Effort |
|---|---|---|
| ~~1~~ | ~~Bing API migration~~ — **withdrawn 2026-08-12. My error, not a defect: `api.svc/json` is Microsoft's migration *target*; SOAP/POX retire and this codebase has zero of either.** | no action |
| 2 | Delete the free-trial FAQ + rewrite the "not collecting emails" line | minutes |
| 3 | Privacy policy (needed for email *and* payments) | half day |
| 4 | `/patent-cliff` hub + year pages + `/drug/` module — **data is ready** | 2 days |
| 5 | Email form + double opt-in + unsubscribe | 1 day |
| 6 | Date-change alert engine (free tier — becomes the Pro feature) | 2–3 days |
| 7 | Nav regroup 14 → 5, surface Glossary/Learn/Methodology | half day |
| 8 | Conference miner fix, then publish 41 confs + 9 verified presenters | 1 day |

---

# 7. BOTTOM LINE

The patent cliff is **built, classified and verified** — 427 drugs, 97% with a therapeutic family, from a free authoritative source, with the two defects I introduced found and fixed before delivery. It's ~30 new indexable pages targeting queries we currently rank for nowhere, and it extends the site from "what happens next month" to "what happens over five years."

The email list is the right call, and it's better than it looks: the alert engine behind it is the same engine Pro needs. Build it once, give the basic version away, and the Pro upgrade becomes obvious rather than argued.

One caution: the free-trial claim is still live on `/pricing` while you're about to add an email form to the same page. **Fix that first — it's minutes.**

---
*Verify every date against the FDA Orange Book and primary filings. Not investment advice.*

**Artifacts**
- `patent_cliff_2026_2031_TA.csv` — 427 cliffs with therapeutic family ⭐
- `patent_cliff_ta_map.py` — ATC classifier (frequency-based, multi-candidate lookup)
- `patent_cliff_prototype.py` — Orange Book LOE aggregation
- `_atc_cache.json` — 483 cached ingredient→ATC lookups
