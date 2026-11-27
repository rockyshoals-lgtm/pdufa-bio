import ROWS from './post_speed_data.mjs';
import { resolveTier, meter, head, fail, quota402 } from './_lib.mjs';
import crypto from 'node:crypto';

/** Free, keyless. How long after its primary source pdufa.bio published each FDA decision or goal-date change.
 *  One row per event that has BOTH a verified source time (the earliest public SEC filing, wire release or FDA
 *  notice we could time to the minute) and a verified site time (the first public commit to main that carried
 *  the fact). Built by build_post_speed.py from _source_times.json; tests/test_post_speed.py guards it.
 *  Times carry their UTC offset (RULE 1). minutes_after_source is floored to whole minutes. Facts only. */
export default async (req, res) => {
  const rid = 'req_' + crypto.randomUUID().slice(0, 18);
  const { tier, key } = await resolveTier(req);
  if (tier === null) return fail(res, 401, 'invalid_key', 'Unknown API key. Pass a valid x-api-key header, or omit it for anonymous access.', { request_id: rid });
  const cost = 1;
  const m = await meter(req, tier, key, cost);
  head(res, { rid, tier, m, cost });
  if (m.blocked) return quota402(res, m, rid, []);

  const q = req.query || {};
  let rows = ROWS;
  if (q.ticker) { const t = String(q.ticker).toUpperCase(); rows = rows.filter(r => r.ticker === t); }
  if (q.kind) {
    const k = String(q.kind).toLowerCase();
    if (k !== 'decision' && k !== 'date_change') return fail(res, 400, 'invalid_param', 'kind must be decision or date_change.', { request_id: rid });
    rows = rows.filter(r => r.kind === k);
  }
  const mins = rows.map(r => r.minutes_after_source).sort((a, b) => a - b);
  const median = mins.length ? (mins.length % 2 ? mins[(mins.length - 1) / 2] : Math.floor((mins[mins.length / 2 - 1] + mins[mins.length / 2]) / 2)) : null;
  res.setHeader('Content-Type', 'application/json');
  res.status(200).json({
    meta: {
      source: 'pdufa.bio', tier: tier || 'anonymous', request_id: rid, returned: rows.length,
      median_minutes_after_source: median,
      method: 'https://www.pdufa.bio/research/posting-speed',
      conventions: {
        source_published_at: 'earliest verified public time of the primary source (SEC acceptance, wire release or FDA feed), with its UTC offset',
        site_published_at: 'commit time of the first public commit to main that carried the fact; the live site updates a few minutes after it deploys',
        minutes_after_source: 'site_published_at minus source_published_at, floored to whole minutes',
      },
      note: 'Measured times only. Events whose source we could not time, or that were disclosed earlier somewhere we could not time, are left out.',
    },
    data: rows,
  });
};
