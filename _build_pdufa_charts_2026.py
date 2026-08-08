# -*- coding: utf-8 -*-
"""Complete 2026 PDUFA charts: decided (T-120->T+30, outcome-colored) + upcoming (T-120->today, pending)."""
import json, datetime as dt, numpy as np
ev=json.load(open('_chart2026_events.json'))
px=json.load(open('_chart_pxcache.json'))
MON=["","Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
def series(tk): return sorted((px.get(tk) or {}).items())

def win_decided(tk,pdate,pre=120,post=30):
    s=series(tk)
    if len(s)<30: return None
    dates=[x[0] for x in s]; idx=None
    for i,dd in enumerate(dates):
        if dd<=pdate: idx=i
        else: break
    if idx is None: return None
    lo=max(0,idx-pre); hi=min(len(s),idx+post+1)
    w=s[lo:hi]
    return [p for _,p in w],[d for d,_ in w],idx-lo,len(w)  # prices,dates,pivot,axis_n

def win_upcoming(tk,pdate,pre=120):
    s=series(tk)
    if len(s)<20: return None
    last=dt.date.fromisoformat(s[-1][0]); pdd=dt.date.fromisoformat(pdate)
    d2p=int(np.busday_count(last,pdd))
    if d2p<0: d2p=0
    histn=pre-d2p
    if histn<8: return None          # too far out — no meaningful runup window yet
    hist=s[-histn:] if histn<=len(s) else s
    prices=[p for _,p in hist]; dates=[d for d,_ in hist]
    pivot=len(prices)-1+d2p; axis_n=pivot+3
    return prices,dates,pivot,axis_n,d2p

def chart(e):
    up = e['status']=='upcoming'
    r = win_upcoming(e['ticker'],e['date']) if up else win_decided(e['ticker'],e['date'])
    if not r: return None
    if up: prices,dates,piv,n,d2p=r
    else:  prices,dates,piv,n=r; d2p=0
    if len(prices)<10: return None
    W,H=360,168; x0,x1,y0,y1=36,W-8,30,H-20
    lo,hi=min(prices),max(prices); sp=(hi-lo) or 1; lo-=sp*0.08; hi+=sp*0.08; rng=(hi-lo) or 1
    X=lambda i:x0+i/(n-1)*(x1-x0); Y=lambda v:y1-(v-lo)/rng*(y1-y0)
    pts=" ".join(f"{X(i):.1f},{Y(p):.1f}" for i,p in enumerate(prices))
    appr=e['outcome']=='APPROVAL'
    mc = "#7fa8d8" if up else ("#5fd07a" if appr else "#ff7a7a")
    xp=X(piv)
    shade=f'<rect x="{xp:.1f}" y="{y0}" width="{x1-xp:.1f}" height="{y1-y0}" fill="{mc}" opacity="0.06"/>' if not up else ""
    vline=f'<line x1="{xp:.1f}" y1="{y0}" x2="{xp:.1f}" y2="{y1}" stroke="{mc}" stroke-width="1.3" stroke-dasharray="3,2"/>'
    dot="" if up else f'<circle cx="{xp:.1f}" cy="{Y(prices[piv]):.1f}" r="2.6" fill="{mc}"/>'
    lastdot=f'<circle cx="{X(len(prices)-1):.1f}" cy="{Y(prices[-1]):.1f}" r="2.2" fill="#e3ba5e"/>' if up else ""
    ylab=(f'<text x="{x0-3:.0f}" y="{Y(max(prices))+3:.0f}" fill="#7e95b6" font-size="8.5" text-anchor="end">${max(prices):.2f}</text>'
          f'<text x="{x0-3:.0f}" y="{Y(min(prices))+3:.0f}" fill="#7e95b6" font-size="8.5" text-anchor="end">${min(prices):.2f}</text>')
    def shortd(d): p=d.split('-'); return f"{MON[int(p[1])]}{p[2]}"
    def dl(xpos,txt,anchor,col="#7e95b6"): return f'<text x="{xpos:.0f}" y="{H-7:.0f}" fill="{col}" font-size="8.5" text-anchor="{anchor}">{txt}</text>'
    xlabs=dl(X(0),shortd(dates[0]),"start")+dl(xp,shortd(e['date']),"middle",mc)+(dl(X(len(prices)-1),shortd(dates[-1]),"end","#e3ba5e") if up else dl(X(n-1),shortd(dates[-1]),"end"))
    p0idx=piv if not up else len(prices)-1
    runup=(prices[p0idx]/prices[0]-1)*100
    if up:
        sub=f"PDUFA {e['date']} · UPCOMING (in {d2p}td) · runup-so-far {runup:+.0f}%"
    else:
        npost=len(prices)-1-piv                       # sessions AFTER the decision in-window
        if npost<=0:
            # decided but no post-decision session has closed yet. "+0%" would read as a flat
            # reaction; the truth is there is no post data. Say so.
            sub=f"PDUFA {e['date']} · {'APPR' if appr else 'CRL'} · runup {runup:+.0f}% · post pending"
        else:
            post=(prices[-1]/prices[piv]-1)*100
            sub=f"PDUFA {e['date']} · {'APPR' if appr else 'CRL'} · runup {runup:+.0f}% · post{npost}d {post:+.0f}%"
    title=f"{e['ticker']} · {e['drug'][:24]}"
    svg=(f'<svg viewBox="0 0 {W} {H}" class="mc">'
         f'<text x="4" y="12" fill="#f2f6fc" font-size="11" font-weight="700">{title}</text>'
         f'<text x="4" y="23" fill="{mc}" font-size="9">{sub}</text>'
         f'{shade}<polyline points="{pts}" fill="none" stroke="#e3ba5e" stroke-width="1.4"/>{vline}{dot}{lastdot}{ylab}{xlabs}</svg>')
    return dict(svg=svg,up=up,appr=appr,runup=runup)

bym={}; built=0; skipped=0
for e in sorted(ev,key=lambda x:x['date']):
    c=chart(e)
    if not c: skipped+=1; continue
    bym.setdefault(e['date'][:7],[]).append((e,c)); built+=1
allc=[c for v in bym.values() for _,c in v]
dec=[c for c in allc if not c['up']]; upc=[c for c in allc if c['up']]
appr=[c for c in dec if c['appr']]; crl=[c for c in dec if not c['appr']]
import statistics as st
parts=[f"""<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>2026 PDUFA price paths · T-120 → T+30</title><style>
*{{box-sizing:border-box}}body{{margin:0;background:#02060d;color:#f2f6fc;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif}}
.wrap{{max-width:1320px;margin:0 auto;padding:20px 16px 70px}}
h1{{font-size:22px;margin:0 0 4px}}h1 b{{color:#e3ba5e}}.sub{{color:#a7bcd9;font-size:13px;margin-bottom:14px}}
.kpis{{display:flex;gap:10px;flex-wrap:wrap;margin:12px 0 18px}}
.kpi{{background:#0c1d38;border:1px solid #1a3358;border-radius:10px;padding:9px 13px;font-size:12.5px;color:#a7bcd9}}.kpi b{{color:#f2f6fc;font-size:15px}}
.nav{{position:sticky;top:0;background:#02060dee;backdrop-filter:blur(6px);padding:8px 0;border-bottom:1px solid #1a3358;margin-bottom:10px;font-size:12px}}
.nav a{{color:#6fb6ff;text-decoration:none;margin-right:10px}}
.mhead{{font-size:15px;color:#e3ba5e;font-weight:800;margin:22px 0 8px;border-bottom:1px solid #1a3358;padding-bottom:5px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:10px}}
.cell{{background:#0a1730;border:1px solid #16304f;border-radius:10px;padding:4px}}
svg.mc{{width:100%;display:block;background:#071528;border-radius:8px}}
.g{{color:#5fd07a}}.r{{color:#ff7a7a}}.b{{color:#7fa8d8}}.gold{{color:#e3ba5e}}
footer{{margin-top:30px;font-size:11px;color:#637a99}}</style></head><body><div class=wrap>
<h1>2026 FDA <b>PDUFA price paths</b> — complete year</h1>
<div class=sub>All 2026 PDUFAs. <span class=g>Green = approval</span>, <span class=r>red = CRL</span> (T-120→T+30, shaded = post-decision); <span class=b>blue = upcoming</span> (T-120→today, gold dot = latest close, dashed marker = the pending PDUFA date). Historical data, not advice.</div>
<div class=kpis>
<div class=kpi><b>{built}</b> events</div>
<div class=kpi><b class=g>{len(appr)}</b> approvals</div><div class=kpi><b class=r>{len(crl)}</b> CRLs</div>
<div class=kpi><b class=b>{len(upc)}</b> upcoming</div>
<div class=kpi>decided approval rate <b>{(100*len(appr)/max(1,len(dec))):.0f}%</b></div>
</div>"""]
months=sorted(bym)
parts.append("<div class=nav>Jump: "+" ".join(f'<a href="#m{m}">{MON[int(m[5:7])]}</a>' for m in months)+"</div>")
for m in months:
    rows=sorted(bym[m],key=lambda x:x[0]['date'])
    nup=sum(1 for _,c in rows if c['up'])
    tag=f" · {nup} upcoming" if nup else ""
    parts.append(f'<div class="mhead" id="m{m}">{MON[int(m[5:7])]} {m[:4]} — {len(rows)} PDUFAs{tag}</div><div class=grid>')
    for e,c in rows: parts.append(f'<div class=cell>{c["svg"]}</div>')
    parts.append('</div>')
parts.append(f'<footer>2026 PDUFA decisions: outcomes verified against primary sources (company 8-K / press release); upcoming from the pdufa.bio crawler; daily closes from market data providers, most recent sessions verified against live quotes. {built} charted, {skipped} skipped (insufficient/too-early price history). Informational/educational only — not investment advice.</footer></div></body></html>')
open('PDUFA_2026_complete_charts.html','w',encoding='utf-8').write("".join(parts))
print(f"built {built} | decided {len(dec)} (appr {len(appr)} crl {len(crl)}) | upcoming {len(upc)} | skipped {skipped}")
