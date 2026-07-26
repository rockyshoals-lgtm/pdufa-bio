import { DATA } from './_lib.mjs';
export default (req,res)=>{
  res.setHeader('Access-Control-Allow-Origin','*');
  res.setHeader('Cache-Control','no-store');
  res.status(200).json({status:'ok',version:'v1',events:DATA.length,
    metered: !!((process.env.KV_REST_API_URL||process.env.UPSTASH_REDIS_REST_URL)&&(process.env.KV_REST_API_TOKEN||process.env.UPSTASH_REDIS_REST_TOKEN)),
    billing: !!(process.env.STRIPE_SECRET_KEY&&process.env.STRIPE_WEBHOOK_SECRET),
    prices_configured: ['PRO_MONTHLY','PRO_ANNUAL','CREDITS_25K','CREDITS_100K','CREDITS_300K'].filter(k=>process.env['STRIPE_PRICE_'+k]).length,
    enforcing: process.env.API_ENFORCE==='1',
    billing_live: process.env.BILLING_LIVE==='1',   // Pro checkout kill-switch
    as_of:new Date().toISOString()});
};
