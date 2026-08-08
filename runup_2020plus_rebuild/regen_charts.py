import json,re,os,glob,datetime
import numpy as np
c=json.load(open(os.path.join(os.path.dirname(__file__),'t120_2020plus.json')))
def bdate(pdufa, off):
    d=np.busday_offset(pdufa, int(off), roll='backward'); return datetime.date.fromisoformat(str(d))
def fmt(d): return d.strftime('%-m/%-d/%y')
def build_svg(path, pdufa_date):
    vals={int(o):v for o,v in path.items() if v is not None}
    if len(vals)<10: return None
    offs=sorted(vals); o0,o1=offs[0],offs[-1]
    pre={o:vals[o] for o in offs if o<=-1}
    if len(pre)<5: pre=vals
    hi=max(pre.values()); lo=min(pre.values())
    ho=[o for o in offs if o in pre and vals[o]==hi][0]; lo_o=[o for o in offs if o in pre and vals[o]==lo][0]
    pd=datetime.date.fromisoformat(pdufa_date)
    X0,X1,Y0,Y1=14,628,12,150
    def X(o): return X0+(o-o0)/(o1-o0 or 1)*(X1-X0)
    def Y(v): return Y1-(v-lo)/((hi-lo) or 1)*(Y1-Y0)
    pts=' '.join(f"{X(o):.1f},{Y(vals[o]):.1f}" for o in offs)
    xp=X(0) if o0<=0<=o1 else None
    parts=[f'<svg viewBox="0 0 640 190" role="img" style="width:100%;display:block;aspect-ratio:640/190;background:#071528;border:1px solid #1a3358;border-radius:10px">']
    # PDUFA vertical marker
    if xp is not None:
        parts.append(f'<line x1="{xp:.1f}" y1="{Y0}" x2="{xp:.1f}" y2="{Y1}" stroke="#e3ba5e" stroke-width="1" stroke-dasharray="3 3" opacity="0.85"/>')
        lx=min(xp+4,548); parts.append(f'<text x="{lx:.1f}" y="{Y1+27:.0f}" fill="#e3ba5e" font-size="10" font-family="system-ui" text-anchor="end">PDUFA {fmt(pd)}</text>')
    parts.append(f'<polyline points="{pts}" fill="none" stroke="#7aa8ff" stroke-width="1.6"/>')
    # high / low dots + labels
    parts.append(f'<circle cx="{X(ho):.1f}" cy="{Y(hi):.1f}" r="2.6" fill="#5fd07a"/><text x="{X(ho):.1f}" y="{max(Y(hi)-5,10):.1f}" fill="#5fd07a" font-size="10" font-family="system-ui" text-anchor="middle">${hi:g}</text>')
    parts.append(f'<circle cx="{X(lo_o):.1f}" cy="{Y(lo):.1f}" r="2.6" fill="#ff8f6b"/><text x="{max(X(lo_o),26):.1f}" y="{Y(lo)-6:.1f}" fill="#ff8f6b" font-size="10" font-family="system-ui" text-anchor="middle">${lo:g}</text>')
    # start date label
    parts.append(f'<text x="{X0}" y="{Y1+14:.0f}" fill="#94a9c9" font-size="10" font-family="system-ui">{fmt(bdate(pdufa_date,o0))}</text>')
    parts.append('</svg>')
    note=(f'<div class="note">Daily close, T-120 ({fmt(bdate(pdufa_date,o0))}) through T+5. '
          f'Run-up high ${hi:g} on {fmt(bdate(pdufa_date,ho))}, low ${lo:g} on {fmt(bdate(pdufa_date,lo_o))} (T-120 to T-1). '
          f'FDA decision {fmt(pd)}. Historical price action, not a forecast.</div>')
    return ''.join(parts)+note

pat=re.compile(r'<svg viewBox="0 0 640 190".*?</svg><div class="note">[^<]*</div>', re.S)
done=0; skip=0
for f in glob.glob('pdufa_site_src/fda-decision/*/index.html'):
    d=os.path.basename(os.path.dirname(f)); m=re.match(r'^(.+)-(\d{4}-\d{2}-\d{2})$',d)
    if not m: skip+=1; continue
    key=f"{m.group(1)}|{m.group(2)}"; rec=c.get(key,{})
    if not rec.get('ok') or not rec['path']: skip+=1; continue
    svg=build_svg(rec['path'], m.group(2))
    if not svg: skip+=1; continue
    s=open(f,encoding='utf-8').read()
    s2,n=pat.subn(svg,s,count=1)
    if n: open(f,'w',encoding='utf-8').write(s2); done+=1
    else: skip+=1
print(f"regenerated {done} fda-decision charts | skipped {skip}")
