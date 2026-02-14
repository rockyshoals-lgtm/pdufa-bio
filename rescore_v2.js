// ODIN v10.68 Regression Test — Rescore all catalysts from scratch
// Base logit from historical FDA approval rate
const BASE_LOGIT = 1.3957;

// Tier thresholds
function getTier(prob) {
  if (prob > 0.85) return 'TIER_1';
  if (prob >= 0.70) return 'TIER_2';
  if (prob >= 0.60) return 'TIER_3';
  return 'TIER_4';
}

// Verified wins from the momentum analysis file
const VERIFIED_TICKERS = {
  'CAPR': { origScore: 0.75, outcome: 'WIN', return: '+404%', action: 'TRADED' },
  'MIST': { origScore: 0.72, outcome: 'WIN', return: '+130%', action: 'TRADED' },
  'TOVX': { origScore: 0.72, outcome: 'WIN', return: '+92%', action: 'TRADED' },
  'ARWR': { origScore: 0.91, outcome: 'WIN', return: '+52%', action: 'TRADED' },
  'SNDX': { origScore: 0.85, outcome: 'WIN', return: '+51%', action: 'TRADED' },
  'KURA': { origScore: 0.88, outcome: 'WIN', return: '+45%', action: 'TRADED' },
  'ARCT': { origScore: 0.90, outcome: 'WIN', return: '+27%', action: 'TRADED' },
  'CYTK': { origScore: 0.92, outcome: 'WIN', return: '+25%', action: 'TRADED' },
  'AMRX': { origScore: 0.85, outcome: 'WIN', return: '+24%', action: 'TRADED' },
  'AGIO': { origScore: 0.82, outcome: 'WIN', return: '+23%', action: 'TRADED' },
  'NVO':  { origScore: 0.95, outcome: 'WIN', return: '+13%', action: 'TRADED' },
  'AZN':  { origScore: 0.92, outcome: 'WIN', return: '+8%', action: 'TRADED' },
  'BHVN': { origScore: 0.38, outcome: 'CRL', return: '-43.8%', action: 'AVOIDED' },
  'RGNX': { origScore: 0.45, outcome: 'CRL', return: '-1.7%', action: 'AVOIDED' },
  'ASND': { origScore: 0.58, outcome: 'DELAY', return: '-0.7%', action: 'AVOIDED' },
};

// Read and parse the JSX file
const fs = require('fs');
const content = fs.readFileSync('/sessions/charming-eager-brahmagupta/pdufa-bio/src/App.jsx', 'utf8');

// Extract the CATALYSTS_DATA array
const startMarker = 'const CATALYSTS_DATA = [';
const startIdx = content.indexOf(startMarker);
let bracketCount = 0;
let endIdx = startIdx + startMarker.length - 1; // position of '['

for (let i = endIdx; i < content.length; i++) {
  if (content[i] === '[') bracketCount++;
  if (content[i] === ']') bracketCount--;
  if (bracketCount === 0) {
    endIdx = i + 1;
    break;
  }
}

const arrayStr = content.substring(startIdx + startMarker.length - 1, endIdx);

// Parse using eval (safe for known local file)
let catalysts;
try {
  catalysts = eval(arrayStr);
} catch(e) {
  console.error('Failed to parse CATALYSTS_DATA:', e.message);
  process.exit(1);
}

console.log(`\n${'='.repeat(80)}`);
console.log('ODIN v10.68 REGRESSION TEST — FULL RESCORE');
console.log(`${'='.repeat(80)}`);
console.log(`Total catalysts in database: ${catalysts.length}`);
console.log(`Base logit: ${BASE_LOGIT}`);
console.log(`\n`);

// Rescore every catalyst
let mismatches = 0;
let totalChecked = 0;
let verifiedFound = [];

const results = catalysts.map(c => {
  const signals = c.signals || {};
  const signalKeys = Object.keys(signals);
  const recalcTotalAdj = signalKeys.reduce((sum, k) => sum + signals[k], 0);
  const recalcLogit = BASE_LOGIT + recalcTotalAdj;
  const recalcProb = 1 / (1 + Math.exp(-recalcLogit));
  const recalcTier = getTier(recalcProb);

  const probDiff = Math.abs(recalcProb - c.prob);
  const adjDiff = Math.abs(recalcTotalAdj - (c.totalAdj || 0));
  const logitDiff = Math.abs(recalcLogit - (c.logit || 0));
  const tierMatch = recalcTier === c.tier;

  totalChecked++;
  if (!tierMatch || probDiff > 0.005) mismatches++;

  return {
    ticker: c.ticker,
    drug: c.drug,
    storedProb: c.prob,
    recalcProb: Math.round(recalcProb * 10000) / 10000,
    probDiff: Math.round(probDiff * 10000) / 10000,
    storedTier: c.tier,
    recalcTier,
    tierMatch,
    storedTotalAdj: c.totalAdj,
    recalcTotalAdj: Math.round(recalcTotalAdj * 10000) / 10000,
    adjDiff: Math.round(adjDiff * 10000) / 10000,
    storedLogit: c.logit,
    recalcLogit: Math.round(recalcLogit * 10000) / 10000,
    signalCount: signalKeys.length,
    signals: signals,
    isVerified: VERIFIED_TICKERS[c.ticker] !== undefined,
  };
});

// Show ALL catalysts first — summary
console.log('--- ALL CATALYSTS RESCORE ---');
console.log(`${'Ticker'.padEnd(10)} ${'Drug'.padEnd(30)} ${'Stored'.padEnd(8)} ${'Recalc'.padEnd(8)} ${'Diff'.padEnd(8)} ${'S-Tier'.padEnd(8)} ${'R-Tier'.padEnd(8)} ${'Match'.padEnd(6)} ${'Sigs'.padEnd(5)}`);
console.log('-'.repeat(105));

for (const r of results) {
  const flag = r.isVerified ? ' ⭐' : '';
  console.log(
    `${(r.ticker + flag).padEnd(12)} ${r.drug.substring(0, 28).padEnd(30)} ${(r.storedProb*100).toFixed(1).padStart(6)}% ${(r.recalcProb*100).toFixed(1).padStart(6)}% ${(r.probDiff*100).toFixed(2).padStart(6)}% ${r.storedTier.padEnd(8)} ${r.recalcTier.padEnd(8)} ${r.tierMatch ? '✅' : '❌'}     ${r.signalCount}`
  );
}

// Show verified wins detail
console.log(`\n${'='.repeat(80)}`);
console.log('VERIFIED WINS — DETAILED SIGNAL BREAKDOWN');
console.log(`${'='.repeat(80)}`);

const verifiedResults = results.filter(r => r.isVerified);
for (const r of verifiedResults) {
  const v = VERIFIED_TICKERS[r.ticker];
  console.log(`\n--- ${r.ticker} | ${r.drug} ---`);
  console.log(`  Original prediction (from trades): ${(v.origScore * 100).toFixed(1)}%`);
  console.log(`  Current v10.68 stored prob:        ${(r.storedProb * 100).toFixed(1)}%`);
  console.log(`  Recalculated prob:                 ${(r.recalcProb * 100).toFixed(1)}%`);
  console.log(`  Prob diff (stored vs recalc):      ${(r.probDiff * 100).toFixed(3)}%`);
  console.log(`  Prob diff (original vs current):   ${((r.storedProb - v.origScore) * 100).toFixed(1)}%`);
  console.log(`  Tier: ${r.storedTier} → Recalc: ${r.recalcTier} ${r.tierMatch ? '✅' : '❌ MISMATCH'}`);
  console.log(`  Outcome: ${v.outcome} | Return: ${v.return} | Action: ${v.action}`);
  console.log(`  Signals (${r.signalCount}):`);
  for (const [k, w] of Object.entries(r.signals)) {
    console.log(`    ${w >= 0 ? '+' : ''}${w.toFixed(4).padStart(8)}  ${k}`);
  }
  console.log(`  totalAdj: stored=${r.storedTotalAdj} recalc=${r.recalcTotalAdj} diff=${r.adjDiff}`);
  console.log(`  logit:    stored=${r.storedLogit} recalc=${r.recalcLogit}`);

  // Check directional correctness
  const correctCall = (v.action === 'TRADED' && r.recalcProb >= 0.60) ||
                      (v.action === 'AVOIDED' && r.recalcProb < 0.60);
  console.log(`  Directional call: ${correctCall ? '✅ CORRECT' : '❌ WRONG'} (${v.action === 'TRADED' ? 'needed ≥60%' : 'needed <60%'})`);
}

// Summary stats
console.log(`\n${'='.repeat(80)}`);
console.log('REGRESSION TEST SUMMARY');
console.log(`${'='.repeat(80)}`);
console.log(`Total catalysts checked: ${totalChecked}`);
console.log(`Score mismatches (>0.5% prob diff or tier mismatch): ${mismatches}`);
console.log(`Match rate: ${((totalChecked - mismatches) / totalChecked * 100).toFixed(1)}%`);

const verifiedCorrect = verifiedResults.filter(r => {
  const v = VERIFIED_TICKERS[r.ticker];
  return (v.action === 'TRADED' && r.recalcProb >= 0.60) ||
         (v.action === 'AVOIDED' && r.recalcProb < 0.60);
}).length;

console.log(`\nVerified wins found in current DB: ${verifiedResults.length}`);
console.log(`Directionally correct on verified: ${verifiedCorrect}/${verifiedResults.length}`);
console.log(`Missing from current DB: ${Object.keys(VERIFIED_TICKERS).filter(t => !verifiedResults.find(r => r.ticker === t)).join(', ') || 'None'}`);

// Check for score drift from original predictions
console.log(`\n--- SCORE DRIFT CHECK (original prediction vs current v10.68) ---`);
for (const r of verifiedResults) {
  const v = VERIFIED_TICKERS[r.ticker];
  const drift = (r.storedProb - v.origScore) * 100;
  const driftDir = drift > 0 ? '↑' : drift < 0 ? '↓' : '→';
  console.log(`  ${r.ticker.padEnd(8)} Original: ${(v.origScore*100).toFixed(0).padStart(3)}%  Current: ${(r.storedProb*100).toFixed(1).padStart(5)}%  Drift: ${driftDir} ${Math.abs(drift).toFixed(1)}pp  ${Math.abs(drift) > 10 ? '⚠️ SIGNIFICANT' : '✅ OK'}`);
}
