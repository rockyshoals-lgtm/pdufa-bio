// /build-info.json -- served at REQUEST time, not build time.
//
// Audit 2026-09-20 P0-C: the static file was generated at ~00:26 UTC (20:26 Eastern) with
// next_days computed for that moment, then served unchanged for ~24 hours. From the Eastern
// midnight onward it read one day high -- for about twenty hours out of every twenty-four.
// The build still writes the file (api/_build-info.json, not a function because of the
// underscore); this recomputes every date-relative field from the Eastern calendar date of
// the request. vercel.json rewrites /build-info.json here; the static copy is not deployed.
import { readFileSync } from 'node:fs';

function easternToday() {
  // en-CA gives YYYY-MM-DD; America/New_York handles EDT/EST.
  return new Date().toLocaleDateString('en-CA', { timeZone: 'America/New_York' });
}
function dayDiff(a, b) {            // whole days from ISO date a to ISO date b
  const [ay, am, ad] = a.split('-').map(Number), [by, bm, bd] = b.split('-').map(Number);
  return Math.round((Date.UTC(by, bm - 1, bd) - Date.UTC(ay, am - 1, ad)) / 86400000);
}
function secondsToEasternMidnight() {
  const now = new Date();
  const et = new Date(now.toLocaleString('en-US', { timeZone: 'America/New_York' }));
  const s = (24 * 3600) - (et.getHours() * 3600 + et.getMinutes() * 60 + et.getSeconds());
  return Math.max(1, Math.min(s, 600));
}

let base = null;
try {
  base = JSON.parse(readFileSync(new URL('./_build-info.json', import.meta.url), 'utf8'));
} catch (e) {
  base = null;
}

export default function handler(req, res) {
  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  res.setHeader('Access-Control-Allow-Origin', '*');
  if (!base) {
    res.statusCode = 503;
    res.end(JSON.stringify({ error: 'build-info unavailable' }));
    return;
  }
  const today = easternToday();
  const out = { ...base, as_of_eastern: today, served_at: new Date().toISOString() };
  if (base.next_date) {
    const n = dayDiff(today, base.next_date);
    const awaiting = n < 0;
    out.next_status = awaiting ? 'awaiting' : 'upcoming';
    out.next_days = awaiting ? null : n;
    out.days_since_goal = awaiting ? -n : null;
  }
  // Cache at the edge only until the Eastern date changes (capped at 10 minutes).
  res.setHeader('Cache-Control', `public, max-age=0, s-maxage=${secondsToEasternMidnight()}`);
  res.statusCode = 200;
  res.end(JSON.stringify(out, null, 1));
}
