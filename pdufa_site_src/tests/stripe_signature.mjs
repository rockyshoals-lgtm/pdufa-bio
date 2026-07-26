import crypto from 'node:crypto';
import { verifyStripeSig } from '../api/_stripe.mjs';
const secret='whsec_test_abc123';
const body=Buffer.from(JSON.stringify({id:'evt_1',type:'checkout.session.completed'}));
const t=Math.floor(Date.now()/1000);
const sig=crypto.createHmac('sha256',secret).update(t+'.'+body.toString(),'utf8').digest('hex');
let p=0,f=0; const T=(n,c)=>{c?(p++,console.log('  PASS',n)):(f++,console.log('  FAIL',n))};

T('valid signature accepted',        verifyStripeSig(body,`t=${t},v1=${sig}`,secret)===true);
T('wrong secret rejected',           verifyStripeSig(body,`t=${t},v1=${sig}`,'whsec_wrong')===false);
T('tampered body rejected',          verifyStripeSig(Buffer.from('{"id":"evt_evil"}'),`t=${t},v1=${sig}`,secret)===false);
T('missing header rejected',         verifyStripeSig(body,null,secret)===false);
T('no v1 scheme rejected',           verifyStripeSig(body,`t=${t},v0=${sig}`,secret)===false);
// replay: 10 minutes old
const old=t-600;
const oldSig=crypto.createHmac('sha256',secret).update(old+'.'+body.toString(),'utf8').digest('hex');
T('stale timestamp rejected (replay)',verifyStripeSig(body,`t=${old},v1=${oldSig}`,secret)===false);
// v0 downgrade attempt alongside a bad v1
T('v0 present but v1 invalid -> reject', verifyStripeSig(body,`t=${t},v1=deadbeef,v0=${sig}`,secret)===false);
// multiple v1 (secret rolling) — one valid
T('rolled secret: one of two v1 valid', verifyStripeSig(body,`t=${t},v1=deadbeef,v1=${sig}`,secret)===true);
console.log(`\n${p} passed, ${f} failed`);
process.exit(f?1:0);
