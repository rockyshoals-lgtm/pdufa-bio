# -*- coding: utf-8 -*-
"""Zoomed T-15 -> T+5 charts, nano/micro/small 2025-26 PDUFAs, every date on the axis (run-in comparison)."""
import json, datetime as dt, numpy as np
ev=json.load(open('_chart15_events.json'))
px=json.load(open('_chart_pxcache.json'))
MON=["","Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
def series(tk): return sorted((px.get(tk) or {}).items())
def md(d): p=d.split('-'); return f"{int(p[1])}/{int(p[2])}"

def win(e,pre=15,post=5):
    s=series(e['ticker'])
    if len(s)<10: return None
    if e['status']=='upcoming':
        last=dt.date.fromisoformat(s[-1][0]); pdd=dt.date.fromisoformat(e['date'])
        d2p=max(0,int(np.busday_count(last,pdd)))
        hist=s[-(pre+1):]
        prices=[p for _,p in hist]; dates=[d for d,_ in hist]
        return prices,dates,len(prices)-1+d2p,len(prices)-1+d2p+2,d2p,len(prices)-1
    dates_all=[x[0] for x in s]; idx=None
    for i,dd in enumerate(dates_all):
        if dd<=e['date']: idx=i
        else: break
    if idx is None or idx<8: return None
    lo=max(0,idx-pre); hi=min(len(s),idx+post+1)
    w=s[lo:hi]
    return [p for _,p in w],[d for d,_ in w],idx-lo,len(w),0,len(w)-1

def chart(e):
    r=win(e)
    if not r: return None
    prices,dates,piv,n,d2p,lastpx=r
    if len(prices)<8: return None
    up=e['status']=='upcoming'
    W,H=384,212; x0,x1,y0,y1=34,W-10,28,150
    lo,hi=min(prices),max(prices); sp=(hi-lo) or 1; lo-=sp*0.10; hi+=sp*0.10; rng=(hi-lo) or 1
    X=lambda i:x0+i/(n-1)*(x1-x0); Y=lambda v:y1-(v-lo)/rng*(y1-y0)
    appr=e['outcome']=='APPROVAL'
    mc="#7fa8d8" if up else ("#5fd07a" if appr else "#ff7a7a")
    pts=" ".join(f"{X(i):.1f},{Y(p):.1f}" for i,p in enumerate(prices))
    dots="".join(f'<circle cx="{X(i):.1f}" cy="{Y(p):.1f}" r="1.5" fill="#e3ba5e"/>' for i,p in enumerate(prices))
    xp=X(piv)
    shade=("" if up else f'<rect x="{xp:.1f}" y="{y0}" width="{x1-xp:.1f}" height="{y1-y0}" fill="{mc}" opacity="0.07"/>')
    vline=f'<line x1="{xp:.1f}" y1="{y0}" x2="{xp:.1f}" y2="{y1}" stroke="{mc}" stroke-width="1.5" stroke-dasharray="3,2"/>'
    t0lab=f'<text x="{xp:.1f}" y="{y0-2:.0f}" fill="{mc}" font-size="8" text-anchor="middle" font-weight="700">PDUFA</text>'
    # all dates rotated -45 under each price point
    dl=[]
    for i,d in enumerate(dates):
        col= mc if i==piv else "#8aa0c0"
        dl.append(f'<text transform="rotate(-45,{X(i):.1f},{y1+7:.0f})" x="{X(i):.1f}" y="{y1+7:.0f}" fill="{col}" font-size="7" text-anchor="end">{md(d)}</text>')
    # date under the PDUFA marker if it's beyond the plotted prices (upcoming)
    if up and piv>len(prices)-1:
        dl.append(f'<text transform="rotate(-45,{xp:.1f},{y1+7:.0f})" x="{xp:.1f}" y="{y1+7:.0f}" fill="{mc}" font-size="7" text-anchor="end" font-weight="700">{md(e["date"])}</text>')
    ylab=(f'<text x="{x0-3:.0f}" y="{Y(max(prices))+3:.0f}" fill="#7e95b6" font-size="8.5" text-anchor="end">${max(prices):.2f}</text>'
          f'<text x="{x0-3:.0f}" y="{Y(min(prices))+3:.0f}" fill="#7e95b6" font-size="8.5" text-anchor="end">${min(prices):.2f}</text>')
    # metrics
    p0=prices[piv] if piv<len(prices) else prices[lastpx]
    t15=(p0/prices[0]-1)*100
    if up:
        sub=f"{e['tier']} · UPCOMING (in {d2p}td) · T-15→now {t15:+.0f}%"
    else:
        pre1=prices[piv-1] if piv>0 else prices[0]; d1=(prices[piv]/pre1-1)*100 if piv>0 else 0
        post5=(prices[-1]/prices[piv]-1)*100
        sub=f"{e['tier']} · {'APPR' if appr else 'CRL'} · into:{(pre1/prices[0]-1)*100:+.0f}% · d1:{d1:+.0f}% · T+5:{post5:+.0f}%"
    title=f"{e['ticker']} · {e['drug'][:22]}"
    svg=(f'<svg viewBox="0 0 {W} {H}" class="mc">'
         f'<text x="4" y="12" fill="#f2f6fc" font-size="11" font-weight="700">{title}</text>'
         f'<text x="4" y="23" fill="{mc}" font-size="9">PDUFA {e["date"]} · {sub}</text>'
         f'{shade}<polyline points="{pts}" fill="none" stroke="#e3ba5e" stroke-width="1.5"/>{dots}{vline}{t0lab}{ylab}{"".join(dl)}</svg>')
    return dict(svg=svg,up=up,appr=appr)

bym={}; built=0; skipped=0
for e in sorted(ev,key=lambda x:x['date']):
    c=chart(e)
    if not c: skipped+=1; continue
    bym.setdefault(e['date'][:7],[]).append((e,c)); built+=1
allc=[c for v in bym.values() for _,c in v]
dec=[c for c in allc if not c['up']]; upc=[c for c in allc if c['up']]
appr=[c for c in dec if c['appr']]; crl=[c for c in dec if not c['appr']]
parts=[f"""<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>Nano/Micro/Small PDUFAs · T-15 → T+5</title><style>
*{{box-sizing:border-box}}body{{margin:0;background:#02060d;color:#f2f6fc;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif}}
.wrap{{max-width:1340px;margin:0 auto;padding:20px 16px 70px}}h1{{font-size:22px;margin:0 0 4px}}h1 b{{color:#e3ba5e}}
.sub{{color:#a7bcd9;font-size:13px;margin-bottom:14px}}.kpis{{display:flex;gap:10px;flex-wrap:wrap;margin:12px 0 16px}}
.kpi{{background:#0c1d38;border:1px solid #1a3358;border-radius:10px;padding:9px 13px;font-size:12.5px;color:#a7bcd9}}.kpi b{{color:#f2f6fc;font-size:15px}}
.nav{{position:sticky;top:0;background:#02060dee;backdrop-filter:blur(6px);padding:8px 0;border-bottom:1px solid #1a3358;margin-bottom:10px;font-size:12px}}.nav a{{color:#6fb6ff;text-decoration:none;margin-right:9px}}
.mhead{{font-size:15px;color:#e3ba5e;font-weight:800;margin:20px 0 8px;border-bottom:1px solid #1a3358;padding-bottom:5px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(350px,1fr));gap:10px}}
.cell{{background:#0a1730;border:1px solid #16304f;border-radius:10px;padding:4px}}svg.mc{{width:100%;display:block;background:#071528;border-radius:8px}}
.g{{color:#5fd07a}}.r{{color:#ff7a7a}}.b{{color:#7fa8d8}}footer{{margin-top:28px;font-size:11px;color:#637a99}}</style></head><body><div class=wrap>
<h1>Nano / Micro / Small <b>PDUFAs</b> — the last 3 weeks in (T-15 → T+5)</h1>
<div class=sub>2025–26, CAPR/MNKD/UNCY-sized only. Gold line+dots = daily close, every date on the axis; dashed marker = the <b>PDUFA date</b> (<span class=g>green approval</span>, <span class=r>red CRL</span>, <span class=b>blue upcoming</span>); shaded = T-0→T+5. Subtitle: run-in to T-1 · decision-day · T+5. Not advice.</div>
<div class=kpis><div class=kpi><b>{built}</b> events</div><div class=kpi><b class=g>{len(appr)}</b> approvals</div><div class=kpi><b class=r>{len(crl)}</b> CRLs</div><div class=kpi><b class=b>{len(upc)}</b> upcoming</div></div>"""]
months=sorted(bym)
parts.append("<div class=nav>Jump: "+" ".join(f'<a href="#m{m}">{MON[int(m[5:7])]}{m[2:4]}</a>' for m in months)+"</div>")
for m in months:
    rows=sorted(bym[m],key=lambda x:x[0]['date'])
    parts.append(f'<div class="mhead" id="m{m}">{MON[int(m[5:7])]} {m[:4]} — {len(rows)}</div><div class=grid>')
    for e,c in rows: parts.append(f'<div class=cell>{c["svg"]}</div>')
    parts.append('</div>')
parts.append(f'<footer>Nano/Micro/Small 2025-26 PDUFAs (outcomes: bifrost + BPC historical; daily closes: FMP). {built} charted, {skipped} skipped. Informational/educational only — not investment advice.</footer></div></body></html>')
open('PDUFA_smallcap_T15_T5_charts.html','w',encoding='utf-8').write("".join(parts))
print(f"built {built} | decided {len(dec)} (appr {len(appr)} crl {len(crl)}) | upcoming {len(upc)} | skipped {skipped}")
