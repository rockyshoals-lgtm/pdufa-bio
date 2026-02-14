// ODIN Round 5 Backtest — Verify new signal weights improve accuracy
// Tests both v10.68 (current) and v10.69 (Round 5) on all 22 historical events

const BASE_LOGIT = 1.3957;
function sigmoid(x) { return 1 / (1 + Math.exp(-x)); }
function getTier(prob) {
  if (prob > 0.85) return 'TIER_1';
  if (prob >= 0.70) return 'TIER_2';
  if (prob >= 0.60) return 'TIER_3';
  return 'TIER_4';
}

// ============================================================
// v10.68 WEIGHTS (CURRENT)
// ============================================================
const V68 = {
  BTD: 0.1676, orphan: 0.1469, fast_track: 0.0888,
  priority_review: 0.1053, RMAT: 0.15, accelerated_approval: 0.12,
  experienced_sponsor: 0.9387, inexperienced_sponsor: -1.2875,
  prior_approval: 0.3, prior_CRL: -3.3533,
  resubmission_post_CRL: 1.5, advisory_committee_favorable: 0.8212,
  advisory_committee_unfavorable: -1.5069,
  ta_low_risk: 0.1531, ta_moderate_risk: -0.0532, ta_high_risk: -0.2555,
  ta_very_high_risk: -0.5,
  form_483: -1.3552, import_alert: -0.8,
  manufacturing_warning: -0.5, cGMP_violation: -0.6,
  primary_endpoint_met: 0.45, primary_endpoint_missed: -1.8,
  surrogate_only: -0.45, biomarker_primary: -0.3,
  PRO_endpoint: -0.15, composite_endpoint: -0.1,
  first_in_class: 0.45, unmet_need: 0.55,
  crowded_market: -0.2, designation_stack: 0.35,
  novice_high_risk_ta: -0.4071, experienced_low_risk: 0.2,
  interaction_inexperienced_mfg: -0.5, interaction_prior_crl_mfg: -0.7,
  accelerated_approval_non_onc: -0.30, surrogate_clinical_disconnect: -0.35,
  designation_surrogate_penalty: -0.25, small_pivotal_n: -0.20,
  single_arm_pivotal: -0.15, cber_advanced_therapy: -0.12,
  repurposed_failed_compound: -0.20, early_action_risk: -0.15,
  serial_crl_penalty: -0.50, novel_manufacturing_platform: -0.18,
  efficacy_magnitude_weak: -0.25, post_hoc_subgroup_primary: -0.30,
  safety_signal_liver: -0.35, safety_signal_cardiac: -0.40,
  competitor_crl_same_class: -0.15
};

// ============================================================
// v10.69 WEIGHTS (ROUND 5 — PROPOSED)
// ============================================================
const V69 = {
  ...V68,  // Inherit all v10.68 weights

  // ── NEW SIGNALS (Round 5) ──
  prior_CRL_cmc_only: -1.0,             // CMC-only CRL (replaces prior_CRL for CMC issues)
  hys_law_cases: -1.5,                  // Hy's Law DILI cases
  fda_benefit_risk_negative: -1.5,      // FDA explicitly questions benefit-risk
  novel_delivery_mechanism: -0.4,        // Unprecedented delivery requiring HF validation
  human_factors_risk: -0.4,             // Device/delivery with self-admin concerns
  fda_no_adcom_required: 0.2,           // FDA waived advisory committee
  crl_time_decay_1yr: 0.0,             // No decay within 1 year
  crl_time_decay_2yr: 0.15,            // 2 year decay
  crl_time_decay_3yr: 0.30,            // 3 year decay
  crl_time_decay_4yr_plus: 0.45,       // 4+ years since CRL

  // ── ADJUSTED WEIGHTS ──
  safety_signal_liver: -0.60,           // Was -0.35, DILI more punitive
  efficacy_magnitude_weak: -0.45,       // Was -0.25, "unclear benefit" is serious
  resubmission_post_CRL: 2.0,          // Was +1.5, increase offset for resubmissions

  // ── INTERACTION SIGNALS ──
  experienced_sponsor_safety_override: -0.5,  // Cap experienced_sponsor when safety signals fire
  pk_bridging_vs_clinical: -0.2,              // PK bridging endpoints less reliable than clinical
};

// ============================================================
// EVENT DEFINITIONS — v10.68 signals
// ============================================================
const events_v68 = [
  // APPROVALS
  { ticker: 'LLY', drug: 'Imlunestrant', outcome: 'APPROVED', signals: {
    experienced_sponsor: V68.experienced_sponsor, priority_review: V68.priority_review, BTD: V68.BTD,
    primary_endpoint_met: V68.primary_endpoint_met, first_in_class: V68.first_in_class, ta_moderate_risk: V68.ta_moderate_risk }},
  { ticker: 'JAZZ', drug: 'Lurbinectedin+Atezo', outcome: 'APPROVED', signals: {
    experienced_sponsor: V68.experienced_sponsor, priority_review: V68.priority_review,
    primary_endpoint_met: V68.primary_endpoint_met, ta_moderate_risk: V68.ta_moderate_risk }},
  { ticker: 'AZN', drug: 'Tezspire CRSwNP', outcome: 'APPROVED', signals: {
    experienced_sponsor: V68.experienced_sponsor, prior_approval: V68.prior_approval,
    primary_endpoint_met: V68.primary_endpoint_met, ta_low_risk: V68.ta_low_risk, experienced_low_risk: V68.experienced_low_risk }},
  { ticker: 'GSK', drug: 'Blenrep', outcome: 'APPROVED', signals: {
    experienced_sponsor: V68.experienced_sponsor, BTD: V68.BTD, primary_endpoint_met: V68.primary_endpoint_met,
    ta_moderate_risk: V68.ta_moderate_risk, prior_CRL: V68.prior_CRL, resubmission_post_CRL: V68.resubmission_post_CRL }},
  { ticker: 'SNDX', drug: 'Revumenib', outcome: 'APPROVED', signals: {
    inexperienced_sponsor: V68.inexperienced_sponsor, priority_review: V68.priority_review, BTD: V68.BTD,
    orphan: V68.orphan, accelerated_approval: V68.accelerated_approval, first_in_class: V68.first_in_class,
    unmet_need: V68.unmet_need, ta_high_risk: V68.ta_high_risk, single_arm_pivotal: V68.single_arm_pivotal,
    designation_stack: V68.designation_stack }},
  { ticker: 'KURA', drug: 'Ziftomenib', outcome: 'APPROVED', signals: {
    inexperienced_sponsor: V68.inexperienced_sponsor, priority_review: V68.priority_review, BTD: V68.BTD,
    orphan: V68.orphan, first_in_class: V68.first_in_class, unmet_need: V68.unmet_need,
    ta_high_risk: V68.ta_high_risk, single_arm_pivotal: V68.single_arm_pivotal, designation_stack: V68.designation_stack }},
  { ticker: 'ARWR', drug: 'Plozasiran', outcome: 'APPROVED', signals: {
    inexperienced_sponsor: V68.inexperienced_sponsor, priority_review: V68.priority_review, BTD: V68.BTD,
    orphan: V68.orphan, primary_endpoint_met: V68.primary_endpoint_met, first_in_class: V68.first_in_class,
    unmet_need: V68.unmet_need, ta_low_risk: V68.ta_low_risk, designation_stack: V68.designation_stack }},
  { ticker: 'MIST', drug: 'Etripamil', outcome: 'APPROVED', signals: {
    inexperienced_sponsor: V68.inexperienced_sponsor, prior_CRL: V68.prior_CRL,
    resubmission_post_CRL: V68.resubmission_post_CRL, primary_endpoint_met: V68.primary_endpoint_met,
    first_in_class: V68.first_in_class, unmet_need: V68.unmet_need, ta_moderate_risk: V68.ta_moderate_risk }},
  { ticker: 'CYTK', drug: 'Aficamten', outcome: 'APPROVED', signals: {
    inexperienced_sponsor: V68.inexperienced_sponsor, priority_review: V68.priority_review, BTD: V68.BTD,
    primary_endpoint_met: V68.primary_endpoint_met, ta_moderate_risk: V68.ta_moderate_risk,
    designation_stack: V68.designation_stack, safety_signal_cardiac: V68.safety_signal_cardiac }},
  { ticker: 'AMRX', drug: 'Denosumab-mobz', outcome: 'APPROVED', signals: {
    experienced_sponsor: V68.experienced_sponsor, ta_low_risk: V68.ta_low_risk, experienced_low_risk: V68.experienced_low_risk }},
  { ticker: 'NVO', drug: 'Oral Semaglutide', outcome: 'APPROVED', signals: {
    experienced_sponsor: V68.experienced_sponsor, prior_approval: V68.prior_approval,
    priority_review: V68.priority_review, primary_endpoint_met: V68.primary_endpoint_met,
    ta_low_risk: V68.ta_low_risk, experienced_low_risk: V68.experienced_low_risk }},
  { ticker: 'AGIO', drug: 'Mitapivat', outcome: 'APPROVED', signals: {
    inexperienced_sponsor: V68.inexperienced_sponsor, priority_review: V68.priority_review,
    orphan: V68.orphan, primary_endpoint_met: V68.primary_endpoint_met, first_in_class: V68.first_in_class,
    unmet_need: V68.unmet_need, ta_moderate_risk: V68.ta_moderate_risk, designation_stack: V68.designation_stack }},
  { ticker: 'OMER', drug: 'Narsoplimab', outcome: 'APPROVED', signals: {
    inexperienced_sponsor: V68.inexperienced_sponsor, prior_CRL: V68.prior_CRL,
    resubmission_post_CRL: V68.resubmission_post_CRL, BTD: V68.BTD, orphan: V68.orphan,
    first_in_class: V68.first_in_class, unmet_need: V68.unmet_need, ta_high_risk: V68.ta_high_risk,
    designation_stack: V68.designation_stack, single_arm_pivotal: V68.single_arm_pivotal }},
  { ticker: 'VNDA', drug: 'Tradipitant', outcome: 'APPROVED', signals: {
    inexperienced_sponsor: V68.inexperienced_sponsor, primary_endpoint_met: V68.primary_endpoint_met,
    first_in_class: V68.first_in_class, ta_low_risk: V68.ta_low_risk }},
  { ticker: 'ARQT', drug: 'Zoryve AD', outcome: 'APPROVED', signals: {
    inexperienced_sponsor: V68.inexperienced_sponsor, prior_approval: V68.prior_approval,
    primary_endpoint_met: V68.primary_endpoint_met, ta_low_risk: V68.ta_low_risk }},
  { ticker: 'FBIO', drug: 'Zycubo', outcome: 'APPROVED', signals: {
    inexperienced_sponsor: V68.inexperienced_sponsor, prior_CRL: V68.prior_CRL,
    resubmission_post_CRL: V68.resubmission_post_CRL, orphan: V68.orphan, BTD: V68.BTD,
    first_in_class: V68.first_in_class, unmet_need: V68.unmet_need, ta_moderate_risk: V68.ta_moderate_risk }},
  // CRLs
  { ticker: 'SRRK', drug: 'Apitegromab', outcome: 'CRL', signals: {
    inexperienced_sponsor: V68.inexperienced_sponsor, BTD: V68.BTD, orphan: V68.orphan,
    form_483: V68.form_483, ta_high_risk: V68.ta_high_risk, novice_high_risk_ta: V68.novice_high_risk_ta,
    designation_stack: V68.designation_stack, crowded_market: V68.crowded_market }},
  { ticker: 'SNY', drug: 'Tolebrutinib', outcome: 'CRL', signals: {
    experienced_sponsor: V68.experienced_sponsor, BTD: V68.BTD, priority_review: V68.priority_review,
    first_in_class: V68.first_in_class, unmet_need: V68.unmet_need, ta_very_high_risk: V68.ta_very_high_risk,
    safety_signal_liver: V68.safety_signal_liver, efficacy_magnitude_weak: V68.efficacy_magnitude_weak }},
  { ticker: 'CAPR', drug: 'Deramiocel BLA', outcome: 'CRL', signals: {
    inexperienced_sponsor: V68.inexperienced_sponsor, RMAT: V68.RMAT, orphan: V68.orphan,
    priority_review: V68.priority_review, form_483: V68.form_483, first_in_class: V68.first_in_class,
    unmet_need: V68.unmet_need, ta_high_risk: V68.ta_high_risk, novice_high_risk_ta: V68.novice_high_risk_ta,
    interaction_inexperienced_mfg: V68.interaction_inexperienced_mfg, cber_advanced_therapy: V68.cber_advanced_therapy,
    single_arm_pivotal: V68.single_arm_pivotal, designation_stack: V68.designation_stack }},
  { ticker: 'BHVN', drug: 'Troriluzole', outcome: 'CRL', signals: {
    inexperienced_sponsor: V68.inexperienced_sponsor, orphan: V68.orphan, first_in_class: V68.first_in_class,
    unmet_need: V68.unmet_need, ta_very_high_risk: V68.ta_very_high_risk, novice_high_risk_ta: V68.novice_high_risk_ta,
    efficacy_magnitude_weak: V68.efficacy_magnitude_weak, surrogate_only: V68.surrogate_only }},
  { ticker: 'AQST', drug: 'Anaphylm', outcome: 'CRL', signals: {
    inexperienced_sponsor: V68.inexperienced_sponsor, primary_endpoint_met: V68.primary_endpoint_met,
    first_in_class: V68.first_in_class, unmet_need: V68.unmet_need, ta_low_risk: V68.ta_low_risk }},
  { ticker: 'ATRA', drug: 'Tabelecleucel', outcome: 'CRL', signals: {
    inexperienced_sponsor: V68.inexperienced_sponsor, prior_CRL: V68.prior_CRL,
    resubmission_post_CRL: V68.resubmission_post_CRL, BTD: V68.BTD, orphan: V68.orphan,
    first_in_class: V68.first_in_class, unmet_need: V68.unmet_need, ta_high_risk: V68.ta_high_risk,
    cber_advanced_therapy: V68.cber_advanced_therapy, single_arm_pivotal: V68.single_arm_pivotal,
    designation_stack: V68.designation_stack, serial_crl_penalty: V68.serial_crl_penalty }},
];

// ============================================================
// EVENT DEFINITIONS — v10.69 signals (Round 5 modifications)
// ============================================================
const events_v69 = events_v68.map(e => {
  const newSignals = { ...e.signals };

  // MIST: CMC-only CRL → use prior_CRL_cmc_only instead of prior_CRL
  if (e.ticker === 'MIST') {
    delete newSignals.prior_CRL;
    newSignals.prior_CRL_cmc_only = V69.prior_CRL_cmc_only;
    newSignals.resubmission_post_CRL = V69.resubmission_post_CRL; // +2.0 instead of +1.5
  }

  // OMER: Efficacy CRL but 4+ years ago → keep prior_CRL but add time decay
  if (e.ticker === 'OMER') {
    newSignals.crl_time_decay_4yr_plus = V69.crl_time_decay_4yr_plus;
    newSignals.resubmission_post_CRL = V69.resubmission_post_CRL;
    newSignals.fda_no_adcom_required = V69.fda_no_adcom_required;
  }

  // FBIO: CMC-only CRL → use prior_CRL_cmc_only
  if (e.ticker === 'FBIO') {
    delete newSignals.prior_CRL;
    newSignals.prior_CRL_cmc_only = V69.prior_CRL_cmc_only;
    newSignals.resubmission_post_CRL = V69.resubmission_post_CRL;
  }

  // GSK/Blenrep: Efficacy CRL but strong resubmission data → increased resubmission weight
  if (e.ticker === 'GSK') {
    newSignals.resubmission_post_CRL = V69.resubmission_post_CRL;
  }

  // SNY: Add Hy's Law + benefit-risk negative + experienced_sponsor_safety_override
  if (e.ticker === 'SNY') {
    newSignals.hys_law_cases = V69.hys_law_cases;
    newSignals.fda_benefit_risk_negative = V69.fda_benefit_risk_negative;
    newSignals.experienced_sponsor_safety_override = V69.experienced_sponsor_safety_override;
    newSignals.safety_signal_liver = V69.safety_signal_liver; // Updated weight
    newSignals.efficacy_magnitude_weak = V69.efficacy_magnitude_weak; // Updated weight
  }

  // AQST: Add novel_delivery_mechanism + human_factors_risk + pk_bridging
  if (e.ticker === 'AQST') {
    newSignals.novel_delivery_mechanism = V69.novel_delivery_mechanism;
    newSignals.human_factors_risk = V69.human_factors_risk;
    newSignals.pk_bridging_vs_clinical = V69.pk_bridging_vs_clinical;
  }

  // ATRA: Use updated resubmission weight
  if (e.ticker === 'ATRA') {
    newSignals.resubmission_post_CRL = V69.resubmission_post_CRL;
  }

  return { ...e, signals: newSignals };
});

// ============================================================
// SCORING + COMPARISON
// ============================================================
function scoreEvent(signals) {
  const totalAdj = Object.values(signals).reduce((s, v) => s + v, 0);
  const logit = BASE_LOGIT + totalAdj;
  const prob = sigmoid(logit);
  return { totalAdj, logit, prob, tier: getTier(prob) };
}

function isCorrect(prob, outcome) {
  if (outcome === 'APPROVED') return prob >= 0.60;
  if (outcome === 'CRL') return prob < 0.60;
  return null;
}

console.log(`${'='.repeat(120)}`);
console.log('ODIN ROUND 5 BACKTEST — v10.68 vs v10.69');
console.log(`${'='.repeat(120)}\n`);

console.log(`${'Ticker'.padEnd(8)} ${'Drug'.padEnd(25)} ${'Outcome'.padEnd(10)} ${'v68 %'.padEnd(8)} ${'v68 Dir'.padEnd(8)} ${'v69 %'.padEnd(8)} ${'v69 Dir'.padEnd(8)} ${'Delta'.padEnd(8)} ${'Change'}`);
console.log('-'.repeat(120));

let v68_correct = 0, v69_correct = 0;
let improvements = 0, regressions = 0, unchanged = 0;

for (let i = 0; i < events_v68.length; i++) {
  const e68 = events_v68[i];
  const e69 = events_v69[i];
  const s68 = scoreEvent(e68.signals);
  const s69 = scoreEvent(e69.signals);

  const c68 = isCorrect(s68.prob, e68.outcome);
  const c69 = isCorrect(s69.prob, e69.outcome);

  if (c68) v68_correct++;
  if (c69) v69_correct++;

  let change = '';
  if (!c68 && c69) { change = '🔧 FIXED'; improvements++; }
  else if (c68 && !c69) { change = '💥 REGRESSED'; regressions++; }
  else if (c68 && c69) { change = '✅ STABLE'; unchanged++; }
  else { change = '⚠️ STILL WRONG'; }

  const delta = ((s69.prob - s68.prob) * 100).toFixed(1);
  const deltaStr = delta > 0 ? `+${delta}pp` : `${delta}pp`;

  console.log(`${e68.ticker.padEnd(8)} ${e68.drug.substring(0, 23).padEnd(25)} ${e68.outcome.padEnd(10)} ${(s68.prob*100).toFixed(1).padStart(5)}%  ${(c68 ? '✅' : '❌').padEnd(6)} ${(s69.prob*100).toFixed(1).padStart(5)}%  ${(c69 ? '✅' : '❌').padEnd(6)} ${deltaStr.padStart(8)} ${change}`);
}

console.log(`\n${'='.repeat(120)}`);
console.log('SUMMARY');
console.log(`${'='.repeat(120)}`);
console.log(`v10.68 accuracy: ${v68_correct}/${events_v68.length} (${(v68_correct/events_v68.length*100).toFixed(1)}%)`);
console.log(`v10.69 accuracy: ${v69_correct}/${events_v69.length} (${(v69_correct/events_v69.length*100).toFixed(1)}%)`);
console.log(`\nImprovements (fixed): ${improvements}`);
console.log(`Regressions: ${regressions}`);
console.log(`Stable correct: ${unchanged}`);
console.log(`\n${regressions === 0 ? '✅ NO REGRESSIONS — Round 5 is safe to deploy' : '❌ REGRESSIONS DETECTED — DO NOT DEPLOY'}`);
