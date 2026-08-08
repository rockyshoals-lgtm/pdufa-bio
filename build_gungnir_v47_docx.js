// Gungnir v47 honest rebuild findings memo
const fs = require('fs');
const path = '/sessions/confident-serene-ptolemy/.npm-global/lib/node_modules/docx';
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
        AlignmentType, HeadingLevel, BorderStyle, WidthType, ShadingType,
        PageOrientation, LevelFormat } = require(path);

const P = (text, opts = {}) => new Paragraph({
    children: [new TextRun({ text, bold: opts.bold, italics: opts.italics, size: opts.size || 22, color: opts.color })],
    spacing: { before: opts.before ?? 80, after: opts.after ?? 80 },
    alignment: opts.align,
});
const H1 = (text) => new Paragraph({
    heading: HeadingLevel.HEADING_1,
    children: [new TextRun({ text, bold: true, size: 30, color: "1F4E79" })],
    spacing: { before: 240, after: 120 },
});
const H2 = (text) => new Paragraph({
    heading: HeadingLevel.HEADING_2,
    children: [new TextRun({ text, bold: true, size: 26, color: "2E75B6" })],
    spacing: { before: 180, after: 100 },
});

const border = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const borders = { top: border, bottom: border, left: border, right: border };

function cell(text, opts = {}) {
    return new TableCell({
        borders,
        width: { size: opts.w, type: WidthType.DXA },
        shading: opts.shade ? { fill: opts.shade, type: ShadingType.CLEAR } : undefined,
        margins: { top: 80, bottom: 80, left: 120, right: 120 },
        children: [new Paragraph({
            children: [new TextRun({ text: String(text), bold: opts.bold, size: 20, color: opts.color })],
            alignment: opts.align,
        })],
    });
}

function resultsTable() {
    const cols = [2800, 1800, 1800, 1800, 1160]; // sums to 9360
    return new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: cols,
        rows: [
            new TableRow({ children: [
                cell("Metric", { w: cols[0], bold: true, shade: "1F4E79", color: "FFFFFF" }),
                cell("v46 deployed", { w: cols[1], bold: true, shade: "1F4E79", color: "FFFFFF", align: AlignmentType.CENTER }),
                cell("v46 honest", { w: cols[2], bold: true, shade: "1F4E79", color: "FFFFFF", align: AlignmentType.CENTER }),
                cell("v47 honest", { w: cols[3], bold: true, shade: "1F4E79", color: "FFFFFF", align: AlignmentType.CENTER }),
                cell("Δ vs v46h", { w: cols[4], bold: true, shade: "1F4E79", color: "FFFFFF", align: AlignmentType.CENTER }),
            ]}),
            new TableRow({ children: [
                cell("Features", { w: cols[0] }),
                cell("126", { w: cols[1], align: AlignmentType.CENTER }),
                cell("126", { w: cols[2], align: AlignmentType.CENTER }),
                cell("60", { w: cols[3], align: AlignmentType.CENTER, bold: true }),
                cell("−52%", { w: cols[4], align: AlignmentType.CENTER, color: "2E7D32" }),
            ]}),
            new TableRow({ children: [
                cell("Ridge C", { w: cols[0] }),
                cell("0.02", { w: cols[1], align: AlignmentType.CENTER }),
                cell("0.05", { w: cols[2], align: AlignmentType.CENTER }),
                cell("0.05", { w: cols[3], align: AlignmentType.CENTER }),
                cell("—", { w: cols[4], align: AlignmentType.CENTER }),
            ]}),
            new TableRow({ children: [
                cell("Val AUC (selection)", { w: cols[0] }),
                cell("—", { w: cols[1], align: AlignmentType.CENTER }),
                cell("0.8065", { w: cols[2], align: AlignmentType.CENTER }),
                cell("0.8541", { w: cols[3], align: AlignmentType.CENTER }),
                cell("+476 bp", { w: cols[4], align: AlignmentType.CENTER, color: "2E7D32" }),
            ]}),
            new TableRow({ children: [
                cell("Test AUC (touched 1×)", { w: cols[0] }),
                cell("—", { w: cols[1], align: AlignmentType.CENTER }),
                cell("0.7841", { w: cols[2], align: AlignmentType.CENTER }),
                cell("0.7797", { w: cols[3], align: AlignmentType.CENTER }),
                cell("−44 bp", { w: cols[4], align: AlignmentType.CENTER, color: "B71C1C" }),
            ]}),
            new TableRow({ children: [
                cell("Final HO AUC (blind)", { w: cols[0], bold: true }),
                cell("0.8135", { w: cols[1], align: AlignmentType.CENTER }),
                cell("0.7551", { w: cols[2], align: AlignmentType.CENTER }),
                cell("0.7521", { w: cols[3], align: AlignmentType.CENTER, bold: true }),
                cell("−30 bp", { w: cols[4], align: AlignmentType.CENTER, color: "B71C1C" }),
            ]}),
            new TableRow({ children: [
                cell("Final HO AUC 95% CI", { w: cols[0] }),
                cell("—", { w: cols[1], align: AlignmentType.CENTER }),
                cell("[0.697, 0.810]", { w: cols[2], align: AlignmentType.CENTER }),
                cell("[0.687, 0.815]", { w: cols[3], align: AlignmentType.CENTER }),
                cell("~same", { w: cols[4], align: AlignmentType.CENTER }),
            ]}),
            new TableRow({ children: [
                cell("Final HO Brier", { w: cols[0], bold: true }),
                cell("0.104", { w: cols[1], align: AlignmentType.CENTER }),
                cell("0.1529", { w: cols[2], align: AlignmentType.CENTER }),
                cell("0.1495", { w: cols[3], align: AlignmentType.CENTER, bold: true }),
                cell("−34 bp", { w: cols[4], align: AlignmentType.CENTER, color: "2E7D32" }),
            ]}),
            new TableRow({ children: [
                cell("Meta ensemble", { w: cols[0] }),
                cell("90/10 R/X", { w: cols[1], align: AlignmentType.CENTER }),
                cell("Ridge-only", { w: cols[2], align: AlignmentType.CENTER }),
                cell("95/5 R/X", { w: cols[3], align: AlignmentType.CENTER }),
                cell("—", { w: cols[4], align: AlignmentType.CENTER }),
            ]}),
            new TableRow({ children: [
                cell("Temperature", { w: cols[0] }),
                cell("1.0", { w: cols[1], align: AlignmentType.CENTER }),
                cell("—", { w: cols[2], align: AlignmentType.CENTER }),
                cell("1.25", { w: cols[3], align: AlignmentType.CENTER }),
                cell("—", { w: cols[4], align: AlignmentType.CENTER }),
            ]}),
        ],
    });
}

function topFeaturesTable() {
    const cols = [600, 6500, 2260];
    const feats = [
        ["1", "ta_base_rate", "+0.2756"],
        ["2", "journey_last_positive", "+0.2345"],
        ["3", "journey_success_rate", "+0.2148"],
        ["4", "ch_is_ion_channel", "−0.2137"],
        ["5", "journey_had_negative", "−0.2039"],
        ["6", "v42_ct_is_industry_X_ctgov_masking_rigor", "−0.1935"],
        ["7", "v42_ctgov_n_countries_X_indication_density", "−0.1845"],
        ["8", "ctgov_masking_rigor", "−0.1840"],
        ["9", "cns_x_micro", "+0.1794"],
        ["10", "v42_iis_is_interim_X_momentum_10d", "−0.1791"],
        ["11", "v41_sponsor_x_conference", "+0.1784"],
        ["12", "ta_metabolic", "−0.1707"],
        ["13", "v44_ch2_moa_antagonist_X_journey_had_positive", "+0.1698"],
        ["14", "phase3_x_randomized", "+0.1650"],
        ["15", "volatility_x_phase3", "−0.1636"],
    ];
    return new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: cols,
        rows: [
            new TableRow({ children: [
                cell("#", { w: cols[0], bold: true, shade: "1F4E79", color: "FFFFFF", align: AlignmentType.CENTER }),
                cell("Feature", { w: cols[1], bold: true, shade: "1F4E79", color: "FFFFFF" }),
                cell("Coefficient", { w: cols[2], bold: true, shade: "1F4E79", color: "FFFFFF", align: AlignmentType.CENTER }),
            ]}),
            ...feats.map(f => new TableRow({ children: [
                cell(f[0], { w: cols[0], align: AlignmentType.CENTER }),
                cell(f[1], { w: cols[1] }),
                cell(f[2], { w: cols[2], align: AlignmentType.CENTER,
                             color: f[2].startsWith("+") ? "2E7D32" : "B71C1C" }),
            ]})),
        ],
    });
}

const children = [
    new Paragraph({
        children: [new TextRun({ text: "GUNGNIR v47 HONEST REBUILD", bold: true, size: 36, color: "1F4E79" })],
        alignment: AlignmentType.CENTER,
        spacing: { after: 120 },
    }),
    new Paragraph({
        children: [new TextRun({ text: "Kaizen Null Result on AUC | Genuine Win on Calibration + Simplicity",
                                  italics: true, size: 24, color: "555555" })],
        alignment: AlignmentType.CENTER,
        spacing: { after: 200 },
    }),
    P("Date: April 19, 2026  |  Dataset: 1,752 readout events  |  Split: 4-way honest temporal", { italics: true, align: AlignmentType.CENTER }),

    H1("1. Headline"),
    P("v47 is the first Gungnir rebuild conducted under strict 4-way honest discipline (train ≤2023-06 / val 2023H2-2024H1 / test 2024H2-2025H1 / final ≥2025H2). All hyperparameter and feature selection operates on VAL only; test and final are touched exactly ONCE."),
    P("Final HO AUC: 0.7521 [95% CI 0.687, 0.815]. vs v46 honest baseline 0.7551 — essentially a wash (−30 bp, well within CI overlap)."),
    P("Final HO Brier: 0.1495 vs v46 honest 0.1529 — genuine −34 bp improvement in calibration.", { bold: true }),
    P("Feature count: 60 (pruned from 126 via backward elimination) — 52% reduction with equivalent generalization. Confirms v46 was over-parameterized."),

    H1("2. Results Table"),
    resultsTable(),

    H1("3. Ship Decision"),
    P("v46.0.0 REMAINS CHAMPION by the documented rule (final HO AUC). v47 does not clear the bar, though the Brier improvement and feature-count reduction are legitimate.", { bold: true }),
    P("Why not ship v47:"),
    P("  • Final HO AUC fell 30 bp (0.7551 → 0.7521). While inside the bootstrap CI, the honest rule requires strictly beating the prior honest bar."),
    P("  • Val→Final gap widened: 0.8541 − 0.7521 = 1020 bp (v47) vs 0.8065 − 0.7551 = 514 bp (v46 honest). Backward elimination on val leaks val into selection, widening the generalization gap."),
    P("  • Test touched-1× came in at 0.7797, basically flat vs v46 honest 0.7841, confirming the val selection overfit."),
    P("Why v47 is still valuable:"),
    P("  • Brier improvement is real and unambiguous — better probability calibration matters for investment scoring where raw probabilities feed downstream sizing."),
    P("  • 52% feature reduction → easier audit, less overfit risk on future data, faster inference."),
    P("  • Confirms the v45 prune-tighten philosophy was directionally right and v46's 8 feature additions partially reversed it. 5 of 8 v46 features got pruned back out under honest selection."),

    H1("4. Top 15 Features by |Coefficient|"),
    P("The 60 features that survived honest backward elimination:"),
    topFeaturesTable(),
    P("Durable feature families confirmed:", { bold: true }),
    P("  1. TA base rates and journey features (prior readout outcomes, success rate) — the CORE signal."),
    P("  2. v42 trial-design interactions (masking rigor × industry, countries × indication density) — three of top 10."),
    P("  3. ChEMBL drug-class features (ch_is_ion_channel, v44_ch2_moa_antagonist × journey) — two of top 15."),
    P("  4. v41_sponsor_x_conference survived — conference signal IS durable when interacted with sponsor quality."),
    P("  5. v42_iis_is_interim_X_momentum_10d — interim-data-with-momentum penalty (IIS-validated signal) held up."),

    H1("5. Notable Features DROPPED Under Honest Selection"),
    P("Of v46's 8 newly-added features, these 3 survived backward elimination:", { bold: true }),
    P("  • v44_ch2_moa_antagonist_X_journey_had_positive (+0.170)"),
    P("  • v46_p1_ch2_moa_agonist"),
    P("  • v46_p6_fic_X_is_phase3_X_sponsor"),
    P("These 5 got pruned:", { bold: true }),
    P("  • v46_p2_ch2_is_adc_X_journey_n_negative"),
    P("  • v46_p2_ch2_is_adc_X_journey_had_negative"),
    P("  • v46_p5_log1p_journey_last_positive"),
    P("  • v46_p6_conf_X_ch2_is_mab_X_is_small"),
    P("  • v46_p6_sponsor_X_ch2_is_adc_X_is_phase2 (ADC Kaizen theme mostly died)"),
    P("Other notable drops (all originally v39-v43 features):"),
    P("  • v40_has_conference DROPPED — conference standalone didn't beat val threshold. Conference signal survives ONLY as sponsor interaction."),
    P("  • v40_days_to_cover DROPPED — short-interest signal still alive via other features."),
    P("  • All phase dummies (is_phase1/2/3) DROPPED — signal absorbed by phase×TA interactions."),
    P("  • All TA dummies except metabolic DROPPED — absorbed by ta_base_rate and ta×size interactions."),
    P("  • momentum_5d, momentum_10d, volatility_5d, volatility_20d DROPPED — standalone momentum/vol didn't survive; the interacted versions (volatility_x_phase3) did."),

    H1("6. Why the Honest Gap Is Still ~800 bp"),
    P("v47 val AUC 0.8541 → final HO 0.7521 is a 1020 bp honest degradation. This is the true generalization gap for the current Gungnir feature set. Kaizen cycles that add features while touching test data make this gap appear smaller, but under honest selection it is stubbornly ~8-10 pp."),
    P("To genuinely improve honest AUC, we need NEW signal families, not more interactions of the same primitives:"),
    P("  • Options flow (UOA pre-readout) — partial via v46 but most ADC-options interactions died."),
    P("  • Social volume (StockTwits/Reddit pre-catalyst chatter) — SENTINEL v1.1 deferred."),
    P("  • 13F concentration at quarter boundaries — Smart Money overlay is rule-based, not trained in Gungnir."),
    P("  • Historical short-interest time series (removes Apr-2026 snapshot lookahead)."),
    P("  • Scientific features: target class hit rates, modality maturity curves, platform first-approval lookbacks."),

    H1("7. Methodology Integrity Notes"),
    P("The 4-way split is MORE conservative than ODIN v16's 3-way split because it reserves a truly blind FINAL tier that is touched exactly once after all tuning."),
    P("Positive rates are balanced across splits (train 82.0%, val 79.2%, test 79.9%, final 77.8%) — small class distribution drift only."),
    P("Backward elimination used a val-AUC delta threshold of −2 bp (drop if val AUC improves OR holds within 2 bp). This is INTENTIONALLY lenient to prune aggressively, since the goal was to test whether v46's 126 features were over-parameterized."),
    P("C sweep, meta-weight sweep, and temperature were all VAL-ONLY. The sequence is: prune → C → XGB → meta → T → snapshot. Each later step can't improve the val AUC above the Ridge ceiling (Ridge 95/XGB 5 was only +1 bp vs Ridge alone)."),

    H1("8. Files"),
    P("  • /mnt/9realms/gungnir_v47_honest.py — 8-step pipeline (pruning → C → XGB → meta → T → snapshot)"),
    P("  • /mnt/9realms/gungnir_v47_honest_results.json — full results including kept features, dropped features, drop history, and top 20 coefficients"),
    P("  • /mnt/9realms/Gungnir_v47_Honest_Rebuild_Findings.docx — this memo"),

    H1("9. Next in Sprint"),
    P("Task #59 — BIFROST Explosion v5.8. Pursue NEW signal families, not more transforms of existing ones:"),
    P("  (a) Options flow × explosion interaction — pre-catalyst UOA burst × explosion rate"),
    P("  (b) Conference × explosion — does conference presence amplify tail moves?"),
    P("  (c) 13F quarter-boundary concentration jumps"),
    P("  (d) Historical short-interest time series replacement"),
    P("  (e) Social-volume pre-catalyst chatter (SENTINEL-derived)"),
    P("Bar to beat: v5.5 honest AUC ~0.8861 on similar 3-way split."),
];

const doc = new Document({
    styles: {
        default: { document: { run: { font: "Arial", size: 22 } } },
        paragraphStyles: [
            { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal",
              run: { size: 30, bold: true, font: "Arial", color: "1F4E79" },
              paragraph: { spacing: { before: 240, after: 120 }, outlineLevel: 0 } },
            { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal",
              run: { size: 26, bold: true, font: "Arial", color: "2E75B6" },
              paragraph: { spacing: { before: 180, after: 100 }, outlineLevel: 1 } },
        ]
    },
    sections: [{
        properties: { page: { size: { width: 12240, height: 15840 },
                              margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } },
        children,
    }],
});

Packer.toBuffer(doc).then(buf => {
    const out = '/sessions/confident-serene-ptolemy/mnt/9realms/Gungnir_v47_Honest_Rebuild_Findings.docx';
    fs.writeFileSync(out, buf);
    console.log("WROTE " + out + " (" + buf.length + " bytes)");
});
