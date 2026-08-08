#!/usr/bin/env python3
"""Red Team Pass 14 SEO fixups — post-processor over final pdufa_site_src files.
Run as the LAST build step (after build_seo_pages + xlink_schema_injector).
Idempotent. Fixes:
 - per-event: consolidate ld+json into ONE @graph (BreadcrumbList+FAQPage+Event) -> kills NO_TYPE
 - titles <=60 (keyword-front-loaded), meta descriptions <=155, sitewide
 - /coverage: add Dataset schema ; months: add BreadcrumbList + ItemList
"""
import re, glob, os, json, html

ROOT='pdufa_site_src'; BASE='https://www.pdufa.bio'
MON=['','Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
MONF=['','January','February','March','April','May','June','July','August','September','October','November','December']

def fmt(iso):
    if not iso: return ''
    y,m,d=iso.split('-'); return f"{MON[int(m)]} {int(d)} {y}"
def clip(s,n=155):
    s=re.sub(r'\s+',' ',s).strip()
    if len(s)<=n: return s
    cut=s[:n]; 
    if ' ' in cut: cut=cut[:cut.rfind(' ')]
    return cut.rstrip(' ,;:-—')+'.'
def set_title(h,t):
    e=html.escape(t)
    for pat in [r'<title>[^<]*</title>', r'(<meta property="og:title" content=")[^"]*(")', r'(<meta name="twitter:title" content=")[^"]*(")']:
        if pat.startswith('<title'):
            h=re.sub(pat, '<title>'+e+'</title>', h, count=1)
        else:
            h=re.sub(pat, lambda m:m.group(1)+e+m.group(2), h, count=1)
    return h
def set_meta(h,m):
    e=html.escape(m,quote=True)
    for pat in [r'(<meta name="description" content=")[^"]*(")', r'(<meta property="og:description" content=")[^"]*(")']:
        h=re.sub(pat, lambda mo:mo.group(1)+e+mo.group(2), h, count=1)
    return h
def ld_blocks(h): return list(re.finditer(r'<script type="application/ld\+json">(.*?)</script>', h, re.S))

def consolidate_event_schema(h, tk):
    faq=event=crumb=None
    for b in ld_blocks(h):
        try: arr=json.loads(b.group(1).strip())
        except: continue
        items=arr if isinstance(arr,list) else [arr]
        flat=[]
        for it in items:
            if isinstance(it,dict) and '@graph' in it: flat+=it['@graph']
            else: flat.append(it)
        for it in flat:
            ty=it.get('@type') if isinstance(it,dict) else None
            if ty=='FAQPage': faq=it
            elif ty=='Event': event=it
            elif ty=='BreadcrumbList':
                if crumb is None or len(it.get('itemListElement',[]))>=len(crumb.get('itemListElement',[])): crumb=it
    if crumb is None:
        crumb={"@type":"BreadcrumbList","itemListElement":[
            {"@type":"ListItem","position":1,"name":"Home","item":BASE+"/"},
            {"@type":"ListItem","position":2,"name":"PDUFA Calendar","item":BASE+"/calendar"},
            {"@type":"ListItem","position":3,"name":tk,"item":BASE+"/pdufa/"+tk}]}
    for o in (faq,event,crumb):
        if isinstance(o,dict): o.pop('@context',None)
    graph=[x for x in (crumb,faq,event) if x]
    payload=json.dumps({"@context":"https://schema.org","@graph":graph}, ensure_ascii=False)
    newblock='<script type="application/ld+json">'+payload+'</script>'
    h=h.replace('<!--ld-v1-->','')
    h=re.sub(r'<script type="application/ld\+json">.*?</script>','',h,flags=re.S)
    h=h.replace('</head>', newblock+'</head>',1)
    return h

def do_event(f):
    h=open(f,encoding='utf-8').read(); orig=h
    mt=re.search(r'<title>([^<]*)</title>',h); t=html.unescape(mt.group(1)) if mt else ''
    tk=t.split(' PDUFA')[0].strip()
    md=re.search(r'(\d{4}-\d{2}-\d{2})',t); date=md.group(1) if md else None
    m=re.search(r'PDUFA Date:\s*(.*?)\s*[—-]\s*FDA Decision', t); drug=m.group(1).strip() if m else ''
    ab=re.search(r'\(([A-Za-z0-9-]{2,9})\)', drug)
    short=ab.group(1) if ab else (drug.split('(')[0].strip() or tk)
    nt=f"{tk} PDUFA date — {short}, {fmt(date)} | pdufa.bio"
    if len(nt)>60: nt=f"{tk} PDUFA date — {short}, {fmt(date)}"
    if len(nt)>60: nt=f"{tk} PDUFA — {short}, {fmt(date)}"
    if len(nt)>60: nt=nt[:59].rstrip()+'…'
    om=re.search(r'<meta name="description" content="([^"]*)"',h); od=html.unescape(om.group(1)) if om else ''
    mi=re.search(r' in ([^.]+?)\.', od); ind=mi.group(1).strip() if mi else ''
    nm=f"{tk}'s FDA PDUFA date is {fmt(date)} for {drug}"+(f" ({ind})" if ind else "")+". See the T-120 run-up, cap-tier base rates, and the primary source."
    h=set_title(h,nt); h=set_meta(h,clip(nm))
    h=consolidate_event_schema(h, tk)
    if h!=orig: open(f,'w',encoding='utf-8').write(h)
    return nt,len(nt)

def add_block_before_head(h, obj):
    blk='<script type="application/ld+json">'+json.dumps(obj,ensure_ascii=False)+'</script>'
    return h.replace('</head>', blk+'</head>',1)

def do_home(f):
    if not os.path.exists(f): return
    h=open(f,encoding='utf-8').read()
    h=set_title(h,"2026 FDA PDUFA Calendar — Dates & Run-up History | pdufa.bio")
    h=set_meta(h,clip("Every upcoming FDA PDUFA decision with the facts to weigh it: live price, options-implied move, run-up history by market cap, cohort base rates, and primary sources."))
    open(f,'w',encoding='utf-8').write(h)

def do_coverage(f):
    if not os.path.exists(f): return
    h=open(f,encoding='utf-8').read()
    h=set_title(h,"Data Coverage & Integrity | pdufa.bio")
    h=set_meta(h,clip("How complete and fresh pdufa.bio is: catalysts tracked, % with primary-source links, PDUFA recall, date-precision, and explicit limitations."))
    if '"@type": "Dataset"' not in h and '"@type":"Dataset"' not in h:
        ds={"@context":"https://schema.org","@type":"Dataset","name":"pdufa.bio FDA catalyst coverage",
            "description":"Coverage and data-integrity summary for pdufa.bio: FDA PDUFA dates, CRLs and clinical readouts tracked, with primary-source links and date-precision tags.",
            "creator":{"@type":"Organization","name":"pdufa.bio","url":BASE},
            "license":"https://creativecommons.org/licenses/by/4.0/","temporalCoverage":"2024/2026",
            "isAccessibleForFree":True,"url":BASE+"/coverage"}
        h=add_block_before_head(h,ds)
    open(f,'w',encoding='utf-8').write(h)

def do_month(f):
    h=open(f,encoding='utf-8').read(); orig=h
    mm=re.search(r'/calendar/2026/([a-z]+)/', f.replace(os.sep,'/'))
    name=mm.group(1).capitalize() if mm else ''
    h=set_title(h,f"{name} 2026 FDA PDUFA Calendar | pdufa.bio")
    h=set_meta(h,clip(f"Every FDA PDUFA decision scheduled for {name} 2026: company, ticker, drug and indication, each linked to its primary source."))
    if '"ItemList"' not in h:
        tickers=[]
        for mt in re.finditer(r'href="/pdufa/([A-Za-z0-9-]+)"', h):
            if mt.group(1) not in tickers: tickers.append(mt.group(1))
        if tickers:
            items=[{"@type":"ListItem","position":i+1,"url":BASE+"/pdufa/"+t} for i,t in enumerate(tickers)]
            il={"@context":"https://schema.org","@type":"ItemList","name":f"{name} 2026 FDA PDUFA dates","numberOfItems":len(items),"itemListElement":items}
            h=add_block_before_head(h,il)
        bc={"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[
            {"@type":"ListItem","position":1,"name":"Home","item":BASE+"/"},
            {"@type":"ListItem","position":2,"name":"PDUFA Calendar","item":BASE+"/calendar"},
            {"@type":"ListItem","position":3,"name":f"{name} 2026","item":BASE+"/calendar/2026/"+(mm.group(1) if mm else '')}]}
        h=add_block_before_head(h,bc)
    if h!=orig: open(f,'w',encoding='utf-8').write(h)

def do_condition(f):
    h=open(f,encoding='utf-8').read(); orig=h
    mt=re.search(r'<title>([^<]*)</title>',h); t=html.unescape(mt.group(1)) if mt else ''
    m=re.search(r'Upcoming (.*?) Clinical-Trial Readouts',t); lab=m.group(1).strip() if m else t.split('|')[0].strip()
    nt=f"{lab} FDA Decisions & Readouts 2026 | pdufa.bio"
    if len(nt)<=60: h=set_title(h,nt)
    if h!=orig: open(f,'w',encoding='utf-8').write(h)

# ---- run ----
ev=sorted(glob.glob(ROOT+'/pdufa/*/index.html'))
maxlen=0; over=[]
for f in ev:
    nt,L=do_event(f); maxlen=max(maxlen,L)
    if L>60: over.append((f.split(os.sep)[-2],L))
do_home(ROOT+'/index.html')
do_coverage(ROOT+'/coverage/index.html')
months=sorted(glob.glob(ROOT+'/calendar/2026/*/index.html'))
for f in months: do_month(f)
conds=sorted(glob.glob(ROOT+'/condition/*/index.html'))
for f in conds: do_condition(f)
print(f"per-event processed: {len(ev)}  max title len: {maxlen}  over60: {len(over)} {over[:6]}")
print(f"months processed: {len(months)}  conditions: {len(conds)}")
print("done")
