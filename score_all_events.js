// ODIN v10.68 — Score ALL historical events from Sept 2025 - Feb 2026
// Reconstructs signal profiles from research data and scores through current engine

const BASE_LOGIT = 1.3957;

function sigmoid(x) { return 1 / (1 + Math.exp(-x)); }
function getTier(prob) {
  if (prob > 0.85) return 'TIER_1';
  if (prob >= 0.70) return 'TIER_2';
  if (prob >= 0.60) return 'TIER_3';
  return 'TIER_4';
}
function getAction(tier) {
  return (tier === 'TIER_1' || tier === 'TIER_2') ? 'BUY' : (tier === 'TIER_3' ? 'RUNUP_ONLY' : 'AVOID');
}

// Signal weight reference (v10.68)
const W = {
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

function score(signals) {
  const totalAdj = Object.values(signals).reduce((s, v) => s + v, 0);
  const logit = BASE_LOGIT + totalAdj;
  const prob = sigmoid(logit);
  return { totalAdj: Math.round(totalAdj * 10000) / 10000, logit: Math.round(logit * 10000) / 10000, prob: Math.round(prob * 10000) / 10000, tier: getTier(prob), action: getAction(getTier(prob)) };
}

// ============================================================
// EVENT SIGNAL PROFILES — Reconstructed from research
// ============================================================

const events = [
  // --- APPROVALS ---
  {
    ticker: 'LLY', drug: 'Imlunestrant (Inluriyo)', indication: 'ER+/HER2- breast cancer',
    outcome: 'APPROVED', date: '2025-10-02', ta: 'Oncology',
    signals: {
      experienced_sponsor: W.experienced_sponsor,    // Eli Lilly = mega-cap experienced
      priority_review: W.priority_review,             // Priority Review
      BTD: W.BTD,                                     // Breakthrough
      primary_endpoint_met: W.primary_endpoint_met,   // Phase 3 EMBER-3 met PFS
      first_in_class: W.first_in_class,               // Oral SERD
      ta_moderate_risk: W.ta_moderate_risk,            // Oncology moderate risk
    }
  },
  {
    ticker: 'JAZZ', drug: 'Lurbinectedin+Atezo', indication: 'ES-SCLC maintenance',
    outcome: 'APPROVED', date: '2025-10-02', ta: 'Oncology',
    signals: {
      experienced_sponsor: W.experienced_sponsor,
      priority_review: W.priority_review,
      primary_endpoint_met: W.primary_endpoint_met,
      ta_moderate_risk: W.ta_moderate_risk,
    }
  },
  {
    ticker: 'AZN', drug: 'Tezepelumab (Tezspire) CRSwNP', indication: 'Nasal polyps',
    outcome: 'APPROVED', date: '2025-10-17', ta: 'Immunology',
    signals: {
      experienced_sponsor: W.experienced_sponsor,    // AstraZeneca/Amgen
      prior_approval: W.prior_approval,              // Already approved for asthma
      primary_endpoint_met: W.primary_endpoint_met,
      ta_low_risk: W.ta_low_risk,                    // Immunology = low risk TA
      experienced_low_risk: W.experienced_low_risk,  // Interaction
    }
  },
  {
    ticker: 'GSK', drug: 'Belantamab mafodotin (Blenrep)', indication: 'R/R Multiple Myeloma',
    outcome: 'APPROVED', date: '2025-10-24', ta: 'Oncology',
    signals: {
      experienced_sponsor: W.experienced_sponsor,
      BTD: W.BTD,
      primary_endpoint_met: W.primary_endpoint_met,
      ta_moderate_risk: W.ta_moderate_risk,
      prior_CRL: W.prior_CRL,                        // Previously withdrawn/CRL
      resubmission_post_CRL: W.resubmission_post_CRL,// Resubmitted with new data (DREAMM-7)
    }
  },
  {
    ticker: 'SNDX', drug: 'Revumenib (Revuforj)', indication: 'R/R NPM1-mutated AML',
    outcome: 'APPROVED', date: '2025-11-06', ta: 'Oncology',
    signals: {
      inexperienced_sponsor: W.inexperienced_sponsor, // Syndax is small biotech
      priority_review: W.priority_review,
      BTD: W.BTD,
      orphan: W.orphan,
      accelerated_approval: W.accelerated_approval,
      first_in_class: W.first_in_class,               // First menin inhibitor (already approved = prior approval pathway)
      unmet_need: W.unmet_need,
      ta_high_risk: W.ta_high_risk,                    // Oncology hematology
      single_arm_pivotal: W.single_arm_pivotal,        // AUGMENT-101 single arm
      designation_stack: W.designation_stack,           // BTD + orphan + priority
    }
  },
  {
    ticker: 'KURA', drug: 'Ziftomenib (Komzifti)', indication: 'R/R NPM1-mutated AML',
    outcome: 'APPROVED', date: '2025-11-13', ta: 'Oncology',
    signals: {
      inexperienced_sponsor: W.inexperienced_sponsor,  // Kura is small biotech
      priority_review: W.priority_review,
      BTD: W.BTD,
      orphan: W.orphan,
      first_in_class: W.first_in_class,
      unmet_need: W.unmet_need,
      ta_high_risk: W.ta_high_risk,
      single_arm_pivotal: W.single_arm_pivotal,
      designation_stack: W.designation_stack,
    }
  },
  {
    ticker: 'ARWR', drug: 'Plozasiran (Redemplo)', indication: 'FCS triglycerides',
    outcome: 'APPROVED', date: '2025-11-18', ta: 'Cardio/Rare',
    signals: {
      inexperienced_sponsor: W.inexperienced_sponsor,  // Arrowhead first FDA approval
      priority_review: W.priority_review,
      BTD: W.BTD,
      orphan: W.orphan,
      primary_endpoint_met: W.primary_endpoint_met,     // PALISADE met primary
      first_in_class: W.first_in_class,                 // First siRNA for FCS
      unmet_need: W.unmet_need,
      ta_low_risk: W.ta_low_risk,                       // Rare disease, not high-risk TA
      designation_stack: W.designation_stack,
    }
  },
  {
    ticker: 'MIST', drug: 'Etripamil (Cardamyst)', indication: 'PSVT',
    outcome: 'APPROVED', date: '2025-12-12', ta: 'Cardiology',
    signals: {
      inexperienced_sponsor: W.inexperienced_sponsor,  // Milestone Pharma
      prior_CRL: W.prior_CRL,                          // CRL March 2025 (CMC/nitrosamines)
      resubmission_post_CRL: W.resubmission_post_CRL,  // Resubmitted after fixing CMC
      primary_endpoint_met: W.primary_endpoint_met,
      first_in_class: W.first_in_class,                 // First nasal spray for PSVT
      unmet_need: W.unmet_need,
      ta_moderate_risk: W.ta_moderate_risk,
    }
  },
  {
    ticker: 'CYTK', drug: 'Aficamten (Myqorzo)', indication: 'Obstructive HCM',
    outcome: 'APPROVED', date: '2025-12-19', ta: 'Cardiology',
    signals: {
      inexperienced_sponsor: W.inexperienced_sponsor,  // Cytokinetics (first solo approval)
      priority_review: W.priority_review,
      BTD: W.BTD,
      primary_endpoint_met: W.primary_endpoint_met,     // SEQUOIA-HCM met primary
      ta_moderate_risk: W.ta_moderate_risk,
      designation_stack: W.designation_stack,
      safety_signal_cardiac: W.safety_signal_cardiac,   // Cardiac safety monitoring required
    }
  },
  {
    ticker: 'AMRX', drug: 'Denosumab-mobz (Boncresa)', indication: 'Biosimilar',
    outcome: 'APPROVED', date: '2025-12-22', ta: 'Biosimilar',
    signals: {
      experienced_sponsor: W.experienced_sponsor,       // Amneal has multiple approved drugs
      ta_low_risk: W.ta_low_risk,                       // Biosimilars = low risk
      experienced_low_risk: W.experienced_low_risk,
    }
  },
  {
    ticker: 'NVO', drug: 'Oral Semaglutide (Wegovy pill)', indication: 'Obesity',
    outcome: 'APPROVED', date: '2025-12-22', ta: 'Metabolic',
    signals: {
      experienced_sponsor: W.experienced_sponsor,       // Novo Nordisk
      prior_approval: W.prior_approval,                 // Semaglutide already approved multiple forms
      priority_review: W.priority_review,
      primary_endpoint_met: W.primary_endpoint_met,     // OASIS 4 met primary
      ta_low_risk: W.ta_low_risk,
      experienced_low_risk: W.experienced_low_risk,
    }
  },
  {
    ticker: 'AGIO', drug: 'Mitapivat (Aqvesme)', indication: 'Thalassemia',
    outcome: 'APPROVED', date: '2025-12-23', ta: 'Hematology/Rare',
    signals: {
      inexperienced_sponsor: W.inexperienced_sponsor,  // Agios (small biotech)
      priority_review: W.priority_review,
      orphan: W.orphan,
      primary_endpoint_met: W.primary_endpoint_met,
      first_in_class: W.first_in_class,                // First PK activator for thalassemia
      unmet_need: W.unmet_need,
      ta_moderate_risk: W.ta_moderate_risk,
      designation_stack: W.designation_stack,
    }
  },
  {
    ticker: 'OMER', drug: 'Narsoplimab (Yartemlea)', indication: 'TA-TMA',
    outcome: 'APPROVED', date: '2025-12-23', ta: 'Hematology/Rare',
    signals: {
      inexperienced_sponsor: W.inexperienced_sponsor,  // Omeros
      prior_CRL: W.prior_CRL,                          // CRL Oct 2021
      resubmission_post_CRL: W.resubmission_post_CRL,
      BTD: W.BTD,
      orphan: W.orphan,
      first_in_class: W.first_in_class,                // First lectin pathway inhibitor
      unmet_need: W.unmet_need,
      ta_high_risk: W.ta_high_risk,                    // Hematology, high severity
      designation_stack: W.designation_stack,
      single_arm_pivotal: W.single_arm_pivotal,        // Single arm study
    }
  },
  {
    ticker: 'VNDA', drug: 'Tradipitant (Nereus)', indication: 'Motion sickness',
    outcome: 'APPROVED', date: '2025-12-30', ta: 'Neurology',
    signals: {
      inexperienced_sponsor: W.inexperienced_sponsor,  // Vanda
      primary_endpoint_met: W.primary_endpoint_met,
      first_in_class: W.first_in_class,                // First NK-1 for motion sickness
      ta_low_risk: W.ta_low_risk,                      // Motion sickness = low TA risk
    }
  },
  {
    ticker: 'ARQT', drug: 'Roflumilast (Zoryve) AD 2-5yr', indication: 'Atopic dermatitis children',
    outcome: 'APPROVED', date: '2025-10-06', ta: 'Dermatology',
    signals: {
      inexperienced_sponsor: W.inexperienced_sponsor,  // Arcutis
      prior_approval: W.prior_approval,                // Zoryve already approved
      primary_endpoint_met: W.primary_endpoint_met,
      ta_low_risk: W.ta_low_risk,                      // Dermatology = low risk
    }
  },
  {
    ticker: 'FBIO', drug: 'Copper histidinate (Zycubo)', indication: 'Menkes disease',
    outcome: 'APPROVED', date: '2026-01-12', ta: 'Rare/Genetic',
    signals: {
      inexperienced_sponsor: W.inexperienced_sponsor,  // Fortress/Sentynl
      prior_CRL: W.prior_CRL,                          // CRL Oct 2025 (CMC)
      resubmission_post_CRL: W.resubmission_post_CRL,
      orphan: W.orphan,
      BTD: W.BTD,
      first_in_class: W.first_in_class,
      unmet_need: W.unmet_need,
      ta_moderate_risk: W.ta_moderate_risk,
    }
  },

  // --- CRLs ---
  {
    ticker: 'SRRK', drug: 'Apitegromab', indication: 'SMA',
    outcome: 'CRL', date: '2025-09-24', ta: 'Neurology/Rare',
    signals: {
      inexperienced_sponsor: W.inexperienced_sponsor,
      BTD: W.BTD,
      orphan: W.orphan,
      form_483: W.form_483,                            // CMC facility issue (Catalent)
      ta_high_risk: W.ta_high_risk,                    // Neurology = high risk
      novice_high_risk_ta: W.novice_high_risk_ta,      // Inexperienced + high risk TA
      designation_stack: W.designation_stack,
      crowded_market: W.crowded_market,                // Spinraza already approved
    }
  },
  {
    ticker: 'SNY', drug: 'Tolebrutinib', indication: 'nrSPMS',
    outcome: 'CRL', date: '2025-12-24', ta: 'Neurology',
    signals: {
      experienced_sponsor: W.experienced_sponsor,       // Sanofi = big pharma
      BTD: W.BTD,
      priority_review: W.priority_review,
      first_in_class: W.first_in_class,                 // Brain-penetrant BTK inhibitor for MS
      unmet_need: W.unmet_need,                         // No approved tx for nrSPMS
      ta_very_high_risk: W.ta_very_high_risk,           // Progressive MS = very high risk
      safety_signal_liver: W.safety_signal_liver,       // DILI cases, Hy's Law
      efficacy_magnitude_weak: W.efficacy_magnitude_weak,// FDA: "unclear benefit"
    }
  },
  {
    ticker: 'CAPR', drug: 'Deramiocel BLA', indication: 'DMD cardiomyopathy',
    outcome: 'CRL', date: '2025-07-11', ta: 'Rare/CBER',
    signals: {
      inexperienced_sponsor: W.inexperienced_sponsor,
      RMAT: W.RMAT,
      orphan: W.orphan,
      priority_review: W.priority_review,
      form_483: W.form_483,                             // Form 483 at San Diego facility
      first_in_class: W.first_in_class,
      unmet_need: W.unmet_need,
      ta_high_risk: W.ta_high_risk,
      novice_high_risk_ta: W.novice_high_risk_ta,
      interaction_inexperienced_mfg: W.interaction_inexperienced_mfg,
      cber_advanced_therapy: W.cber_advanced_therapy,
      single_arm_pivotal: W.single_arm_pivotal,        // HOPE-2 was open-label
      designation_stack: W.designation_stack,
    }
  },
  {
    ticker: 'BHVN', drug: 'Troriluzole (Vyglxia)', indication: 'SCA',
    outcome: 'CRL', date: '2025-11-04', ta: 'Neurology/Rare',
    signals: {
      inexperienced_sponsor: W.inexperienced_sponsor,  // Biohaven
      orphan: W.orphan,
      first_in_class: W.first_in_class,
      unmet_need: W.unmet_need,
      ta_very_high_risk: W.ta_very_high_risk,          // Neurodegenerative = very high risk
      novice_high_risk_ta: W.novice_high_risk_ta,
      efficacy_magnitude_weak: W.efficacy_magnitude_weak,// External control issues
      surrogate_only: W.surrogate_only,                 // Clinical outcome surrogate debate
    }
  },
  {
    ticker: 'AQST', drug: 'Anaphylm', indication: 'Anaphylaxis',
    outcome: 'CRL', date: '2026-01-30', ta: 'Allergy',
    signals: {
      inexperienced_sponsor: W.inexperienced_sponsor,  // Aquestive
      primary_endpoint_met: W.primary_endpoint_met,    // PK bridging met
      first_in_class: W.first_in_class,                // First oral epinephrine
      unmet_need: W.unmet_need,
      ta_low_risk: W.ta_low_risk,                      // Allergy = low risk
    }
  },
  {
    ticker: 'ATRA', drug: 'Tabelecleucel (Ebvallo)', indication: 'EBV+ PTLD',
    outcome: 'CRL', date: '2026-01-09', ta: 'Oncology/CBER',
    signals: {
      inexperienced_sponsor: W.inexperienced_sponsor,  // Atara/Pierre Fabre
      prior_CRL: W.prior_CRL,                          // CRL Jan 2025 (CMC)
      resubmission_post_CRL: W.resubmission_post_CRL,
      BTD: W.BTD,
      orphan: W.orphan,
      first_in_class: W.first_in_class,
      unmet_need: W.unmet_need,
      ta_high_risk: W.ta_high_risk,
      cber_advanced_therapy: W.cber_advanced_therapy,
      single_arm_pivotal: W.single_arm_pivotal,        // ALLELE study
      designation_stack: W.designation_stack,
      serial_crl_penalty: W.serial_crl_penalty,        // 2nd CRL
    }
  },
];

// ============================================================
// SCORE ALL EVENTS
// ============================================================

console.log(`${'='.repeat(100)}`);
console.log('ODIN v10.68 — COMPREHENSIVE HISTORICAL SCORING');
console.log(`${'='.repeat(100)}`);
console.log(`Events scored: ${events.length}`);
console.log(`Base logit: ${BASE_LOGIT}\n`);

console.log(`${'Ticker'.padEnd(8)} ${'Drug'.padEnd(35)} ${'Prob'.padEnd(8)} ${'Tier'.padEnd(8)} ${'Action'.padEnd(12)} ${'Outcome'.padEnd(10)} ${'Correct?'.padEnd(10)} ${'Sigs'}`);
console.log('-'.repeat(110));

let correct = 0;
let incorrect = 0;
let results = [];

for (const e of events) {
  const s = score(e.signals);
  const isApproval = e.outcome === 'APPROVED';
  const isCRL = e.outcome === 'CRL';

  // Directional correctness: BUY/RUNUP_ONLY for approvals, AVOID for CRLs
  let directionallyCorrect;
  if (isApproval) {
    directionallyCorrect = s.prob >= 0.60; // Would have traded/runup
  } else if (isCRL) {
    directionallyCorrect = s.prob < 0.60; // Would have avoided
  }

  if (directionallyCorrect) correct++;
  else incorrect++;

  const flag = directionallyCorrect ? '✅' : '❌';
  console.log(`${e.ticker.padEnd(8)} ${e.drug.substring(0, 33).padEnd(35)} ${(s.prob*100).toFixed(1).padStart(5)}%  ${s.tier.padEnd(8)} ${s.action.padEnd(12)} ${e.outcome.padEnd(10)} ${flag.padEnd(10)} ${Object.keys(e.signals).length}`);

  results.push({ ...e, ...s, directionallyCorrect });
}

// ============================================================
// SUMMARY
// ============================================================

console.log(`\n${'='.repeat(100)}`);
console.log('DIRECTIONAL ACCURACY SUMMARY');
console.log(`${'='.repeat(100)}`);
console.log(`Total events scored: ${events.length}`);
console.log(`Correct directional calls: ${correct}`);
console.log(`Incorrect directional calls: ${incorrect}`);
console.log(`Accuracy: ${(correct / events.length * 100).toFixed(1)}%`);

// Show misses in detail
const misses = results.filter(r => !r.directionallyCorrect);
if (misses.length > 0) {
  console.log(`\n--- MISSES (Incorrect Directional Calls) ---`);
  for (const m of misses) {
    console.log(`\n${m.ticker} | ${m.drug} | ${m.outcome}`);
    console.log(`  ODIN Score: ${(m.prob*100).toFixed(1)}% | Tier: ${m.tier} | Action: ${m.action}`);
    console.log(`  Expected: ${m.outcome === 'APPROVED' ? '≥60% (would trade)' : '<60% (would avoid)'}`);
    console.log(`  Error: ${m.outcome === 'APPROVED' ? 'FALSE NEGATIVE (missed approval)' : 'FALSE POSITIVE (missed CRL)'}`);
    console.log(`  Signals:`);
    for (const [k, v] of Object.entries(m.signals)) {
      console.log(`    ${v >= 0 ? '+' : ''}${v.toFixed(4).padStart(8)}  ${k}`);
    }
    console.log(`  Total adj: ${m.totalAdj} | Logit: ${m.logit}`);
  }
}

// Approval vs CRL breakdown
const approvals = results.filter(r => r.outcome === 'APPROVED');
const crls = results.filter(r => r.outcome === 'CRL');

console.log(`\n--- BREAKDOWN BY OUTCOME ---`);
console.log(`Approvals scored correctly: ${approvals.filter(r => r.directionallyCorrect).length}/${approvals.length} (${(approvals.filter(r => r.directionallyCorrect).length / approvals.length * 100).toFixed(1)}%)`);
console.log(`CRLs scored correctly: ${crls.filter(r => r.directionallyCorrect).length}/${crls.length} (${(crls.filter(r => r.directionallyCorrect).length / crls.length * 100).toFixed(1)}%)`);

// Show score distribution
console.log(`\n--- SCORE DISTRIBUTION ---`);
console.log(`Approvals — avg prob: ${(approvals.reduce((s, r) => s + r.prob, 0) / approvals.length * 100).toFixed(1)}%`);
console.log(`CRLs — avg prob: ${(crls.reduce((s, r) => s + r.prob, 0) / crls.length * 100).toFixed(1)}%`);
console.log(`Separation: ${((approvals.reduce((s, r) => s + r.prob, 0) / approvals.length - crls.reduce((s, r) => s + r.prob, 0) / crls.length) * 100).toFixed(1)}pp`);
