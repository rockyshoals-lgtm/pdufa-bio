#!/usr/bin/env python3
"""Pass 14b — GENERIC sitewide normalizer (run after seo_pass14_fixups.py).
 - schema: collapse ALL bare-array / multi-block ld+json into one object or @graph (kills NO_TYPE everywhere); dedupe BreadcrumbList.
 - titles -> <=60 (brand-aware, natural-break preferring); metas -> <=155 (word clip).
Idempotent. Leaves already-good pages untouched."""
import re, glob, os, json, html
ROOT='pdufa_site_src'
def ldb(h): return list(re.finditer(r'<script type="application/ld\+json">(.*?)</script>', h, re.S))
def clip(s,n=155):
    s=re.sub(r'\s+',' ',s).strip()
    if len(s)<=n: return s
    cut=s[:n]; 
    if ' ' in cut: cut=cut[:cut.rfind(' ')]
    return cut.rstrip(' ,;:-—–·&(')+'.'
def set_title(h,t):
    e=html.escape(t)
    h=re.sub(r'<title>[^<]*</title>','<title>'+e+'</title>',h,count=1)
    h=re.sub(r'(<meta property="og:title" content=")[^"]*(")',lambda m:m.group(1)+e+m.group(2),h,count=1)
    h=re.sub(r'(<meta name="twitter:title" content=")[^"]*(")',lambda m:m.group(1)+e+m.group(2),h,count=1)
    return h
def set_meta(h,m):
    e=html.escape(m,quote=True)
    h=re.sub(r'(<meta name="description" content=")[^"]*(")',lambda mo:mo.group(1)+e+mo.group(2),h,count=1)
    h=re.sub(r'(<meta property="og:description" content=")[^"]*(")',lambda mo:mo.group(1)+e+mo.group(2),h,count=1)
    return h
def short_title(t, path):
    if len(t)<=60: return t
    brand=' | pdufa.bio'; main=t[:-len(brand)].strip() if t.endswith(brand) else t
    budget=60-len(brand)
    if '/condition/' in path:
        m=re.search(r'Upcoming (.*?) Clinical-Trial',main); 
        if m:
            lab=m.group(1).strip()
            for cand in [f"{lab} — FDA Decisions & Readouts 2026", f"{lab} — FDA Decisions 2026", f"{lab} FDA Decisions 2026"]:
                if len(cand)<=budget: return cand+brand
    if len(main)>budget:
        for sep in [' — ',' – ',' - ',' (',': ',' · ']:
            if sep in main:
                c=main.split(sep)[0].strip()
                if 12<=len(c)<=budget: main=c; break
    if len(main)>budget:
        cut=main[:budget]
        if ' ' in cut: cut=cut[:cut.rfind(' ')]
        main=cut.rstrip(' -—–:·,&(')
    return main+brand
def normalize_schema(h):
    blocks=ldb(h)
    if not blocks: return h
    objs=[]
    for b in blocks:
        try: j=json.loads(b.group(1).strip())
        except: return h
        for it in (j if isinstance(j,list) else [j]):
            if isinstance(it,dict) and '@graph' in it: objs+=[x for x in it['@graph'] if isinstance(x,dict)]
            elif isinstance(it,dict): objs.append(it)
    objs=[o for o in objs if o]
    if not objs: return h
    crumbs=[o for o in objs if o.get('@type')=='BreadcrumbList']
    if len(crumbs)>1:
        keep=max(crumbs,key=lambda c:len(c.get('itemListElement',[])))
        objs=[o for o in objs if o.get('@type')!='BreadcrumbList' or o is keep]
    for o in objs: o.pop('@context',None)
    if len(objs)==1: payload=json.dumps({'@context':'https://schema.org',**objs[0]},ensure_ascii=False)
    else: payload=json.dumps({'@context':'https://schema.org','@graph':objs},ensure_ascii=False)
    nb='<script type="application/ld+json">'+payload+'</script>'
    if '</head>' not in h: return h
    h=re.sub(r'<script type="application/ld\+json">.*?</script>','',h,flags=re.S)
    return h.replace('</head>', nb+'</head>',1)

pages=glob.glob(ROOT+'/**/index.html',recursive=True)
ch_s=ch_t=ch_m=0
for f in pages:
    h=open(f,encoding='utf-8').read(); orig=h
    h=normalize_schema(h)
    if h!=orig: ch_s+=1
    mt=re.search(r'<title>([^<]*)</title>',h); t=html.unescape(mt.group(1)) if mt else ''
    if len(t)>60:
        nt=short_title(t,f.replace(os.sep,'/'))
        if nt!=t and len(nt)<=60: h=set_title(h,nt); ch_t+=1
    mm=re.search(r'<meta name="description" content="([^"]*)"',h); md=html.unescape(mm.group(1)) if mm else ''
    if len(md)>155: h=set_meta(h,clip(md,155)); ch_m+=1
    if h!=open(f,encoding='utf-8').read(): open(f,'w',encoding='utf-8').write(h)
print(f"pages={len(pages)} schema_normalized={ch_s} titles_shortened={ch_t} metas_clipped={ch_m}")
