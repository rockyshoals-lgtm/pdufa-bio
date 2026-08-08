const fs = require('fs');
const path = require('path');
const docx = require('/sessions/confident-serene-ptolemy/node_modules/docx');

const {
  Document, Paragraph, TextRun, HeadingLevel, AlignmentType, PageBreak,
  Table, TableRow, TableCell, WidthType, BorderStyle, ShadingType, TabStopType,
  Packer, LevelFormat, convertInchesToTwip, convertMillimetersToTwip
} = docx;

const BRAND = { primary: '2E5C8A', accent: '8B4513', text: '2C3E50', muted: '6B7280' };

function p(text, opts={}) {
  const { size=22, bold=false, italics=false, align=AlignmentType.LEFT, color=null, spacing=null, indent=null } = opts;
  const runs = Array.isArray(text) ? text : [{ text: String(text ?? '') }];
  const children = runs.map(r => new TextRun({
    text: r.text ?? '',
    bold: r.bold ?? bold,
    italics: r.italics ?? italics,
    size: r.size ?? size,
    color: r.color ?? color,
  }));
  return new Paragraph({
    children,
    alignment: align,
    spacing: spacing ?? { after: 120 },
    indent: indent ?? undefined,
  });
}

function h(text, level=1) {
  const sizes = { 1: 32, 2: 26, 3: 22 };
  return new Paragraph({
    children: [new TextRun({ text, bold: true, size: sizes[level] || 24, color: BRAND.primary })],
    heading: level === 1 ? HeadingLevel.HEADING_1 : level === 2 ? HeadingLevel.HEADING_2 : HeadingLevel.HEADING_3,
    spacing: { before: 240, after: 120 },
  });
}

function bullet(text, opts={}) {
  const { size=22, bold=false, color=null } = opts;
  const runs = Array.isArray(text) ? text : [{ text: String(text ?? '') }];
  return new Paragraph({
    children: runs.map(r => new TextRun({ text: r.text ?? '', bold: r.bold ?? bold, size: r.size ?? size, color: r.color ?? color })),
    bullet: { level: 0 },
    spacing: { after: 60 },
  });
}

function cell(text, opts={}) {
  const { bold=false, shading=null, align=AlignmentType.LEFT, w=1800, size=18, color=null } = opts;
  const runOpts = { text: String(text ?? ''), bold, size };
  if (color) runOpts.color = color;
  const cellOpts = {
    children: [new Paragraph({ children: [new TextRun(runOpts)], alignment: align })],
    width: { size: w, type: WidthType.DXA },
    margins: { top: 60, bottom: 60, left: 80, right: 80 },
  };
  if (shading) cellOpts.shading = { type: ShadingType.CLEAR, color: 'auto', fill: shading };
  return new TableCell(cellOpts);
}

function table(headers, rows, widths) {
  const headerRow = new TableRow({
    children: headers.map((h, i) => cell(h, { bold: true, shading: BRAND.primary, color: 'FFFFFF', w: widths[i] || 1800, align: AlignmentType.CENTER })),
  });
  const bodyRows = rows.map((row, ridx) =>
    new TableRow({
      children: row.map((c, i) => cell(c, { w: widths[i] || 1800, shading: ridx % 2 === 1 ? 'F2F4F7' : null })),
    })
  );
  return new Table({ rows: [headerRow, ...bodyRows], width: { size: 100, type: WidthType.PERCENTAGE } });
}

const sections = [];

// Cover
sections.push(
  p('9 REALMS / PDUFA.BIO', { size: 24, bold: true, color: BRAND.primary, align: AlignmentType.CENTER }),
  p('Q2 2026 OPTIONS PLAYBOOK', { size: 48, bold: true, color: BRAND.primary, align: AlignmentType.CENTER, spacing: { before: 480, after: 240 } }),
  p('Forward-Looking Options Plan for the Aggressive 30-Name Q2 Roster', { size: 26, italics: true, color: BRAND.muted, align: AlignmentType.CENTER, spacing: { after: 480 } }),
  p('As of April 17, 2026', { size: 22, align: AlignmentType.CENTER, color: BRAND.text }),
  p('Companion to Q2_2026_Aggressive_Strategy.docx', { size: 20, italics: true, align: AlignmentType.CENTER, color: BRAND.muted }),
  new Paragraph({ children: [new PageBreak()] }),
);

// Executive summary
sections.push(h('Executive Summary'));
sections.push(p([
  { text: 'Bottom line: ', bold: true },
  { text: '29 of the 30 aggressive Q2 roster names are AACR conference plays happening this week (Apr 17–22). The T-14 options entry window for AACR already closed on April 1. Those 29 names are ' },
  { text: 'equity-only ', bold: true },
  { text: 'from here — exit per the rotation waterfall and book gains before each presentation.' },
]));
sections.push(p([
  { text: 'The actual Q2 options opportunity is forward-looking: ', bold: true },
  { text: 'three high-priority setups totaling a 5.5% capital budget — UNCY PDUFA Jun 27 (2.0%), OSTX PDUFA Jun 30 (2.0%), and CABA EULAR Jun 3 (1.5%). All three ride the GOLD / ASYMMETRIC segments of the BIFROST Options v1.1 backtest (PDUFA Micro +36.7% avg, Phase 2 Readout Small +29.8% avg). Staggered entries May 14 → Jun 11.' },
]));
sections.push(p([
  { text: 'Near-term: ', bold: true },
  { text: 'ALXO ESMO May 7 (D-20) is the only currently-open options window worth considering, and even there IV is elevated at 252% / ivPct1Y 79%. Hold off until IV pulls back at least 15%, then size ≤1.5% as an options overlay on top of the 55% equity core. ' },
  { text: 'AXSM Apr 30 PDUFA', bold: true },
  { text: ' is T-14 active but falls in the MARGINAL mid-cap PDUFA segment (+1.8% avg, 36.2% win) — skip options, play via BIFROST v4 equity timing.' },
]));

// Data disclosure
sections.push(h('Honest Data Disclosure', 2));
sections.push(bullet([
  { text: 'ORATS cache coverage: ', bold: true },
  { text: 'only 9 tickers have complete Apr 2 snapshots (ABSI, ALXO, BHC, BHVN, CABA, GRCE, MNKD, NUVB, WHWK). Overlap with the 30-name roster: GRCE. Plus ALXO (broad scan per your direction).' },
]));
sections.push(bullet([
  { text: '28 of 30 roster names: ', bold: true },
  { text: 'require a live ORATS fetch before fresh cheapness scoring. Current recommendations use (a) BIFROST v1.1 segment backtest, (b) BIFROST v1.0 deploy-scan data from Apr 4, (c) live IV observations from operational notes.' },
]));
sections.push(bullet([
  { text: 'BIFROST v1.1 backtest fills: ', bold: true },
  { text: 'mid-price. Ask-price fills flip many segments negative. LIMIT ORDERS at mid or better are not optional.' },
]));

// Current portfolio
sections.push(h('Active Options Window Now (Apr 17)', 2));

sections.push(h('ALXO — ESMO Breast May 7 (D-20)', 3));
sections.push(p([
  { text: 'Stock now $1.65. ', bold: true },
  { text: 'ORATS Apr 2 snapshot: IV=252%, ivPct1Y=79%, ivRank1Y=54. That is elevated — expect IV to hold at these levels into May 7 with potential further expansion in the final week. ALXO is a core 55% equity held position, so stacking options increases thesis concentration.' },
]));
sections.push(p([
  { text: 'Recommendation: ', bold: true },
  { text: 'DO NOT CHASE at current IV. Watch for ≥15% IV pullback before entry. If entered: max 1.5% of capital in ATM calls, strike $2.00 or $2.50, May 15 monthly (spans the May 7 event). Combined ALXO equity + options exposure ceiling = 60%.' },
]));

sections.push(h('AXSM — AXS-05 sNDA Apr 30 (D-13)', 3));
sections.push(p([
  { text: 'T-14 options window is OPEN this week. ', bold: true },
  { text: 'However, mid-cap PDUFA segment has +1.8% avg return and 36.2% win rate per the 1,828-trade BIFROST v1.1 backtest — roughly flat EV with full theta exposure.' },
]));
sections.push(p([
  { text: 'Recommendation: ', bold: true },
  { text: 'SKIP options. If strong conviction, cap at 0.5% capital, ATM $60 May 15, limit orders only. Equity play via BIFROST v4 timing is superior.' },
]));

sections.push(new Paragraph({ children: [new PageBreak()] }));

// Top 3 high-priority plays
sections.push(h('Top 3 High-Priority Q2 Options Plays'));
sections.push(p([{ text: 'Wait for T-14 — staggered entries May 14 → Jun 11.', italics: true, color: BRAND.muted }]));

const topPlaysHeaders = ['Rank', 'Ticker', 'Catalyst', 'Cat Date', 'Mcap', 'Entry (T-14)', 'Expiry', 'Size', 'Segment Edge'];
const topPlaysRows = [
  ['1', 'UNCY', 'Zephyr-HC oral soln PDUFA', '2026-06-27', 'Micro', '2026-06-08', 'Jul 17', '2.0%', 'GOLD +36.7% 50% win'],
  ['1', 'OSTX', 'OST-HER2 PDUFA (osteosarcoma)', '2026-06-30', 'Micro', '2026-06-11', 'Jul 17', '2.0%', 'GOLD +36.7% 50% win'],
  ['3', 'CABA', 'EULAR RESET-SLE/SSc data', '2026-06-03', 'Small', '2026-05-14', 'Jun 19', '1.5%', 'Phase 2 +29.8% 41.8%'],
];
sections.push(table(topPlaysHeaders, topPlaysRows, [700, 900, 3400, 1400, 900, 1400, 1000, 700, 2400]));

sections.push(h('1. UNCY — PDUFA Micro GOLD', 3));
sections.push(p([
  { text: 'GOLD segment ', bold: true },
  { text: '(PDUFA Micro: +36.7% avg, 50% win, 19.3% of trades >100%). Single best-edge options segment in the universe.' },
]));
sections.push(bullet([{ text: 'Entry: ', bold: true }, { text: 'June 8, 2026 (T-14 trading days before June 27)' }]));
sections.push(bullet([{ text: 'Expiry: ', bold: true }, { text: 'July 17 monthly (spans catalyst, ~21 days to cover IV crush exit)' }]));
sections.push(bullet([{ text: 'Size: ', bold: true }, { text: '2.0% of capital. ATM calls.' }]));
sections.push(bullet([{ text: 'Calendar reminder: ', bold: true }, { text: 'June 5.' }]));

sections.push(h('2. OSTX — PDUFA Micro GOLD (co-equal)', 3));
sections.push(p([
  { text: 'OST-HER2 is orphan oncology with BTD stack. ODIN v14 weights: is_oncology (+0.120), gt_x_btd (+0.140), accel_orphan_btd interactions.' },
]));
sections.push(bullet([{ text: 'Entry: ', bold: true }, { text: 'June 11, 2026 (T-14 trading days before June 30)' }]));
sections.push(bullet([{ text: 'Expiry: ', bold: true }, { text: 'July 17 monthly' }]));
sections.push(bullet([{ text: 'Size: ', bold: true }, { text: '2.0% of capital' }]));
sections.push(bullet([{ text: 'Calendar reminder: ', bold: true }, { text: 'June 9.' }]));

sections.push(h('3. CABA — EULAR Jun 3 Conference Readout', 3));
sections.push(p([
  { text: 'Small-cap Phase 2 readout at major conference. Smart Money Overlay flagged CEO buying + Cormorant ownership. 100% MG-ADL response at RESET-MG. BTD+ODD+RMAT stack. Current IV per operational notes: 73% near / 99% far — MODERATE cheapness.' },
]));
sections.push(bullet([{ text: 'Entry: ', bold: true }, { text: 'May 14, 2026 (T-14 trading days before June 3)' }]));
sections.push(bullet([{ text: 'Expiry: ', bold: true }, { text: 'June 19 monthly' }]));
sections.push(bullet([{ text: 'Size: ', bold: true }, { text: '1.5% of capital' }]));
sections.push(bullet([{ text: 'Calendar reminder: ', bold: true }, { text: 'May 12.' }]));

sections.push(new Paragraph({ children: [new PageBreak()] }));

// Skip list
sections.push(h('Explicit SKIP-Options Names from Q2 Roster', 2));
const skipHeaders = ['Ticker', 'Segment', 'Reason', 'Action'];
const skipRows = [
  ['DBVT', 'Phase 3 Readout Small', 'Segment avg -5.8%, 32.3% win', 'Equity only (BIFROST v4)'],
  ['RNA',  'Phase 3 Readout Mid',   'Segment avg -5.8%, negative EV',  'Equity only'],
  ['LNTH', 'PDUFA Mid',             'Segment avg +1.8% — marginal',    'Equity only or skip'],
  ['AXSM', 'PDUFA Mid',             'Segment avg +1.8% — marginal',    'Equity preferred via BIFROST v4'],
  ['HCM',  'Conference Mid',        'Liquidity 29 (illiquid chains)',  'Equity only'],
  ['All AACR names (22)', 'Conference, D-0 to D-5', 'T-14 window closed Apr 1', 'Equity only, exit pre-presentation'],
];
sections.push(table(skipHeaders, skipRows, [1600, 2400, 3600, 3400]));

// Expiry comparison
sections.push(h('Weekly vs Monthly Expiry Comparison', 2));
const expiryHeaders = ['Ticker', 'Cat Date', 'Monthly (3rd Fri)', 'Weekly (1st Fri after)', 'Preferred'];
const expiryRows = [
  ['UNCY', '2026-06-27', '2026-07-17', '2026-07-02', 'Weekly — more leverage, 5d buffer'],
  ['OSTX', '2026-06-30', '2026-07-17', '2026-07-02', 'Weekly — more leverage'],
  ['CABA', '2026-06-03', '2026-06-19', '2026-06-05', 'Monthly — weekly too tight'],
  ['ALXO', '2026-05-07', '2026-05-15', '2026-05-08', 'Monthly — weekly 1d post'],
  ['AXSM', '2026-04-30', '2026-05-15', '2026-05-01', 'Monthly — weekly expires day-of'],
];
sections.push(table(expiryHeaders, expiryRows, [900, 1600, 1800, 2000, 4500]));
sections.push(p([
  { text: 'Rule: ', bold: true },
  { text: 'Monthly expiry preferred when the first post-catalyst Friday is <3 days after the event. Weekly preferred when there are ≥5 days between catalyst and next Friday (more leverage, exit T-1 before weekend).' },
]));

// Segment edge reference
sections.push(h('BIFROST Options v1.1 Segment Edge Reference', 2));
sections.push(p('1,828 real ORATS-backed trades, 2022–2026, mid-price fills with LIMIT ORDER discipline.'));
const segHeaders = ['Segment', 'Avg Return', 'Win Rate', '% >100%', 'Verdict'];
const segRows = [
  ['PDUFA Micro',      '+36.7%', '50.0%', '19.3%', 'GOLD'],
  ['Phase 1/2 Readout','+28.2%', '52.9%', '21.4%', 'GOLD'],
  ['Phase 2 Readout',  '+29.8%', '41.8%', '17.6%', 'ASYMMETRIC'],
  ['PDUFA Small',      '+12.6%', '38.4%', '12.5%', 'DECENT'],
  ['PDUFA Mid',        '+1.8%',  '36.2%', '—',     'MARGINAL'],
  ['PDUFA Large',      '-5.5%',  '31.0%', '—',     'AVOID (theta)'],
  ['Phase 3 Readout',  '-5.8%',  '32.3%', '—',     'AVOID'],
  ['Phase 2b Readout', '-19.4%', '29.6%', '—',     'AVOID'],
];
sections.push(table(segHeaders, segRows, [3000, 1800, 1800, 1500, 2400]));

// Risk rules
sections.push(h('Options Position Sizing & Risk Rules', 2));
sections.push(bullet([{ text: 'Max single options position: ', bold: true }, { text: '2% of capital (vs 3–5% equity). Sniper multiplier up to 1.5× with explosion tier confirm → 3% cap.' }]));
sections.push(bullet([{ text: 'Filter: ', bold: true }, { text: 'ODIN T1 (≥0.85) or T2 (0.65–0.85) only. Honest-calibrated probabilities (×0.96).' }]));
sections.push(bullet([{ text: 'LIMIT ORDERS MANDATORY. ', bold: true }, { text: 'Bid-ask spreads cost ~23pp on average. Ask-price fills flip EV negative.' }]));
sections.push(bullet([{ text: 'Never hold through the event. ', bold: true }, { text: 'Exit T-1 before close. No exceptions. Options amplify gains AND losses — IV crush is real.' }]));
sections.push(bullet([{ text: 'Combined options + equity on same name ≤ 60% of portfolio. ', bold: true }, { text: '(Applied specifically to ALXO — 55% equity + any options addition.)' }]));
sections.push(bullet([{ text: 'Re-score cheapness at T-14. ', bold: true }, { text: 'Skip if ivPct1Y > 80 or IV/RV > 2.0 at entry time.' }]));

// Budget summary
sections.push(h('Q2 Options Capital Budget', 2));
sections.push(p([
  { text: 'Total budget: ', bold: true },
  { text: '5.5% of capital across three staggered plays (UNCY 2.0% + OSTX 2.0% + CABA 1.5%). Peak concurrent options heat ~4.5% (UNCY + OSTX overlap Jun 11–26). All three resolve by end of Q2. Fits inside the aggressive 35–40% peak concurrent heat budget without crowding the equity rotation.' },
]));
sections.push(p([
  { text: 'If ALXO IV pulls back and qualifies for an options overlay, add ≤1.5% May 7 play and bring total Q2 options budget to ~7%.', italics: true },
]));

// Honest caveats
sections.push(h('Honest Caveats', 2));
sections.push(bullet([{ text: 'ORATS cache coverage: ', bold: true }, { text: 'only 1 of 30 roster names has fresh ORATS data. All specific cheapness scores require live ORATS fetch at T-14.' }]));
sections.push(bullet([{ text: 'Stage classification check: ', bold: true }, { text: 'DBVT and RNA appear Phase 3 (AVOID). XNCR stage needs verification before sizing — Phase 2 vs 2b flips edge from +29.8% to -19.4%.' }]));
sections.push(bullet([{ text: 'Backtest selection bias: ', bold: true }, { text: 'The 1,828 trades are T-1 compliant, but greedy backtest period selection could inflate segment edge by 5–10pp. Treat returns as ordinal, not absolute.' }]));
sections.push(bullet([{ text: 'Live IV will change things. ', bold: true }, { text: 'Re-run cheapness at each T-14 entry. This playbook is a plan, not a limit order.' }]));

const doc = new Document({
  creator: '9 Realms / pdufa.bio',
  title: 'Q2 2026 Options Playbook',
  description: 'Forward-looking options plan complementing Q2 aggressive strategy',
  styles: {
    default: {
      document: { run: { font: 'Calibri', size: 22 } },
    },
  },
  sections: [{
    properties: { page: { margin: { top: convertInchesToTwip(0.8), bottom: convertInchesToTwip(0.8), left: convertInchesToTwip(0.8), right: convertInchesToTwip(0.8) } } },
    children: sections,
  }],
});

Packer.toBuffer(doc).then(buffer => {
  const outPath = '/sessions/confident-serene-ptolemy/mnt/9realms/Q2_2026_Options_Appendix.docx';
  fs.writeFileSync(outPath, buffer);
  console.log(`Wrote ${outPath} (${buffer.length} bytes, ${sections.length} elements)`);
});
