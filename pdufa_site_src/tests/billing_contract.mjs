import crypto from 'node:crypto';
process.env.STRIPE_WEBHOOK_SECRET='whsec_testsecret';
process.env.STRIPE_SECRET_KEY='sk_test_fake';

// in-memory KV stand-in
const STORE=new Map();
global.fetch=async(url,opts)=>{
  if(String(url).includes('KVFAKE')){
    const cmd=JSON.parse(opts.body); const [c,k,v]=cmd;
    let result=null;
    if(c==='GET') result=STORE.has(k)?STORE.get(k):null;
    else if(c==='SET'){ if(cmd.includes('NX')&&STORE.has(k)) result=null; else {STORE.set(k,v); result='OK';} }
    else if(c==='INCRBY'){ const n=(Number(STORE.get(k))||0)+Number(v); STORE.set(k,String(n)); result=n; }
    else if(c==='DEL'){ result=STORE.delete(k)?1:0; }
    return {ok:true,json:async()=>({result})};
  }
  throw new Error('unexpected fetch '+url);
};
process.env.KV_REST_API_URL='https://KVFAKE';
process.env.KV_REST_API_TOKEN='tok';

const S=await import('../api/_stripe.mjs');
const {default:webhook}=await import('../api/stripe/webhook.mjs');
const {default:keyEp}=await import('../api/stripe/key.mjs');
const lib=await import('../api/v1/_lib.mjs');
const {default:events}=await import('../api/v1/events.mjs');

let p=0,f=0; const T=(n,c,x='')=>{c?(p++,console.log('  PASS '+n)):(f++,console.log('  FAIL '+n+' '+x))};

function mockRes(){const r={code:0,hdrs:{},body:null,
 setHeader(k,v){this.hdrs[k.toLowerCase()]=v},status(c){this.code=c;return this},
 json(b){this.body=b;return this},send(b){this.body=b;return this},end(){return this},
 writeHead(c,h){this.code=c;Object.assign(this.hdrs,h);return this}};return r}
function signed(ev){
  const body=Buffer.from(JSON.stringify(ev));
  const t=Math.floor(Date.now()/1000);
  const sig=crypto.createHmac('sha256','whsec_testsecret').update(t+'.'+body.toString()).digest('hex');
  const req={method:'POST',headers:{'stripe-signature':`t=${t},v1=${sig}`},body,query:{}};
  return req;
}
const sleep=ms=>new Promise(r=>setTimeout(r,ms));

console.log('\n== WEBHOOK SECURITY ==');
let r=mockRes();
await webhook({method:'POST',headers:{'stripe-signature':'t=1,v1=bad'},body:Buffer.from('{}'),query:{}},r);
T('forged signature -> 400', r.code===400 && r.body.error==='signature_verification_failed');
r=mockRes();
await webhook({method:'GET',headers:{},query:{}},r);
T('GET -> 405', r.code===405);

console.log('\n== SUBSCRIPTION: checkout.session.completed ==');
r=mockRes();
await webhook(signed({id:'evt_sub1',type:'checkout.session.completed',
  data:{object:{id:'cs_test_123',mode:'subscription',customer:'cus_1',subscription:'sub_1',
    customer_details:{email:'a@b.com'},metadata:{tier:'pro',plan:'pro_monthly'}}}}),r);
T('webhook acks 200 fast', r.code===200 && r.body.received===true);
await sleep(60);
const issued=STORE.get('sess:cs_test_123');
T('API key issued + bound to session', !!issued && issued.startsWith('pk_live_'));
T('key record stored hashed', STORE.has('key:'+S.hashKey(issued)));
T('customer -> key mapping', STORE.get('cust:cus_1')===issued);

console.log('\n== ISSUED KEY UNLOCKS DEPTH (the whole point) ==');
let [q,rr]=[{headers:{'x-api-key':issued},query:{limit:'200'}},mockRes()];
await events(q,rr);
T('tier resolves to pro from KV', rr.body.meta.tier==='pro');
T('no _locked marker', rr.body.data[0]._locked===undefined);
const withCoh=rr.body.data.find(d=>d.cohort_n);
T('real Depth data returned', !!withCoh && typeof withCoh.cohort_move_median_pct==='number');

console.log('\n== IDEMPOTENCY (Stripe delivers at-least-once) ==');
const before=STORE.get('cust:cus_1');
r=mockRes();
await webhook(signed({id:'evt_sub1',type:'checkout.session.completed',
  data:{object:{id:'cs_test_123',mode:'subscription',customer:'cus_1',subscription:'sub_1',metadata:{tier:'pro'}}}}),r);
await sleep(60);
T('replayed event does NOT reissue key', STORE.get('cust:cus_1')===before);

console.log('\n== CREDIT PACK + double-credit protection ==');
r=mockRes();
await webhook(signed({id:'evt_cr1',type:'checkout.session.completed',
  data:{object:{id:'cs_cr_1',mode:'payment',customer:'cus_1',payment_intent:'pi_1',
    metadata:{credits:'25000',plan:'credits_25k'}}}}),r);
await sleep(60);
T('25k credits added', Number(STORE.get('credits:'+S.hashKey(issued)))===25000);
r=mockRes();
await webhook(signed({id:'evt_cr2',type:'checkout.session.completed',
  data:{object:{id:'cs_cr_1',mode:'payment',customer:'cus_1',payment_intent:'pi_1',
    metadata:{credits:'25000'}}}}),r);
await sleep(60);
T('same payment_intent cannot double-credit', Number(STORE.get('credits:'+S.hashKey(issued)))===25000);

console.log('\n== LIFECYCLE ==');
r=mockRes();
await webhook(signed({id:'evt_pf',type:'invoice.payment_failed',data:{object:{customer:'cus_1'}}}),r);
await sleep(50);
T('payment_failed -> past_due (NOT revoked)', JSON.parse(STORE.get('key:'+S.hashKey(issued))).status==='past_due');
r=mockRes();
await webhook(signed({id:'evt_paid',type:'invoice.paid',data:{object:{customer:'cus_1'}}}),r);
await sleep(50);
T('invoice.paid -> reactivated (renewal works)', JSON.parse(STORE.get('key:'+S.hashKey(issued))).status==='active');
r=mockRes();
await webhook(signed({id:'evt_del',type:'customer.subscription.deleted',data:{object:{customer:'cus_1'}}}),r);
await sleep(50);
const rec=JSON.parse(STORE.get('key:'+S.hashKey(issued)));
T('subscription.deleted -> tier=free', rec.tier==='free' && rec.status==='canceled');
// Gating was reconciled 2026-07-11: cohort/indication/etc are PUBLIC on the site, so they are
// free in the API. The real moat is the per-event run-up SERIES. That is what must re-lock.
[q,rr]=[{headers:{'x-api-key':issued},query:{limit:'5'}},mockRes()];
await events(q,rr);
T('cancelled key -> tier drops to free', rr.body.meta.tier==='free');
T('cancelled key still gets PUBLIC fields (by design)', 'cohort_n' in rr.body.data[0]);
const {default:runupEp}=await import('../api/v1/runup.mjs');
[q,rr]=[{headers:{'x-api-key':issued},query:{ticker:'MRK'}},mockRes()];
await runupEp(q,rr);
T('cancelled key -> RUN-UP SERIES re-locks (the real moat)', rr.code===403 && rr.body.error.code==='tier_forbidden');

console.log('\n== KEY REVEAL: show once, then burn ==');
STORE.set('sess:cs_reveal','pk_live_abc');
let kr=mockRes(); await keyEp({query:{session_id:'cs_reveal'}},kr);
T('first reveal returns key', kr.code===200 && kr.body.api_key==='pk_live_abc');
kr=mockRes(); await keyEp({query:{session_id:'cs_reveal'}},kr);
T('second reveal -> 404 (burned)', kr.code===404);
kr=mockRes(); await keyEp({query:{session_id:'../etc'}},kr);
T('malformed session_id rejected', kr.code===400);

console.log(`\n${p} passed, ${f} failed`);
process.exit(f?1:0);
