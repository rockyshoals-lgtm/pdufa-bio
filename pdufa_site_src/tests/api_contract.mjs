process.env.API_KEYS_FREE='free_test_key';
process.env.API_KEYS_PRO='pro_test_key';
process.env.API_KEYS_QUANT='quant_test_key';
const { default: events } = await import('../api/v1/events.mjs');
const { default: usage }  = await import('../api/v1/usage.mjs');
const { default: exp }    = await import('../api/v1/export.mjs');
const { default: ics }    = await import('../api/v1/calendar.ics.mjs');
const { default: health } = await import('../api/v1/health.mjs');

// Reconciled: these are visible on public /pdufa/* pages, so they MUST be free in the API.
const PUBLIC_FREE=['nct_id','indication','market_cap_usd','cash_runway_months','days_to_decision',
 'cohort_move_median_pct','cohort_move_p25_pct','cohort_move_p75_pct','cohort_n'];

function mock(headers={},query={}){
  const res={code:0,hdrs:{},body:null,
    setHeader(k,v){this.hdrs[k.toLowerCase()]=v},
    status(c){this.code=c;return this},
    json(b){this.body=b;return this},
    send(b){this.body=b;return this},
    end(){return this}};
  return [{headers,query},res];
}
let pass=0,fail=0;
const t=(name,cond,extra='')=>{ if(cond){pass++;console.log('  PASS  '+name)} else {fail++;console.log('  FAIL  '+name+' '+extra)} };

console.log('\n== ANONYMOUS (no key) ==');
let [q,r]=mock({},{limit:'3'}); await events(q,r);
t('200 OK', r.code===200);
t('PUBLIC fields are FREE (not locked)', PUBLIC_FREE.every(k=>k in r.body.data[0]));
t('no _locked (nothing in payload is gated)', r.body.data[0]._locked===undefined);
t('_pro pointer present', String(r.body.data[0]._pro).includes('/pricing'));
t('core fields present', !!r.body.data[0].id && !!r.body.data[0].ticker && !!r.body.data[0].url);
t('stable id format', /^(pdufa|readout|conference|adcomm)_/.test(r.body.data[0].id), r.body.data[0].id);
t('date_precision present', ['day','month','quarter',null].includes(r.body.data[0].date_precision));
t('link-back url to pdufa.bio', String(r.body.data[0].url).startsWith('https://'));
t('tier=anonymous', r.body.meta.tier==='anonymous');
t('X-Quota-State header', !!r.hdrs['x-quota-state']);
t('X-Request-Id header', !!r.hdrs['x-request-id']);
t('X-Credits-Cost=1', r.hdrs['x-credits-cost']==='1');
t('stale-if-error in Cache-Control', String(r.hdrs['cache-control']).includes('stale-if-error'));
t('ETag set', !!r.hdrs['etag']);

console.log('\n== FREE key ==');
[q,r]=mock({'x-api-key':'free_test_key'},{limit:'3'}); await events(q,r);
t('200 OK', r.code===200);
t('free key also gets the public fields', PUBLIC_FREE.every(k=>k in r.body.data[0]));
t('free: cohort data actually populated', r.body.data.some(d=>typeof d.cohort_n==='number'));
t('tier=free', r.body.meta.tier==='free');
t('meta lists pro_features', Array.isArray(r.body.meta.pro_features));

console.log('\n== PRO key ==');
[q,r]=mock({'x-api-key':'pro_test_key'},{limit:'200'}); await events(q,r);
const withCohort=r.body.data.find(d=>d.cohort_n);
t('200 OK', r.code===200);
t('tier=pro', r.body.meta.tier==='pro');
t('pro: no _pro pointer', r.body.data[0]._pro===undefined);
t('pro: cohort present', 'cohort_move_median_pct' in r.body.data[0]);
t('real cohort data returned', !!withCohort && typeof withCohort.cohort_move_median_pct==='number',
   withCohort?JSON.stringify({n:withCohort.cohort_n,med:withCohort.cohort_move_median_pct}):'none');
t('pro: no pro_features nag', r.body.meta.pro_features===undefined);

console.log('\n== BAD KEY ==');
[q,r]=mock({'x-api-key':'nope'},{}); await events(q,r);
t('401 invalid_key', r.code===401 && r.body.error.code==='invalid_key');
t('error has request_id+docs', !!r.body.error.request_id && !!r.body.error.docs);

console.log('\n== BAD PARAM ==');
[q,r]=mock({},{bogus:'1'}); await events(q,r);
t('400 invalid_param', r.code===400 && r.body.error.code==='invalid_param');
t('lists valid values', String(r.body.error.message).includes('ticker'));

console.log('\n== TIER-GATED ENDPOINTS ==');
[q,r]=mock({},{}); await exp(q,r);
t('export 403 for anonymous', r.code===403 && r.body.error.code==='tier_forbidden');
t('403 carries _upgrade', String(r.body.error._upgrade).includes('/pricing'));
[q,r]=mock({'x-api-key':'pro_test_key'},{format:'csv'}); await exp(q,r);
t('export 200 CSV for pro', r.code===200 && String(r.body).split('\n')[0].includes('cohort_move_median_pct'));
t('export cost=50', r.hdrs['x-credits-cost']==='50');
[q,r]=mock({},{}); await ics(q,r);
t('ics 403 for anonymous', r.code===403);
[q,r]=mock({'x-api-key':'pro_test_key'},{ticker:'CELC'}); await ics(q,r);
t('ics 200 for pro + VCALENDAR', r.code===200 && String(r.body).startsWith('BEGIN:VCALENDAR'));

console.log('\n== USAGE / HEALTH ==');
[q,r]=mock({'x-api-key':'free_test_key'},{}); await usage(q,r);
t('usage 200', r.code===200 && r.body.tier==='free');
t('usage shows depth_access=false', r.body.depth_access===false);
t('usage gives upgrade url', String(r.body.upgrade).includes('/pricing'));
[q,r]=mock({},{}); await health(q,r);
t('health ok', r.code===200 && r.body.status==='ok');
t('health reports unmetered (fail-open)', r.body.metered===false);

console.log('\n== CSV + include=runup cost ==');
[q,r]=mock({'x-api-key':'pro_test_key'},{format:'csv',limit:'2'}); await events(q,r);
t('csv format', typeof r.body==='string' && r.body.includes(','));
[q,r]=mock({'x-api-key':'pro_test_key'},{include:'runup'}); await events(q,r);
t('include=runup cost=5', r.hdrs['x-credits-cost']==='5');


console.log('\n== RUN-UP SERIES: the actual moat (Pro-only) ==');
const {default:runup}=await import('../api/v1/runup.mjs');
[q,r]=mock({},{ticker:'CELC'}); await runup(q,r);
t('anon -> 403 tier_forbidden', r.code===403 && r.body.error.code==='tier_forbidden');
t('403 explains Core stays free', String(r.body.error.message).toLowerCase().includes('free'));
[q,r]=mock({'x-api-key':'free_test_key'},{ticker:'CELC'}); await runup(q,r);
t('free key -> 403 too', r.code===403);
[q,r]=mock({'x-api-key':'pro_test_key'},{ticker:'MRK'}); await runup(q,r);
t('pro -> 200 with series', r.code===200 && r.body.data.length>0 && !!r.body.data[0].idx);
t('series is the T-120..T+5 path', Object.keys(r.body.data[0].idx).length>40);
t('runup costs 5 credits', r.hdrs['x-credits-cost']==='5');
[q,r]=mock({'x-api-key':'pro_test_key'},{}); await runup(q,r);
t('no id/ticker -> 400', r.code===400);

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail?1:0);
