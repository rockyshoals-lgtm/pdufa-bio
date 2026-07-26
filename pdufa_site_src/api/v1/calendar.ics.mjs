import { DATA, resolveTier, meter, TIERS, fail, head } from './_lib.mjs';
import crypto from 'node:crypto';
const esc=s=>String(s||'').replace(/[\\;,]/g,m=>'\\'+m).replace(/\n/g,'\\n');
export default async (req,res)=>{
  const rid='req_'+crypto.randomUUID().slice(0,18);
  const {tier,key}=await resolveTier(req);
  if(tier===null) return fail(res,401,'invalid_key','Unknown API key.',{request_id:rid});
  if(!TIERS[tier].depth) return fail(res,403,'tier_forbidden',
    'Subscribable .ics calendar feeds are a Pro feature.',
    {request_id:rid,_upgrade:'https://www.pdufa.bio/pricing?ref=api_ics'});
  const m=await meter(req,tier,key,1); head(res,{rid,tier,m,cost:1});
  const q=req.query||{};
  let rows=DATA.filter(e=>e.dp==='day'&&e.d);
  if(q.ticker){const s=String(q.ticker).toLowerCase().split(',').map(x=>x.trim());rows=rows.filter(e=>s.includes(String(e.t).toLowerCase()));}
  if(q.type) rows=rows.filter(e=>String(e.type).toLowerCase()===String(q.type).toLowerCase());
  const L=['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//pdufa.bio//catalyst calendar//EN','CALSCALE:GREGORIAN','X-WR-CALNAME:pdufa.bio catalysts'];
  for(const e of rows){
    const d=e.d.replace(/-/g,'');
    L.push('BEGIN:VEVENT',`UID:${e.id}@pdufa.bio`,`DTSTAMP:${new Date().toISOString().replace(/[-:]/g,'').split('.')[0]}Z`,
      `DTSTART;VALUE=DATE:${d}`,`SUMMARY:${esc(e.t+' — '+e.type+': '+e.name)}`,
      `DESCRIPTION:${esc((e.ta||'')+' · pdufa.bio — facts, not investment advice.')}`,
      `URL:${String(e.url).startsWith('http')?e.url:'https://www.pdufa.bio'+e.url}`,'END:VEVENT');
  }
  L.push('END:VCALENDAR');
  res.setHeader('Content-Type','text/calendar; charset=utf-8');
  res.status(200).send(L.join('\r\n'));
};
