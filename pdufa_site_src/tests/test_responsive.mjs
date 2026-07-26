/**
 * Responsive invariants. Static, no browser needed, runs in CI.
 *
 * WHY THIS EXISTS
 * The homepage — the single most-crawled URL on the site — was never migrated to the shared
 * responsive header. It shipped with 11 flat nav links, no hamburger, and an 81px horizontal
 * overflow at 914px, because its 2-column grid only collapsed under 820px and CSS grid children
 * default to min-width:auto (so the sidebar refused to shrink and punched out of the container).
 * Google indexes mobile-first: that overflow is a "Content wider than screen" failure on the
 * page that passes PageRank to everything else.
 *
 * A page can regress silently. A test cannot.
 */
import { readFileSync, existsSync } from 'node:fs';

const PAGES = [
  ['/',            'index.html'],
  ['/calendar',    'calendar/index.html'],
  ['/decisions',   'decisions/index.html'],
  ['/readouts',    'readouts/index.html'],
  ['/screener',    'screener/index.html'],
  ['/conferences', 'conferences/index.html'],
];

let fail = 0;
const bad = (p, m) => { console.error(`  FAIL ${p}: ${m}`); fail++; };

for (const [route, file] of PAGES) {
  if (!existsSync(file)) { console.log(`  skip ${route} (${file} not present)`); continue; }
  const h = readFileSync(file, 'utf8');

  // 1. the shared responsive header must be present
  if (!h.includes('id="navpolish"')) bad(route, 'missing the shared responsive header (#navpolish)');
  if (!h.includes('pd-burger'))      bad(route, 'no mobile hamburger — nav will not collapse on a phone');

  // 2. any multi-column grid must let its children shrink, or it will overflow
  const hasMultiColGrid = /grid-template-columns:\s*[^;}]*(fr\s+\d|\dfr\s)/.test(h);
  if (hasMultiColGrid && !/min-width:\s*0/.test(h)) {
    bad(route, 'multi-column grid without min-width:0 on children -> horizontal overflow (grid kids default to min-width:auto)');
  }
  if (!fail) console.log(`  ok   ${route}`);
}

if (fail) { console.error(`\n${fail} responsive invariant(s) FAILED — do not deploy.`); process.exit(1); }
console.log('\nresponsive invariants: all pages carry the shared header and cannot overflow.');
