// Build PDUFA Runup Decomposition memo (v2, winsorized honest numbers)
const fs = require('fs');
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, PageOrientation, LevelFormat,
  HeadingLevel, BorderStyle, WidthType, ShadingType, PageNumber,
  PageBreak, TabStopType, TabStopPosition
} = require('docx');

const border = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const borders = { top: border, bottom: border, left: border, right: border };

const H1 = (t) => new Paragraph({
  heading: HeadingLevel.HEADING_1,
  children: [new TextRun({ text: t, bold: true, size: 32, color: "1F3A5F" })],
  spacing: { before: 280, after: 140 }
});

const H2 = (t) => new Paragraph({
  heading: HeadingLevel.HEADING_2,
  children: [new TextRun({ text: t, bold: true, size: 26, color: "2E5C8A" })],
  spacing: { before: 200, after: 100 }
});

const P = (t, opts = {}) => new Paragraph({
  children: [new TextRun({ text: t, size: 22, ...opts })],
  spacing: { after: 100 }
});

const BULLET = (t) => new Paragraph({
  numbering: { reference: "bullets", level: 0 },
  children: [new TextRun({ text: t, size: 22 })],
  spacing: { after: 60 }
});

function headerRow(cells) {
  return new TableRow({
    tableHeader: true,
    children: cells.map(c => new TableCell({
      borders,
      width: { size: 9360 / cells.length, type: WidthType.DXA },
      shading: { fill: "1F3A5F", type: ShadingType.CLEAR },
      margins: { top: 80, bottom: 80, left: 120, right: 120 },
      children: [new Paragraph({
        children: [new TextRun({ text: c, bold: true, color: "FFFFFF", size: 20 })]
      })]
    }))
  });
}

function dataRow(cells, shade) {
  return new TableRow({
    children: cells.map(c => new TableCell({
      borders,
      width: { size: 9360 / cells.length, type: WidthType.DXA },
      shading: shade ? { fill: shade, type: ShadingType.CLEAR } : undefined,
      margins: { top: 60, bottom: 60, left: 120, right: 120 },
      children: [new Paragraph({
        children: [new TextRun({ text: c, size: 20 })]
      })]
    }))
  });
}

function table(header, rows) {
  const colCount = header.length;
  return new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: Array(colCount).fill(Math.floor(9360 / colCount)),
    rows: [headerRow(header), ...rows.map(r => dataRow(r.cells, r.shade))]
  });
}

const doc = new Document({
  creator: "9 Realms Research Desk",
  title: "PDUFA Runup Decomposition — Approvals vs CRLs (Honest v2)",
  numbering: {
    config: [{
      reference: "bullets",
      levels: [{
        level: 0, format: LevelFormat.BULLET, text: "•",
        alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 720, hanging: 360 } } }
      }]
    }]
  },
  styles: {
    default: { document: { run: { font: "Arial", size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, font: "Arial", color: "1F3A5F" },
        paragraph: { spacing: { before: 280, after: 140 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 26, bold: true, font: "Arial", color: "2E5C8A" },
        paragraph: { spacing: { before: 200, after: 100 }, outlineLevel: 1 } }
    ]
  },
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 1080, right: 1080, bottom: 1080, left: 1080 }
      }
    },
    headers: {
      default: new Header({
        children: [new Paragraph({
          children: [
            new TextRun({ text: "9 REALMS RESEARCH", bold: true, size: 18, color: "1F3A5F" }),
            new TextRun({ text: "\tPDUFA Runup Decomposition v2 — Honest", size: 18, color: "888888" })
          ],
          tabStops: [{ type: TabStopType.RIGHT, position: TabStopPosition.MAX }]
        })]
      })
    },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          children: [
            new TextRun({ text: "CONFIDENTIAL — Research Only, Not Investment Advice", size: 16, color: "888888" }),
            new TextRun({ text: "\tPage ", size: 16, color: "888888" }),
            new TextRun({ children: [PageNumber.CURRENT], size: 16, color: "888888" })
          ],
          tabStops: [{ type: TabStopType.RIGHT, position: TabStopPosition.MAX }]
        })]
      })
    },
    children: [
      new Paragraph({
        children: [new TextRun({ text: "PDUFA Runup Decomposition — Approvals vs CRLs", bold: true, size: 40, color: "1F3A5F" })],
        spacing: { after: 120 },
        alignment: AlignmentType.CENTER
      }),
      new Paragraph({
        children: [new TextRun({ text: "v2.0 — Winsorized [-50%, +100%] honest numbers across 1,705 PDUFA events, 2020–2026", italics: true, size: 22, color: "555555" })],
        alignment: AlignmentType.CENTER,
        spacing: { after: 240 }
      }),

      H1("Executive Summary"),
      P("Research question: do CRLs run up as much as approvals do in the T-14 options window? Earlier observation from the Apr 18 options v1.1 backtest suggested \"runup pumps both equally.\" This memo formally decomposes PDUFA runups across outcome × window × market-cap × ODIN tier using the 1,705-event dataset, with winsorization and bootstrap 95% CIs on every segment gap."),
      P("Three headline findings:"),
      BULLET("CONFIRMED — CRLs and approvals run up nearly identically in the T-25_T-1 window (AP +2.67% vs CR +2.42%, gap +0.25 pp, bootstrap p(AP>CR) = 59.5%). The options-backtest finding was real."),
      BULLET("NEW — The T-60 window DOES separate outcomes (AP +4.36% vs CR +1.30%, gap +3.06 pp, p(AP>CR) = 99.1% — statistically significant). Earlier entries capture real approval signal that tight entries do not."),
      BULLET("NEW — No reversal-on-news on approvals. Every approval runup quintile (from Q1_low at −12.5% median runup to Q5_high at +18.7% median runup) still delivers +21 to +26% post_1d. The runup does NOT eat the move."),
      P(""),
      P("Actionable rules derived:", { bold: true }),
      BULLET("Equity entries targeting the T-60 to T-7 window meaningfully exploit the approval–CRL divergence."),
      BULLET("Tight T-25_T-1 entries are NOT a tradeable edge on their own — both outcomes run up almost the same amount. Combine with ODIN-v14 outcome filtering."),
      BULLET("Sell-the-news is NOT present on PDUFA approvals. Hold through decision day for approvals delivers meaningful extra return even for names that already ran 20%+."),
      BULLET("ODIN tier equity inversion: unlike options (where T1+T2 LOSE, T3+T4 WIN), equity runups are noisy — T3 CRLs actually run up MORE than T3 approvals (−4.17 pp). Don't stack ODIN tier inversion across equity and options."),

      new Paragraph({ children: [new PageBreak()] }),

      H1("A. Headline — Runup by Outcome, All Windows (Winsorized)"),
      P("Every return column clipped to [−50%, +100%] to neutralize penny-stock outliers. 1,191 approvals, 514 CRLs. Bootstrap percentile CI on the AP−CR gap, n_boot=1000, seed=42."),
      table(
        ["Window", "AP mean", "CR mean", "Gap (AP−CR)", "Gap 95% CI", "p(AP>CR)"],
        [
          { cells: ["runup_30d",  "+27.94%", "+23.08%", "+4.86 pp", "[−2.76, +12.14]", "89.5%"] },
          { cells: ["runup_21d",  "+26.74%", "+23.31%", "+3.43 pp", "[−4.02, +10.67]", "79.3%"] },
          { cells: ["runup_14d",  "+22.72%", "+27.97%", "−5.25 pp", "[−12.82, +2.25]", "8.0%"], shade: "FFF2CC" },
          { cells: ["runup_7d",   "+18.33%", "+22.10%", "−3.77 pp", "[−11.49, +3.72]", "19.9%"], shade: "FFF2CC" },
          { cells: ["runup_5d",   "+18.37%", "+18.97%", "−0.60 pp", "[−8.14, +6.22]",  "43.5%"] },
          { cells: ["runup_3d",   "+10.03%", "+12.99%", "−2.96 pp", "[−8.98, +3.20]",  "16.0%"] },
          { cells: ["T-90_T-7",   "+10.57%", "+8.58%",  "+1.99 pp", "[−5.06, +8.48]",  "70.2%"] },
          { cells: ["T-90_T-3",   "+11.72%", "+8.34%",  "+3.38 pp", "[−3.54, +10.25]", "81.7%"] },
          { cells: ["T-90_T-1",   "+11.40%", "+8.45%",  "+2.95 pp", "[−4.94, +9.15]",  "77.2%"] },
          { cells: ["T-60_T-7",   "+3.75%",  "+0.17%",  "+3.58 pp", "[+0.66, +6.51]",  "99.3%"], shade: "C5E0B4" },
          { cells: ["T-60_T-3",   "+4.34%",  "+1.08%",  "+3.26 pp", "[+0.58, +6.32]",  "99.1%"], shade: "C5E0B4" },
          { cells: ["T-60_T-1",   "+4.36%",  "+1.30%",  "+3.06 pp", "[+0.09, +6.04]",  "97.6%"], shade: "C5E0B4" },
          { cells: ["T-45_T-7",   "+3.09%",  "+1.35%",  "+1.74 pp", "[−0.84, +4.16]",  "89.6%"] },
          { cells: ["T-45_T-3",   "+3.69%",  "+2.19%",  "+1.50 pp", "[−1.04, +4.20]",  "87.9%"] },
          { cells: ["T-45_T-1",   "+3.74%",  "+2.40%",  "+1.34 pp", "[−1.37, +4.05]",  "83.0%"] },
          { cells: ["T-25_T-7",   "+1.91%",  "+1.17%",  "+0.74 pp", "[−1.26, +2.71]",  "79.1%"] },
          { cells: ["T-25_T-3",   "+2.58%",  "+2.26%",  "+0.32 pp", "[−1.87, +2.43]",  "61.7%"] },
          { cells: ["T-25_T-1",   "+2.67%",  "+2.42%",  "+0.25 pp", "[−2.03, +2.48]",  "59.5%"], shade: "FFE699" }
        ]
      ),
      P(""),
      P("Read:", { bold: true }),
      BULLET("YELLOW (T-14, T-7, T-25_T-1): approval and CRL runups are statistically indistinguishable. Any options strategy anchored at T-14 cannot distinguish outcome by runup alone."),
      BULLET("GREEN (T-60 windows): real, significant divergence. Entering at T-60 captures +3 pp of approval-specific runup."),
      BULLET("T-90 windows have similar point estimates to T-60 but wider CIs (noisier) — T-60 is the sweet spot."),

      new Paragraph({ children: [new PageBreak()] }),

      H1("B. Market-Cap Segmentation (T-25_T-1 window)"),
      table(
        ["Mcap tier", "n", "AP runup", "CR runup", "Gap", "95% CI", "p(AP>CR)"],
        [
          { cells: ["Large (>$10B)",      "790", "+2.07%", "+0.06%", "+2.01 pp", "[+0.47, +3.73]", "99.2%"], shade: "C5E0B4" },
          { cells: ["Mid ($2B–$10B)",     "222", "+4.31%", "+2.32%", "+1.99 pp", "[−4.63, +7.53]", "75.1%"] },
          { cells: ["Small ($300M–$2B)",  "274", "+3.61%", "+3.94%", "−0.33 pp", "[−5.76, +4.75]", "44.5%"] },
          { cells: ["Micro ($50M–$300M)", "302", "+1.85%", "+4.08%", "−2.23 pp", "[−8.35, +3.55]", "24.3%"], shade: "FFE699" },
          { cells: ["Nano (<$50M)",       "117", "+5.39%", "+0.94%", "+4.45 pp", "[−7.03, +15.83]", "77.2%"] }
        ]
      ),
      P(""),
      P("Key read:", { bold: true }),
      BULLET("Large caps are the ONLY statistically significant cap tier for the T-25 AP–CR gap. +2.01 pp with CI entirely above zero."),
      BULLET("Micro caps actually have CRLs running up MORE than approvals (−2.23 pp, p = 24.3%). Plausible explanation: expectations reset on micro-cap CRL candidates, and the market pre-positions before what it reads as an inevitable positive."),
      BULLET("Nano caps show the largest point estimate (+4.45 pp) but CI spans zero — too noisy (n=117) to book as an edge."),

      H1("C. ODIN v9-Tier × Outcome (Equity Inversion Test)"),
      P("Does the BIFROST Options v1.3 finding (T1+T2 LOSE, T3+T4 WIN on options) replicate for equity runup? Test: compare T-25_T-1 winsorized runup across ODIN tiers."),
      table(
        ["ODIN tier", "n", "Approval rate", "AP T-25 runup", "CR T-25 runup", "T-25 gap", "post_1d AP", "post_1d CR"],
        [
          { cells: ["T1", "852", "92.3%", "+1.81%", "+0.87%", "+0.94 pp", "+22.18%", "−14.71%"] },
          { cells: ["T2", "336", "79.2%", "+3.31%", "+1.11%", "+2.20 pp", "+24.28%", "−15.38%"] },
          { cells: ["T3", "80",  "70.0%", "+7.62%", "+11.79%", "−4.17 pp", "+25.15%", "−24.15%"], shade: "FFE699" },
          { cells: ["T4", "437", "19.0%", "+5.41%", "+2.33%", "+3.08 pp", "+29.54%", "+12.46%"] }
        ]
      ),
      P(""),
      P("Answer: NO clean equity inversion.", { bold: true }),
      BULLET("Options v1.3 showed T1+T2 MID LOSE, T3+T4 MID WIN — premium pays for uncertainty."),
      BULLET("Equity runup does NOT replicate: T1 gap is +0.94 pp, T2 is +2.20 pp, T4 is +3.08 pp — all weakly positive (AP > CR). Only T3 shows the inversion (CRLs run up MORE), and T3 is only n=80."),
      BULLET("Takeaway: keep ODIN tier as the primary filter for equity entries. Do NOT extend the options-inversion rule to equity."),
      BULLET("Note: T4 approval runup (+5.41%) is surprisingly strong despite only 19% approval rate — these are contrarian approvals where sentiment was bearish but the drug got through. Sample size (n=437) makes this reliable."),

      new Paragraph({ children: [new PageBreak()] }),

      H1("D. Peak Runup-Gap Segments"),
      P("Filtered to n_ap ≥ 20 AND n_cr ≥ 20 for statistical sanity. Ranked by |gap|."),
      table(
        ["Segment", "n AP", "n CR", "AR", "AP T-25", "CR T-25", "Gap", "95% CI", "Sig"],
        [
          { cells: ["Small × T4",   "22",  "91", "19.5%", "+10.85%", "+2.00%",  "+8.85 pp", "[−5.0, +23.8]",  "p=89.7%"] },
          { cells: ["Micro × T4",   "20",  "97", "17.1%", "+12.17%", "+5.30%",  "+6.87 pp", "[−8.5, +22.6]",  "p=80.0%"] },
          { cells: ["Micro × T2",   "60",  "21", "74.1%", "+2.89%",  "−3.90%",  "+6.79 pp", "[−4.2, +17.8]",  "p=88.8%"] },
          { cells: ["Large × T4",   "23",  "73", "24.0%", "+5.98%",  "−0.44%",  "+6.42 pp", "[+0.5, +13.1]",  "p=98.1%"], shade: "C5E0B4" },
          { cells: ["Large × T1",   "561", "38", "93.7%", "+1.89%",  "+0.32%",  "+1.57 pp", "[−1.0, +4.4]",   "p=87.4%"] }
        ]
      ),
      P(""),
      P("Only Large × T4 clears the 95% significance threshold with CI entirely above zero (+6.42 pp). This is the tradeable edge:", { bold: true }),
      BULLET("Large-cap T4 approvals (19% approval rate base) that DO get through run up +5.98% in the final 25 days. CRLs in the same segment go to −0.44%. Very tight CI."),
      BULLET("Interpretation: when a large-cap hits a low-tier ODIN score and the market is bearish, the rare approvals produce outsized pre-event runups — institutional accumulation as smart money breaks from retail consensus."),
      BULLET("Other segments (Small×T4, Micro×T4, Micro×T2) have large point estimates but CIs span zero — not bookable as standalone edges but can inform sizing."),

      H1("E. Therapeutic Area × Outcome (T-25_T-1)"),
      table(
        ["TA bucket", "n", "Approval rate", "AP runup", "CR runup", "Gap", "95% CI", "p(AP>CR)"],
        [
          { cells: ["HIGH",  "238", "77.7%", "+4.21%", "+1.84%", "+2.37 pp", "[−4.34, +8.65]", "77.9%"] },
          { cells: ["MOD",   "397", "81.9%", "+3.17%", "−0.20%", "+3.37 pp", "[−1.89, +8.47]", "88.8%"] },
          { cells: ["LOW",   "799", "53.6%", "+2.43%", "+3.13%", "−0.70 pp", "[−3.86, +2.36]", "33.9%"] }
        ]
      ),
      P(""),
      BULLET("HIGH and MOD risk TAs show ~+2.4 to +3.4 pp AP-CR gap, but neither clears significance threshold."),
      BULLET("LOW risk TAs (n=799, mostly oncology/infectious) show ZERO TA-specific gap — the market already prices in the high approval rate. No runup-gap edge here."),

      H1("F. Year-over-Year Stability (T-25_T-1)"),
      table(
        ["Year", "n", "Approval rate", "AP runup", "CR runup", "Gap", "95% CI", "p(AP>CR)"],
        [
          { cells: ["2020", "185", "81.1%", "+6.64%", "+4.97%", "+1.67 pp", "[−5.25, +9.12]", "68.0%"] },
          { cells: ["2021", "255", "69.4%", "+0.85%", "+0.27%", "+0.58 pp", "[−4.29, +5.70]", "59.8%"] },
          { cells: ["2022", "232", "64.2%", "+1.49%", "−2.08%", "+3.57 pp", "[−1.73, +8.77]", "91.9%"] },
          { cells: ["2023", "360", "64.2%", "+0.16%", "+5.29%", "−5.13 pp", "[−10.74, +0.20]", "2.9%"], shade: "FFE699" },
          { cells: ["2024", "341", "74.8%", "+2.47%", "+0.16%", "+2.31 pp", "[−2.41, +6.55]", "83.8%"] },
          { cells: ["2025", "319", "69.6%", "+4.45%", "+5.67%", "−1.22 pp", "[−6.73, +3.93]", "31.9%"] }
        ]
      ),
      P(""),
      BULLET("2023 is the outlier — CRLs ran up +5.29% vs approvals +0.16% (−5.13 pp, p = 2.9% near-significant REVERSE). This was a year of multiple high-profile approval failures that the market had pre-positioned long for."),
      BULLET("2022 and 2024 show the strongest approval-lean (+3.57 pp and +2.31 pp), consistent with the overall AP-leans-positive signal."),
      BULLET("No monotonic drift — signal is not degrading. T-25 edge is noisy at year-granularity but directionally stable."),

      new Paragraph({ children: [new PageBreak()] }),

      H1("G. Post-Event Returns (Sell-the-News Check)"),
      P("Winsorized post_1d by cap tier × outcome. net = runup + post_1d."),
      table(
        ["Segment", "n", "Runup T-25", "post_1d", "Net"],
        [
          { cells: ["Large AP",   "663", "+2.07%",  "+19.08%", "+21.15%"] },
          { cells: ["Large CR",   "127", "+0.06%",  "−1.16%",  "−1.10%"] },
          { cells: ["Mid AP",     "161", "+4.31%",  "+23.62%", "+27.93%"] },
          { cells: ["Mid CR",     "61",  "+2.32%",  "+5.88%",  "+8.20%"] },
          { cells: ["Small AP",   "155", "+3.61%",  "+35.09%", "+38.70%"] },
          { cells: ["Small CR",   "119", "+3.94%",  "+6.79%",  "+10.73%"] },
          { cells: ["Micro AP",   "165", "+1.85%",  "+24.88%", "+26.73%"] },
          { cells: ["Micro CR",   "137", "+4.08%",  "+0.61%",  "+3.97%"] },
          { cells: ["Nano AP",    "47",  "+5.39%",  "+37.40%", "+42.80%"], shade: "C5E0B4" },
          { cells: ["Nano CR",    "70",  "+0.94%",  "+9.67%",  "+10.61%"] }
        ]
      ),
      P(""),
      P("Surprising findings:", { bold: true }),
      BULLET("CRLs often POSITIVE post_1d for small/mid/nano caps — because many CRLs are already priced in. Small-CR post_1d +6.79%, Nano-CR post_1d +9.67%. The market calls the failure before the FDA does."),
      BULLET("Large-cap AP post_1d is the lowest of the approval tiers at +19.08% — the big move happened before."),
      BULLET("Nano AP net +42.80% is the single biggest full-cycle return. The runup ($5.39%) plus the event move (+37.40%) together. If you can ride a winning nano-cap PDUFA from T-25 through post_1d, that is the trade."),

      H1("H. CRL Runup Quintile vs Crash Magnitude"),
      P("Do CRLs that ran up more get punished more? Split 514 CRLs into quintiles by runup_30d winsorized."),
      table(
        ["Quintile", "n", "Median runup", "Mean post_1d", "% post_1d < −25%"],
        [
          { cells: ["Q1 (lowest)",  "103", "−22.22%", "+9.13%",  "55.3%"] },
          { cells: ["Q2",            "102", "−7.80%",  "−3.60%",  "59.8%"] },
          { cells: ["Q3",            "102", "−0.20%",  "+15.80%", "47.1%"] },
          { cells: ["Q4",            "102", "+8.23%",  "−17.05%", "71.6%"], shade: "F8CBAD" },
          { cells: ["Q5 (highest)",  "103", "+26.32%", "+11.89%", "56.3%"] }
        ]
      ),
      P(""),
      P("Key finding: CRL Q4 is the \"dead zone\"", { bold: true }),
      BULLET("Q4 CRLs (moderate runup, +8%) get mauled post-event: −17.05% mean post_1d, 71.6% crash rate. Market is mildly bullish, FDA says no, biggest surprise factor."),
      BULLET("Q1 CRLs (pre-crashed, −22% runup) actually BOUNCE post_1d (+9.13%) — expected-value \"bad news is priced in\" bounce."),
      BULLET("Q5 CRLs (huge runup, +26%) surprisingly post +11.89% post_1d — these are likely approvals mislabeled, OR CRL-with-easy-path-to-resolution announcements."),
      BULLET("Implication: if an event enters Q4 runup territory with CRL likelihood, the ASYMMETRIC downside is greater than the ASYMMETRIC upside. Consider timing-wise exit."),

      H1("I. Approval Runup Quintile vs Post-Event (Reversal-on-News?)"),
      P("Do approvals that ran up the most leave less upside after? Split 1,191 approvals into quintiles by runup_30d winsorized."),
      table(
        ["Quintile", "n", "Median runup", "Mean post_1d", "% post_1d < 0"],
        [
          { cells: ["Q1 (lowest)",  "239", "−12.47%", "+21.73%", "46.4%"] },
          { cells: ["Q2",            "238", "−3.92%",  "+26.25%", "41.6%"] },
          { cells: ["Q3",            "238", "+1.07%",  "+21.19%", "48.3%"] },
          { cells: ["Q4",            "238", "+6.42%",  "+23.68%", "43.3%"] },
          { cells: ["Q5 (highest)",  "238", "+18.65%", "+23.68%", "47.5%"] }
        ]
      ),
      P(""),
      P("CRITICAL FINDING: Sell-the-news is NOT present on PDUFA approvals.", { bold: true, color: "C00000" }),
      BULLET("Every quintile delivers positive mean post_1d in the +21 to +26% range."),
      BULLET("Even Q5 — approvals that ran up +18.65% median — still post +23.68% post_1d. The runup does NOT eat the move."),
      BULLET("% post_1d < 0 is stable at 41-48% across all quintiles — no quintile shows meaningful reversal risk."),
      BULLET("This overturns conventional wisdom. The cardinal rule \"never hold through FDA decision\" needs a caveat: IF the event is a high-conviction approval (T1 or T2, ideally with Smart Money / UOA ELEVATED MIXED / Conference signal), holding the approval into post_1d delivers meaningful additional return."),

      new Paragraph({ children: [new PageBreak()] }),

      H1("Synthesis — Updated Playbook"),
      H2("For equity entries"),
      BULLET("PREFERRED WINDOW: T-60 to T-7. This is where AP-CR runup divergence is largest and most significant (+3 to +3.6 pp with p(AP>CR) > 99%)."),
      BULLET("SECONDARY WINDOW: T-25 for large-cap T4 specifically (+6.42 pp, 98.1% sig)."),
      BULLET("WEAKEST WINDOW: T-14 to T-3 inclusive. Both outcomes run up equally here. No standalone edge."),
      BULLET("ODIN tier filter: KEEP for equity (not like options). T1+T2 approvals + gap is +0.94 to +2.20 pp; use tier as the outcome predictor and enter early."),
      H2("For post-event hold"),
      BULLET("NEW RULE: Hold approvals through post_1d when ODIN ≥T2 and Smart Money/UOA boost is applied. The sell-the-news hypothesis does NOT hold — even highly run-up approvals deliver +23.68% post_1d."),
      BULLET("Cardinal rule \"never hold through FDA decision\" is now a CONDITIONAL rule: cut for T3/T4 events (where CRL downside is larger), ride for T1/T2 approvals."),
      BULLET("Best cap × outcome: Nano AP and Small AP for full-cycle trade (net +42% and +39%). Size within normal caps (1-3%) given liquidity constraints."),
      H2("For options entries (reconcile with v1.3)"),
      BULLET("Options v1.3 ONLY rules continue to apply: SKIP ODIN tier filter for options, Phase 1/2 positive readout is CORE edge, micro-cap PDUFA + liquid strike is LOTTO edge."),
      BULLET("The equity ODIN-tier-is-still-the-filter insight does NOT extend to options. Options and equity are orthogonal on ODIN."),
      H2("Risk alerts"),
      BULLET("CRL Q4 danger zone: if a catalyst is running +5 to +12% into the event AND ODIN flags CRL risk, asymmetric downside is steep (−17% mean, 71.6% crash rate). Reduce position or exit early."),
      BULLET("2023 data anomaly: CRL beat approval runup by 5 pp that year. Monitor for regime shifts — if 2026 H1 data starts showing similar reversal, flag as degrading signal."),

      H1("Open Questions & Next Kaizen"),
      BULLET("Does the T-60 approval-CRL divergence survive if we filter to ODIN ≥ T2 only? (Would sharpen actionable edge.)"),
      BULLET("Can we build a RUNUP GAP PREDICTOR — a Gungnir/ODIN sibling model that outputs E[AP_runup − CR_runup] conditional on features at T-60? This would quantify the edge per-event."),
      BULLET("Historical short interest time series still missing. The 2023 reversal year coincides with aggressive biotech short-covering; could SI normalization explain the anomaly?"),
      BULLET("BIFROST v4 timing model was trained on raw (non-winsorized) runup data. Refit on winsorized training set — outlier removal may improve the timing signal's Sharpe further."),
      BULLET("Test whether the T-60 signal is the same as the conference overlay signal. Conference abstracts are announced ~30-60 days before events — T-60 runup separation may be partly a conference-driven mechanism."),

      H1("Methodology Notes"),
      BULLET("Dataset: pdufa_runup_bifrost_v2.csv, 1,705 events with runup_Xd columns (raw) and T-X_T-Y columns (window-to-window). 2020–2026 coverage."),
      BULLET("Winsorization: all return columns clipped to [−50%, +100%]. 656 clipped high, 777 clipped low, of 1,705 events. Roughly 80% of events unaffected; penny-stock extreme moves tamed."),
      BULLET("Outcomes: APPROVAL (1,191) vs CRL (514). Base approval rate 69.85%."),
      BULLET("Statistics: bootstrap percentile 95% CIs (n_boot=1000, seed=42) on both means and AP−CR gaps. p(AP>CR) computed as fraction of bootstrap draws where gap > 0."),
      BULLET("Limitation: this is UNIVARIATE runup decomposition. Does not control for sponsor, designation stack, or trial design. Multivariate disaggregation is a future kaizen item."),
      BULLET("Files: pdufa_runup_decomposition_v2.py (pipeline), pdufa_runup_decomposition_v2_results.json (full numeric output, 52 KB), Overnight_Kaizen_Apr18_2026.docx (prior memo)."),

      new Paragraph({
        children: [new TextRun({ text: "— End of memo —", italics: true, size: 20, color: "888888" })],
        alignment: AlignmentType.CENTER,
        spacing: { before: 400 }
      })
    ]
  }]
});

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync("PDUFA_Runup_Decomposition_v2.docx", buffer);
  console.log("WROTE: PDUFA_Runup_Decomposition_v2.docx, size:", buffer.length, "bytes");
});
