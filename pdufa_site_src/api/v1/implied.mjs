import ROWS, { META } from './implied_data.mjs';
import { resolveTier, meter, TIERS, head, fail, quota402 } from './_lib.mjs';
import crypto from 'node:crypto';

/** ULTRA only (the API's `quant` tier, 2026-11-26). What the options market priced before each FDA decision, beside
 *  what the stock did. Built by build_history_api.py from implied_moves.json, kept only for decisions still in the
 *  curated run-up study, with the study's own outcome and after-decision moves; tests/test_history_api.py guards it.
 *  The two caveats ship with the data (build_implied_moves.py): a straddle two weeks out prices two weeks of ordinary
 *  movement plus the event, and these are measurements of history. Not investment advice. */
const CAPS = { large: 'Large', mid: 'Mid', small: 'Small', micro: 'Micro', nano: 'Nano' };

export default async (req, res) => {
  const rid = 'req_' + crypto.randomUUID().slice(0, 18);
  const { tier, key } = await resolveTier(req);
  if (tier === null) return fail(res, 401, 'invalid_key', 'Unknown API key.', { request_id: rid });
  if (!TIERS[tier].history) return fail(res, 403, 'tier_forbidden',
    'Options-priced vs actual moves per decision is an ULTRA feature. The study-wide figures are free at /research/implied-vs-actual.',
    { request_id: rid, _upgrade: 'https://www.pdufa.bio/pricing?ref=api_implied' });

  const q = req.query || {};
  const cost = 50;
  const m = await meter(req, tier, key, cost);
  head(res, { rid, tier, m, cost });
  if (m.blocked) return quota402(res, m, rid, []);

  const bad = msg => fail(res, 400, 'invalid_param', msg, { request_id: rid });
  let rows = ROWS;
  if (q.ticker) { const t = String(q.ticker).toUpperCase(); rows = rows.filter(r => r.ticker === t); }
  if (q.year) {
    if (!/^\d{4}$/.test(String(q.year))) return bad('year must be a four-digit year.');
    rows = rows.filter(r => String(r.decision_date || '').startsWith(String(q.year)));
  }
  if (q.outcome) {
    const o = String(q.outcome).toLowerCase();
    if (o !== 'approval' && o !== 'crl') return bad('outcome must be approval or crl.');
    rows = rows.filter(r => r.outcome === o);
  }
  if (q.cap) {
    const c = CAPS[String(q.cap).toLowerCase()];
    if (!c) return bad('cap must be one of large, mid, small, micro, nano.');
    rows = rows.filter(r => String(r.market_cap_tier || '').startsWith(c));
  }

  if (String(q.format || 'json').toLowerCase() === 'csv') {
    const cols = META.fields;
    const esc = v => v == null ? '' : /[",\n]/.test(String(v)) ? '"' + String(v).replace(/"/g, '""') + '"' : String(v);
    res.setHeader('Content-Type', 'text/csv; charset=utf-8');
    res.setHeader('Content-Disposition', 'attachment; filename="pdufa-bio-options-priced-vs-actual.csv"');
    return res.status(200).send([cols.join(','), ...rows.map(r => cols.map(c => esc(r[c])).join(','))].join('\n'));
  }
  res.setHeader('Content-Type', 'application/json');
  res.status(200).json({
    meta: {
      source: 'pdufa.bio', tier, request_id: rid, total: rows.length, returned: rows.length,
      coverage: { decisions: META.rows, date_min: META.date_min, date_max: META.date_max, computed_as_of: META.computed_as_of },
      conventions: {
        snapshot_date: 'the options chain snapshot closest to 14 days before the decision (accepted in the 30 days before it)',
        days_before: 'calendar days from the snapshot to the decision date',
        expiry: 'the first listed expiry after the decision date',
        priced_move_pct: 'at-the-money straddle (call mid + put mid at the strike nearest spot) divided by spot',
        post_Nd_pct: 'the run-up study’s own move from the eve close to the close N sessions after the decision',
        exceeded_Nd: 'true when the absolute post move is larger than the priced move',
      },
      caveats: [
        'A straddle two weeks out prices two weeks of ordinary movement plus the event. priced_move_pct is the move priced from the snapshot through the first expiry after the decision, not an event-only implied move.',
        'These are measurements of history. They are not a property of future decisions, not a strategy, and not investment advice.',
      ],
    },
    data: rows,
  });
};
