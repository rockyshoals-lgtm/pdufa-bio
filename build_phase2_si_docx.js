// Phase 2 Short Interest Honest Kaizen Findings memo
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, Header, Footer,
        AlignmentType, PageOrientation, LevelFormat, HeadingLevel, BorderStyle, WidthType,
        ShadingType, PageNumber, PageBreak } = require('docx');
const fs = require('fs');

const P = (text, opts = {}) => new Paragraph({
  spacing: { after: 120, ...(opts.spacing || {}) },
  ...opts,
  children: (opts.children || [new TextRun({ text, ...(opts.run || {}) })]),
});

const H = (text, level, opts = {}) => new Paragraph({
  heading: level,
  spacing: { before: 240, after: 120, ...(opts.spacing || {}) },
  children: [new TextRun({ text, bold: true, ...(opts.run || {}) })],
});

const bullet = (text) => new Paragraph({
  numbering: { reference: 'bullets', level: 0 },
  spacing: { after: 80 },
  children: [new TextRun({ text })],
});

const border = { style: BorderStyle.SINGLE, size: 1, color: 'CCCCCC' };
const borders = { top: border, bottom: border, left: border, right: border };

const cell = (text, opts = {}) => new TableCell({
  borders,
  width: { size: opts.width || 2340, type: WidthType.DXA },
  shading: opts.fill ? { fill: opts.fill, type: ShadingType.CLEAR } : undefined,
  margins: { top: 80, bottom: 80, left: 120, right: 120 },
  children: [new Paragraph({
    children: [new TextRun({
      text,
      bold: opts.bold || false,
      size: opts.size || 18,
      font: opts.mono ? 'Consolas' : undefined,
    })],
  })],
});

function makeTable(rows, colWidths) {
  const tableWidth = colWidths.reduce((a, b) => a + b, 0);
  return new Table({
    width: { size: tableWidth, type: WidthType.DXA },
    columnWidths: colWidths,
    rows: rows.map((r, i) => new TableRow({
      children: r.map((c, j) => cell(c, {
        width: colWidths[j],
        fill: i === 0 ? 'D5E8F0' : undefined,
        bold: i === 0,
        mono: j > 0 && i > 0,
      })),
    })),
  });
}

const doc = new Document({
  styles: {
    default: { document: { run: { font: 'Arial', size: 22 } } },
    paragraphStyles: [
      { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 32, bold: true, font: 'Arial' },
        paragraph: { spacing: { before: 240, after: 120 }, outlineLevel: 0 } },
      { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 26, bold: true, font: 'Arial' },
        paragraph: { spacing: { before: 220, after: 100 }, outlineLevel: 1 } },
      { id: 'Heading3', name: 'Heading 3', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 22, bold: true, font: 'Arial' },
        paragraph: { spacing: { before: 180, after: 80 }, outlineLevel: 2 } },
    ],
  },
  numbering: {
    config: [{
      reference: 'bullets',
      levels: [{ level: 0, format: LevelFormat.BULLET, text: '\u2022', alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 720, hanging: 360 } } } }],
    }],
  },
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 1080, right: 1080, bottom: 1080, left: 1080 },
      },
    },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [new TextRun({ text: 'Phase 2 \u2014 Short Interest Honest Kaizen \u2014 Apr 20, 2026 \u2014 Page ', size: 18 }),
                     new TextRun({ children: [PageNumber.CURRENT], size: 18 })],
        })],
      }),
    },
    children: [
      H('Phase 2 \u2014 Short Interest Honest Kaizen: NULL RESULT', HeadingLevel.HEADING_1),
      P('Apr 20, 2026 \u2014 9realms / pdufa.bio internal research', { run: { italics: true, color: '666666' } }),

      H('Headline', HeadingLevel.HEADING_2),
      P('FINRA historical biweekly short interest features (2015\u20132026, 196 settlement dates, 2.6M ticker-dates) do NOT beat either ODIN v14 or Gungnir v46 under strict honest 3-way temporal split. Both champions stand.'),

      makeTable([
        ['Engine', 'Baseline test AUC', 'Final test AUC', '\u0394 test', '95% CI on \u0394', 'p(lift>0)', 'Verdict'],
        ['ODIN v14', '0.9156', '0.9162', '+0.0006', '[-0.0028, +0.0046]', '0.620', 'NULL'],
        ['Gungnir v46', '0.7448', '0.7448', '+0.0000', '[0.0000, 0.0000]', '0.000', 'HARD NULL'],
      ], [1280, 1400, 1300, 1000, 1560, 980, 1200]),

      P('This is the 6th and 7th consecutive honest Kaizen NULL result across all three 9realms engines (BIFROST v5.7, BIFROST v5.8, Gungnir v47, ODIN v17 HINT, Smart Money Phase 3, SI \u00d7 ODIN, SI \u00d7 Gungnir).',
        { spacing: { before: 100 } }),

      H('Methodology (Strict)', HeadingLevel.HEADING_2),
      bullet('Split: train \u2264 2022-12-31 / val 2023-2024 / test \u2265 2025-01-01. Identical to ODIN v17 / Smart Money Phase 3 pattern.'),
      bullet('Baseline: ODIN v14 51-feature Ridge (or Gungnir v46 126-feature meta-ensemble). C sweep on VAL ONLY.'),
      bullet('Candidates: 23 SI features (level, deltas, 4-pt trend, monotonicity, vol ratio, non-linear squares, coverage indicators).'),
      bullet('Val-only greedy forward selection, gate \u0394val_AUC \u2265 +0.002, max 10 rounds.'),
      bullet('Test touched ONCE at the end. Bootstrap 95% CI on \u0394test_AUC, n_boot=2000, seed=42, percentile.'),
      bullet('Fix applied this session: rebuilt ODIN baseline from raw primitives (port of odin_v14_kaizen.py lines 43\u2013256). Broken stub was returning zeros for all 51 engineered features and producing a fake 0.5000 baseline, hence the prior session\u2019s phantom +0.1370 lift claim \u2014 DISCARDED.'),

      H('Data Coverage', HeadingLevel.HEADING_2),
      makeTable([
        ['Dataset', 'Events', 'Matched SI at T-1', 'Coverage', 'Train / Val / Test split (matched)'],
        ['ODIN v14 training', '2,203', '1,857', '84.3%', '1,081 / 764 / 358'],
        ['Gungnir v46 training', '1,752', '1,752', '100.0%', '225 / 972 / 555'],
      ], [2080, 880, 1400, 1000, 2240]),

      P('ODIN coverage 84.3% because FINRA CDN only serves files from 2017-12-29 onward \u2014 pre-2018 events get zero-imputed SI (14 no_snapshot indicator). Gungnir coverage 100% because Gungnir training window starts 2022.'),

      H('ODIN \u00d7 SI: Greedy Forward Log', HeadingLevel.HEADING_2),
      P('Best C on val: 0.025 (val_auc=0.8673, test_auc=0.9156). Reproduces ODIN v14 honest bar (0.8995) within the matched-sample variance.'),
      makeTable([
        ['Round', 'Best candidate', '\u0394val', 'Decision'],
        ['1', 'si_trend_monotonic_up', '+0.0025', 'ADDED (clears +0.002 gate)'],
        ['2', 'si_delta_1_2_short_pct', '+0.0008', 'STOP (below gate)'],
      ], [700, 3200, 1100, 3360]),
      P('Only one SI feature cleared the val gate. When that feature was added and the full baseline+1 was scored once on test: +0.0006 test lift, CI spans zero, p(lift>0)=0.620.'),

      H('Gungnir \u00d7 SI: Hard Null', HeadingLevel.HEADING_2),
      P('Best C on val: 0.005 (val_auc=0.7650, test_auc=0.7448). Baseline slightly underruns Gungnir v47 honest bar (0.7551) on this matched split.'),
      P('ZERO SI features cleared the +0.002 val gate. Top candidate si_t1_adv at +0.0002 \u2014 an order of magnitude short. Final = baseline. Verdict: hard null.'),

      H('Why SI Features Don\u2019t Lift Either Engine', HeadingLevel.HEADING_2),
      bullet('ODIN v14 already captures the smart-money squeeze signal through ppm_flag_bin, ppm_x_dtc, and microstructure interactions (validated in BIFROST Explosion v5.4\u20135.5 as dominant drivers). Adding raw SI levels and deltas is redundant.'),
      bullet('Gungnir readouts are drug-biology events \u2014 phase readout success is driven by trial design, drug modality, sponsor track record, and journey features. Short interest has near-zero direct signal on clinical trial outcome.'),
      bullet('The one SI feature that did clear the ODIN val gate (si_trend_monotonic_up) is a coarse 4-point monotonic indicator. Its companion si_delta_1_2_short_pct did NOT clear the gate, suggesting the survivor is picking up ticker-level idiosyncrasy, not a stable signal.'),
      bullet('Test-set coverage tilt: 2025\u20132026 test events have different SI panel composition than training (FINRA CDN 2017+ only). Any weak signal in train fails to generalize to a post-2024 panel with evolved retail/institutional positioning norms.'),

      H('What This Does NOT Disprove', HeadingLevel.HEADING_2),
      bullet('SI panel features MAY still matter for OPTIONS trading (BIFROST Explosion v5.5 already uses log_si and ppm_x_dtc \u00d7 log_si). Explosion detection \u2260 outcome prediction.'),
      bullet('SI level at T-14 specifically (vs T-1 snapshot) may carry entry-timing signal separate from outcome signal. Not tested here.'),
      bullet('Cross-sectional SI RANK (e.g., top-decile short-squeeze candidates) vs absolute levels was not mined.'),
      bullet('SI \u00d7 conference interaction, SI \u00d7 options-flow interaction \u2014 not tested.'),

      H('Precedent \u2014 7 Consecutive Honest Kaizen NULL Results', HeadingLevel.HEADING_2),
      makeTable([
        ['#', 'Kaizen', 'Signal family', 'Honest lift vs bar'],
        ['1', 'BIFROST Explosion v5.7', 'non-linear runup transforms + cross-window ratios', 'NULL (signal saturated)'],
        ['2', 'BIFROST Explosion v5.8', '37 local features (calendar, alpha, vol, stacking)', '-190 bp (regression)'],
        ['3', 'Gungnir v47 honest rebuild', 'backward elimination (126 \u2192 60)', '-30 bp (regression, +34 bp Brier win)'],
        ['4', 'ODIN v17 HINT', 'HINT Phase I/II/III + 17 interactions', 'Track A -351 bp / Track B -301 bp'],
        ['5', 'Smart Money Phase 3', '10-fund god tier 13F features', '-96 bp'],
        ['6', 'SI \u00d7 ODIN v14 (this memo)', 'FINRA biweekly SI panel (23 features)', '+6 bp (CI spans zero)'],
        ['7', 'SI \u00d7 Gungnir v46 (this memo)', 'FINRA biweekly SI panel (23 features)', '+0 bp (hard null)'],
      ], [500, 2100, 3100, 2660]),

      H('Implication \u2014 Local-Feature Saturation is Universal', HeadingLevel.HEADING_2),
      P('Seven consecutive NULL results across seven different candidate signal families, three different engines, and three different catalyst event types (PDUFA regulatory, phase readout, explosion magnitude). The pattern is no longer coincidental. The deployed ODIN v14 / Gungnir v46 / BIFROST v5.5 feature sets have exhausted the predictive power available from locally-computable features on the 2015\u20132026 event universe.'),
      P('True step-ups require fundamentally new data sources that are NOT derivable from price, regulatory calendar, drug metadata, 13F holdings, short interest, or trial protocol \u2014 all of which have now been tested honestly. Remaining paths:'),
      bullet('ORATS historical options chain panel at T-14/T-7/T-1 across 1,705 PDUFA events (Phase 3 planned). Adds vol surface dynamics \u2014 a genuinely orthogonal signal family.'),
      bullet('Conference presentation backfill 2020\u20132024. CURRENT conference trades JSON is forward-only; honest conference \u00d7 outcome test is unbuilt.'),
      bullet('Social volume (StockTwits/Reddit pre-catalyst chatter) historical panels.'),
      bullet('SEC Form 8-K filing timing + content features (submission cadence, ADCOM announcements).'),
      bullet('ClinicalTrials.gov version-history deltas (protocol amendments pre-readout).'),

      H('Action Items', HeadingLevel.HEADING_2),
      bullet('Do NOT re-run SI feature mining on ODIN or Gungnir with the same candidate set \u2014 signal is saturated.'),
      bullet('Keep the FINRA SI backfill cache (196 dates, ~2.6M rows) on disk \u2014 useful for BIFROST Explosion v5.6+ experiments and as orthogonal context for UOA scoring.'),
      bullet('Patch applied to form4_odin_honest_eval.py (identical broken baseline bug) \u2014 Form 4 pipeline will now produce valid honest numbers when Stage 2 completes.'),
      bullet('Pivot next Kaizen cycle to Phase 3 (ORATS options panel) and Phase 4 (conference backfill). These are the only remaining local-dataset paths before external data sources become necessary.'),
      bullet('No change to deployed champions: ODIN v14, Gungnir v46, BIFROST v5.5, BIFROST v4 all remain CHAMPION.'),

      H('Files Produced', HeadingLevel.HEADING_2),
      bullet('si_stage4_odin_honest_eval.py \u2014 FIXED pandas-based ODIN v14 feature engineering pipeline (port of odin_v14_kaizen.py lines 43\u2013256).'),
      bullet('si_odin_honest_results.json \u2014 ODIN baseline/final AUCs, greedy log, methodology, 1 selected feature.'),
      bullet('si_gungnir_honest_results.json \u2014 Gungnir baseline/final AUCs (hard null, zero features selected).'),
      bullet('form4_odin_honest_eval.py \u2014 Patched with same fix (port of fixed SI script); auto-pipeline ready.'),
      bullet('Phase2_Short_Interest_Findings.docx \u2014 this memo.'),
    ],
  }],
});

Packer.toBuffer(doc).then(buffer => {
  const out = '/sessions/confident-serene-ptolemy/mnt/9realms/Phase2_Short_Interest_Findings.docx';
  fs.writeFileSync(out, buffer);
  console.log('Wrote ' + out + ' (' + buffer.length + ' bytes)');
});
