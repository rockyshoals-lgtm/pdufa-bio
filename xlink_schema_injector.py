#!/usr/bin/env python3
"""
pdufa.bio per-event SEO injector (Red Team Pass 13, Task B).

For each pdufa_site_src/pdufa/<TICKER>/index.html:
  1. Inject 2 internal hub links after <!--story-v1--> :
       - condition page /condition/<slug>  (classified from indication text)
       - PDUFA month   /calendar/2026/<month>  (from the FDA decision date)
     Only links targets that exist on disk. Marked <!--xlinks-v1-->. Idempotent.
  2. Append a valid ld+json block (BreadcrumbList Home>Calendar>TICKER + Event).
     Marked <!--ld-v1-->. Idempotent. Does not touch the existing FAQPage block.

Safe to re-run. Reports counts + per-page detail.
"""
import re, glob, os, html, json, sys

ROOT='pdufa_site_src'
PDUFA_DIR=os.path.join(ROOT,'pdufa')
BASE='https://www.pdufa.bio'

MONTHS={'01':'january','02':'february','03':'march','04':'april','05':'may','06':'june',
        '07':'july','08':'august','09':'september','10':'october','11':'november','12':'december'}

CONDITION_LABEL={
 'cancer':'Cancer & Oncology','obesity-metabolic':'Obesity & Metabolic',
 'cns-neurology':'CNS & Neurology','immunology':'Immunology & Inflammation',
 'cardiovascular':'Cardiovascular','rare-disease':'Rare Disease',
 'infectious-disease':'Infectious Disease','hematology':'Hematology',
 'ophthalmology':'Ophthalmology',
}

def classify(s):
    """Map indication text -> condition slug, per Red Team mapping. Eye-first so
    diabetic-macular/eye cases beat the generic 'diabetes->metabolic' rule."""
    s=(s or '').lower()
    H=lambda *ws: any(w in s for w in ws)
    if H('ophthalmic','ophthalmolog','macular','retina','retinal','geographic atrophy',
         'thyroid eye','uveitis','glaucoma','presbyopia','diabetic macular','diabetic retinopath'):
        return 'ophthalmology'
    if H('oncolog','cancer','carcinoma','tumor','tumour','lymphoma','leukemia','leukaemia',
         'myeloma','melanoma','sarcoma','glioma','mastocytosis','myelofibrosis','neoplas',
         'malignan','polycythemia vera'):
        return 'cancer'
    if H('obesity','obese','diabet','metabolic','hyperphosphat','phosphate','dialysis',
         'weight loss','nash','mash','hypercholesterol','dyslipidem','hypertriglycerid','glycogen storage'):
        return 'obesity-metabolic'
    if H('cns','neuro','alzheimer','parkinson','epilep','seizure','migraine','multiple sclerosis',
         'huntington','schizophren','agitation','myasthenia','narcolepsy','amyotrophic','ketamine','alexander disease'):
        return 'cns-neurology'
    if H('immune','immunolog','arthritis','psoriasis','psoriatic','derm','lupus','colitis','crohn',
         'atopic','eczema','vitiligo','inflammat','urticaria','hidradenitis','asthma'):
        return 'immunology'
    if H('cardio','heart','hypertension','atrial','cardiomyopath','coronary','myocard'):
        return 'cardiovascular'
    if H('anemia','anaemia','hemophilia','haemophilia','sickle','thrombocytopenia','iga nephropathy','nephropathy'):
        return 'hematology'
    if H('infection','viral','virus','vaccine','hepatitis','hiv','bacterial','antibiotic','antimicrob',
         'influenza','rsv','cuti','urinary tract infection','respiratory papillomatosis','hpv','contracept'):
        return 'infectious-disease'
    if H('duchenne','dystrophy','rare','orphan','amyloid','muscular','mucopolysacchar','sanfilippo',
         'fibrodysplasia','ossificans','genetic hearing','deficiency','syndrome'):
        return 'rare-disease'
    return None

def extract(h):
    """Return (ticker_display, drug, date, indication_text_for_classify)."""
    mt=re.search(r'<title>([^<]*)</title>', h)
    title=mt.group(1) if mt else ''
    date=None
    md=re.search(r'(\d{4})-(\d{2})-(\d{2})', title)
    if md: date=md.group(0); mm=md.group(2)
    else: mm=None
    # H1: "<TICKER> PDUFA Date: <DRUG>"
    mh=re.search(r'<h1[^>]*>(.*?)</h1>', h, re.S)
    h1=html.unescape(re.sub(r'<[^>]+>','',mh.group(1))).strip() if mh else ''
    tk=h1.split(' PDUFA')[0].strip()
    drug=''
    if 'PDUFA Date:' in h1: drug=h1.split('PDUFA Date:',1)[1].strip()
    # indication: .sub line after h1 + the story-card 'to treat' clause
    m2=re.search(r'</h1><div class="sub">(.*?)</div>', h, re.S)
    sub=html.unescape(re.sub(r'<[^>]+>','',m2.group(1))) if m2 else ''
    ind=sub.split('·')[-1].strip() if '·' in sub else sub
    ms=re.search(r'story-v1-->.*?<div class="card"><div class="sub"[^>]*>(.*?)</div>', h, re.S)
    story=html.unescape(re.sub(r'<[^>]+>','',ms.group(1)))[:300] if ms else ''
    return tk, drug, date, mm, (ind+' || '+story)

def build_xlinks(slug, cond_exists, month, month_exists):
    pill=('font-size:13px;color:#cfe2ff;background:#0c1d38;border:1px solid #2a496f;'
          'border-radius:20px;padding:5px 13px;text-decoration:none;display:inline-block')
    parts=[]
    if slug and cond_exists:
        parts.append('<a href="/condition/%s" style="%s">More %s FDA decisions →</a>'
                     %(slug, pill, html.escape(CONDITION_LABEL[slug])))
    if month and month_exists:
        parts.append('<a href="/calendar/2026/%s" style="%s">All %s 2026 PDUFA dates →</a>'
                     %(month, pill, month.capitalize()))
    if not parts: return ''
    return ('<!--xlinks-v1--><div style="display:flex;flex-wrap:wrap;gap:8px;margin:10px 0 4px">'
            +''.join(parts)+'</div>')

def build_ld(tk, drug, date):
    name=(drug+' FDA decision').strip() if drug else (tk+' FDA decision')
    crumb={"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[
        {"@type":"ListItem","position":1,"name":"Home","item":BASE+"/"},
        {"@type":"ListItem","position":2,"name":"PDUFA Calendar","item":BASE+"/calendar"},
        {"@type":"ListItem","position":3,"name":tk,"item":BASE+"/pdufa/"+tk},
    ]}
    event={"@context":"https://schema.org","@type":"Event","name":name,
        "description":(name+" — FDA PDUFA target decision date. Facts only, not advice."),
        "eventStatus":"https://schema.org/EventScheduled",
        "eventAttendanceMode":"https://schema.org/OnlineEventAttendanceMode",
        "organizer":{"@type":"Organization","name":"U.S. Food and Drug Administration","url":"https://www.fda.gov"},
        "location":{"@type":"VirtualLocation","url":BASE+"/pdufa/"+tk},
        "url":BASE+"/pdufa/"+tk}
    if date:
        event["startDate"]=date; event["endDate"]=date
    payload=json.dumps([crumb,event], ensure_ascii=False)
    return '<!--ld-v1--><script type="application/ld+json">'+payload+'</script>'

def main():
    pages=sorted(glob.glob(os.path.join(PDUFA_DIR,'*','index.html')))
    n_xlinks=0; n_ld=0; skipped=[]; bad_target=[]; detail={}
    for f in pages:
        tk_dir=f.split(os.sep)[-2]
        h=open(f,encoding='utf-8').read(); orig=h
        tk, drug, date, mm, ind = extract(h)
        slug=classify(ind)
        cond_exists = bool(slug) and os.path.isdir(os.path.join(ROOT,'condition',slug))
        month = MONTHS.get(mm) if mm else None
        month_exists = bool(month) and os.path.isdir(os.path.join(ROOT,'calendar','2026',month))
        # validate on-disk for any link we intend to emit
        if slug and not cond_exists: bad_target.append((tk_dir,'/condition/'+slug))
        if month and not month_exists: bad_target.append((tk_dir,'/calendar/2026/'+month))

        # 1) xlinks (idempotent)
        if '<!--xlinks-v1-->' not in h:
            block=build_xlinks(slug, cond_exists, month, month_exists)
            if block:
                h=h.replace('<!--story-v1-->','<!--story-v1-->'+block,1)
                n_xlinks+=1
        if not (slug and cond_exists):
            skipped.append((tk_dir, ind.split('||')[0].strip()[:50]))

        # 2) ld (idempotent)
        if '<!--ld-v1-->' not in h:
            ld=build_ld(tk, drug, date)
            h=h.replace('</head>', ld+'</head>', 1)
            n_ld+=1

        if h!=orig:
            open(f,'w',encoding='utf-8').write(h)
        detail[tk_dir]=('/condition/'+slug if (slug and cond_exists) else 'SKIP',
                        '/calendar/2026/'+month if month_exists else 'SKIP')

    print("pages processed:", len(pages))
    print("xlinks injected:", n_xlinks)
    print("ld blocks appended:", n_ld)
    print("skipped (no condition link):", len(skipped))
    for t,i in skipped: print("   SKIP", t, "::", i)
    print("on-disk-missing targets attempted (should be 0):", len(bad_target), bad_target)
    for t in ['UNCY','VRDN','CELC','VNDA']:
        if t in detail: print("SPOT", t, detail[t])
    return detail

if __name__=='__main__':
    main()
