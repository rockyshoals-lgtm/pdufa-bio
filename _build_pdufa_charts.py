# -*- coding: utf-8 -*-
"""Build T-120 -> T+30 small-multiple charts for all 2025-26 PDUFAs, with dated axis + PDUFA marker."""
import json, datetime as dt
ev=json.load(open('_chart_events.json'))
px=json.load(open('_chart_pxcache.json'))
MON=["","Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

def series(tk):
    d=px.get(tk) or {}
    return sorted(d.items())  # [(date,close)]

def window(tk, pdate, pre=120, post=30):
    s=series(tk)
    if len(s)<30: return None
    dates=[x[0] for x in s]
    # index of last trading day <= pdufa date
    idx=None
    for i,dd in enumerate(dates):
        if dd<=pdate: idx=i
        else: break
    if idx is None: return None
    lo=max(0,idx-pre); hi=min(len(s),idx+post+1)
    w=s[lo:hi]; pivot=idx-lo
    return w, pivot

def chart(e):
    r=window(e['ticker'], e['date'])
    if not r: return None
    w,piv=r
    if len(w)<20: return None
    prices=[p for _,p in w]; dates=[d for d,_ in w]
    W,H=360,168; padL,padR,padT,padB=36,8,30,20
    x0,x1,y0,y1=padL,W-padR,padT,H-padB
    lo,hi=min(prices),max(prices); sp=(hi-lo) or 1; lo-=sp*0.08; hi+=sp*0.08; rng=(hi-lo) or 1
    n=len(w)
    X=lambda i:x0+i/(n-1)*(x1-x0)
    Y=lambda v:y1-(v-lo)/rng*(y1-y0)
    pts=" ".join(f"{X(i):.1f},{Y(p):.1f}" for i,p in enumerate(prices))
    appr = e['outcome'].upper().startswith('APPROV')
    mc = "#5fd07a" if appr else "#ff7a7a"
    xp=X(piv)
    # post-event shade
    shade=f'<rect x="{xp:.1f}" y="{y0}" width="{x1-xp:.1f}" height="{y1-y0}" fill="{mc}" opacity="0.06"/>'
    # pdufa vertical
    vline=f'<line x1="{xp:.1f}" y1="{y0}" x2="{xp:.1f}" y2="{y1}" stroke="{mc}" stroke-width="1.3" stroke-dasharray="3,2"/>'
    # decision-day dot
    dot=f'<circle cx="{xp:.1f}" cy="{Y(prices[piv]):.1f}" r="2.6" fill="{mc}"/>'
    # y labels (min/max)
    ylab=(f'<text x="{x0-3:.0f}" y="{Y(max(prices))+3:.0f}" fill="#7e95b6" font-size="8.5" text-anchor="end">${max(prices):.2f}</text>'
          f'<text x="{x0-3:.0f}" y="{Y(min(prices))+3:.0f}" fill="#7e95b6" font-size="8.5" text-anchor="end">${min(prices):.2f}</text>')
    # x date labels: start, pdufa, end
    def dl(i,txt,anchor,col="#7e95b6"):
        return f'<text x="{X(i):.0f}" y="{H-7:.0f}" fill="{col}" font-size="8.5" text-anchor="{anchor}">{txt}</text>'
    def shortd(d): p=d.split('-'); return f"{MON[int(p[1])]}{p[2]}"
    xlabs=dl(0,shortd(dates[0]),"start")+dl(piv,shortd(dates[piv]),"middle",mc)+dl(n-1,shortd(dates[-1]),"end")
    # runup / post numbers
    p120=prices[0]; p0=prices[piv]; pend=prices[-1]
    runup=(p0/p120-1)*100; post=(pend/p0-1)*100
    dm = e.get('dmove')
    dmtxt = (f"  d1 {dm:+.0f}%" if dm is not None else "")
    title=f"{e['ticker']} · {e['asset'][:24]}"
    sub=f"PDUFA {e['date']} · {'APPR' if appr else 'CRL'}{dmtxt} · runup {runup:+.0f}% · post30 {post:+.0f}%"
    svg=(f'<svg viewBox="0 0 {W} {H}" class="mc">'
         f'<text x="4" y="12" fill="#f2f6fc" font-size="11" font-weight="700">{title}</text>'
         f'<text x="4" y="23" fill="{mc}" font-size="9">{sub}</text>'
         f'{shade}<polyline points="{pts}" fill="none" stroke="#e3ba5e" stroke-width="1.4"/>{vline}{dot}{ylab}{xlabs}</svg>')
    return dict(svg=svg, runup=runup, post=post, appr=appr)

# group by month
bym={}; built=0; skipped=[]
for e in sorted(ev,key=lambda x:x['date']):
    c=chart(e)
    if not c: skipped.append(e['ticker']+":"+e['date']); continue
    k=e['date'][:7]; bym.setdefault(k,[]).append((e,c)); built+=1

# aggregate
allc=[c for v in bym.values() for _,c in v]
appr=[c for c in allc if c['appr']]; crl=[c for c in allc if not c['appr']]
import statistics as st
def med(xs,key):
    v=[x[key] for x in xs]; return st.median(v) if v else 0

parts=[]
parts.append(f"""<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>2025–26 PDUFA price paths · T-120 → T+30</title><style>
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
.legend{{font-size:12px;color:#a7bcd9;margin:6px 0 2px}}.g{{color:#5fd07a}}.r{{color:#ff7a7a}}.gold{{color:#e3ba5e}}
footer{{margin-top:30px;font-size:11px;color:#5f7characters;color:#637characters}}</style></head><body><div class=wrap>
<h1>2025–26 FDA <b>PDUFA price paths</b> — T-120 → T+30</h1>
<div class=sub>Every decided 2025–26 PDUFA. Gold line = daily close; dashed vertical marks the <span class=gold>PDUFA decision date</span> (<span class=g>green = approval</span>, <span class=r>red = CRL</span>); shaded band = the 30 days after. Historical data, not advice.</div>
<div class=kpis>
<div class=kpi><b>{built}</b> events charted</div>
<div class=kpi><b class=g>{len(appr)}</b> approvals · median post-30 <b class=g>{med(appr,'post'):+.0f}%</b></div>
<div class=kpi><b class=r>{len(crl)}</b> CRLs · median post-30 <b class=r>{med(crl,'post'):+.0f}%</b></div>
<div class=kpi>median runup (all) <b>{med(allc,'runup'):+.0f}%</b></div>
</div>""")
# month nav
months=sorted(bym)
parts.append("<div class=nav>Jump: "+" ".join(f'<a href="#m{m}">{MON[int(m[5:7])]} {m[:4]}</a>' for m in months)+"</div>")
for m in months:
    rows=sorted(bym[m],key=lambda x:x[0]['date'])
    parts.append(f'<div class="mhead" id="m{m}">{MON[int(m[5:7])]} {m[:4]} — {len(rows)} decisions</div><div class=grid>')
    for e,c in rows:
        parts.append(f'<div class=cell>{c["svg"]}</div>')
    parts.append('</div>')
parts.append(f'<footer>Source: pdufa.bio internal cohort (FMP daily closes). {built} of {len(ev)} events charted ({len(skipped)} skipped for insufficient price history). Informational/educational only — not investment advice.</footer></div></body></html>')
html="".join(parts).replace("#5f7characters;color:#637characters","#637a99")
open('PDUFA_2025-26_charts_T120_T30.html','w',encoding='utf-8').write(html)
print(f"built {built} charts | skipped {len(skipped)} | approvals {len(appr)} crl {len(crl)}")
print("skipped:", ", ".join(skipped[:20]))
