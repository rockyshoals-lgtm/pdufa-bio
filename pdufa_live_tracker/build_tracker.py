#!/usr/bin/env python3
import csv, json, os, datetime, collections
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt, numpy as np
BASE=os.path.dirname(os.path.abspath(__file__))
LOG=os.path.join(BASE,'daily_log.csv')
rows=list(csv.DictReader(open(LOG))) if os.path.exists(LOG) else []
if not rows:
    open(os.path.join(BASE,'tracker.html'),'w').write("<h1>No data yet</h1>"); raise SystemExit
# latest snapshot per ticker + series
by_tk=collections.defaultdict(list)
for r in rows: by_tk[r['ticker']].append(r)
latest={}; series={}
for tk,rs in by_tk.items():
    rs.sort(key=lambda x:x['ts_utc']); latest[tk]=rs[-1]
    series[tk]=[(r['ts_utc'], float(r['runup_idx']) if r['runup_idx'] else None) for r in rs]
cur=[latest[tk] for tk in latest]
cur=[c for c in cur if c['days_to_pdufa'] and int(c['days_to_pdufa'])>=0]
cur.sort(key=lambda c:int(c['days_to_pdufa']))
BG='#02060d'; INK='#f2f6fc'; GRID='#1a3358'; GOLD='#e3ba5e'; GREEN='#5fd07a'; RED='#ff8f6b'
# chart: runup_idx vs days_to_pdufa (current positions)
fig,ax=plt.subplots(figsize=(11,6),dpi=120); fig.patch.set_facecolor(BG); ax.set_facecolor(BG)
for s in ax.spines.values(): s.set_color(GRID)
ax.tick_params(colors=INK,labelsize=9); ax.grid(True,color=GRID,alpha=.35,lw=.6); ax.axhline(100,color=INK,lw=.8,alpha=.5)
xs=[int(c['days_to_pdufa']) for c in cur]; ys=[float(c['runup_idx']) if c['runup_idx'] else 100 for c in cur]
cols=[GREEN if y>=100 else RED for y in ys]
ax.scatter(xs,ys,c=cols,s=45,zorder=5,edgecolor=BG,lw=.6)
for c in cur:
    y=float(c['runup_idx']) if c['runup_idx'] else 100
    ax.annotate(f"{c['ticker']}",(int(c['days_to_pdufa']),y),color=INK,fontsize=8,xytext=(4,3),textcoords='offset points')
ax.invert_xaxis(); ax.set_xlabel("Business days to PDUFA (0 = decision)",color=INK)
ax.set_ylabel("Run-up index (T-120 = 100)",color=INK)
ax.set_title("Current PDUFAs — live run-up positions",color=INK,fontsize=13,pad=8)
plt.tight_layout(); plt.savefig(os.path.join(BASE,'tracker_positions.png'),facecolor=BG); plt.close()
# sparkline SVG per ticker
def spark(tk):
    pts=[v for _,v in series[tk] if v is not None]
    if len(pts)<2: return ''
    lo,hi=min(pts),max(pts); rng=hi-lo or 1; W,H=90,22
    xs=[i/(len(pts)-1)*W for i in range(len(pts))]; ys=[H-(v-lo)/rng*H for v in pts]
    d=' '.join(f"{x:.1f},{y:.1f}" for x,y in zip(xs,ys))
    col=GREEN if pts[-1]>=pts[0] else RED
    return f'<svg width="{W}" height="{H}"><polyline points="{d}" fill="none" stroke="{col}" stroke-width="1.5"/></svg>'
def cls(v):
    try: return 'pos' if float(v)>=100 else 'neg'
    except: return ''
tbody=""
for c in cur:
    idx=c['runup_idx']; chg=c['chg_pct']
    chgc='pos' if (chg and float(chg)>=0) else 'neg'
    tbody+=(f"<tr><td><b>{c['ticker']}</b></td><td class='dr'>{c['pdufa_date']}</td>"
            f"<td>{c['days_to_pdufa']}</td><td>{c.get('price','')}</td>"
            f"<td class='{chgc}'>{('+' if chg and float(chg)>=0 else '')}{chg}%</td>"
            f"<td class='{cls(idx)}'>{idx}</td><td>{spark(c['ticker'])}</td>"
            f"<td class='dg'>{c['ticker'] and next((r['drug'] for r in by_tk[c['ticker']] if 'drug' in r), '')}</td></tr>")
n_snap=len({r['ts_utc'] for r in rows}); last=rows[-1]['ts_utc']
html=f"""<!doctype html><meta charset=utf-8><title>Current PDUFA Tracker — live</title>
<style>body{{background:{BG};color:{INK};font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;margin:0;padding:26px 20px 60px;max-width:1000px;margin:auto}}
h1{{font-size:24px;margin:0 0 4px}}h1 b{{color:{GOLD}}}.sub{{color:#a7bcd9;font-size:13px;margin-bottom:18px}}
img{{width:100%;border:1px solid {GRID};border-radius:12px;margin:8px 0 20px}}
table{{width:100%;border-collapse:collapse;font-size:13px}}th,td{{padding:7px 9px;border-bottom:1px solid {GRID};text-align:right}}
th:first-child,td:first-child,td.dr,td.dg{{text-align:left}}th{{color:{GOLD};font-size:11px;letter-spacing:.4px}}
td.pos{{color:{GREEN}}}td.neg{{color:{RED}}}td.dg{{color:#94a9c9;max-width:230px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}</style>
<h1>Current PDUFA <b>tracker</b> — live</h1>
<div class=sub>{len(cur)} in-flight PDUFAs · {n_snap} snapshots logged · last update {last} UTC · run-up indexed to T-120=100 · private / for research, not advice</div>
<img src="tracker_positions.png" alt="current runup positions">
<table><tr><th>Ticker</th><th>PDUFA</th><th>Days</th><th>Price</th><th>Day</th><th>Run-up idx</th><th>Trend</th><th>Drug</th></tr>{tbody}</table>"""
open(os.path.join(BASE,'tracker.html'),'w').write(html)
print(f"tracker rebuilt: {len(cur)} PDUFAs, {n_snap} snapshots")
