import io, sys, py_compile

P = "catalyst_crawler.py"
src = io.open(P, encoding="utf-8").read()
orig = src

edits = []

# R1 — qa_diff: add a drug-keyed recall (not deflated by month-precision differences)
edits.append((
'''    def keyset(df, types=None):
        d=df.copy()
        if types: d=d[d.catalyst_type.astype(str).str.contains(types,case=False,na=False)]
        return set((norm_t(r.ticker), str(r.catalyst_date)[:7]) for _,r in d.iterrows() if pd.notna(r.catalyst_date) and pd.notna(r.ticker))
    p,b=keyset(primary,label_filter),keyset(bpc,label_filter)
    return {"overlap":len(p&b),"in_primary_not_bpc":sorted([f"{t}:{d}" for t,d in (p-b)])[:60],
            "in_bpc_not_primary":sorted([f"{t}:{d}" for t,d in (b-p)])[:60],
            "recall_vs_bpc":round(len(p&b)/max(1,len(b)),3)}''',
'''    def keyset(df, types=None):
        d=df.copy()
        if types: d=d[d.catalyst_type.astype(str).str.contains(types,case=False,na=False)]
        return set((norm_t(r.ticker), str(r.catalyst_date)[:7]) for _,r in d.iterrows() if pd.notna(r.catalyst_date) and pd.notna(r.ticker))
    def drugset(df, types=None):
        d=df.copy()
        if types: d=d[d.catalyst_type.astype(str).str.contains(types,case=False,na=False)]
        s=set()
        for _,r in d.iterrows():
            dr=_drug_root(r.get("drug"))
            if pd.notna(r.ticker) and dr: s.add((norm_t(r.ticker), dr))
        return s
    p,b=keyset(primary,label_filter),keyset(bpc,label_filter)
    pdr,bdr=drugset(primary,label_filter),drugset(bpc,label_filter)
    return {"overlap":len(p&b),"in_primary_not_bpc":sorted([f"{t}:{d}" for t,d in (p-b)])[:60],
            "in_bpc_not_primary":sorted([f"{t}:{d}" for t,d in (b-p)])[:60],
            "recall_vs_bpc":round(len(p&b)/max(1,len(b)),3),
            "recall_vs_bpc_bydrug":round(len(pdr&bdr)/max(1,len(bdr)),3)}'''
))

# R2 — add the earnings-transcript miner (mega-cap self-completion)
edits.append((
'''    print(f"  [fmp_press] scanned {nscan} tickers -> {len(out)} PDUFA/AdComm/Device dates from press releases")
    return out

def enrich_fmp(df, key):''',
'''    print(f"  [fmp_press] scanned {nscan} tickers -> {len(out)} PDUFA/AdComm/Device dates from press releases")
    return out
def fmp_transcript_catalysts(tickers, key, ua=None, max_per=3):
    """Mine recent earnings-call transcripts for PDUFA/AdComm/device dates that mega-caps disclose in
    pipeline sections rather than a standalone 8-K (LLY/MRK/PFE/BMY/GILD/REGN/IONS/VRTX...). Each row keeps
    its FMP transcript URL as provenance. Opt-in (--transcripts) because transcripts are long = slower."""
    out=[]; nscan=0
    for tk in tickers:
        rows=_fmp("https://financialmodelingprep.com/stable/earning-call-transcript",{"symbol":tk,"limit":max_per},key)
        if not isinstance(rows,list) or not rows:
            rows=_fmp(f"https://financialmodelingprep.com/api/v3/earning_call_transcript/{tk}",{"limit":max_per},key)
        if not isinstance(rows,list): continue
        nscan+=1
        for x in rows:
            if not isinstance(x,dict): continue
            txt=clean_html(str(x.get("content","") or x.get("transcript","") or ""))
            if not txt: continue
            yr=x.get("year") or ""; q=x.get("quarter") or ""
            url=f"https://site.financialmodelingprep.com/earnings-transcript/{tk}"+(f"?year={yr}&quarter={q}" if yr else "")
            out+=_scan_catalyst_text(tk, txt, url, "fmp_transcript", conf_adj=0.15)
    print(f"  [fmp_transcript] scanned {nscan} tickers -> {len(out)} catalyst dates from earnings transcripts (mega-cap fill)")
    return out

def enrich_fmp(df, key):'''
))

# R3 — register the --transcripts flag
edits.append((
'''    ap.add_argument("--discover",action="store_true",help="Layer 2: run SEC EDGAR full-text discovery across ALL filers (not just the universe) to catch off-list PDUFA/CRL/BLA catalysts")''',
'''    ap.add_argument("--discover",action="store_true",help="Layer 2: run SEC EDGAR full-text discovery across ALL filers (not just the universe) to catch off-list PDUFA/CRL/BLA catalysts")
    ap.add_argument("--transcripts",action="store_true",help="Layer 2b: mine FMP earnings-call transcripts for mega-cap PDUFA/AdComm dates that don't appear in a standalone 8-K (needs FMP_API_KEY; slower)")'''
))

# R4 — wire the transcript miner into main()
edits.append((
'''        print("FMP general news (foreign/mega-cap + device fill — facts cited to article URL) ...")
        recs+=_src("fmp_news", fmp_news_catalysts, tickers, os.environ["FMP_API_KEY"], args.ua)''',
'''        print("FMP general news (foreign/mega-cap + device fill — facts cited to article URL) ...")
        recs+=_src("fmp_news", fmp_news_catalysts, tickers, os.environ["FMP_API_KEY"], args.ua)
        if getattr(args,"transcripts",False):
            print("FMP earnings-call transcripts (mega-cap pipeline disclosures SEC-only misses) ...")
            recs+=_src("fmp_transcript", fmp_transcript_catalysts, tickers, os.environ["FMP_API_KEY"], args.ua)'''
))

# R5 — emit a paste-ready seed_candidates.csv alongside coverage_gaps.csv
edits.append((
'''            if grows:
                safe_to_csv(pd.DataFrame(grows).drop_duplicates(), os.path.join(args.out,"coverage_gaps.csv"))
                print(f"  [coverage] {len(grows)} BPC PDUFA-ish events not independently sourced -> coverage_gaps.csv")''',
'''            if grows:
                safe_to_csv(pd.DataFrame(grows).drop_duplicates(), os.path.join(args.out,"coverage_gaps.csv"))
                print(f"  [coverage] {len(grows)} BPC PDUFA-ish events not independently sourced -> coverage_gaps.csv")
                _seedrows=[]
                for g in grows:
                    _d=str(g.get("catalyst_date") or "")
                    _prec="day" if len(_d)==10 else ("month" if len(_d)==7 else "year")
                    _seedrows.append({"ticker":g.get("ticker"),"company":g.get("company") or "","catalyst_type":"PDUFA",
                        "catalyst_date":g.get("catalyst_date"),"date_precision":_prec,"drug":g.get("drug") or "",
                        "indication":g.get("indication") or "","source":"curated_pharma","source_url":"",
                        "confidence":0.6,"redistribute":True})
                safe_to_csv(pd.DataFrame(_seedrows).drop_duplicates(), os.path.join(args.out,"seed_candidates.csv"))
                print("  [coverage] paste-ready -> seed_candidates.csv (add a source_url per row, append to bigpharma_pdufa_seed.csv)")'''
))

for i,(old,new) in enumerate(edits,1):
    c = src.count(old)
    if c != 1:
        print(f"R{i}: EXPECTED 1 match, found {c} -> ABORT (no write)"); sys.exit(1)
    src = src.replace(old, new)

io.open(P, "w", encoding="utf-8").write(src)
try:
    py_compile.compile(P, doraise=True)
    print(f"ALL 5 EDITS APPLIED + COMPILES OK ✅  ({len(src.splitlines())} lines, was {len(orig.splitlines())})")
except py_compile.PyCompileError as e:
    print("COMPILE FAILED after patch:", e); sys.exit(2)
