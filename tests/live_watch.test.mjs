// node --test tests/live_watch.test.mjs   (run by tests/test_live_watch.py)
// The every-minute news watch must post only what its primary source says, and say nothing it cannot check.
// Headlines under a "red team" line are ones a red team (2026-11-27) got through an earlier version.
import test from 'node:test';
import assert from 'node:assert/strict';
import { headlineKind, check, bound, reconcile, etWallToMs, etIso, parseFeed, sentence, timeOk, clean, norm,
         exhibitHeadline, exhibitDate, pickRow, readControl, readState, isRetracted, pageDay, corrections, correctionHeadline } from '../pdufa_site_src/api/_live_check.mjs';
import REAL from '../pdufa_site_src/api/_watch_armed.mjs';

const NOW = Date.parse('2026-12-01T21:10:00Z');           // Dec 1, 2026, 4:10 PM ET
const ago = min => NOW - min * 60000;
const TODAY = '2026-12-01';                                // the Eastern day of NOW

// Each test row carries the reviewed indication words of the real armed row for the same drug (_fast_lane.json).
const REVIEWED = ['phrases', 'tok', 'partners', 'forms', 'aliases', 'cls', 'paren'];
const realOf = o => REAL.rows.find(r => r.t === o.t && (r.terms || []).some(x => (o.terms || []).includes(x)));
const row = (o) => {
  const r = realOf(o) || {};
  return { terms: [], need: [], avoid: [], shared: [], ind: [], siblings: [], feeds: [], cik: null, company: '', name: '', url: '/pdufa/X',
           ...Object.fromEntries(REVIEWED.map(k => [k, r[k] || []])), ...o };
};
const ARMED = {
  publish: true, retract: {},
  rows: [
    row({ id: 'pdufa_mlys_2026-12-22', t: 'MLYS', company: 'Mineralys Therapeutics, Inc.', name: 'Lorundrostat', d: '2026-12-22',
          terms: ['lorundrostat'], need: ['hypertension', 'blood pressure'], cik: 1933414, url: '/pdufa/MLYS-lorundrostat',
          feeds: ['https://ir.mineralys.com/rss'] }),
    row({ id: 'pdufa_cort_2026-12-30', t: 'CORT', company: 'Corcept Therapeutics Incorporated', name: 'Relacorilant - (GRACE resubmission)',
          d: '2026-12-30', terms: ['relacorilant'], need: ['Cushing', 'hypercortisolism'], avoid: ['ovarian'], cik: 1088856 }),
    row({ id: 'pdufa_mrk_2027-02-15', t: 'MRK', company: 'Merck & Co., Inc.', name: 'Sacituzumab tirumotecan (sac-TMT) - endometrial cancer',
          d: '2027-02-15', terms: ['sacituzumab tirumotecan', 'sac-TMT', 'MK-2870'], need: ['endometrial'],
          avoid: ['breast', 'lung', 'NSCLC', 'gastric', 'cervical'], cik: 310158 }),
    row({ id: 'pdufa_bbio_2027-01-10', t: 'BBIO', company: 'BridgeBio Pharma, Inc.', name: 'Oral infigratinib - achondroplasia in children',
          d: '2027-01-10', terms: ['infigratinib'], need: ['achondroplasia'], avoid: ['hypochondroplasia', 'cholangiocarcinoma'], cik: 1743881 }),
    row({ id: 'pdufa_bbio_2027-02-01', t: 'BBIO', company: 'BridgeBio Pharma, Inc.', name: 'Encaleret - ADH1',
          d: '2027-02-01', terms: ['encaleret'], need: ['ADH1', 'autosomal dominant hypocalcemia', 'hypocalcemia'], cik: 1743881 }),
    row({ id: 'pdufa_bmy_2027-01-20', t: 'BMY', company: 'Bristol-Myers Squibb Company', name: 'Mezigdomide - myeloma',
          d: '2027-01-20', terms: ['mezigdomide'], need: ['carfilzomib', 'Kyprolis'], avoid: ['bortezomib', 'pomalidomide', 'daratumumab'], cik: 14272 }),
  ],
  status: { 'pdufa_mlys_2026-12-22': { st: 'Upcoming' }, 'pdufa_cort_2026-12-30': { st: 'Upcoming' } },
};
const edgar = (cik, title, o = {}) => check({ channel: 'edgar', cik, title, exDay: TODAY, atMs: ago(3), url: 'https://www.sec.gov/x', ...o }, ARMED, {}, NOW);
const mlys = (title, o = {}) => edgar(1933414, title, o);
// The real armed row for a drug, checked on an SEC filing by its sponsor dated the goal day, 3 minutes old.
const onRow = (t, title, match) => {
  const r = REAL.rows.find(x => x.t === t && (!match || x.terms.some(y => y.toLowerCase() === match.toLowerCase())));
  const now = Date.parse(r.d + 'T21:10:00Z');
  return check({ channel: 'edgar', cik: r.cik, title, exDay: r.d, atMs: now - 3 * 60000, url: 'https://www.sec.gov/rt4' },
               { ...REAL, status: {}, retract: {} }, {}, now);
};

test('approval and letter headlines read as decisions', () => {
  for (const t of [
    'Mineralys Therapeutics Announces FDA Approval of Lorundrostat for Uncontrolled Hypertension',
    'U.S. FDA Approves BioMarin\'s VOXZOGO (vosoritide) for Children with Hypochondroplasia',
    'FDA Approves Genentech\'s Enspryng, a First Treatment for MOGAD',
    'Hibsago (bepirovirsen) approved in the US for the treatment of chronic hepatitis B',
    'Inovio Announces FDA Accelerated Approval of VOCERYQ',
    'U.S. Food and Drug Administration Approves Lorundrostat',
  ]) assert.equal(headlineKind(t).kind, 'approval', t);
  for (const t of [
    'Achieve Life Sciences Receives Complete Response Letter from FDA for Cytisinicline NDA',
    'Unicycive Therapeutics Receives Complete Response Letter',
  ]) assert.equal(headlineKind(t).kind, 'crl', t);
});

test('a real decision on an armed drug posts, in each known shape, on each primary channel', () => {
  for (const t of [
    'Mineralys Therapeutics Announces FDA Approval of Lorundrostat for Uncontrolled Hypertension',
    'FDA Approves Mineralys\' Lorundrostat for Adults With Uncontrolled Hypertension',
    'U.S. Food and Drug Administration Approves Mineralys Therapeutics\' Lorundrostat for Hypertension',
    'Lorundrostat Receives U.S. FDA Approval for Hypertension',
    'Lorundrostat Approved by the FDA for High Blood Pressure',
    'Mineralys Announces the U.S. Food and Drug Administration Has Approved Lorundrostat for Hypertension',
    'FDA Approves Lorundrostat, First Aldosterone Synthase Inhibitor, for Uncontrolled Hypertension',
    'FDA Approves Lorundrostat for Hypertension in Adults Aged 18 Years and Older',
    'FDA Approves Lorundrostat, the First Aldosterone Synthase Inhibitor, for Uncontrolled Hypertension',
    'Mineralys Therapeutics Receives U.S. FDA Approval of LORVENZA (lorundrostat) Tablets for the Treatment of Hypertension',
    'FDA Grants Accelerated Approval to LORVENZA (lorundrostat) for Hypertension',
    'Mineralys announces FDA approval of lorundrostat for hypertension',
    'Mineralys Announces FDA Approval of Lorundrostat for the Treatment of Hypertension',
    'Mineralys Announce FDA Approval of Lorundrostat for Hypertension',
    'FDA Grants Full Approval to Lorundrostat for Hypertension',
    'Mineralys Receives Complete Response Letter from the FDA for Lorundrostat in Hypertension',
    'Mineralys Announces Receipt of Complete Response Letter for Lorundrostat for Hypertension',
    'FDA Issues Complete Response Letter for Lorundrostat in Hypertension',
    'Lorundrostat Receives Complete Response Letter in Hypertension',
    'FDA Approves Lorundrostat&#160;for&#160;Hypertension',
  ]) {
    const c = mlys(t);
    assert.equal(c.ok, true, `${t}: ${c.why}`);
  }
  assert.equal(check({ channel: 'rss', feed: 'https://ir.mineralys.com/rss', title: 'FDA Approves Lorundrostat for Hypertension', atMs: ago(2), url: 'https://ir.mineralys.com/a', fresh: true, exDay: TODAY }, ARMED, {}, NOW).ok, true);
  assert.equal(edgar(1088856, 'Corcept Announces FDA Approval of Relacorilant for Hypercortisolism (Cushing\'s Syndrome)').ok, true);
  assert.equal(edgar(14272, 'U.S. FDA Approves Mezigdomide in Combination With Carfilzomib and Dexamethasone for Relapsed Multiple Myeloma').ok, true);
  assert.equal(edgar(1743881, 'BridgeBio Receives FDA Approval of Encaleret for Autosomal Dominant Hypocalcemia Type 1 (ADH1)').ok, true);
  assert.equal(edgar(14272, 'U.S. FDA Approves Bristol Myers Squibb\'s Mezigdomide in Combination With Carfilzomib for Myeloma').ok, true);
  assert.equal(edgar(14272, 'FDA Approves Mezigdomide Plus Carfilzomib and Dexamethasone for Relapsed or Refractory Multiple Myeloma').ok, true);
});

// Real-looking headlines, one or more for every armed row, in the ways sponsors word a decision: they post.
test('recall: each armed row posts its own decision in the usual wordings', () => {
  for (const [t, h, m] of [
 ['VRTX','Vertex Pharmaceuticals Announces FDA Approval of Povetacicept for IgA Nephropathy'],
 ['GILD','Kite and Arcellx Announce U.S. FDA Approval of Anitocabtagene Autoleucel for Relapsed or Refractory Multiple Myeloma'],
 ["GILD","U.S. FDA Approves Kite's Anito-cel for Relapsed or Refractory Multiple Myeloma"],
 ['MLYS','FDA Approves Lorundrostat, First Aldosterone Synthase Inhibitor, for Uncontrolled Hypertension'],
 ['MLYS','FDA Approves LORVENZA (lorundrostat), First-in-Class Treatment for Uncontrolled Hypertension'],
 ['MLYS','U.S. FDA Approves LORVENZA (lorundrostat) to Lower Blood Pressure in Adults With Hypertension'],
 ['MLYS','Mineralys Announces the U.S. Food and Drug Administration Has Approved Lorundrostat for Hypertension'],
 ["EXEL","U.S. FDA Approves Exelixis' Zanzalintinib Plus Atezolizumab for Metastatic Colorectal Cancer"],
 ['NTLA','Intellia Therapeutics Announces FDA Approval of Lonvoguran Ziclumeran (lonvo-z), a One-Time Treatment for Hereditary Angioedema'],
 ['APMD','FDA Approves Apnimed\'s AD109 for Obstructive Sleep Apnea (OSA)'],
 ['ZBIO','Zenas BioPharma Announces FDA Approval of Obexelimab for IgG4-Related Disease'],
 ['QURE',"uniQure Announces FDA Accelerated Approval of AMT-130 for Huntington's Disease"],
 ['UNCY','Unicycive Announces FDA Approval of Oxylanthanum Carbonate for Hyperphosphatemia in Patients With Chronic Kidney Disease on Dialysis'],
 ['SVRA','Savara Announces FDA Approval of MOLBREEVI for Autoimmune Pulmonary Alveolar Proteinosis (aPAP)'],
 ['CGEM','FDA Approves Zipalertinib for Locally Advanced or Metastatic NSCLC With EGFR Exon 20 Insertion Mutations'],
 ['PRAX','Praxis Precision Medicines Announces FDA Approval of Relutrigine for Developmental and Epileptic Encephalopathies','relutrigine'],
 ['AXSM','Axsome Therapeutics Announces FDA Approval of AXS-12 for Cataplexy in Narcolepsy'],
 ['BLTE','Belite Bio Announces FDA Approval of Tinlarebant for Stargardt Disease'],
 ['IMNM','Immunome Announces FDA Approval of Varegacestat for Desmoid Tumors'],
 ['INBX','FDA Approves Ozekibart for Conventional Chondrosarcoma'],
 ['VNDA','Vanda Pharmaceuticals Announces FDA Approval of Imsidolimab for Generalized Pustular Psoriasis'],
 ['PVLA','Palvella Therapeutics Announces FDA Approval of QTORIN Rapamycin for Microcystic Lymphatic Malformations'],
 ['AQST','Aquestive Therapeutics Announces FDA Approval of Anaphylm for Severe Allergic Reactions Including Anaphylaxis'],
 ['PHVS','Pharvaris Announces FDA Approval of Deucrictibant for Acute Attacks of Hereditary Angioedema'],
 ['MRK',"FDA Approves Merck's Sacituzumab Tirumotecan for Previously Treated Endometrial Cancer"],
 ['CORT','Corcept Receives Complete Response Letter for Relacorilant in Hypercortisolism'],
 ['PRAX','Praxis Announces FDA Approval of Ulixacaltamide for Essential Tremor','ulixacaltamide'],
 ['BBIO','BridgeBio Announces FDA Approval of Encaleret for Autosomal Dominant Hypocalcemia Type 1','encaleret'],
  ]) { const c = onRow(t, h, m); assert.equal(c.ok, true, `${h}: ${c.why}`); }
});

test('everything that is not a new U.S. decision on that drug is held', () => {
  for (const t of [
    'Unicycive Therapeutics Announces FDA Acceptance of Oxylanthanum Carbonate New Drug Application Resubmission and PDUFA Date of March 25, 2027',
    'Mineralys Announces FDA Acceptance of Lorundrostat NDA for Hypertension',
    'Vertex Announces Extension of PDUFA Target Action Date by up to Three Months',
    'Lilly\'s Jaypirca recommended by CHMP for approval in the European Union',
    'MYQORZO Approved by the European Commission for Adults with Obstructive HCM',
    'Company Presents New Data on FDA-Approved Drug at ASH',
    'FDA Grants Priority Review to Lorundrostat NDA for Hypertension',
    'Mineralys Expects FDA Decision on Lorundrostat by December 22',
    'Capricor Provides Regulatory Update on Deramiocel BLA',
    'FDA Advisory Committee Votes in Favor of Lorundrostat for Hypertension',
    'Lorundrostat Now Available in the U.S. Following FDA Approval for Hypertension',
    'Company Withdraws NDA for Lorundrostat',
    'FDA Approves Lorundrostat and Issues Complete Response Letter for Second Indication',
    // ---- red team 1 ----
    'Mineralys Says FDA Has Not Approved Lorundrostat for Hypertension',
    'Mineralys Denies Reports That FDA Approved Lorundrostat for Hypertension',
    'FDA Rescinds Approval of Lorundrostat for Hypertension',
    'FDA Revokes Lorundrostat Approval in Hypertension',
    'FDA Approves New Manufacturing Site for Lorundrostat',
    'FDA Approves Lorundrostat Pivotal Protocol Amendment in Hypertension',
    'FDA Approval of Lorundrostat for Hypertension Triggers $50 Million Milestone',
    'Shareholder Alert: Investigation After FDA Approval of Lorundrostat',
    'Mineralys shares rise after FDA approval of Lorundrostat rival',
    'Mineralys Statement on FDA Approval of Competing Drug; Lorundrostat',
    'FDA Approves Rival Baxdrostat; Mineralys Comments on Lorundrostat',
    'Partner Received FDA Complete Response Letter; Lorundrostat Unaffected',
    'Mineralys Resolves Complete Response Letter for Lorundrostat',
    'Mineralys Responds to FDA Complete Response Letter for Lorundrostat',
    'Mineralys Announces Taiwan FDA Approval of Lorundrostat for Hypertension',
    'Mineralys Announces Saudi FDA Approval of Lorundrostat for Hypertension',
    'Mineralys Announces Jordan FDA Approval of Lorundrostat for Hypertension',
    'Mineralys Announces JFDA Approval of Lorundrostat for Hypertension',
    'Approval of Lorundrostat by Israel Ministry of Health Following FDA Approval',
    'Mineralys Announces Canadian Approval of Lorundrostat, Following FDA approval',
    'Lorundrostat Receives Approval in Hong Kong Following FDA Approval',
    'FDA Approves Lorundrostat; Com­pany Ex­pects Launch in Q1',
    'FDA Approves Generic Version of Lorundrostat',
    'FDA Approves Label Update for Lorundrostat',
    // ---- red team 2: a timetable or a status, the drug only near the verb, the indication elsewhere ----
    'FDA Decision on Lorundrostat for Hypertension Remains on Track',
    'Lorundrostat Advances Toward FDA Approval in Hypertension',
    'FDA Approval of Lorundrostat for Hypertension Set for December',
    'Mineralys Reiterates Guidance: FDA Approval of Lorundrostat for Hypertension Due in Q4',
    'Mineralys Awaits FDA Approval of Lorundrostat for Hypertension',
    'FDA Approval of Lorundrostat in Hypertension Is Next Milestone',
    'FDA Approves Baxdrostat for Hypertension, Also Reviewing Lorundrostat',
    'FDA Approves AstraZeneca\'s Baxdrostat With Lorundrostat Data Pending; Hypertension',
    'FDA Approves Lorundrostat in Chronic Kidney Disease; Hypertension Study Continues',
    'FDA Approves Lorundrostat in CKD, Hypertension Filing Planned',
    'FDA Approves Lorundrostat Higher Dose for Hypertension',
    'FDA Approves First Drug for Hypertension Since Lorundrostat',
    'FDA Approves Drug Similar to Lorundrostat for Hypertension',
    'Alternative to Lorundrostat Receives FDA Approval for Hypertension',
    'Mineralys Receives Complete Response Letter for Lorundrostat Partner Program in Hypertension',
    'FDA Approves Mineralys\' Lorundrostat',                                      // no indication: held
    'FDA Approves Lorundrostat — the first in Hypertension',                 // the indication in another clause
    'FDA Approves Lorundrostat for Hypertension &#8211; Mineralys',                // a second clause after a dash
    'FDA Approves Lorundrostat for CKD - Hypertension Approval Open',
    // ---- red team 3: a denial, approval of something else, an access programme, a quoted or hypothetical clause ----
    "Lorundrostat Hasn't Received a Complete Response Letter in Hypertension, Mineralys Says",
    "Mineralys: Lorundrostat Hasn't Received Complete Response Letter in Hypertension",
    "Lorundrostat Hasn't Been Approved by the FDA for Hypertension",
    "Lorundrostat Isn't Approved by FDA for Hypertension Yet",
    "Lorundrostat Won't Be Approved by the FDA for Hypertension This Year",
    'Lorundrostat Cannot Be Approved by FDA for Hypertension Before 2027',
    'Lorundrostat (MLS-101) Unlikely Approved by FDA for Hypertension',
    'Lorundrostat Receives FDA Approval to Begin Pivotal Trial in Hypertension',
    'Lorundrostat Receives FDA Approval for Phase 3 Trial in Hypertension',
    'FDA Approves Phase 3 Lorundrostat Trial in Hypertension',
    'Mineralys Receives FDA Approval of Pivotal Lorundrostat Trial in Hypertension',
    'FDA Grants Approval to Lorundrostat Trial Design in Hypertension',
    'FDA Approves Lorundrostat Pediatric Waiver Request in Hypertension',
    'FDA Approves Lorundrostat REMS Modification for Hypertension',
    'Lorundrostat Receives FDA Approval Pathway Clarity in Hypertension',
    'Mineralys Announces FDA Approval of Lorundrostat Proprietary Name for Hypertension',
    'Lorundrostat Approved by FDA for Compassionate Use in Hypertension',
    'FDA Approves Lorundrostat for Early Access in Resistant Hypertension',
    'Mineralys Warns of Fake Release Claiming the FDA Approves Lorundrostat for Hypertension',
    'Mineralys Retracts Erroneous Release Stating That the FDA Approves Lorundrostat for Hypertension',
    'Mineralys Will Hire 200 Reps Once the FDA Approves Lorundrostat for Hypertension',
    'Mineralys Hopes the FDA Approves Lorundrostat for Hypertension by Year End',
    'Correction: Lorundrostat Receives FDA Approval for Hypertension Headline Was Issued in Error',
    'Erroneous Headline Lorundrostat Receives FDA Approval for Hypertension Retracted by Mineralys',
    'Lorundrostat Receives FDA Approval for Hypertension, Mineralys Mistakenly Said; Correction Issued',
    'FDA Approves Baxdrostat Beating Lorundrostat in Hypertension',
    'Lorundrostat Challenger Baxdrostat Receives FDA Approval for Hypertension',
    'Lorundrostat Receives FDA Approval in Ghana for Hypertension',
    'Ghana-FDA Approves Lorundrostat for Hypertension',
    'Lorundrostat Receives Complete Response Letter Rescission in Hypertension',
    'FDA Approves Lorundrostat for Hypertension?',
    'Acme Announces FDA Approval of Lorundrostat for Hypertension',               // not the sponsor's own name
    'FDA Approves Once-Daily Lorundrostat for Hypertension',
  ]) {
    const c = mlys(t);
    assert.equal(c.ok, false, `should hold: ${t}`);
  }
});

test('the decision must be tied to the drug and its indication in a known shape', () => {
  const M = ARMED.rows[0];
  assert.equal(bound('FDA Approves Mineralys\' Lorundrostat for Hypertension', 'approval', M), true);
  assert.equal(bound('FDA Approves Mineralys\' Lorundrostat', 'approval', M), false, 'no indication');
  assert.equal(bound('FDA Approves Acme\'s Lorundrostat for Hypertension', 'approval', M), false);
  assert.equal(bound('FDA Approves Baxdrostat; Lorundrostat Review Continues', 'approval', M), false);
  assert.equal(bound('FDA Approves a Treatment for Hypertension From a Company Whose Pipeline Includes the Investigational Lorundrostat', 'approval', M), false);
  assert.equal(bound('FDA Approves Keytruda Plus Lorundrostat for Hypertension', 'approval', M), false);
  assert.equal(bound('FDA Approves Keytruda, Lorundrostat for Hypertension', 'approval', M), false);
  assert.equal(bound('FDA approves higher-dose lorundrostat for hypertension', 'approval', M), false);
  assert.equal(bound('Mineralys Receives Complete Response Letter for Lorundrostat in Hypertension', 'crl', M), true);
  assert.equal(bound('Mineralys Receives Complete Response Letter for Lorundrostat NDA for Hypertension', 'crl', M), true);
  assert.equal(bound('Mineralys Receives Complete Response Letter for Lorundrostat', 'crl', M), false, 'a letter that names no indication is held');
  assert.equal(bound('Receives Complete Response Letter for Lorundrostat in Hypertension', 'crl', M), false);
  assert.equal(norm('U.S. Food and Drug Administration (FDA) Approves X'), 'U.S. FDA Approves X');
});

test('one application: its indication, none of its avoid words, no other armed drug', () => {
  const c = t => edgar(1088856, t);
  assert.equal(c('Corcept Announces FDA Approval of Relacorilant').ok, false);
  assert.equal(c('FDA Approves Corcept\'s Relacorilant for Platinum-Resistant Ovarian Cancer').ok, false);
  assert.equal(c('FDA Approves Relacorilant for Hypercortisolism; Ovarian Cancer Review Continues').ok, false);
  const b = t => edgar(1743881, t);
  assert.equal(b('FDA Approves BridgeBio\'s Infigratinib for Children With Achondroplasia').ok, true, b('FDA Approves BridgeBio\'s Infigratinib for Children With Achondroplasia').why);
  assert.equal(b('FDA Approves Infigratinib for Cholangiocarcinoma').ok, false);
  assert.equal(b('FDA Approves Infigratinib for Achondroplasia and Hypochondroplasia').ok, false);
  assert.equal(b('FDA Approves Infigratinib for Achondroplasia; Encaleret Review Continues').ok, false, 'names another armed drug');
  const bm = t => edgar(14272, t);
  assert.equal(bm('FDA Approves Mezigdomide With Bortezomib and Dexamethasone, After Carfilzomib').ok, false);
  const p = pickRow('FDA Approves Lorundrostat for Hypertension', 'approval', [ARMED.rows[0]], ARMED.rows);
  assert.equal(p.row.id, 'pdufa_mlys_2026-12-22');
});

test('a word cut from another drug\'s name never matches (sacituzumab govitecan vs sac-TMT)', () => {
  const m = t => edgar(310158, t);
  assert.equal(m('FDA Approves Merck\'s KEYTRUDA Plus Gilead\'s Sacituzumab Govitecan for Breast Cancer').ok, false);
  assert.equal(m('FDA Approves Merck\'s Sacituzumab Tirumotecan (sac-TMT) for Endometrial Cancer').ok, true);
  assert.equal(m('FDA Approves Merck\'s Sacituzumab Tirumotecan for Endometrial Cancer and Breast Cancer').ok, false);
});

test('an SEC filing is judged on its exhibit\'s own headline and its dateline day', () => {
  const ex = '<html><body><p>Exhibit 99.1</p><p><b>Mineralys Therapeutics Announces FDA Approval of Lorundrostat for Hypertension</b></p>'
    + '<p>RADNOR, Pa., Dec. 1, 2026 (GLOBE NEWSWIRE) -- Mineralys today announced</p></body></html>';
  assert.equal(exhibitHeadline(ex), 'Mineralys Therapeutics Announces FDA Approval of Lorundrostat for Hypertension');
  assert.equal(exhibitDate(ex), '2026-12-01');
  assert.equal(exhibitDate('<p>Headline of the release goes here</p><p>SAN DIEGO--(BUSINESS WIRE)--Dec. 1, 2026--Text</p>'), '2026-12-01');
  assert.equal(exhibitDate('<p>Headline of the release goes here</p><p>LEIDEN, the Netherlands, Dec. 1, 2026 (GLOBE NEWSWIRE) -- Text</p>'), '2026-12-01');
  assert.equal(exhibitHeadline('<p>Mineralys Receives Complete Response Letter for Lorundrostat in Hypertension</p><p>Reissued December 1, 2026</p><p>RADNOR, Pa., June 2, 2026 -- x</p>'), '', 'a date before the dateline');
  assert.equal(exhibitHeadline('<p><b>FDA Approves Lorundrostat<br>for Hypertension in Adults</b></p><p>RADNOR, Pa., Dec. 1, 2026 -- x</p>'), 'FDA Approves Lorundrostat for Hypertension in Adults');
  const noDate = '<p>Mineralys Therapeutics Announces FDA Approval of Lorundrostat for Hypertension</p><p>Mineralys today announced</p>';
  assert.equal(exhibitHeadline(noDate), '');
  const inducement = '<p>Mineralys Therapeutics Announces Inducement Grants</p><p>RADNOR, Pa., Dec. 1, 2026 -- focused on lorundrostat, after the FDA approved its site</p>';
  assert.equal(mlys(exhibitHeadline(inducement)).ok, false);
  const t = 'Mineralys Therapeutics Announces FDA Approval of Lorundrostat for Hypertension';
  assert.equal(mlys(t, { exDay: '' }).ok, false, 'no dateline');
  assert.equal(mlys(t, { exDay: '2026-06-02' }).ok, false, 'an old release re-filed');
  assert.equal(mlys(t, { exDay: '2026-11-30' }).ok, true, 'a day apart is the same news');
});

test('the source must be the sponsor\'s own', () => {
  const t = 'Mineralys Therapeutics Announces FDA Approval of Lorundrostat for Hypertension';
  assert.equal(edgar(999, t).ok, false);
  assert.equal(check({ channel: 'rss', feed: 'https://evil.example/rss', title: t, atMs: ago(2), url: 'https://evil.example/a' }, ARMED, {}, NOW).ok, false);
  assert.equal(check({ channel: 'fda', title: t, atMs: ago(2), url: 'https://www.fda.gov/x' }, ARMED, {}, NOW).ok, false);
  // a newswire release alone never posts: a forger writes its headline, ticker and dateline
  const w = { channel: 'wire', ticker: 'MLYS', title: t, atMs: ago(2), url: 'https://www.globenewswire.com/news-release/x', wirePageTitle: t,
              wireLead: '(GLOBE NEWSWIRE) -- Mineralys Therapeutics, Inc. (Nasdaq: MLYS)' };
  assert.equal(check(w, ARMED, {}, NOW).ok, false);
  // a feed item must link to the sponsor's own site
  const f = { channel: 'rss', feed: 'https://ir.mineralys.com/rss', title: t, atMs: ago(2), fresh: true, exDay: TODAY };
  assert.equal(check({ ...f, url: 'https://ir.mineralys.com/news/1' }, ARMED, {}, NOW).ok, true);
  assert.equal(check({ ...f, url: 'https://www.mineralys.com/news/1' }, ARMED, {}, NOW).ok, true);
  assert.equal(check({ ...f, url: 'https://evil.example/news/1' }, ARMED, {}, NOW).ok, false);
  assert.equal(check({ ...f, url: 'http://ir.mineralys.com/news/1' }, ARMED, {}, NOW).ok, false);
  assert.equal(check({ ...f, url: 'https://careers.mineralys.com/news/1' }, ARMED, {}, NOW).ok, false, 'another subdomain');
  // a feed item must be new since the watch first read the feed, and its page must carry the same day's dateline
  assert.equal(check({ ...f, url: 'https://ir.mineralys.com/news/1', fresh: false }, ARMED, {}, NOW).ok, false);
  assert.equal(check({ ...f, url: 'https://ir.mineralys.com/news/1', exDay: '' }, ARMED, {}, NOW).ok, false);
  assert.equal(check({ ...f, url: 'https://ir.mineralys.com/news/1', exDay: '2025-02-04' }, ARMED, {}, NOW).ok, false);
  // the same source is never posted twice, even under another row id
  assert.equal(check({ ...f, url: 'https://ir.mineralys.com/news/1' }, ARMED, { old_id: { source: { url: 'https://ir.mineralys.com/news/1' } } }, NOW).ok, false);
});

test('stale, out-of-window, already posted, withdrawn by hand or already decided: no post', () => {
  const t = 'Mineralys Announces FDA Approval of Lorundrostat for Hypertension';
  assert.equal(mlys(t, { atMs: ago(13 * 60) }).ok, false);
  assert.equal(mlys(t, { atMs: NaN }).ok, false);
  assert.equal(mlys(t, { atMs: NOW + 30 * 60000 }).ok, false);
  const it = { channel: 'edgar', cik: 1933414, title: t, exDay: TODAY, url: 'https://www.sec.gov/x', atMs: ago(2) };
  assert.equal(check(it, ARMED, { 'pdufa_mlys_2026-12-22': {} }, NOW).ok, false);
  assert.equal(check(it, { ...ARMED, status: { 'pdufa_mlys_2026-12-22': { st: 'Decided', oc: 'Approved' } } }, {}, NOW).ok, false);
  assert.equal(check(it, { ...ARMED, retract: { 'pdufa_mlys_2026-12-22': 'Posted in error.' } }, {}, NOW).ok, false);
  for (const v of ['', false, 0, null]) assert.equal(check(it, { ...ARMED, retract: { 'pdufa_mlys_2026-12-22': v } }, {}, NOW).ok, false, `retract reason ${JSON.stringify(v)}`);
  assert.equal(check(it, { ...ARMED, stopped: { 'https://www.sec.gov/x': ago(30) } }, {}, NOW).ok, false, 'first seen while stopped');
  assert.equal(check(it, { ...ARMED, stopAt: ago(1) }, {}, NOW).ok, false, 'published before the last stopped minute');
  assert.equal(check({ ...it, atMs: NaN }, { ...ARMED, stopAt: ago(60) }, {}, NOW).ok, false, 'no source time after a stop');
  assert.equal(check(it, { ...ARMED, stopAt: ago(3) }, {}, NOW).ok, true, 'published after posting resumed');
  assert.equal(isRetracted(['pdufa_mlys_2026-12-22'], 'pdufa_mlys_2026-12-22'), false, 'only a plain object is a retract list (readControl stops on any other)');
  assert.notEqual(timeOk(NOW, NOW, '2027-09-01'), '');            // more than 120 days before the goal
  assert.equal(timeOk(NOW, NOW, '2026-12-22'), '');
});

test('self-heal: confirm the same outcome on the same day; retract another outcome or by hand', () => {
  const src = { published_at: '2026-12-01T16:05:00-05:00' };
  const pub = { a: { id: 'a', kind: 'approval', status: 'posted', source: src }, b: { id: 'b', kind: 'approval', status: 'posted', source: src },
                c: { id: 'c', kind: 'crl', status: 'posted', source: src }, d: { id: 'd', kind: 'approval', status: 'posted', source: src },
                e: { id: 'e', kind: 'approval', status: 'posted', source: src, page: '/pdufa/E' },
                f: { id: 'f', kind: 'approval', status: 'posted', source: src, page: '/pdufa/F' } };
  const out = reconcile(pub, { retract: { d: 'Posted on the wrong application.' },
    status: { a: { st: 'Decided', oc: 'Approved', dcd: '2026-12-01', url: '/fda-decision/A' }, b: { st: 'Decided', oc: 'CRL', dcd: '2026-12-01' },
              c: { st: 'Upcoming' }, e: { st: 'Decided', oc: 'Approved', dcd: '2027-02-10', url: '/fda-decision/E' },
              f: { st: 'Decided', oc: 'Approved', dcd: '2026-11-30', url: '//evil.example/x' } } }, NOW);
  // not confirmed three days after the source (by the clock): withdrawn, a blank outcome too; a bare true gets a reason
  const late = reconcile({ g: { id: 'g', kind: 'approval', status: 'posted', source: src }, h: { id: 'h', kind: 'approval', status: 'posted', source: src },
                           i: { id: 'i', kind: 'approval', status: 'posted', source: src }, j: { id: 'j', kind: 'approval', status: 'posted', source: src } },
    { as_of: '2026-12-04', retract: { j: true }, status: { g: { st: 'Upcoming' }, h: { st: 'Decided', oc: '', dcd: '2026-12-01' } } }, NOW + 3 * 86400000);
  assert.equal(late.g.status, 'retracted');
  assert.equal(late.h.status, 'retracted', 'decided with no outcome three days on');
  assert.equal(late.i.status, 'retracted', 'no reviewed record at all');
  assert.equal(late.j.retract_reason, 'Withdrawn by pdufa.bio.');
  assert.equal(reconcile({ g: { id: 'g', kind: 'approval', status: 'posted', source: src } }, { as_of: '2026-12-02', status: { g: { st: 'Upcoming' } } }, NOW + 86400000).g.status, 'posted');
  assert.equal(out.a.status, 'confirmed'); assert.equal(out.a.page, '/fda-decision/A');
  assert.equal(out.b.status, 'retracted'); assert.match(out.b.retract_reason, /CRL/);
  assert.equal(out.c.status, 'posted');
  assert.equal(out.d.status, 'retracted'); assert.equal(out.d.retract_reason, 'Posted on the wrong application.');
  assert.equal(out.e.status, 'posted', 'approved, but on another day: left posted for now');
  assert.equal(reconcile({ e: pub.e }, { status: { e: { st: 'Decided', oc: 'Approved', dcd: '2027-02-10' } } }, NOW + 3 * 86400000).e.status, 'retracted', '... and withdrawn three days on');
  // a confirmed post is withdrawn when the record later says otherwise; "Complete Response Letter" is a letter
  const conf = { id: 'k', kind: 'approval', status: 'confirmed', source: src };
  assert.equal(reconcile({ k: conf }, { status: { k: { st: 'Decided', oc: 'CRL', dcd: '2026-12-01' } } }, NOW).k.status, 'retracted');
  const crl = { id: 'l', kind: 'crl', status: 'posted', source: src };
  assert.equal(reconcile({ l: crl }, { status: { l: { st: 'Decided', oc: 'Complete Response Letter', dcd: '2026-12-01' } } }, NOW).l.status, 'confirmed');
  // a stalled build cannot keep a post up: the three days run on the clock
  assert.equal(reconcile({ g: { id: 'g', kind: 'approval', status: 'posted', source: src } }, { as_of: '2026-11-20', status: { g: { st: 'Upcoming' } } }, NOW + 3 * 86400000).g.status, 'retracted');
  assert.deepEqual(Object.keys(reconcile({ x: null, y: pub.a }, { status: {} }, NOW)), ['y'], 'a null post is dropped');
  assert.equal(out.f.status, 'confirmed'); assert.equal(out.f.page, '/pdufa/F', 'a page link stays on pdufa.bio');
});

test('text is cleaned before it is read', () => {
  assert.equal(clean('OXNIMBI™ approved'), 'OXNIMBI approved');
  assert.equal(clean('OXNIMBI&#8482; approved'), 'OXNIMBI approved');
  assert.equal(clean('Com­pany ex​pects'), 'Company expects');
  assert.equal(clean('Merck&#x2019;s'), "Merck's");
  assert.equal(clean('Merck&#8217;s &ndash; A&amp;B'), "Merck's - A&B");
  assert.equal(clean('a &#60;img onerror=x&#62; b'), 'a img onerror=x b');
});

test('times: Eastern with the zone, never guessed', () => {
  assert.equal(new Date(etWallToMs('2026-11-20 19:55:00')).toISOString(), '2026-11-21T00:55:00.000Z');   // EST
  assert.equal(new Date(etWallToMs('2026-07-01 09:30:00')).toISOString(), '2026-07-01T13:30:00.000Z');   // EDT
  assert.ok(Number.isNaN(etWallToMs('2026-11-01 01:30:00')), 'the fall-back hour happens twice: unknown');
  assert.ok(Number.isNaN(etWallToMs('2026-03-08 02:30:00')), 'the spring-forward hour never happens');
  assert.equal(etIso(Date.parse('2026-11-21T00:55:00Z')), '2026-11-20T19:55:00-05:00');
  const feed = d => parseFeed(`<rss><item><title>A</title><link>https://x/a</link><pubDate>${d}</pubDate></item></rss>`)[0].atMs;
  assert.equal(new Date(feed('Mon, 30 Nov 2026 16:05:00 -0500')).toISOString(), '2026-11-30T21:05:00.000Z');
  for (const d of ['Mon, 30 Nov 2026 16:05:00', 'Thu, 27 Nov 2026 GMT', 'Nov 27, 2026 EST', '2026-11-27Z',
                   'Thu, 27 Nov 2026 00:00:00 GMT', '2026-11-27T00:00:00-05:00', 'Nov 27, 2026 12:00 AM EST'])
    assert.ok(Number.isNaN(feed(d)), `not a time: ${d}`);
  // the first publication time, not a later edit
  const atom = parseFeed('<feed><entry><title>A</title><link href="https://x/a"/><published>2026-11-30T16:05:00-05:00</published><updated>2026-12-01T09:00:00-05:00</updated></entry></feed>')[0];
  assert.equal(new Date(atom.atMs).toISOString(), '2026-11-30T21:05:00.000Z');
});

test('the posted sentence quotes the source headline and attributes it', () => {
  const r = ARMED.rows[0];
  const h = 'Mineralys Therapeutics Announces FDA Approval of Lorundrostat for Hypertension';
  assert.equal(sentence({ channel: 'edgar', form: '8-K', title: h }, r), `Mineralys Therapeutics' SEC filing (8-K) says: "${h}"`);
  assert.equal(sentence({ channel: 'edgar', form: '8-K', title: h }, { ...r, company: 'Merck & Co., Inc.' }).startsWith("Merck's SEC filing"), true);
  assert.match(sentence({ channel: 'wire', url: 'https://www.businesswire.com/x', title: h }, r), /release on Business Wire says: "/);
  assert.equal(sentence({ channel: 'rss', title: h }, { ...r, company: 'Harmony Biosciences Holdings, Inc.' }).startsWith("Harmony Biosciences' news release says"), true);
});

// ---- red team 4: every input below posted on an earlier version. Each is checked on the real armed row, with an
// SEC filing by the sponsor dated the goal day, 3 minutes old. ----
test('red team 4: another disease, line, regimen or population is held', () => {
  for (const [t, title, m] of [
    ['MLYS', 'FDA Approves Lorundrostat for Pulmonary Arterial Hypertension'],
    ['APMD', 'FDA Approves AD109 for Central Sleep Apnea'],
    ['BMY', 'U.S. FDA Approves Mezigdomide for Patients With Carfilzomib-Refractory Multiple Myeloma'],
    ['BMY', 'FDA Approves Mezigdomide for Relapsed Multiple Myeloma Previously Treated With Carfilzomib'],
    ['CGEM', 'FDA Approves Zipalertinib for NSCLC With EGFR PACC Mutations'],
    ['CGEM', 'Cullinan Therapeutics Announces FDA Approval of Zipalertinib for EGFR-Mutant NSCLC in Combination With Amivantamab'],
    ['BBIO', 'BridgeBio Announces FDA Approval of Encaleret for Chronic Hypoparathyroidism', 'encaleret'],
    ['PRAX', 'FDA Approves Relutrigine for Seizures in Dravet Syndrome', 'relutrigine'],
    ['PRAX', 'FDA Approves Relutrigine for Focal Onset Seizures in Adults', 'relutrigine'],
    ['PHVS', 'FDA Approves Deucrictibant for Acquired Angioedema Attacks'],
    ['PHVS', 'FDA Approves Deucrictibant Oral Solution for HAE Attacks in Children'],
    ['PHVS', 'FDA Approves Deucrictibant for HAE Attacks in Children'],
    ['CORT', 'FDA Approves Relacorilant for Pancreatic Cancer Patients With Cushing Features'],
    ['MRK', 'FDA Approves Sac-TMT for Endometrial Cancer in Combination With Lenvatinib'],
    ['EXEL', 'FDA Approves Zanzalintinib for Colorectal Cancer in Combination With Bevacizumab'],
    ['MLYS', 'FDA Approves Lorundrostat for CKD Patients Without Hypertension'],
    ['MLYS', 'FDA Approves Lorundrostat for Primary Aldosteronism Instead of Hypertension'],
    ['MLYS', 'FDA Approves Lorundrostat for Kidney Disease Other Than Hypertension'],
    ['MLYS', 'FDA Approves Lorundrostat, the First Drug Studied Beyond Hypertension, for Primary Aldosteronism'],
    ['MLYS', 'FDA Approves Lorundrostat, the First Treatment for Hypertension, for Primary Aldosteronism'],
    // a combination, a competitor, a supplement or another form in the drug's place
    ['MLYS', 'FDA Approves Lorundrostat (With Amlodipine) for Hypertension'],
    ['MLYS', 'FDA Approves Lorvenza Duo (lorundrostat and amlodipine) for Hypertension'],
    ['MLYS', 'FDA Approves Baxdrostat (Unlike Lorundrostat) for Hypertension'],
    ['MLYS', 'FDA Approves Baxdrostat (Lorundrostat Comparator) for Hypertension'],
    ['MLYS', 'FDA Approves Teva ANDA (Lorundrostat) for Hypertension'],
    ['MLYS', 'FDA Approves ANDA (Lorundrostat) for Hypertension'],
    ['MLYS', 'FDA Approves Lorundrostat (sNDA) for Hypertension'],
    ['MLYS', 'FDA Approves Lorundrostat Injection for Hypertension'],
    ['BMY', 'FDA Approves Mezigdomide (With Elotuzumab) for Kyprolis-Refractory Myeloma'],
    // a second meaning after the indication: a denial, a timetable, a past event, a hypothetical
    ...['Is Untrue', 'Headline Incorrect', 'Is Inaccurate', 'Hoax Debunked', 'According to Unverified Social Media Posts',
        'Soon', 'by Year-End', 'in Q1 2027', 'Will Follow', 'Must Wait', 'Hinges on Inspection', 'Unless Mineralys Misses Deadline',
        'in 2024', 'in Dogs', 'Then Pulls It Days Later', 'in June', 'in Adults in Europe']
      .map(x => ['MLYS', `FDA Approves Lorundrostat for Hypertension ${x}`]),
    ['MLYS', 'Lorundrostat Approved by the FDA for Hypertension Soon'],
    ['MLYS', 'Mineralys Announces FDA Approval of Lorundrostat for Hypertension by Year-End'],
    ['MLYS', 'Mineralys Receives Complete Response Letter for Lorundrostat in Hypertension Last Year'],
    ['MLYS', 'Mineralys Receives Complete Response Letter for Lorundrostat in Hypertension in 2025'],
    ['MLYS', 'Lorundrostat Receives Complete Response Letter in Hypertension in June'],
    ['MLYS', 'FDA Issues Complete Response Letter for Lorundrostat in Hypertension Nine Months Ago'],
    ['MLYS', 'Lorundrostat Receives Complete Response Letter in Hypertension Overturned on Appeal'],
    ['MLYS', 'Lorundrostat Receives Complete Response Letter in Hypertension Lifted'],
    // separators, quote marks and look-alike or invisible characters
    ...['–Mineralys Denial', ' -Satire', ' ⸺ Satire', ' / Satire', ' ~ Satire Piece', ' ¦ Spoof', ' · Spoof', ' ･ Spoof',
        ' ؛ Spoof', ' ︰ Spoof', ' ꞉ Spoof', ' ⁏ Spoof', ' «Satire»', ' (Satire)', ' Is Fаke', ' N⁡ot', ' N͏ot', ' Fake️',
        ' \u{E0046}\u{E0041}\u{E004B}\u{E0045}', '᠎ Fake']
      .map(x => ['MLYS', `FDA Approves Lorundrostat for Hypertension${x}`]),
  ]) {
    const c = onRow(t, title, m);
    assert.equal(c.ok, false, `should hold: ${title}`);
  }
});

test('red team 4: an exhibit is read whole, never in part', () => {
  const D = '<p>RADNOR, Pa., Dec. 22, 2026 -- Mineralys today announced</p>';
  const H = 'Mineralys Therapeutics Announces FDA Approval of Lorundrostat for Hypertension';
  const post = html => onRow('MLYS', exhibitHeadline(html, ['Mineralys Therapeutics, Inc.'])).ok;
  assert.equal(post(`<p>Exhibit 99.1</p><p>Mineralys Therapeutics, Inc.</p><p>${H}</p>${D}`), true, 'labels and the letterhead name are skipped');
  for (const html of [
    `<p>RETRACTION</p><p>${H}</p>${D}`,
    `<p>CORRECTION</p><p>${H}</p>${D}`,
    `<p>Fake release notice</p><p>${H}</p>${D}`,
    `<!-- <p>FDA Approves Lorundrostat for Hypertension</p> --><p>Mineralys Announces FDA Extension</p>${D}`,
    `<div style="display:none"><p>${H}</p></div><p>Mineralys Announces FDA Extension</p>${D}`,
    `<div style="display: none"><p>${H}</p></div>${D}`,
    `<p hidden>${H}</p>${D}`,
    `<p><s>${H}</s></p><p>Mineralys Withdraws Erroneous Release</p>${D}`,
    `<p><strike>${H}</strike></p>${D}`,
    `<p><del>${H}</del></p>${D}`,
    `<p style="text-decoration: line-through">${H}</p>${D}`,
    `<head><title>Lorundrostat Receives Complete Response Letter in Hypertension</title></head><body>${D}`,
    `<p>Lorundrostat Receives Complete Response Letter in Hypertension</p><p>(Originally issued 06/02/2026)</p>${D}`,
    `<p>FDA Approves Lorundrostat for Hypertension</p><p>Rumor Denied by Company; FDA Review Continues</p>${D}`,
  ]) assert.equal(post(html), false, html);
  assert.equal(exhibitHeadline(`<p>FDA Approves Lorundrostat</p><p>for Hypertension</p>${D}`), 'FDA Approves Lorundrostat for Hypertension', 'a headline over two blocks');
  assert.equal(exhibitDate(`<p>${H}</p><p>(Originally issued 2026-06-02)</p>${D}`), '');
});

test('red team 4: the owner\'s control and a damaged store fail safe', () => {
  assert.deepEqual(readControl(null), {});
  assert.deepEqual(readControl('{"publish":true}'), { publish: true });
  assert.deepEqual(readControl('{"retract":{"pdufa_mlys_2026-12-22":""}}'), { retract: { 'pdufa_mlys_2026-12-22': '' } });
  for (const bad of ['{"retract":["pdufa_mlys_2026-12-22"]}', '{"retract":"pdufa_mlys_2026-12-22"}', '{"retract":null}',
                     '{"publish":"false"}', '{"publish":"true"}', '{"hide":"yes"}', '{"Publish":false}', 'false', 'off', '[]', '{bad'])
    assert.deepEqual(readControl(bad), { publish: false, bad: true }, bad);
  for (const v of [null, undefined]) assert.deepEqual(readState(v), {}, 'no key: empty');
  for (const v of ['null', '[]', '"x"', '{bad', '5', '{"pub":{"a":1}']) assert.equal(readState(v), null, `damaged: ${v}`);
});

// ---- red team 5 ----
test('red team 5: hidden marks and long headlines are held on every channel, not only as raw titles', () => {
  const D = '<p>RADNOR, Pa., Dec. 22, 2026 -- Mineralys today announced</p>';
  const strike = [...'FDA Approves Lorundrostat for Hypertension'].map(c => c + '̶').join('');
  const tagged = 'FDA Approves Lorundrostat for Hypertension\u{E0046}\u{E0041}\u{E004B}\u{E0045}';
  for (const h of [strike, tagged]) {
    assert.equal(onRow('MLYS', exhibitHeadline(`<p>${h}</p>${D}`)).ok, false, 'exhibit');
    const it = parseFeed(`<rss><item><title>${h}</title><link>https://ir.mineralys.com/a</link><pubDate>Tue, 22 Dec 2026 21:07:00 GMT</pubDate></item></rss>`)[0];
    assert.equal(it.title, '', 'feed title');
    assert.equal(pageDay(`<p>${h}</p>${D}`, 'FDA Approves Lorundrostat for Hypertension'), '', 'page');
  }
  const long = 'Mineralys Therapeutics, Inc. Announces U.S. Food and Drug Administration Approval of LORVENZA (lorundrostat) Tablets, the First and Only Oral Aldosterone Synthase Inhibitor, for the Treatment of Adults and Patients With Uncontrolled or Resistant High Blood Pressure (Hypertension) in Combination Without Diuretics; FDA Issues Complete Response Letter for the Fixed-Dose Combination';
  assert.equal(exhibitHeadline(`<p>${long}</p>${D}`), '');
  assert.equal(onRow('MLYS', long).ok, false);
});

test('red team 5: a past-tense letter or approval is an old one, and a brand is never another INN', () => {
  for (const [t, h] of [
    ['UNCY', 'Unicycive Received Complete Response Letter for Oxylanthanum Carbonate for Hyperphosphatemia'],
    ['AQST', 'Aquestive Therapeutics Announced Receipt of Complete Response Letter for Anaphylm for Anaphylaxis'],
    ['MLYS', 'FDA Issued Complete Response Letter for Lorundrostat in Hypertension'],
    ['MLYS', 'Lorundrostat Received Complete Response Letter in Hypertension'],
    ['MLYS', 'Mineralys Announced FDA Approval of Lorundrostat for Hypertension'],
    ['MLYS', 'FDA Granted Approval to Lorundrostat for Hypertension'],
    ['MLYS', 'FDA Approves Baxdrostat (lorundrostat) for Hypertension'],
    ['MLYS', 'FDA Approves Keytrudamab (lorundrostat) for Hypertension'],
  ]) assert.equal(onRow(t, h).ok, false, h);
});

test('red team 5: a confirmed post is not withdrawn by a record that only went quiet', () => {
  const src = { published_at: '2026-12-01T16:05:00-05:00' };
  const conf = { k: { id: 'k', kind: 'approval', status: 'confirmed', source: src } };
  assert.equal(reconcile(conf, { status: {} }, NOW + 9 * 86400000).k.status, 'confirmed', 'row gone');
  assert.equal(reconcile(conf, { status: { k: { st: 'Upcoming' } } }, NOW + 9 * 86400000).k.status, 'confirmed', 'under review for a build');
  const post = { a: { id: 'a', kind: 'approval', status: 'posted', source: src } };
  assert.equal(reconcile(post, { status: { a: { st: 'Decided', oc: 'Accelerated approval', dcd: '2026-12-01' } } }, NOW).a.status, 'confirmed');
  assert.equal(reconcile(post, { status: { a: { st: 'Decided', oc: 'Not approved', dcd: '2026-12-01' } } }, NOW).a.status, 'posted', 'an unclear outcome waits');
});

test('red team 5: a feed item\'s page must carry its title above a same-day dateline', () => {
  const T = 'FDA Approves Lorundrostat for Hypertension';
  const D = '<p>RADNOR, Pa., Dec. 22, 2026 -- Mineralys today announced</p>';
  assert.equal(pageDay(`<div style="display:none">menu</div><h1>${T}</h1>${D}`, T), '2026-12-22', 'hidden page furniture is fine');
  assert.equal(pageDay(`<h1>FDA Approves Lorundrostat for Hypertension in Dogs</h1>${D}`, T), '', 'the feed cut the title short');
  assert.equal(pageDay(`<h1>${T}</h1><p>Reissued 06/02/2026</p>${D}`, T), '');
});

test('recall after red team 5', () => {
  for (const [t, h, m] of [
    ['NTLA', 'Intellia Announces FDA Approval of Lonvoguran Ziclumeran to Prevent Attacks of Hereditary Angioedema'],
    ['CORT', 'Corcept Announces FDA Approval of Relacorilant for Patients With Hypertension Secondary to Hypercortisolism'],
    ['MLYS', 'FDA Approves Lorundrostat (MLS-101) for Hypertension'],
    ['AXSM', 'FDA Approves AXS-12 (reboxetine) for Cataplexy in Narcolepsy'],
    ['SVRA', 'FDA Approves MOLBREEVI Inhalation Solution for Autoimmune Pulmonary Alveolar Proteinosis'],
    ['CGEM', 'Cullinan Therapeutics and Taiho Oncology Announce FDA Approval of Zipalertinib for NSCLC With EGFR Exon 20 Insertion Mutations'],
  ]) { const c = onRow(t, h, m); assert.equal(c.ok, true, `${h}: ${c.why}`); }
  const H = 'Mineralys Announces FDA Approval of Lorundrostat for Hypertension';
  assert.equal(exhibitDate(`<p>${H}</p><p>RADNOR, Pa., DECEMBER 22, 2026 -- x</p>`), '2026-12-22', 'a month in capitals');
  assert.equal(exhibitDate(`<p>${H}</p><p>RADNOR, Pa.,\nDec. 22,\n2026 -- x</p>`), '2026-12-22', 'a line break inside the dateline');
  assert.equal(exhibitHeadline(`<p>FDA Approves Mineralys&#146; Lorundrostat for Hypertension</p><p>RADNOR, Pa., Dec. 22, 2026 -- x</p>`), "FDA Approves Mineralys' Lorundrostat for Hypertension");
});

test('red team 6: a sponsor word or a non-drug word is never a brand', () => {
  for (const h of ['FDA Approves Placebo (lorundrostat) for Hypertension', 'FDA Approves Mineralys (lorundrostat) for Hypertension',
                   'FDA Approves Therapy (lorundrostat) for Hypertension'])
    assert.equal(onRow('MLYS', h).ok, false, h);
  assert.equal(onRow('MLYS', 'FDA Approves Lorundrostat for Hypertension').ok, true);
});

test('red team 6: text a reader sees outside the page text voids the exhibit', () => {
  const D = '<p>RADNOR, Pa., Dec. 22, 2026 -- x</p>', H = '<p>Mineralys Announces FDA Approval of Lorundrostat for Hypertension</p>';
  assert.equal(exhibitHeadline(H + D), 'Mineralys Announces FDA Approval of Lorundrostat for Hypertension');
  for (const x of ['<!--><p>CORRECTION: WITHDRAWN</p>', '<!---><p>CORRECTION: WITHDRAWN</p>', '<!-- a --!><p>CORRECTION: WITHDRAWN</p>'])
    assert.match(exhibitHeadline(x + H + D), /^CORRECTION: WITHDRAWN /, x);        // read, so the whole fails to parse
  for (const x of ['<input value="CORRECTION:">', '<img alt="WITHDRAWN" src="a.png">', '<svg><text>Not</text></svg>', '<iframe src="x"></iframe>'])
    assert.equal(exhibitHeadline(x + H + D, ['Mineralys Therapeutics, Inc.']), '', x);
  for (const x of ['<img alt="NOT APPROVED">', '<img alt="Update: FDA letter">', '<img alt="Retracted">'])
    assert.equal(exhibitHeadline(x + H + D, ['Mineralys Therapeutics, Inc.']), '', x);
  for (const x of ['<img alt="Mineralys Therapeutics logo" src="a.png">', '<img alt="ex99-1_001.jpg" src="a.png">', '<img src="a.png">',
                   '<img alt="A blue and white logo Description automatically generated" src="a.png">', '<img alt="Company Logo">',
                   '<img alt="MLYS">', '<img alt="Text Description automatically generated with medium confidence">'])
    assert.notEqual(exhibitHeadline(x + H + D, ['Mineralys Therapeutics, Inc.']), '', x);
});

test('red team 6: a hand-edited state is damaged, not empty', () => {
  for (const v of ['{"pub":{"x":null}}', '{"pub":[]}', '{"seen":null}', '{"done":[1]}', '{"rss":"x"}'])
    assert.equal(readState(v), null, v);
  assert.deepEqual(readState('{"pub":{},"seen":{"edgar|x":null}}'), { pub: {}, seen: { 'edgar|x': null } });
});

test('red team 6: a post once made is never made again', () => {
  const it = { channel: 'edgar', cik: 1933414, title: 'Mineralys Announces FDA Approval of Lorundrostat for Hypertension', exDay: TODAY, url: 'https://www.sec.gov/x', atMs: ago(2), key: 'edgar|1' };
  assert.equal(check(it, ARMED, {}, NOW).ok, true);
  for (const k of ['pdufa_mlys_2026-12-22', 'https://www.sec.gov/x', 'edgar|1'])
    assert.equal(check(it, { ...ARMED, done: { [k]: ago(60) } }, {}, NOW).ok, false, k);
});

test('red team 6: the record may date the decision a few days before the release, and its outcome is what it opens with', () => {
  const rec = { id: 'a', kind: 'approval', status: 'posted', source: { published_at: '2026-11-23T08:00:00-05:00' } };
  const at = h => Date.parse('2026-11-23T13:00:00Z') + h * 3600000;
  const st = (oc, dcd) => ({ ...ARMED, status: { a: { st: 'Decided', oc, dcd } } });
  assert.equal(reconcile({ a: rec }, st('Approved', '2026-11-20'), at(80)).a.status, 'confirmed', 'Friday action, Monday release');
  assert.equal(reconcile({ a: rec }, st('Approved', '2026-11-10'), at(80)).a.status, 'retracted', 'two weeks before: not this release');
  assert.equal(reconcile({ a: rec }, st('Approved', '2026-11-23'), at(1)).a.status, 'confirmed');
  assert.equal(reconcile({ a: rec }, st('CRL', '2026-11-23'), at(1)).a.status, 'retracted');
  assert.equal(reconcile({ a: rec }, st('Not approvable letter', '2026-11-23'), at(1)).a.status, 'retracted');
  // both kinds of word, or "approvable": unclear, so the post waits (red team 7)
  for (const oc of ['Approved (after CRL)', 'Approved in part; CRL for second indication', 'Approvable letter'])
    for (const kind of ['approval', 'crl'])
      assert.equal(reconcile({ a: { ...rec, kind } }, st(oc, '2026-11-23'), at(1)).a.status, 'posted', `${oc} / ${kind}`);
});

test('red team 6: the sponsor\'s own correction withdraws a live post', () => {
  const r = ARMED.rows[0];
  const pub = { [r.id]: { status: 'posted', source: { url: 'https://www.sec.gov/a', published_at: etIso(ago(60)) } } };
  const item = (title, o = {}) => ({ channel: 'edgar', cik: r.cik, title, atMs: ago(5), url: 'https://www.sec.gov/b', ...o });
  for (const h of ['Mineralys Retracts Press Release Regarding FDA Approval of Lorundrostat; No FDA Decision Has Been Received',
                   'Mineralys Issues Correction to Earlier Release Regarding FDA Decision', 'Mineralys Clarifies Status of Lorundrostat Application',
                   'Mineralys Updates Previously Issued Press Release Regarding Lorundrostat', 'Mineralys Comments on False Report of FDA Approval',
                   'Mineralys Issues Statement Regarding Inaccurate Report on Lorundrostat', 'Mineralys Amends Press Release Regarding FDA Approval',
                   'FDA Approval of Lorundrostat Has Not Occurred; Mineralys Statement', 'Mineralys Notes Misstatement in Lorundrostat Release',
                   'Mineralys Says FDA Has Not Yet Approved Lorundrostat'])
    assert.deepEqual(corrections(item(h), ARMED, pub), [r.id], h);
  assert.deepEqual(corrections(item('Mineralys Retracts Press Release', { atMs: ago(90) }), ARMED, pub), [], 'older than the post');
  assert.deepEqual(corrections(item('Mineralys Retracts Press Release', { cik: 1088856 }), ARMED, pub), [], 'another sponsor');
  assert.deepEqual(corrections(item('Mineralys to Present at Conference'), ARMED, pub), []);
  const conf = { [r.id]: { ...pub[r.id], status: 'confirmed' } };
  assert.deepEqual(corrections(item('Mineralys Issues Correction to Earlier Release Regarding FDA Decision'), ARMED, conf), [], 'a confirmed post needs the drug named');
  // routine news that corrects a date, a call time or a media report about something else withdraws nothing (red team 7)
  for (const h of ['CORRECTING and REPLACING Mineralys to Report Fourth Quarter Results; Updated Conference Call Release Time',
                   'Mineralys Issues Statement Clarifying Timing of Phase 3 Readout', 'Mineralys Statement on Erroneous Media Report About Acquisition',
                   'Mineralys Corrects Date of Investor Day Announcement', 'Mineralys Announces Withdrawal of European MAA for Lorundrostat; Statement'])
    assert.deepEqual(corrections(item(h), ARMED, pub), [], h);
  // a correction that strikes the old words through is read from its text above the dateline, struck text included
  assert.deepEqual(corrections(item('', { ctitle: correctionHeadline('<p>CORRECTION: <del>FDA Approves</del> Lorundrostat Not Yet Approved</p><p>RADNOR, Pa., Dec. 1, 2026 -- x</p>') }), ARMED, pub), [r.id]);
  // a feed item read in the feed's first read, or linking off-site, is not read for corrections
  const fr = { channel: 'rss', feed: 'https://ir.mineralys.com/rss', url: 'https://ir.mineralys.com/news/2', atMs: ago(5), title: 'Mineralys Retracts Lorundrostat Release' };
  assert.deepEqual(corrections({ ...fr, fresh: true }, ARMED, pub), [r.id]);
  assert.deepEqual(corrections({ ...fr, fresh: false }, ARMED, pub), []);
  assert.deepEqual(corrections({ ...fr, fresh: true, url: 'https://evil.example/news/2' }, ARMED, pub), []);
  assert.deepEqual(corrections(item('Mineralys Corrects Lorundrostat Label Statement'), ARMED, conf), [r.id]);
});
