import SERIES from './runup_series.mjs';
import { resolveTier, meter, TIERS, head, fail, quota402 } from './_lib.mjs';
import crypto from 'node:crypto';

/** Pro and ULTRA (API tier `quant`). The per-event daily T-120 → T+5 price path — the one thing we
 *  do NOT publish as numbers anywhere on the site. This is the actual moat. */
export default async (req, res) => {
  const rid = 'req_' + crypto.randomUUID().slice(0, 18);
  const { tier, key } = await resolveTier(req);
  if (tier === null) return fail(res, 401, 'invalid_key', 'Unknown API key.', { request_id: rid });
  if (!TIERS[tier].depth) return fail(res, 403, 'tier_forbidden',
    'The per-event run-up series is a Pro feature. Core catalyst data (including cohort statistics) stays free.',
    { request_id: rid, _upgrade: 'https://www.pdufa.bio/pricing?ref=api_runup' });

  const q = req.query || {};
  const cost = 5;
  const m = await meter(req, tier, key, cost);
  head(res, { rid, tier, m, cost });
  if (m.blocked) return quota402(res, m, rid, []);

  const id = q.id, ticker = String(q.ticker || '').toUpperCase();
  let rows = [];
  if (id) { if (SERIES[id]) rows = [{ id, ...SERIES[id] }]; }
  else if (ticker) rows = Object.entries(SERIES).filter(([, v]) => v.t === ticker).map(([k, v]) => ({ id: k, ...v }));
  else return fail(res, 400, 'invalid_param', 'Pass id=<event_id> or ticker=<TICKER>.', { request_id: rid });

  if (!rows.length) return fail(res, 404, 'not_found', 'No run-up series for that event.', { request_id: rid });
  if (String(q.format || 'json').toLowerCase() === 'csv') {
    // one row per event per trading day: offset from the decision (0), close indexed to 100 at T-120
    const lines = ['id,ticker,decision_date,base_close,offset,index'];
    for (const r of rows) for (const [o, v] of Object.entries(r.idx || {}).sort((a, b) => +a[0] - +b[0]))
      lines.push([r.id, r.t, r.d, r.base, o, v].join(','));
    res.setHeader('Content-Type', 'text/csv; charset=utf-8');
    res.setHeader('Content-Disposition', 'attachment; filename="pdufa-bio-runup-' + (id || ticker) + '.csv"');
    return res.status(200).send(lines.join('\n'));
  }
  res.setHeader('Content-Type', 'application/json');
  res.status(200).json({
    meta: { source: 'pdufa.bio', tier, returned: rows.length,
      offsets: 'trading days relative to the FDA decision (T-0). Values indexed to 100 at T-120.',
      note: 'Historical price action. Not investment advice.', request_id: rid },
    data: rows,
  });
};
