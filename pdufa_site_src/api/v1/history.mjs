import ROWS, { META } from './history_data.mjs';
import SERIES from './runup_series.mjs';
import { resolveTier, meter, TIERS, head, fail, quota402 } from './_lib.mjs';
import crypto from 'node:crypto';

/** ULTRA only (the API's `quant` tier, 2026-11-26). The whole run-up study in one feed: every FDA decision
 *  the site's statistics are computed from (2020 to today), with its outcome, the study's measured windows
 *  before and after the decision, and the daily T-120 -> T+5 indexed price path where we have one.
 *  Built by build_history_api.py from allow-listed study columns only; tests/test_history_api.py guards it.
 *  Historical facts, not investment advice. */
const OFFSETS = Array.from({ length: 126 }, (_, i) => String(i - 120));      // "-120" .. "5"
const col = o => (o === '0' ? 'idx_t0' : (o.startsWith('-') ? 'idx_t' + o : 'idx_t+' + o));
const CAPS = { large: 'Large', mid: 'Mid', small: 'Small', micro: 'Micro', nano: 'Nano' };

export default async (req, res) => {
  const rid = 'req_' + crypto.randomUUID().slice(0, 18);
  const { tier, key } = await resolveTier(req);
  if (tier === null) return fail(res, 401, 'invalid_key', 'Unknown API key.', { request_id: rid });
  if (!TIERS[tier].history) return fail(res, 403, 'tier_forbidden',
    'The full run-up study history is an ULTRA feature. Pro includes the per-event series (/api/v1/runup); core catalyst data stays free.',
    { request_id: rid, _upgrade: 'https://www.pdufa.bio/pricing?ref=api_history' });

  const q = req.query || {};
  const cost = 100;
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
  if (q.from) {
    if (!/^\d{4}-\d\d-\d\d$/.test(String(q.from))) return bad('from must be YYYY-MM-DD.');
    rows = rows.filter(r => (r.decision_date || '') >= String(q.from));
  }
  if (q.to) {
    if (!/^\d{4}-\d\d-\d\d$/.test(String(q.to))) return bad('to must be YYYY-MM-DD.');
    rows = rows.filter(r => (r.decision_date || '') <= String(q.to));
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
  if (q.area) { const a = String(q.area).toLowerCase(); rows = rows.filter(r => String(r.therapeutic_area || '').toLowerCase().includes(a)); }

  // The daily path roughly triples a row's size; pages stay well under the response limit.
  const withSeries = String(q.series ?? '1') !== '0';
  const maxLimit = withSeries ? 500 : 2000;
  const limit = Math.min(Math.max(parseInt(q.limit) || maxLimit, 1), maxLimit);
  const offset = Math.max(parseInt(q.offset) || 0, 0);
  const total = rows.length;
  const page = rows.slice(offset, offset + limit).map(r => {
    const s = r.series_id ? SERIES[r.series_id] : null;
    return withSeries ? { ...r, series_base_close: s ? s.base : null, series: s ? s.idx : null } : { ...r };
  });

  const fmt = String(q.format || 'json').toLowerCase();
  if (fmt === 'csv') {
    const cols = [...META.fields, ...(withSeries ? ['series_base_close', ...OFFSETS.map(col)] : [])];
    const esc = v => v == null ? '' : /[",\n]/.test(String(v)) ? '"' + String(v).replace(/"/g, '""') + '"' : String(v);
    const lines = [cols.join(',')];
    for (const r of page) {
      const flat = { ...r };
      if (withSeries) for (const o of OFFSETS) flat[col(o)] = r.series ? r.series[o] : null;
      lines.push(cols.map(c => esc(flat[c])).join(','));
    }
    res.setHeader('Content-Type', 'text/csv; charset=utf-8');
    res.setHeader('Content-Disposition', 'attachment; filename="pdufa-bio-runup-history.csv"');
    return res.status(200).send(lines.join('\n'));
  }
  res.setHeader('Content-Type', 'application/json');
  res.status(200).json({
    meta: {
      source: 'pdufa.bio', tier, request_id: rid, total, limit, offset, returned: page.length,
      study: { decisions: META.rows, approvals: META.approvals, crls: META.crls, with_daily_path: META.with_series,
               date_min: META.date_min, date_max: META.date_max },
      conventions: {
        eve: 'last trading session strictly before the decision date; eve_close is the study\u2019s stored close for it (provider-adjusted, so it can differ from the price printed that day)',
        runup_Nd_pct: 'percent change from the close N sessions before eve to the eve close',
        post_Nd_pct: 'percent change from the eve close to the close N sessions after',
        pre_tA_tB_pct: 'percent change from A sessions before eve to B sessions before eve',
        pre_t120_peak_pct: 'percent from the close 120 sessions before eve to the highest close before eve',
        volume_ratio: 'decision-day volume divided by mean volume over the 30 sessions before eve',
        series: 'daily close indexed to 100 at T-120; keys are trading days relative to the decision (0)',
      },
      note: 'Historical price action and FDA outcomes. Facts only, not investment advice.',
    },
    data: page,
  });
};
