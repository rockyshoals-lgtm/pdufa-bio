import DATA from './dataset.mjs';
import crypto from 'node:crypto';
import { readFileSync } from 'node:fs';

/* Audit 2026-10-03 Tier 1.4: meta.as_of is the REQUEST date (it advanced every day while the
   build was stalled from 09-27 to 10-03, so a consumer could not tell the data was six days old).
   meta.data_built_at is when the dataset was last rebuilt, from the same build-info the site's
   freshness stamps read. */
let DATA_BUILT_AT = null;
try {
  const bi = JSON.parse(readFileSync(new URL('../_build-info.json', import.meta.url), 'utf8'));
  DATA_BUILT_AT = bi.data_built_at || bi.built || null;
} catch (e) { DATA_BUILT_AT = null; }
export { DATA_BUILT_AT };

/* ---------------- tiers ---------------- */
export const TIERS = {
  anonymous: { quota: 1000,    window: 'day',   burst: 10,  depth: false, history: false },
  free:      { quota: 10000,   window: 'month', burst: 30,  depth: false, history: false },
  pro:       { quota: 100000,  window: 'month', burst: 120, depth: true,  history: false },
  quant:     { quota: 2000000, window: 'month', burst: 600, depth: true,  history: true  },
};
const list = v => (process.env[v] || '').split(',').map(s => s.trim()).filter(Boolean);

export async function resolveTier(req) {
  const key = req.headers['x-api-key'] || (req.query && req.query.key) || null;
  if (!key) return { tier: 'anonymous', key: null };
  // env lists first (manual override / internal keys)
  if (list('API_KEYS_QUANT').includes(key)) return { tier: 'quant', key };
  if (list('API_KEYS_PRO').includes(key))   return { tier: 'pro',   key };
  if (list('API_KEYS_FREE').includes(key) || list('API_KEYS').includes(key)) return { tier: 'free', key };
  // then the paid store (Stripe-issued)
  const t = await tierFromStore(key);
  if (t) return { tier: t, key };
  return { tier: null, key };            // key supplied but unknown -> 401
}

/* ---------------- request-time status (audit 2026-10-03, Tier 1.5) ----------------
   Time-derived statuses were baked into dataset.mjs at build time. When the build stalled from
   09-27 to 10-03, AACR Pancreatic and ASTRO kept saying "In progress" after they ended and EASD
   and WMS said "Scheduled" while they ran. A status that is a pure function of today's date is
   computed per request from the Eastern calendar day (RULE 1), never read from the build. */
export function easternToday() {
  return new Date().toLocaleDateString('en-CA', { timeZone: 'America/New_York' });
}
export function liveStatus(e, today = easternToday()) {
  if (!e || !e.d) return null;
  const st = String(e.st || '');
  if (e.type === 'Conference') {
    const start = String(e.d).slice(0, 10), end = String((e._d && e._d.end) || e.d).slice(0, 10);
    if (!/^\d{4}-\d\d-\d\d$/.test(start)) return st || null;
    return end < today ? 'Ended' : (start <= today ? 'In progress' : 'Scheduled');
  }
  if (e.type === 'PDUFA' && st.toLowerCase() === 'upcoming' && e.dp === 'day'
      && String(e.d).slice(0, 10) < today) return 'Awaiting';
  /* Audit 2026-10-03 item 4.6 (the 13 -- now 103 -- forward readouts whose window has passed): a readout
     still marked Estimated/Guided after its whole window has ended is neither reported nor upcoming.
     It is served as "Window passed" (no result in our record), computed from the date, never baked.
     A month window ends with its month (`dm`); a coarser window's `d` is already its end. */
  if (e.type === 'Readout' && (st === 'Estimated' || st === 'Guided')) {
    /* Ruling 2026-10-03 (readout leads #52): what ClinicalTrials.gov itself states, recorded on the row
       by apply_readout_registry_signals.py; never an inferred outcome. A sponsor result (Reported) wins. */
    const reg = e._d && e._d.registry;
    if (reg) {
      const os_ = String(reg.overall_status || '');
      if (os_ === 'TERMINATED') return 'Terminated per registry';
      if (os_ === 'WITHDRAWN') return 'Withdrawn per registry';
      if (os_ === 'SUSPENDED') return 'Suspended per registry';
      if (os_ === 'COMPLETED' || (reg.primary_completion_type === 'ACTUAL'
          && String(reg.primary_completion || '9999').slice(0, 10) <= today)) return 'Completed per registry';
    }
    const ended = e.dp === 'month' ? (String(e.dm || e.d).slice(0, 7) < today.slice(0, 7))
                                   : (String(e.d).slice(0, 10) < today);
    if (ended) return 'Window passed';
  }
  return st || null;
}

/* ---------------- fields ---------------- */
const CORE = e => ({
  id: e.id, ticker: e.t, company: e.company || null,
  /* `date` IS A DAY OR IT IS NULL (2026-09-09, audit 09-09b item 3, approved by David).
     It used to carry a month MIDPOINT when date_precision was not 'day', with a comment here
     telling consumers not to read it as a day. 263 of 456 rows served "the 15th" and 62 more
     served the 30th/31st -- 71% of the public dataset carrying a day no sponsor ever gave, in
     the endpoint /developers advertises. A comment in our source is not a control on someone
     else's parser, and an AI summarising this feed reads 2026-06-15 and repeats it.
     A field that means two things means neither, so `date` now means one: an announced day.
     Month and quarter rows carry their real granularity in `date_month` and nothing else.
     BREAKING for consumers who sorted on `date`; sort on `date_month` then `date`. */
  date: (e.dp === 'day' ? (e.d || null) : null),
  date_precision: e.dp || null,
  /* Same rule one level coarser (2026-09-10). A YEAR-precision row carries a year-end sentinel
     in `d` (2027-12-31 for TYRA, 2026-12-31 for NVO denecimig), and deriving date_month from it
     published "2027-12" -- December asserted from a row whose sponsor said only "2027". The
     fallback is fine for month and quarter rows, where d's month IS the real month; it is a
     fabrication for year rows, so they get null and `date_precision: "year"` is the whole
     answer. */
  date_month: e.dm || (e.dp === 'year' ? null : (e.d ? String(e.d).slice(0, 7) : null)),
  name: e.name, type: e.type,
  therapeutic_area: e.ta || null, market_cap_tier: e.cap || null,
  status: e.st || null,
  url: String(e.url).startsWith('http') ? e.url : 'https://www.pdufa.bio' + e.url,
  updated_at: e.ua,
});
// Reconciled 2026-07-11: if a field is visible on a public page, it is FREE in the API.
// indication / nct_id / market_cap_usd / cash_runway_months / days_to_decision / cohort_* are all
// rendered on /pdufa/* — charging for them was leaky and dishonest. They are now Core.
// Pro sells what we do NOT publish as data: the per-event daily run-up series (/api/v1/runup),
// bulk export, .ics feeds, webhooks, and 100k/mo quota.
const CORE_EXTRA = ['nct_id','indication','market_cap_usd','cash_runway_months','days_to_decision',
  'cohort_move_median_pct','cohort_move_p25_pct','cohort_move_p75_pct','cohort_n','runup_summary',
  /* Audit 09-15 ORDER 4: the provenance the site stands on, in the feed. `source` names the
     filing ("Corcept 8-K 2026-07-29 (EX-99.1)"), `source_url` is the primary document, and
     `date_history` records every date a row has held and why it moved (an FDA extension, a
     registry estimate that slid, a day withdrawn as unsourced). A day-precision row with a null
     source_url is one we could not settle in a filing; the field says so instead of the row
     implying otherwise. 0 of 456 rows exposed any of this before today. */
  'source','source_url','date_history',
  /* Audit 09-20 ORDER 1: provenance of the DECISION date, not only of the goal date. A margin
     is the difference of two dates; decision_date_note says when the date held is the sponsor's
     announcement day rather than the FDA's action day, decision_date_unsourced is the flag the
     timing statistic and every renderer gate on, goal_unsourced is its mirror (09-18). */
  'decision_source','decision_source_url','decision_date_note','decision_date_unsourced','goal_unsourced',
  /* 2026-10-09 (audit P0, MRK I-DXd): status "Withdrawn" -- the sponsor withdrew the application
     before the FDA acted. No decision, no outcome; dated and sourced like one. */
  'withdrawn_date','withdrawn_source','withdrawn_source_url','withdrawn_quote',
  /* 09-20b: the FDA's own action date where its released letter states it (CRLs). */
  'fda_action_date',
  /* 2026-10-03: the registry's own status on a readout row (ruling for leads #52) and the basis of a
     hand-assigned therapeutic area (item 3.3), so a consumer can see why a status or tag is what it is. */
  'registry','ta_basis'];
const DEPTH_KEYS = [];

export function shape(e, tier) {
  const base = CORE(e);
  const d = e._d || {};
  for (const k of CORE_EXTRA) base[k] = (k in d) ? d[k] : null;   // free — it's on the public page
  /* 2026-10-09: a withdrawn or decided application has no decision ahead; an enrichment step
     re-stamped days_to_decision:1 on the withdrawn MRK row. A closed row never carries a countdown. */
  if (/^(withdrawn|decided)$/i.test(String(e.st || ''))) base.days_to_decision = null;
  /* Conference rows carry presenters in _d (sync_conferences_to_api.py). Observed live 2026-08-16:
     the dataset had 8 conferences with presenter entries and this whitelist silently dropped every
     one -- the API said "presenters: none" while /conferences printed them. Same 2026-07-11 rule
     applies: rendered on a public page -> free in the API. */
  if (e.type === 'Conference') {
    base.end_date = d.end || null;
    base.presenters = d.presenters || [];
    base.presenter_note = d.presenter_note || null;
  }
  /* days_to_decision is BAKED into dataset.mjs when that file is generated, and freezes there.
     On 2026-07-22 every record still carried the value computed on 07-11 — e.g. CORT (PDUFA
     2026-07-11, decided 2026-03-25) reported -108 when the true figure was -119. Consumers of the public API were
     being served an 11-day-stale countdown with no signal that it was stale.
     Recompute per request from the event date. Both sides normalised to UTC midnight so the
     difference is an exact whole-day count and cannot drift with the hour of the request.
     Partial dates ("2026-11") pad to the 1st; anything unparseable stays null. */
  if (base.date) {
    const p = String(base.date).split('-');
    const v = Date.UTC(+p[0], +(p[1] || 1) - 1, +(p[2] || 1));
    /* RULE 1 (2026-10-03): the day is the EASTERN calendar day, not UTC. From 20:00 ET (EDT)
       the UTC date is already tomorrow and the countdown read one day short. */
    const et = easternToday().split('-');
    const t0 = Date.UTC(+et[0], +et[1] - 1, +et[2]);
    base.days_to_decision = Number.isNaN(v) ? null : Math.round((v - t0) / 864e5);
  } else {
    /* No announced day, so no countdown. Counting to a month midpoint we invented would be
       the same fabrication one field over, and `date_month` already tells a consumer the
       granularity we actually have. */
    base.days_to_decision = null;
  }
  /* A Decided record must state its OUTCOME and be internally consistent. Decision capture flips
     status->Decided but leaves the PDUFA goal date in `date` and a stale positive days_to_decision
     (MNKD served as Decided, date 2026-07-26, days_to_decision +1, no outcome -- and /llms.txt sends
     AI crawlers straight here). Expose the real outcome + decision date; never report a countdown to
     the future for something already decided. And a PDUFA whose date has passed with no outcome yet
     is not "Upcoming" -- surface it as "Awaiting" (e.g. OTSKY centanafadine). */
  base.outcome = e.oc || null;              // "Approved" | "CRL" | "Withdrawn"
  base.decision_date = e.dcd || null;       // actual FDA action date (may differ from the goal date)
  if (base.status === 'Decided') {
    base.days_to_decision = null;
  } else if (String(base.status).toLowerCase() === 'upcoming'
             && base.days_to_decision != null && base.days_to_decision < 0) {
    base.status = 'Awaiting';
  }
  const live = liveStatus(e);
  if (live && base.status !== 'Decided') base.status = live;
  if (!(TIERS[tier] && TIERS[tier].depth)) {
    base._pro = 'Per-event run-up series, bulk export and .ics feeds are Pro: https://www.pdufa.bio/pricing';
  }
  return base;
}

/* ---------------- limiter (fail-open) ---------------- */
const KV_URL = process.env.KV_REST_API_URL || process.env.UPSTASH_REDIS_REST_URL;
const KV_TOK = process.env.KV_REST_API_TOKEN || process.env.UPSTASH_REDIS_REST_TOKEN;
const ENFORCE = process.env.API_ENFORCE === '1';   // Phase 1: observe-only by default

function idFor(req, key) {
  if (key) return 'k:' + crypto.createHash('sha256').update(key).digest('hex').slice(0, 24);
  const ip = (req.headers['x-forwarded-for'] || '').split(',')[0].trim() || 'noip';
  const ua = req.headers['user-agent'] || 'noua';
  return 'a:' + crypto.createHash('sha256').update(ip + ua).digest('hex').slice(0, 24);
}
async function kv(cmd) {
  const r = await fetch(KV_URL, {
    method: 'POST',
    headers: { Authorization: 'Bearer ' + KV_TOK, 'Content-Type': 'application/json' },
    body: JSON.stringify(cmd), signal: AbortSignal.timeout(1800),
  });
  if (!r.ok) throw new Error('kv ' + r.status);
  return (await r.json()).result;
}
const sha = s => crypto.createHash('sha256').update(s).digest('hex');

/** Paid keys live in KV (issued by the Stripe webhook). Env lists remain as a manual override. */
export async function tierFromStore(key) {
  if (!key || !KV_URL || !KV_TOK) return null;
  try {
    const raw = await kv(['GET', 'key:' + sha(key)]);
    if (!raw) return null;
    const rec = JSON.parse(raw);
    // canceled/unpaid subscriptions fall back to free — Depth re-locks automatically
    if (rec.status === 'canceled' || rec.status === 'unpaid') return 'free';
    return TIERS[rec.tier] ? rec.tier : 'free';
  } catch { return null; }
}
export async function meter(req, tier, key, cost) {
  const t = TIERS[tier];
  const win = t.window === 'day' ? 86400 : 2592000;
  const bucket = t.window === 'day'
    ? new Date().toISOString().slice(0, 10)
    : new Date().toISOString().slice(0, 7);
  const out = { limit: t.quota, remaining: t.quota, used: 0, state: 'ok', reset: 0, credits: 0, blocked: false };
  out.reset = Math.floor(Date.now() / 1000) + win;
  if (!KV_URL || !KV_TOK) { out.state = 'unmetered'; return out; }   // fail-open: no meter configured
  try {
    const k = `q:${idFor(req, key)}:${bucket}`;
    const used = await kv(['INCRBY', k, String(cost)]);
    await kv(['EXPIRE', k, String(win), 'NX']);
    out.used = Number(used) || 0;
    out.remaining = Math.max(0, t.quota - out.used);
    const credits = key ? (Number(await kv(['GET', 'credits:' + sha(key)]).catch(() => 0)) || 0) : 0;
    out.credits = credits;
    if (out.used > t.quota * 1.10 && credits <= 0) { out.state = 'exhausted'; out.blocked = ENFORCE; }
    else if (out.used > t.quota) out.state = 'grace';
    else if (out.used > t.quota * 0.8) out.state = 'warning';
  } catch (e) { out.state = 'unmetered'; }                            // fail-open on limiter outage
  return out;
}

/* ---------------- responses ---------------- */
export function head(res, { rid, tier, m, cost, etag }) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Headers', 'x-api-key,content-type,if-none-match');
  /* Audit 2026-09-07 C1 (P1): the first request of the auditor's run got a payload with
     as_of two days old and no SRRK row, 66 s before the same URL served the current one.
     The old policy (s-maxage 1800 / SWR 86400 / SIE 604800) let the edge hand out an answer
     up to 24.5 h old while it revalidated. For a site whose product is the date, a stale
     answer is a wrong answer. Now: 5 min fresh, at most 5 more minutes stale while the
     edge refetches, and an hour of stale-on-origin-error rather than a week (auditor 08:40:
     SIE <= 3600). Worst case a reader can now see is a 10-minute-old payload. */
  const CC = 's-maxage=300, stale-while-revalidate=300, stale-if-error=3600';
  res.setHeader('Cache-Control', CC);
  res.setHeader('CDN-Cache-Control', CC);            // survives Vercel's client-header rewrite
  res.setHeader('Vercel-CDN-Cache-Control', CC);     // edge keeps serving on origin failure
  res.setHeader('X-Request-Id', rid);
  res.setHeader('X-Api-Tier', tier || 'anonymous');
  if (m) {
    res.setHeader('X-RateLimit-Limit', String(m.limit));
    res.setHeader('X-RateLimit-Remaining', String(m.remaining));
    res.setHeader('X-RateLimit-Reset', String(m.reset));
    res.setHeader('X-Credits-Remaining', String(m.credits));
    res.setHeader('X-Quota-State', m.state);
  }
  if (cost) res.setHeader('X-Credits-Cost', String(cost));
  if (etag) res.setHeader('ETag', etag);
}
export function fail(res, status, code, message, extra = {}) {
  const rid = extra.request_id || 'req_' + crypto.randomUUID().slice(0, 18);
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('X-Request-Id', rid);
  res.status(status).json({ error: { code, message, docs: 'https://www.pdufa.bio/developers#errors', request_id: rid, ...extra } });
}
export function quota402(res, m, rid, data) {
  res.setHeader('Retry-After', '1800');
  res.setHeader('X-Quota-State', 'exhausted');
  res.setHeader('Link', '<https://www.pdufa.bio/pricing>; rel="payment"');
  res.status(402).json({
    error: {
      code: 'quota_exhausted',
      message: 'Monthly quota used. Add credits or upgrade to Pro to continue.',
      quota: { limit: m.limit, used: m.used, resets_at: new Date(m.reset * 1000).toISOString() },
      options: [
        { type: 'credits', label: 'Add 25,000 requests — $5', url: 'https://www.pdufa.bio/pricing/credits?pack=25k&ref=api_402' },
        { type: 'upgrade', label: 'Go Pro — $10/mo, 100k req + run-up data + webhooks', url: 'https://www.pdufa.bio/pricing?ref=api_402' },
      ],
      retry_after: 1800, request_id: rid,
    },
    meta: { served_from: 'stale_cache', as_of: new Date().toLocaleDateString('en-CA', { timeZone: 'America/New_York' }), data_built_at: DATA_BUILT_AT },
    data: data || [],
  });
}

const csv = rows => {
  if (!rows.length) return '';
  const cols = Object.keys(rows[0]).filter(c => !c.startsWith('_'));
  const esc = v => v == null ? '' : /[",\n]/.test(String(v)) ? '"' + String(v).replace(/"/g, '""') + '"' : String(v);
  return [cols.join(','), ...rows.map(r => cols.map(c => esc(typeof r[c] === 'object' ? JSON.stringify(r[c]) : r[c])).join(','))].join('\n');
};

/* ---------------- main serve ---------------- */
export async function serve(req, res, type) {
  const rid = 'req_' + crypto.randomUUID().slice(0, 18);
  const { tier, key } = await resolveTier(req);
  if (tier === null) return fail(res, 401, 'invalid_key', 'Unknown API key. Pass a valid x-api-key header, or omit it for anonymous access.', { request_id: rid });

  const q = req.query || {};
  const include = String(q.include || '').split(',').map(s => s.trim()).filter(Boolean);
  const cost = include.includes('runup') ? 5 : 1;

  const m = await meter(req, tier, key, cost);
  const etag = 'W/"' + crypto.createHash('sha1').update(JSON.stringify([type, q, tier, DATA.length])).digest('hex').slice(0, 20) + '"';
  head(res, { rid, tier, m, cost, etag });

  if (m.blocked) return quota402(res, m, rid, []);
  if (req.headers['if-none-match'] === etag) return res.status(304).end();

  const VALID = ['ticker','type','ta','status','from','to','limit','offset','include','format','key','id','q'];
  for (const k of Object.keys(q)) if (!VALID.includes(k))
    return fail(res, 400, 'invalid_param', `Unknown parameter "${k}". Valid: ${VALID.join(', ')}`, { field: k, request_id: rid });

  let rows = DATA.slice();
  if (type) rows = rows.filter(e => e.type === type);
  if (q.id) rows = rows.filter(e => e.id === q.id);
  if (q.ticker) { const set = String(q.ticker).toLowerCase().split(',').map(s=>s.trim()); rows = rows.filter(e => set.includes(String(e.t).toLowerCase())); }
  if (q.type)   rows = rows.filter(e => String(e.type).toLowerCase() === String(q.type).toLowerCase());
  if (q.ta)     rows = rows.filter(e => String(e.ta || '').toLowerCase() === String(q.ta).toLowerCase());
  if (q.status) { const td = easternToday(); rows = rows.filter(e => String(liveStatus(e, td) || '').toLowerCase() === String(q.status).toLowerCase()); }
  if (q.from)   rows = rows.filter(e => (e.d || '') >= q.from);
  if (q.to)     rows = rows.filter(e => (e.d || '') <= q.to);
  if (q.q)      { const s = String(q.q).toLowerCase(); rows = rows.filter(e => (e.t+' '+e.name+' '+(e.company||'')).toLowerCase().includes(s)); }

  const total = rows.length;
  const limit = Math.min(parseInt(q.limit) || 500, 1000), offset = parseInt(q.offset) || 0;
  rows.sort((a, b) => (a.d || '') < (b.d || '') ? -1 : 1);
  const data = rows.slice(offset, offset + limit).map(e => shape(e, tier));

  if (String(q.format).toLowerCase() === 'csv') {
    res.setHeader('Content-Type', 'text/csv; charset=utf-8');
    return res.status(200).send(csv(data));
  }
  res.setHeader('Content-Type', 'application/json');
  res.status(200).json({
    meta: {
      source: 'pdufa.bio', license: 'Attribution + link-back required. Facts and historical statistics only — not investment advice.',
      tier: tier, quota_state: m.state, total, limit, offset, returned: data.length,
      as_of: new Date().toLocaleDateString('en-CA', { timeZone: 'America/New_York' }), data_built_at: DATA_BUILT_AT, request_id: rid,
      ...(TIERS[tier].depth ? {} : { pro_features: ['runup_series','export','calendar.ics','webhooks'], upgrade: 'https://www.pdufa.bio/pricing?ref=api_meta' }),
    },
    data,
  });
}
export { DATA };
