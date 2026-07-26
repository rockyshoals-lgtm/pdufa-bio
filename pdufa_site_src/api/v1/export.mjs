import { DATA, resolveTier, meter, TIERS, head, fail, quota402, shape } from './_lib.mjs';
import crypto from 'node:crypto';
export default async (req,res)=>{
  const rid='req_'+crypto.randomUUID().slice(0,18);
  const {tier,key}=await resolveTier(req);
  if(tier===null) return fail(res,401,'invalid_key','Unknown API key.',{request_id:rid});
  if(!TIERS[tier].depth) return fail(res,403,'tier_forbidden',
    'Bulk export is a Pro feature. Upgrade to export the full dataset as CSV or JSONL.',
    {request_id:rid,_upgrade:'https://www.pdufa.bio/pricing?ref=api_export'});
  const m=await meter(req,tier,key,50);
  head(res,{rid,tier,m,cost:50});
  if(m.blocked) return quota402(res,m,rid,[]);
  const fmt=String((req.query&&req.query.format)||'csv').toLowerCase();
  const rows=DATA.map(e=>shape(e,tier));
  if(fmt==='jsonl'){
    res.setHeader('Content-Type','application/x-ndjson');
    res.setHeader('Content-Disposition','attachment; filename="pdufa-bio-export.jsonl"');
    return res.status(200).send(rows.map(r=>JSON.stringify(r)).join('\n'));
  }
  const cols=Object.keys(rows[0]).filter(c=>!c.startsWith('_'));
  const esc=v=>v==null?'':/[",\n]/.test(String(v))?'"'+String(v).replace(/"/g,'""')+'"':String(v);
  const csv=[cols.join(','),...rows.map(r=>cols.map(c=>esc(typeof r[c]==='object'?JSON.stringify(r[c]):r[c])).join(','))].join('\n');
  res.setHeader('Content-Type','text/csv; charset=utf-8');
  res.setHeader('Content-Disposition','attachment; filename="pdufa-bio-export.csv"');
  res.status(200).send(csv);
};
