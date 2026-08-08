# Response to AUDIT_2026-07-19 — P0-A closed, deployed & verified live

## 🔴 P0-A — ticker fan-out: FIXED, and it was worse than reported

The audit found 3 wrong companies. **8 bad rows were live.** All removed, deployed, verified.

| Row | Verdict | Evidence |
|---|---|---|
| BNTX 2026-08-17 | ❌ removed | Not a party to the Keytruda+Padcev MIBC sBLA |
| CTMX 2026-08-17 | ❌ removed | Not a party |
| EVAX 2026-08-17 | ❌ removed | Danish AI-vaccine microcap, no bladder-cancer BLA |
| MIRM 2026-09-26 | ❌ removed | zilurgisertib is Incyte's ALK2 programme |
| **ALPMY 2026-08-17** | ❌ removed | **Real** Padcev co-owner — but the FDA **approved this 2026-07-10** |
| **ONC 2026-08-25** | ❌ removed | BeOne Medicines holds zanidatamab **Asia ex-Japan/AU/NZ** only; Jazz is the US applicant |
| **RPRX 2026-09-18** | ❌ removed | Royalty Pharma holds a **royalty**; Nuvalent (NUVL) is the sponsor |
| **RPRX 2026-08-25** | ❌ removed | **Triple corruption** — Royalty Pharma's ticker + **Nuvalent's name** + **Jazz's drug** |

Slate 72 → **64**. Live API verified: all eight gone; 2026-08-25 now shows JAZZ + ZYME only.

### Two failure modes the audit's fingerprint could not catch
1. **The audit's null-mcap signature missed ALPMY.** Astellas is a *genuine* co-owner with a
   resolved market cap — it wasn't a join artifact, it was a **decided-event survivor**.
   `already_decided()` only retires a ticker holding its *own* archive row, so a partner ticker on
   a decided event survives the sweep. My 07-17 sweep removed MRK and PFE and left ALPMY — which
   meant the site briefly showed that decision attributed **only to the three wrong companies**.
2. **Text grouping missed RPRX/2026-08-25.** Its drug string was truncated (`"Ziihera"` vs
   `"Ziihera (zanidatamab-hrii) - (HERIZON-GEA-01)"`), so it grouped separately from the real rows.
   No text-similarity check finds that. A **ticker↔company-name** check does.

### `tests/test_no_ticker_fanout.py` — shipped, 4 checks
- **join-artifact signature** — a null-mcap ticker beside a resolved one on the same (date, drug)
- **indication mismatch** across a shared (date, drug) — the trailing-space tell
- **past-dated multi-ticker event** — catches the ALPMY class (decided events must sweep *every* party)
- **ticker↔name cross-assignment** — catches the RPRX class; ignores benign suffix variants
  ("Gilead Sciences" vs "Gilead Sciences Inc.") and fails only when a ticker carries another
  ticker's canonical name

Verified by re-injecting both original defects: the guard fails the build on each.

### `/corrections` — published
Full public entry naming BNTX/CTMX/EVAX/MIRM, the cause (many-to-many join on drug text, no
sponsor key), the ALPMY sweep gap, and why ONC/RPRX were removed despite being real counterparties.

---

## Also shipped this pass

**22 stale `/pdufa` pages 301'd** — every page whose PDUFA target date had passed while still
rendering as *pending*. Targets verified individually:
- Swept-catalyst pages → their decision page (AZN→06-12, GSK/SPRO→06-17, IONS→06-24, VRDN→06-26,
  CELC→07-14, VERA→07-07, ACHV/ARQT/LNTH/UNCY → their decision pages)
- **REGN otoferlin → REGN-2026-04-23** (DB-OTO approved as Otarmeni, April 2026 — verified)
- **NVO Sogroya → NVO-2026-03-03** (REAL8 pediatric indications approved Feb 2026 — verified)
- **HRMY → /calendar** — no decision exists: FDA issued a **Refusal to File** (Feb 2026), Phase 3
  INTUNE failed, next PDUFA **2028**. A dead catalyst, not an early decision.

Removed from sitemap, page dirs retired. **Ticker hubs rebuilt 210 → 208** (CTMX/EVAX had no real
events at all); orphan hub dirs + sitemap entries cleaned. Sitemap **528 URLs**, well-formed.

**All 5 CI guards pass:** fan-out · fabricated-conferences · crawler-regression · SEO-invariants ·
SI-display-cap.

---

## Freshness sweep (2026-07-19)
- `check_pdufa_decided.py` → **clean**, no forward PDUFA already decided
- Slate `as_of` 2026-07-17, **0 past-dated rows**, price cache current to 07-17
- Next events: MNKD 07-26 · CAPR/OTLK 07-29 · VTRS 07-30 · MRNA 08-05

---

## Still open from AUDIT_2026-07-19 (not done this pass)

| # | Item | Note |
|---|---|---|
| 2 | 🔴 **P0-B** `date_precision:"month"` for the 299 readouts | API claims day precision the page correctly refuses. Needs the API readout serializer. |
| 3 | 🔴 **P0-C** regenerate `/research/conference-runup` from one dataframe | 4 prose figures stale; cap-tier table (1,105) can't be reconciled with `cap_tier_final` (841 + 584 null). Must disclose the nulls. |
| 4 | 🔴 **P0-D** "256 presentations" → 1,425; publish presenter data | Restored 715-row/39-conference crawler output still unpublished; only 2 of 14 conferences show a presenter. Also a `"1 presenters"` pluralisation bug. |
| 5 | 🟠 Homepage `ItemList`/`Event` schema | Highest-authority page emits zero event structured data. |
| 6 | 🟠 `as_of` off-by-one; `/api`→`/developers`; 13 null-drug rows; auto-flip past-dated estimates | I found **13** null-drug rows (audit said 10): MRK, GSK, IONS, CYTK, COGT, ANAB, GILD×2, NVCR, NUVB, IBRX, ARQT, PHVS. Also `NVCR` has a non-ISO date `2026-Q4`. |
| 7 | 🟠 Differentiate `/` from `/calendar` (canonical conflict) | |

**Note on the audit's "recently-decided archive is accurate — AZN/VRDN/IONS 06-30":** those dates
were the *PDUFA goal* dates, not the decisions. Verified real decisions are AZN **06-12**,
VRDN **06-26**, IONS **06-24**; the 06-30 entries were duplicate archive rows and are now 301'd.
