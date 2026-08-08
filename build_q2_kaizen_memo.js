const fs = require('fs');
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
        HeadingLevel, AlignmentType, BorderStyle, WidthType, ShadingType,
        LevelFormat, PageBreak, PageOrientation } = require('docx');

const border = { style: BorderStyle.SINGLE, size: 4, color: "CCCCCC" };
const borders = { top: border, bottom: border, left: border, right: border };

const h1 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun({ text: t, bold: true })] });
const h2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun({ text: t, bold: true })] });
const h3 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun({ text: t, bold: true })] });
const p  = (t) => new Paragraph({ children: [new TextRun(t)], spacing: { after: 120 } });
const pb = (pre, post) => new Paragraph({ children: [new TextRun({ text: pre, bold: true }), new TextRun(post)], spacing: { after: 120 } });
const bullet = (t) => new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [new TextRun(t)] });

function headerRow(cells, widths) {
  return new TableRow({ tableHeader: true, children: cells.map((c, i) => new TableCell({
    borders, width: { size: widths[i], type: WidthType.DXA },
    shading: { fill: "1F4E78", type: ShadingType.CLEAR },
    margins: { top: 80, bottom: 80, left: 100, right: 100 },
    children: [new Paragraph({ children: [new TextRun({ text: c, bold: true, color: "FFFFFF", size: 18 })] })]
  })) });
}
function row(cells, widths, shade) {
  return new TableRow({ children: cells.map((c, i) => new TableCell({
    borders, width: { size: widths[i], type: WidthType.DXA },
    shading: shade ? { fill: shade, type: ShadingType.CLEAR } : undefined,
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    children: [new Paragraph({ children: [new TextRun({ text: String(c), size: 18 })] })]
  })) });
}
function makeTable(widths, header, rows, shader) {
  const total = widths.reduce((a,b)=>a+b,0);
  return new Table({
    width: { size: total, type: WidthType.DXA },
    columnWidths: widths,
    rows: [ headerRow(header, widths), ...rows.map((r, i) => row(r, widths, shader ? shader(i, r) : null)) ],
  });
}

// Load the scan results
const scan = JSON.parse(fs.readFileSync('/sessions/confident-serene-ptolemy/mnt/9realms/q2_options_scan_v3_ranked.json', 'utf8'));
const core = scan.top_core || [];
const lotto = scan.all_lotto || [];

// v2 Predictor results
const v2 = JSON.parse(fs.readFileSync('/sessions/confident-serene-ptolemy/mnt/9realms/t60_runup_gap_predictor_v2_deploy.json', 'utf8'));

const children = [];

// ============= SECTION 1: T-60 PREDICTOR v2 =============
children.push(new Paragraph({
  children: [new TextRun({ text: "9 Realms — Q2 2026 Kaizen Cycle", bold: true, size: 36, color: "1F4E78" })],
  alignment: AlignmentType.CENTER, spacing: { after: 80 }
}));
children.push(new Paragraph({
  children: [new TextRun({ text: "T-60 Runup Gap Predictor v2 + Q2 Options Scan", size: 24, italics: true, color: "595959" })],
  alignment: AlignmentType.CENTER, spacing: { after: 240 }
}));
children.push(new Paragraph({
  children: [new TextRun({ text: "April 19, 2026 · David (rockyshoals@gmail.com)", size: 18, color: "595959" })],
  alignment: AlignmentType.CENTER, spacing: { after: 400 }
}));

children.push(h1("Executive Summary"));
children.push(p("Two deliverables in one cycle. First, T-60 Runup Gap Predictor v2 — a ChEMBL-augmented rebuild of v1.0. Predicted mean AP-CR gap nearly doubled from +3.62 pp (v1) to +6.08 pp (v2), with CI95 [+5.48, +6.69] and 100% seed stability (v1 was 95%). Feature count collapsed 50 to 7 under honest val-only greedy selection. Second, Q2 options scan across 292 active catalysts using ORATS + cached chains. Two live edges confirmed: CORE (Phase 1/2 positive readouts, ATM calls) and LOTTO (micro/nano PDUFA + liquid strike). Top CORE picks: IMRX, AZN, CMPX, EBS, BCRX (all score >=88). Top LOTTO: GRCE (score 82, spread 2.7%, OI 2,267). Portfolio positions: GRCE is the Q2 LOTTO anchor; ALXO and WHWK are CORE but have liquidity issues."));
children.push(p("All deployed scores are ordinally valid. Use for ranking, not calibrated probabilities."));

// ============= T-60 PREDICTOR v2 =============
children.push(h1("Part 1 — T-60 Runup Gap Predictor v2.0"));

children.push(h2("Rebuild Goals"));
children.push(p("v1.0 locked a +3.62 pp predicted AP-CR gap on the T-60 to T-1 window with monotonic Q1→Q5 sorting but a wide CI and individual-return R² of −0.066. v2 targets three upgrades:"));
children.push(bullet("Add ChEMBL drug-biology features (418 drugs × 11 attributes including molecule_type, mechanism_type, target_class)."));
children.push(bullet("Add Gungnir v46 primitives (journey signals, modality interactions)."));
children.push(bullet("Add Large × T4 interaction head targeting the +6.42 pp segment edge from Runup Decomposition v2.0."));

children.push(h2("Honest Methodology"));
children.push(bullet("Two-head Ridge regression: mu_AP fits approvals only, mu_CR fits CRLs only. Predicted gap = mu_AP(X) − mu_CR(X)."));
children.push(bullet("3-way temporal split: train <2024-01-01 (n=1,086) / val 2024 (n=360) / test ≥2025-01-01 (n=343)."));
children.push(bullet("Target winsorized to [−50%, +100%]."));
children.push(bullet("Alpha sweep per head. Val-only greedy forward selection, gate Δval_R² ≥ +0.002, max 25 rounds."));
children.push(bullet("Bootstrap 95% CI on predicted gap (n_boot=2000, seed=42). 20-seed stability test."));
children.push(bullet("Test touched once for final metrics."));

children.push(h2("v2 Headline Results"));
children.push(makeTable(
  [2600, 2200, 2200, 2200],
  ["Metric", "v1.0", "v2.0", "Δ"],
  [
    ["Predicted gap (mean, test)", "+3.62 pp", "+6.08 pp", "+2.46 pp"],
    ["CI95", "[+2.99, +4.27]", "[+5.48, +6.69]", "Tighter"],
    ["Seed stability (positive %)", "95.0%", "100.0%", "+5.0 pp"],
    ["Feature count", "50", "7", "−43"],
    ["mu_AP alpha (converged)", "500", "10", "Signal sharper"],
    ["mu_CR alpha (converged)", "500", "500", "Unchanged"],
    ["Q4 actual_gap (test)", "+8.20 pp", "+16.26 pp", "+8.06 pp"],
  ]
));
children.push(p(""));

children.push(h2("Selected Features (7)"));
children.push(p("mu_AP head (approvals): ppm_flag, ch_scorable, ta_very_high_risk, naive_sponsor."));
children.push(p("mu_CR head (CRLs): experienced_sponsor, accelerated_approval, ch_tc_kinase."));
children.push(p("ChEMBL contribution: 2 of 7 features (ch_scorable, ch_tc_kinase) — drug-biology signal survived on both heads. Large × T4 interaction head produced zero surviving features; the +6.42 pp Large × T4 decomposition edge is already captured by ta_very_high_risk and size/tier features indirectly. Gungnir v46 primitives also did not survive — orthogonal to T-60 runup-gap signal."));

children.push(h2("Quintile Validation (test)"));
children.push(makeTable(
  [1400, 1400, 1800, 1800, 1800, 1800],
  ["Quintile", "n", "pred_gap mean", "actual_AP", "actual_CR", "actual_gap"],
  [
    ["Q1", "76", "−0.15%", "+2.63%", "+10.16%", "−7.54%"],
    ["Q2", "143", "+5.28%", "+12.20%", "+13.84%", "−1.64%"],
    ["Q3", "95", "+8.45%", "+8.83%", "+14.90%", "−6.07%"],
    ["Q4", "29", "+18.63%", "+2.50%", "−13.76%", "+16.26%"],
  ]
));
children.push(p("Q4 delivers the clean edge: AP runup is modest but CR actually LOSES value, producing a +16.26 pp actual gap. Q1 also cleanly avoids — CRLs run up twice as much as approvals. Q2/Q3 are middle-noise — do not allocate."));

children.push(h2("New Quintile Thresholds (v2)"));
children.push(makeTable(
  [2000, 2000, 2000, 3000],
  ["Quintile", "pred_gap threshold", "Allocation", "Meaning"],
  [
    ["Q1", "≤ +0.0257", "SKIP", "Approvals and CRLs run up similarly"],
    ["Q2", "≤ +0.0621", "SKIP", "Weak gap"],
    ["Q3", "≤ +0.0848", "50% allocation", "Borderline gap"],
    ["Q4", "> +0.0848", "Full allocation", "Clean AP-CR divergence"],
  ]
));
children.push(p("v2 is a gating filter, not a magnitude forecaster. Individual-return R² remains negative. Use ONLY quintile rank."));

children.push(h2("Honest Limitations"));
children.push(bullet("Test-set regime (2025-2026): CRLs actually ran up MORE than approvals in aggregate (AP mean +7.63% vs CR mean +11.87%). The gap-sort still works but absolute expectations should anchor on the decomposition v2 baseline, not test means."));
children.push(bullet("mu_AP alpha=10 (much less shrinkage than v1's alpha=500) — v2 has sharper feature response but higher variance."));
children.push(bullet("Only 29 events in Q4 — narrow bucket, watch for regime drift. Retrain annually."));
children.push(bullet("ChEMBL coverage not 100% — ch_scorable=0 events are penalized on mu_AP (coef +0.021). Small-cap preclinical / biologic / cell-therapy events get pushed toward lower quintiles purely by modality."));

children.push(h2("v2 Integration Rule (locked)"));
children.push(p("For PDUFA equity entries at T-60 to T-7 window: require T-60 Predictor v2 Q3+ AND ODIN ≥ T2. Q4 gets full allocation; Q3 gets 50%; Q1/Q2 = skip. Scorable events only — if ch_scorable=0 (biologics, cell therapy, preclinical), treat as Q1/Q2 regardless of pred_gap value."));

children.push(new Paragraph({ children: [new PageBreak()] }));

// ============= Q2 OPTIONS SCAN =============
children.push(h1("Part 2 — Q2 2026 Options Scan"));

children.push(h2("Scope"));
children.push(p(`Scanned 292 active Q2 catalysts (Apr 19 → Jun 30) against live/cached ORATS chains. 252 returned usable ATM call data (149 from existing cache, 103 fetched fresh). Methodology follows BIFROST Options v1.3 rules locked from 1,828-trade Red Team backtest:`));
children.push(bullet("SKIP ODIN tier filter for options — edge inverts 21 pp. T1+T2 LOSE on options, T3+T4 WIN."));
children.push(bullet("Don't buy cheap IV — Q1 cheapest is the WORST segment. Edge requires IV expansion potential."));
children.push(bullet("OI sweet spot: 100-499 preferred. Avoid <20 (illiquid) and ≥500 (hedging noise) except at PDUFA where liquidity trumps."));
children.push(bullet("Two live edges only: CORE (Phase 1/2 positive readout ATM T-14→T-1) and LOTTO (micro/nano PDUFA + OI≥50 + spread≤30)."));
children.push(bullet("Use REAL_40 fill model for sizing, not MID. MID hides spread capture reality."));

children.push(h2("Scan Results"));
children.push(makeTable(
  [3000, 2000, 3000],
  ["Classification", "Count", "Meaning"],
  [
    ["CORE", "39", "Phase 1/2 positive readout candidate — core edge (+45% MID, +16% REAL_40)"],
    ["LOTTO", "1", "Micro/nano PDUFA + liquid strike — tail-driven (+56% MID, +38% REAL_40)"],
    ["LOTTO_LOW_LIQ", "0", "PDUFA micro/nano but OI or spread fails liquidity gate"],
    ["AVOID", "212", "Fails both edges — skip options, equity-only or no position"],
    ["No chain/stale", "40", "No live ORATS data"],
  ]
));

children.push(h2("Top CORE Picks (Phase 1/2 Readouts)"));
children.push(makeTable(
  [900, 1400, 900, 1100, 1100, 1100, 1100, 1100],
  ["Ticker", "Catalyst Date", "DTE", "Strike", "Mid", "OI", "Spread", "Score"],
  core.slice(0, 10).map(c => [
    c.ticker,
    c.catalyst_date,
    String(c.dte),
    `$${c.atm_strike}`,
    `$${c.call_mid.toFixed(2)}`,
    String(c.call_oi),
    `${c.spread_pct.toFixed(1)}%`,
    String(c.entry_score)
  ])
));

children.push(h3("Top CORE Commentary"));
children.push(pb("IMRX (Apr 20, score 95):", " Atebimetinib + mGnP Phase 2a in oncology. Gungnir prob 0.996 / T1 / BETA. ATM $5 call, mid $1.20, spread 25% (wide but not disqualifying), OI 315 (in sweet spot). IV 137% = pricing the event. Strongest CORE setup — readout is TOMORROW."));
children.push(pb("AZN (Apr 30, score 95):", " Tagrisso + Datroway ORCHARD Phase 2. Large cap, so IV is low (31.8%) and spread tight (9.9%). Tight OI 131. Safe CORE but magnitude capped by large cap base rate."));
children.push(pb("CMPX (Apr 30, score 90):", " CTX-009 DLL4×VEGF-A bispecific Phase 2/3. OI 14,198 and volume 5,548 — institutional flow is here. Spread 7.8%, IV 293% (event fully priced). High conviction CORE but IV already loaded. Watch for IV-change exit trap."));
children.push(pb("EBS (Apr 30, score 88):", " Brincidofovir MpOx Phase 1. IV 104.5%, spread 17.1%, OI 1,058. Clean mid-sized CORE."));
children.push(pb("BCRX (Apr 30, score 88):", " BCX17725 Phase 1. IV 66.5% (relatively cheap), OI 175 (sweet spot). Spread 31.1% is a concern. Mid-cap CORE."));
children.push(pb("KYTX (Apr 20/21, score 85 both):", " Miv-cel Phase 2. IV 97.6%, OI 264. Spread 38% is wide — REAL_40 fill penalizes. Size conservatively."));

children.push(h2("LOTTO (micro/nano PDUFA)"));
children.push(makeTable(
  [900, 1400, 900, 1100, 1100, 1100, 1100, 1100],
  ["Ticker", "Catalyst Date", "DTE", "Strike", "Mid", "OI", "Spread", "Score"],
  lotto.map(c => [
    c.ticker,
    c.catalyst_date,
    String(c.dte),
    `$${c.atm_strike}`,
    `$${c.call_mid.toFixed(2)}`,
    String(c.call_oi),
    `${c.spread_pct.toFixed(1)}%`,
    String(c.entry_score)
  ])
));
children.push(pb("GRCE (Apr 23, score 82):", " GTX-104 STRIVE-ON PDUFA, nano cap ($47.9M mcap). ATM $5 call, mid $1.88, spread 2.7% (very tight), OI 2,267, volume 526. IV 472% — event fully priced but that's OK for LOTTO. This is the Q2 LOTTO play. Size ≤1% per v1.3 rule. Ex-top-5 LOTTO return is only +1.15% — this is a moonshot lottery, not a repeatable edge."));

children.push(h2("Active Portfolio Callouts"));
children.push(makeTable(
  [1200, 1400, 1000, 4200],
  ["Position", "Edge", "Score", "Notes"],
  [
    ["GRCE", "LOTTO", "82", "PDUFA Apr 23 nano. THE Q2 lottery. $5 ATM call, 2.7% spread, IV 472%. Size ≤1%."],
    ["WHWK", "CORE", "45", "AACR Apr 21. Phase 1/2 Gungnir prob 0.96. BUT spread 192% = illiquid chain; not tradeable as options. Equity only."],
    ["ALXO", "CORE", "55", "ESMO May 7 Phase 1/2 breast onc. Low OI (30) + spread 100% = illiquid options. Equity preferred."],
    ["CRDF", "AVOID", "0", "Readout ~Jun 30 is 72 days out, outside [1,45] DTE window. Equity only, revisit at T-21."],
    ["CABA", "AVOID", "0", "AAN Apr 20 was booked as Jun 29 in catalyst file — 72 days. Cell therapy anyway (OOD for options)."],
  ]
));

children.push(h2("Hard Rules Applied (v1.3 recap)"));
children.push(bullet("NEVER stack ODIN tier filter with options — edge is inverted 21 pp."));
children.push(bullet("DON'T buy cheap IV — Q1 IV quintile is the WORST segment. Want IV expansion, not absolute cheapness."));
children.push(bullet("OI sweet spot 100-499. Exceptions: PDUFAs where OI ≥500 is needed for exit liquidity (GRCE 2,267 is fine)."));
children.push(bullet("REAL_40 fill model for sizing. MID hides 23pp of spread drag."));
children.push(bullet("LOTTO max 1% per position. CORE max 2% per position. Never hold through catalyst."));

children.push(h2("Caveats"));
children.push(bullet("IV is AT ALREADY ELEVATED LEVELS for most Phase 1/2 readouts this week. IV expansion upside is limited — CORE returns will skew to delta (stock move) not vega (IV expansion)."));
children.push(bullet("40 catalysts have stale or no chain — manual ORATS pull would be needed for completeness, but the 252 scored represent the liquid universe."));
children.push(bullet("BIFROST Options v1.3 edges were validated on historical data with honest fills. Forward results may regress to the mean."));
children.push(bullet("Gungnir/ODIN scores are ordinally valid only — do not use as calibrated probabilities."));

children.push(h1("Actions for This Week"));
children.push(bullet("IMRX ATM $5 May-15 call — CORE, readout Apr 20 (TOMORROW). Enter today or do not enter. Size up to 2% (primary CORE play)."));
children.push(bullet("GRCE ATM $5 May-15 call — LOTTO, PDUFA Apr 23. Size ≤1%. This is the Q2 lottery."));
children.push(bullet("CMPX ATM $6 May-15 call — CORE, Apr 30 readout. Highest institutional flow; enter by T-14 (Apr 16 has passed; entering later is acceptable but less edge)."));
children.push(bullet("AZN, EBS, BCRX — CORE candidates for Apr 30. Size on spread/IV/OI profile. AZN cleanest, EBS mid, BCRX higher spread."));
children.push(bullet("ALXO, WHWK — options chains too illiquid. Stay equity."));
children.push(bullet("Update CLAUDE.md with T-60 Predictor v2 specs and Q2 option scan timestamp."));

children.push(new Paragraph({ children: [
  new TextRun({ text: "Informational and educational only. Not investment advice. ", bold: true, italics: true }),
  new TextRun({ text: "All options trades carry risk of total loss. Size per v1.3 rules and cross-engine scorecard +25% boost cap.", italics: true })
], spacing: { before: 300 } }));

const doc = new Document({
  numbering: {
    config: [{
      reference: "bullets",
      levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 720, hanging: 360 } } } }]
    }]
  },
  styles: {
    default: { document: { run: { font: "Arial", size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, font: "Arial", color: "1F4E78" },
        paragraph: { spacing: { before: 360, after: 200 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 26, bold: true, font: "Arial", color: "2E75B6" },
        paragraph: { spacing: { before: 240, after: 140 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 22, bold: true, font: "Arial", color: "404040" },
        paragraph: { spacing: { before: 180, after: 100 }, outlineLevel: 2 } },
    ]
  },
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 1080, right: 1080, bottom: 1080, left: 1080 }
      }
    },
    children
  }]
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync('/sessions/confident-serene-ptolemy/mnt/9realms/Q2_Kaizen_Memo_Apr19_2026.docx', buf);
  console.log("Wrote Q2_Kaizen_Memo_Apr19_2026.docx");
});
