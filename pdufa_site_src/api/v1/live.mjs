import { kvReady, kv } from '../_stripe.mjs';
import { readState, readControl, isRetracted } from '../_live_check.mjs';
import ARMED from '../_watch_armed.mjs';
import { READ_LUA } from '../_live_read.mjs';

/** Free, keyless. What the every-minute news watch (api/cron/news-watch.mjs) has posted: each FDA decision it read
 *  from a primary source and posted within the minute, with the source's time, the time it was posted (Eastern, with
 *  the offset; RULE 1), and its status:
 *    posted     read from the source by the automatic check; the full review of the page follows
 *    confirmed  the reviewed record shows the same outcome
 *    retracted  the reviewed record shows another outcome, or the post was withdrawn; the reason is given
 *  Also the watch's heartbeat (when it last ran and which sources it could read), so anyone can see it is alive.
 *  Served from the CDN for 15 seconds. Facts only. Guard: tests/test_live_watch.py. */
let memo = { at: 0, state: null };          // one store read per instance per 5 s, whatever the query string

export default async (req, res) => {
  res.setHeader('Content-Type', 'application/json');
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Cache-Control', 'public, max-age=0, s-maxage=15, stale-while-revalidate=15');
  if (!kvReady()) return res.status(503).json({ error: { code: 'store_unavailable', message: 'The live store is not configured.' } });
  let state = memo.state;
  if (!state || Date.now() - memo.at > 5000) {
    try {
      // GET, not MGET: a key of another type is an error here, so every post is hidden (red team 6).
      const [v, c] = await kv('EVAL', READ_LUA, '2', 'live:state', 'live:control');
      state = readState(v) || {};                 // a damaged store shows nothing
      // Shown unless live:control is absent, or a well-formed control whose "hide" is absent or false; anything else
      // (a typo, bad JSON, a malformed retract list) hides every post. A retract applies here at once, before the
      // watch's next minute; a retract key that names no post and no armed row (a typo) hides every post, so a
      // retraction that missed never leaves the post up (red team 6).
      const control = readControl(c);
      const pub = state.pub && typeof state.pub === 'object' && !Array.isArray(state.pub) ? state.pub : {};
      const ids = new Set([...ARMED.rows.map(r => r.id), ...Object.keys(pub)]);
      const rk = control.retract && typeof control.retract === 'object' ? Object.keys(control.retract) : [];
      const hideAll = control.bad || control.hide === true || rk.some(k => !ids.has(k));
      if (hideAll) state = { ...state, pub: {}, hidden: true };
      else if (rk.length) state = { ...state, pub: Object.fromEntries(Object.entries(pub).map(([id, p]) => {
        if (!isRetracted(control.retract, id) || !p || typeof p !== 'object' || p.status === 'retracted') return [id, p];
        const why = control.retract[id];
        // no time until the watch records it (a time here would move on every read, red team 7)
        return [id, { ...p, status: 'retracted', retracted_at: null,
          retract_reason: typeof why === 'string' && why.trim() ? why.trim() : 'Withdrawn by pdufa.bio.' }];
      })) };
      memo = { at: Date.now(), state };
    } catch {
      return res.status(503).json({ error: { code: 'store_unavailable', message: 'The live store could not be read.' } });
    }
  }
  const q = req.query || {};
  const plain = x => !!x && typeof x === 'object' && !Array.isArray(x);
  let posts = Object.values(plain(state.pub) ? state.pub : {}).filter(plain).sort((a, b) => (Date.parse(b.posted_at) || 0) - (Date.parse(a.posted_at) || 0));
  if (q.id) posts = posts.filter(p => p.id === String(q.id));
  if (q.ticker) { const t = String(q.ticker).toUpperCase(); posts = posts.filter(p => p.ticker === t); }
  const b = plain(state.beat) ? state.beat : {};
  return res.status(200).json({
    meta: {
      source: 'pdufa.bio', returned: posts.length,
      watch: { every: '1 minute', last_heartbeat: b.at || null, heartbeat_note: 'The watch runs every minute and records this heartbeat at least every 10 minutes.',
        posting: b.publish === true && !state.hidden, ...(state.hidden ? { posts_hidden: true } : {}), sources: { sec_edgar: b.edgar || null, sponsor_feeds: b.rss || null } },
      method: 'https://www.pdufa.bio/research/posting-speed',
      note: 'Each post states what its primary source says, attributed to the source. A post is made only when an automatic check of the source headline passes; everything else waits for a full review. Times are US Eastern with their UTC offset.',
    },
    data: posts.map(p => ({ id: p.id, ticker: p.ticker, kind: p.kind, text: p.text, status: p.status,
      source: p.source, posted_at: p.posted_at, minutes_after_source: p.minutes_after_source, page: p.page,
      ...(p.confirmed_at ? { confirmed_at: p.confirmed_at } : {}),
      ...(p.status === 'retracted' ? { retracted_at: p.retracted_at, retract_reason: p.retract_reason } : {}) })),
  });
};
