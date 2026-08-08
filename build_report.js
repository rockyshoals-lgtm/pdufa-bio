const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
        Header, Footer, AlignmentType, LevelFormat,
        TableOfContents, HeadingLevel, BorderStyle, WidthType, ShadingType,
        PageNumber, PageBreak } = require('docx');
const fs = require('fs');

// ── Table helpers ──────────────────────────────────────────────────────
const border = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const borders = { top: border, bottom: border, left: border, right: border };
const cellMargins = { top: 60, bottom: 60, left: 100, right: 100 };

function headerCell(text, width) {
  return new TableCell({
    borders,
    width: { size: width, type: WidthType.DXA },
    shading: { fill: "1B4F72", type: ShadingType.CLEAR },
    margins: cellMargins,
    verticalAlign: "center",
    children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [
      new TextRun({ text, bold: true, font: "Arial", size: 18, color: "FFFFFF" })
    ]})]
  });
}

function dataCell(text, width, opts = {}) {
  return new TableCell({
    borders,
    width: { size: width, type: WidthType.DXA },
    shading: opts.shading ? { fill: opts.shading, type: ShadingType.CLEAR } : undefined,
    margins: cellMargins,
    children: [new Paragraph({
      alignment: opts.align || AlignmentType.CENTER,
      children: [new TextRun({ text: String(text), font: "Arial", size: 18, bold: opts.bold || false,
        color: opts.color || "333333" })]
    })]
  });
}

function makeTable(headers, rows, colWidths) {
  const totalWidth = colWidths.reduce((a, b) => a + b, 0);
  return new Table({
    width: { size: totalWidth, type: WidthType.DXA },
    columnWidths: colWidths,
    rows: [
      new TableRow({ children: headers.map((h, i) => headerCell(h, colWidths[i])) }),
      ...rows.map(row => new TableRow({
        children: row.map((cell, i) => {
          if (typeof cell === 'object' && cell.text !== undefined) {
            return dataCell(cell.text, colWidths[i], cell);
          }
          return dataCell(cell, colWidths[i]);
        })
      }))
    ]
  });
}

// ── Text helpers ─────────────────────────────────────────────────────
function h1(text) { return new Paragraph({ heading: HeadingLevel.HEADING_1, spacing: { before: 360, after: 200 }, children: [new TextRun({ text, font: "Arial" })] }); }
function h2(text) { return new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: { before: 280, after: 160 }, children: [new TextRun({ text, font: "Arial" })] }); }
function h3(text) { return new Paragraph({ heading: HeadingLevel.HEADING_3, spacing: { before: 200, after: 120 }, children: [new TextRun({ text, font: "Arial" })] }); }
function p(text, opts = {}) {
  return new Paragraph({
    spacing: { after: opts.after || 160 },
    alignment: opts.align || AlignmentType.JUSTIFIED,
    children: [new TextRun({ text, font: "Arial", size: 22, bold: opts.bold, italics: opts.italics, color: opts.color })]
  });
}
function pMulti(runs) {
  return new Paragraph({
    spacing: { after: 160 },
    alignment: AlignmentType.JUSTIFIED,
    children: runs.map(r => new TextRun({ text: r.text, font: "Arial", size: 22, bold: r.bold, italics: r.italics, color: r.color }))
  });
}

// ── BUILD DOCUMENT ───────────────────────────────────────────────────
const doc = new Document({
  styles: {
    default: { document: { run: { font: "Arial", size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, font: "Arial", color: "1B4F72" },
        paragraph: { spacing: { before: 360, after: 240 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 26, bold: true, font: "Arial", color: "2E75B6" },
        paragraph: { spacing: { before: 280, after: 180 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 23, bold: true, font: "Arial", color: "5B9BD5" },
        paragraph: { spacing: { before: 200, after: 120 }, outlineLevel: 2 } },
    ]
  },
  numbering: {
    config: [
      { reference: "bullets",
        levels: [{ level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
    ]
  },
  sections: [
    // ── TITLE PAGE ──
    {
      properties: {
        page: {
          size: { width: 12240, height: 15840 },
          margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 }
        }
      },
      children: [
        new Paragraph({ spacing: { before: 3600 } }),
        new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 400 }, children: [
          new TextRun({ text: "PDUFA & Phase Readout Runup Dynamics:", font: "Arial", size: 40, bold: true, color: "1B4F72" })
        ]}),
        new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 400 }, children: [
          new TextRun({ text: "An Empirical Analysis of 1,451 FDA Catalyst Events", font: "Arial", size: 32, color: "2E75B6" })
        ]}),
        new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 }, children: [
          new TextRun({ text: "Tier-Stratified Timing Optimization for the ODIN Scoring Framework", font: "Arial", size: 24, italics: true, color: "5B9BD5" })
        ]}),
        new Paragraph({ spacing: { before: 1200 } }),
        new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 100 }, children: [
          new TextRun({ text: "ODIN Quantitative Research", font: "Arial", size: 24, bold: true })
        ]}),
        new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 100 }, children: [
          new TextRun({ text: "pdufa.bio", font: "Arial", size: 22, color: "2E75B6" })
        ]}),
        new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 100 }, children: [
          new TextRun({ text: "March 2026", font: "Arial", size: 22 })
        ]}),
        new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 600, after: 200 }, children: [
          new TextRun({ text: "Working Paper v1.0 | Dataset: 2,210 PDUFA events (2015\u20132026) | 1,451 events with daily price series", font: "Arial", size: 18, italics: true, color: "666666" })
        ]}),
        new Paragraph({ children: [new PageBreak()] }),
      ]
    },
    // ── TOC + BODY ──
    {
      properties: {
        page: {
          size: { width: 12240, height: 15840 },
          margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 }
        }
      },
      headers: {
        default: new Header({ children: [new Paragraph({
          alignment: AlignmentType.RIGHT,
          children: [new TextRun({ text: "ODIN Runup Research | pdufa.bio", font: "Arial", size: 16, color: "999999", italics: true })]
        })] })
      },
      footers: {
        default: new Footer({ children: [new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [new TextRun({ text: "Page ", font: "Arial", size: 16, color: "999999" }),
                     new TextRun({ children: [PageNumber.CURRENT], font: "Arial", size: 16, color: "999999" })]
        })] })
      },
      children: [
        new TableOfContents("Table of Contents", { hyperlink: true, headingStyleRange: "1-3" }),
        new Paragraph({ children: [new PageBreak()] }),

        // ═══════════════════════════════════════════════════════════════
        // SECTION 1: ABSTRACT
        // ═══════════════════════════════════════════════════════════════
        h1("1. Abstract"),
        p("This paper presents the first large-scale empirical analysis of pre-catalyst stock price dynamics surrounding FDA PDUFA decisions and clinical phase readouts. Using a dataset of 1,451 events with daily price time series spanning 2016\u20132025, we characterize the magnitude, timing, and determinants of runup returns across ODIN-tier-stratified catalyst categories. Our principal finding is that naive T-90\u2192T-7 windows produce statistically significant but economically modest mean returns of +5.6% (t=4.88, p<0.0001), with high dispersion (\u03c3=41.5%) and a hit rate of only 53.8%. The distribution exhibits pronounced positive skewness (5.75) and extreme leptokurtosis (68.3), indicating fat right tails drive positive mean returns while the median runup of just +2.0% reflects the experience of a typical trade."),

        p("Tier-stratified timing optimization reveals dramatically different optimal windows: TIER_1 events (ODIN probability \u22650.85) show peak risk-adjusted returns in tight T-14\u2192T-7 windows (annualized Sharpe 0.82), while TIER_3 events (\u22650.40) optimize at T-21\u2192T-14 (annualized Sharpe 1.06). TIER_4 events (probability <0.40) exhibit negative median runups across all windows and should be avoided entirely. The T-7\u2192T-1 period is confirmed as statistically indistinguishable from zero for TIER_1 and TIER_2 (\u201cdead money\u201d), though TIER_3 shows a surprising +2.14% mean (p=0.006), suggesting market uncertainty drives late-stage positioning in lower-confidence catalysts."),

        p("Factor analysis identifies Rare Disease (+14.8% vs. overall) and Cardiovascular (+7.3%) therapeutic areas as significant positive contributors, while Oncology (\u22123.9%) and Ophthalmology (\u22126.4%) systematically underperform. ODIN score shows a modest but statistically significant correlation with runup magnitude (r=0.055, p=0.047), with the bottom quartile (score <0.685) producing negative median returns (\u22123.8%) versus the top quartile (score >0.923) at +3.8%. These findings directly inform the ODIN v10.67 Runup Module specification and optimal window templates for production deployment on pdufa.bio."),

        new Paragraph({ children: [new PageBreak()] }),

        // ═══════════════════════════════════════════════════════════════
        // SECTION 2: DATA AND METHODOLOGY
        // ═══════════════════════════════════════════════════════════════
        h1("2. Data and Methodology"),
        h2("2.1 Dataset Construction"),
        p("The primary dataset comprises 2,210 FDA catalyst events from the ODIN enriched dataset (ODIN_MODEL_READY_v1071_T1_2015on_ENRICHED.csv), spanning January 2015 through April 2026. Events include PDUFA action dates (NDA, BLA, sNDA, sBLA), Priority Review milestones, and clinical phase readouts (Phase 1 through Phase 3). Each event is scored by the ODIN v10.70 production model, assigning an approval probability and corresponding tier classification (TIER_1 through TIER_4)."),

        p("From this universe, we select 1,847 events with known binary outcomes (APPROVAL or CRL) and catalyst dates between January 2016 and December 2025. Stratified random sampling by tier and outcome yields a price-fetch target of 640 events, with the following allocation: TIER_1 (200 events, 65% approval), TIER_2 (160 events), TIER_3 (130 events), and TIER_4 (150 events). Combined with 162 events from a preliminary fetch, the final dataset contains 1,451 events with complete daily price time series."),

        h2("2.2 Price Data Collection"),
        p("Daily OHLCV data for each event is fetched via the Yahoo Finance API (yfinance), covering trading days from T-130 (calendar days before catalyst) through T+15 (calendar days after). This captures the full runup period plus a short post-event window. Of the 640 targeted events, 502 returned valid price data (78.4% success rate), with 117 failures due to delisted tickers, yfinance authentication errors, or insufficient data. The resulting time series contains 151,427 daily price observations across 1,451 unique events."),

        h2("2.3 Return Computation"),
        p("For each event, we compute returns over 12 standard windows by identifying the closest available trading day to each target offset (with \u00b12-day tolerance). Returns are calculated as simple percentage changes: R = (P_exit / P_entry \u2212 1) \u00d7 100. Normalized returns use the T-120 (or earliest available) price as reference. The 12 windows span entry points from T-120 to T-14 and exit points from T-14 to T-1, capturing short-term sprint, medium-term accumulation, and full-cycle runup dynamics."),

        h2("2.4 Statistical Methods"),
        p("Descriptive statistics include mean, median, standard deviation, hit rate (percentage of positive returns), skewness, and kurtosis. Statistical significance is assessed via one-sample t-tests (H0: mean return = 0) and two-sample Welch t-tests for group comparisons. Distribution normality is tested using the Jarque-Bera statistic. Timing optimization employs a systematic grid search over 42 entry-exit combinations (7 entry points \u00d7 6 exit points), ranking by annualized Sharpe ratio with the approximation: Sharpe_ann = Sharpe_raw \u00d7 sqrt(252 / holding_days). Multivariate factor analysis uses OLS linear regression with indicator variables for ODIN tier, therapeutic area, and regulatory designation."),

        new Paragraph({ children: [new PageBreak()] }),

        // ═══════════════════════════════════════════════════════════════
        // SECTION 3: DESCRIPTIVE STATISTICS
        // ═══════════════════════════════════════════════════════════════
        h1("3. Descriptive Statistics of PDUFA Runups"),
        h2("3.1 Overall Runup Characteristics"),
        p("Table 1 presents the full descriptive statistics for all 12 measurement windows across the 1,451-event sample. The flagship T-90\u2192T-7 window yields a mean return of +5.62% (t=4.88, p<0.0001) with a median of +2.02%. The 1.6 percentage-point gap between mean and median immediately signals the influence of positive outliers. Standard deviation of 41.5% dwarfs the mean, implying a raw Sharpe ratio of just 0.14 \u2014 economically meaningful only with position sizing and tier selection."),

        // Table 1: Overall descriptive stats
        makeTable(
          ['Window', 'N', 'Mean %', 'Median %', 'Std %', 'Hit Rate', 'Skewness', 't-stat', 'p-value'],
          [
            ['T-90\u2192T-7', '1,300', '+5.62', '+2.02', '41.51', '53.8%', '5.75', '4.878', '<0.0001'],
            ['T-90\u2192T-5', '1,300', '+5.87', '+1.96', '41.10', '54.1%', '5.37', '5.153', '<0.0001'],
            ['T-60\u2192T-7', '1,442', '+3.57', '+1.61', '26.97', '53.8%', '1.69', '5.025', '<0.0001'],
            ['T-60\u2192T-14', '1,442', '+2.75', '+1.17', '25.02', '53.3%', '1.58', '4.171', '<0.0001'],
            ['T-30\u2192T-7', '1,443', '+2.23', '+0.91', '19.09', '53.4%', '2.11', '4.439', '<0.0001'],
            ['T-30\u2192T-5', '1,443', '+2.52', '+0.77', '19.71', '52.3%', '1.93', '4.852', '<0.0001'],
            ['T-14\u2192T-5', '1,443', '+1.37', '+0.28', '12.74', '52.1%', '3.01', '4.085', '<0.0001'],
            ['T-14\u2192T-7', '1,443', '+1.06', '+0.40', '11.65', '52.3%', '4.14', '3.457', '0.0006'],
            [{text: 'T-7\u2192T-1', color: 'CC0000'}, '1,443', {text: '+0.46', color: 'CC0000'}, {text: '\u22120.22', color: 'CC0000'}, '9.09', {text: '48.0%', color: 'CC0000'}, '2.29', {text: '1.932', color: 'CC0000'}, {text: '0.054', color: 'CC0000'}],
            [{text: 'T-5\u2192T-1', color: 'CC0000'}, '1,443', {text: '+0.15', color: 'CC0000'}, {text: '0.00', color: 'CC0000'}, '7.07', {text: '49.1%', color: 'CC0000'}, '1.21', {text: '0.809', color: 'CC0000'}, {text: '0.419', color: 'CC0000'}],
          ],
          [1200, 700, 900, 900, 800, 900, 1000, 900, 960]
        ),

        p("Table 1: Overall Runup Descriptive Statistics across 12 measurement windows. Red rows indicate windows that fail to reject H0 at the 5% level, confirming the dead-money hypothesis for T-7\u2192T-1 and T-5\u2192T-1.", { italics: true, after: 240 }),

        p("Several patterns emerge. First, all windows from T-90 through T-5 show statistically significant positive mean returns, confirming that pre-catalyst runups are a genuine market phenomenon. Second, the hit rate is remarkably stable at 52\u201354% across all profitable windows \u2014 barely above a coin flip \u2014 meaning the strategy depends critically on the magnitude of winners exceeding losers, not on directional accuracy. Third, the T-7\u2192T-1 and T-5\u2192T-1 windows fail to reject the null hypothesis (p=0.054 and p=0.419 respectively), with negative medians and sub-50% hit rates, confirming that the final week before a PDUFA decision is dead money on average."),

        h2("3.2 Tier-Stratified Runup Profiles"),
        p("Table 2 disaggregates the T-90\u2192T-7 and T-30\u2192T-7 windows by ODIN tier, revealing a clear monotonic relationship between model confidence and runup profitability."),

        makeTable(
          ['Tier', 'N', 'Mean %', 'Median %', 'Std %', 'Hit Rate', 'Sharpe'],
          [
            [{text: 'TIER_1', bold: true, shading: 'E8F5E9', color: '1B5E20'}, '569', {text: '+6.22', color: '1B5E20'}, {text: '+3.23', color: '1B5E20'}, '27.78', {text: '57.8%', bold: true, color: '1B5E20'}, {text: '0.224', bold: true, color: '1B5E20'}],
            [{text: 'TIER_2', bold: true, shading: 'E3F2FD'}, '376', '+7.42', '+2.19', '48.44', '54.0%', '0.153'],
            [{text: 'TIER_3', bold: true, shading: 'FFF3E0'}, '199', '+5.12', '+0.83', '42.25', '51.3%', '0.121'],
            [{text: 'TIER_4', bold: true, shading: 'FFEBEE', color: 'B71C1C'}, '156', {text: '\u22120.32', color: 'B71C1C'}, {text: '\u22128.28', color: 'B71C1C', bold: true}, '60.11', {text: '41.7%', color: 'B71C1C'}, {text: '\u22120.005', color: 'B71C1C'}],
          ],
          [1200, 800, 1000, 1000, 900, 1000, 1100]
        ),

        p("Table 2: T-90\u2192T-7 Runup Returns by ODIN Tier (N=1,300). TIER_1 achieves the highest hit rate (57.8%) and Sharpe (0.224), while TIER_4 shows negative median returns (\u22128.3%) and a sub-42% hit rate.", { italics: true, after: 240 }),

        p("TIER_1 events show a +3.23% median return with a 57.8% hit rate \u2014 the only tier exceeding 55% directional accuracy. TIER_2 has the highest mean (+7.42%) but also the highest standard deviation (48.44%), reflecting fat-tailed outliers in mid-confidence events. TIER_3 barely clings to positive territory with a +0.83% median. TIER_4 is unambiguously negative: \u22128.28% median, 41.7% hit rate, and a Sharpe of essentially zero. This validates the ODIN framework\u2019s TIER_4 = NO TRADE rule with out-of-sample price data."),

        h2("3.3 Outcome-Conditional Runups"),
        p("A critical question is whether the market \u201cknows\u201d the outcome before the decision. Table 3 separates runup returns by actual outcome (Approval vs. CRL), revealing that events ultimately approved run up +7.07% on average (T-90\u2192T-7) versus \u22120.70% for CRLs. This 7.77 percentage-point spread is statistically significant and suggests partial information leakage \u2014 likely through informed trading, clinical data signals, or FDA communication patterns \u2014 during the pre-decision window."),

        makeTable(
          ['Outcome', 'N', 'Mean %', 'Median %', 'Std %', 'Hit Rate'],
          [
            [{text: 'APPROVAL', bold: true, color: '1B5E20'}, '1,057', {text: '+7.07', color: '1B5E20'}, {text: '+2.68', color: '1B5E20'}, '40.73', {text: '55.4%', color: '1B5E20'}],
            [{text: 'CRL', bold: true, color: 'B71C1C'}, '243', {text: '\u22120.70', color: 'B71C1C'}, {text: '\u22122.83', color: 'B71C1C'}, '44.29', {text: '46.5%', color: 'B71C1C'}],
          ],
          [1500, 1000, 1200, 1200, 1200, 1200]
        ),

        p("Table 3: T-90\u2192T-7 Runup Returns by Actual Outcome. Events later approved run up +7.07% on average, while CRL events show \u22120.70%, consistent with partial information leakage.", { italics: true, after: 240 }),

        new Paragraph({ children: [new PageBreak()] }),

        // ═══════════════════════════════════════════════════════════════
        // SECTION 4: FACTOR ANALYSIS
        // ═══════════════════════════════════════════════════════════════
        h1("4. Factor Analysis: Determinants of Runup Magnitude"),
        h2("4.1 Therapeutic Area Effects"),
        p("Therapeutic area exerts a powerful and economically significant effect on runup magnitude. Table 4 presents the mean runup differential by TA relative to the overall sample mean of +5.65%."),

        makeTable(
          ['Therapeutic Area', 'N', 'Mean %', 'Median %', 'vs. Overall'],
          [
            [{text: 'Rare Disease', bold: true, color: '1B5E20'}, '59', {text: '+20.47', color: '1B5E20', bold: true}, {text: '+8.72', color: '1B5E20'}, {text: '+14.82', color: '1B5E20', bold: true}],
            [{text: 'Cardiovascular', bold: true}, '34', '+12.96', '+6.78', {text: '+7.31', color: '1B5E20'}],
            ['Nephrology', '22', '+10.68', '+10.53', {text: '+5.03', color: '1B5E20'}],
            ['Metabolic/Endocrine', '29', '+9.04', '+10.99', {text: '+3.39', color: '1B5E20'}],
            ['CNS/Neurology', '73', '+8.19', '+2.05', '+2.54'],
            ['Immunology', '82', '+7.01', '+1.78', '+1.36'],
            ['Other', '258', '+8.47', '+4.45', '+2.82'],
            ['Infectious Disease', '124', '+4.53', '+2.74', '\u22121.12'],
            [{text: 'Oncology', color: 'B71C1C'}, '502', {text: '+1.79', color: 'B71C1C'}, '+0.20', {text: '\u22123.86', color: 'B71C1C'}],
            [{text: 'Ophthalmology', color: 'B71C1C'}, '29', {text: '\u22120.75', color: 'B71C1C'}, '+4.59', {text: '\u22126.40', color: 'B71C1C'}],
            [{text: 'Dermatology', color: 'B71C1C'}, '18', {text: '\u22123.68', color: 'B71C1C'}, '+1.96', {text: '\u22129.34', color: 'B71C1C'}],
          ],
          [2200, 800, 1100, 1100, 1200]
        ),

        p("Table 4: Therapeutic Area Effects on T-90\u2192T-7 Runup Returns. Rare Disease events show a +14.8pp differential versus overall, while Oncology underperforms by \u22123.9pp.", { italics: true, after: 240 }),

        p("Rare Disease dominates with a +20.47% mean runup (\u22488.7% median), driven by smaller company sizes, lower institutional coverage, and the high-drama narrative around orphan drug approvals. Cardiovascular and Nephrology also outperform, likely reflecting investor enthusiasm for underserved therapeutic areas with large unmet need. Oncology\u2019s underperformance (+1.79% mean, +0.20% median) is counterintuitive given the therapeutic area\u2019s dominance but consistent with the hypothesis that oncology catalysts are more efficiently priced due to higher analyst coverage and more frequent interim data releases that reduce pre-PDUFA information asymmetry."),

        h2("4.2 Regulatory Designation Effects"),
        p("Breakthrough Therapy Designation (BTD), Orphan Drug, Priority Review, and other regulatory markers show surprisingly muted runup effects. BTD-designated events show +7.26% mean versus +5.34% for non-BTD (diff=+1.92%, p=0.39), while orphan drugs show +8.39% versus +4.93% (diff=+3.47%, p=0.19). None of these differences reach statistical significance at the 5% level, suggesting that regulatory designations are largely priced in by T-90."),

        h2("4.3 ODIN Score as Runup Predictor"),
        p("The ODIN approval probability score shows a modest but statistically significant positive correlation with runup magnitude (Pearson r=0.055, p=0.047). When stratified by quartile, the pattern is monotonic in hit rate: Q1 (score <0.685) produces a 46.5% hit rate with \u22123.80% median, while Q4 (score >0.923) achieves a 59.3% hit rate with +3.77% median. This 12.8 percentage-point spread in hit rate across the ODIN score distribution validates the model\u2019s utility as a runup filter, even though the linear correlation is weak."),

        makeTable(
          ['Score Quartile', 'N', 'Score Range', 'Mean Runup %', 'Median %', 'Hit Rate'],
          [
            [{text: 'Q1 (Lowest)', color: 'B71C1C'}, '327', '[0.130, 0.685]', {text: '+1.71', color: 'B71C1C'}, {text: '\u22123.80', color: 'B71C1C', bold: true}, {text: '46.5%', color: 'B71C1C'}],
            ['Q2', '328', '[0.685, 0.834]', '+8.19', '+2.25', '53.4%'],
            ['Q3', '326', '[0.834, 0.923]', '+7.19', '+2.48', '56.1%'],
            [{text: 'Q4 (Highest)', color: '1B5E20'}, '327', '[0.923, 0.981]', {text: '+5.51', color: '1B5E20'}, {text: '+3.77', color: '1B5E20', bold: true}, {text: '59.3%', color: '1B5E20', bold: true}],
          ],
          [1600, 800, 1700, 1600, 1200, 1200]
        ),

        p("Table 5: Runup Returns by ODIN Score Quartile. The bottom quartile produces negative median returns and a sub-47% hit rate, while the top quartile achieves a 59.3% hit rate.", { italics: true, after: 240 }),

        h2("4.4 Multivariate Regression"),
        p("A multivariate OLS regression of T-90\u2192T-7 returns on factor indicators yields R\u00b2=0.013 \u2014 low but consistent with the inherently noisy nature of biotech stock returns. The largest coefficients are ODIN score (+14.3pp per unit), CNS/Neurology (\u221213.7pp, reflecting high-variance outcomes in neurological trials), Rare Disease (+9.5pp), and Oncology (\u22127.2pp). The TIER_1 indicator shows a negative coefficient (\u22124.3pp), which is counterintuitive but reflects the collinearity with ODIN score \u2014 when score is already in the model, the tier indicator captures residual variance."),

        new Paragraph({ children: [new PageBreak()] }),

        // ═══════════════════════════════════════════════════════════════
        // SECTION 5: TIMING OPTIMIZATION
        // ═══════════════════════════════════════════════════════════════
        h1("5. Timing Optimization: Optimal Entry/Exit by Tier"),
        h2("5.1 Methodology"),
        p("We conduct a systematic grid search over 42 entry-exit combinations (7 entry points: T-120, T-90, T-60, T-45, T-30, T-21, T-14; 6 exit points: T-1, T-3, T-5, T-7, T-10, T-14) for each tier independently. The ranking criterion is annualized Sharpe ratio, computed as Sharpe_ann = (mean_return / std_return) \u00d7 sqrt(252 / holding_days). This penalizes longer holding periods that do not proportionally increase returns, favoring efficient capital deployment."),

        h2("5.2 Results by Tier"),
        p("Table 6 presents the optimal window for each tier along with the top-3 alternatives, revealing a striking divergence in optimal timing across confidence levels."),

        makeTable(
          ['Tier', 'Optimal Window', 'Mean %', 'Hit Rate', 'Ann. Sharpe', 'Hold (days)'],
          [
            [{text: 'TIER_1', bold: true, color: '1B5E20'}, {text: 'T-14 \u2192 T-7', bold: true, color: '1B5E20'}, {text: '+1.03', color: '1B5E20'}, {text: '53.2%', color: '1B5E20'}, {text: '0.815', bold: true, color: '1B5E20'}, '7'],
            ['TIER_1 (#2)', 'T-14 \u2192 T-10', '+0.57', '52.9%', '0.776', '4'],
            ['TIER_1 (#3)', 'T-21 \u2192 T-7', '+1.57', '56.2%', '0.576', '14'],
            [{text: 'TIER_2', bold: true, color: '2E75B6'}, {text: 'T-14 \u2192 T-5', bold: true, color: '2E75B6'}, {text: '+1.47', color: '2E75B6'}, {text: '53.2%', color: '2E75B6'}, {text: '0.615', bold: true, color: '2E75B6'}, '9'],
            ['TIER_2 (#2)', 'T-14 \u2192 T-7', '+1.17', '52.3%', '0.521', '7'],
            ['TIER_2 (#3)', 'T-30 \u2192 T-5', '+3.36', '54.9%', '0.516', '25'],
            [{text: 'TIER_3', bold: true, color: 'E65100'}, {text: 'T-21 \u2192 T-14', bold: true, color: 'E65100'}, {text: '+2.51', color: 'E65100'}, {text: '55.5%', color: 'E65100'}, {text: '1.056', bold: true, color: 'E65100'}, '7'],
            ['TIER_3 (#2)', 'T-21 \u2192 T-10', '+2.95', '51.4%', '0.830', '11'],
            ['TIER_3 (#3)', 'T-45 \u2192 T-14', '+5.18', '54.8%', '0.571', '31'],
            [{text: 'TIER_4', bold: true, color: 'B71C1C'}, {text: 'NO TRADE', bold: true, color: 'B71C1C'}, '\u2014', {text: '<50%', color: 'B71C1C'}, '\u2014', '\u2014'],
          ],
          [1600, 1600, 1000, 1000, 1200, 1000]
        ),

        p("Table 6: Optimal Timing Windows by ODIN Tier. TIER_3 achieves the highest annualized Sharpe (1.056) with a tight T-21\u2192T-14 window, while TIER_1 optimizes at T-14\u2192T-7.", { italics: true, after: 240 }),

        h2("5.3 Interpretation"),
        p("The tier-specific timing results reveal a fundamental insight about information dynamics in biotech catalysts. TIER_1 events (high-confidence approvals) have their outcome largely anticipated by the market, so the runup is compressed into the final two trading weeks before the decision. Entering earlier (T-90, T-60) adds noise without proportional return, as the stock is already well-owned by informed participants. The optimal T-14\u2192T-7 window captures the final momentum burst as less sophisticated participants join the trade."),

        p("TIER_3 events tell the opposite story. With approval probability in the 40\u201365% range, genuine uncertainty persists much longer. The market gradually resolves this uncertainty through news flow, insider activity, and sentiment shifts. The optimal T-21\u2192T-14 window captures this information resolution phase \u2014 and critically, the strategy exits at T-14, well before the final-week dead zone where uncertainty creates directionless volatility."),

        p("TIER_4\u2019s consistent negative median returns across all windows (worst: \u22128.69% median at T-120\u2192T-7) confirm that low-probability catalysts exhibit pre-event decay rather than runup, as informed money exits while retail momentum fails to materialize. This is the strongest empirical justification for the TIER_4 = NO TRADE rule."),

        new Paragraph({ children: [new PageBreak()] }),

        // ═══════════════════════════════════════════════════════════════
        // SECTION 6: ROBUSTNESS CHECKS
        // ═══════════════════════════════════════════════════════════════
        h1("6. Robustness Checks"),

        h2("6.1 Subperiod Stability"),
        p("We partition the sample into three subperiods to test temporal stability: 2020\u20132022 (N=556, includes COVID volatility) and 2023\u20132025 (N=736, post-COVID normalization). The 2016\u20132019 subperiod has insufficient events with price data after filtering."),

        p("The 2023\u20132025 subperiod shows higher mean returns (+6.95%) than 2020\u20132022 (+3.38%), consistent with increased retail participation in biotech catalysts during the post-COVID era. Crucially, the tier ordering is preserved in both subperiods: TIER_1 outperforms TIER_4 in mean, median, and hit rate across all time windows, confirming that the ODIN tier stratification is not an artifact of a single market regime."),

        p("The most notable subperiod divergence is TIER_3: strongly negative in 2020\u20132022 (\u22124.23% mean) but strongly positive in 2023\u20132025 (+14.33% mean). This suggests that mid-confidence catalysts are particularly sensitive to market regime \u2014 in risk-off environments, uncertain catalysts decay, while in risk-on environments, they attract speculative capital. This regime dependence should be incorporated into position sizing."),

        h2("6.2 Distribution Properties"),
        p("All runup return distributions are dramatically non-normal, with Jarque-Bera statistics in the tens of thousands (p<0.0001). Skewness ranges from 1.58 (T-60\u2192T-14) to 5.75 (T-90\u2192T-7), confirming that the positive mean is driven by a fat right tail of large winners. Kurtosis values of 9.1 to 68.3 indicate extreme leptokurtosis \u2014 there are far more extreme observations (both positive and negative) than a normal distribution would predict."),

        p("Extreme moves (>+50% or <\u221230%) occur in 15.1% of T-90\u2192T-7 observations: 6.2% exceed +50% (representing massive pre-PDUFA rallies in micro-cap biotechs) while 8.9% decline more than 30% (reflecting pre-decision selloffs in troubled programs). These tails have profound implications for position sizing \u2014 standard Gaussian risk models will dramatically underestimate tail risk."),

        h2("6.3 Dead Money Confirmation"),
        p("The T-7\u2192T-1 dead money hypothesis is tested formally across all tiers. Overall, the T-7\u2192T-1 window shows a mean of +0.46% with a p-value of 0.054 \u2014 borderline insignificant. By tier, TIER_1 (\u22120.20%, p=0.42) and TIER_2 (+0.34%, p=0.44) are clearly indistinguishable from zero. TIER_3 is the surprising exception: +2.14% mean (p=0.006), suggesting that market uncertainty in low-confidence events drives continued positioning into the final week. TIER_4 shows +1.05% (p=0.30), consistent with noise rather than signal."),

        new Paragraph({ children: [new PageBreak()] }),

        // ═══════════════════════════════════════════════════════════════
        // SECTION 7: IMPLICATIONS
        // ═══════════════════════════════════════════════════════════════
        h1("7. Implications for the ODIN/Gungnir Framework"),

        h2("7.1 Runup Module Specification"),
        p("These findings directly inform the ODIN v10.67 Runup Module with the following production parameters:"),

        makeTable(
          ['Parameter', 'TIER_1', 'TIER_2', 'TIER_3', 'TIER_4'],
          [
            [{text: 'Optimal Entry', bold: true}, 'T-14', 'T-14', 'T-21', 'NO TRADE'],
            [{text: 'Optimal Exit', bold: true}, 'T-7', 'T-5', 'T-14', 'NO TRADE'],
            [{text: 'Hold Period', bold: true}, '7 days', '9 days', '7 days', '\u2014'],
            [{text: 'Expected Return', bold: true}, '+1.0%', '+1.5%', '+2.5%', '\u2014'],
            [{text: 'Hit Rate', bold: true}, '53%', '53%', '56%', '<42%'],
            [{text: 'Ann. Sharpe', bold: true}, '0.82', '0.62', '1.06', 'N/A'],
            [{text: 'Max Position %', bold: true}, '5%', '3%', '1.5%', '0%'],
            [{text: 'Strategy', bold: true}, 'Equity/ITM Calls', 'Call Spreads', 'OTM Calls only', 'NONE'],
          ],
          [1800, 1800, 1800, 1800, 1800]
        ),

        p("Table 7: ODIN Runup Module Production Parameters derived from 1,451-event empirical analysis.", { italics: true, after: 240 }),

        h2("7.2 Factor Adjustments"),
        p("The TA factor analysis suggests the following adjustments to expected runup returns: Rare Disease (+15pp), Cardiovascular (+7pp), CNS/Neurology (+3pp), Oncology (\u22124pp), Ophthalmology (\u22126pp), Dermatology (\u22129pp). These adjustments should be applied multiplicatively to the base expected return for each tier. Regulatory designations (BTD, Orphan, Priority Review) show economically meaningful but statistically insignificant effects and should receive smaller adjustments (\u00b12\u20133pp) pending further validation with larger subsamples."),

        h2("7.3 Risk Management Rules"),
        p("The extreme leptokurtosis and 15% tail-event frequency necessitate strict risk management: (1) Position sizes must reflect the true 41.5% standard deviation, not a Gaussian approximation. (2) Stop-losses should be avoided in the runup window as the distribution is right-skewed \u2014 stops would systematically remove the winners that drive positive expected value. (3) The T-7 hard exit for TIER_1/2 and T-14 exit for TIER_3 serve as built-in risk limits by ensuring no position is held through the binary event itself."),

        new Paragraph({ children: [new PageBreak()] }),

        // ═══════════════════════════════════════════════════════════════
        // SECTION 8: LIMITATIONS
        // ═══════════════════════════════════════════════════════════════
        h1("8. Limitations and Future Research"),

        p("Several limitations constrain the generalizability of these findings. First, survivorship bias affects the price data: 117 of 640 targeted events (18.3%) failed to return price data, predominantly due to delisted tickers. Delisted biotechs are more likely to have experienced CRL outcomes and subsequent corporate failures, potentially biasing our sample toward more successful events. Second, the stratified sampling approach over-weights certain tiers relative to their population frequency, though this is by design to ensure statistical power across all tiers."),

        p("Third, transaction costs, market impact, and bid-ask spreads are not modeled. Micro-cap biotechs with wide spreads (often 1\u20133% of price) could significantly erode the +1\u20132.5% expected returns in the optimized windows. Fourth, the analysis assumes the ODIN tier assignment is known at T-90 or earlier; in practice, the score may be updated as new information arrives, and some events may shift tiers during the runup period."),

        p("Fifth, the R\u00b2 of the multivariate regression (0.013) confirms that the vast majority of runup variance is unexplained by observable factors. Market regime, sector momentum, options flow, and social media sentiment \u2014 factors not included in this analysis \u2014 likely contribute meaningfully. Future research should incorporate the Gungnir phase readout dataset (2,022 events), intraday price dynamics, and options market data to refine timing signals. The integration of FinBrain insider trading signals and LunarCrush social sentiment as real-time runup indicators represents a particularly promising avenue for improving the T-14 entry signal."),

        p("Finally, the observed regime sensitivity (TIER_3 returns swinging from \u22124.2% to +14.3% across subperiods) suggests that a market regime overlay \u2014 perhaps based on biotech sector ETF (XBI/IBB) momentum or VIX levels \u2014 could meaningfully improve position sizing decisions. This is a priority for the ODIN v10.68 specification."),

        new Paragraph({ spacing: { before: 600 } }),
        new Paragraph({ alignment: AlignmentType.CENTER, children: [
          new TextRun({ text: "\u2014 END OF REPORT \u2014", font: "Arial", size: 20, color: "999999", italics: true })
        ]}),
      ]
    }
  ]
});

// ── Write file ──
Packer.toBuffer(doc).then(buffer => {
  const outPath = '/sessions/tender-vigilant-planck/mnt/outputs/ODIN_Runup_Research_Paper_v1.docx';
  fs.writeFileSync(outPath, buffer);
  console.log(`Written: ${outPath} (${(buffer.length / 1024).toFixed(1)} KB)`);
});
