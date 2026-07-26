import { resolveTier, meter, TIERS, head, fail } from './_lib.mjs';
import crypto from 'node:crypto';
export default async (req,res)=>{
  const rid='req_'+crypto.randomUUID().slice(0,18);
  const {tier,key}=await resolveTier(req);
  if(tier===null) return fail(res,401,'invalid_key','Unknown API key.',{request_id:rid});
  const m=await meter(req,tier,key,0);
  head(res,{rid,tier,m,cost:0});
  res.setHeader('Cache-Control','no-store');
  res.status(200).json({tier,quota:{limit:m.limit,used:m.used,remaining:m.remaining,
    state:m.state,resets_at:new Date(m.reset*1000).toISOString(),window:TIERS[tier].window},
    credits_remaining:m.credits,burst_per_min:TIERS[tier].burst,
    depth_access:TIERS[tier].depth,history_access:TIERS[tier].history,
    upgrade: TIERS[tier].depth?null:'https://www.pdufa.bio/pricing?ref=api_usage', request_id:rid});
};
