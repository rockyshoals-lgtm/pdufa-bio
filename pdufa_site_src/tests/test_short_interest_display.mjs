import { formatDaysToCover, renderShortInterest } from '../lib/short_interest.mjs';
let fail = 0;
const check = (cond, msg) => { if (!cond) { console.error(`  FAIL ${msg}`); fail++; } else console.log(`  ok   ${msg}`); };

// 18.3% of the FINRA panel is >100 days. None of it may ever render as a number.
check(formatDaysToCover(4200).show_number === false, 'DTC 4200 does NOT render a number');
check(formatDaysToCover(1000).show_number === false, 'DTC 1000 (sentinel) does NOT render a number');
check(formatDaysToCover(150).text === 'very illiquid',  'DTC 150 renders "very illiquid"');
check(formatDaysToCover(61).show_number === false,      'DTC 61 (just over cap) suppressed');
check(formatDaysToCover(45).show_number === true && formatDaysToCover(45).qualifier !== null,
      'DTC 45 shows a number BUT carries a caution qualifier');
check(formatDaysToCover(3.4).show_number === true && formatDaysToCover(3.4).qualifier === null,
      'DTC 3.4 (the median) renders plainly');
check(formatDaysToCover(null).text === 'not reported',  'null renders "not reported", never 0');

// the settlement date is not optional
let threw = false;
try { renderShortInterest(5, null); } catch { threw = true; }
check(threw, 'rendering WITHOUT a settlement date throws — a snapshot must never look live');
check(renderShortInterest(5, '2026-06-30').line.includes('settlement 2026-06-30'),
      'settlement date is printed on the line');

if (fail) { console.error(`\n${fail} short-interest display failure(s).`); process.exit(1); }
console.log('\nshort-interest display rules hold: absurd ratios never render as numbers.');
