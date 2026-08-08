# pdufa.bio — LAYOUT & UX AUDIT PACKAGE
Generated 2026-06-19. For Gemini / Perplexity. **Focus: layout, information architecture, visual hierarchy, navigation, and UX of BOTH the web dashboard and the mobile app.** Full data arrays are elided (sampled) so you see structure, not 300KB of rows. We are close to public launch — we want sharp, specific layout/UX recommendations.

Ground rules the product must keep (audit for violations too): facts-not-advice (no buy/sell, no position sizing, no per-drug approval probability); cohort base rates are labeled history, not prediction; not affiliated with/endorsed by the FDA.

---

## 0. Design system (shared tokens)
**Web `:root`:** `--navy:#061325;--card:#0c203b;--card2:#0e2547;--line:#1b355a;--gold:#e0b65c;--ink:#f0f5fc;--mut:#a3b8d5;--mut2:#7e95b6;--red:#ff7a7a;--amber:#ffc46b;--blue:#6fb6ff;--green:#5fd07a;--purp:#b9a3ff`
**App `:root`:** `--bg:#050f1f;--card:#0c1d38;--card2:#0f2547;--line:#1a3358;--gold:#e3ba5e;--ink:#f2f6fc;--mut:#a7bcd9;--mut2:#7890b3;--red:#ff7a7a;--amber:#ffc46b;--blue:#6fb6ff;--green:#5fd07a;--purp:#b9a3ff`
Type: system UI stack. Web is a responsive CSS grid of cards (desktop + mobile web). App is a fixed ≤440px mobile shell with a sticky bottom tab bar. Dark navy theme, gold (#e3ba5e) accent, green/red for up/down + approve/CRL.

---

## 1. WEB DASHBOARD — information architecture
Single AES-gated page (`/today.html`). Two top-level views toggled by chips: **Today** and **Historic decisions**.

**Global chrome (top, sticky):** brand `pdufa.bio` + "FACTS, NOT ADVICE" tag + freshness ("LIVE · …"). Below it: a **filter bar**.
- Today filters: View toggle (Today / Historic) · **Status** (All / Pending / Decided) · **Window** (T-) · **Size** (cap tier) · **Options only** · **High relative premium** · **Runway <12mo** · **Watchlist ★** · text search.
- Historic filters: Outcome · Size · ticker search · a persistent **experimental banner**.

**Today view = month-grouped feed.** Catalysts sorted chronologically with **month headers** (June 2026, July 2026 …). Each catalyst is a compact **3-line "tape" card** (anatomy below). Decided names (e.g. SPRO/GSK Approved) appear in their month with a decision-day move.

**Historic view = year/outcome archive.** Cards for 2024–present approvals & CRLs, each with a T-120 chart + validation badge; tap → detail sheet.

### 1a. Today "tape" card anatomy (the core component)
Row layout: `[T-minus pill] | meta block | facts strip`.
- **T-minus pill** (left, fixed width): big number + "days"/"today"/"done"; colored by urgency (≤7 red, ≤21 amber, ≤45 blue) or outcome (green ✓ / red ✗).
- **Line 1:** ticker · cap-tier chip · today's % move · decided badge (✓ Approved / ✗ CRL / "Date passed — outcome unknown") · ★ watchlist.
- **Line 2:** date-confidence dot (green High / amber Medium) · **date-type pill** ("PDUFA (FDA)" / "(company-guided)" / "(registry est.)") · date · T- · **"Sourced: …" pill** (provenance).
- **Line 3 (drug):** drug — indication (truncated). Risk icons row: CASH <6mo / 6-12mo, IV CRUSH, REG SLIP.
- **Facts strip (full-width footer of card):** Price · Market cap · Cash runway · LOA (cohort, with ⓘ).
- **Options one-liner (if liquid):** ±implied% vs ±cohort-hist% · **Vol rich/low vs cohort ×** · C/P skew.
- **Registry line:** ✓ CT.gov · status · primary-completion (type) · ⚠ if date changed (Silent Shift).
- *Note: the T-120 sparkline was moved OFF the card into the detail sheet (audit 5.1); decision-day move is de-emphasized.*

### 1b. Today detail sheet (tap a card → bottom overlay)
Header (ticker, cap, decided badge, date-type pill, date, T-, confidence). Body: **T-120 run-up chart** (swing highs green / lows red) → Drug → **Facts** (price/cap/runway/LOA) → **Options (ORATS)** (implied move, cohort hist, premium-vs-cohort, ATM IV, expiry/DTE, call wall, C/P) → **Registry** (NCT link, status, PCD, slip note) → **Prior FDA history for TICKER** (clickable list of this ticker's past decisions → opens historic sheet) → **Base-rate context** (cohort paragraph, "not probabilities for this drug") → **source + not-advice footer** ("Sourced from: …").

### 1c. Historic detail sheet
Header (ticker, size, year, outcome badge). Body: data-note/correction (if mislabel) → validation note → **↗ View primary source** link → T-120 chart → decision-day move + run-up → **CRL reason** (category chip + text) → **CRL → next-decision recovery** (mini-timeline "● CRL date (reason) → trough $ → outcome date" + recovery chart + run-up stats) → not-advice footer.

---

## 2. MOBILE APP — information architecture
`/app.html`, AES-gated, installable PWA (manifest + icons + service worker; "Remember me" auto-unlock). Fixed ≤440px shell, **sticky bottom tab bar (5 tabs): Radar · Calendar · Watchlist · History · More.** Tap any row → a **bottom sheet** (slides up, dim overlay). First-visit facts-not-advice modal.

**Header (sticky):** brand + freshness + "FACTS, NOT ADVICE" tag; on Radar only: greeting + **search**.

### 2a. Radar (home / first screen after login)
Vertical sections of tap-rows:
1. **Decisions — today & just in** (decided/T-0, highlighted hero cards).
2. **High visibility** (near-term + high IV: IV≥120% & T≤3) — new grouping.
3. **This week (T-7).**
4. **Next 30 days.**
Empty states per section ("Nothing in the next 7 days.").

### 2b. Radar row anatomy
`[T-minus pill] | ticker · cap · today% | drug · indication | chips`.
- Chips are **capped at 3 + "+N more"**, priority: Approved/CRL → Vol rich/low → CASH <6mo → IV CRUSH → REG SLIP → ±exp move.

### 2c. Calendar tab
Full slate, **month-grouped** (Jun 2026 …), same rows.

### 2d. Watchlist tab
★-saved names (localStorage), month-sorted; empty state prompts tapping ★.

### 2e. History tab (NEW)
Experimental banner → **year-grouped** list of 2024–present decisions. Each row: ✓/✗ outcome pill, ticker, size, decision-day %, **validation badge** (✓ verified / ~ probable / ⚠ unverified/mislabel). Tap → sheet with chart, decision-day move, run-up, CRL reason, **↗ primary source link**, recovery timeline.

### 2f. App detail sheet (catalyst)
Grab handle → header (ticker, cap, decided badge, ★) → name → date-type pill + date + T- + confidence → **"Sourced: …"** → body: T-120 chart → Drug → Facts (price/cap/runway) → Options (ORATS) → Registry → **collapsible "Base-rate context (LOA & hist. move) ›"** (LOA + cohort hist + cohort paragraph hidden until tapped, audit 1.2) → source + not-advice footer.

### 2g. More tab
Methodology (incl. Vol rich/low + IV-crush explanation) + full legal/non-affiliation.

---

## 3. Recent changes already shipped (so you don't re-flag them)
3-line tape cards; month grouping; Status filter; "High relative premium" rename; Vol rich/low-vs-cohort wording; date taxonomy (FDA/company-guided/registry-est) + confidence dot; per-card "Sourced:" pills + structured source taxonomy; pending "Date passed — outcome unknown" badge; chart moved to detail; first-visit + historic experimental modals; cohort medians aligned to cap tiers (694 PDUFAs); CRL validation badges + **16 source-verified / 17 mislabel / 20 primary-source links**; app **High-visibility** group; **3-chip cap**; collapsible base-rate; **History tab**; **prior-FDA-history** block + recovery **mini-timeline**; installable **PWA** + **remember-me** gate.

---

## 4. WEB DASHBOARD — full front-end (data elided)
```html

<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>pdufa.bio — Today</title>
<style>
*{box-sizing:border-box}
:root{--navy:#061325;--card:#0c203b;--card2:#0e2547;--line:#1b355a;--gold:#e0b65c;--ink:#f0f5fc;--mut:#a3b8d5;--mut2:#7e95b6;--red:#ff7a7a;--amber:#ffc46b;--blue:#6fb6ff;--green:#5fd07a;--purp:#b9a3ff}
html,body{margin:0;background:var(--navy);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;-webkit-font-smoothing:antialiased}
.wrap{max-width:1180px;margin:0 auto;padding:0 16px}
header{border-bottom:1px solid var(--line);background:linear-gradient(180deg,#081a33,#061325);position:sticky;top:0;z-index:20}
.top{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:13px 16px;max-width:1180px;margin:0 auto;flex-wrap:wrap}
.brand{display:flex;align-items:baseline;gap:10px}.brand .logo{font-size:22px;font-weight:800;letter-spacing:-.5px}.brand .logo b{color:var(--gold)}.brand .tag{font-size:11.5px;color:var(--gold);font-weight:700;letter-spacing:.4px}
.fresh{font-size:11.5px;color:var(--mut);text-align:right}.fresh b{color:var(--green)}.fresh a{color:var(--blue);text-decoration:none}
.filters{display:flex;gap:7px;flex-wrap:wrap;align-items:center;padding:9px 16px;max-width:1180px;margin:0 auto;border-top:1px solid #102744}
.chip{font-size:12px;padding:6px 11px;border:1px solid var(--line);border-radius:999px;background:#0a1c34;color:var(--mut);cursor:pointer;user-select:none;white-space:nowrap}
.chip.on{background:var(--gold);color:#061325;border-color:var(--gold);font-weight:700}.chip.tog.on{background:#15406b;color:#cfe4ff;border-color:#2f6aa6}
.chip.lbl{border:0;background:transparent;color:var(--mut2);cursor:default;padding-left:2px;font-weight:700;text-transform:uppercase;font-size:10px;letter-spacing:.5px}
.search{margin-left:auto;flex:1;min-width:110px;max-width:210px;padding:7px 11px;border-radius:9px;border:1px solid var(--line);background:#0a1c34;color:#fff;font-size:13px}
main{padding:16px 0 60px}.count{font-size:12px;color:var(--mut);margin:2px 2px 12px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:13px}@media(max-width:780px){.grid{grid-template-columns:1fr}}
.card{border:1px solid var(--line);border-radius:13px;background:var(--card);overflow:hidden;display:flex;flex-direction:column;box-shadow:0 3px 10px rgba(0,0,0,.28);cursor:pointer;transition:border-color .12s}
.card:hover{border-color:#2f5687}
.hd{display:flex;gap:11px;padding:12px 13px 8px;align-items:flex-start}
.tm{flex:0 0 auto;width:62px;text-align:center;border-radius:10px;padding:7px 4px;background:#081a33;border:1px solid var(--line)}
.tm .n{font-size:21px;font-weight:800;line-height:1}.tm .u{font-size:9px;color:var(--mut);text-transform:uppercase;letter-spacing:.4px;margin-top:2px}
.tm.red{border-color:var(--red)}.tm.red .n{color:var(--red)}.tm.amber{border-color:var(--amber)}.tm.amber .n{color:var(--amber)}.tm.blue{border-color:var(--blue)}.tm.blue .n{color:var(--blue)}.tm.grey .n{color:var(--mut)}
.hmeta{flex:1;min-width:0}.r1{display:flex;align-items:center;gap:7px;flex-wrap:wrap}
.tk{font-size:18px;font-weight:800}.cap{font-size:9px;font-weight:700;color:var(--gold);border:1px solid #46618a;border-radius:5px;padding:1px 5px;text-transform:uppercase}
.chgp{font-size:12.5px;font-weight:700}.chgp.up{color:var(--green)}.chgp.dn{color:var(--red)}
.star{margin-left:auto;font-size:16px;color:var(--mut2);cursor:pointer;line-height:1;padding:0 2px}.star.on{color:var(--gold)}
.ricons{display:flex;gap:4px;margin-left:6px}
.ic{font-size:9px;font-weight:700;text-transform:uppercase;padding:2px 6px;border-radius:5px;letter-spacing:.2px}
.ic.dilC{background:#3a1010;color:#ff8a8a;border:1px solid #6e2020}.ic.dilE{background:#34230e;color:#ffc46b;border:1px solid #5f3f18}.ic.crush{background:#2c1230;color:#e6a3ff;border:1px solid #51265a}
.r2{display:flex;align-items:center;gap:6px;margin-top:5px;flex-wrap:wrap;font-size:11.5px;color:var(--mut)}.r2 b{color:var(--ink)}
.dpill{font-size:9px;font-weight:700;text-transform:uppercase;background:#10325a;color:#9ecbff;border:1px solid #29507e;border-radius:5px;padding:1px 6px}
.co{font-size:11px;color:var(--mut2);margin-top:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.drug{padding:2px 13px 8px}.drug .d{font-size:13px;font-weight:600}.drug .i{font-size:11.5px;color:var(--mut);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.facts{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:var(--line);border-top:1px solid var(--line);border-bottom:1px solid var(--line)}
.f{background:var(--card);padding:7px 9px}.f .k{font-size:9px;color:var(--mut2);text-transform:uppercase;letter-spacing:.3px;font-weight:400}
.f .v{font-size:14px;font-weight:800;margin-top:2px;color:var(--ink)}.f .v.cri{color:var(--red)}.f .v.ele{color:var(--amber)}.f .v.loa{color:var(--mut);font-weight:700}
.ii{cursor:help;color:var(--mut2);font-size:8.5px;border:1px solid var(--mut2);border-radius:50%;padding:0 3px;margin-left:3px}
.brow{display:flex;align-items:center;gap:7px;padding:6px 13px;border-bottom:1px solid var(--line);background:#091d36;flex-wrap:wrap}
.bbadge{font-size:9.5px;color:var(--mut);border:1px solid var(--line);border-radius:5px;padding:2px 7px;cursor:help}
.sig{font-size:11.5px;color:var(--mut);margin-left:auto}.sig b{color:var(--ink)}
.volb{font-size:9.5px;font-weight:700;padding:2px 7px;border-radius:5px;text-transform:uppercase}
.volb.rich{background:#34230e;color:#ffce85;border:1px solid #5f3f18}.volb.cheap{background:#0e2c4a;color:#8fc6ff;border:1px solid #245078}.volb.fair{background:#14253f;color:var(--mut);border:1px solid var(--line)}
.opt{padding:8px 13px;background:var(--card2)}
.orow{display:flex;align-items:center;gap:12px}
.em{font-size:19px;font-weight:800;color:var(--gold);line-height:1}.emk{font-size:8.5px;color:var(--mut2);text-transform:uppercase}
.osub{font-size:11px;color:var(--mut);display:flex;flex-direction:column;gap:1px}.osub b{color:var(--ink)}
.bar{position:relative;height:6px;background:#0a1c34;border:1px solid var(--line);border-radius:4px;margin-top:8px}
.bar .fill{position:absolute;left:0;top:0;bottom:0;background:linear-gradient(90deg,#7a5f24,var(--gold));border-radius:3px}.bar .tick{position:absolute;top:-3px;bottom:-3px;width:2px;background:var(--ink)}
.barlbl{display:flex;justify-content:space-between;font-size:9px;color:var(--mut2);margin-top:3px}
.vbadge{font-size:8.5px;font-weight:700;padding:1px 5px;border-radius:4px;margin-left:5px}.vbadge.ok{background:#0e3320;color:#7ee2a0;border:1px solid #1f6e42}.vbadge.warn{background:#34230e;color:#ffc46b;border:1px solid #5f3f18}.card.decided{opacity:.6}.dec{font-size:9px;font-weight:800;text-transform:uppercase;padding:2px 7px;border-radius:5px}.dec.app{background:#0e3320;color:#7ee2a0;border:1px solid #1f6e42}.dec.crl{background:#3a1010;color:#ff8a8a;border:1px solid #6e2020}.dec.pen{background:#14253f;color:var(--mut);border:1px solid var(--line)}
.slip{padding:7px 13px;background:#3a1410;border-bottom:1px solid #6e2a1a;color:#ffb09b;font-size:11px;font-weight:600;display:flex;gap:6px;align-items:flex-start}.regln{padding:6px 13px;font-size:10.5px;color:var(--mut2);border-top:1px solid var(--line);display:flex;gap:5px;flex-wrap:wrap;align-items:center}.regln .rv{color:var(--green);font-weight:700}.regln b{color:var(--mut)}.regln a{color:var(--blue);text-decoration:none}
.mhead{grid-column:1/-1;font-size:13px;font-weight:800;color:var(--gold);padding:16px 4px 4px;border-bottom:1px solid var(--line);margin-top:6px;letter-spacing:.3px}.cchart{padding:7px 11px 9px;border-top:1px solid var(--line)}​.tlx{font-size:11px;color:var(--mut);background:#0c1d38;border:1px solid var(--line);border-radius:8px;padding:7px 10px;margin:6px 0}.vb{font-size:8.5px;font-weight:700;padding:1px 5px;border-radius:5px;margin-left:4px}.vb.ver{background:#0c2417;color:#7ee2a0;border:1px solid #1f6e42}.vb.mis{background:#3a1010;color:#ff9b9b;border:1px solid #6e2020}.vb.prob{background:#14253f;color:#9fb0c8;border:1px solid #1b355a}.vb.warn{background:#241a0d;color:#ffc46b;border:1px solid #5f3f18}.vb.imm{background:#13243f;color:#7890b3;border:1px solid #1a3358}.srcp{font-size:9px;color:var(--mut2);border:1px solid var(--line);border-radius:4px;padding:0 4px;white-space:nowrap}.ddm{font-size:10px;margin-top:3px;color:var(--mut2)}.ddm b{font-weight:800}
.tline{padding:5px 13px;font-size:11.5px;color:var(--mut);border-top:1px solid var(--line);display:flex;flex-wrap:wrap;gap:5px;align-items:center}.tline.reg{color:var(--mut2);font-size:10.5px}.tline .rv{color:var(--green);font-weight:700}.oem{color:var(--gold);font-weight:800;font-size:13px}.omut{color:var(--mut2)}.tfacts{display:flex;border-top:1px solid var(--line);font-size:12px}.tfacts span{flex:1;padding:6px 9px;border-right:1px solid var(--line);color:var(--ink);font-weight:700;text-align:center}.tfacts span:last-child{border-right:0}.tfacts span.cri{color:var(--red)}.tfacts span.ele{color:var(--amber)}.tfacts .ii{font-weight:400;cursor:help}.cdot{width:7px;height:7px;border-radius:50%;display:inline-block;vertical-align:middle}.drug1{font-size:11.5px;color:var(--ink);margin-top:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.ricons{margin-top:5px;display:flex;gap:4px;flex-wrap:wrap}
footer{border-top:1px solid var(--line);padding:22px 16px 40px;color:var(--mut2);font-size:11px;line-height:1.6;max-width:1180px;margin:0 auto}footer b{color:var(--mut)}
.disc{margin-top:10px;padding:10px 12px;border:1px solid var(--line);border-radius:9px;background:#0a1c34;color:var(--mut)}
#ov{display:none;position:fixed;inset:0;background:rgba(2,8,18,.72);z-index:50;align-items:flex-end;justify-content:center}
@media(min-width:680px){#ov{align-items:center}}
#sheet{background:var(--card);border:1px solid var(--line);border-radius:16px 16px 0 0;max-width:560px;width:100%;max-height:88vh;overflow:auto;padding:0}
@media(min-width:680px){#sheet{border-radius:16px}}
.sh{padding:16px 18px;border-bottom:1px solid var(--line);position:sticky;top:0;background:var(--card)}
.sh .x{float:right;font-size:20px;color:var(--mut);cursor:pointer;line-height:1}
.sb{padding:14px 18px}.sb h4{margin:14px 0 6px;font-size:11px;color:var(--gold);text-transform:uppercase;letter-spacing:.5px}
.sb .kv{display:flex;justify-content:space-between;font-size:13px;padding:4px 0;border-bottom:1px solid #112b48}.sb .kv span{color:var(--mut)}.sb .kv b{color:var(--ink)}
.sb p{font-size:12px;color:var(--mut);line-height:1.5}
.sb a{color:var(--blue);text-decoration:none;font-size:12px}
@media(max-width:780px){.co{display:none}}
</style></head>
<body>
<header><div class="top">
 <div class="brand"><div class="logo">pdufa<b>.bio</b></div><div class="tag">FACTS, NOT ADVICE</div></div>
 <div class="fresh">Catalyst data as of <b id="asof"></b> · <a href="#m">Methodology</a><br>Live <b id="optfresh">ORATS + FMP · snapshot</b> · auto-refresh ~5×/day</div></div>
 <div class="filters">
   <span class="chip vchip on" data-view="today">Today</span><span class="chip vchip" data-view="historic">Historic decisions</span><span style="width:8px"></span><span class="chip lbl">Status</span><span class="chip st on" data-st="all">All</span><span class="chip st" data-st="pending">Pending</span><span class="chip st" data-st="decided">Decided</span><span class="chip lbl">Window</span><span class="chip" data-w="14">&le;2wk</span><span class="chip" data-w="30">&le;30d</span><span class="chip on" data-w="90">&le;90d</span><span class="chip" data-w="999">All</span>
   <span class="chip lbl">Size</span><span class="chip on" data-c="all">All</span><span class="chip" data-c="Micro">Micro</span><span class="chip" data-c="Small">Small</span><span class="chip" data-c="Mid">Mid</span><span class="chip" data-c="Large">Large</span>
   <span class="chip tog" data-t="wl">★ Watchlist</span><span class="chip tog" data-t="opt">Options only</span><span class="chip tog" data-t="vol" title="Shows events where options implied move is significantly larger than the median move for similar market-cap cohorts. High relative premium does not predict direction and is not a recommendation to buy or sell volatility.">High relative premium</span><span class="chip tog" data-t="run">Runway &lt;12mo</span>
   <input class="search" id="q" placeholder="Search…"></div>
</header>
<div class="filters" id="histf" style="display:none"><span class="chip lbl">Outcome</span><span class="chip hoc on" data-oc="all">All</span><span class="chip hoc" data-oc="Approved">Approved</span><span class="chip hoc" data-oc="CRL">CRL</span><span class="chip lbl">Year</span><span class="chip hyr on" data-yr="all">All</span><span class="chip hyr" data-yr="2026">2026</span><span class="chip hyr" data-yr="2025">2025</span><span class="chip hyr" data-yr="2024">2024</span><span class="chip lbl">Size</span><span class="chip hsz on" data-sz="all">All</span><span class="chip hsz" data-sz="Micro">Micro</span><span class="chip hsz" data-sz="Small">Small</span><span class="chip hsz" data-sz="Mid">Mid</span><span class="chip hsz" data-sz="Large">Large</span><input class="search" id="hq" placeholder="Search ticker…"></div><div id="ack" style="display:none;position:fixed;inset:0;background:rgba(2,8,18,.86);z-index:80;align-items:center;justify-content:center;padding:18px"><div style="max-width:460px;background:var(--card);border:1px solid var(--gold);border-radius:14px;padding:22px"><div style="color:var(--gold);font-weight:800;letter-spacing:.4px;font-size:13px">PDUFA.BIO \u2014 FACTS, NOT ADVICE</div><p style="font-size:13px;color:var(--ink);line-height:1.55;margin:10px 0">pdufa.bio provides data and historical statistics. It is <b>not investment advice</b>, does not recommend trades, and does not estimate individual-drug approval probabilities. It is <b>not affiliated with or endorsed by the FDA</b>. By continuing you agree to verify all dates and outcomes against primary sources \u2014 dates can slip and historical labels are still being validated.</p><button onclick="ackOk()" style="width:100%;padding:11px;border:0;border-radius:9px;background:var(--gold);color:#061325;font-weight:700;font-size:15px;cursor:pointer">I understand \u2014 show me the facts</button></div></div><div id="ackh" style="display:none;position:fixed;inset:0;background:rgba(2,8,18,.86);z-index:80;align-items:center;justify-content:center;padding:18px"><div style="max-width:460px;background:var(--card);border:1px solid var(--gold);border-radius:14px;padding:22px"><div style="color:var(--gold);font-weight:800;font-size:13px">HISTORIC DECISIONS \u2014 EXPERIMENTAL</div><p style="font-size:13px;color:var(--ink);line-height:1.55;margin:10px 0">Historic decisions are for research and education. Outcome and CRL labels are still being validated. Always cross-check company filings before making trading decisions.</p><button onclick="ackOkH()" style="width:100%;padding:11px;border:0;border-radius:9px;background:var(--gold);color:#061325;font-weight:700;font-size:15px;cursor:pointer">I understand</button></div></div><main class="wrap"><div class="count" id="count"></div><div class="grid" id="list"></div></main>
<div id="ov"><div id="sheet"></div></div>
<footer><b id="m">What you're looking at.</b> Every upcoming FDA decision (PDUFA) with the facts to weigh it — price &amp; today's move, market cap, cash runway &amp; dilution tier, the drug in plain English, and the current options market (expected move, IV, OI skew) vs the cohort base rate. Sorted by time-to-decision; tap any card for full detail &amp; sources. <b>Methodology:</b> options via ORATS (ATM straddle → expected move); price via FMP; "Hist. move/LOA" are cohort base rates (694-PDUFA study, 2024–26), describing history — not this drug. Dilution: red &lt;6mo cash, amber 6–12mo (small/mid). "VOL RICH ×" = implied move ÷ cohort median; context, <b>not a recommendation</b>.
<div class="disc"><b>Not affiliated with or endorsed by the FDA.</b> pdufa.bio is an independent service, not affiliated with, endorsed by, or officially connected to the U.S. Food and Drug Administration, HHS, or any government agency. &ldquo;FDA,&rdquo; &ldquo;PDUFA,&rdquo; and all company, drug &amp; ticker names are used descriptively and remain the property of their respective owners.<br><br><b>Informational / educational only — not investment advice.</b> We never tell anyone to buy or sell and never invent an approval probability. Verify every date against the primary FDA/company filing — dates can slip.</div></footer>
<script>
const DATA=/* «16431 chars elided — sample: {"as_of":"2026-06-17","catalysts":[{"ticker":"GSK","name":"GSK plc American Depositary Shares (Each representing two)","date":"2026-06-18","t_minus":1,"drug":"Tebipenem HBr (SPR994) - (PIVOT-PO)","indication":"Complicated urinary tract infection (cUTI), including acute pyelonephritis (AP)","price":52.11,"mcap":104036582163.0,"cap":"Large","adv":3953624.0,"cash_months":15.82,"loa":87.58,"pop":87.58 …» */ {}; const HIST=/* «39 chars elided — sample: {"Micro":7,"Small":3,"Mid":2,"Large":1} …» */ {};
const CH=/* «19945 chars elided — sample: {"GSK":{"c":[61.18,60.85,59.52,59.26,59.12,59.54,58.07,59.13,58.29,57.07,56.83,55.27,54.51,55.51,55.32,55.15,54.28,53.39,53.77,53.41,52.06,52.37,51.84,51.99,52.95,54.7,53.94,53.84,54.23,55.19,55.99,56.69,56.37,55.84,57.37,58.36,58.21,58.94,59.18,57.81,57.13,58.35,57.35,56.12,55.7,55.63,54.44,54.22,54.47,51.4,52.31,51.61,50.9,50.38,50.53,50.5,50.41,49.81,50.9,50.99,50.96,49.67,50.26,51.05,50.78,51. …» */ {}; let VIEW='today'; const HISTORIC=/* «219773 chars elided — sample: [{"t":"ASND","date":"2026-02-28","yr":2026,"outcome":"Approved","dmove":3.7,"lo":196.01,"hi":242.09,"runup":19.0,"ta":null,"c":[203.23,208.24,199.22,209.55,210.85,196.63,202.82,208.98,209.29,217.32,235.39,223.59,224.19,230.21,233.5,239.22],"piv":[0,15],"sz":"Large"},{"t":"ETON","date":"2026-02-25","yr":2026,"outcome":"Approved","dmove":-3.4,"lo":14.35,"hi":19.25,"runup":4.0,"ta":null,"c":[18.46,17 …» */ {}; let HF={oc:'all',yr:'all',sz:'all'};
document.getElementById('asof').textContent=DATA.as_of;
let W=90,C='all',Q='',ST='all',T={wl:false,opt:false,vol:false,run:false};
let WL=[]; try{WL=JSON.parse(localStorage.getItem('pb_watch')||'[]')}catch(e){WL=[]}
const fmtB=v=>v==null?'—':(v>=1e9?'$'+(v/1e9).toFixed(1)+'B':v>=1e6?'$'+(v/1e6).toFixed(0)+'M':'$'+v.toFixed(0));
const shortCo=s=>(s||'').replace(/,? (Inc|Inc\.|Incorporated|Corporation|Corp|Corp\.|Ltd|Ltd\.|Limited|Holdings|Therapeutics|Pharmaceuticals|Pharma|Plc|PLC|A\/S|S\.A\.|N\.V\.)\.?$/,'').slice(0,32);
const BR={Micro:'Historically modest pre-run-up (~55% rose); decision day still a coin-flip even on approvals (694-PDUFA cohort, 2024–26). Not a recommendation.',Small:'Historically modest pre-run-up (~55% rose); decision day still a coin-flip even on approvals (694-PDUFA cohort, 2024–26). Not a recommendation.',Mid:'~+6% typical run-up; smaller decision-day moves (694-PDUFA cohort, 2024–26). Not a recommendation.',Large:'Efficient — little run-up and small decision-day moves (694-PDUFA cohort, 2024–26). Not a recommendation.'};
const LOAT='Cohort-level historical likelihood of approval (694-PDUFA study, 2024–26). NOT a modelled probability for this specific drug.';

function chartSVG(o,Hh){if(!o||!o.c||o.c.length<3)return '';Hh=Hh||132;const c=o.c,n=c.length,W=480,pad=10;const lo=Math.min.apply(null,c),hi=Math.max.apply(null,c),rng=(hi-lo)||1;const X=i=>pad+i/(n-1)*(W-2*pad),Y=v=>pad+(1-(v-lo)/rng)*(Hh-2*pad);let pts=c.map((v,i)=>X(i).toFixed(1)+','+Y(v).toFixed(1)).join(' ');let dots='';(o.piv||[]).forEach(i=>{const v=c[i];const isHi=(i===0?(c[1]!=null&&v>c[1]):i===n-1?(v>c[n-2]):(v>=c[i-1]&&v>=c[i+1]));dots+='<circle cx="'+X(i).toFixed(1)+'" cy="'+Y(v).toFixed(1)+'" r="2.6" fill="'+(isHi?'#5fd07a':'#ff7a7a')+'"/>';});const hiI=c.indexOf(hi),loI=c.indexOf(lo);let lbl='<text x="'+Math.min(W-30,Math.max(20,X(hiI))).toFixed(1)+'" y="'+(Y(hi)-4).toFixed(1)+'" fill="#5fd07a" font-size="9" text-anchor="middle">$'+hi+'</text><text x="'+Math.min(W-30,Math.max(20,X(loI))).toFixed(1)+'" y="'+(Y(lo)+11).toFixed(1)+'" fill="#ff7a7a" font-size="9" text-anchor="middle">$'+lo+'</text>';return '<svg viewBox="0 0 '+W+' '+Hh+'" style="width:100%;height:auto;background:#081a33;border:1px solid var(--line);border-radius:8px"><polyline points="'+pts+'" fill="none" stroke="#e0b65c" stroke-width="1.4"/><line x1="'+(W-pad)+'" y1="'+pad+'" x2="'+(W-pad)+'" y2="'+(Hh-pad)+'" stroke="#6fb6ff" stroke-dasharray="2 2"/>'+dots+lbl+'</svg>';}
function chartBlock(o,decision){if(!o)return '';return '<h4>Run-up — T-120 price path</h4>'+chartSVG(o)+'<p style="font-size:10.5px;color:var(--mut2)">● Green = local high · ● red = local low / sell-off · blue dashed = '+(decision||'decision')+'. Range $'+Math.min.apply(null,o.c)+'–$'+Math.max.apply(null,o.c)+'.</p>';}
function tmClass(d){return d<=7?'red':d<=21?'amber':d<=45?'blue':'grey'}
function band(p){return p==null?'all':p<10?'micro':p<40?'small':'large'}
function volClass(r){return r>=2?'rich':r<=1?'cheap':'fair'}
function isWL(t){return WL.indexOf(t)>=0}
function toggleWL(t,ev){ev.stopPropagation();const i=WL.indexOf(t);if(i>=0)WL.splice(i,1);else WL.push(t);try{localStorage.setItem('pb_watch',JSON.stringify(WL))}catch(e){};render()}
function closeDetail(ev){if(ev)ev.stopPropagation();document.getElementById('ov').style.display='none';}
function openDetail(idx){var c=DATA.catalysts[idx];var o=(c.opt&&c.opt.em_pct!=null)?c.opt:null;var h=HIST[c.cap];var cd=CH[c.ticker];var dec=c.decided,oc=c.outcome;var ddm=(dec&&cd&&cd.c&&cd.c.length>1)?((cd.c[cd.c.length-1]/cd.c[cd.c.length-2]-1)*100):null;
var decB=dec?'<span class="dec '+(oc==='Approved'?'app':oc==='CRL'?'crl':'pen')+'">'+(oc==='Approved'?'✓ Approved':oc==='CRL'?'✗ CRL':'Date passed — outcome unknown')+'</span>':'';
var vl='';if(o&&h){var r=o.em_pct/h,vc=volClass(r);vl='<div class="kv"><span>Premium vs cohort</span><b>'+(vc==='rich'?'Vol rich vs cohort '+r.toFixed(1)+'×':vc==='cheap'?'Vol low vs cohort '+r.toFixed(1)+'×':'Vol ~ cohort')+'</b></div>';}
var opth=o?('<h4>Options (ORATS)</h4><div class="kv"><span>Implied move</span><b>±'+o.em_pct+'%</b></div><div class="kv"><span>Cohort hist. move</span><b>±'+(h!=null?h:'?')+'%</b></div>'+vl+'<div class="kv"><span>ATM IV</span><b>'+(o.atm_iv_pct!=null?o.atm_iv_pct+'%':'—')+'</b></div><div class="kv"><span>Expiry · DTE</span><b>'+o.exp+' · '+o.dte+'d</b></div><div class="kv"><span>Call wall · C/P OI</span><b>$'+o.call_wall+' · '+(o.cp_oi!=null?o.cp_oi+'×':'—')+'</b></div>'):'<h4>Options</h4><p style="font-size:12px;color:var(--mut)">No liquid options snapshot.</p>';
var rg=c.reg;var reg="";if(rg){reg='<h4>Registry — ClinicalTrials.gov</h4><div class="kv"><span>Trial</span><b><a href="https://clinicaltrials.gov/study/'+rg.nct+'" target="_blank" style="color:#6fb6ff">'+rg.nct+'</a></b></div><div class="kv"><span>Status</span><b>'+rg.status+'</b></div><div class="kv"><span>Primary completion</span><b>'+(rg.pcd||"—")+' ('+(rg.pcd_type||"")+')</b></div>';if(rg.slip)reg+='<p style="color:#ffc46b;font-size:11px">⚠ Primary-completion date changed '+rg.slip.from+'→'+rg.slip.to+' ('+(rg.slip.days>=0?"+":"")+rg.slip.days+'d). Our detection, not an FDA signal — verify with filings.</p>';}
var base=(c.cap==='Micro'||c.cap==='Small')?'Small/micro names historically had a modest pre-run-up; the decision day is roughly a coin-flip even on approvals (694-PDUFA cohort).':c.cap==='Mid'?'Mid-caps historically ran ~+6% with smaller decision-day moves.':'Large-caps are efficient — little run-up, near-zero decision-day move.';
var src=(c.source&&c.source.detail)||'company/FDA filing';var phl=HISTORIC.map(function(e,ii){return[e,ii];}).filter(function(x){return x[0].t===c.ticker;});var ph=phl.length?('<h4>Prior FDA history for '+c.ticker+'</h4>'+phl.map(function(x){var e=x[0];return '<div class="kv"><span><a href="#" onclick="openHist('+x[1]+');return false;" style="color:#6fb6ff;text-decoration:none">'+(e.outcome==="Approved"?"\u2713 ":"\u2717 ")+e.outcome+' \u00b7 '+e.date+'</a></span><b>'+(e.dmove>=0?'+':'')+e.dmove+'%</b></div>';}).join('')):'';document.getElementById('sheet').innerHTML='<div class="sh"><span class="x" onclick="closeDetail(event)">✕</span><div style="font-size:20px;font-weight:800">'+c.ticker+' <span class="cap">'+c.cap+'</span> '+decB+'</div><div style="font-size:12px;color:var(--mut)">'+c.name+'</div><div style="font-size:12.5px;margin-top:4px"><span class="dpill" title="'+(c.date_note||'')+'">'+(c.date_type||'PDUFA')+'</span> <b>'+c.date+'</b> · T-'+(c.t_minus<=0?'0':c.t_minus)+' · <span style="color:'+(c.date_conf==='Medium'?'#ffc46b':'#5fd07a')+'">'+(c.date_conf||'High')+' confidence</span></div></div><div class="sb">'+(cd?'<h4>Run-up — T-120</h4>'+chartSVG(cd)+'<p style="font-size:10.5px;color:var(--mut2)">● green = local high · ● red = low/sell-off'+(dec&&ddm!=null?' · decision-day move <b style="color:'+(ddm>=0?'#5fd07a':'#ff7a7a')+'">'+(ddm>=0?'+':'')+ddm.toFixed(1)+'%</b>':'')+'</p>':'')+'<h4>Drug</h4><div style="font-size:13px;font-weight:600">'+(c.drug||'')+'</div><div style="font-size:12.5px;color:var(--mut)">'+(c.indication||'')+'</div><h4>Facts</h4><div class="kv"><span>Price'+(c.chg!=null?' (today)':'')+'</span><b>'+(c.price!=null?'$'+c.price.toFixed(2):'—')+(c.chg!=null?' ('+(c.chg>=0?'+':'')+c.chg.toFixed(1)+'%)':'')+'</b></div><div class="kv"><span>Market cap</span><b>'+fmtB(c.mcap)+'</b></div><div class="kv"><span>Cash runway</span><b>'+(c.cash_months!=null?c.cash_months.toFixed(0)+' mo':'—')+'</b></div><div class="kv"><span>Hist. LOA (cohort)</span><b>'+(c.loa!=null?c.loa.toFixed(0)+'%':'—')+'</b></div>'+opth+reg+'<h4>Base-rate context (not a recommendation)</h4><p style="font-size:12px;color:var(--mut)">'+base+' These are historical cohort base rates by market-cap tier (694 PDUFAs, 2024–26), not probabilities for this specific drug.</p>'+ph+'<p style="font-size:10.5px;color:var(--mut2);margin-top:10px;border-top:1px solid var(--line);padding-top:8px">Sourced from: '+src+'. pdufa.bio provides data and historical statistics. It is not investment advice and does not recommend trades or estimate individual-drug approval probabilities. Not affiliated with or endorsed by the FDA. Verify against primary filings.</p></div>';document.getElementById('ov').style.display='flex';}
function card(c,idx){var o=c.opt&&c.opt.em_pct!=null?c.opt:null,tm=c.t_minus,h=HIST[c.cap];var dt=(c.cash_months!=null&&c.mcap!=null&&c.mcap<2e9)?(c.cash_months<6?'C':c.cash_months<12?'E':null):null;var crush=(o&&o.atm_iv_pct!=null&&o.atm_iv_pct>=120),rg=c.reg;var ric='';if(dt==='C')ric+='<span class="ic dilC" title="Short cash runway (<6 months); financing path not guaranteed.">CASH &lt;6mo</span>';else if(dt==='E')ric+='<span class="ic dilE" title="6-12 months cash; may raise/deal around the catalyst.">CASH 6-12mo</span>';if(crush)ric+='<span class="ic crush" title="ATM IV \u2265120% \u2014 high IV-crush risk after the event.">IV CRUSH</span>';if(rg&&rg.slip)ric+='<span class="ic dilE" title="ClinicalTrials.gov primary-completion date changed; our detection, not an FDA signal \u2014 verify with filings.">REG SLIP</span>';var chg=c.chg!=null?'<span class="chgp '+(c.chg>=0?'up':'dn')+'">'+(c.chg>=0?'+':'')+c.chg.toFixed(1)+'%</span>':'';var dec=c.decided,oc=c.outcome;var decBadge=dec?'<span class="dec '+(oc==='Approved'?'app':oc==='CRL'?'crl':'pen')+'" title="'+(oc==='Approved'||oc==='CRL'?'':'PDUFA date has passed; we have not yet tagged an approval or CRL. Check primary filings.')+'">'+(oc==='Approved'?'\u2713 Approved':oc==='CRL'?'\u2717 CRL':'Date passed \u2014 outcome unknown')+'</span>':'';var conf=c.date_conf||'High',cdot=conf==='High'?'#5fd07a':conf==='Medium'?'#ffc46b':'#ff7a7a';var optln='';if(o){var r=h?o.em_pct/h:0,vc=volClass(r);var vl=h?(vc==='rich'?'Vol rich vs cohort '+r.toFixed(1)+'\u00d7':vc==='cheap'?'Vol low vs cohort '+r.toFixed(1)+'\u00d7':'Vol ~ cohort'):'cohort n/a';var sk=o.cp_oi!=null?((o.cp_oi>=1.5?'call-heavy':o.cp_oi<=0.67?'put-heavy':'balanced')+' '+o.cp_oi+'\u00d7'):'';optln='<div class="tline"><span class="oem">\u00b1'+o.em_pct+'%</span> implied <span class="omut">vs \u00b1'+(h!=null?h:'?')+'% hist</span> \u00b7 <span class="volb '+vc+'" title="Options imply a move \u00b1'+o.em_pct+'% vs the \u00b1'+(h!=null?h:'?')+'% median for similar events in this cap cohort (694 PDUFAs). Context about premium, not a guarantee of move size or profit/loss, and not a trade recommendation.">'+vl+'</span>'+(sk?' \u00b7 <span class="omut">'+sk+' C/P</span>':'')+'</div>';}var cd=CH[c.ticker];var ddm=(dec&&cd&&cd.c&&cd.c.length>1)?((cd.c[cd.c.length-1]/cd.c[cd.c.length-2]-1)*100):null;var chartln=cd?'<div class="cchart">'+chartSVG(cd,74)+'</div>':'';var decln=(dec&&ddm!=null)?'<div class="ddm">Decision-day move: <b style="color:'+(ddm>=0?'#5fd07a':'#ff7a7a')+'">'+(ddm>=0?'+':'')+ddm.toFixed(1)+'%</b></div>':'';var regln=rg?'<div class="tline reg"><span class="rv">\u2713 CT.gov</span> '+rg.status+' \u00b7 PC '+(rg.pcd||'\u2014')+' ('+(rg.pcd_type||'')+')'+(rg.slip?' \u00b7 <span style="color:#ffc46b">\u26a0 date changed</span>':'')+'</div>':'';return '<div class="card'+(dec?' decided':'')+'" onclick="openDetail('+idx+')">'+'<div class="hd"><div class="tm '+tmClass(tm)+'"><div class="n">'+(dec?(oc==='Approved'?'\u2713':oc==='CRL'?'\u2717':'\u2022'):(tm<=0?'\u2022':tm))+'</div><div class="u">'+(dec?'done':(tm<=0?'today':'days'))+'</div></div>'+'<div class="hmeta"><div class="r1"><span class="tk">'+c.ticker+'</span><span class="cap">'+c.cap+'</span>'+chg+decBadge+'<span class="star '+(isWL(c.ticker)?'on':'')+'" onclick="toggleWL(\''+c.ticker+'\',event)" title="Watchlist">'+(isWL(c.ticker)?'\u2605':'\u2606')+'</span></div>'+'<div class="r2"><span class="cdot" style="background:'+cdot+'" title="Date confidence: '+conf+'"></span><span class="dpill" title="'+(c.date_note||'PDUFA target date from FDA/company filings.')+'">'+(c.date_type||'PDUFA target')+'</span> <b>'+c.date+'</b> <span class="omut">\u00b7 T-'+(tm<=0?'0':tm)+'</span> <span class="srcp" title="Sourced from '+((c.source&&c.source.detail)||'company/FDA filing')+'. Verify against primary filings.">Sourced: '+((c.source&&c.source.label)||'filing')+'</span></div>'+'<div class="drug1">'+((c.drug||'').slice(0,36))+' \u2014 <span class="omut">'+((c.indication||'').slice(0,38))+'</span></div>'+decln+(ric?'<div class="ricons">'+ric+'</div>':'')+'</div></div>'+'<div class="tfacts"><span>'+(c.price!=null?'$'+c.price.toFixed(2):'\u2014')+'</span><span>'+fmtB(c.mcap)+'</span><span class="'+(dt==='C'?'cri':dt==='E'?'ele':'')+'">'+(c.cash_months!=null?c.cash_months.toFixed(0)+'mo':'\u2014')+'</span><span>LOA '+(c.loa!=null?c.loa.toFixed(0)+'%':'\u2014')+' <span class="ii" title="Cohort historical LOA (694 PDUFAs, by cap). NOT this drug\'s probability.">\u24d8</span></span></div>'+optln+regln+'</div>';}
function pass(c){const o=c.opt&&c.opt.em_pct!=null?c.opt:null;
  if(c.t_minus>W)return false; if(C!=='all'&&c.cap!==C)return false;
  if(Q&&!(c.ticker+' '+c.name+' '+c.drug+' '+c.indication).toLowerCase().includes(Q))return false;
  if(ST==='pending'&&c.decided)return false; if(ST==='decided'&&!c.decided)return false; if(T.wl&&!isWL(c.ticker))return false; if(T.opt&&!o)return false;
  if(T.vol){if(!o)return false;const h=HIST[c.cap];if(!(h&&o.em_pct/h>=1.5))return false;}
  if(T.run&&!(c.cash_months!=null&&c.cash_months<12))return false; return true;}

function setView(v){VIEW=v;document.querySelectorAll('.vchip').forEach(x=>x.classList.toggle('on',x.dataset.view===v));document.querySelectorAll('.filters .chip:not(.vchip),.filters .lbl,.filters .search').forEach(e=>{e.style.display=(v==='today')?'':'none'});document.getElementById('histf').style.display=(v==='historic')?'flex':'none';if(v==='historic'){try{if(!localStorage.getItem('pb_ack_hist'))document.getElementById('ackh').style.display='flex';}catch(e){}}render();}
function ensureHistoric(){return;}
function hcard(e,idx){const up=e.dmove>=0;var vs=e.vstatus,vb=vs==="verified"?'<span class="vb ver">\u2713 verified</span>':vs==="mislabel"?'<span class="vb mis">\u26a0 mislabel</span>':vs==="consistent"?'<span class="vb prob">~ probable</span>':vs==="disputed"?'<span class="vb warn">\u26a0 unverified</span>':vs==="immaterial"?'<span class="vb imm">immaterial</span>':'';return '<div class="card" onclick="openHist('+idx+')"><div class="hd"><div class="tm grey" style="width:58px"><div class="n" style="font-size:13px;color:'+(e.outcome==='Approved'?'#5fd07a':'#ff7a7a')+'">'+(e.outcome==='Approved'?'✓':'✗')+'</div><div class="u">'+e.outcome+'</div></div><div class="hmeta"><div class="r1"><span class="tk">'+e.t+'</span><span class="cap">'+e.yr+'</span>'+vb+'</div><div class="r2">decision <b>'+e.date+'</b></div><div class="co">decision-day '+(up?'+':'')+e.dmove+'% · ran +'+e.runup+'% into it</div></div></div><div style="padding:8px 12px">'+chartSVG(e)+'</div></div>';}
function openHist(idx){var e=HISTORIC[idx];var rec=e.nx?('<h4>After the CRL \u2192 next decision (recovery)</h4>'+'<div class="tlx">\u25cf CRL '+e.date+(e.reason&&e.reason.cat?' ('+e.reason.cat+')':'')+' \u2192 trough $'+e.nx.trough+' \u2192 '+e.nx.outcome+' '+e.nx.date+'</div>'+chartSVG(e.nx)+'<div class="kv"><span>Next decision</span><b>'+e.nx.date+' ('+e.nx.outcome+')</b></div>'+'<div class="kv"><span>Post-CRL run-up (trough\u2192peak)</span><b>+'+e.nx.runup+'% over '+e.nx.days+'d</b></div>'+'<div class="kv"><span>CRL \u2192 trough \u2192 next price</span><b>$'+e.nx.crl_px+' \u2192 $'+e.nx.trough+' \u2192 $'+e.nx.end_px+'</b></div>'+'<p style="font-size:10.5px;color:var(--mut2)">The fallen-angel pattern: a CRL crash, then the run-up into the resubmission. Past outcomes do not predict future results.</p>'):'';var reason=e.reason?('<h4>CRL reason</h4><p><span class="dec '+((/CMC|Inspection/).test(e.reason.cat)?'pen':'crl')+'" style="margin-right:6px">'+e.reason.cat+'</span>'+e.reason.txt+'</p><p style="color:var(--mut2);font-size:10.5px">Source: '+e.reason.src+'</p>'):(e.outcome==='CRL'?'<h4>CRL reason</h4><p style="color:var(--mut)">Reason not yet curated \u2014 see the company 8-K / FDA action for the basis (efficacy, safety, or CMC).</p>':'');var vnote=(e.outcome==='CRL'&&!e.correction)?(e.vstatus==='disputed'?'<div style="margin:10px 0;padding:9px 11px;border:1px solid #5f3f18;border-radius:8px;background:#241a0d;color:#ffc46b;font-size:11px"><b>\u26a0 Label validation:</b> the decision-day move ('+(e.dmove>=0?'+':'')+e.dmove+'%) is atypical for a CRL and this outcome label is <b>not yet verified</b> against a primary source \u2014 treat with caution.</div>':e.vstatus==='verified'?'<div style="margin:10px 0;padding:7px 11px;border:1px solid #1f6e42;border-radius:8px;background:#0c2417;color:#7ee2a0;font-size:11px">\u2713 Outcome verified against a primary source.</div>':e.vstatus==='immaterial'?'<div style="font-size:10.5px;color:var(--mut2);margin:6px 0">Large-cap label-expansion CRL \u2014 typically immaterial to the stock.</div>':e.vstatus==='consistent'?'<div style="font-size:10.5px;color:var(--mut2);margin:6px 0">Probable CRL \u2014 consistent with the price reaction but not yet source-verified.</div>':''):'';var corr=e.correction?('<div style="margin:10px 0;padding:9px 11px;border:1px solid #5f3f18;border-radius:8px;background:#241a0d;color:#ffce85;font-size:11.5px"><b>\u26a0 Data note:</b> '+e.correction+'</div>'):'';var srclink=e.src_url?('<p style="font-size:11px;margin:8px 0"><a href="'+e.src_url+'" target="_blank" rel="noopener" style="color:#6fb6ff;text-decoration:none">\u2197 View primary source</a> <span style="color:var(--mut2)">(opens company PR / FDA / SEC)</span></p>'):'';document.getElementById('sheet').innerHTML='<div class="sh"><span class="x" onclick="closeDetail(event)">\u2715</span><div style="font-size:20px;font-weight:800">'+e.t+' <span class="cap">'+e.sz+' \u00b7 '+e.yr+'</span> <span class="dec '+(e.outcome==='Approved'?'app':'crl')+'">'+(e.outcome==='Approved'?'\u2713 Approved':'\u2717 CRL')+'</span></div><div style="font-size:12.5px;color:var(--mut)">FDA decision '+e.date+'</div></div><div class="sb">'+corr+vnote+chartBlock(e,'decision day')+'<h4>Decision</h4><div class="kv"><span>Outcome</span><b>'+e.outcome+'</b></div><div class="kv"><span>Decision-day move</span><b>'+(e.dmove>=0?'+':'')+e.dmove+'%</b></div><div class="kv"><span>T-120 run-up (low\u2192high)</span><b>+'+e.runup+'% ($'+e.lo+'\u2192$'+e.hi+')</b></div>'+reason+rec+'<p style="color:var(--mut2);font-size:10.5px;margin-top:10px">Informational/educational only \u2014 not investment advice. Past outcomes do not predict future results.</p></div>';document.getElementById('ov').style.display='flex';}
function renderHistoric(){let rows=HISTORIC.map((e,i)=>[e,i]).filter(x=>{const e=x[0];if(HF.oc!=='all'&&e.outcome!==HF.oc)return false;if(HF.yr!=='all'&&String(e.yr)!==HF.yr)return false;if(HF.sz!=='all'&&e.sz!==HF.sz)return false;if(Q&&!(e.t).toLowerCase().includes(Q))return false;return true;});document.getElementById('count').textContent=rows.length+' past FDA decisions (2024–present) · click any for its T-120 chart & outcome';var EB='<div style="grid-column:1/-1;padding:9px 12px;border:1px solid #5f3f18;border-radius:8px;background:#241a0d;color:#ffc46b;font-size:11.5px;margin-bottom:2px">\u26a0 Historic outcome labels are under active validation \u2014 treat as experimental and cross-check primary sources. \u2713 = source-verified \u00b7 \u26a0 = unverified \u00b7 ~ = probable (price-only).</div>';document.getElementById('list').innerHTML=EB+(rows.map(x=>hcard(x[0],x[1])).join('')||'<div class="count">none match.</div>');}
function render(){ if(VIEW==='historic'){renderHistoric();return;}var rows=DATA.catalysts.map(function(c,i){return [c,i];}).filter(function(x){return pass(x[0]);});rows.sort(function(a,b){return a[0].date<b[0].date?-1:a[0].date>b[0].date?1:0;});document.getElementById('count').textContent=rows.length+' FDA decisions \u00b7 grouped by month';var MN=['January','February','March','April','May','June','July','August','September','October','November','December'];var html='',curM='';for(var z=0;z<rows.length;z++){var x=rows[z],m=x[0].date.slice(0,7);if(m!==curM){curM=m;html+='<div class="mhead">'+MN[(+m.slice(5,7))-1]+' '+m.slice(0,4)+'</div>';}html+=card(x[0],x[1]);}document.getElementById('list').innerHTML=html||'<div class="count">No catalysts match these filters.</div>';}
document.querySelectorAll('.chip[data-w]').forEach(e=>e.onclick=()=>{document.querySelectorAll('.chip[data-w]').forEach(x=>x.classList.remove('on'));e.classList.add('on');W=+e.dataset.w;render()});
document.querySelectorAll('.chip[data-c]').forEach(e=>e.onclick=()=>{document.querySelectorAll('.chip[data-c]').forEach(x=>x.classList.remove('on'));e.classList.add('on');C=e.dataset.c;render()});
document.querySelectorAll('.chip[data-st]').forEach(e=>e.onclick=()=>{document.querySelectorAll('.chip[data-st]').forEach(x=>x.classList.remove('on'));e.classList.add('on');ST=e.dataset.st;render()});document.querySelectorAll('.chip[data-t]').forEach(e=>e.onclick=()=>{T[e.dataset.t]=!T[e.dataset.t];e.classList.toggle('on');render()});
document.getElementById('q').oninput=e=>{Q=e.target.value.toLowerCase().trim();render()};document.getElementById('hq').oninput=e=>{Q=e.target.value.toLowerCase().trim();render()};document.querySelectorAll('.vchip').forEach(e=>e.onclick=()=>setView(e.dataset.view));document.querySelectorAll('.hoc').forEach(e=>e.onclick=()=>{document.querySelectorAll('.hoc').forEach(x=>x.classList.remove('on'));e.classList.add('on');HF.oc=e.dataset.oc;render()});document.querySelectorAll('.hyr').forEach(e=>e.onclick=()=>{document.querySelectorAll('.hyr').forEach(x=>x.classList.remove('on'));e.classList.add('on');HF.yr=e.dataset.yr;render()});document.querySelectorAll('.hsz').forEach(e=>e.onclick=()=>{document.querySelectorAll('.hsz').forEach(x=>x.classList.remove('on'));e.classList.add('on');HF.sz=e.dataset.sz;render()});
async function refresh(){try{const r=await fetch('/api/data',{cache:'no-store'});if(!r.ok)return;const j=await r.json();if(j&&j.catalysts&&j.catalysts.length){DATA.catalysts=j.catalysts;if(j.hist)Object.assign(HIST,j.hist);if(j.as_of){DATA.as_of=j.as_of;var a=document.getElementById('asof');if(a)a.textContent=j.as_of;}var of=document.getElementById('optfresh');if(of)of.textContent='ORATS + FMP · LIVE · '+(j.refreshed_utc||'');render();}}catch(e){}}
function ackOk(){try{localStorage.setItem('pb_ack','1')}catch(e){};document.getElementById('ack').style.display='none';}function ackOkH(){try{localStorage.setItem('pb_ack_hist','1')}catch(e){};document.getElementById('ackh').style.display='none';}try{if(!localStorage.getItem('pb_ack'))document.getElementById('ack').style.display='flex';}catch(e){}render(); refresh(); setInterval(refresh,600000);
</script></body></html>
```

---

## 5. MOBILE APP — full front-end (data elided)
```html

<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no"><meta name="robots" content="noindex,nofollow">
<link rel="manifest" href="/manifest.webmanifest"><meta name="theme-color" content="#050f1f"><link rel="apple-touch-icon" href="/icon-192.png"><meta name="apple-mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<title>pdufa.bio</title>
<style>
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
:root{--bg:#050f1f;--card:#0c1d38;--card2:#0f2547;--line:#1a3358;--gold:#e3ba5e;--ink:#f2f6fc;--mut:#a7bcd9;--mut2:#7890b3;--red:#ff7a7a;--amber:#ffc46b;--blue:#6fb6ff;--green:#5fd07a;--purp:#b9a3ff}
html,body{margin:0;background:#02060d;color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;-webkit-font-smoothing:antialiased}
.app{max-width:440px;margin:0 auto;min-height:100vh;background:var(--bg);position:relative;padding-bottom:74px;overflow-x:hidden}
.top{position:sticky;top:0;z-index:30;background:linear-gradient(180deg,#071528,#050f1f);border-bottom:1px solid var(--line);padding:14px 16px 10px}
.brand{display:flex;align-items:center;justify-content:space-between}
.logo{font-size:20px;font-weight:800;letter-spacing:-.4px}.logo b{color:var(--gold)}
.tag{font-size:10px;color:var(--gold);font-weight:700;letter-spacing:.5px}
.fresh{font-size:10px;color:var(--mut2);margin-top:1px}
.hello{font-size:22px;font-weight:800;margin-top:8px;letter-spacing:-.4px}
.search{margin-top:10px;width:100%;padding:11px 13px;border-radius:12px;border:1px solid var(--line);background:#091a31;color:#fff;font-size:14px}
.scr{padding:14px 14px 20px;display:none}.scr.on{display:block;animation:fade .2s}
@keyframes fade{from{opacity:.4}to{opacity:1}}
.sect{font-size:12px;font-weight:800;color:var(--mut2);text-transform:uppercase;letter-spacing:.6px;margin:16px 2px 8px;display:flex;justify-content:space-between}
.sect .ct{color:var(--gold)}
.mhead{font-size:14px;font-weight:800;color:var(--gold);margin:18px 2px 8px;letter-spacing:.3px}
.row{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:12px;margin-bottom:10px;display:flex;gap:11px;align-items:center;cursor:pointer;transition:transform .08s}
.row:active{transform:scale(.985)}
.tm{flex:0 0 auto;width:50px;text-align:center;border-radius:11px;padding:7px 3px;background:#071528;border:1px solid var(--line)}
.tm .n{font-size:18px;font-weight:800;line-height:1}.tm .u{font-size:8.5px;color:var(--mut2);text-transform:uppercase;margin-top:2px}
.tm.red{border-color:var(--red)}.tm.red .n{color:var(--red)}.tm.amber{border-color:var(--amber)}.tm.amber .n{color:var(--amber)}.tm.blue{border-color:var(--blue)}.tm.blue .n{color:var(--blue)}.tm.grey .n{color:var(--mut)}.tm.green{border-color:var(--green)}.tm.green .n{color:var(--green)}
.mid{flex:1;min-width:0}
.l1{display:flex;align-items:center;gap:6px}
.tk{font-size:16px;font-weight:800}.cap{font-size:8.5px;font-weight:700;color:var(--gold);border:1px solid #4a648c;border-radius:4px;padding:1px 4px;text-transform:uppercase}
.chg{font-size:12px;font-weight:700;margin-left:auto}.chg.up{color:var(--green)}.chg.dn{color:var(--red)}
.sub{font-size:11.5px;color:var(--mut);margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.chips{display:flex;gap:5px;margin-top:6px;flex-wrap:wrap}
.cc{font-size:9.5px;font-weight:700;padding:2px 7px;border-radius:6px;white-space:nowrap}
.cc.app{background:#0e3320;color:#7ee2a0;border:1px solid #1f6e42}.cc.crl{background:#3a1010;color:#ff8a8a;border:1px solid #6e2020}
.cc.vol{background:#34230e;color:#ffce85;border:1px solid #5f3f18}.cc.cash{background:#3a1010;color:#ff9b9b;border:1px solid #6e2020}.cc.iv{background:#2c1230;color:#e6a3ff;border:1px solid #51265a}.cc.reg{background:#0e2c4a;color:#8fc6ff;border:1px solid #245078}
.cc.mut{background:#13243f;color:var(--mut);border:1px solid var(--line)}
.hero{background:linear-gradient(135deg,#13315c,#0c1d38);border:1px solid var(--gold)}
.empty{color:var(--mut2);font-size:13px;text-align:center;padding:26px 10px}
/* bottom sheet */
#sheet{position:fixed;left:0;right:0;bottom:0;z-index:60;max-width:440px;margin:0 auto;background:var(--card);border-radius:18px 18px 0 0;border:1px solid var(--line);max-height:90vh;overflow:auto;transform:translateY(110%);transition:transform .26s cubic-bezier(.2,.8,.2,1)}
#sheet.on{transform:translateY(0)}
#ov{position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:55;opacity:0;pointer-events:none;transition:opacity .2s}#ov.on{opacity:1;pointer-events:auto}
.sh{padding:16px 16px 12px;border-bottom:1px solid var(--line);position:sticky;top:0;background:var(--card)}
.grab{width:38px;height:4px;border-radius:3px;background:#2c4a72;margin:0 auto 12px}
.sb{padding:14px 16px 26px}.sb h4{margin:15px 0 7px;font-size:11px;color:var(--gold);text-transform:uppercase;letter-spacing:.6px}
.kv{display:flex;justify-content:space-between;font-size:13.5px;padding:6px 0;border-bottom:1px solid #112b48}.kv span{color:var(--mut)}.kv b{color:var(--ink)}
.sb p{font-size:12px;color:var(--mut);line-height:1.5}
.dec{font-size:10px;font-weight:800;padding:2px 7px;border-radius:6px}.dec.app{background:#0e3320;color:#7ee2a0;border:1px solid #1f6e42}.dec.crl{background:#3a1010;color:#ff8a8a;border:1px solid #6e2020}
.star{font-size:18px;color:var(--mut2)}.hbann{padding:9px 12px;border:1px solid #5f3f18;border-radius:10px;background:#241a0d;color:#ffc46b;font-size:11px;margin-bottom:8px;line-height:1.45}.tlx{font-size:11px;color:var(--mut);background:#071528;border:1px solid var(--line);border-radius:8px;padding:7px 10px;margin:6px 0}.dnote{margin:8px 0;padding:9px 11px;border:1px solid #5f3f18;border-radius:10px;background:#241a0d;color:#ffce85;font-size:11.5px}.dpill{font-size:9.5px;border:1px solid var(--line);border-radius:5px;padding:1px 5px;color:var(--mut)}.brc{margin-top:12px;border:1px solid var(--line);border-radius:10px;padding:9px 12px}.brc summary{cursor:pointer;font-size:12px;color:var(--gold);font-weight:700;list-style:none}.brc[open] summary{margin-bottom:6px}.star.on{color:var(--gold)}
/* tab bar */
.tabs{position:fixed;left:0;right:0;bottom:0;z-index:40;max-width:440px;margin:0 auto;display:flex;background:#071528;border-top:1px solid var(--line);padding:6px 0 calc(6px + env(safe-area-inset-bottom))}
.tab{flex:1;text-align:center;padding:6px 0;color:var(--mut2);font-size:10px;font-weight:600;cursor:pointer}
.tab.on{color:var(--gold)}.tab .ic{font-size:19px;display:block;line-height:1.1}
#ack{position:fixed;inset:0;background:rgba(2,8,18,.9);z-index:90;display:flex;align-items:center;justify-content:center;padding:22px}
#ack .bx{background:var(--card);border:1px solid var(--gold);border-radius:16px;padding:22px;max-width:380px}
#ack b{color:var(--gold)}#ack button{margin-top:14px;width:100%;padding:12px;border:0;border-radius:11px;background:var(--gold);color:#051020;font-weight:800;font-size:15px}
</style></head>
<body><div class="app">
<div class="top"><div class="brand"><div><div class="logo">pdufa<b>.bio</b></div><div class="fresh" id="fresh">loading…</div></div><div class="tag">FACTS, NOT ADVICE</div></div>
<div id="rhead"><div class="hello" id="hello">Today</div><input class="search" id="q" placeholder="Search ticker or drug…"></div></div>

<div class="scr on" id="s-radar"></div>
<div class="scr" id="s-cal"></div>
<div class="scr" id="s-watch"></div>
<div class="scr" id="s-hist"></div>
<div class="scr" id="s-more">
  <div class="sect">Methodology</div>
  <p style="font-size:12.5px;color:var(--mut);line-height:1.6">Every upcoming FDA decision (PDUFA) with the facts to weigh it: live price &amp; today's move, market cap, cash runway, the drug in plain English, the current options market (expected move, IV, skew) vs the cohort base rate, the ClinicalTrials.gov registry status, and a T-120 run-up chart. Options via ORATS; price via FMP; "Hist. move / LOA" are cohort base rates (694-PDUFA study, 2024–26) describing history, <b>not this drug</b>. Auto-refreshes ~5×/day.</p><p style="font-size:12px;color:var(--mut);line-height:1.6;margin-top:8px"><b style="color:var(--mut)">Vol rich / Vol low</b> compare the options-implied move to the median move for similar events in the same market-cap cohort — context about how expensive premium is versus history, <b>not</b> a guarantee of move size or a trade signal. After a binary event, implied volatility collapses (<b>IV crush</b>), which can cause losses on <b>both</b> long-vol and short-vol positions regardless of direction.</p>
  <div class="sect">Legal</div>
  <p style="font-size:12px;color:var(--mut2);line-height:1.6"><b style="color:var(--mut)">Not affiliated with or endorsed by the FDA.</b> Independent service; "FDA," "PDUFA," and all company/drug/ticker names used descriptively, property of their owners. <b style="color:var(--mut)">Informational/educational only — not investment advice.</b> No buy/sell calls, no approval probabilities. Verify every date against the primary filing; dates can slip and historic labels are still being validated.</p>
</div>

<div class="tabs">
  <div class="tab on" data-s="radar" onclick="go('radar')"><span class="ic">◎</span>Radar</div>
  <div class="tab" data-s="cal" onclick="go('cal')"><span class="ic">▦</span>Calendar</div>
  <div class="tab" data-s="watch" onclick="go('watch')"><span class="ic">★</span>Watchlist</div>
  <div class="tab" data-s="hist" onclick="go('hist')"><span class="ic">◷</span>History</div>
  <div class="tab" data-s="more" onclick="go('more')"><span class="ic">≡</span>More</div>
</div>
<div id="ov" onclick="closeSheet()"></div><div id="sheet"></div>
<div id="ack"><div class="bx"><b>PDUFA.BIO — FACTS, NOT ADVICE</b><p style="font-size:13px;color:var(--ink);line-height:1.5;margin-top:8px">Data &amp; historical statistics only. <b>Not investment advice</b>; no trade recommendations; no individual-drug approval probabilities. <b>Not affiliated with or endorsed by the FDA.</b> Verify all dates &amp; outcomes against primary sources.</p><button onclick="ackOk()">I understand — show me the facts</button></div></div>
</div>
<script>
var DATA=/* «41506 chars elided — sample: {"as_of":"2026-06-17","catalysts":[{"ticker":"GSK","name":"GSK plc American Depositary Shares (Each representing two)","date":"2026-06-18","t_minus":1,"drug":"Tebipenem HBr (SPR994) - (PIVOT-PO)","indication":"Complicated urinary tract infection (cUTI), including acute pyelonephritis (AP)","price":52.11,"mcap":104036582163.0,"cap":"Large","adv":3953624.0,"cash_months":15.82,"loa":87.58,"pop":87.58 …» */ {};
var HISTORIC=/* «219773 chars elided — sample: [{"t":"ASND","date":"2026-02-28","yr":2026,"outcome":"Approved","dmove":3.7,"lo":196.01,"hi":242.09,"runup":19.0,"ta":null,"c":[203.23,208.24,199.22,209.55,210.85,196.63,202.82,208.98,209.29,217.32,235.39,223.59,224.19,230.21,233.5,239.22],"piv":[0,15],"sz":"Large"},{"t":"ETON","date":"2026-02-25","yr":2026,"outcome":"Approved","dmove":-3.4,"lo":14.35,"hi":19.25,"runup":4.0,"ta":null,"c":[18.46,17 …» */ {};
var WL=[]; try{WL=JSON.parse(localStorage.getItem('pb_wl')||'[]')}catch(e){}
function fmtB(v){return v==null?'—':v>=1e9?'$'+(v/1e9).toFixed(1)+'B':v>=1e6?'$'+(v/1e6).toFixed(0)+'M':'$'+v.toFixed(0)}
function tmC(d){return d<=7?'red':d<=21?'amber':d<=45?'blue':'grey'}
function isWL(t){return WL.indexOf(t)>=0}
function tglWL(t,ev){if(ev)ev.stopPropagation();var i=WL.indexOf(t);if(i>=0)WL.splice(i,1);else WL.push(t);try{localStorage.setItem('pb_wl',JSON.stringify(WL))}catch(e){};paint();}
function volTxt(c){var o=c.opt;if(!o||o.em_pct==null)return null;var h=HIST[c.cap];if(!h)return null;var r=o.em_pct/h;return r>=2?'Vol rich '+r.toFixed(1)+'×':r<=1?'Vol low '+r.toFixed(1)+'×':null}
function chartSVG(o,Hh){if(!o||!o.c||o.c.length<3)return '';Hh=Hh||120;var c=o.c,n=c.length,W=400,pad=8,lo=Math.min.apply(null,c),hi=Math.max.apply(null,c),rng=(hi-lo)||1;var X=function(i){return pad+i/(n-1)*(W-2*pad)},Y=function(v){return pad+(1-(v-lo)/rng)*(Hh-2*pad)};var pts=c.map(function(v,i){return X(i).toFixed(1)+','+Y(v).toFixed(1)}).join(' ');var dots='';(o.piv||[]).forEach(function(i){var v=c[i],isHi=(i===0?(c[1]!=null&&v>c[1]):i===n-1?v>c[n-2]:(v>=c[i-1]&&v>=c[i+1]));dots+='<circle cx="'+X(i).toFixed(1)+'" cy="'+Y(v).toFixed(1)+'" r="2.4" fill="'+(isHi?'#5fd07a':'#ff7a7a')+'"/>'});var hiI=c.indexOf(hi),loI=c.indexOf(lo);return '<svg viewBox="0 0 '+W+' '+Hh+'" style="width:100%;background:#071528;border:1px solid var(--line);border-radius:10px"><polyline points="'+pts+'" fill="none" stroke="#e3ba5e" stroke-width="1.4"/>'+dots+'<text x="'+X(hiI).toFixed(1)+'" y="'+(Y(hi)-3).toFixed(1)+'" fill="#5fd07a" font-size="9" text-anchor="middle">$'+hi+'</text><text x="'+X(loI).toFixed(1)+'" y="'+(Y(lo)+10).toFixed(1)+'" fill="#ff7a7a" font-size="9" text-anchor="middle">$'+lo+'</text></svg>'}
function row(c,i){
  var tm=c.t_minus,dec=c.decided,oc=c.outcome;
  var tmcls=dec?(oc==='Approved'?'green':oc==='CRL'?'red':'grey'):tmC(tm);
  var tmn=dec?(oc==='Approved'?'✓':oc==='CRL'?'✗':'•'):(tm<=0?'•':tm);
  var tmu=dec?'done':(tm<=0?'today':'days');
  var chg=c.chg!=null?'<span class="chg '+(c.chg>=0?'up':'dn')+'">'+(c.chg>=0?'+':'')+c.chg.toFixed(1)+'%</span>':'';
  var tags=[];
  if(dec)tags.push(oc==='Approved'?'<span class="cc app">✓ Approved</span>':oc==='CRL'?'<span class="cc crl">✗ CRL</span>':'<span class="cc mut">Date passed — outcome unknown</span>');
  var v=volTxt(c);if(v)tags.push('<span class="cc vol">'+v+'</span>');
  if(c.cash_months!=null&&c.cash_months<6&&c.mcap!=null&&c.mcap<2e9)tags.push('<span class="cc cash">CASH &lt;6mo</span>');
  if(c.opt&&c.opt.atm_iv_pct!=null&&c.opt.atm_iv_pct>=120)tags.push('<span class="cc iv">IV CRUSH</span>');
  if(c.reg&&c.reg.slip)tags.push('<span class="cc reg">REG SLIP</span>');
  if(c.opt&&c.opt.em_pct!=null)tags.push('<span class="cc mut">±'+c.opt.em_pct+'% exp</span>');
  var chips=tags.slice(0,3).join('');if(tags.length>3)chips+='<span class="cc mut">+'+(tags.length-3)+' more</span>';
  return '<div class="row'+(dec?'':'')+'" onclick="openS('+i+')"><div class="tm '+tmcls+'"><div class="n">'+tmn+'</div><div class="u">'+tmu+'</div></div>'+
    '<div class="mid"><div class="l1"><span class="tk">'+c.ticker+'</span><span class="cap">'+c.cap+'</span>'+chg+'</div>'+
    '<div class="sub">'+(c.drug||'').slice(0,30)+' · '+(c.indication||'').slice(0,26)+'</div>'+
    '<div class="chips">'+chips+'</div></div></div>';
}
function sortDate(a,b){return a[0].date<b[0].date?-1:1}
function paint(){
  var q=(document.getElementById('q').value||'').toLowerCase().trim();
  var all=DATA.catalysts.map(function(c,i){return[c,i]}).filter(function(x){return !q||(x[0].ticker+' '+x[0].name+' '+x[0].drug+' '+x[0].indication).toLowerCase().indexOf(q)>=0});
  // RADAR
  var today=all.filter(function(x){return x[0].decided||x[0].t_minus<=0}).sort(sortDate);
  var hv=all.filter(function(x){return !x[0].decided&&x[0].t_minus>=0&&x[0].t_minus<=3&&x[0].opt&&x[0].opt.atm_iv_pct!=null&&x[0].opt.atm_iv_pct>=120}).sort(sortDate);var hvs={};hv.forEach(function(x){hvs[x[0].ticker]=1});
  var wk=all.filter(function(x){return !x[0].decided&&!hvs[x[0].ticker]&&x[0].t_minus>0&&x[0].t_minus<=7}).sort(sortDate);
  var mo=all.filter(function(x){return !x[0].decided&&!hvs[x[0].ticker]&&x[0].t_minus>7&&x[0].t_minus<=30}).sort(sortDate);
  var R='';
  if(today.length)R+='<div class="sect">Decisions — today &amp; just in</div>'+today.map(function(x){return row(x[0],x[1]).replace('class="row','class="row hero')}).join('');
  if(hv.length)R+='<div class="sect">High visibility <span class="ct">near-term · high IV</span></div>'+hv.map(function(x){return row(x[0],x[1])}).join('');
  R+='<div class="sect">This week <span class="ct">T-7</span></div>'+(wk.length?wk.map(function(x){return row(x[0],x[1])}).join(''):'<div class="empty">Nothing in the next 7 days.</div>');
  R+='<div class="sect">Next 30 days</div>'+(mo.length?mo.map(function(x){return row(x[0],x[1])}).join(''):'<div class="empty">Nothing in 8–30 days.</div>');
  document.getElementById('s-radar').innerHTML=R;
  // CALENDAR (month grouped)
  var rows=all.slice().sort(sortDate);var C='',cur='';var MN=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  rows.forEach(function(x){var m=x[0].date.slice(0,7);if(m!==cur){cur=m;C+='<div class="mhead">'+MN[(+m.slice(5,7))-1]+' '+m.slice(0,4)+'</div>'}C+=row(x[0],x[1])});
  document.getElementById('s-cal').innerHTML=C||'<div class="empty">No matches.</div>';
  // WATCHLIST
  var w=all.filter(function(x){return isWL(x[0].ticker)}).sort(sortDate);
  renderHist();document.getElementById('s-watch').innerHTML='<div class="sect">Your watchlist <span class="ct">'+w.length+'</span></div>'+(w.length?w.map(function(x){return row(x[0],x[1])}).join(''):'<div class="empty">Tap ★ on any catalyst to add it here.</div>');
}
function openS(i){var c=DATA.catalysts[i];var o=c.opt&&c.opt.em_pct!=null?c.opt:null;var h=HIST[c.cap];var cd=CH[c.ticker];
  var dec=c.decided,oc=c.outcome;var ddm=(dec&&cd&&cd.c&&cd.c.length>1)?((cd.c[cd.c.length-1]/cd.c[cd.c.length-2]-1)*100):null;
  var opth=o?('<h4>Options (ORATS)</h4><div class="kv"><span>Implied move</span><b>±'+o.em_pct+'%</b></div><div class="kv"><span>ATM IV</span><b>'+(o.atm_iv_pct!=null?o.atm_iv_pct+'%':'—')+'</b></div><div class="kv"><span>Expiry · DTE</span><b>'+o.exp+' · '+o.dte+'d</b></div><div class="kv"><span>Call wall · C/P OI</span><b>$'+o.call_wall+' · '+(o.cp_oi!=null?o.cp_oi+'×':'—')+'</b></div>'):'<h4>Options</h4><p>No liquid options snapshot.</p>';
  var reg=c.reg?('<h4>Registry — ClinicalTrials.gov</h4><div class="kv"><span>Trial</span><b><a href="https://clinicaltrials.gov/study/'+c.reg.nct+'" target="_blank" style="color:#6fb6ff">'+c.reg.nct+'</a></b></div><div class="kv"><span>Status</span><b>'+c.reg.status+'</b></div><div class="kv"><span>Primary completion</span><b>'+(c.reg.pcd||'—')+' ('+(c.reg.pcd_type||'')+')</b></div>'+(c.reg.slip?'<p style="color:#ffc46b">⚠ Primary-completion date changed '+c.reg.slip.from+'→'+c.reg.slip.to+' ('+(c.reg.slip.days>=0?'+':'')+c.reg.slip.days+'d). Our detection, not an FDA signal — verify with filings.</p>':'')):'';
  document.getElementById('sheet').innerHTML='<div class="sh"><div class="grab"></div><div style="display:flex;align-items:center;gap:8px"><span class="tk" style="font-size:22px">'+c.ticker+'</span><span class="cap">'+c.cap+'</span>'+(dec?'<span class="dec '+(oc==='Approved'?'app':oc==='CRL'?'crl':'mut')+'">'+(oc==='Approved'?'✓ Approved':oc==='CRL'?'✗ CRL':'Date passed — outcome unknown')+'</span>':'')+'<span class="star '+(isWL(c.ticker)?'on':'')+'" style="margin-left:auto" onclick="tglWL(\''+c.ticker+'\',event)">'+(isWL(c.ticker)?'★':'☆')+'</span></div><div style="font-size:12.5px;color:var(--mut);margin-top:3px">'+c.name+'</div><div style="font-size:12.5px;margin-top:4px"><span class="dpill">'+(c.date_type||'PDUFA')+'</span> <b>'+c.date+'</b> · T-'+(c.t_minus<=0?'0':c.t_minus)+' · <span style="color:'+(c.date_conf==='Medium'?'#ffc46b':'#5fd07a')+'">'+(c.date_conf||'High')+' confidence</span></div>'+'<div style="font-size:10px;color:var(--mut2);margin-top:2px">Sourced: '+((c.source&&c.source.detail)||'company/FDA filing')+'</div></div>'+
  '<div class="sb">'+(cd?'<h4>Run-up — T-120</h4>'+chartSVG(cd,118)+'<p style="font-size:10.5px;color:var(--mut2)">● green = local high · ● red = low/sell-off'+(dec&&ddm!=null?' · decision-day move <b style="color:'+(ddm>=0?'#5fd07a':'#ff7a7a')+'">'+(ddm>=0?'+':'')+ddm.toFixed(1)+'%</b>':'')+'</p>':'')+
  '<h4>Drug</h4><div style="font-size:13px;font-weight:600">'+(c.drug||'')+'</div><div style="font-size:12.5px;color:var(--mut)">'+(c.indication||'')+'</div>'+
  '<h4>Facts</h4><div class="kv"><span>Price'+(c.chg!=null?' (today)':'')+'</span><b>'+(c.price!=null?'$'+c.price.toFixed(2):'—')+(c.chg!=null?' ('+(c.chg>=0?'+':'')+c.chg.toFixed(1)+'%)':'')+'</b></div><div class="kv"><span>Market cap</span><b>'+fmtB(c.mcap)+'</b></div><div class="kv"><span>Cash runway</span><b>'+(c.cash_months!=null?c.cash_months.toFixed(0)+' mo':'—')+'</b></div>'+
  opth+reg+
  '<details class="brc"><summary>Base-rate context (LOA &amp; hist. move) ›</summary>'+'<div class="kv"><span>Hist. LOA (cohort)</span><b>'+(c.loa!=null?c.loa.toFixed(0)+'%':'—')+'</b></div>'+'<div class="kv"><span>Cohort hist. move</span><b>±'+(h!=null?h:'—')+'%</b></div>'+'<p style="font-size:11.5px;color:var(--mut)">'+(c.cap==='Micro'||c.cap==='Small'?'Small/micro names historically had a modest pre-run-up; the decision day is roughly a coin-flip even on approvals.':c.cap==='Mid'?'Mid-caps historically ran ~+6% with smaller decision-day moves.':'Large-caps are efficient — little run-up, near-zero decision-day move.')+' These are historical cohort base rates by market-cap tier (694 PDUFAs, 2024–26). They are not probabilities for this specific drug, and past cohorts do not guarantee future outcomes.</p></details>'+
  '<p style="font-size:10.5px;color:var(--mut2);margin-top:8px">Sourced from: '+((c.source&&c.source.detail)||'company/FDA filing')+'. pdufa.bio provides data and historical statistics — not investment advice, no trade recommendations, no individual-drug approval probabilities. Not affiliated with or endorsed by the FDA. Verify against primary filings.</p></div>';
  document.getElementById('ov').classList.add('on');document.getElementById('sheet').classList.add('on');
}
function closeSheet(){document.getElementById('ov').classList.remove('on');document.getElementById('sheet').classList.remove('on');}
function vbApp(e){var v=e.vstatus;return v==='verified'?'<span class="cc app">✓ verified</span>':v==='mislabel'?'<span class="cc crl">⚠ mislabel</span>':v==='consistent'?'<span class="cc mut">~ probable</span>':v==='disputed'?'<span class="cc vol">⚠ unverified</span>':v==='immaterial'?'<span class="cc mut">immaterial</span>':'';}
function hrow(e,i){var up=e.dmove>=0;return '<div class="row" onclick="openHsheet('+i+')"><div class="tm '+(e.outcome==='Approved'?'green':'red')+'"><div class="n">'+(e.outcome==='Approved'?'✓':'✗')+'</div><div class="u">'+(e.outcome==='Approved'?'appr':'CRL')+'</div></div><div class="mid"><div class="l1"><span class="tk">'+e.t+'</span><span class="cap">'+e.sz+'</span><span class="chg '+(up?'up':'dn')+'">'+(up?'+':'')+e.dmove+'%</span></div><div class="sub">decision '+e.date+' · ran +'+e.runup+'% in</div><div class="chips">'+vbApp(e)+'</div></div></div>';}
function renderHist(){var q=(document.getElementById('q').value||'').toLowerCase().trim();var rows=HISTORIC.map(function(e,i){return[e,i];}).filter(function(x){return !q||x[0].t.toLowerCase().indexOf(q)>=0;});rows.sort(function(a,b){return a[0].date<b[0].date?1:-1;});var H='<div class="hbann">⚠ Experimental — outcome/CRL labels under active validation. ✓ source-verified · ~ price-only · ⚠ unverified/mislabel. Cross-check filings.</div>';var cur='';rows.forEach(function(x){var y=x[0].date.slice(0,4);if(y!==cur){cur=y;H+='<div class="mhead">'+y+'</div>';}H+=hrow(x[0],x[1]);});document.getElementById('s-hist').innerHTML=H;}
function openHsheet(i){var e=HISTORIC[i];var up=e.dmove>=0;
var rec=e.nx?('<h4>After the CRL → next decision</h4><div class="tlx">● CRL '+e.date+' → trough $'+e.nx.trough+' → '+e.nx.outcome+' '+e.nx.date+'</div>'+chartSVG(e.nx,110)+'<div class="kv"><span>Post-CRL run-up</span><b>+'+e.nx.runup+'% / '+e.nx.days+'d</b></div>'):'';
var reason=e.reason?('<h4>CRL reason</h4><p style="font-size:12.5px;color:var(--mut)">'+(e.reason.cat?'<b style="color:var(--ink)">'+e.reason.cat+'</b> — ':'')+(e.reason.txt||'')+'</p>'):'';
var corr=e.correction?('<div class="dnote"><b>⚠ Data note:</b> '+e.correction+'</div>'):'';
var srclink=e.src_url?('<p style="font-size:11.5px;margin:8px 0"><a href="'+e.src_url+'" target="_blank" rel="noopener" style="color:#6fb6ff">↗ View primary source</a></p>'):'';
document.getElementById('sheet').innerHTML='<div class="sh"><div class="grab"></div><div style="display:flex;align-items:center;gap:8px"><span class="tk" style="font-size:22px">'+e.t+'</span><span class="cap">'+e.sz+' · '+e.date.slice(0,4)+'</span><span class="dec '+(e.outcome==='Approved'?'app':'crl')+'">'+(e.outcome==='Approved'?'✓ Approved':'✗ CRL')+'</span></div><div style="font-size:12.5px;color:var(--mut);margin-top:3px">FDA decision '+e.date+'</div></div><div class="sb">'+corr+(vbApp(e)?'<div style="margin:6px 0">'+vbApp(e)+'</div>':'')+srclink+'<h4>Run-up — T-120</h4>'+chartSVG(e,118)+'<div class="kv"><span>Decision-day move</span><b style="color:'+(up?'#5fd07a':'#ff7a7a')+'">'+(up?'+':'')+e.dmove+'%</b></div><div class="kv"><span>T-120 run-up (low→high)</span><b>+'+e.runup+'% ($'+e.lo+'→$'+e.hi+')</b></div>'+reason+rec+'<p style="font-size:10.5px;color:var(--mut2);margin-top:10px">Informational/educational only — not investment advice. Past outcomes do not predict future results.</p></div>';
document.getElementById('ov').classList.add('on');document.getElementById('sheet').classList.add('on');}
function go(s){['radar','cal','watch','hist','more'].forEach(function(x){document.getElementById('s-'+x).classList.toggle('on',x===s);});document.querySelectorAll('.tab').forEach(function(t){t.classList.toggle('on',t.dataset.s===s)});document.getElementById('rhead').style.display=(s==='radar')?'block':'none';window.scrollTo(0,0);}
document.getElementById('q').oninput=paint;
function ackOk(){try{localStorage.setItem('pb_ack','1')}catch(e){};document.getElementById('ack').style.display='none';}
try{if(localStorage.getItem('pb_ack'))document.getElementById('ack').style.display='none';}catch(e){}
function setFresh(s){document.getElementById('fresh').textContent=s;}
setFresh('as of '+DATA.as_of);
paint();
if('serviceWorker' in navigator){navigator.serviceWorker.register('/sw.js').catch(function(){});}
(async function(){try{var r=await fetch('/api/data',{cache:'no-store'});if(r.ok){var j=await r.json();if(j&&j.catalysts&&j.catalysts.length){DATA=j;if(j.hist)HIST=j.hist;setFresh('LIVE · '+(j.refreshed_utc||DATA.as_of));paint();}}}catch(e){}})();
setInterval(function(){fetch('/api/data',{cache:'no-store'}).then(function(r){return r.ok?r.json():null}).then(function(j){if(j&&j.catalysts){DATA=j;if(j.hist)HIST=j.hist;setFresh('LIVE · '+(j.refreshed_utc||''));paint();}}).catch(function(){});},600000);
</script></body></html>
```

---

## 6. What we want from THIS audit (be specific — cite the section/component)
1. **Visual hierarchy & scannability:** does the 3-line tape card show the right things in the right order? Is anything still too dense or competing for attention? Is the decision-day move / risk-icon placement right?
2. **Information architecture:** are the 5 app tabs the right split? Is "High visibility" earning its spot above "This week"? Should Calendar/History merge? Is the web Today/Historic toggle discoverable enough?
3. **Detail sheet:** right order of sections? Too long on mobile? Should anything else be collapsed (like base-rate already is)?
4. **Provenance UX:** are the "Sourced:" pills + validation badges + "↗ primary source" links clear and trustworthy without implying more certainty than we have? Where do we most need real per-fact links next?
5. **Advice-risk in layout:** any arrangement, emphasis, color, or sort that could read as a recommendation or a per-drug probability?
6. **First-run & onboarding:** is the gate → modal → Radar flow good? What's missing for a brand-new retail user to orient in <15s?
7. **Empty/loading/error states**, accessibility (contrast, tap targets, focus), and responsive behavior of the web grid.
8. **The #1 layout change** you'd make to each surface before public launch, and why.
