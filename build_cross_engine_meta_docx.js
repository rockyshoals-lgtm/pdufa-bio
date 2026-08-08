const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  Table, TableRow, TableCell, WidthType, BorderStyle, ShadingType,
  PageOrientation, LevelFormat, PageBreak
} = require("docx");

const results = JSON.parse(fs.readFileSync("/sessions/confident-serene-ptolemy/mnt/9realms/cross_engine_meta_v1_results.json", "utf8"));

const BORDER = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const BORDERS = { top: BORDER, bottom: BORDER, left: BORDER, right: BORDER };

const pt = (size, bold=false, color=null) => ({ size, bold, font: "Arial", ...(color?{color}:{}) });

function P(text, opts={}) {
  const { bold=false, size=22, color=null, align=null, spaceAfter=80, spaceBefore=0 } = opts;
  return new Paragraph({
    alignment: align,
    spacing: { after: spaceAfter, before: spaceBefore },
    children: [ new TextRun({ text, bold, size, font: "Arial", ...(color?{color}:{}) }) ],
  });
}

function H1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 280, after: 160 },
    children: [ new TextRun({ text, bold: true, size: 32, font: "Arial" }) ],
  });
}

function H2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 220, after: 120 },
    children: [ new TextRun({ text, bold: true, size: 26, font: "Arial" }) ],
  });
}

function bullet(text) {
  return new Paragraph({
    numbering: { reference: "bullets", level: 0 },
    spacing: { after: 40 },
    children: [ new TextRun({ text, size: 22, font: "Arial" }) ],
  });
}

function cell(text, opts={}) {
  const { bold=false, fill=null, width=2000, align=AlignmentType.LEFT } = opts;
  return new TableCell({
    borders: BORDERS,
    width: { size: width, type: WidthType.DXA },
    ...(fill ? { shading: { fill, type: ShadingType.CLEAR } } : {}),
    margins: { top: 80, bottom: 80, left: 120, right: 120 },
    children: [
      new Paragraph({
        alignment: align,
        children: [ new TextRun({ text, bold, size: 20, font: "Arial" }) ],
      }),
    ],
  });
}

function fmt(num, places=4, pct=false, sign=false) {
  if (num === null || num === undefined) return "–";
  const v = pct ? num * 100 : num;
  const s = v.toFixed(places);
  if (sign && num > 0) return "+" + s + (pct ? "%" : "");
  return s + (pct ? "%" : "");
}

const H = results.headline;
const O = results.odin;
const B = results.bifrost;
const M = results.meta;

const children = [];

children.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { after: 120 },
  children: [ new TextRun({ text: "Cross-Engine Meta v1.0 — ODIN × BIFROST", bold: true, size: 36, font: "Arial" }) ],
}));
children.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { after: 240 },
  children: [ new TextRun({ text: "Honest Cross-Engine Stacking — NULL Result", italics: true, size: 24, font: "Arial", color: "C0392B" }) ],
}));
children.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { after: 320 },
  children: [ new TextRun({ text: "9 Realms · April 20, 2026", size: 20, font: "Arial", color: "666666" }) ],
}));

children.push(H1("Headline"));
children.push(P("The cross-engine meta-learner — stacking honest ODIN v14 approval probabilities with honest BIFROST v5.x explosion probabilities on the same PDUFA events — does NOT beat an ODIN-only baseline on the held-out 2025+ test set. Test AUC lift is +0.0025 with CI95 [-0.0038, +0.0090] and P(lift>0) = 0.776. Verdict: NULL."));
children.push(P("This is the 5th consecutive honest kaizen to return NULL (BIFROST Explosion v5.7, v5.8; Gungnir v47; ODIN v17 HINT; Cross-engine meta v1). The pattern strongly confirms that locally-computable signal families on the existing panel are saturated."));

children.push(H2("Key numbers"));

const tblHead = new Table({
  width: { size: 9360, type: WidthType.DXA },
  columnWidths: [3360, 2000, 2000, 2000],
  rows: [
    new TableRow({ children: [
      cell("Metric",            { bold: true, fill: "2E75B6", width: 3360 }),
      cell("ODIN-only",          { bold: true, fill: "2E75B6", width: 2000 }),
      cell("META",               { bold: true, fill: "2E75B6", width: 2000 }),
      cell("Lift (META − ODIN)", { bold: true, fill: "2E75B6", width: 2000 }),
    ] }),
    new TableRow({ children: [
      cell("Test AUC",                  { width: 3360 }),
      cell(fmt(H.odin_only_test_auc, 4), { width: 2000, align: AlignmentType.CENTER }),
      cell(fmt(H.meta_test_auc, 4),      { width: 2000, align: AlignmentType.CENTER }),
      cell(fmt(H.lift_mean, 4, false, true), { width: 2000, align: AlignmentType.CENTER }),
    ] }),
    new TableRow({ children: [
      cell("Test AUC CI95", { width: 3360 }),
      cell(`[${fmt(H.odin_only_test_auc_ci95[0], 4)}, ${fmt(H.odin_only_test_auc_ci95[1], 4)}]`, { width: 2000, align: AlignmentType.CENTER }),
      cell(`[${fmt(H.meta_test_auc_ci95[0], 4)}, ${fmt(H.meta_test_auc_ci95[1], 4)}]`, { width: 2000, align: AlignmentType.CENTER }),
      cell(`[${fmt(H.lift_ci95[0], 4, false, true)}, ${fmt(H.lift_ci95[1], 4, false, true)}]`, { width: 2000, align: AlignmentType.CENTER }),
    ] }),
    new TableRow({ children: [
      cell("Test Brier", { width: 3360 }),
      cell(fmt(H.odin_only_test_brier, 4), { width: 2000, align: AlignmentType.CENTER }),
      cell(fmt(H.meta_test_brier, 4),      { width: 2000, align: AlignmentType.CENTER }),
      cell(fmt(H.meta_test_brier - H.odin_only_test_brier, 4, false, true), { width: 2000, align: AlignmentType.CENTER }),
    ] }),
    new TableRow({ children: [
      cell("P(lift > 0)", { width: 3360 }),
      cell("–", { width: 2000, align: AlignmentType.CENTER }),
      cell("–", { width: 2000, align: AlignmentType.CENTER }),
      cell(fmt(H.p_lift_positive, 3), { width: 2000, align: AlignmentType.CENTER }),
    ] }),
  ],
});
children.push(tblHead);

children.push(P(" ", { spaceAfter: 120 }));
children.push(P("CI95 from bootstrap with n_boot=2000, seed=42, percentile method. Meta beats ODIN on point estimate (+25 bp AUC, −28 bp Brier) but the lift CI crosses zero and P(lift>0) falls below the 0.90 SHIP threshold.", { size: 20 }));

children.push(H1("Methodology"));

children.push(H2("Unified honest 3-way split"));
children.push(bullet("Train: catalyst date ≤ 2022-12-31"));
children.push(bullet("Val: catalyst date in 2023-01-01 … 2024-12-31"));
children.push(bullet("Holdout (test): catalyst date ≥ 2025-01-01"));
children.push(bullet("Split anchored on ODIN cutoffs for consistency with ODIN v14 honest. BIFROST's native schema (train ≤2023 / val 2024 / test ≥2025) is replaced by this unified schema — any BIFROST-train-2023 event becomes unified-val here."));

children.push(H2("Base learner 1 — ODIN v14 honest"));
children.push(bullet(`51 features (full v14 deployed feature list), LogisticRegression(C=0.01, lbfgs, class_weight='balanced')`));
children.push(bullet(`C=0.01 is the odin_v14_honest.py winner — 10× stronger regularization than the deployed C=0.10 that leaked during Kaizen`));
children.push(bullet(`Forward-only temporal feature engineering (defaultdict accumulators frozen on train, applied to val/test)`));
children.push(bullet(`Event counts — train: ${O.train_n}, val: ${O.val_n}, test: ${O.test_n}`));
children.push(bullet(`Full ODIN val AUC = ${fmt(O.val_auc_full,4)}, full ODIN test AUC = ${fmt(O.test_auc_full,4)}`));

children.push(H2("Base learner 2 — BIFROST Explosion honest"));
children.push(bullet(`57 features (V54_BASE: surprise, market cap tiers, runup windows, XBI sector, short interest, ODIN regulatory pass-throughs, interactions)`));
children.push(bullet(`Target: big_move = 1 if |post_1d| > 25% else 0 — predicts explosion, not approval`));
children.push(bullet(`Short interest features gated by si_cutoff guard to prevent lookahead on pre-snapshot events`));
children.push(bullet(`C swept on VAL over [0.01, 0.03, 0.05, 0.1, 0.25, 0.5, 1.0]. Winner: C=${B.C}, val AUC = ${fmt(B.val_auc,4)}`));
children.push(bullet(`Event counts — train: ${B.train_n}, val: ${B.val_n}, test: ${B.test_n}`));
children.push(bullet(`BIFROST test AUC on explosion target = ${fmt(B.test_auc_explosion_target,4)} — internally consistent with v5.x honest range`));

children.push(H2("Meta-learner"));
children.push(bullet("6 meta features: odin_p, bifrost_p, |odin_p − bifrost_p| (disagreement), odin_p × bifrost_p (interaction), hi_both = 1 if odin_p>0.7 AND bf_p>0.15, hi_odin_lo_bf = 1 if odin_p>0.85 AND bf_p<0.05"));
children.push(bullet("Merge key: (TICKER upper, catalyst_date[:10]). Merged intersection — train: " + M.merged_train_n + ", val: " + M.merged_val_n + ", test: " + M.merged_test_n));
children.push(bullet("Meta fitted on VAL predictions (stacking discipline — not train, because base learners are in-sample on train)"));
children.push(bullet("C sweep on VAL: [0.1, 1.0, 10.0, 100.0] via 5-fold cross_val_score. Winner: C=" + M.best_C + ", CV AUC = " + fmt(M.best_cv_val_auc,4)));
children.push(bullet("TEST touched exactly once. Bootstrap CI with n_boot=2000, seed=42, percentile 2.5/97.5"));

children.push(H2("Meta coefficients"));

const tblCoef = new Table({
  width: { size: 9360, type: WidthType.DXA },
  columnWidths: [4680, 2340, 2340],
  rows: [
    new TableRow({ children: [
      cell("Meta feature", { bold: true, fill: "2E75B6", width: 4680 }),
      cell("Coefficient",  { bold: true, fill: "2E75B6", width: 2340 }),
      cell("Sign / role",  { bold: true, fill: "2E75B6", width: 2340 }),
    ] }),
    new TableRow({ children: [
      cell("odin_p",        { width: 4680 }),
      cell(fmt(M.coefficients.odin_p, 4, false, true),     { width: 2340, align: AlignmentType.CENTER }),
      cell("DOMINANT +",    { width: 2340, align: AlignmentType.CENTER }),
    ] }),
    new TableRow({ children: [
      cell("bifrost_p",     { width: 4680 }),
      cell(fmt(M.coefficients.bifrost_p, 4, false, true),  { width: 2340, align: AlignmentType.CENTER }),
      cell("near zero",     { width: 2340, align: AlignmentType.CENTER }),
    ] }),
    new TableRow({ children: [
      cell("abs_diff (|ODIN − BF|)", { width: 4680 }),
      cell(fmt(M.coefficients.abs_diff, 4, false, true),   { width: 2340, align: AlignmentType.CENTER }),
      cell("disagreement penalty −", { width: 2340, align: AlignmentType.CENTER }),
    ] }),
    new TableRow({ children: [
      cell("interact (ODIN × BF)",   { width: 4680 }),
      cell(fmt(M.coefficients.interact, 4, false, true),   { width: 2340, align: AlignmentType.CENTER }),
      cell("−",                      { width: 2340, align: AlignmentType.CENTER }),
    ] }),
    new TableRow({ children: [
      cell("hi_both",       { width: 4680 }),
      cell(fmt(M.coefficients.hi_both, 4, false, true),    { width: 2340, align: AlignmentType.CENTER }),
      cell("small +",       { width: 2340, align: AlignmentType.CENTER }),
    ] }),
    new TableRow({ children: [
      cell("hi_odin_lo_bf", { width: 4680 }),
      cell(fmt(M.coefficients.hi_odin_lo_bf, 4, false, true), { width: 2340, align: AlignmentType.CENTER }),
      cell("≈ zero",        { width: 2340, align: AlignmentType.CENTER }),
    ] }),
    new TableRow({ children: [
      cell("intercept",     { width: 4680 }),
      cell(fmt(M.intercept, 4, false, true), { width: 2340, align: AlignmentType.CENTER }),
      cell("baseline",      { width: 2340, align: AlignmentType.CENTER }),
    ] }),
  ],
});
children.push(tblCoef);

children.push(H1("Why it didn't lift"));

children.push(bullet("ODIN dominates the meta (coef +2.79). BIFROST explosion probability contributes only +0.11 — the raw explosion probability is nearly orthogonal to approval probability in directional contribution but carries almost no marginal signal about approval once ODIN is present."));
children.push(bullet("Disagreement signal (abs_diff coef −1.14) is negative — events where ODIN and BIFROST disagree get DERATED, consistent with the hypothesis that the meta shrinks confidence where engines conflict. But the magnitude of the lift from this derating is within bootstrap noise."));
children.push(bullet("The hi_both quadrant indicator (+0.31) captures a small boost when both engines agree on high probability, but fires in only a small subset of events — insufficient to produce a robust test-set lift."));
children.push(bullet("Target orthogonality eats the lift: BIFROST predicts |post_1d|>25% (magnitude/variance); ODIN predicts approval (direction). An explosive stock can be an explosive approval OR an explosive CRL — BIFROST's raw probability cannot distinguish these without structural features ODIN already captures (btd, ppm_flag, crl_rate, sponsor_win_rate, resub_class)."));
children.push(bullet("Merge coverage is good (intersection 659/676/326 = 76-95% of each engine's own split) so this is NOT a sample-size artifact."));

children.push(H1("Precedent — 5th consecutive honest NULL"));

const tblNulls = new Table({
  width: { size: 9360, type: WidthType.DXA },
  columnWidths: [3120, 3120, 3120],
  rows: [
    new TableRow({ children: [
      cell("Kaizen",            { bold: true, fill: "2E75B6", width: 3120 }),
      cell("Signal family",     { bold: true, fill: "2E75B6", width: 3120 }),
      cell("Verdict",           { bold: true, fill: "2E75B6", width: 3120 }),
    ] }),
    new TableRow({ children: [
      cell("BIFROST Explosion v5.7", { width: 3120 }),
      cell("Non-linear transforms + cross-window ratios", { width: 3120 }),
      cell("NULL — absorbed by v5.5", { width: 3120 }),
    ] }),
    new TableRow({ children: [
      cell("BIFROST Explosion v5.8", { width: 3120 }),
      cell("37 new local features + architecture sweep", { width: 3120 }),
      cell("NULL — test 0.8671 vs 0.8861 bar", { width: 3120 }),
    ] }),
    new TableRow({ children: [
      cell("Gungnir v47",            { width: 3120 }),
      cell("Backward elimination + honest split",  { width: 3120 }),
      cell("NULL — final HO 0.7521 vs 0.7551", { width: 3120 }),
    ] }),
    new TableRow({ children: [
      cell("ODIN v17 HINT",          { width: 3120 }),
      cell("HINT Phase I/II/III + 17 interactions", { width: 3120 }),
      cell("NULL — test 0.8694 vs 0.8995", { width: 3120 }),
    ] }),
    new TableRow({ children: [
      cell("Cross-engine meta v1", { width: 3120, fill: "FDE9D9" }),
      cell("ODIN × BIFROST stacking",   { width: 3120, fill: "FDE9D9" }),
      cell("NULL — lift +0.0025 CI [-0.0038, +0.0090]", { width: 3120, fill: "FDE9D9" }),
    ] }),
  ],
});
children.push(tblNulls);
children.push(P(" ", { spaceAfter: 120 }));

children.push(H1("What this tells us"));
children.push(bullet("Local-feature and local-stacking edges are saturated across ODIN, BIFROST, Gungnir. The sixth-order polynomial of pre-catalyst info that's locally computable has been wrung out."));
children.push(bullet("True step-ups now require NEW external data: historical short-interest time series, ORATS T-14 options panel at scale, 13F quarter-boundary concentration jumps, pre-catalyst social volume (SENTINEL historical backfill), submission/ADCOM metadata streams."));
children.push(bullet("The cross-engine score scorecard ordering is preserved: ODIN v14 honest AUC ≈ 0.9099, Gungnir v46 honest HO AUC ≈ 0.7551, BIFROST Explosion v5.x honest ≈ 0.86-0.89. These remain the production numbers for Q2 2026 portfolio ranking."));
children.push(bullet("v1.0 of this meta is SHELVED, not deployed. No changes to MCP. Production scores remain unchanged."));

children.push(H1("Files"));
children.push(bullet("cross_engine_meta_v1.py — 5-step honest pipeline (ODIN → BIFROST → merge → meta on VAL → one-shot TEST with bootstrap)"));
children.push(bullet("cross_engine_meta_v1_results.json — full deploy-format results"));
children.push(bullet("cross_engine_meta_v1.log — execution log with per-step metrics"));
children.push(bullet("Cross_Engine_Meta_v1_Findings.docx — this memo"));

children.push(H1("Next kaizen priorities"));
children.push(bullet("1. HISTORICAL SHORT INTEREST (FINRA biweekly 2020-2026). Removes BIFROST's SI lookahead and unblocks a proper T-1-compliant SI time series feature. Probably +50-100 bp on BIFROST Explosion."));
children.push(bullet("2. ORATS T-14 OPTIONS PANEL at scale across 1,704 events. Unlocks options-flow features in ODIN/BIFROST. Term-structure tilt, put-call delta, event-expiry concentration."));
children.push(bullet("3. CONFERENCE BACKFILL 2020-2024. Currently only Q2 2026 forward-looking abstracts are structured — historical conference × explosion test is blocked without this."));
children.push(bullet("4. SUBMISSION + ADCOM METADATA STREAM. Public FDA briefing docs, Advisory Committee voting records — a T-1-compliant but underused data source for ODIN."));
children.push(bullet("5. SENTINEL SOCIAL VOLUME BACKFILL. Pre-catalyst StockTwits/Reddit chatter — proxy for retail positioning intensity orthogonal to options flow."));

const doc = new Document({
  creator: "9 Realms",
  title: "Cross-Engine Meta v1.0 Findings",
  styles: {
    default: { document: { run: { font: "Arial", size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, font: "Arial" },
        paragraph: { spacing: { before: 240, after: 160 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 26, bold: true, font: "Arial" },
        paragraph: { spacing: { before: 200, after: 120 }, outlineLevel: 1 } },
    ],
  },
  numbering: {
    config: [
      { reference: "bullets",
        levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
    ],
  },
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 },
      },
    },
    children,
  }],
});

Packer.toBuffer(doc).then(buf => {
  const out = "/sessions/confident-serene-ptolemy/mnt/9realms/Cross_Engine_Meta_v1_Findings.docx";
  fs.writeFileSync(out, buf);
  console.log("WROTE " + out);
});
