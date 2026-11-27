import ARMED from '../_watch_armed.mjs';
import { kvReady, kv } from '../_stripe.mjs';
import { READ_LUA, WRITE_LUA } from '../_live_read.mjs';
import { check, etIso, sentence, sourceLabel, reconcile, corrections, correctionHeadline, itemText, parseFeed, exhibitHeadline, exhibitDate, headlineKind, pageDay,
  readState, readControl, compareSource, sourcePrint, RECHECK_AT }
  from '../_live_check.mjs';

/** The every-minute news watch (vercel.json cron "* * * * *"). David, 2026-11-27: "Ensure its down to minutes".
 *
 *  Each run reads, in parallel, with an overall deadline well inside the function's limit:
 *    * SEC EDGAR's live list of 8-K and 6-K filings (only when SEC_USER_AGENT is set: the SEC requires a contact in
 *      the User-Agent, and the site owner chooses it), then, once per filing, the press-release exhibit of a filing
 *      by an armed sponsor (its own first heading, before the dateline, is what is checked);
 *    * the armed sponsors' own news feeds (_sponsor_feeds.json, RSS only). A feed's first read is a baseline that never
      posts; a later item's own page is read for its dateline.
 *  A newswire release alone is never posted (red team 3): a forged release passes every check of the page itself.
 *  Each item goes through _live_check.mjs. An item that passes is posted at once: it is written to the store and
 *  shows on the drug's page and at /api/v1/live within the minute, with the source's time and the time it was
 *  posted (RULE 1: Eastern, with the zone). An item that fails is not posted; the GitHub news watch still raises its
 *  HELD lead for review, as before.
 *
 *  Self-heal, every run: a post is marked confirmed when the reviewed record (dataset.mjs at the last deploy) shows
 *  the same outcome on the same day, and RETRACTED, in public with the reason, when it shows another outcome, when
 *  the application was withdrawn, when the review still has no decision three days after the source, or when
 *  _fast_lane.json or live:control lists it, or when the review has not confirmed it three days after the source.
 *  "publish": false in _fast_lane.json stops all posting (kill switch); so does live:control in the store, without a
 *  deploy (see readControl). What would have posted while posting was stopped is kept in state.stopped and never
 *  posts on its own when posting resumes.
 *
 *  Only Vercel's cron may call this: it sends "Authorization: Bearer CRON_SECRET". With CRON_SECRET unset nothing
 *  runs. One run at a time (live:lock, SET NX EX 50). Store: live:state and live:control, read once per run and written only when a
 *  post or the filing cache changes, or every 10 minutes (the heartbeat). Guard: tests/test_live_watch.py. */

const EDGAR_CURRENT = t => `https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=${t}&company=&dateb=&owner=include&start=0&count=100&output=atom`;
const UA_SITE = 'Mozilla/5.0 (compatible; pdufa.bio news watch; +https://www.pdufa.bio/about)';
const DEADLINE_MS = 35000;          // stop reading sources here; maxDuration is 55 s
const SEEN_MAX = 300;

async function get(url, { ua = UA_SITE, ms = 6000, limit = 1500000, until = Infinity, finalUrl = false } = {}) {
  const left = until - Date.now();
  if (left < 500) return null;
  const ac = new AbortController();
  const timer = setTimeout(() => ac.abort(), Math.min(ms, left));
  try {
    const r = await fetch(url, { headers: { 'User-Agent': ua, Accept: '*/*' }, signal: ac.signal, redirect: 'follow' });
    if (!r.ok) return null;
    const txt = (await r.text()).slice(0, limit);
    return finalUrl ? { txt, url: r.url || url } : txt;
  } catch { return null; } finally { clearTimeout(timer); }
}

/** A read that keeps the status: {status, txt, url}, or null when nothing came back (a timeout, a network error). */
async function getStatus(url, { ua = UA_SITE, ms = 6000, limit = 1500000, until = Infinity, manual = false } = {}) {
  const left = until - Date.now();
  if (left < 500) return null;
  const ac = new AbortController();
  const timer = setTimeout(() => ac.abort(), Math.min(ms, left));
  try {
    // The SEC's contact line never follows a redirect (red team 14): a moved SEC file is answered as moved.
    const r = await fetch(url, { headers: { 'User-Agent': ua, Accept: '*/*' }, signal: ac.signal, redirect: manual ? 'manual' : 'follow' });
    if (!r.ok) { try { await r.body?.cancel(); } catch {} }
    return { status: r.status, txt: r.ok ? (await r.text()).slice(0, limit) : '', url: r.url || url };
  } catch { return null; } finally { clearTimeout(timer); }
}

/** The right-after check (David, 2026-11-27, "Right after"): each post's source is read again about a minute after it
 *  posts, then 30 minutes and 3 hours after. The post is paused (hidden until the full review confirms it) when the
 *  source is gone or moved, now carries a notice of a correction or hidden text it did not carry when it posted, or its
 *  headline or opening changed and no longer says what the post says (red team 15: never for words it already held).
 *  A sponsor's page that cannot be read as the release is paused after four minutes of tries on the first re-read and
 *  ten on a later one. An SEC file never changes once filed, so its being unreadable (the SEC's rate limit, a slow
 *  minute) never pauses a post: after ten tries that re-read is skipped. At most two SEC files and six posts in all are
 *  read per run. */
async function recheckPosts(pub, ua, until, nowMs) {
  const out = {};                                               // id -> fields to set, applied only to a post still up
  const pause = (id, why) => { out[id] = { status: 'paused', paused_at: etIso(nowMs),
    paused_reason: `the right-after check of the source failed: ${why}` }; };
  let sec = 0;
  const due = Object.entries(pub).filter(([, p]) => p && p.status === 'posted' && Number.isFinite(Number(p.run_ms))
    && (Number(p.checks) || 0) < RECHECK_AT.length && nowMs - Number(p.run_ms) >= RECHECK_AT[Number(p.checks) || 0])
    .filter(([, p]) => (p.source || {}).channel !== 'edgar' || ++sec <= 2).slice(0, 6);
  await Promise.all(due.map(async ([id, p]) => {
    try {
      const n = Number(p.checks) || 0, src = p.source || {};
      const row = ARMED.rows.find(r => r.id === id);
      const host = u => { try { return new URL(u).hostname.toLowerCase(); } catch { return ''; } };
      const edgar = src.channel === 'edgar';
      const fail = why => {
        const tries = (Number(p.tries) || 0) + 1, first = Number(p.first_try) > 0 ? Number(p.first_try) : nowMs;
        if (!edgar && n === 0 && nowMs - first >= 4 * 60000) return pause(id, why);
        if (!edgar && n > 0 && tries >= 10) return pause(id, why);
        if (edgar && tries >= 10) { out[id] = { checks: n + 1, tries: 0, first_try: 0 }; return; }
        out[id] = { tries, first_try: first };
      };
      if (!row) return pause(id, 'the drug is no longer on the list this check reads');
      if (!/^https:\/\//i.test(String(src.url || '')) || (edgar && host(src.url) !== 'www.sec.gov'))
        return pause(id, 'the post has no source this check can read');
      if (edgar && !ua) return fail('the SEC is not read without its contact line');
      const got = await getStatus(src.url, { ua: edgar ? ua : UA_SITE, until, manual: edgar });
      if (!got) return fail('the source could not be read again');
      if (got.status === 404 || got.status === 410) return pause(id, 'the source is no longer at its address');
      if (edgar && got.status >= 300 && got.status < 400) return pause(id, 'the SEC now sends readers to another address');
      if (got.status < 200 || got.status >= 300) return fail(`the source answered ${got.status}`);
      if (host(got.url) !== host(src.url) || !/^https:/i.test(got.url)) return pause(id, 'the source now sends readers to another site');
      const cos = [row.company, ...(row.aliases || [])].filter(Boolean);
      const r = compareSource(got.txt, p, row, edgar ? ARMED.rows.filter(x => x.cik && Number(x.cik) === Number(row.cik)).flatMap(x => [x.company, ...(x.aliases || [])]) : cos);
      if (r.unread) return fail('the source no longer reads as the release');
      if (!r.ok) return pause(id, r.why);
      out[id] = { checks: n + 1, tries: 0, first_try: 0, rechecked_at: etIso(nowMs), ...(r.print ? { source_print: r.print } : {}) };
    } catch { /* one post's re-read never stops the run; it is tried again next minute */ }
  }));
  return out;
}

/** EDGAR: the exhibit of each new filing by an armed sponsor is read ONCE and remembered in state.seen. */
async function edgarItems(ua, beat, seen, until, listed, nowMs) {
  const ciks = new Set(ARMED.rows.filter(r => r.cik).map(r => Number(r.cik)));
  const fresh = [];
  let read = 0;
  const lists = await Promise.all(['8-K', '6-K'].map(async form => ({ form, xml: await get(EDGAR_CURRENT(form), { ua, until }) })));
  for (const { xml } of lists) {
    if (!xml) continue;
    read++;
    for (const e of parseFeed(xml)) {
      const m = e.title.match(/^(\S+) - .*\((\d{10})\)/);
      if (!m || !ciks.has(Number(m[2]))) continue;
      const acc = (e.url.match(/(\d{10}-\d{2}-\d{6})/) || [])[1];
      if (acc) listed.push(`edgar|${acc}`);
      // a filing is read until it reads (5 tries at most, so unreadable ones never crowd out new ones, red team 11)
      const was = seen[`edgar|${acc}`];
      if (!acc || (was && (!plain(was) || typeof was.title === 'string' || Number(was.tries) >= 5))) continue;
      fresh.push({ form: m[1], cik: Number(m[2]), acc, atMs: e.atMs, tries: plain(was) ? Number(was.tries) || 0 : 0,
                   first: plain(was) && Number(was.first) > 0 ? Number(was.first) : nowMs });
    }
  }
  await Promise.all(fresh.slice(0, 8).map(async f => {
    const base = `https://www.sec.gov/Archives/edgar/data/${f.cik}/${f.acc.replace(/-/g, '')}`;
    const miss = () => { seen[`edgar|${f.acc}`] = { form: f.form, cik: f.cik, atMs: f.atMs, first: f.first, tries: f.tries + 1 }; };
    const idx = await get(base + '/index.json', { ua, until });
    if (!idx) return miss();                                 // unread: try again next minute
    let names = [];
    try { names = JSON.parse(idx).directory.item.map(x => x.name).filter(n => /\.html?$/i.test(n)); } catch {}
    const ex = names.filter(n => /ex(?:hibit)?[-_]?99|press/i.test(n)).sort()[0];
    const doc = ex ? await get(`${base}/${ex}`, { ua, until }) : '';
    if (ex && !doc) return miss();
    // No press release exhibit: the filing's own text (Item 7.01 or 8.01) is read for corrections only (red team 10).
    // The main document: not an exhibit, an index page or an XBRL view (red team 11); the first two read, until one has
    // the Item text.
    const docs = ex ? [] : names.filter(n => !/^ex|[-_]ex\d|-index(?:-headers)?\.html?$|^R\d+\.htm|FilingSummary/i.test(n))
      .sort((a, b) => (/8-?k|6-?k|form/i.test(b) ? 1 : 0) - (/8-?k|6-?k|form/i.test(a) ? 1 : 0) || a.localeCompare(b));
    let text = '';
    for (const n of docs.slice(0, 2)) {
      const body = await get(`${base}/${n}`, { ua, until });
      if (!body) return miss();
      text = itemText(body);
      if (text) break;
    }
    const cos = ARMED.rows.filter(r => Number(r.cik) === f.cik).flatMap(r => [r.company, ...(r.aliases || [])]);
    seen[`edgar|${f.acc}`] = { form: f.form, cik: f.cik, atMs: f.atMs, first: f.first, url: ex ? `${base}/${ex}` : base,
                               title: ex ? exhibitHeadline(doc, cos) : '', exDay: ex ? exhibitDate(doc) : '',
                               // what a correction is read from: the text above the dateline, struck-out text included
                               ctitle: ex ? correctionHeadline(doc) : text, ...(ex ? {} : { cbody: true }),
                               // the exhibit's print, for the right-after check
                               ...(ex && sourcePrint(doc, 'edgar', '', cos) ? { print: sourcePrint(doc, 'edgar', '', cos) } : {}) };
  }));
  beat.edgar = read ? 'read' : 'unreadable';
  return Object.entries(seen).filter(([k, v]) => k.startsWith('edgar|') && plain(v)
      && ((typeof v.title === 'string' && v.title) || (typeof v.ctitle === 'string' && v.ctitle) || /\/A$/i.test(String(v.form || ''))))
    .map(([k, v]) => ({ channel: 'edgar', form: v.form, cik: v.cik, title: typeof v.title === 'string' ? v.title : '',
                        ctitle: typeof v.ctitle === 'string' ? v.ctitle : '', exDay: v.exDay, url: v.url, atMs: v.atMs, key: k,
                        firstMs: Number(v.first) || 0, cbody: v.cbody === true, print: plain(v.print) ? v.print : null }));
}

/** Sponsor feeds. A feed is first read as a baseline: nothing in it then is ever posted, so an old release the feed
 *  re-dates cannot post (red team 4). An item that appears later is fresh; its own page is read (on the feed's host,
 *  after any redirect) for its dateline, which must be the day of its time, as for an SEC exhibit. rss: state.rss,
 *  {feeds: {feed: 1}, urls: {url: {f: first seen ms (0 = in the baseline), d: dateline day, n: page reads}}}. */
async function rssItems(beat, until, rss, nowMs) {
  const feeds = [...new Set(ARMED.rows.flatMap(r => r.feeds))];
  const res = await Promise.all(feeds.map(async f => ({ f, xml: await get(f, { until }) })));
  beat.rss = `${res.filter(x => x.xml).length}/${feeds.length} feeds read`;
  const items = [];
  for (const { f, xml } of res) {
    if (!xml) continue;
    const list = parseFeed(xml).filter(i => i.url);
    if (!list.length) continue;                                   // an empty read never sets a baseline
    const base = !rss.feeds[f];
    rss.feeds[f] = 1;
    for (const i of list) {
      if (!rss.urls[i.url]) rss.urls[i.url] = { f: base ? 0 : nowMs, d: '', n: 0 };
      rss.urls[i.url].seen = nowMs;
      items.push({ ...i, channel: 'rss', feed: f, key: `rss|${i.url}`, fresh: rss.urls[i.url].f > 0, firstMs: Number(rss.urls[i.url].f) || 0 });
    }
  }
  // Read the page of a fresh item that could be a decision (at most 4 a minute, 5 reads each).
  const want = items.filter(i => i.fresh && !rss.urls[i.url].d && rss.urls[i.url].n < 5 && headlineKind(i.title).kind
    && Number.isFinite(i.atMs) && i.atMs > nowMs - 12 * 3600000).slice(0, 4);
  await Promise.all(want.map(async i => {
    rss.urls[i.url].n++;
    const page = await get(i.url, { until, finalUrl: true });
    if (!page) return;
    const host = u => { try { return new URL(u).hostname.toLowerCase(); } catch { return ''; } };
    if (host(page.url) !== host(i.url) || !/^https:/i.test(page.url)) return;   // redirected elsewhere: no dateline
    rss.urls[i.url].d = pageDay(page.txt, i.title);
    const pr = rss.urls[i.url].d ? sourcePrint(page.txt, 'rss', i.title) : null;   // for the right-after check
    if (pr) rss.urls[i.url].p = pr;
  }));
  for (const i of items) { i.exDay = rss.urls[i.url].d || ''; i.print = plain(rss.urls[i.url].p) ? rss.urls[i.url].p : null; }
  return items;
}

function trimRss(rss, nowMs) {
  const urls = Object.entries(rss.urls || {}).filter(([, v]) => v && typeof v === 'object')
    .filter(([, v]) => (v.seen || 0) > nowMs - 90 * 86400000)
    .sort((a, b) => (b[1].seen || 0) - (a[1].seen || 0)).slice(0, 2000);
  return { feeds: rss.feeds || {}, urls: Object.fromEntries(urls) };
}

/** live:state and live:control in one read. live:control is the owner's emergency lever, set by hand in the store
 *  without a deploy: {"publish": false} stops posting, {"retract": {"<row id>": "<public reason>"}} withdraws a post,
 *  {"hide": true} hides every post from /api/v1/live and the pages. */
async function loadState() {
  try {
    // GET, not MGET: a key of another type (a hash, a JSON document made in the console) is an error, and the watch
    // stops, where MGET would read it as missing and ignore the owner's stop or forget what was posted (red team 6).
    const [v, c] = await kv('EVAL', READ_LUA, '2', 'live:state', 'live:control');
    const state = readState(v);
    // A state this watch wrote always holds done and stopAt. Without them (no key, or "{}" written by hand to repair
    // it) the run is a baseline, so nothing published before it posts again (red team 7).
    const fresh = !!state && !(plain(state.done) && typeof state.stopAt === 'number');
    return { state, control: readControl(c), fresh };
  } catch { return null; }
}

const plain = x => !!x && typeof x === 'object' && !Array.isArray(x);

/** What must be written at once: a new baseline, a new item, a new page dateline or read (not the "seen" times). */
function rssFirst(rss) {
  const urls = plain(rss) && plain(rss.urls) ? rss.urls : {};
  return [Object.keys(plain(rss) && plain(rss.feeds) ? rss.feeds : {}).sort(),
          Object.entries(urls).map(([k, v]) => [k, plain(v) ? [v.f, v.d, v.n] : null]).sort()];
}

function trimSeen(seen, nowMs) {
  const keep = Object.entries(seen).filter(([, v]) => v && typeof v === 'object')
    .filter(([, v]) => !Number.isFinite(v.atMs) || v.atMs > nowMs - 3 * 86400000)
    .sort((a, b) => (b[1].atMs || 0) - (a[1].atMs || 0)).slice(0, SEEN_MAX);
  return Object.fromEntries(keep);
}

export default async (req, res) => {
  res.setHeader('Cache-Control', 'no-store');
  const secret = (process.env.CRON_SECRET || '').trim();
  if (!secret) return res.status(503).json({ error: 'not configured' });
  if (req.headers.authorization !== `Bearer ${secret}`) return res.status(401).json({ error: 'unauthorized' });
  const nowMs = Date.now();
  const until = nowMs + DEADLINE_MS;
  if (!kvReady()) return res.status(503).json({ error: 'store not configured' });
  try {
    if ((await kv('SET', 'live:lock', String(nowMs), 'NX', 'EX', '50')) === null) return res.status(200).json({ ok: true, skipped: 'another run is in progress' });
  } catch { return res.status(503).json({ error: 'store unreadable' }); }
  const loaded = await loadState();
  if (loaded === null) return res.status(503).json({ error: 'store unreadable' });
  const { state, control, fresh } = loaded;
  // A damaged live:state is never overwritten: a fresh state would post again what was posted, and forget what a
  // person is holding (red team 5). The owner deletes the key (the next run is a baseline, so nothing published
  // before it posts); until then nothing runs.
  if (state === null) return res.status(503).json({ error: 'live:state is damaged' });
  // Sources first seen while posting was stopped; they never post on their own (a person releases them by hand).
  const stopped0 = plain(state.stopped) ? state.stopped : {};
  const stopped = Object.fromEntries(Object.entries(stopped0).filter(([, t]) => Number(t) > nowMs - 3 * 86400000));
  // The last minute posting was stopped. A source published at or before it never posts on its own, even one the
  // watch could not list while stopped (SEC or a feed down then).
  // With no state at all (the first run, or the key deleted by hand) this run is a baseline: nothing published before
  // it posts on its own, so deleting the state never posts again what was posted or held (red team 6).
  const stopAt0 = fresh ? nowMs : Number(state.stopAt) > nowMs - 3 * 86400000 ? Number(state.stopAt) : 0;
  const done0 = plain(state.done) ? state.done : {};
  const done = Object.fromEntries(Object.entries(done0).filter(([, t]) => Number(t) > nowMs - 400 * 86400000)
    .sort((a, b) => b[1] - a[1]).slice(0, 2000));
  // Posting stops too while posts are hidden, and when a retract key names no armed row and no post (a typo would
  // otherwise withdraw nothing and say nothing).
  const ids = new Set([...ARMED.rows.map(r => r.id), ...Object.keys(plain(state.pub) ? state.pub : {})]);
  const badKeys = Object.keys(plain(control.retract) ? control.retract : {}).filter(k => !ids.has(k));
  const armed = { ...ARMED, publish: ARMED.publish === true && (control.publish === undefined || control.publish === true)
                    && control.hide !== true && !badKeys.length,
                  retract: { ...(plain(ARMED.retract) ? ARMED.retract : {}), ...(plain(control.retract) ? control.retract : {}) },
                  stopped, stopAt: stopAt0, done };
  const pub0 = Object.fromEntries(Object.entries(plain(state.pub) ? state.pub : {}).filter(([, x]) => plain(x)));
  const seen0 = plain(state.seen) ? state.seen : {};
  const seen = { ...seen0 };
  const rss0 = plain(state.rss) ? state.rss : {};
  const rss = { feeds: plain(rss0.feeds) ? { ...rss0.feeds } : {},
                urls: Object.fromEntries(Object.entries(plain(rss0.urls) ? rss0.urls : {}).filter(([, x]) => plain(x)).map(([k, x]) => [k, { ...x }])) };
  const beat = { at: etIso(nowMs), publish: armed.publish, armed: armed.rows.length,
                 ...(badKeys.length ? { control: `retract key not recognised: ${badKeys.slice(0, 3).join(', ')}` } : {}) };
  const listed = [];
  const ua = (process.env.SEC_USER_AGENT || '').trim();

  // The right-after check of what is already up runs beside the reads (a post made in this run is first read again
  // in the next); its results apply only to a post still up after the corrections below.
  const [edgar, rssList, rechecked] = await Promise.all([
    ua ? edgarItems(ua, beat, seen, until, listed, nowMs) : (beat.edgar = 'SEC_USER_AGENT not set', []),
    rssItems(beat, until, rss, nowMs),
    recheckPosts(reconcile(pub0, armed, nowMs), ua, until, nowMs),
  ]);

  // While posting is stopped, every source listed is remembered, read or not, passing or not, so none of them
  // posts on its own when posting resumes (red team 5).
  if (!armed.publish) for (const k of [...listed, ...rssList.map(i => i.key)]) stopped[k] = stopped[k] || nowMs;
  const stopAt = armed.publish ? stopAt0 : nowMs;
  const doneChanged = JSON.stringify(done) !== JSON.stringify(done0);
  let pub = reconcile(pub0, armed, nowMs);
  // A later release by the sponsor that may contradict a post pauses it: hidden until the full review confirms or
  // withdraws it (red teams 6 to 9).
  for (const item of [...edgar, ...rssList]) for (const id of corrections(item, armed, pub))
    pub = { ...pub, [id]: { ...pub[id], status: 'paused', paused_at: etIso(nowMs),
      paused_reason: `a later release by the sponsor (${item.url}) may change this` } };
  for (const [id, set] of Object.entries(rechecked)) if (pub[id] && pub[id].status === 'posted') pub = { ...pub, [id]: { ...pub[id], ...set } };
  const held = [], shadow = [];
  for (const item of [...edgar, ...rssList]) {
    if (!item.title) continue;                       // read only for corrections (above)
    const c = check(item, armed, pub, nowMs);
    if (!c.ok) {
      if (/headline names no armed drug|does not name the FDA|names no decision/.test(c.why)) continue;   // ordinary news
      held.push({ key: item.key, why: c.why });
      continue;
    }
    const rec = {
      id: c.row.id, ticker: c.row.t, kind: c.kind, text: sentence(item, c.row),
      source: { label: sourceLabel(item), url: item.url, published_at: etIso(item.atMs), channel: item.channel },
      posted_at: etIso(Date.now()), run_ms: nowMs, headline: item.title, minutes_after_source: Math.max(0, Math.floor((Date.now() - item.atMs) / 60000)),
      ...(item.print ? { source_print: item.print } : {}),
      page: c.row.url, status: 'posted', check: `headline "${item.title.slice(0, 160)}" names ${c.term} and an FDA ${c.kind === 'approval' ? 'approval' : 'complete response letter'}`,
    };
    // A release by the sponsor in this same read that contradicts or retracts it, first seen in the last day (so one
    // read a minute earlier counts too, red team 10), never lets it post; the feed's baseline never does (red team 11).
    const would = { ...pub, [rec.id]: { ...rec, run_ms: nowMs - 86400000 } };
    if ([...edgar, ...rssList].some(x => x !== item && corrections(x, armed, would).includes(rec.id))) {
      held.push({ key: item.key, why: 'a release by the sponsor in the same read may contradict it' });
      continue;
    }
    if (armed.publish) { pub = { ...pub, [rec.id]: rec }; for (const k of [rec.id, item.url, item.key]) if (k) done[k] = nowMs; }
    else { shadow.push(rec); stopped[item.key] = stopped[item.key] || nowMs; if (item.url) stopped[item.url] = stopped[item.url] || nowMs; }
  }
  beat.held = held.slice(0, 20);
  // Shadow mode (publish false): what WOULD have posted, kept for review, never public; each item once.
  const shadow0 = (plain(state.beat) && Array.isArray(state.beat.shadow) ? state.beat.shadow : []).filter(plain);
  const shadowKeys = new Set(shadow0.map(x => x.id + '|' + (x.source || {}).url));
  const shadowNew = shadow.filter(x => !shadowKeys.has(x.id + '|' + (x.source || {}).url));
  beat.shadow = [...shadow0, ...shadowNew].slice(-20);

  const seenOut = trimSeen(seen, nowMs);
  const rssOut = trimRss(rss, nowMs);
  const changed = JSON.stringify(pub) !== JSON.stringify(pub0);
  const seenChanged = JSON.stringify(seenOut) !== JSON.stringify(seen0)
    || JSON.stringify(stopped) !== JSON.stringify(stopped0) || stopAt !== stopAt0 || doneChanged || JSON.stringify(rssFirst(rssOut)) !== JSON.stringify(rssFirst(rss0));
  const lastBeat = Date.parse((plain(state.beat) && state.beat.at) || '') || 0;
  if (changed || seenChanged || shadowNew.length || nowMs - lastBeat > 10 * 60000) {
    // Written only while this run still holds the lock, so a run that overran never overwrites a newer one's pauses
    // (red team 10); the lock is released with the write.
    let wrote;
    try { wrote = await kv('EVAL', WRITE_LUA, '2', 'live:lock', 'live:state', String(nowMs), JSON.stringify({ pub, beat, seen: seenOut, stopped, stopAt, done, rss: rssOut })); } catch (e) { return res.status(503).json({ error: 'store write failed' }); }
    if (Number(wrote) !== 1) return res.status(200).json({ ok: true, skipped: 'lock lost; a newer run writes' });
  }
  return res.status(200).json({ ok: true, changed, posts: Object.keys(pub).length });
};
