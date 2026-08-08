// BIFROST v4 Winsorized Retrain Findings Memo
// Output: BIFROST_v4_Winsorized_Findings.docx
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, LevelFormat, TabStopType, TabStopPosition,
  HeadingLevel, BorderStyle, WidthType, ShadingType, PageNumber, PageBreak,
  PageOrientation
} = require('/sessions/confident-serene-ptolemy/.npm-global/lib/node_modules/docx');
const fs = require('fs');

const results = JSON.parse(fs.readFileSync('/sessions/confident-serene-ptolemy/mnt/9realms/bifrost_v4_winsorized_results.json', 'utf8'));

const BORDER = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const BORDERS = { top: BORDER, bottom: BORDER, left: BORDER, right: BORDER };
const HEADER_FILL = "D5E8F0";
const ALT_FILL = "F6F9FC";

function P(text, opts = {}) {
  return new Paragraph({
    children: [new TextRun({ text, bold: opts.bold, italics: opts.italics, size: opts.size, color: opts.color })],
    spacing: { before: opts.before ?? 60, after: opts.after ?? 60 },
    alignment: opts.align,
  });
}

function H1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    children: [new TextRun({ text, bold: true, size: 32 })],
    spacing: { before: 240, after: 120 },
  });
}

function H2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    children: [new TextRun({ text, bold: true, size: 26 })],
    spacing: { before: 200, after: 80 },
  });
}

function cell(text, opts = {}) {
  return new TableCell({
    borders: BORDERS,
    width: { size: opts.width ?? 1560, type: WidthType.DXA },
    shading: opts.fill ? { fill: opts.fill, type: ShadingType.CLEAR } : undefined,
    margins: { top: 80, bottom: 80, left: 120, right: 120 },
    children: [new Paragraph({
      alignment: opts.align ?? AlignmentType.LEFT,
      children: [new TextRun({ text: String(text), bold: opts.bold, size: opts.size ?? 20 })],
    })],
  });
}

// ----- Main three-mode comparison table -----
function fmt(n, dec = 2) {
  if (n === null || n === undefined) return "—";
  if (typeof n === "number") return n.toFixed(dec);
  return String(n);
}

function buildComparisonTable() {
  const COLS = [1200, 900, 900, 1100, 1100, 1100, 1100, 1960];
  const header = new TableRow({
    children: [
      cell("Mode", { width: COLS[0], fill: HEADER_FILL, bold: true }),
      cell("Kelly", { width: COLS[1], fill: HEADER_FILL, bold: true, align: AlignmentType.CENTER }),
      cell("LGB", { width: COLS[2], fill: HEADER_FILL, bold: true, align: AlignmentType.CENTER }),
      cell("Trades", { width: COLS[3], fill: HEADER_FILL, bold: true, align: AlignmentType.RIGHT }),
      cell("Win Rate", { width: COLS[4], fill: HEADER_FILL, bold: true, align: AlignmentType.RIGHT }),
      cell("Sharpe", { width: COLS[5], fill: HEADER_FILL, bold: true, align: AlignmentType.RIGHT }),
      cell("Max DD", { width: COLS[6], fill: HEADER_FILL, bold: true, align: AlignmentType.RIGHT }),
      cell("Final Value", { width: COLS[7], fill: HEADER_FILL, bold: true, align: AlignmentType.RIGHT }),
    ],
  });

  const rows = [header];
  const modes = ["none", "train_only", "full"];
  let idx = 0;
  for (const mode of modes) {
    for (const r of results.results_by_mode[mode]) {
      const fill = (idx++ % 2 === 0) ? undefined : ALT_FILL;
      rows.push(new TableRow({
        children: [
          cell(mode, { width: COLS[0], fill }),
          cell(fmt(r.kelly), { width: COLS[1], fill, align: AlignmentType.CENTER }),
          cell(r.use_lgb ? "True" : "False", { width: COLS[2], fill, align: AlignmentType.CENTER }),
          cell(r.n_trades, { width: COLS[3], fill, align: AlignmentType.RIGHT }),
          cell((r.win_rate * 100).toFixed(2) + "%", { width: COLS[4], fill, align: AlignmentType.RIGHT }),
          cell(fmt(r.sharpe), { width: COLS[5], fill, align: AlignmentType.RIGHT }),
          cell(r.max_drawdown.toFixed(2) + "%", { width: COLS[6], fill, align: AlignmentType.RIGHT }),
          cell("$" + (r.final_value / 1e6).toFixed(2) + "M", { width: COLS[7], fill, align: AlignmentType.RIGHT }),
        ],
      }));
    }
  }

  return new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: COLS,
    rows,
  });
}

function buildVerdictTable() {
  const COLS = [1400, 2200, 1400, 1400, 2960];
  const v = results.verdicts;
  const header = new TableRow({
    children: [
      cell("Mode", { width: COLS[0], fill: HEADER_FILL, bold: true }),
      cell("Best Config", { width: COLS[1], fill: HEADER_FILL, bold: true }),
      cell("Sharpe", { width: COLS[2], fill: HEADER_FILL, bold: true, align: AlignmentType.RIGHT }),
      cell("Max DD", { width: COLS[3], fill: HEADER_FILL, bold: true, align: AlignmentType.RIGHT }),
      cell("Auto-Verdict", { width: COLS[4], fill: HEADER_FILL, bold: true }),
    ],
  });
  const rows = [header];
  for (const mode of ["train_only", "full"]) {
    const r = v[mode];
    rows.push(new TableRow({
      children: [
        cell(mode, { width: COLS[0] }),
        cell(r.best_config, { width: COLS[1] }),
        cell(fmt(r.sharpe) + " (Δ " + fmt(r.sharpe_delta_vs_v4) + ")", { width: COLS[2], align: AlignmentType.RIGHT }),
        cell(r.max_dd.toFixed(2) + "%", { width: COLS[3], align: AlignmentType.RIGHT }),
        cell(r.verdict, { width: COLS[4] }),
      ],
    }));
  }
  return new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: COLS,
    rows,
  });
}

// ----- Document assembly -----
const children = [
  new Paragraph({
    children: [new TextRun({ text: "BIFROST v4 Winsorized Retrain — Findings Memo", bold: true, size: 40 })],
    spacing: { before: 0, after: 120 },
  }),
  new Paragraph({
    children: [new TextRun({ text: "Honest retest under [-50%, +100%] winsorization. v4.0 remains CHAMPION.", italics: true, size: 22, color: "666666" })],
    spacing: { before: 0, after: 80 },
  }),
  new Paragraph({
    children: [new TextRun({ text: "Date: April 19, 2026  |  Author: Claude (9 Realms ML)  |  Status: v4.0 REMAINS DEPLOYED", size: 20 })],
    spacing: { before: 0, after: 240 },
  }),

  H1("Executive Summary"),
  P("BIFROST v4 was retrained with training labels clipped to [-50%, +100%] to test whether the deployed Sharpe 5.45 / $18.1M final value is being propped up by penny-stock outliers. Three modes were tested: NONE (control, raw returns), TRAIN_ONLY (training targets clipped, backtest uses raw P&L), and FULL (both clipped — stress-test of capped upside)."),
  P("Bottom line: training-label winsorization moves Sharpe by -2bp (noise), tightens max DD by 1.1pp, and costs $1.13M (-6%) in compounded final value. There is no accuracy win to ship. v4.0 (raw training, Kelly=0.5, LGB=True, Sharpe 5.45, FV $18.12M) REMAINS DEPLOYED as the BIFROST magnitude champion."),
  P("The FULL mode Sharpe (7.11) looks like a win but is a diagnostic artifact — artificially capping exits at +100% halves the strategy's compounded value ($9.63M vs $18.12M). Higher Sharpe on fewer dollars is not a shippable improvement."),

  H1("Three-Mode Comparison (12 configs)"),
  buildComparisonTable(),
  P(" "),
  P("Baseline v4.0 deployed: Sharpe 5.45, Win Rate 70.8%, Max DD -4.9%, Final Value $18.1M, 910 trades.", { italics: true, size: 20 }),
  P("Winsor bounds: [-50.0%, +100.0%]. All numbers reproducible via bifrost_v4_winsorized.py.", { italics: true, size: 20 }),

  H1("Auto-Verdict (from script) vs Honest Interpretation"),
  buildVerdictTable(),
  P(" "),
  P("The script auto-flagged FULL mode as \"SHIP as v4.1 WINSORIZED\" because Sharpe 7.11 ≥ 5.45 and DD tightened by 1pp. This verdict is misleading.", { italics: true }),

  H1("Why FULL Mode is NOT a Ship Candidate"),
  P("FULL mode clips BOTH the training labels AND the backtest exits at +100%. Clipping exits is not a real strategy — it's equivalent to saying \"sell every trade that goes above 100% gain at the cap\". In reality, the top-decile exits on small-cap PDUFA events deliver >100% moves. Capping them artificially inflates the ratio of realized-return to standard deviation (that's the Sharpe gain) while deleting the right-tail dollars that compound the portfolio."),
  P("Evidence:"),
  P("  • NONE (Kelly=0.5, LGB=True): FV = $18.12M, Sharpe = 5.45", { size: 20 }),
  P("  • FULL (Kelly=0.5, LGB=True): FV = $9.63M, Sharpe = 7.11", { size: 20 }),
  P("  • Same 910 trades, same win rate (70.8% → 71.3%, +0.5pp)", { size: 20 }),
  P("  • FV delta: -$8.49M (-46.8%) for +1.66 Sharpe", { size: 20 }),
  P("A Sharpe gain that costs $8.49M of compounded capital is not an accuracy improvement — it's a stress-test diagnostic showing that v4's dollar P&L depends on uncapped upside."),

  H1("Why TRAIN_ONLY Is the Only Honest Comparison"),
  P("TRAIN_ONLY is the theoretically correct test: cap outliers in the TRAINING signal (to test whether the magnitude model is overfit to penny-stock tails) while letting the BACKTEST see the real market returns. Under this test:"),
  P("  • Sharpe: 5.43 vs 5.45 → -2bp (noise, within stability band)", { size: 20 }),
  P("  • Max DD: -4.1% vs -4.9% → +0.8pp tighter (genuine improvement)", { size: 20 }),
  P("  • Win Rate: 71.3% vs 70.8% → +0.5pp (marginal)", { size: 20 }),
  P("  • Final Value: $16.99M vs $18.12M → -$1.13M (-6.2%)", { size: 20 }),
  P("Interpretation: the 208 training rows with raw returns >+100% and the 267 with returns <-50% are doing genuine work. The model learns magnitude calibration from these tails; clipping them loses 6% of compounded FV for a 1pp DD tightening. For drawdown-sensitive accounts this tradeoff may be desirable — TRAIN_ONLY is worth documenting as an OPTIONAL variant. But it should not replace v4.0 as the default deploy."),

  H1("Pipeline Reproduction Validation"),
  P("NONE mode with Kelly=0.5, LGB=True produced Sharpe 5.45, WR 70.77%, DD -4.9%, FV $18,119,273 — an EXACT match to the deployed v4 headline numbers (5.45 / 70.8% / -4.9% / $18.1M). This confirms bifrost_v4_winsorized.py is a clean methodology variant of bifrost_v4_kaizen.py with no pipeline drift, and that the TRAIN_ONLY and FULL deltas measured above are real signal — not implementation noise."),

  H1("Ship Decision"),
  P("KEEP v4.0 DEPLOYED as BIFROST magnitude champion.", { bold: true }),
  P("  • Kelly = 0.5", { size: 20 }),
  P("  • LGB = True (triple ensemble Ridge 30% / XGB 35% / LGB 35%)", { size: 20 }),
  P("  • Raw training labels (no winsorization)", { size: 20 }),
  P("  • Deployed Sharpe 5.45, FV $18.12M, DD -4.9%", { size: 20 }),
  P("Log this winsorized retrain as a KAIZEN NULL RESULT. Do not create a v4.1 deploy artifact. If a drawdown-constrained account variant is ever needed, use TRAIN_ONLY bounds [-50, +100] with the explicit cost of -6% FV disclosed."),

  H1("What We Actually Learned"),
  P("1. v4's magnitude ensemble is not being propped up by penny-stock label noise. Clipping training tails at a strict [-50%, +100%] only moves Sharpe by noise (-2bp)."),
  P("2. Right-tail training labels (>100% returns on small-cap PDUFA events) carry genuine magnitude signal. Removing them costs $1.13M in compounded FV."),
  P("3. Max DD responds modestly (+1pp tighter) to training-label winsorization, consistent with the hypothesis that outlier training labels push position sizes slightly heavy in tail regimes."),
  P("4. Sharpe is not the right optimization target when tails are capped — it rewards capping upside. Always report final value alongside Sharpe for magnitude models."),
  P("5. The auto-verdict logic in bifrost_v4_winsorized.py needs a dollar-P&L guardrail: \"don't ship if FV drops >10% from baseline\" would have flagged the FULL mode correctly."),

  H1("Files"),
  P("  • bifrost_v4_winsorized.py — winsorized retrain pipeline (3 modes × 4 configs)", { size: 20 }),
  P("  • bifrost_v4_winsorized_results.json — full 12-result matrix + verdicts + methodology", { size: 20 }),
  P("  • BIFROST_v4_Winsorized_Findings.docx — this memo", { size: 20 }),

  H1("Next in Sprint"),
  P("Task #58 — Gungnir v47 honest rebuild under 3-way split, val-only selection, Conference as proper feature. Bar: test AUC > v46 honest 0.7551."),
  P("Task #59 — BIFROST Explosion v5.8 new signal families (options flow, conference × explosion, 13F, SI time series). Bar: v5.5 honest ~0.8861."),
];

const doc = new Document({
  styles: {
    default: { document: { run: { font: "Arial", size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, font: "Arial" },
        paragraph: { spacing: { before: 240, after: 120 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 26, bold: true, font: "Arial" },
        paragraph: { spacing: { before: 200, after: 80 }, outlineLevel: 1 } },
    ],
  },
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 },
      },
    },
    headers: {
      default: new Header({ children: [new Paragraph({
        alignment: AlignmentType.RIGHT,
        children: [new TextRun({ text: "BIFROST v4 Winsorized Retrain — 9 Realms", size: 18, color: "888888" })],
      })] }),
    },
    footers: {
      default: new Footer({ children: [new Paragraph({
        alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: "Page ", size: 18, color: "888888" }), new TextRun({ children: [PageNumber.CURRENT], size: 18, color: "888888" })],
      })] }),
    },
    children,
  }],
});

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync('/sessions/confident-serene-ptolemy/mnt/9realms/BIFROST_v4_Winsorized_Findings.docx', buf);
  console.log("WROTE BIFROST_v4_Winsorized_Findings.docx (" + buf.length + " bytes)");
});
