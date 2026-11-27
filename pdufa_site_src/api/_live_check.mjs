/** The fast lane's automatic check: may a news item be posted on pdufa.bio within the minute?
 *
 *  David, 2026-11-27: "Ensure its down to minutes" and "Fake news is worst than no news at all". So the check is
 *  built to say NO. An item is posted only when EVERY rule below holds; anything else waits for the existing
 *  watchers' HELD lead and a full review (news-watch.yml, quarantine_leads.py), exactly as before.
 *
 *   0. A reviewed application. Only rows on _fast_lane.json's hand-reviewed list are armed (build_watch_armed.py),
 *      each with its drug's own brand, code or full INN (terms), its exact indication phrases (phrases), the few
 *      other words its indication may carry (tok), its partner drugs (partners), its dosage forms (forms), other
 *      names its sponsor uses (aliases), need words and avoid words.
 *   1. Primary source. The sponsor's own SEC filing (8-K / 6-K under the sponsor's CIK; the headline is everything
 *      above the exhibit's dateline, whose day must be the filing's day), or a NEW item in the sponsor's own news
 *      feed (not in the feed's first read; on the feed's own host; its page's dateline the day of its time). A
 *      newswire release alone is never posted: a forger writes every word of it.
 *   2. A decision headline, start to end, in one of a few fixed shapes built from that row's own words (see "the
 *      whole-headline grammar" below): the decision, the drug, and a closing clause made only of closed words that
 *      names one of the row's own indication phrases. Plain text only, the U.S. FDA and no other regulator, and none
 *      of the words that make it something else (NEG: an acceptance, a timetable, a denial, a trial, a rival ...).
 *   3. One application: exactly one armed row fits, none of its avoid words, no narrowing word it does not need, no
 *      other armed drug.
 *   4. Fresh and in range. The source carries a time to the minute with its zone, no more than 12 hours old, and
 *      falls between 120 days before and 45 days after the goal date.
 *   5. Not yet posted (by row or by source), not withdrawn by hand, not first seen or published while posting was stopped, and
 *      the row is still awaiting a decision in the reviewed dataset.
 *
 *  The post quotes the source's headline, attributed to it ("Unicycive's SEC filing (8-K) says: "...""). Times are
 *  shown in Eastern time with the zone (RULE 1). Guards: tests/live_watch.test.mjs, tests/test_live_watch.py. */

// The FDA, or the U.S. as the place of approval ("Hibsago approved in the US", GSK headlines name no FDA).
export const FDA_RE = /\bFDA\b|\bapproved (?:in|by) (?:the )?(?:US|U\.S\.)(?![A-Za-z])|\b(?:US|U\.S\.) approval\b/i;
export const APPROVE_RE = /\b(approves|approved|approval (?:of|for|to)|grants? (?:\w+ ){0,2}approval|receives? (?:\w+ ){0,3}approval|wins? (?:\w+ ){0,2}approval|secures? (?:\w+ ){0,2}approval|gains? (?:\w+ ){0,2}approval|obtains? (?:\w+ ){0,2}approval)\b/i;
export const CRL_RE = /\b(complete response letter|CRL)\b/i;
export const NEG_RE = new RegExp('\\b(' + [
  'if approved', 'potential\\w*', 'seek\\w*', 'accept\\w*', 'submi\\w*', 'fil(?:e|es|ed|ing)', 'priority review',
  'breakthrough', 'fast track', 'orphan', 'rare pediatric', 'PDUFA', 'target action', 'goal date', 'anticipat\\w*',
  'expect\\w*', 'plan\\w*', 'upcoming', 'advisory committee', 'meeting', 'type [abc]', 'expanded access',
  'emergency use', 'IND', 'clearance', 'cleared', '510\\(k\\)', 'tentative', 'previously approved', 'anniversary',
  'launch\\w*', 'availab\\w*', 'extend\\w*', 'extension', 'delay\\w*', 'postpone\\w*', 'withdr\\w*',
  'refus\\w*', 'rolling', 'positive opinion', 'recommend\\w*', 'present\\w*', 'data', 'results', 'study', 'trials?',
  'phase', 'pivotal', 'waiver', 'REMS', 'pathway', 'path', 'timeline', 'proprietary', 'name', 'design', 'ongoing',
  'review', 'request\\w*', 'designation', 'program\\w*', 'agreement', 'clarity', 'ahead', 'toward\\w*',
  'webcast', 'conference call', 'earnings', 'quarter', 'financial', 'update on', 'regulatory update',
  'would', 'could', 'may(?!\\s+\\d)', 'aims?', 'intends?', 'pending', 'under review', 'proposed', 'draft',
  'not', 'no', 'never', 'den(?:y|ies|ied)', 'rescind\\w*', 'revok\\w*', 'reject\\w*', 'label\\w*', 'site', 'facility',
  'manufactur\\w*', 'protocol', 'amendment', 'milestone\\w*', 'royalt\\w*', 'million', 'billion', 'shares?',
  'stock', 'investor\\w*', 'investigat\\w*', 'alert', 'lawsuit', 'class action', 'rival\\w*', 'compet\\w*',
  'statement', 'comments?', 'respond\\w*', 'resolv\\w*', 'partner\\w*', 'licens(?:e|es|ing) (?:agreement|deal)s?', 'licensing', 'in-licens\\w*', 'unaffected',
  'following', 'after', 'generic', 'biosimilar', 'versus', 'vs', 'reports?', 'rumou?r\\w*', 'speculat\\w*',
  'supplement\\w*', 'expan\\w*', 'new indication', 'formulation', 'dos(?:e|es|ing)',
  // a denial, a hypothetical, a correction or a fake, and access programmes (red team 3)
  '\\w+n\'t', 'cannot', 'unlikely', 'yet', 'once', 'when', 'if', 'hopes?', 'hoped', 'claim\\w*', 'false\\w*', 'fake\\w*',
  'fraud\\w*', 'erroneous\\w*', 'errors?', 'correct\\w*', 'retract\\w*', 'disavow\\w*', 'mistak\\w*', 'challenger',
  'beat\\w*', 'rescission', 'reversal', 'revers\\w*', 'compassionate', 'early access', 'named[- ]patient', 'right to try',
  'single[- ]patient', 'says?', 'said', 'warns?', 'asks?', 'court', 'order\\w*', 'hire\\w*',
  // a timetable or a status, not a decision (red team 2)
  'decision', 'next', 'await\\w*', 'advanc(?:e|es|ing|ement)', 'develop(?:s|ed|ing|ment)?', 'guidance', 'continu\\w*', 'remain\\w*',
  'set for', 'due', 'schedul\\w*', 'slated', 'target(?:s|ing)?', 'timing', 'reiterat\\w*', 'also', 'while',
  // a contrast, a denial or a reversal written after the decision (red team 4)
  'without', 'instead', 'other than', 'beyond', 'except\\w*', 'exclud\\w*', 'unless', 'soon', 'untrue', 'inaccura\\w*',
  'incorrect\\w*', 'hoax\\w*', 'debunk\\w*', 'satir\\w*', 'spoof\\w*', 'parod\\w*', 'unverified', 'overturn\\w*',
  'lift\\w*', 'pull\\w*', 'recall\\w*', 'suspen\\w*', 'halt\\w*', 'last year', 'ago',
].join('|') + ')\\b', 'i');
export const ADJ_RE = /FDA-approved|FDA approved (?:drug|product|therapy|treatment|medicine)/i;
export const OTHER_REG = /\b(EU|Europe\w*|EC|EMA|CHMP|Japan\w*|China|Chinese|NMPA|PMDA|MHRA|UK|British|Kingdom|Canad\w*|Swiss\w*|TGA|Australia\w*|Brazil\w*|ANVISA|Korea\w*|MFDS|Taiwan\w*|TFDA|Saudi|SFDA|Jordan\w*|JFDA|Israel\w*|Hong Kong|Macau|Singapore\w*|HSA|India\w*|CDSCO|Mexic\w*|COFEPRIS|Russia\w*|Thai\w*|Philippine\w*|Indonesia\w*|Turk\w*|Egypt\w*|Argentin\w*|Chile\w*|Colombia\w*|Malaysia\w*|UAE|Emirat\w*|Ministry|Ghana\w*|Nigeria\w*|Kenya\w*|South Africa\w*|Africa\w*|Asia\w*|Vietnam\w*|Pakistan\w*|Peru\w*|Ecuador\w*|Venezuela\w*|Bangladesh\w*|Sri Lanka\w*|Nepal\w*|Iran\w*|Iraq\w*|Lebanon|Kuwait\w*|Qatar\w*|Bahrain\w*|Oman\w*|Morocc\w*|Tunisia\w*|Algeria\w*|Ethiopia\w*|Uganda\w*|Tanzania\w*|Zimbabwe\w*|Zambia\w*|Philippines|New Zealand|Norw\w*|Swed\w*|Denmark|Danish|Finland|Finnish|Iceland\w*|German\w*|France|French|Ital\w*|Spain|Spanish|Portug\w*|Dutch|Netherlands|Belgi\w*|Austria\w*|Polish|Poland|Czech\w*|Hungar\w*|Roman\w*|Greece|Greek|Ukrain\w*|Kazakh\w*|Latin|Middle East|region\w*|countr\w*|abroad|territor\w*|global\w*|worldwide|international\w*|ex-U\.?S\.?|outside)\b/i;
// The word right before "FDA" must leave it the U.S. agency ("Taiwan FDA", "Saudi FDA" are other agencies).
const FDA_BEFORE_OK = new Set(['', 'u.s.', 'us', 'the', 'of', 'an', 'by', 'from',
  'announce', 'announces', 'announced', 'announcing', 'receive', 'receives', 'received', 'receiving',
  'secure', 'secures', 'secured', 'win', 'wins', 'won', 'gain', 'gains', 'gained', 'obtain', 'obtains', 'obtained',
  'grant', 'grants', 'granted', 'issue', 'issues', 'issued']);
export const WIRES = { 'www.globenewswire.com': 'GlobeNewswire', 'globenewswire.com': 'GlobeNewswire',
  'www.businesswire.com': 'Business Wire', 'businesswire.com': 'Business Wire',
  'www.prnewswire.com': 'PR Newswire', 'prnewswire.com': 'PR Newswire' };

const DAY = 86400000;
const esc = s => String(s).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
/** A case-insensitive pattern for a literal, so the rest of a pattern can stay case-sensitive. */
const ci = s => esc(s).replace(/[A-Za-z]/g, c => `[${c.toLowerCase()}${c.toUpperCase()}]`);

export function termIn(term, text) {
  return new RegExp('(?<![A-Za-z0-9])' + esc(term) + '(?![A-Za-z0-9])', 'i').test(text || '');
}

const NAMED = { nbsp: ' ', ndash: '-', mdash: '-', lsquo: "'", rsquo: "'", ldquo: '"', rdquo: '"', amp: '&',
  quot: '"', apos: "'", trade: ' ', reg: ' ', copy: ' ', hellip: '...' };
// Windows-1252 code points written as numeric entities (&#146; is an apostrophe in a Word export).
const W1252 = { 145: "'", 146: "'", 147: '"', 148: '"', 150: '-', 151: '-', 153: ' ' };
const cp = n => (W1252[n] ?? (Number.isFinite(n) && n > 0 && n <= 0x10FFFF ? String.fromCodePoint(n) : ' '));

function decode(s) {
  return String(s || '').replace(/<[^>]+>/g, ' ')
    .replace(/&#x([0-9a-f]+);/gi, (_, h) => cp(parseInt(h, 16)))
    .replace(/&#(\d+);/g, (_, d) => cp(parseInt(d, 10)))
    .replace(/&([a-z]+);/gi, (m, n) => (NAMED[n.toLowerCase()] ?? ' '));
}

/** Invisible marks other than the soft hyphen and zero-width spaces and joiners a word processor leaves: a headline
 *  that hides any (a tag character, a variation selector, an invisible operator) is held, not cleaned. */
export function hiddenMarks(s) {
  return /[\p{Cf}\p{Mn}]/u.test(decode(s).replace(/[\u00AD\u200B-\u200D\u2060\uFEFF]/g, ''));
}

export function clean(s) {
  return decode(s)
    .replace(/[™®©]/g, ' ')                                    // TM, (R), (C): never glue a name
    .normalize('NFKC').replace(/[\p{Cf}\p{Mn}]/gu, '')                 // invisible format marks and combining marks (red team 4)
    .replace(/[‐-―−]/g, '-').replace(/[‘’‛′]/g, "'").replace(/[“”]/g, '"')
    .replace(/[<>]/g, ' ').replace(/\s+/g, ' ').trim();
}

/** A headline made ready for the fixed shapes: cleaned, "Food and Drug Administration" read as "FDA". */
export function norm(title) {
  return clean(title).replace(/\bFood\s+(?:and|&)\s+Drug\s+Administration\b(?:\s*\((?:U\.?S\.?\s*)?FDA\))?/gi, 'FDA')
    .replace(/\bFDA\s*\(FDA\)/g, 'FDA')
    // an age bound is one closed word ("Ages 12 and Older", "12 Years of Age and Older"); a year never is
    .replace(/\b(?:aged?|ages)\s+\d{1,2}(?:\s+(?:years?|months?))?(?:\s+(?:of\s+age\s+)?(?:and|or)\s+(?:older|above))?(?![A-Za-z0-9])/gi, 'aged')
    .replace(/\b\d{1,2}\s+(?:years?|months?)\s+(?:of\s+age\s+)?(?:and|or)\s+(?:older|above)(?![A-Za-z0-9])/gi, 'aged');
}

/** 'approval' | 'crl' | null, and why not. */
export function headlineKind(title) {
  const t = norm(title);
  // "Complete Response Letter" is the FDA's own term: a headline that says it needs no "FDA" (Unicycive, June 2026).
  if (!FDA_RE.test(t) && !/\bcomplete response letter\b/i.test(t)) return { kind: null, why: 'headline does not name the FDA' };
  if (OTHER_REG.test(t)) return { kind: null, why: 'headline names another regulator' };
  if (/[?"]/.test(t)) return { kind: null, why: 'headline asks or quotes' };
  if (hiddenMarks(title)) return { kind: null, why: 'headline holds invisible characters' };
  // Plain text only (red team 4: guillemets, look-alike letters, "/", "~", "·" and other separators carried a second
  // clause or a "Fake" past every word list). A hyphen joins two words; it never stands alone or at an edge.
  if (/[^A-Za-z0-9 ',.()%+&-]/.test(t)) return { kind: null, why: 'headline has a character outside plain text' };
  if (/(?:^|[^A-Za-z0-9])-|-(?:[^A-Za-z0-9]|$)/.test(t)) return { kind: null, why: 'headline has a dash between clauses' };
  if (/[A-Za-z0-9\-\/_.]FDA\b/.test(t)) return { kind: null, why: 'headline glues something to "FDA"' };
  for (const m of t.matchAll(/(?:^|\s)(\S*)\s+(?=FDA\b)/gi)) {
    if (!FDA_BEFORE_OK.has(m[1].toLowerCase().replace(/[,;:(]+$/, '').replace(/^\(/, ''))) return { kind: null, why: `headline says "${m[1]} FDA"` };
  }
  if (ADJ_RE.test(t)) return { kind: null, why: 'headline calls something FDA-approved, not a new decision' };
  const neg = t.match(NEG_RE);
  if (neg) return { kind: null, why: `headline says "${neg[0]}"` };
  const a = APPROVE_RE.test(t), c = CRL_RE.test(t);
  if (a && !c) return { kind: 'approval', why: '' };
  if (c && !a) return { kind: 'crl', why: '' };
  return { kind: null, why: a && c ? 'headline names both an approval and a letter' : 'headline names no decision' };
}

// ---------- the whole-headline grammar ----------
//
// Red team 3 (2026-11-27) got a decision "shape" through inside a longer sentence; red team 4 got one through with a
// second meaning in the words after the drug ("... for Hypertension Is Untrue", "... in Dogs", "... in 2024", "for
// Pulmonary Arterial Hypertension", "(With Amlodipine)"). So the WHOLE headline must parse, start to end, as one of
// these shapes for ONE armed row, built from that row's own reviewed words, and anything else is held:
//
//   A1  FDA Approves | FDA Has Approved | FDA Grants [kind] Approval to|for                    DRUG [PARTNER] REST
//   A2  CO Announces|Receives|Secures|Wins|Gains|Obtains [the] FDA [kind] Approval of|for     DRUG [PARTNER] REST
//   A3  [CO's] DRUG [PARTNER] Receives|Wins|Gains|Secures|Obtains|Granted FDA [kind] Approval            REST
//   A4  [CO's] DRUG [PARTNER] [Is|Has Been] Approved by [the] FDA | Approved in the U.S.                 REST
//   A5  CO Announces [that] [the] FDA Has Approved                                          DRUG [PARTNER] REST
//   C1  CO Announces|Receives [Receipt of] [a] [FDA] CRL [from the FDA] for|regarding [its] DRUG [APP]    REST
//   C2  [CO's] DRUG Receives [a] [FDA] Complete Response Letter                                          REST
//   C3  FDA Issues [a] Complete Response Letter for|regarding                                 DRUG [APP] REST
//
//   CO       the sponsor's own name (a leading run of its words) or a reviewed alias, never any other words
//   DRUG     [CO's] TERM [form words] [(TERM)] [form words]   or   [CO's] BRAND (TERM) [form words]
//            TERM: one of the row's own terms; BRAND: one capitalised word, not a filing type or another armed drug;
//            form words: tablets or capsules, or the row's own (forms)
//   PARTNER  plus|with|and|in combination with  one of the row's own partner drugs (partners)
//   REST     [, [the|a|an] <closed words>[,]]  for|to|to treat|in|as  <1 to 20 closed words>  [.]  end
//   closed   the generic patient words below, the row's own indication phrases, tok and partner words; nothing else
//            (no year, month, verb, other disease, other drug or second clause can be written with them)
// and the closing clause must name one of the row's own indication phrases, whole.

const US = `(?:${ci('U.S.')}\\s+|${ci('US')}\\s+)?`;
const FDA = `${US}FDA`;
const KIND = `(?:(?:${ci('accelerated')}|${ci('full')}|${ci('traditional')})\\s+)?`;
const APPROVAL = ci('approval');
const LETTER = `(?:${ci('complete response letter')}|CRL)`;
const byLen = words => [...new Set(words.filter(Boolean))].sort((a, b) => b.length - a.length);
const alt = words => `(?:${byLen(words).map(ci).join('|')})`;
const wordAlt = words => `(?:${byLen(words).map(w => ci(w).replace(/ /g, '\\s+')).join('|')})(?![A-Za-z0-9'-])`;
const APP = `(?:\\s+(?:NDA|BLA|${ci('new drug application')}|${ci('biologics license application')}))?`;
// Words that may stand in any closing clause: who is treated, and how far the disease has gone. No disease, body
// part, drug, place, time, verb or negation is among them.
const TAIL_GENERIC = ['for', 'to', 'treat', 'treatment', 'treating', 'the', 'of', 'in', 'with', 'and', 'or', 'a', 'an',
  'patients', 'patient', 'adult', 'adults', 'people', 'individuals', 'who', 'have', 'aged', 'older', 'combination',
  'uncontrolled', 'relapsed', 'refractory', 'advanced', 'metastatic', 'recurrent', 'unresectable', 'locally',
  'moderate', 'severe', 'moderate-to-severe', 'symptomatic'];
const APPOS_GENERIC = ['first', 'only', 'and', 'first-in-class', 'oral', 'treatment', 'therapy', 'medicine', 'drug',
  'option', 'non-steroidal', 'nonsteroidal', 'novel', 'new'];
const INN_STEM = /(?:mab|cept|nib|stat|tide|vir|parin|olol|pril|sartan|azole|cillin|mycin|cycline|platin|taxel|rubicin|gene|cel|leucel|ase|dronate|lukast|setron|tinib|ciclib|lisib|rafenib|degib|parib|zomib|lidomide|domide|tamide|trigine|dirsen|siran|rsen|gliflozin|glutide|tide|ximab|zumab|umab)$/i;
const BAD_BRAND = new Set(['anda', 'nda', 'snda', 'bla', 'sbla', 'fda', 'generic', 'new', 'oral', 'drug', 'the', 'its',
  'once', 'first', 'only', 'novel', 'teva', 'sandoz', 'viatris', 'mylan', 'hikma', 'amneal', 'lupin', 'cipla',
  'placebo', 'vehicle', 'sham', 'candidate', 'therapy', 'treatment', 'product', 'medicine', 'medication', 'biosimilar',
  'investigational', 'experimental', 'compound', 'molecule', 'agent', 'program', 'injection', 'infusion', 'vaccine',
  'company', 'companys', 'partner', 'rival', 'competitor', 'competing', 'unapproved', 'unrelated', 'another', 'other']);
// A brand is never a word of an armed sponsor's own name or alias ("FDA Approves Mineralys (lorundrostat)", red team 6).
const coWords = all => new Set(all.flatMap(o => [o.company || '', ...(o.aliases || [])])
  .flatMap(c => String(c).toLowerCase().split(/[^a-z0-9]+/)).filter(w => w.length > 2));

/** The sponsor's own name as a pattern: a leading run of its words ("Mineralys", "Mineralys Therapeutics"),
 *  hyphen or space between them ("Bristol Myers Squibb"), with an optional corporate suffix, or a reviewed alias
 *  ("Kite" for Gilead); two of them joined by "and" for a joint release. */
function coPattern(company, aliases = []) {
  const words = shortCompany(company).split(/[\s-]+/).filter(w => /^[A-Za-z0-9.']+$/.test(w));
  const runs = [];
  for (let n = words.length; n >= 1; n--) runs.push(words.slice(0, n).map(ci).join('[\\s-]+'));
  for (const a of aliases) if (/^[A-Za-z0-9.' -]+$/.test(a)) runs.push(ci(a.trim()).replace(/ /g, '[\\s-]+'));
  if (!runs.length) return null;
  const one = `(?:${runs.sort((a, b) => b.length - a.length).join('|')})(?:,?\\s+(?:${ci('inc')}|${ci('corp')}|N\\.V|${ci('ltd')}|${ci('plc')})\\.?)?`;
  return `${one}(?:\\s+${ci('and')}\\s+${one})?`;
}

function grammar(kind, row) {
  const terms = (row.terms || []).filter(Boolean);
  if (!terms.length || !(row.phrases || []).length) return [];
  const CO = coPattern(row.company, row.aliases || []);
  const T = `(?<![A-Za-z0-9])${alt(terms)}(?![A-Za-z0-9])`;
  const FORM = `(?:\\s+${wordAlt(['tablets', 'tablet', 'capsules', 'capsule', ...(row.forms || [])])})`;
  const POSS = CO ? `(?:${CO}(?:'s|')\\s+)?` : '';
  // in parentheses after the drug: another of its own terms, or a reviewed code or ingredient name (paren)
  const PT = (row.paren || []).length ? `(?:${T}|${wordAlt(row.paren)})` : T;
  const DRUG = `${POSS}(?:${T}${FORM}{0,3}(?:\\s*\\(${PT}\\))?${FORM}{0,3}|(?<brand>[A-Z][A-Za-z0-9]{2,24})\\s*\\(${T}\\)${FORM}{0,3})`;
  const P = (row.partners || []).length ? wordAlt(row.partners) : null;
  const PARTNER = P ? `(?:\\s+(?:${alt(['in combination with', 'plus', 'with', 'and'])}|\\+)\\s+${P})?` : '';
  const tailWords = [...TAIL_GENERIC, ...(row.tok || []),
    ...(row.phrases || []).flatMap(p => p.split(/\s+/)), ...(row.partners || []).flatMap(p => p.split(/\s+/))];
  const W = wordAlt(tailWords);
  const TAIL = `(?<tail>\\s+${wordAlt(['for', 'to treat', 'to', 'in', 'as'])}(?:\\s+(?:${W}|\\(${W}(?:\\s+${W}){0,5}\\))){1,20})`;
  const AW = wordAlt([...APPOS_GENERIC, ...(row.cls || [])]);
  const APPOS = `(?:,\\s+(?:${alt(['the', 'a', 'an'])}\\s+)?${AW}(?:\\s+${AW}){0,8},?)?`;
  const REST = `${APPOS}${TAIL}\\s*\\.?$`;
  const pats = kind === 'approval' ? [
    `^${FDA}\\s+(?:${alt(['approves', 'has approved'])}|${ci('grants')}\\s+${KIND}${APPROVAL}\\s+${alt(['to', 'for'])})\\s+${DRUG}${PARTNER}${REST}`,
    CO && `^${CO}\\s+${alt(['announces', 'announce', 'receives', 'receive', 'secures', 'wins', 'gains', 'obtains'])}\\s+(?:${ci('the')}\\s+)?${FDA}\\s+${KIND}${APPROVAL}\\s+${alt(['of', 'for'])}\\s+${DRUG}${PARTNER}${REST}`,
    `^${DRUG}${PARTNER}\\s+${alt(['receives', 'wins', 'gains', 'secures', 'obtains', 'granted'])}\\s+${FDA}\\s+${KIND}${APPROVAL}${REST}`,
    `^${DRUG}${PARTNER}\\s+(?:${alt(['is', 'has been'])}\\s+)?${ci('approved')}\\s+(?:${ci('by')}\\s+(?:${ci('the')}\\s+)?${FDA}|${ci('in the')}\\s+(?:US|U\\.S\\.)(?![A-Za-z]))${REST}`,
    CO && `^${CO}\\s+${alt(['announces', 'announce'])}\\s+(?:${ci('that')}\\s+)?(?:${ci('the')}\\s+)?${FDA}\\s+${ci('has approved')}\\s+${DRUG}${PARTNER}${REST}`,
  ] : [
    CO && `^${CO}\\s+${alt(['announces', 'announce', 'receives', 'receive'])}\\s+(?:${ci('receipt of')}\\s+)?(?:${alt(['a', 'an'])}\\s+)?(?:${FDA}\\s+)?${LETTER}\\s+(?:${ci('from')}\\s+(?:${ci('the')}\\s+)?${FDA}\\s+)?${alt(['for', 'regarding'])}\\s+(?:${ci('its')}\\s+)?${DRUG}${APP}${REST}`,
    `^${DRUG}\\s+${ci('receives')}\\s+(?:${alt(['a', 'an'])}\\s+)?(?:${FDA}\\s+)?${LETTER}${REST}`,
    `^${FDA}\\s+${ci('issues')}\\s+(?:${alt(['a', 'an'])}\\s+)?${LETTER}\\s+${alt(['for', 'regarding'])}\\s+${DRUG}${APP}${REST}`,
  ];
  return pats.filter(Boolean);
}

/** Does the whole headline parse as a decision on this row's drug for one of its own indication phrases?
 *  all: every armed row (a brand that is another armed drug's term is not this drug's brand). */
export function boundMatch(title, kind, row, all = []) {
  const t = norm(title);
  for (const p of grammar(kind, row)) {
    const m = t.match(new RegExp(p));
    if (!m) continue;
    const g = m.groups || {};
    // a brand is never another drug's INN: no international non-proprietary-name stem (Baxdrostat, Keytruda's pembrolizumab)
    if (g.brand && (BAD_BRAND.has(g.brand.toLowerCase()) || INN_STEM.test(g.brand) || coWords([row, ...all]).has(g.brand.toLowerCase()) || all.some(o => o.id !== row.id && (o.terms || []).some(x => termIn(x, g.brand))))) continue;
    if (!(row.phrases || []).some(ph => new RegExp(`(?<![A-Za-z0-9'-])${ci(ph).replace(/ /g, '\\s+')}(?![A-Za-z0-9'-])`).test(g.tail || ''))) continue;
    return { tail: (g.tail || '').trim(), brand: g.brand || '' };
  }
  return null;
}

export function bound(title, kind, row, all = []) { return !!boundMatch(title, kind, row, all); }

// Words that narrow a drug to one use (a line of therapy, prevention, a regimen): a headline that names one is held
// unless the row's own need words name it (red team 3: "Once-Daily Deucrictibant", "First-Line ... NSCLC").
const NARROW = ['first-line', 'first line', 'frontline', 'front-line', 'second-line', 'newly diagnosed', 'treatment-naive',
  'treatment naive', 'untreated', 'maintenance', 'adjuvant', 'neoadjuvant', 'prevent', 'prevention', 'preventive',
  'prophylaxis', 'prophylactic', 'once-daily', 'once daily', 'long-term', 'long term'];

/** Every armed row of this source the headline decides: {r, term}. */
function deciders(title, kind, rows, all) {
  const out = [];
  const t = norm(title);
  for (const r of rows) {
    if (!(r.need || []).some(w => termIn(w, t))) continue;
    if (!bound(title, kind, r, all)) continue;
    out.push({ r, term: (r.terms || []).find(x => termIn(x, t)) || r.terms[0] });
  }
  return out;
}

/** The one armed row the headline decides, or why there is none. rows: the source's own armed rows; all: every
 *  armed row (a headline that also names another armed drug is held). */
export function pickRow(title, kind, rows, all = rows) {
  const t = norm(title);
  if (!rows.some(r => (r.terms || []).some(x => termIn(x, t)))) return { row: null, why: 'headline names no armed drug' };
  const d = deciders(title, kind, rows, all);
  if (!d.length) {
    const named = rows.find(r => (r.terms || []).some(x => termIn(x, t)));
    if (!(named.need || []).length || !(named.phrases || []).length) return { row: null, why: `${named.id} has no reviewed indication words` };
    return { row: null, why: `the headline is not a plain FDA ${kind === 'approval' ? 'approval' : 'letter'} of ${named.terms.find(x => termIn(x, t))} for its reviewed indication (${named.phrases.join(', ')})` };
  }
  if (d.length > 1) return { row: null, why: `the headline fits ${d.length} armed applications (${d.map(x => x.r.id).join(', ')})` };
  const { r, term } = d[0];
  const av = (r.avoid || []).find(w => termIn(w, t));
  if (av) return { row: null, why: `the headline names "${av}", which marks another application of ${term}` };
  const own = [...(r.need || []), ...(r.tok || []), ...(r.phrases || [])];
  const nw = NARROW.find(w => termIn(w, t) && !own.some(n => termIn(w, n)));
  if (nw) return { row: null, why: `the headline names "${nw}", which may mark another use of ${term}` };
  const other = all.find(o => o.id !== r.id && (o.terms || []).some(x => termIn(x, t)));
  if (other) return { row: null, why: `the headline also names another armed application (${other.id})` };
  return { row: r, term, why: '' };
}
/** Is the source time usable: a real time, at most 12 h old (5 min of clock skew allowed), within the goal window. */
export function timeOk(atMs, nowMs, goal) {
  if (!Number.isFinite(atMs)) return 'the source gives no time with a zone';
  if (atMs > nowMs + 5 * 60000) return 'the source time is in the future';
  if (atMs < nowMs - 12 * 3600000) return 'the source is more than 12 hours old';
  const g = Date.parse(goal + 'T12:00:00Z');
  if (Number.isFinite(g) && (atMs < g - 120 * DAY || atMs > g + 45 * DAY)) return 'the source falls outside 120 days before to 45 days after the goal date';
  return '';
}

/** The wire release's own dateline paragraph is the sponsor's: the FIRST exchange ticker in it ("(Nasdaq: MLYS)") is
 *  the sponsor's; with no ticker at all, the paragraph names the sponsor's full name less its corporate suffix.
 *  A partner's or a supplier's release names its own ticker first, and is not the sponsor's. */
export function leadNames(lead, row) {
  const l = clean(lead);
  if (!l) return false;
  const first = l.match(/\(\s*(?:NASDAQ|NYSE(?:\s+American)?|OTC\w*|TSX|LSE|SIX|Euronext)(?:\s*(?:GS|GM|CM))?\s*:\s*([A-Za-z.]+)\s*[;,)]/i);
  if (first) return first[1].toUpperCase() === String(row.t).toUpperCase();
  const co = shortCompany(row.company);
  return co.split(/\s+/).length >= 2 && termIn(co, l);
}

export function shortCompany(name) {
  let co = String(name || '').trim(), prev;
  do {
    prev = co;
    co = co.replace(/,?\s+(?:Inc\.?|Incorporated|Corporation|Corp\.?|Ltd\.?|Limited|plc|PLC|AG|SE|N\.V\.|NV|S\.A\.|SA|LLC|L\.P\.|Co\.?|& Co\.?|Company|Holdings?|Group)$/i, '').trim();
  } while (co !== prev);
  return co;
}

function etDay(ms) { return etIso(ms).slice(0, 10); }

/** Full check of one item. item: {channel: 'edgar'|'rss', title, url, atMs, cik?, form?, exDay?, feed?}
 *  armed: the _watch_armed module (with the owner's live:control applied). Returns {ok, row, kind, term, why}. */
export function check(item, armed, posted, nowMs) {
  if (String(item.title || '').length > 300) return { ok: false, why: 'headline too long to read whole' };
  const k = headlineKind(item.title);
  if (!k.kind) return { ok: false, why: k.why };
  let rows;
  if (item.channel === 'edgar') rows = armed.rows.filter(r => r.cik && Number(r.cik) === Number(item.cik));
  else if (item.channel === 'rss') rows = armed.rows.filter(r => (r.feeds || []).includes(item.feed));
  // A newswire release alone is never posted: a forged release (GlobeNewswire, 2021) passes every check of the page
  // itself, because the forger writes the headline, the ticker and the dateline (red team 3).
  else return { ok: false, why: item.channel === 'wire' ? 'a newswire release alone is never posted' : 'unknown channel' };
  if (!rows.length) return { ok: false, why: 'source is not an armed sponsor\'s own' };
  const p = pickRow(item.title, k.kind, rows, armed.rows);
  if (!p.row) return { ok: false, why: p.why };
  const r = p.row;
  if (isRetracted(armed.retract, r.id)) return { ok: false, why: 'withdrawn by hand' };
  // First seen while posting was stopped: never posted on its own when posting resumes (red team 4).
  const has = k => !!k && plain(armed.stopped) && Object.prototype.hasOwnProperty.call(armed.stopped, k);
  if (has(item.url) || has(item.key))
    return { ok: false, why: 'first seen while posting was stopped; a person must release it' };
  const stopAt = Number(armed.stopAt);
  if (stopAt > 0 && !(Number.isFinite(item.atMs) && item.atMs > stopAt))
    return { ok: false, why: 'published while posting was stopped; a person must release it' };
  // A feed item is new only if it was not in the feed when the watch first read it, so an old release whose date
  // the feed re-stamps never posts (red team 4).
  if (item.channel === 'rss' && item.fresh !== true) return { ok: false, why: 'the feed item was already in the feed when the watch first read it' };
  if (item.channel === 'edgar' || item.channel === 'rss') {
    if (!item.exDay) return { ok: false, why: item.channel === 'edgar' ? 'the exhibit carries no dateline' : 'the release page carries no dateline' };
    const fd = Number.isFinite(item.atMs) ? Date.parse(etDay(item.atMs) + 'T12:00:00Z') : NaN;
    const xd = Date.parse(item.exDay + 'T12:00:00Z');
    if (!Number.isFinite(fd) || !Number.isFinite(xd) || Math.abs(fd - xd) > DAY) return { ok: false, why: `the source is dated ${item.exDay}, not the day it was published` };
  }
  if (item.channel === 'rss' && !onFeedSite(item))
    return { ok: false, why: 'the feed item links off the sponsor\'s own site' };
  const st = (armed.status || {})[r.id];
  if (st && String(st.st).toLowerCase() !== 'upcoming') return { ok: false, why: `the reviewed record already shows ${st.st}` };
  if (posted && posted[r.id]) return { ok: false, why: 'already posted' };
  // Posted once, ever (state.done): a post deleted from the store by hand is never posted again (red team 6).
  const done = k => !!k && plain(armed.done) && Object.prototype.hasOwnProperty.call(armed.done, k);
  if (done(r.id) || done(item.url) || done(item.key)) return { ok: false, why: 'already posted once' };
  if (posted && Object.values(posted).some(x => x && (x.source || {}).url === item.url)) return { ok: false, why: 'this source is already posted' };
  const tw = timeOk(item.atMs, nowMs, r.d);
  if (tw) return { ok: false, why: tw };
  return { ok: true, row: r, kind: k.kind, term: p.term, why: '' };
}

// ---------- the store (live:state, live:control) ----------

const plain = x => !!x && typeof x === 'object' && !Array.isArray(x);

/** live:state: no key reads as empty; a key that is not a JSON object reads as null (damaged), and the cron then
 *  stops without writing, so it never posts again what it posted before (red team 5). */
export function readState(v) {
  if (v === null || v === undefined) return {};
  try {
    const x = JSON.parse(v);
    if (!plain(x)) return null;
    // A hand-edited record is damaged, not empty: a post set to null or a list in place of a map would otherwise be
    // dropped and posted again (red team 6).
    for (const k of ['pub', 'seen', 'stopped', 'done', 'rss', 'beat']) if (x[k] !== undefined && !plain(x[k])) return null;
    if (x.pub && !Object.values(x.pub).every(plain)) return null;
    return x;
  } catch { return null; }
}

/** live:control. No key: {}. Anything but a plain object with only known keys of the right types reads as "stop":
 *  {"publish":"false"}, a bare false, "off", bad JSON, {"Publish":false}, {"retract":[...]} or {"retract":"id"}. */
export function readControl(c) {
  if (c === null || c === undefined) return {};
  try {
    const x = JSON.parse(c);
    const known = ['publish', 'retract', 'hide'];
    if (plain(x) && Object.keys(x).every(k => known.includes(k))
        && (x.publish === undefined || typeof x.publish === 'boolean')
        && (x.hide === undefined || typeof x.hide === 'boolean')
        && (x.retract === undefined || plain(x.retract))) return x;
  } catch {}
  return { publish: false, bad: true };          // "bad": /api/v1/live hides every post too
}

// ---------- time (RULE 1: every time carries its zone; display in Eastern) ----------

const ET = 'America/New_York';

/** UTC ms for a wall-clock time in Eastern ("2026-11-20 19:55:00" from FMP). */
export function etWallToMs(s) {
  const m = String(s || '').match(/^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})(?::(\d{2}))?$/);
  if (!m) return NaN;
  const [, y, mo, d, h, mi, se] = m.map(Number);
  const guess = Date.UTC(y, mo - 1, d, h, mi, se || 0);
  const fits = [5, 4].map(off => guess + off * 3600000)          // EST, EDT: the ones that read back as this wall time
    .filter(t => etParts(t).wall === `${m[1]}-${m[2]}-${m[3]} ${m[4]}:${m[5]}`);
  return fits.length === 1 ? fits[0] : NaN;                          // none (spring gap) or two (fall-back hour): unknown
}

export function etParts(ms) {
  const f = new Intl.DateTimeFormat('en-US', { timeZone: ET, year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23', timeZoneName: 'short' });
  const p = Object.fromEntries(f.formatToParts(new Date(ms)).map(x => [x.type, x.value]));
  return { wall: `${p.year}-${p.month}-${p.day} ${p.hour}:${p.minute}`, zone: p.timeZoneName, p };
}

/** ISO 8601 in Eastern with its offset: 2026-11-20T19:55:00-05:00 */
export function etIso(ms) {
  const { p, zone } = etParts(ms);
  const off = zone === 'EDT' ? '-04:00' : '-05:00';
  return `${p.year}-${p.month}-${p.day}T${p.hour}:${p.minute}:${p.second}${off}`;
}

/** "Nov 20, 2026, 7:55 PM ET" */
export function etLabel(ms) {
  return new Intl.DateTimeFormat('en-US', { timeZone: ET, month: 'short', day: 'numeric', year: 'numeric',
    hour: 'numeric', minute: '2-digit' }).format(new Date(ms)) + ' ET';
}

export function gapLabel(min) {
  if (min < 60) return `${min} min`;
  if (min < 2880) return `${Math.floor(min / 60)} h ${min % 60} min`;
  return `${Math.floor(min / 1440)} d ${Math.floor((min % 1440) / 60)} h`;
}

/** The posted sentence: the source's own headline, quoted and attributed. Nothing is restated in other words. */
export function sentence(item, row) {
  const c = shortCompany(row.company);
  const co = /s$/i.test(c) ? `${c}'` : `${c}'s`;
  const h = clean(item.title);
  if (item.channel === 'edgar') return `${co} SEC filing (${item.form || '8-K'}) says: "${h}"`;
  if (item.channel === 'rss') return `${co} news release says: "${h}"`;
  return `${co} release on ${WIRES[new URL(item.url).hostname]} says: "${h}"`;
}

export function sourceLabel(item) {
  if (item.channel === 'edgar') return `SEC EDGAR, ${item.form || '8-K'} accepted`;
  if (item.channel === 'rss') return 'sponsor news feed';
  return WIRES[new URL(item.url).hostname];
}

/** Does a feed item link to the feed's own site? Its host, or the host less a first label such as "investor."
 *  ("investor.bridgebio.com" -> "bridgebio.com"), https only. */
export function onFeedSite(item) {
  const host = u => { try { const x = new URL(u); return x.protocol === 'https:' ? x.hostname.toLowerCase() : ''; } catch { return ''; } };
  const fh = host(item.feed), ih = host(item.url);
  const labels = fh.split('.');
  const base = labels.length >= 3 && !/^(?:co|com|org|net|ac|gov|edu)$/.test(labels[labels.length - 2]) ? labels.slice(1).join('.') : fh;
  return !!fh && !!ih && (ih === fh || ih === base || ih === 'www.' + base);
}

/** A sponsor's own later release that contradicts or withdraws what a live post said (red teams 6, 7, 8). Returns the
 *  ids of live posts to withdraw: posts of a row of the same sponsor (same SEC filer, or a fresh item of the same feed
 *  on its own site), sourced before this item, when the item's headline:
 *    * names the opposite decision on the drug (a complete response letter after an approval post, an approval after a
 *      letter), or names it as a correction;
 *    * says it retracts a release, that a release was issued in error, false or fraudulent, or tells readers to
 *      disregard one (a post not yet confirmed by the review is withdrawn on this alone, within 7 days);
 *    * or corrects, clarifies or denies something and names the drug or a decision word with an earlier release.
 *  Routine news (a loan amended, guidance updated, a call time corrected) names no decision and no retraction, and a
 *  headline about another country's regulator is not about the US post. Any wording at all: the headline need not
 *  parse, because withdrawing is always safe; the full review then puts back what was true. */
const RETRACTS = /\b(?:retract\w*|withdr[ae]w\w* (?:(?:its|the|an?|this|that|earlier|previous|prior|today's)\s+)*(?:press |news )?(?:release|announcement|statement)|(?:issued|published|distributed|sent) (?:in error|erroneously|by mistake|without authori[sz]ation)|in error|(?:erroneous(?:ly)?|fraudulent|fake|false|unauthori[sz]ed|bogus|forged|spoofed) (?:issued |distributed |published )?(?:press |news )?(?:release|announcement|statement)s?|disregard\w*|correction to (?:\S+\s+){0,3}?(?:press |news )?release|(?:correct|amend|updat)(?:s|ed|es|ing|e)? (?:(?:its|the|an?|earlier|previous|previously issued|prior)\s+)*(?:press |news )?release)\b/i;
export const CORRECTS = /\b(?:retract\w*|withdr[ae]w\w*|correct(?:s|ed|ion|ions|ing)?|clarif\w*|erroneous\w*|in error|mistaken\w*|misstat\w*|inaccura\w*|disregard\w*|rescind\w*|supersed\w*|updat(?:e|es|ed|ing) (?:to )?(?:its |the |an? )?(?:previously issued|earlier|previous|prior) (?:press |news )?(?:release|announcement|statement)|(?:false|untrue|fake|unfounded|incorrect|fraudulent) (?:media )?(?:report|reports|rumou?rs?|claims?|statements?|release|press release)|has not (?:occurred|been (?:received|issued|approved|granted))|did not (?:occur|receive|approve)|not (?:yet )?(?:received|approved|issued)|no (?:fda )?(?:decision|approval|action) (?:has|was|yet))\b/i;
const DECISION_WORDS = /\b(?:FDA|approv(?!able)\w*|complete response|CRL|PDUFA)\b/i;
const EARLIER_WORDS = /\b(?:press release|news release|release|announcement|statement|report|earlier|previous|previously|prior)\b/i;
const CRL_WORDS = /\b(?:complete response|CRL|not approvable)\b/i;
const APPROVAL_WORDS = /\bFDA\b[^.;]*\bapprov(?:es|ed|al)\b(?!able)|\bapprov(?:es|ed|al)\b[^.;]*\bFDA\b/i;
const OTHER_REGULATOR = /\b(?:EMA|CHMP|MAA|European|EU|Europe|PMDA|Japan\w*|MHRA|UK|Health Canada|Canad\w*|NMPA|China|Chinese|TGA|Australia\w*|Swissmedic|Swiss|Switzerland|ANVISA|Brazil\w*|Korea\w*|MFDS|India\w*|CDSCO|Taiwan\w*|Israel\w*|Mexic\w*|COFEPRIS|Saudi|SFDA)\b/;
export function corrections(item, armed, pub) {
  const t = norm(clean(item.ctitle || item.title || ''));
  if (!t || !Number.isFinite(item.atMs)) return [];
  if (OTHER_REGULATOR.test(t) && !/\bFDA\b|\b(?:US|U\.S\.)\b/.test(t)) return [];
  let rows = [];
  if (item.channel === 'edgar') rows = armed.rows.filter(r => r.cik && Number(r.cik) === Number(item.cik));
  else if (item.channel === 'rss' && item.fresh === true && onFeedSite(item)) rows = armed.rows.filter(r => (r.feeds || []).includes(item.feed));
  if (!rows.length) return [];
  const retracts = RETRACTS.test(t), corrects = CORRECTS.test(t);
  const aboutDecision = DECISION_WORDS.test(t) && EARLIER_WORDS.test(t);
  return rows.filter(r => {
    const p = (pub || {})[r.id];
    if (!p || typeof p !== 'object' || (p.status !== 'posted' && p.status !== 'confirmed')) return false;
    const src = Date.parse((p.source || {}).published_at || '');
    if (!Number.isFinite(src) || item.atMs <= src || (p.source || {}).url === item.url) return false;
    const named = (r.terms || []).some(x => termIn(x, t));
    // the opposite decision, from the sponsor itself, on this drug; or, said as a correction, with no other drug named
    // (a large sponsor's decision on another drug of its own is not about this one)
    const others = armed.rows.filter(o => o.id !== r.id && (o.terms || []).some(x => termIn(x, t)));
    const opposite = p.kind === 'approval' ? CRL_WORDS.test(t) : APPROVAL_WORDS.test(t);
    if (opposite && (named || ((retracts || corrects) && !others.length))) return true;
    if (retracts && (named || (p.status === 'posted' && !others.length && item.atMs - src <= 7 * DAY))) return true;
    // a confirmed post (the review agreed) is withdrawn only by a release that names its drug
    return corrects && (named || (aboutDecision && p.status === 'posted' && !others.length));
  }).map(r => r.id);
}

/** Is a row withdrawn by hand? Any own key of a plain-object retract list counts, whatever its reason ("", false). */
export function isRetracted(retract, id) {
  return !!retract && typeof retract === 'object' && !Array.isArray(retract) && Object.prototype.hasOwnProperty.call(retract, id);
}

/** Self-heal: compare each post with the reviewed record. Returns the posts with status updated.
 *  Same outcome, same day (within 1.5 days): confirmed. Same outcome, another day: left as posted (the source said
 *  what it said; the reviewer sees both). Another outcome (even after a confirmation), a withdrawal, or a manual
 *  retraction: retracted. Not confirmed three days after the source (by the clock, so a stalled build cannot keep a
 *  post up): retracted. */
export function reconcile(pub, armed, nowMs) {
  const out = {};
  for (const [id, rec] of Object.entries(pub || {})) {
    if (!rec || typeof rec !== 'object') continue;
    const r = { ...rec };
    const m0 = isRetracted(armed.retract, id) ? armed.retract[id] : undefined;
    const man = m0 === undefined ? '' : (typeof m0 === 'string' && m0.trim() ? m0.trim() : 'Withdrawn by pdufa.bio.');
    const st = (armed.status || {})[id];
    const srcDay = Date.parse(String((r.source || {}).published_at || '').slice(0, 10) + 'T12:00:00Z');
    const late = !Number.isFinite(srcDay) || nowMs - srcDay >= 3 * DAY;
    const unconfirmed = () => Object.assign(r, { status: 'retracted', retracted_at: etIso(nowMs),
      retract_reason: 'The full review had not confirmed this three days after the source, so it was withdrawn.' });
    if (man && r.status !== 'retracted') {
      Object.assign(r, { status: 'retracted', retracted_at: etIso(nowMs), retract_reason: String(man) });
    } else if (r.status === 'posted' || r.status === 'confirmed') {
      const s = String((st || {}).st || '').toLowerCase(), oc = String((st || {}).oc || '').toLowerCase();
      // The record's outcome, read only when it is plain: a letter, or an approval of some kind; anything else waits.
      // The outcome is what the text opens with ("Approved (after CRL)" is an approval, red team 6).
      const o = oc.trim();
      // Both kinds of word ("Approved in part; CRL for ...") or "Approvable letter": unclear, so it waits (red team 7).
      const crlWord = /\bcrl\b|complete response|approvable/.test(o), apprWord = /\bapprov(?!able)/.test(o.replace(/not approvable/g, ''));
      const isCrl = !apprWord && /^(?:crl\b|complete response|not approvable)/.test(o);
      const isAppr = !crlWord && /^(?:approv|accelerated approv|full approv|conditional approv)/.test(o)
        && !/\b(?:not|un)\s*approv|withdraw|revok|rescind/.test(o);
      if (s === 'decided' && (isCrl || isAppr)) {
        const same = r.kind === 'approval' ? isAppr : isCrl;
        const dd = Date.parse(String(st.dcd || '') + 'T12:00:00Z');
        // The FDA often acts a few days before the sponsor says so (a Friday action, a Monday release), never after.
        const near = Number.isFinite(dd) && Number.isFinite(srcDay) && dd - srcDay <= 1.5 * DAY && srcDay - dd <= 7 * DAY;
        const page = /^\/[^/\\]/.test(String(st.url || '')) ? st.url : r.page;
        if (same && near) { if (r.status === 'posted') Object.assign(r, { status: 'confirmed', confirmed_at: etIso(nowMs), page }); }
        else if (same) { if (r.status === 'posted' && late) unconfirmed(); }
        else Object.assign(r, { status: 'retracted', retracted_at: etIso(nowMs),
          retract_reason: `The reviewed record says ${st.oc}, not ${r.kind === 'approval' ? 'an approval' : 'a complete response letter'}.` });
      } else if (s === 'withdrawn') {
        Object.assign(r, { status: 'retracted', retracted_at: etIso(nowMs), retract_reason: 'The reviewed record says the application was withdrawn.' });
      } else if (r.status === 'posted' && late) unconfirmed();
      // A confirmed post stays confirmed when the record is renamed, retired or reads as under review for a build:
      // only the opposite outcome, a withdrawal or a person retracts it (red team 5).
    }
    out[id] = r;
  }
  return out;
}

// ---------- 8-K / 6-K exhibits ----------

const MON = `(?:${['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'].map(ci).join('|')})[A-Za-z]*\\.?`;
const MONTHS = { jan: 1, feb: 2, mar: 3, apr: 4, may: 5, jun: 6, jul: 7, aug: 8, sep: 9, oct: 10, nov: 11, dec: 12 };
// The dateline opens the first paragraph: a city in capitals, then optional ", State" / ", the Netherlands", then the
// date, or Business Wire's "SAN DIEGO--(BUSINESS WIRE)--Dec. 1, 2026--". "SAN DIEGO, Dec. 1, 2026",
// "SOUTH SAN FRANCISCO, Calif., December 1, 2026 /PRNewswire/", "BOSTON and LONDON, Dec. 1, 2026",
// "LEIDEN, the Netherlands, Dec. 1, 2026".
const CITY = "[A-Z][A-Z.'&\\- ]{1,50}(?:\\s+(?:and|&)\\s+[A-Z][A-Z.'&\\- ]{1,40})?";
const DATELINE = new RegExp(`^${CITY}(?:,\\s*(?:the\\s+)?[A-Z][A-Za-z.'\\- ]{1,30}){0,2}(?:,\\s*|\\s*-{1,2}\\s*\\((?:BUSINESS WIRE|GLOBE NEWSWIRE|PRNewswire)\\)\\s*-{1,2}\\s*|\\s+)(${MON})\\s+(\\d{1,2}),\\s+(20\\d\\d)\\b`);
// A numeric date counts as a date too ("Originally issued 06/02/2026", "2026-06-02"): it is not a dateline.
const ANY_DATE = new RegExp(`\\b${MON}\\s+\\d{1,2},\\s+20\\d\\d\\b|\\b\\d{1,2}[/.-]\\d{1,2}[/.-](?:20)?\\d\\d\\b|\\b20\\d\\d-\\d{2}-\\d{2}\\b`);
// Text a reader never sees, or sees struck out, is never a headline: an exhibit that holds any is not read at all
// (red team 4: a struck-out release, a hidden block, an old headline kept in <title>, a commented-out heading).
const HIDDEN = /\bcontent\s*:\s*(?:"[^"]+"|'[^']+'|attr\b|url\b|counter)|display\s*:\s*none|visibility\s*:\s*hidden|font-size\s*:\s*0(?![.\d]*[1-9])|<\s*(?:del|s|strike)\b|text-decoration[^;"']*line-through|<[^>]*\shidden(?:\s|=|\/?>)/i;

// A picture's words void the exhibit when they could change what the headline says (Word's "Description
// automatically generated", a logo's name or a ticker do not; red team 7).
const ALT_BAD = /\b(?:FDA|approv\w*|CRL|complete response|letter|reject\w*|den(?:y|ied|ial)|declin\w*|delay\w*|extend\w*|postpon\w*|not|no|never|update\w*|notice|warning|important|draft|superseded|void|cancel\w*|errat\w*|obsolete|replac\w*|sample|specimen|archiv\w*|old|mock\w*|illustrat\w*|example|invalid|test|placeholder|watermark|copy|template|preliminary|hypothetical|proposed|pending|unofficial|internal)\b/i;
const FORMLIKE = /<\s*(?:input|textarea|select|option|button|object|embed|iframe|frame|svg|math|template|noscript|marquee)\b/i;

function rawBlocks(html) {
  // HTML5 comment ends: "<!-->" and "<!--->" are whole (empty) comments, and "--!>" closes one too (red team 6).
  const s = String(html || '').replace(/<!--(?:-?>|[\s\S]*?(?:--!?>|$))/g, ' ')
    .replace(/<head\b[\s\S]*?(?:<\/head>|$)/gi, ' ').replace(/<title\b[\s\S]*?(?:<\/title>|$)/gi, ' ')
    .replace(/<(script|style)[\s\S]*?(?:<\/\1>|$)/gi, ' ')
    .replace(/\s+/g, ' ')                                              // a source line break is not a block break
    .replace(/<br\b[^>]*>/gi, ' ')                                     // a headline broken over two lines stays whole
    .replace(/<\/?(?:p|div|tr|td|th|h\d|li|table|center|section|article|header|ul|ol|blockquote)\b[^>]*>/gi, '\n');
  return s.split(/\n+/).map(raw => ({ raw, text: clean(raw) })).filter(b => b.text);
}

function blocks(html) { return rawBlocks(html).map(b => b.text); }


const SKIP = [/^(?:EX-99\.\d+|Exhibit\s+99(?:\.\d+)?)$/i, /^FOR IMMEDIATE RELEASE$/i, /^(?:news|press)\s+release$/i,
  new RegExp(`^${MON}\\s+\\d{1,2},\\s+20\\d\\d$`)];

/** The exhibit's dateline: {index of its block, day 'YYYY-MM-DD'} or null. The first block that carries a date (a
 *  bare date line aside) must be the dateline itself: an exhibit that dates something else first ("Reissued December
 *  1, 2026", "Originally issued 06/02/2026") has no dateline we trust. */
function dateline(bs) {
  for (let i = 0; i < bs.length; i++) {
    if (!ANY_DATE.test(bs[i]) || SKIP[3].test(bs[i])) continue;
    const m = bs[i].match(DATELINE);
    if (!m) return null;
    const mo = MONTHS[m[1].slice(0, 3).toLowerCase()], d = Number(m[2]);
    if (!mo || d < 1 || d > 31) return null;
    return { i, day: `${m[3]}-${String(mo).padStart(2, '0')}-${String(d).padStart(2, '0')}` };
  }
  return null;
}

/** An 8-K / 6-K exhibit's own headline: EVERY block before the dateline paragraph, joined, less exact labels
 *  ("Exhibit 99.1", "FOR IMMEDIATE RELEASE", "Press Release", a bare date). So a "RETRACTION" or "CORRECTION"
 *  line above it, a second line under it, or a sub-heading all become part of what is checked, and the whole must
 *  still parse as one decision (red team 4). With no dateline, or hidden or struck-out text anywhere, there is no
 *  headline, and nothing posts: the body of a filing never stands in for its headline. */
export function exhibitHeadline(html, companies = []) {
  if (HIDDEN.test(String(html || ''))) return '';
  // Text a reader sees that is not text of the page (a form field's value, a picture's words, an embedded frame) is
  // never read, so an exhibit that holds any is not read at all (red team 6). A logo's alt text is allowed when its
  // words are the sponsor's own name, "logo" and the like, or a file name.
  if (FORMLIKE.test(String(html || ''))) return '';
  for (const m of String(html || '').matchAll(/<img\b[^>]*?\balt\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))/gi)) {
    const alt = norm(clean(m[1] ?? m[2] ?? m[3] ?? ''));
    if (ALT_BAD.test(alt) || NEG_RE.test(alt) || CORRECTS.test(alt)) return '';
  }
  const rb = rawBlocks(html);
  const dl = dateline(rb.map(b => b.text));
  if (!dl) return '';
  // A letterhead block that is only the sponsor's own name is a label too.
  const key = x => String(x).toLowerCase().replace(/[^a-z0-9]+/g, '');
  const names = new Set(companies.flatMap(c => [key(c), key(shortCompany(c))]).filter(Boolean));
  const head = rb.slice(0, dl.i).filter(b => !SKIP.some(re => re.test(b.text)) && !names.has(key(b.text)));
  // Invisible or combining marks (a struck-through or tagged headline) are judged on the raw text, before cleaning
  // removes them; a headline too long to read whole is never read in part (red team 5).
  if (head.some(b => hiddenMarks(b.raw))) return '';
  const h = head.map(b => b.text).join(' ');
  return h.length > 300 ? '' : h;
}

/** What a correction is read from: every block before the dateline, struck-out and hidden text included (a
 *  correction often strikes the old words through), at most 600 characters. Never used to post. */
export function correctionHeadline(html) {
  const rb = rawBlocks(html);
  const dl = dateline(rb.map(b => b.text));
  return rb.slice(0, dl ? dl.i : Math.min(rb.length, 4)).map(b => b.text).join(' ').slice(0, 600);
}

/** The exhibit's dateline day, 'YYYY-MM-DD', or ''. */
export function exhibitDate(html) {
  if (HIDDEN.test(String(html || ''))) return '';
  const dl = dateline(blocks(html));
  return dl ? dl.day : '';
}

/** A sponsor feed item's own page: the day of its dateline, when a block above the dateline is exactly the feed
 *  item's title (so a title the feed cut short or shifted onto another link never posts), else ''. Hidden page
 *  furniture (menus, cookie banners) is allowed here, because the headline read is the feed's, checked against it. */
export function pageDay(html, title) {
  const rb = rawBlocks(html);
  const dl = dateline(rb.map(b => b.text));
  const want = clean(title);
  if (!dl || !want) return '';
  return rb.slice(0, dl.i).some(b => b.text === want && !hiddenMarks(b.raw)) ? dl.day : '';
}

/** The dateline paragraph of a wire page: the 400 characters after its wire marker. */
export function wireLead(html) {
  const t = clean(html);
  const m = t.match(/\((?:GLOBE NEWSWIRE|BUSINESS WIRE)\)|\/PRNewswire\//);
  return m ? t.slice(m.index, m.index + 400) : '';
}

// ---------- feeds ----------

export function tag(xml, name) {
  const m = xml.match(new RegExp(`<${name}[^>]*>([\\s\\S]*?)</${name}>`, 'i'));
  return m ? m[1].replace(/^<!\[CDATA\[|\]\]>$/g, '').trim() : '';
}

/** RSS / Atom items: {title, url, atMs, body}. A pubDate without a zone gives NaN (never guessed). The first
 *  publication time is used ("updated" only when the feed gives nothing else). */
export function parseFeed(xml) {
  const out = [];
  for (const m of String(xml || '').matchAll(/<(item|entry)\b[\s\S]*?<\/\1>/gi)) {
    const it = m[0];
    const link = tag(it, 'link') || (it.match(/<link[^>]*href="([^"]+)"/i) || [])[1] || '';
    const when = (tag(it, 'pubDate') || tag(it, 'published') || tag(it, 'dc:date') || tag(it, 'updated')).trim();
    // A time to the minute with its zone; a bare date or an exact midnight is a date, not a time (never guessed).
    const zoned = /([+-]\d{2}:?\d{2}|GMT|UTC|Z|[ECMP][SD]T)\s*$/i.test(when) && /\d{1,2}:\d{2}/.test(when)
      && !/(?:^|[T\s])00:00(?::00(?:\.0+)?)?(?=\s*(?:[+-]\d|Z|GMT|UTC|[ECMP][SD]T|$))/i.test(when)
      && !/\b12:00(?::00)?\s*AM\b/i.test(when)
      // placeholder times a feed writes for a date alone: noon UTC exactly, a minute or so after midnight (red team 4)
      && !/(?:^|[T\s])12:00(?::00(?:\.0+)?)?\s*(?:Z|GMT|UTC|[+-]00:?00)\s*$/i.test(when)
      && !/(?:^|[T\s])00:0\d(?::\d\d(?:\.\d+)?)?(?=\s*(?:[+-]\d|Z|GMT|UTC|[ECMP][SD]T|$))/i.test(when);
    const rawTitle = tag(it, 'title');
    out.push({ title: hiddenMarks(rawTitle) || clean(rawTitle).length > 300 ? '' : clean(rawTitle), url: clean(link), atMs: zoned ? Date.parse(when) : NaN,
               body: clean(tag(it, 'description') || tag(it, 'summary') || tag(it, 'content')) });
  }
  return out;
}
