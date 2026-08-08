#!/usr/bin/env python3
"""
Phase-readout miner — finds EVERY upcoming clinical readout, not just the ones we asked for.

    python phase_readout_miner.py                          # rest of 2026
    python phase_readout_miner.py --from 2026-07-01 --to 2027-06-30
    python phase_readout_miner.py --phases PHASE2,PHASE3   # default: PHASE1..PHASE3
    python phase_readout_miner.py --listed-only            # drop trials we can't map to a ticker

WHY THIS EXISTS
The old path (catalyst_crawler.ctgov_readouts) had three compounding limits that made it
structurally blind:
  1. SPONSOR-DRIVEN   - it queried CT.gov by sponsor name and needed a hand-maintained list.
                        No list -> zero readouts. A missing name -> a silently missing company.
  2. HARD CAP OF 30   - pageSize=max_studies=30 PER SPONSOR. Big pharma runs hundreds of trials.
  3. NO PAGINATION    - nextPageToken was never read, so 30 was a ceiling, not a page size.

This queries the whole universe by PRIMARY COMPLETION DATE instead, so a company we have never
heard of still shows up. Sponsor-independent, fully paginated, no caps.

HONESTY ABOUT THE DATE
CT.gov primary completion date is NOT the readout date. Topline typically lands weeks to months
AFTER primary completion. We therefore mark CT.gov-derived rows date_basis='ctgov_pcd' with
MONTH precision and a lower confidence, and we prefer a company's OWN stated guidance
("topline expected in 2H 2026") when we can find it. We never present a proxy as a promise.
"""
import argparse, json, os, re, sys, time, datetime as dt
import urllib.request as ur, urllib.parse as up
import pandas as pd


_HERE = os.path.dirname(os.path.abspath(__file__))

# Where the keys actually live. `.env_master` under "Odin Perfection" is the real vault —
# FMP, OpenFDA, ORATS, Polygon, FinBrain. The project-local `.env` is a thin override.
#
# Precedence, strongest first:
#   1. a real environment variable   (CI, or a one-off `set FMP_API_KEY=...`)
#   2. ./.env                        (project-local override)
#   3. Odin Perfection/.env_master   (the vault)
# First writer wins, so nothing below can clobber something above it.
#
# Set ENV_MASTER=<path> to point somewhere else.
ENV_FILES = [
    os.path.join(_HERE, '.env'),
    os.environ.get('ENV_MASTER') or os.path.join(_HERE, 'Odin Perfection', '.env_master'),
]

def _load_dotenv(paths=ENV_FILES):
    """Load key=value files into os.environ without ever overwriting what's already set.

    Without this, every keyed code path in the repo does
        os.environ.get("FMP_API_KEY")  ->  None  ->  skip the source, say nothing
    so a perfectly good key sits in a file while the newswire leg quietly never runs.
    A missing key must be a visible absence, not a silent one — see key_status().
    """
    for p in paths:
        if not p or not os.path.exists(p):
            continue
        for line in open(p, encoding='utf-8', errors='ignore'):
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            if line.lower().startswith('export '):
                line = line[7:]
            k, v = line.split('=', 1)
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if k and v and k not in os.environ:      # first writer wins
                os.environ[k] = v

_load_dotenv()

# Some code in this repo reads ORATS_API_KEY, some reads ORATS_API_TOKEN. Same secret,
# two names — alias them so neither spelling silently comes back empty.
for _a, _b in (('ORATS_API_KEY', 'ORATS_API_TOKEN'), ('ORATS_API_TOKEN', 'ORATS_API_KEY')):
    if os.environ.get(_a) and not os.environ.get(_b):
        os.environ[_b] = os.environ[_a]

def key_status(names=('FMP_API_KEY', 'OPENFDA_API_KEY', 'ORATS_API_KEY')):
    """Print which keys resolved. NEVER prints a value — only its length.
    A silent skip is how you end up believing a source ran when it never did."""
    print('api keys:')
    for n in names:
        v = os.environ.get(n) or ''
        print(f'   {n:<18} {"OK (%d chars)" % len(v) if v else "MISSING -> that source will be SKIPPED"}')

UA = {'User-Agent': 'pdufa.bio catalyst research contact@pdufa.bio'}
CTGOV = 'https://clinicaltrials.gov/api/v2/studies'
TODAY = dt.date.today()

# ---------------------------------------------------------------- sponsor -> ticker
SUFFIX = re.compile(
    r'\b(inc|inc\.|incorporated|corp|corp\.|corporation|co|co\.|company|ltd|ltd\.|limited|llc|l\.l\.c\.|'
    r'plc|p\.l\.c\.|sa|s\.a\.|ag|nv|n\.v\.|bv|ab|as|a/s|oyj|spa|s\.p\.a\.|gmbh|kk|k\.k\.|'
    r'pharmaceuticals?|pharma|therapeutics?|biosciences?|bioscience|biopharmaceuticals?|biopharma|'
    r'biotechnology|biotech|laboratories|labs?|holdings?|group|sciences?|medicines?|oncology|'
    r'technologies|international|usa|us|america|the)\b', re.I)

def norm(name):
    s = (name or '').lower()
    s = re.sub(r'[^a-z0-9 ]', ' ', s)
    s = SUFFIX.sub(' ', s)
    return re.sub(r'\s+', ' ', s).strip()

# ---------------------------------------------------------------- subsidiary / ADR map
# A pure name-match against SEC's company list misses two whole classes of real readouts:
#   SUBSIDIARIES  - "Genentech, Inc." files trials; the listed entity is Roche.
#                   "Janssen Research & Development, LLC" -> Johnson & Johnson.
#   ADRs          - "GlaxoSmithKline" and "Hoffmann-La Roche" are US-listed as GSK / RHHBY,
#                   but SEC's title index does not resolve those names.
# Between them these were silently dropping ~100 trials from the biggest sponsors on the board.
# Keys are normalised (lowercase, legal suffixes stripped) — see norm().
PARENT = {
    'glaxosmithkline':'GSK','glaxo smithkline':'GSK','viiv healthcare':'GSK',
    'hoffmann la roche':'RHHBY','roche':'RHHBY','genentech':'RHHBY','chugai':'RHHBY',
    'janssen research development':'JNJ','janssen':'JNJ','janssen biotech':'JNJ',
    'johnson johnson':'JNJ','johnson and johnson':'JNJ',
    'merck sharp dohme':'MRK','msd':'MRK','merck':'MRK',
    'astrazeneca':'AZN','medimmune':'AZN','alexion':'AZN',
    'sanofi':'SNY','genzyme':'SNY','sanofi aventis':'SNY',
    'novartis':'NVS','sandoz':'NVS',
    'bristol myers squibb':'BMY','celgene':'BMY','juno':'BMY',
    'abbvie':'ABBV','allergan':'ABBV','pharmacyclics':'ABBV',
    'eli lilly and':'LLY','eli lilly':'LLY','lilly':'LLY','loxo':'LLY',
    'pfizer':'PFE','wyeth':'PFE','seagen':'PFE','array':'PFE',
    'amgen':'AMGN','horizon':'AMGN',
    'gilead':'GILD','kite':'GILD',
    'bayer':'BAYRY','boehringer ingelheim':'',           # BI is private -> explicitly no ticker
    'takeda':'TAK','novo nordisk':'NVO','ucb':'UCBJY','ucb biopharma':'UCBJY',
    'daiichi sankyo':'DSNKY','astellas':'ALPMY','eisai':'ESALY','otsuka':'OTSKY',
    'merck kgaa':'MKKGY','emd serono':'MKKGY','csl':'CSLLY','csl behring':'CSLLY',
    'ipsen':'IPSEY','grifols':'GRFS','teva':'TEVA','viatris':'VTRS','organon':'OGN',
    'regeneron':'REGN','vertex':'VRTX','biogen':'BIIB','biontech':'BNTX','moderna':'MRNA',
    'incyte':'INCY','alnylam':'ALNY','ionis':'IONS','zai lab':'ZLAB','hutchmed':'HCM',
    'genmab':'GMAB','argenx':'ARGX','ascendis':'ASND','alkermes':'ALKS','jazz':'JAZZ',
    'neurocrine':'NBIX','sarepta':'SRPT','ultragenyx':'RARE','biomarin':'BMRN',
    'legend':'LEGN','beigene':'ONC','servier':'','bavarian nordic':'',
}


SEC_TICKERS_CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sec_company_tickers.json')

def _sec_json(url, tries=5):
    """SEC 429s under load. A transient rate-limit must not kill a 10-minute run."""
    last = None
    for a in range(tries):
        try:
            return json.loads(ur.urlopen(ur.Request(url, headers=UA), timeout=40).read())
        except Exception as e:
            last = e
            if '429' in str(e) or '503' in str(e):
                wait = 3 * (a + 1)
                print(f'    SEC rate-limited, retrying in {wait}s ({a+1}/{tries})', flush=True)
                time.sleep(wait)
            else:
                break
    raise last

def sec_ticker_index():
    # cache on disk: the map changes rarely, and re-fetching it on every run is what earns the 429
    try:
        j = _sec_json('https://www.sec.gov/files/company_tickers.json')
        json.dump(j, open(SEC_TICKERS_CACHE, 'w'))
    except Exception as e:
        if os.path.exists(SEC_TICKERS_CACHE):
            print(f'    SEC unreachable ({e}); using cached ticker map')
            j = json.load(open(SEC_TICKERS_CACHE))
        else:
            # DEGRADE, DO NOT DIE. SEC rate-limits hard under load. The CT.gov data — which is
            # the whole point of the run — is already in hand. Losing the ticker map costs us
            # some small-cap symbols; it must not cost us the entire crawl. The curated PARENT
            # map still resolves every major sponsor.
            print(f'    *** SEC ticker map unavailable ({e}) ***')
            print(f'    Continuing WITHOUT it. Big sponsors still resolve via the parent/ADR map;')
            print(f'    smaller names will have a blank ticker. Re-run later to fill them in.')
            return {}
    idx = {}
    for v in j.values():
        n = norm(v['title'])
        if n and n not in idx:
            idx[n] = v['ticker'].upper()
    return idx

def resolve_ticker(sponsor, idx):
    n = norm(sponsor)
    if not n: return ''
    # 1) curated parent/ADR map first — it is authoritative and beats a fuzzy hit
    if n in PARENT: return PARENT[n]
    for k, v in PARENT.items():
        if n.startswith(k + ' ') or n == k:
            return v
    # 2) exact SEC title match
    if n in idx: return idx[n]
    # a sponsor is often a subsidiary: "Genentech, Inc." under "Roche". Try prefix containment,
    # longest match first so "bristol myers squibb" beats "bristol".
    cands = [(k, v) for k, v in idx.items() if k and (n.startswith(k + ' ') or k.startswith(n + ' '))]
    if cands:
        return sorted(cands, key=lambda kv: -len(kv[0]))[0][1]
    return ''

# ---------------------------------------------------------------- CT.gov (paginated, no caps)
def ctgov_all(d_from, d_to, phases, statuses, sponsor_class, page_cb=None, agg=None):
    tok, out, pages = None, [], 0
    while True:
        p = {
            'filter.advanced': f'AREA[PrimaryCompletionDate]RANGE[{d_from},{d_to}]'
                               + (f' AND AREA[LeadSponsorClass]{sponsor_class}' if sponsor_class else ''),
            'filter.overallStatus': statuses,
            'query.term': 'AREA[Phase](' + ' OR '.join(phases) + ')',
            'fields': 'NCTId,BriefTitle,OfficialTitle,Phase,OverallStatus,PrimaryCompletionDate,'
                      'LeadSponsorName,Condition,EnrollmentCount,InterventionName,StudyType',
            'pageSize': 1000,
        }
        # CT.gov RETURNS `nextPageToken` but the REQUEST parameter is `pageToken`.
        # Sending it back under the name it arrived as gets you: "`nextPageToken` is unknown
        # parameter" -> HTTP 400 on page 2, i.e. a crawler that silently stops at 1,000 rows.
        if tok: p['pageToken'] = tok
        else:   p['countTotal'] = 'true'
        for attempt in range(4):
            try:
                r = json.loads(ur.urlopen(ur.Request(CTGOV + '?' + up.urlencode(p), headers=UA), timeout=60).read())
                break
            except Exception as e:
                if attempt == 3: raise
                time.sleep(2 + attempt * 2)
        studies = r.get('studies', [])
        out += studies
        pages += 1
        if page_cb: page_cb(pages, len(out), r.get('totalCount'))
        tok = r.get('nextPageToken')
        if not tok or not studies:
            break
        time.sleep(0.25)
    return out

def parse_study(s):
    ps = s.get('protocolSection', {})
    ident = ps.get('identificationModule', {})
    stat = ps.get('statusModule', {})
    des = ps.get('designModule', {})
    spon = ps.get('sponsorCollaboratorsModule', {}).get('leadSponsor', {})
    arms = ps.get('armsInterventionsModule', {})
    pcd_s = stat.get('primaryCompletionDateStruct', {}) or {}
    pcd = pcd_s.get('date')
    if not pcd: return None
    prec = 'day' if len(pcd) == 10 else 'month'
    drugs = [i.get('name') for i in (arms.get('interventions') or []) if i.get('name')]
    return dict(
        nct_id=ident.get('nctId'),
        sponsor=spon.get('name', ''),
        title=(ident.get('briefTitle') or '')[:160],
        phase=','.join(des.get('phases', []) or []),
        status=stat.get('overallStatus'),
        pcd=pcd, pcd_precision=prec,
        pcd_type=(pcd_s.get('type') or ''),          # ACTUAL vs ESTIMATED
        indication=(ps.get('conditionsModule', {}).get('conditions') or [None])[0],
        drug='; '.join(drugs[:3]),
        enrollment=(des.get('enrollmentInfo', {}) or {}).get('count'),
    )

# ==========================================================================================
# SOURCE 2 — company communications (SEC full text)
#
# CT.gov gives us a trial's primary completion date. It does NOT give us what the company
# actually TOLD the market: "we expect topline data in 2H 2026". That guidance is the thing
# traders act on, it is often the only date that exists, and it lives in the filings.
#
# We read it out of every form a readout date can hide in:
#   8-K / 6-K   press releases and their EX-99 exhibits
#   10-Q / 10-K MD&A and pipeline discussion ("we anticipate reporting in Q3")
#   S-1 / 424B  prospectus pipeline tables — the richest single source of forward timing
#   20-F        foreign annual reports (the ADRs CT.gov sponsor-matching misses)
#
# THE TRAP WE ARE NOT FALLING INTO AGAIN
# Our conference crawler used to read "Presented data at ESMO 2025" and file it as an UPCOMING
# 2026 catalyst, because when it could not read a year it defaulted to the FILING year and then
# projected forward. 74 of 121 rows were history sold as future. So here, as there:
#   a mention is not a commitment. We require an explicit FORWARD cue, and we refuse any date
#   that lands before the filing that announced it.
# ==========================================================================================
GUIDANCE_PHRASES = [
    # --- SCHEDULING PRs: the ONLY source of an EXACT readout date. Highest value, and we
    # --- were missing them entirely. When a company commits to a date it DROPS the hedge:
    # ---   "Q32 Bio TO REPORT 36-Week Topline Results ... ON JULY 13, 2026"
    # --- Every other phrase here assumes "expects to / on track to / anticipates". Those give
    # --- you "2H 2026". These give you a day.
    # NOTE: EDGAR full-text search requires ADJACENCY inside a quoted phrase. "to report topline"
    # does NOT match "to Report 36-Week Topline Results" — the intervening words break it. So we
    # search short, universal fragments and let the LEAD regexes find the date in the document.
    "Topline Results", "topline results from", "conference call to discuss",
    "will host a conference call", "to discuss the topline",
    "announces topline", "reports topline",
    "topline data", "topline results", "top-line data", "top-line results",
    "data readout", "readout expected", "data are expected", "results are expected",
    "expects to report topline", "on track to report", "plans to report topline",
    "primary endpoint data", "pivotal data", "interim analysis expected",
    "initial data expected", "data expected in", "results anticipated",
    "anticipate reporting", "expect to announce topline",
]
GUIDANCE_FORMS = "8-K,6-K,10-Q,10-K,S-1,424B4,424B5,20-F"

# a forward-looking cue must be present. "reported topline data in Q1 2026" is HISTORY.
FWD_CUE = _RE_FWD = None   # bound in _init_sec()
PAST_CUE = None

def _init_sec():
    """Bind the regexes that need catalyst_crawler's DAY / QH date grammar."""
    global FWD_CUE, PAST_CUE, LEADS, CC
    import catalyst_crawler as CC_
    CC = CC_
    import re as _re_
    FWD_CUE = _re_.compile(
        r"\b(expect\w*|anticipat\w*|on\s+track|plan\w*\s+to|intend\w*\s+to|guidance|"
        r"target\w*|project\w*|upcoming|forthcoming|will\s+(?:report|announce|present|host)|"
        r"remains?\s+on\s+track|"
        # THE UN-HEDGED COMMITMENT. Every other cue above assumes a company is hedging
        # ("expects to", "on track to") and those only ever yield "2H 2026". When a company
        # actually NAMES A DAY it drops the hedge entirely:
        #     "Q32 Bio TO REPORT 36-Week Topline Results ... ON JULY 13, 2026"
        # We were matching the hedge and missing the commitment — i.e. catching the vague
        # quarter and missing the only exact date that exists.
        r"to\s+(?:report|announce|present)|scheduled\s+(?:for|to)|conference\s+call)\b", _re_.I)
    PAST_CUE = _re_.compile(
        r"\b(reported|announced|presented|were\s+reported|was\s+reported|"
        r"previously\s+(?:reported|announced))\b", _re_.I)
    D, Q = CC.DAY, CC.QH
    LEADS = [
        # SCHEDULING PR — matched FIRST because it yields an EXACT DAY, not a quarter.
        #   "to Report 36-Week Topline Results from Part B of SIGNAL-AA ... on July 13, 2026"
        #   "will host a conference call on July 13, 2026 to discuss topline results"
        _re_.compile(r'\bto\s+(?:report|announce|present)\b[^.]{0,110}?'
                     r'(?:top-?line|readout|data|results)[^.]{0,90}?\bon\s+(' + D + ')', _re_.I),
        _re_.compile(r'\bwill\s+(?:report|announce|present|host)\b[^.]{0,110}?'
                     r'(?:top-?line|readout|data|results|conference\s+call)[^.]{0,90}?\bon\s+(' + D + ')', _re_.I),
        _re_.compile(r'\bconference\s+call\b[^.]{0,60}?\bon\s+(' + D + r')[^.]{0,80}?(?:top-?line|results|data)', _re_.I),
        _re_.compile(r'(?:top-?line|pivotal|primary\s+endpoint|interim|initial|final)\s+(?:data|results|readout)'
                     r'[^.]{0,60}?(?:expect\w*|anticipat\w*|on\s+track|project\w*|target\w*)'
                     r'[^.]{0,30}?(?:in|by|during|for)?\s*(' + D + '|' + Q + ')', _re_.I),
        _re_.compile(r'(?:expect\w*|anticipat\w*|plan\w*|on\s+track|remains?\s+on\s+track)'
                     r'[^.]{0,60}?(?:report|announce|present)[^.]{0,40}?(?:data|results|readout)'
                     r'[^.]{0,30}?(?:in|by|during|for)?\s*(' + D + '|' + Q + ')', _re_.I),
        _re_.compile(r'(?:data|results|readout)[^.]{0,30}?(?:are|is)?\s*(?:expect\w*|anticipat\w*)'
                     r'[^.]{0,25}?(?:in|by|during|for)?\s*(' + D + '|' + Q + ')', _re_.I),
    ]

# ------------------------------------------------------------------ milestone attribution
# THE BUG THIS EXISTS TO KILL
# The LEAD regexes chain with [^.]{0,60} — "any run of chars that is not a period". Press-release
# BULLETS DO NOT END IN PERIODS. So the pattern walks across bullet boundaries and stitches a
# readout noun from one bullet to a date in another:
#
#   "DURAVYU Phase 3 DME trials COMO and CAPRI full enrollment anticipated in 2H 2026"
#                                              ^^^^^^^^^^ the 2H 2026 belongs to ENROLLMENT
#
# 46 of 281 guidance rows were pure enrollment milestones filed as readouts, and 39 more were
# ambiguous — 30% of the source contaminated.
#
# THE RULE: a date belongs to the milestone NEAREST it. Not to whichever milestone word the
# regex could reach across a bullet list.
# Bare "data" / "results" / "report" are useless as readout signals: a 10-Q says "results of
# operations" and "interim reports" on every page. We require CLINICAL readout phrasing.
READOUT_TOK = re.compile(
    r'\b(?:top-?line|read-?out|primary\s+endpoint|secondary\s+endpoint|interim\s+analysis|'
    r'final\s+analysis|pivotal\s+data|clinical\s+data|trial\s+(?:data|results)|'
    r'study\s+(?:data|results)|(?:phase\s*[123][^.]{0,24})?(?:data|results)\s+(?:from|for|in)|'
    r'efficacy\s+(?:data|results)|(?:report|announce|present)\s+(?:top-?line|data|results))\b', re.I)
# NOT-A-READOUT milestones. A date sitting next to any of these is a trial STARTING, not a
# trial REPORTING — and it must never reach the readout calendar.
#
# The first version required `initiat\w*` to be IMMEDIATELY followed by trial|study|dosing.
# But nobody writes "initiate trial". They write:
#
#     "Initiation OF zumilokibart Phase 3 trial in AD expected 2H 2026"      (APGE)
#     "Company has initiated dosing OF ELEVATE-44-201 Cohort 2"              (TRDA)
#
# The word after "Initiation" is "of", so the pattern missed it — and milestone_of then fell
# through to the nearest token it DID recognise, which was "data readout" earlier in the same
# bullet list. Result: a trial-START date stamped milestone=readout. The self-check could never
# catch it, because the window really does contain the word "readout".
#
# `initiat\w*` alone is safe: it matches initiate/initiated/initiation/initiating but NOT
# "initial" (there is no 't' after "initia"), so "initial data" still reads as a readout.
ENROLL_TOK = re.compile(
    r'\b(?:enroll\w*|recruit\w*|randomi[sz]\w*|first\s+patient|last\s+patient|'
    r'dos(?:e|ing)\s+the\s+first|initiat\w*|commenc\w*|screen\w*|site\s+activation|'
    r'\bIND\s+(?:filing|clearance|submission)|dose\s+escalation)\b', re.I)

# A 10-Q/10-K is 90% accounting. These phrases mean we are inside a financial statement, not a
# pipeline update — and the "date" nearby is a FISCAL PERIOD END, not a readout.
#   "condensed results of operations ... for the three months ended December 31, 2026"
# That produced 2026-12-31 rows on the readout calendar. Reject the whole window.
FINANCIAL_NOISE = re.compile(
    r'(?:results\s+of\s+operations|financial\s+(?:statements?|condition|position)|'
    r'consolidated|condensed|footnotes?|\baudited|unaudited|balance\s+sheet|cash\s+flows?|'
    r'reporting\s+period|fiscal\s+(?:year|quarter)|interim\s+(?:financial|reports?)|'
    r'accrued|amortiz|\bGAAP\b|net\s+loss|shares\s+outstanding|prior\s+periods?)', re.I)
# NOTE: "financial results" is deliberately NOT here. Every biotech PR is titled "Reports Q4
# Financial Results and Provides Corporate Update" — and that is precisely the document that
# carries the pipeline guidance we want. Rejecting on the headline threw away real readouts and
# still let the accounting body through. Match the accounting STATEMENTS, not the press-release title.

# A regulatory SUBMISSION is a real catalyst — but a DIFFERENT one. "Marketing application
# expected to be submitted to the FDA in Q2 2026" releases NO DATA. Filing it as a phase
# readout is a category error.
SUBMISSION_TOK = re.compile(
    r'(?:submit\w*|submission|marketing\s+application|\bNDA\b|\bBLA\b|\bsNDA\b|\bMAA\b|'
    r'regulatory\s+filing|\bIND\b)', re.I)

# ---------------------------------------------------------------- trial name = the readout's IDENTITY
# A company restates the SAME guidance in every successive quarterly filing. Deduping on
# ticker+date+document therefore never collapses anything — a new document is always "new".
# On a 90-doc sample that turned 8 real readouts into 13 rows (38% inflation).
#
# But the identity is right there in the sentence: SunStone. CHAPTER-3. ALKIVIA. ZEPHYR.
# EMPASSION. EMERALD. A trial has a name, and that name — not the filing that mentions it —
# is what makes two rows the same readout.
TRIAL_STOP = {
    'PHASE','TOPLINE','RESULTS','RESULT','DATA','THE','THIS','THAT','OUR','ITS','COMPANY',
    'UPDATE','ENROLLMENT','COMPLETED','ONGOING','PIVOTAL','CLINICAL','REGISTRATIONAL','FIRST',
    'SECOND','THIRD','FOURTH','FULL','YEAR','QUARTER','REPORTS','ANNOUNCES','PATIENT','PATIENTS',
    'RANDOMIZED','CONTROLLED','BLIND','LABEL','OPEN','EXTENSION','GLOBAL','KEY','LEAD','MAIN',
    'PRIMARY','ADDITIONAL','SAME','SUCH','BOTH','EACH','NEW','A','AN','IN','OF','FOR','AND',
}
# A NAME looks like: SunStone · ZEPHYR · ALKIVIA · CHAPTER-3 · PALISADE-4 · SIGNAL-AA · TX2100
# The hyphen suffix may be LETTERS, not just digits — SIGNAL-AA is a real trial and the first
# version of this could not see it (it allowed -\d+ only, so it matched "SIGNAL" and then choked
# on the "-AA"). A pattern that silently fails on a real trial name is not a pattern.
_NAME = (r'[A-Z][a-z]+[A-Z][A-Za-z]*(?:-[A-Za-z0-9]+)*'   # CamelCase: SunStone, MoonStone
         r'|[A-Z]{3,}[A-Z0-9]*(?:-[A-Za-z0-9]+)*'         # ALLCAPS:   ALKIVIA, CHAPTER-3, SIGNAL-AA
         r'|[A-Z]{2,}-?\d{2,}[A-Za-z0-9-]*')              # code:      TX2100, ML-007C-MA
#
# THE FILLER MUST BE NAMED, NOT WILDCARDED.
# The first version allowed "{0,2} arbitrary words" between the name and "trial". Given
# "Phase 2 SunStone trial" the engine matched at the LEFTMOST viable start — capturing
# "Phase", with "2 SunStone" as filler. Phase is in the stop list so the candidate was
# discarded, but finditer had already consumed the span and never offered SunStone at all.
# A greedy left match ate the very name it was hunting for. So: enumerate the filler that
# legitimately appears ("Phase 3", "clinical", "pivotal") and let backtracking find the name.
_FILL = r'(?i:(?:phase\s*[0-9]+[ab]?(?:/[0-9]+)?\s+|clinical\s+|pivotal\s+|registrational\s+|open-?label\s+|extension\s+|randomized\s+)*)'
_TU   = r'(?:[Tt]rial|[Ss]tudy)'
# (a) NAME (+ named filler) before "trial"/"study"  -> "SunStone trial", "PALISADE-4 Phase 3 trial"
# (b) NAME then a comma and a descriptor            -> "CHAPTER-3, a pivotal Phase 3 study"
_TRIAL_A = re.compile(r'\b(' + _NAME + r')\s+' + _FILL + _TU + r'\b')
_TRIAL_B = re.compile(r'\b(' + _NAME + r')\s*,\s+(?:a|an|the)\b[^,.]{0,60}?' + _TU + r'\b')

def trial_name(ctx, date_pos=None):
    """The trial the DATE belongs to, or ''.

    NOT simply "the first trial name in the window" — that is the same attribution bug that
    once put enrollment dates on the readout calendar. A corporate-update paragraph names
    several trials:

        "Topline results for RAPIDe-3 ... expected in 4Q2025.
         Enrollment continues in CHAPTER-3 ...; topline results expected in 2H2026."

    The first name is RAPIDe-3. The trial that reads out in 2H2026 is CHAPTER-3. Taking the
    first match would mislabel it — and a mislabelled trial is worse than an unlabelled one,
    because it looks like knowledge. So: the name NEAREST the date wins, preferring the name
    that PRECEDES it, which is how these sentences are actually written.
    """
    cands = []
    for rx in (_TRIAL_A, _TRIAL_B):
        for m in rx.finditer(ctx or ''):
            n = m.group(1)
            if n.upper() in TRIAL_STOP:
                continue
            # a name is either ALL-CAPS (ALKIVIA, EMPASSION) or CamelCase (SunStone, MoonStone)
            # or hyphen-numbered (CHAPTER-3). Plain Titlecase is a sentence, not a codename.
            if n.isupper() or any(c.isupper() for c in n[1:]) or '-' in n:
                cands.append((m.start(1), m.end(1), n))
    if not cands:
        return ''
    if date_pos is None:
        return cands[0][2]

    # NEAREST PRECEDING NAME WINS — and a following name is a last resort, not a near-miss.
    #
    # A softer "distance with a penalty" rule got MPLT wrong: the paragraph reads
    #     "Phase 2 ZEPHYR trial ... topline results expected in the third quarter of 2026
    #      Phase 2 IRIS trial for ML-004 ..."
    # ZEPHYR is the trial that reads out. IRIS is simply the next bullet. Under a distance
    # metric IRIS sat a few characters closer and won. But these sentences are ALWAYS written
    # <TRIAL> ... topline expected <DATE>; the name comes first. So take the last name before
    # the date, full stop, and only look forward if nothing precedes it at all.
    MAX_REACH = 200          # beyond this we are guessing, and a guess must not look like a fact
    before = [c for c in cands if c[1] <= date_pos and (date_pos - c[1]) <= MAX_REACH]
    if before:
        return max(before, key=lambda c: c[1])[2]        # the closest one to the LEFT
    after = [c for c in cands if c[0] > date_pos and (c[0] - date_pos) <= 60]
    if after:
        return min(after, key=lambda c: c[0])[2]
    return ''            # unlabelled. Better an honest blank than a confident wrong trial.

# ...and the window must actually be talking about a CLINICAL TRIAL.
CLINICAL_ANCHOR = re.compile(
    r'(?:phase\s*[123]\b|phase\s*i{1,3}\b|top-?line|read-?out|primary\s+endpoint|pivotal|'
    r'clinical\s+trial|clinical\s+study|\bcohort\b|patients?\s+(?:dosed|enrolled|randomi)|'
    r'interim\s+analysis|efficacy|\bNCT\d)', re.I)


def milestone_of(text, date_start, date_end, radius=110):
    """Which milestone does this date belong to? Returns 'readout' | 'enrollment' | 'unknown'.

    Nearest-token wins. If an enrollment word sits closer to the date than any readout word,
    the date is an enrollment milestone and is NOT a readout — no matter what else the bullet
    list happens to contain.
    """
    lo = max(0, date_start - radius)
    hi = min(len(text), date_end + 40)
    win = text[lo:hi]
    dpos = date_start - lo

    def nearest(rx):
        best = None
        for m in rx.finditer(win):
            dist = dpos - m.end() if m.end() <= dpos else m.start() - dpos
            if dist < 0: dist = 0
            if best is None or dist < best: best = dist
        return best

    r = nearest(READOUT_TOK)
    e = nearest(ENROLL_TOK)
    if r is None: return 'unknown'          # no readout word anywhere near -> not a readout
    if e is not None and e < r: return 'enrollment'   # enrollment word is CLOSER -> it owns the date
    return 'readout'


# ------------------------------------------------------------------ non-catalyst filter
# Half the Phase 1 bucket is not a readout in any useful sense. Food-effect studies,
# bioavailability, drug-drug interaction, thorough-QT, hepatic/renal impairment, single- and
# multiple-ascending-dose in healthy volunteers — nobody issues a press release about these,
# they never move a stock, and they frequently never post results to CT.gov (which is why they
# pile up in the "completed, no results" bucket and look like a backlog of pending readouts).
# 497 of 2,174 rows (23%) were this. They are clutter, and they hide the real ones.
NON_CATALYST = re.compile(
    r'(?:bioavailab|bioequival|food[- ]?effect|effect of food|drug[- ]drug interaction|\bDDI\b|'
    r'\bhealthy\b|mass balance|\bADME\b|absorption, metabolism|'
    r'hepatic impair|renal impair|thorough[- ]?qt|\bQTc?\b|cardiac repolari|'
    r'single[- ]ascending|multiple[- ]ascending|\bSAD\b|\bMAD\b|dose[- ]escalation in healthy|'
    r'relative bioavail|formulation|tablet.*capsule|capsule.*tablet|'
    r'pharmacokinetics?,? (?:safety )?(?:and )?(?:tolerability )?(?:of|in) healthy|'
    r'\bpharmacokinetic (?:study|profile) in\b|crossover.*healthy|'
    r'immunogenicity in healthy|lactation|breast milk|'
    r'effect of .{0,40}? on (?:the )?(?:plasma|pharmacokinetic|exposure|concentration)|'  # DDI
    r'plasma (?:levels|concentrations) of|on the pharmacokinetics of)', re.I)

# STUDY TYPES that reach a primary-completion date but are NOT market-moving topline readouts.
# A run of these had a NEAR completion date and looked "imminent", but they are not catalysts:
# extension/OLE studies of an already-read-out drug, first-in-human safety studies, platform
# substudies, expanded-access programs. Measured on a live 506-row CT.gov set: catches 44 (9%),
# ZERO of which mention phase 3 / pivotal / primary endpoint (no real readout dropped).
NON_READOUT_TYPE = re.compile(
    r'(?:\bextension study\b|open-?label extension|\bOLE\b|long-?term extension|'
    r'continuation (?:study|treatment|phase)|roll-?over|'                 # extension / OLE / rollover
    r'first-?in-?human|to learn how safe|to learn about the safety|'      # FIH safety
    r'maximum tolerated dose|\bMTD\b|'                                    # Phase 1 dose ceiling
    r'\bsubstudy\b|sub-study|master protocol|'                            # platform substudy
    r'expanded access|compassionate use|managed access|early access)',   # access, not a readout
    re.I)

# Early-dose studies (dose-escalation / -finding / -ranging) are dropped ONLY when there is no
# efficacy/expansion signal. This keeps a small-cap Phase 2 dose-ranging study that IS the topline
# catalyst, while dropping a pure Phase 1 dose-escalation. The efficacy words are the discriminator.
_DOSE_EARLY = re.compile(r'dose[- ]escalation|dose[- ]finding|dose[- ]ranging', re.I)
_EFFICACY   = re.compile(r'efficacy|response rate|\bORR\b|expansion|\bPFS\b|\bOS\b|'
                         r'progression-free|overall surviv|primary endpoint|pivotal', re.I)
# Pediatric studies are dropped ONLY when they are PK/safety (not a pediatric EFFICACY readout).
_PEDI    = re.compile(r'pediatric|paediatric|in children|adolescents?\b', re.I)
_PEDI_PK = re.compile(r'pharmacokinetic|safety and tolerab|\bPK\b|dose[- ]?finding|'
                      r'to (?:evaluate|assess|characterize) (?:the )?safety', re.I)

def is_catalyst(title):
    """False for studies that reach a completion date but are never a topline stock catalyst:
    PK/plumbing, extension/OLE, first-in-human safety, platform substudies, and PK-only pediatric
    or early-dose studies. Guards protect real efficacy readouts (dose-ranging WITH efficacy, and
    pediatric EFFICACY, both survive)."""
    t = str(title or '')
    if NON_CATALYST.search(t) or NON_READOUT_TYPE.search(t):
        return False
    if _DOSE_EARLY.search(t) and not _EFFICACY.search(t):
        return False
    if _PEDI.search(t) and _PEDI_PK.search(t):
        return False
    return True


def period_bounds(iso):
    """'2026-Q3' -> (2026-07-01, 2026-09-30). Needed because a naive string compare says
    "2026-Q1" >= "2026-07-12" (because 'Q' > '0') and silently lets PAST quarters through."""
    m = re.match(r'^(\d{4})-Q([1-4])$', str(iso))
    if m:
        y, q = int(m.group(1)), int(m.group(2))
        sm = 3 * (q - 1) + 1
        em = sm + 2
        last = [31,28,31,30,31,30,31,31,30,31,30,31][em - 1]
        if em == 2 and y % 4 == 0 and (y % 100 != 0 or y % 400 == 0): last = 29
        return dt.date(y, sm, 1), dt.date(y, em, last)
    m = re.match(r'^(\d{4})-H([12])$', str(iso))
    if m:
        y, h = int(m.group(1)), int(m.group(2))
        return (dt.date(y,1,1), dt.date(y,6,30)) if h == 1 else (dt.date(y,7,1), dt.date(y,12,31))
    m = re.match(r'^(\d{4})-(\d{2})$', str(iso))
    if m:
        y, mo = int(m.group(1)), int(m.group(2))
        last = [31,28,31,30,31,30,31,31,30,31,30,31][mo - 1]
        if mo == 2 and y % 4 == 0 and (y % 100 != 0 or y % 400 == 0): last = 29
        return dt.date(y, mo, 1), dt.date(y, mo, last)
    try:
        d0 = dt.date.fromisoformat(str(iso)[:10]); return d0, d0
    except Exception:
        return None, None


def sec_guidance_readouts(ua, since, until, max_docs=1200, workers=8, lookback_days=450):
    """Mine company-stated readout timing out of SEC filings. Returns list of dicts.

    NOTE the two different windows:
      since/until  = the CATALYST window we care about (e.g. rest of 2026)
      since_dt/..  = the FILING window we search (a 10-K filed 14 months ago can still be the
                     only place a company ever stated its 2026 readout timing)
    """
    _init_sec()
    since_dt = (dt.date.today() - dt.timedelta(days=lookback_days)).isoformat()
    until_dt = dt.date.today().isoformat()
    import concurrent.futures as _cf, re as _re_
    from collections import OrderedDict

    # 1) full-text search each guidance phrase -> candidate documents
    #
    # PER-PHRASE QUOTA. The old loop broke on `len(docs) >= max_docs` INSIDE the phrase
    # iteration, so the FIRST phrase swallowed the entire budget and the other 24 never ran.
    # At --max-docs 1500 only ~3 phrases ever executed — and the scheduling-PR phrases, which
    # are the only source of an EXACT day, were among the ones being starved.
    docs = OrderedDict()
    quota = max(30, max_docs // max(1, len(GUIDANCE_PHRASES)))
    for ph in GUIDANCE_PHRASES:
        n = 0
        try:
            for hit in CC.sec_fulltext(ph, GUIDANCE_FORMS, ua, since_dt, until_dt):
                src = hit.get("_source", {})
                _id = hit.get("_id", "")
                if not _id or _id in docs: continue
                adsh, _, fname = _id.partition(":")
                cik = (src.get("ciks") or [""])[0]
                docs[_id] = dict(cik=str(cik).lstrip("0"), adsh=adsh.replace("-", ""), fname=fname,
                                 form=src.get("root_form") or src.get("file_type"),
                                 filed=src.get("file_date"), phrase=ph)
                n += 1
                if n >= quota or len(docs) >= max_docs: break   # quota is PER PHRASE
        except Exception as e:
            print(f"  [fts] '{ph}': {e}", file=sys.stderr)
        print(f"  [fts] {ph:34s} +{n:4d}  (pool {len(docs)}/{max_docs})", flush=True)
        if len(docs) >= max_docs: break

    # 2) fetch + scan each document
    def scan(item):
        _id, m = item
        url = f"https://www.sec.gov/Archives/edgar/data/{m['cik']}/{m['adsh']}/{m['fname']}"
        try:
            txt = CC.clean_html(CC.sec_get(url, ua).text)
        except Exception:
            return []
        try:
            filed = dt.date.fromisoformat(m["filed"])
        except Exception:
            filed = None
        out, subs, seen = [], [], set()
        for rx in LEADS:
            for mt in rx.finditer(txt):
                raw = mt.group(1)
                # THE TEXT THE GATES JUDGE **IS** THE TEXT WE STORE.
                # These used to be two different windows (win = -260 from match start; ctx = -300
                # from the DATE). So the extractor would accept on `ctx` and the end-of-run
                # self-check would then re-judge the stored `win` and disagree with it. A checker
                # that reads different evidence than the thing it is checking is not a checker.
                # One window. Judged once, stored verbatim.
                ctx = txt[max(0, mt.start(1) - 300): mt.end(1) + 120]
                # --- prospectivity gate: a mention is not a commitment ---
                if not FWD_CUE.search(ctx):        continue
                if PAST_CUE.search(ctx) and not FWD_CUE.search(ctx): continue
                # (a) are we inside a financial statement? then this date is a fiscal period end.
                if FINANCIAL_NOISE.search(ctx):
                    continue
                # (b) is this even about a clinical trial?
                if not CLINICAL_ANCHOR.search(ctx):
                    continue
                # (c) does the date belong to the READOUT, or to enrollment/dosing?
                ms = milestone_of(txt, mt.start(1), mt.end(1))
                if ms != 'readout':
                    continue
                iso, prec = CC.norm_any(raw)
                if not iso: continue
                # --- never accept a date that precedes the filing announcing it ---
                probe = iso if len(iso) == 10 else (iso[:4] + "-12-28")
                try:
                    if filed and dt.date.fromisoformat(probe) < filed: continue
                except Exception:
                    pass
                # window test on the PERIOD, not the string. "2026-Q1" is not >= "2026-07-12"
                # just because 'Q' sorts above '0' — it is a quarter that already ended.
                p0, p1 = period_bounds(iso)
                if not p0: continue
                if p1 < dt.date.fromisoformat(since) or p0 > dt.date.fromisoformat(until): continue
                if iso in seen: continue
                seen.add(iso)
                _dpos = mt.start(1) - max(0, mt.start(1) - 300)   # date's offset inside ctx
                row = dict(nct_id="", sponsor="", title=_re_.sub(r"\s+", " ", ctx)[:400],
                    # the readout's identity. Anchored on the DATE's offset inside ctx, so a
                    # paragraph naming three trials attributes the date to the right one.
                    trial=trial_name(ctx, _dpos),
                    # Carry the raw window and the date's position in it, so the end-of-run
                    # self-check can RE-RUN the real attribution instead of pattern-matching
                    # around it. Token-presence checks cannot catch an APGE-class error: that
                    # window contains BOTH "initiation" and "readout", so any "has enrollment
                    # word AND lacks readout word" test scores it clean while the date is still
                    # attached to the wrong milestone. Only re-deciding can catch a misdecision.
                    _ctx=ctx, _dpos=_dpos,
                    phase="", status="", pcd=iso, pcd_precision=prec, indication="", drug="",
                    enrollment=None, cik=m["cik"], form=m["form"], filed=m["filed"],
                    catalyst_date=iso, date_precision=prec, date_basis="company_guidance",
                    milestone='readout',      # attribution verified: nearest milestone word wins
                    confidence=0.70,   # a company's own stated timing beats a CT.gov proxy
                    source="sec_edgar",
                    source_url=url,
                    note="company-stated guidance from an SEC filing")
                # (d) A regulatory SUBMISSION is a real catalyst — but a DIFFERENT one. Filing a
                # BLA releases no data. It must not sit on the readout calendar. We do not throw
                # it away either: it goes to a sidecar file so a real catalyst is never lost just
                # because it was the wrong KIND of catalyst.
                if SUBMISSION_TOK.search(ctx) and not READOUT_TOK.search(ctx):
                    row['milestone'] = 'submission'
                    row['note'] = 'regulatory submission (NOT a readout — no data is released)'
                    subs.append(row)
                    continue
                out.append(row)
                # A corporate-update PR lists four programs and four dates. Taking only the first
                # threw the other three away. Cap it, don't cripple it.
                if len(out) >= 6: break
            if out or subs: break
        return out, subs

    rows, submissions = [], []
    with _cf.ThreadPoolExecutor(workers) as ex:
        for r, s in ex.map(scan, list(docs.items())):
            rows += r; submissions += s
    print(f"  [fts] {len(docs)} docs scanned -> {len(rows)} guidance dates "
          f"({len(submissions)} regulatory submissions diverted — not readouts)")
    if submissions:
        _sf = f'ro_submissions_{dt.datetime.now().strftime("%H%M%S")}.csv'
        pd.DataFrame(submissions).to_csv(_sf, index=False, quoting=__import__('csv').QUOTE_ALL)
        print(f'  [fts] regulatory submissions written to {_sf} (a real catalyst, a different calendar)')
    return rows


# ---------------------------------------------------------------- [3] NEWSWIRE (FMP press releases)
# THE ONLY SOURCE OF AN EXACT READOUT DAY.
#
# CT.gov gives a completion PROXY. SEC filings give a company's own QUARTER ("topline in 2H26").
# Neither can ever give you a day, and that is not a tuning problem — it is structural:
#
#     "Q32 Bio to Report 36-Week Topline Results from Part B of SIGNAL-AA ... on July 13, 2026"
#      -- PR Newswire, 2026-07-10.  Zero QTTB filings mention SIGNAL-AA or bempikibart.
#
# A scheduling PR is never attached to an 8-K, so SEC full-text is BLIND to it. That PR is a
# T-3 heads-up on a readout that moved the stock. The newswire is the only place it exists.
#
# NOTE ON THE ENDPOINT: FMP's /api/v3/press-releases/ now returns HTTP 403 ("Legacy Endpoint").
# Only /stable/news/press-releases works. The v3 fallback elsewhere in this repo is a corpse.
FMP_PR = 'https://financialmodelingprep.com/stable/news/press-releases'
FMP_NEWS = 'https://financialmodelingprep.com/stable/news/stock'

# How much of a press-release BODY we are willing to hand to a backtracking regex.
# The announcement is in the headline and the lede. Everything past that is the boilerplate
# ("About the Company", forward-looking-statements) which contributes no dates and enormous
# backtracking cost. 3,000 chars comfortably covers the headline + opening bullets.
PR_TEXT_CAP = 3000

# "to report/announce/present/host ... topline/results/data ... on <DAY>"
# Matched against the HEADLINE first — the probe showed the headline alone carries the date.
_D = r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+20\d\d'
PR_SCHED = [
    re.compile(r'\bto\s+(?:report|announce|present|release)\b[^.]{0,150}?'
               r'(?:top-?line|read-?out|results|data)[^.]{0,130}?\bon\s+(' + _D + r')', re.I),
    re.compile(r'\b(?:top-?line|read-?out|pivotal|primary\s+endpoint)[^.]{0,130}?'
               r'(?:expected|anticipated|scheduled|will\s+be\s+(?:reported|announced|presented))'
               r'[^.]{0,60}?\bon\s+(' + _D + r')', re.I),
    re.compile(r'\b(?:conference\s+call|webcast|investor\s+(?:call|event))[^.]{0,110}?'
               r'\bon\s+(' + _D + r')[^.]{0,140}?(?:top-?line|read-?out|results\s+from)', re.I),
]
# A PR that ANNOUNCES the result ("Announces Positive Topline Results") is the readout happening,
# not a readout coming. Never put a past event on a forward calendar.
PR_PAST = re.compile(r'\b(?:announce[sd]?|report(?:s|ed)|present(?:s|ed))\b\s+'
                     r'(?:positive|negative|mixed|topline|top-line|initial|final|\d)', re.I)

def fmp_readout_dates(tickers, key, when_from, when_to, limit=50, workers=8):
    """Scan company press releases for a NAMED DAY on which a readout will be reported."""
    import concurrent.futures as _cf
    try:
        import requests
        import catalyst_crawler as CC     # norm_any lives here; the SEC leg imports it locally too
    except ImportError as e:
        print(f'  [pr] cannot import ({e}) — skipping newswire leg')
        return []

    d0, d1 = dt.date.fromisoformat(when_from), dt.date.fromisoformat(when_to)

    def scan(tk):
        out = []
        try:
            r = requests.get(FMP_PR, params={'symbols': tk, 'limit': limit, 'apikey': key}, timeout=20)
            rows = r.json() if r.status_code == 200 else []
        except Exception:
            return out
        if not isinstance(rows, list):
            return out
        for x in rows:
            if not isinstance(x, dict):
                continue
            title = str(x.get('title') or '')
            body = str(x.get('text') or x.get('content') or '')
            # BOUND THE TEXT. PR_SCHED chains [^.]{0,150}? quantifiers; run those against a
            # 40KB press-release body and the regex engine backtracks catastrophically. On 3
            # tickers it looked fine; on a 946-ticker sweep it burned 649 CPU-SECONDS and the
            # process died without writing a row.
            #
            # The bound is not a workaround, it is the correct scope: the scheduling date lives
            # in the HEADLINE. QTTB's "...on July 13, 2026" was in the title. The lede carries
            # it; the boilerplate at the bottom of a PR never does.
            blob = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', f'{title} . {body[:PR_TEXT_CAP]}'))
            for rx in PR_SCHED:
                mt = rx.search(blob)
                if not mt:
                    continue
                # the same three gates the SEC leg uses — a PR is not exempt from them
                ctx = blob[max(0, mt.start() - 200): mt.end() + 120]
                if FINANCIAL_NOISE.search(ctx):                       continue
                if not CLINICAL_ANCHOR.search(ctx):                   continue
                if SUBMISSION_TOK.search(ctx) and not READOUT_TOK.search(ctx): continue
                # "Announces Positive Topline Results" = it already happened. Not a catalyst.
                if PR_PAST.search(title):                             continue
                iso, prec = CC.norm_any(mt.group(1))
                if not iso or prec != 'day':
                    continue
                try:
                    dd = dt.date.fromisoformat(iso)
                except Exception:
                    continue
                if dd < d0 or dd > d1:
                    continue
                out.append(dict(
                    ticker=tk, nct_id='', sponsor='', title=blob[:400],
                    trial=trial_name(ctx), phase='', status='',
                    pcd=iso, pcd_precision=prec, indication='', drug='', enrollment=None,
                    cik='', form='PR', filed=str(x.get('publishedDate') or x.get('date') or '')[:10],
                    catalyst_date=iso, date_precision='day', date_basis='company_pr',
                    milestone='readout',
                    confidence=0.92,   # a NAMED DAY is a commitment, not a hope. Highest we issue.
                    source='fmp_press', source_url=x.get('url') or x.get('link') or '',
                    # FMP redistribution terms are UNREAD (backlog P2-6). Until they are, this row
                    # is a private QA yardstick — the same slot BioPharmaCatalyst occupies. It must
                    # NOT reach the site, the API, or the sitemap.
                    redistribute=False,
                    note='company scheduling PR — exact day (source terms unverified; DO NOT PUBLISH)'))
                break
        return out

    rows = []
    with _cf.ThreadPoolExecutor(workers) as ex:
        for r in ex.map(scan, tickers):
            rows += r
    # one row per ticker+trial+date; a PR often restates the schedule
    seen, ded = set(), []
    for r in rows:
        k = (r['ticker'], r['catalyst_date'], (r['trial'] or '').upper())
        if k in seen:
            continue
        seen.add(k); ded.append(r)
    print(f'  [pr] {len(tickers)} tickers scanned -> {len(ded)} EXACT-DAY readouts from scheduling PRs')
    return ded


# ---------------------------------------------------------------- [5] FILING ENRICHMENT
# THE READOUT DATE LIVES IN THE FILING, NOT IN CT.gov.
#
# CT.gov gives a data-lock PROXY and tells us WHO to watch. The actual readout date — and whether
# it has ALREADY happened — is in the company's own 8-K / press release. So for every ticker with
# an imminent/near/overdue CT.gov readout, pull its recent PRs and do two things:
#
#   (1) KILL the dead ones.  A PR that ANNOUNCES results ("Mezigdomide Reduces Risk of Disease
#       Progression", "Met its Primary Endpoint", "Topline Results") means the readout ALREADY
#       HAPPENED. It must come off a forward calendar. A stale catalyst is worse than a missing one.
#   (2) UPGRADE the date.  A scheduling PR that NAMES A DAY replaces the CT.gov month-proxy with
#       the company's own stated date.
#
# THE DANGER IS A FALSE KILL — removing a live catalyst. Big pharma runs one drug across many
# trials (AZN/Tezepelumab, MRK/pembrolizumab), so a results PR for indication A must not kill a
# different-indication readout. Rule: kill on a drug match ONLY when the ticker has a SINGLE
# imminent readout for that drug; when the drug spans multiple rows we require a trial-name match,
# and if we cannot confirm the specific trial we FLAG for review rather than silently drop.

# "the TOPLINE readout is OUT" — must be STRONG readout language. Broader than PR_PAST but not
# so broad that "Announces new three-year data" (long-term follow-up of an APPROVED drug) counts
# as a fresh readout. Requires topline / primary-endpoint / pivotal-results / met-missed-failed.
PR_RESULTS_OUT = re.compile(
    r'\b(?:top-?line|primary\s+endpoint|pivotal\s+(?:phase\s*3\s+)?(?:trial|study|data|results)|'
    r'(?:positive|negative|mixed)\s+(?:top-?line\s+)?(?:results|data)|'
    r'(?:met|missed|achieved|did\s+not\s+meet)\s+(?:its\s+)?(?:the\s+)?primary|'
    r'reduces?\s+(?:the\s+)?risk\s+of|statistically\s+significant\s+(?:improvement|reduction|benefit)|'
    r'results\s+from\s+[\w\'’.\s]{0,30}?pivotal|'                         # "Results from <Co>'s Pivotal ..."
    r'pivotal\s+phase\s*3\b[^.]{0,55}?(?:results|data|published|readout|met|positive)|'
    r'phase\s*3[^.]{0,40}?(?:met|results|readout))',
    re.I)
# EXCLUDE long-term / follow-up / post-hoc data of an already-read-out or approved drug — that is
# not a topline readout. "Three-Year VOXZOGO data", "long-term extension", "real-world", "subgroup".
PR_FOLLOWUP = re.compile(
    r'\b(?:\d+-year|\d+-month|long-?term|follow-?up|real-?world|post-?hoc|subgroup|'
    r'extension\s+(?:study|data)|final\s+(?:overall\s+survival|\d)|durability|maintenance\s+of)\b', re.I)
# a headline that is itself a SCHEDULING PR ("to report ... on <day>") is forward, not done
_PR_FUTURE_HDR = re.compile(r'\bto\s+(?:report|announce|present|host)\b', re.I)

_DRUG_STOP = {'placebo', 'matching', 'active', 'reference', 'comparator', 'standard', 'care',
              'carboplatin', 'paclitaxel', 'cisplatin', 'dexamethasone', 'fulvestrant',
              'pembrolizumab', 'nivolumab', 'chemotherapy', 'and', 'or', 'plus', 'best'}

def _lead_drug(s):
    """The lead INVESTIGATIONAL drug from a CT.gov drug field like
    'Dostarlimab; Carboplatin; Paclitaxel' -> 'dostarlimab'. Skips placebo / chemo backbone."""
    for part in re.split(r'[;,/]| and | plus ', str(s or '')):
        w = part.strip()
        if len(w) < 4:
            continue
        if w.lower() in _DRUG_STOP:
            continue
        # a distinctive drug token (INN names are long and unique; skip generic words)
        tok = re.sub(r'[^A-Za-z0-9-]', '', w.split()[0]) if w.split() else ''
        if len(tok) >= 5 and tok.lower() not in _DRUG_STOP:
            return tok
    return ''

def enrich_from_filings(d, key, workers=8, results_lookback=170):
    """Enrich imminent/near/overdue CT.gov rows from company PRs. Returns (d, killed, upgraded, flagged)."""
    import concurrent.futures as _cf
    try:
        import requests
        import catalyst_crawler as CC          # norm_any for date parsing
    except ImportError as e:
        print(f'  [enrich] cannot import ({e}) — skipping filing enrichment')
        return d, 0, 0, 0

    m = (d.date_basis == 'ctgov_pcd') & d.imminence.isin(['IMMINENT', 'NEAR', 'OVERDUE'])
    sub = d[m & d.ticker.astype(str).str.len().gt(0)].copy()
    if not len(sub):
        print('  [enrich] no imminent/near/overdue ctgov rows to enrich')
        return d, 0, 0, 0
    sub['drug1'] = sub.drug.map(_lead_drug)
    tickers = sorted(t for t in sub.ticker.dropna().unique() if str(t) != 'nan')
    # how many imminent readouts per (ticker, drug) — a drug in ONE row is safe to kill on a drug
    # match; a drug across MANY rows (platform drug) needs a trial-name match.
    dcount = sub.groupby(['ticker', 'drug1']).size().to_dict()

    def fetch(tk):
        try:
            r = requests.get(FMP_PR, params={'symbols': tk, 'limit': 40, 'apikey': key}, timeout=20)
            rows = r.json() if r.status_code == 200 else []
        except Exception:
            return tk, []
        out = []
        for x in (rows if isinstance(rows, list) else []):
            if not isinstance(x, dict):
                continue
            title = str(x.get('title') or '')
            body = str(x.get('text') or x.get('content') or '')[:PR_TEXT_CAP]
            pub = str(x.get('publishedDate') or x.get('date') or '')[:10]
            out.append((title, re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', f'{title} . {body}')),
                        pub, x.get('url') or x.get('link') or ''))
        return tk, out
    prmap = {}
    with _cf.ThreadPoolExecutor(workers) as ex:
        for tk, prs in ex.map(fetch, tickers):
            prmap[tk] = prs

    killed = upgraded = flagged = 0
    for idx, row in sub.iterrows():
        drug = row['drug1']
        if not drug:
            continue
        prs = prmap.get(row['ticker'], [])
        dl = drug.lower()
        drx = re.compile(r'\b' + re.escape(dl) + r'\b', re.I)
        trial = str(row.get('trial') or '').strip().lower()
        multi = dcount.get((row['ticker'], drug), 1) > 1

        for title, blob, pub, url in prs:
            if not drx.search(title):                     # match on the HEADLINE (precise)
                continue
            # (1) already read out?  Strong readout language, not follow-up/long-term, not forward.
            if (PR_RESULTS_OUT.search(title) and not _PR_FUTURE_HDR.search(title)
                    and not PR_FOLLOWUP.search(title)):
                confirmed = (not multi) or (trial and trial in blob.lower())
                if confirmed:
                    d.at[idx, 'readout_stage'] = 'read_out'
                    d.at[idx, 'note'] = f'ALREADY READ OUT — {row["ticker"]} PR {pub}: "{title[:90]}"'
                    d.at[idx, 'source_url'] = url or d.at[idx, 'source_url']
                    killed += 1
                else:
                    d.at[idx, 'note'] = (f'POSSIBLE prior readout ({row["ticker"]} PR {pub}) but drug '
                                         f'spans multiple trials — VERIFY before trusting the date')
                    d.at[idx, 'readout_stage'] = 'verify'
                    flagged += 1
                break
            # (2) forward date from a scheduling PR?
            hit = None
            for rx in PR_SCHED:
                mt = rx.search(blob)
                if mt:
                    hit = mt; break
            if hit:
                iso, prec = CC.norm_any(hit.group(1))
                if iso and prec == 'day':
                    try:
                        if dt.date.fromisoformat(iso) >= TODAY:
                            d.at[idx, 'catalyst_date'] = iso
                            d.at[idx, 'date_precision'] = 'day'
                            d.at[idx, 'date_basis'] = 'company_pr'
                            d.at[idx, 'confidence'] = 0.92
                            d.at[idx, 'note'] = f'date from {row["ticker"]} scheduling PR {pub}'
                            d.at[idx, 'source_url'] = url or d.at[idx, 'source_url']
                            upgraded += 1
                    except Exception:
                        pass
                break
    print(f'  [enrich] {len(tickers)} tickers · {len(sub)} imminent rows -> '
          f'{killed} KILLED (already read out) · {upgraded} date-upgraded · {flagged} flagged to verify')
    return d, killed, upgraded, flagged


# ---------------------------------------------------------------- [4] CONFERENCE (exact day, WEEKS ahead)
# THE ONLY EARLY EXACT DATE.
#
# Measured lead times on the other legs:
#     scheduling PR   -> median T-3   (n=4 across 205 tickers. Exact, but late and RARE.)
#     CT.gov pcd      -> a WINDOW, never a day. Cannot be sharpened; do not try.
#     conference      -> the meeting date is published MONTHS out.
#
# A company that says "we will present topline SIGNAL-AA data at ESMO 2026" has told you the
# date. ESMO 2026 is 23-27 October. That is weeks of warning, not three days — and the runup is
# the trade, so warning is the entire game.
#
# HONESTY ABOUT WHAT WE KNOW: we know the CONFERENCE date, not the SESSION slot. A five-day
# meeting has five possible days and we do not know which. We therefore anchor on the meeting's
# FIRST day and say so. That is also the actionable date: the cardinal rule is to be out before
# the conference, so the open is what matters. We never invent a session time we have not seen.
CONF_DATA = re.compile(
    r'(?:top-?line|read-?out|primary\s+endpoint|pivotal|interim|full\s+(?:data|results)|'
    r'(?:phase\s*[123][^.]{0,30})?(?:data|results)|efficacy|late-?break)', re.I)
CONF_FWD = re.compile(
    r'\b(?:will|to)\s+(?:present|report|showcase|share)|upcoming|announces?\s+(?:upcoming\s+)?'
    r'(?:presentation|data\s+presentation)|to\s+be\s+presented|accepted\s+for\s+presentation', re.I)

def conference_readout_dates(tickers, key, when_from, when_to, limit=40, workers=8):
    """Upcoming conference presentations of DATA -> a readout date, known weeks in advance."""
    import concurrent.futures as _cf
    try:
        import requests
        import conference_presentations as CP
    except ImportError as e:
        print(f'  [conf] cannot import ({e}) — skipping conference leg')
        return []

    reg = CP.load_registry()
    d0, d1 = dt.date.fromisoformat(when_from), dt.date.fromisoformat(when_to)

    def scan(tk):
        out, seen = [], set()
        try:
            r = requests.get(FMP_PR, params={'symbols': tk, 'limit': limit, 'apikey': key}, timeout=20)
            rows = r.json() if r.status_code == 200 else []
        except Exception:
            return out
        if not isinstance(rows, list):
            return out
        for x in rows:
            if not isinstance(x, dict):
                continue
            title = str(x.get('title') or '')
            body = str(x.get('text') or x.get('content') or '')
            # Same bound, same reason — see PR_TEXT_CAP. A conference announcement names the
            # meeting in its headline ("... to Present Data at ESMO 2026"), never in the legal
            # boilerplate. Scanning the full body bought us nothing and cost us the process.
            blob = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', f'{title} . {body[:PR_TEXT_CAP]}'))
            pub = str(x.get('publishedDate') or x.get('date') or '')[:10]
            try:
                filed = dt.date.fromisoformat(pub)
            except Exception:
                filed = None

            conf = CP.detect_conference(blob)
            if not conf:
                continue
            # is this a FORWARD-looking presentation, or a recap of one that already happened?
            if not CONF_FWD.search(blob):
                continue
            if CP.prospectivity(blob) == 'past':
                continue
            # is DATA actually being presented? "will present at ESMO" with no data language is
            # a corporate-update slide, not a readout.
            if not CONF_DATA.search(blob):
                continue
            if not CLINICAL_ANCHOR.search(blob):
                continue

            year = CP.detect_year(blob, filed_dt=filed, mode='future')
            iso, prec, basis = CP.resolve_date(conf, year, reg, mode='future')
            if not iso:
                continue
            p0, p1 = period_bounds(iso)
            if not p0 or p1 < d0 or p0 > d1:
                continue
            k = (conf, iso)
            if k in seen:
                continue
            seen.add(k)

            ptype = CP.detect_pres_type(blob) or ''
            out.append(dict(
                ticker=tk, nct_id='', sponsor='', title=blob[:400],
                # trial_name on the FULL blob was the worst offender: _TRIAL_A/_TRIAL_B are
                # alternation-heavy and were being run over an entire document. Give it the
                # headline region, which is where the trial is actually named.
                trial=trial_name(blob[:600]), phase='', status='',
                pcd=iso, pcd_precision=prec, indication='', drug='', enrollment=None,
                cik='', form='PR', filed=pub,
                catalyst_date=iso, date_precision=prec, date_basis='conference_schedule',
                milestone='readout',
                conference=conf, pres_type=ptype,
                # a scheduled presentation at a dated meeting. Slightly under a company naming
                # an exact DAY for a topline PR (0.92), well above a CT.gov proxy (0.60-0.70).
                confidence=0.85 if basis == 'observed' else 0.55,
                source='fmp_press', source_url=x.get('url') or x.get('link') or '',
                # Conference dates and abstract acceptance are PUBLIC. Unlike the newswire leg,
                # nothing here is licensed data — the date comes from our own registry.
                redistribute=True,
                note=(f'{conf} presentation — date is the MEETING\'S FIRST DAY, not the session slot; '
                      f'the meeting runs several days'
                      if basis == 'observed' else
                      f'{conf} — no observed date for that year; month projected from the '
                      f'conference\'s usual timing. NOT a day.')))
        return out

    rows = []
    with _cf.ThreadPoolExecutor(workers) as ex:
        for r in ex.map(scan, tickers):
            rows += r
    obs = sum(1 for r in rows if r['date_precision'] == 'day')
    print(f'  [conf] {len(tickers)} tickers scanned -> {len(rows)} conference readouts '
          f'({obs} with a real meeting date, {len(rows)-obs} month-projected)')
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--from', dest='d_from', default=TODAY.isoformat())
    ap.add_argument('--to',   dest='d_to',   default='2026-12-31')
    ap.add_argument('--phases', default='PHASE1,PHASE2,PHASE3')
    ap.add_argument('--sponsor-class', default='INDUSTRY', help='INDUSTRY | "" for all')
    ap.add_argument('--listed-only', action='store_true', help='keep only trials mapped to a ticker')
    ap.add_argument('--include-enrolling', action='store_true',
                    help='ALSO emit trials that are still recruiting. They are NOT readouts — the date '
                         'will slip — but they are useful pipeline visibility. Clearly flagged.')
    ap.add_argument('--max-stale-days', type=int, default=120,
                    help='drop COMPLETED trials whose data lock is older than this. Beyond ~4 months '
                         'a silent trial has already announced (and just never posted to CT.gov).')
    ap.add_argument('--keep-pk', action='store_true',
                    help='keep PK / healthy-volunteer / bioavailability / DDI studies. They are not '
                         'catalysts and are dropped by default.')
    ap.add_argument('--completed-lookback', type=int, default=365,
                    help='how far back to look for COMPLETED trials whose topline is still pending')
    ap.add_argument('--sec', action='store_true',
                    help='ALSO mine company-stated guidance from SEC filings (8-K/6-K/10-Q/10-K/S-1/424B/20-F). '
                         'CT.gov gives a trial date; this gives what the company TOLD the market.')
    ap.add_argument('--sec-only', action='store_true', help='skip CT.gov, SEC guidance only')
    ap.add_argument('--max-docs', type=int, default=1200, help='cap on SEC documents fetched')
    ap.add_argument('--pr', action='store_true',
                    help='ALSO scan company scheduling PRs on the newswire (needs FMP_API_KEY). '
                         'This is the ONLY source of an EXACT DAY — a scheduling PR is never '
                         'attached to an 8-K, so SEC full-text cannot see it. Rows are marked '
                         'redistribute=False until FMP terms are verified.')
    ap.add_argument('--pr-limit', type=int, default=50, help='press releases fetched per ticker')
    ap.add_argument('--imminent-days', type=int, default=0,
                    help='keep only readouts within N days (plus OVERDUE pending-topline rows). '
                         'Drops DISTANT trials that merely stopped recruiting. 0 = keep all, tiered.')
    ap.add_argument('--no-enrich', action='store_true',
                    help='skip filing enrichment. By default, if FMP_API_KEY is set, the miner '
                         'pulls PRs for the imminent tickers to KILL already-read-out rows and '
                         'upgrade proxy dates to company-stated days (fast, ~15s). This flag turns '
                         'that off. Separate from the slow --pr sector sweep.')
    ap.add_argument('--pr-seeded', action='store_true',
                    help='restrict the newswire sweep to tickers CT.gov/SEC already found. FASTER, but '
                         'it can only confirm what we know — it cannot DISCOVER a readout those legs '
                         'missed, which is the whole point of the newswire. Default is a sector sweep.')
    ap.add_argument('--ua', default='pdufa.bio catalyst research contact@pdufa.bio')
    ap.add_argument('--out', default='phase_readouts_upcoming.csv')
    a = ap.parse_args()

    # Say out loud which keys resolved. The whole reason FMP never ran is that its absence
    # looked exactly like its presence: no error, no output, just a source quietly skipping
    # itself. Never again — an unusable key is now the first thing this run tells you.
    key_status()
    print()

    phases = [p.strip().upper() for p in a.phases.split(',') if p.strip()]
    statuses = 'RECRUITING|ACTIVE_NOT_RECRUITING|ENROLLING_BY_INVITATION|NOT_YET_RECRUITING'
    frames = []

    # ---------------- SOURCE 1: CT.gov — a PENDING READOUT, properly defined -------------
    #
    # I had this backwards and it shipped. A "phase readout" is NOT "a trial with a primary
    # completion date in the window". 69% of what we shipped (1,572 of 2,283) were trials
    # STILL RECRUITING PATIENTS. A trial that is still enrolling has not read out, will not
    # read out on its stated date, and does not belong on a readout calendar.
    #
    # Meanwhile the status filter EXCLUDED `COMPLETED` — trials that have already hit primary
    # completion and whose topline is imminent or overdue. Those are the most actionable rows
    # there are, and we were throwing every one of them away.
    #
    # A pending readout is exactly two things:
    #   A) ENROLLMENT CLOSED  — ACTIVE_NOT_RECRUITING, primary completion still ahead.
    #                           Last patient is in; the clock is running.
    #   B) DATA LOCK HIT      — COMPLETED, primary completion recently passed, and NO results
    #                           posted to CT.gov yet. Topline is imminent or already late.
    # Anything still enrolling is a PIPELINE entry, not a catalyst. It is opt-in via
    # --include-enrolling and is labelled so it can never be mistaken for a readout.
    if not a.sec_only:
        print(f'[1] CT.gov · {"/".join(phases)} · {a.sponsor_class or "ALL sponsors"}')
        parts = []

        print(f'    (A) enrollment closed, readout ahead  [{a.d_from} -> {a.d_to}]')
        sA = ctgov_all(a.d_from, a.d_to, phases, 'ACTIVE_NOT_RECRUITING', a.sponsor_class,
                       lambda p, g, t: print(f'        page {p}: {g}/{t}', flush=True))
        rA = [r for r in (parse_study(x) for x in sA) if r]
        for r in rA: r['readout_stage'] = 'enrollment_closed'
        print(f'        -> {len(rA)}')

        back = (dt.date.fromisoformat(a.d_from) - dt.timedelta(days=a.completed_lookback)).isoformat()
        print(f'    (B) data lock hit, topline pending, no results posted  [{back} -> {a.d_from}]')
        sB = ctgov_all(back, a.d_from, phases, 'COMPLETED', a.sponsor_class,
                       lambda p, g, t: print(f'        page {p}: {g}/{t}', flush=True),
                       agg='results:without')
        rB = [r for r in (parse_study(x) for x in sB) if r]
        for r in rB: r['readout_stage'] = 'completed_pending'
        print(f'        -> {len(rB)}')

        rows = rA + rB
        if a.include_enrolling:
            print(f'    (C) still enrolling  [opt-in — NOT a readout, pipeline visibility only]')
            sC = ctgov_all(a.d_from, a.d_to, phases,
                           'RECRUITING|NOT_YET_RECRUITING|ENROLLING_BY_INVITATION',
                           a.sponsor_class)
            rC = [r for r in (parse_study(x) for x in sC) if r]
            for r in rC: r['readout_stage'] = 'still_enrolling'
            print(f'        -> {len(rC)}  (flagged, not readouts)')
            rows += rC

        c = pd.DataFrame(rows).drop_duplicates(subset=['nct_id'])

        # (i) drop PK/plumbing — not catalysts
        c['is_catalyst'] = c.title.map(is_catalyst)
        n_pk = int((~c.is_catalyst).sum())
        if not a.keep_pk:
            c = c[c.is_catalyst]
            print(f'    dropped {n_pk} PK/healthy-volunteer/DDI studies (never announced, not readouts)')

        # (ii) age out the stale "completed" rows. CT.gov "no results posted" does NOT mean
        # "not announced" — companies PR their topline and often never post structured results.
        # A Phase 3 that locked 11 months ago and has said nothing has already spoken, or is in
        # trouble. Either way it is not an imminent readout.
        cp = c.readout_stage == 'completed_pending'
        if cp.any():
            # pcd mixes month ('2026-08') and day ('2025-07-14') precision. pd.to_datetime on a
            # MIXED-format series coerces the WHOLE series to NaT — silently. The filter then
            # dropped nothing and printed "dropped 0" while 944 stale rows sailed through.
            # Normalise to a full ISO date first.
            _p = c.pcd.astype(str).str.strip()
            _p = _p.where(_p.str.len() == 10, _p + '-01')
            age = (pd.Timestamp(dt.date.today()) - pd.to_datetime(_p, errors='coerce')).dt.days
            stale = cp & (age > a.max_stale_days)
            print(f'    dropped {int(stale.sum())} completed rows >{a.max_stale_days}d past data lock '
                  f'(almost certainly already announced by PR)')
            c = c[~stale]

        STAGE_CONF = {'enrollment_closed': 0.60, 'completed_pending': 0.70, 'still_enrolling': 0.20}
        c['catalyst_type']  = 'PhaseReadout'
        c['catalyst_date']  = c.pcd
        c['date_precision'] = c.pcd_precision
        c['date_basis']     = 'ctgov_pcd'
        c['confidence']     = c.readout_stage.map(STAGE_CONF).fillna(0.40)
        c['milestone']      = 'readout'
        c['source']         = 'clinicaltrials.gov'
        c['source_url']     = 'https://clinicaltrials.gov/study/' + c.nct_id

        # ---- completed_pending: the date we have is NOT the date of the event ----
        # For these trials the primary completion date has ALREADY PASSED (median 79 days, up to
        # 119). It is the DATA LOCK, not the readout. The readout is genuinely still ahead of us
        # and we do not know when it is.
        #
        # Assigning catalyst_date = pcd put 188 PAST dates into a file called "upcoming readouts",
        # where any calendar or API that trusts catalyst_date would publish them as future events.
        # LLY/orforglipron, RHHBY, NVS and VIR were all sitting there dated 2026-03-16.
        #
        # If we do not know the date, we do not print one. The lock date moves to its own column
        # (it is real, and it is the most useful thing about these rows — a trial that locked 4
        # months ago and has said nothing is overdue to speak). The row survives as a watchlist
        # entry. It just cannot masquerade as a scheduled event.
        c['data_lock_date'] = ''
        _cp = c.readout_stage == 'completed_pending'
        if _cp.any():
            c.loc[_cp, 'data_lock_date']  = c.loc[_cp, 'pcd']
            c.loc[_cp, 'catalyst_date']   = ''          # unknown. Say so.
            c.loc[_cp, 'date_precision']  = 'pending'   # NOT a date. Do not put it on a calendar.
            print(f'    {int(_cp.sum())} completed_pending rows: primary completion has PASSED, so the '
                  f'pcd is the DATA LOCK, not the readout.')
            print(f'      -> catalyst_date cleared, precision="pending", lock date kept in data_lock_date.')
            print(f'      -> these are a WATCHLIST (topline overdue), not calendar events.')

        c['note']           = c.readout_stage.map({
            'enrollment_closed': 'enrollment closed; primary completion ahead — readout is coming',
            'completed_pending': 'data lock ALREADY REACHED, no results posted — topline overdue. '
                                 'READOUT DATE UNKNOWN: the date in data_lock_date is the lock, not the event.',
            'still_enrolling':   'STILL ENROLLING — this is not a readout. Pipeline visibility only.'})
        c['cik']=''; c['form']=''; c['filed']=''
        print(f'    -> {len(c)} rows\n')
        frames.append(c)

    # ---------------- SOURCE 2: SEC filings (what the company TOLD the market) ------------
    if a.sec or a.sec_only:
        print(f'[2] SEC company communications · forms {GUIDANCE_FORMS}')
        print(f'    {len(GUIDANCE_PHRASES)} guidance phrases · max {a.max_docs} docs')
        g = sec_guidance_readouts(a.ua, a.d_from, a.d_to, max_docs=a.max_docs)
        if g:
            gdf = pd.DataFrame(g)
            gdf['catalyst_type'] = 'PhaseReadout'
            frames.append(gdf)
        print()

    if not frames: sys.exit('no sources produced rows')
    d = pd.concat(frames, ignore_index=True, sort=False)

    # ---------------- tickers ----------------
    print('resolving sponsors -> tickers ...')
    idx = sec_ticker_index()
    d['ticker'] = [resolve_ticker(sp, idx) for sp in d.sponsor.fillna('')]
    # SEC rows have no sponsor name but they DO have a CIK -> map it directly
    if (d.cik.fillna('') != '').any():
        j = json.load(open(SEC_TICKERS_CACHE)) if os.path.exists(SEC_TICKERS_CACHE) \
            else _sec_json('https://www.sec.gov/files/company_tickers.json')
        cik2t = {str(v['cik_str']): v['ticker'].upper() for v in j.values()}
        need = (d.ticker == '') & (d.cik.fillna('') != '')
        d.loc[need, 'ticker'] = [cik2t.get(str(c).lstrip('0'), '') for c in d.loc[need, 'cik']]
    hit = int((d.ticker != '').sum())
    print(f'  mapped to a US-listed ticker: {hit}/{len(d)} ({hit/max(len(d),1)*100:.0f}%)')

    if a.listed_only:
        d = d[d.ticker != '']

    # ---------------- [3] NEWSWIRE: the only source of an EXACT DAY ----------------
    # This leg runs LAST and deliberately reuses the ticker universe the first two legs
    # discovered. CT.gov and SEC tell us WHO has a readout coming; the newswire is the only
    # thing that tells us WHEN, to the day. See fmp_readout_dates() for why SEC cannot.
    if a.pr:
        key = os.environ.get('FMP_API_KEY')
        tks = sorted({t for t in d.ticker.fillna('') if t})
        print()
        if not key:
            # Loud, not silent. A skipped source that says nothing is how FMP sat dead for months.
            print('[3] NEWSWIRE — *** FMP_API_KEY MISSING, leg SKIPPED. No exact-day dates. ***')
        else:
            # SCANNING ONLY WHAT WE ALREADY FOUND CANNOT DISCOVER ANYTHING NEW.
            #
            # The first version fed this leg the tickers CT.gov and SEC had resolved. It found
            # zero exact-day readouts — not because the extractor failed (it pulls QTTB's
            # "July 13, 2026" perfectly) but because QTTB WAS NOT IN THE LIST. QTTB is precisely
            # the company the other two legs miss; that is the entire reason this leg exists.
            # A discovery source restricted to prior discoveries is just an echo.
            #
            # So by default we sweep the whole listed biotech/healthcare sector.
            if a.pr_seeded:
                print(f'[3] NEWSWIRE — seeded mode: only the {len(tks)} tickers found upstream')
                print('    (this CANNOT surface a company CT.gov/SEC missed — use the default sweep for that)')
            else:
                try:
                    import catalyst_crawler as CC
                    uni = CC.build_universe(key)
                except Exception as e:
                    uni = set()
                    print(f'    universe build failed ({e}); falling back to upstream tickers')
                tks = sorted(set(tks) | set(uni)) if uni else tks
                print(f'[3] NEWSWIRE — sector sweep · {len(tks)} tickers '
                      f'({len(uni)} listed healthcare + {len(set(tks)) - len(uni) if uni else 0} from CT.gov/SEC)')
            if not tks:
                print('    no tickers to scan')
            else:
                pr = fmp_readout_dates(tks, key, a.d_from, a.d_to, limit=a.pr_limit)
                if pr:
                    d = pd.concat([d, pd.DataFrame(pr)], ignore_index=True, sort=False)
                # [4] CONFERENCE — same PR corpus, different question. The newswire asks
                # "did they name a day?" (T-3, rare). This asks "did they say they'll present
                # data at a meeting whose date we already know?" (weeks of warning).
                cf_rows = conference_readout_dates(tks, key, a.d_from, a.d_to, limit=a.pr_limit)
                if cf_rows:
                    d = pd.concat([d, pd.DataFrame(cf_rows)], ignore_index=True, sort=False)

    # ---------------- dedupe: WITHIN each source only ----------------
    # I first deduped on (ticker, month) so that "company guidance would beat a CT.gov proxy".
    # That destroyed 389 real readouts: AstraZeneca has four different Phase 3 trials completing
    # in October and they are four different drugs, not one row said four ways.
    #
    # The honest constraint: a SEC guidance sentence usually carries NO NCT id, so we CANNOT
    # establish that it refers to the same trial as a given CT.gov record. So we do not pretend
    # to. We dedupe inside each source and keep both, clearly labelled by date_basis:
    #   ctgov_pcd        = trial-level. one row per NCT. "this trial completes in October."
    #   company_guidance = company-level. "we expect topline in 2H26." may or may not be the same trial.
    # Overlap is possible. Silently collapsing it would be worse than leaving it visible.
    before = len(d)
    ct = d[d.date_basis == 'ctgov_pcd'].drop_duplicates(subset=['nct_id'])

    gd = d[d.date_basis == 'company_guidance'].copy()
    if len(gd):
        if 'trial' not in gd.columns:
            gd['trial'] = ''
        gd['trial'] = gd['trial'].fillna('')
        # A readout is identified by the TRIAL, not by the filing that mentions it. Deduping on
        # the document meant every quarterly restatement of the same guidance survived as a new
        # readout — 8 real readouts became 13 rows. Key on the trial instead, and keep the MOST
        # RECENT filing, because the newest guidance is the guidance that is still true.
        #
        # If we could not name the trial, we DO NOT collapse: falling back to the document is
        # the conservative choice. Over-counting a readout is a bad day; silently merging two
        # different trials into one is a wrong number on a public page.
        gd['_key'] = gd.apply(
            lambda r: f"{r['ticker']}|{r['catalyst_date']}|{r['trial'].upper()}" if r['trial']
                      else f"{r['ticker']}|{r['catalyst_date']}|~doc:{r['source_url']}", axis=1)
        gd = (gd.sort_values('filed', ascending=False)   # newest guidance wins
                .drop_duplicates(subset=['_key'], keep='first')
                .drop(columns=['_key']))
    n_named = int((gd['trial'].astype(str) != '').sum()) if len(gd) else 0

    # The newswire leg is a THIRD source and must survive this step. Rebuilding `d` from
    # [ct, gd] alone would silently drop every company_pr row — the most valuable rows we have,
    # the only ones carrying an exact day. Dedupe it on its own terms and carry it through.
    pr = d[d.date_basis == 'company_pr'].copy()
    if len(pr):
        if 'trial' not in pr.columns:
            pr['trial'] = ''
        pr['trial'] = pr['trial'].fillna('')
        pr = pr.drop_duplicates(subset=['ticker', 'catalyst_date', 'trial'])

    # The conference leg is a FOURTH source. Rebuilding d from [ct, gd, pr] would silently drop
    # it — the same way [ct, gd] would have dropped the newswire. Every time a leg is added, the
    # concat that reassembles the frame is where it quietly dies. One key per ticker+conference:
    # a company presenting three abstracts at ESMO is ONE readout event, not three.
    cfr = d[d.date_basis == 'conference_schedule'].copy()
    if len(cfr):
        if 'conference' not in cfr.columns:
            cfr['conference'] = ''
        cfr = cfr.drop_duplicates(subset=['ticker', 'catalyst_date', 'conference'])

    d = pd.concat([ct, gd, pr, cfr], ignore_index=True, sort=False)
    print(f'  deduped within-source {before} -> {len(d)}  '
          f'(ct.gov {len(ct)} by NCT · guidance {len(gd)} by ticker+date+TRIAL, newest filing kept'
          + (f' · newswire {len(pr)} by ticker+date+trial' if len(pr) else '')
          + (f' · conference {len(cfr)} by ticker+conference' if len(cfr) else '') + ')')
    if len(gd):
        print(f'  trial named on {n_named}/{len(gd)} guidance rows '
              f'({n_named/len(gd)*100:.0f}%) — unnamed rows are NOT collapsed, by design')
    if len(gd):
        both = set(ct.ticker) & set(gd.ticker)
        print(f'  {len(both)} tickers appear in BOTH sources — these are not necessarily duplicates;'
              f' compare nct_id vs the guidance sentence before merging.')

    d['retrieved_at'] = dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z')

    # ---------------- IMMINENCE: how soon is each readout? ----------------
    # "Imminent readouts, not ones way out." Every row now carries days_to_readout and a tier, so
    # a distant trial that merely stopped recruiting is visibly separated from a readout that is
    # actually coming. Honesty about the anchor: for ctgov_pcd the countdown is to the DATA LOCK
    # (topline lands weeks-to-months after), so its tiers are labelled as a lead indicator.
    def _days_to(row):
        s = str(row.get('catalyst_date') or '').strip()
        if not s:                                    # completed_pending: date cleared -> use lock
            s = str(row.get('data_lock_date') or '').strip()
        if not s:
            return None
        p0, p1 = period_bounds(s)
        # a window's imminence is its NEAR edge (a "2H26" readout could be as soon as July)
        anchor = p0 or p1
        return (anchor - TODAY).days if anchor else None
    d['days_to_readout'] = d.apply(_days_to, axis=1)

    def _tier(row):
        if row.get('readout_stage') == 'completed_pending':
            return 'OVERDUE'                         # data locked, topline not yet posted
        n = row.get('days_to_readout')
        if n is None:                return 'UNDATED'
        if n < 0:                    return 'PAST'
        if n <= 45:                  return 'IMMINENT'
        if n <= 90:                  return 'NEAR'
        if n <= 180:                 return 'SCHEDULED'
        return 'DISTANT'
    d['imminence'] = d.apply(_tier, axis=1)

    # ---------------- [5] FILING ENRICHMENT: real dates + kill the dead ----------------
    # CT.gov gave a proxy and told us WHO is imminent. Now go to the filings for the truth:
    # upgrade proxy dates to company-stated days, and KILL readouts that already happened.
    #
    # This is DECOUPLED from the --pr sector sweep. The sweep scans 900+ tickers for brand-new
    # exact dates (slow). This only fetches PRs for the ~50 tickers CT.gov already flagged as
    # imminent (fast, ~15s) and is the single highest-value scrub — it keeps dead readouts off
    # the calendar. So it runs on ANY run that has an FMP key, not just --pr. Opt out with
    # --no-enrich. It needs ctgov rows (imminence tiers), so it is skipped on --sec-only.
    key = os.environ.get('FMP_API_KEY')
    if not a.no_enrich and key and (d.date_basis == 'ctgov_pcd').any():
        print('\n[5] FILING ENRICHMENT — company PRs are where readout dates actually live')
        d, n_kill, n_up, n_flag = enrich_from_filings(d, key)
        # a readout that already happened must come off the forward feed. Keep it in a sidecar
        # so nothing is silently deleted — a kill is auditable.
        done = d[d.readout_stage == 'read_out']
        if len(done):
            _rf = f'ro_already_read_out_{dt.datetime.now().strftime("%H%M%S")}.csv'
            done.to_csv(_rf, index=False, quoting=__import__('csv').QUOTE_ALL)
            d = d[d.readout_stage != 'read_out']
            print(f'  [5] removed {len(done)} already-read-out rows from the forward feed -> {_rf}')
        # re-tier: an upgraded date may have changed imminence
        d['days_to_readout'] = d.apply(_days_to, axis=1)
        d['imminence'] = d.apply(_tier, axis=1)
    elif not a.no_enrich and not key:
        print('\n[5] FILING ENRICHMENT — skipped: FMP_API_KEY not set (cannot reach company PRs)')

    # optional hard filter: keep only readouts within a horizon. DISTANT trials that merely
    # stopped recruiting are not "upcoming readouts". OVERDUE (pending topline) is kept — it is the
    # opposite problem, and still actionable. Off by default; the tiers alone let you filter.
    if a.imminent_days:
        keepmask = (d.imminence != 'DISTANT') | (d.readout_stage == 'completed_pending')
        keepmask &= (d.days_to_readout.isna()) | (d.days_to_readout <= a.imminent_days) | \
                    (d.readout_stage == 'completed_pending')
        ndrop = int((~keepmask).sum())
        d = d[keepmask]
        print(f'\n--imminent-days {a.imminent_days}: dropped {ndrop} rows reading out beyond the horizon')

    d = d.sort_values(['days_to_readout'], na_position='last')
    # `redistribute` MUST reach the CSV. A row that cannot be published is only safe if the
    # thing that says so travels WITH it. Default True (CT.gov and SEC are public record);
    # the newswire leg sets False until FMP's terms are read.
    if 'redistribute' not in d.columns:
        d['redistribute'] = True
    d['redistribute'] = d['redistribute'].fillna(True)

    keep = ['ticker','catalyst_type','catalyst_date','date_precision','date_basis','confidence',
            'imminence','days_to_readout','redistribute','readout_stage','data_lock_date','milestone',
            'trial','conference','pres_type','phase','status','drug','indication','nct_id','sponsor',
            'enrollment','title','source','source_url','form','filed','note','retrieved_at']
    d = d.reindex(columns=[c for c in keep if c in d.columns])
    d.to_csv(a.out, index=False)

    print(f'\n-> {a.out}  ({len(d)} rows)')
    if 'readout_stage' in d.columns:
        print('\nby readout stage:')
        LBL={'enrollment_closed':'enrollment CLOSED, readout ahead',
             'completed_pending':'data lock HIT, topline pending',
             'still_enrolling':'STILL ENROLLING (not a readout)'}
        for st,n in d.readout_stage.value_counts(dropna=False).items():
            print(f'   {str(st):20s} {n:5d}  {LBL.get(st,"")}')
    print('\nby source:')
    for b, n in d.date_basis.value_counts().items():
        print(f'   {b:18s} {n:4d}')
    print('\nby month:')
    for m, n in d.catalyst_date.astype(str).str[:7].value_counts().sort_index().items():
        print(f'   {m}  {n:4d}')
    print(f'\n{len(d)} readouts across {d.ticker.nunique()} tickers')
    firm = d[d.confidence >= 0.60]
    print(f'HIGH confidence (company-stated, or fully-enrolled trial): {len(firm)}')

    # ---------------- self-check: did contamination get back in? ----------------
    # The SEC leg once shipped 30% enrollment milestones and 15% 10-Q accounting boilerplate
    # ("condensed results of operations ... December 31, 2026" -> a fiscal year-end on the
    # readout calendar). If that ever returns, say so loudly rather than let it ship quietly.
    g2 = d[d.date_basis == 'company_guidance']
    if len(g2):
        w = g2.title.astype(str)
        fin  = int(w.str.contains(FINANCIAL_NOISE).sum())
        noclin = int((~w.str.contains(CLINICAL_ANCHOR)).sum())
        enr  = int((w.str.contains(ENROLL_TOK) & ~w.str.contains(READOUT_TOK)).sum())
        sub  = int((w.str.contains(SUBMISSION_TOK) & ~w.str.contains(READOUT_TOK)).sum())
        # RE-DECIDE, don't re-pattern-match. This is the only check that can catch an
        # APGE-class error ("Initiation of ... Phase 3 trial expected 2H 2026" sitting in a
        # bullet list that also says "data readout"), because that window trips every
        # token-presence test as clean while the date belongs to the wrong milestone.
        mis = 0
        if {'_ctx', '_dpos'} <= set(g2.columns):
            for _, r in g2.iterrows():
                try:
                    c, p = str(r['_ctx']), int(r['_dpos'])
                except Exception:
                    continue
                if milestone_of(c, p, p + 8) != 'readout':
                    mis += 1

        print()
        print('self-check on the guidance leg:')
        print(f'   financial boilerplate   : {fin}   (must be 0)')
        print(f'   no clinical anchor      : {noclin}   (must be 0)')
        print(f'   enrollment-only         : {enr}   (must be 0)')
        print(f'   regulatory submission   : {sub}   (must be 0 — a BLA filing is not a readout)')
        print(f'   re-decided != readout   : {mis}   (must be 0 — attribution re-run on the same window)')
        if fin or noclin or enr or sub or mis:
            print('   *** WARNING: contamination detected. Do NOT publish this file. ***')
        else:
            print('   clean — every guidance row is a clinical readout, not an enrollment or fiscal date.')

    # The scheduling PRs are the whole point: a company that NAMES A DAY has committed.
    if 'date_precision' in d.columns and 'date_basis' in d.columns:
        hard = d[(d.date_precision == 'day') &
                 (d.date_basis.isin(['company_guidance', 'company_pr', 'conference_schedule']))
                 ].sort_values('catalyst_date')
        if len(hard):
            print()
            print(f'EXACT-DAY readout dates: {len(hard)}')
            print('   everything else is a window. LEAD TIME is what makes these tradeable:')
            print('     company_pr          — a named day. Measured median lead: T-3. Exact but LATE.')
            print('     conference_schedule — a dated meeting. Lead: WEEKS. This is the early one.')
            print()
            for _, r in hard.head(40).iterrows():
                lead = ''
                try:
                    lead = f"T-{(dt.date.fromisoformat(str(r.catalyst_date)) - TODAY).days}"
                except Exception:
                    pass
                tag = str(r.get('conference') or r.get('trial') or '?')
                print(f"   {r.catalyst_date} {lead:>6s}  {str(r.ticker):6s} "
                      f"{r.date_basis:19s} [{tag:9s}] {str(r.title)[:44]}")

    # ---------------- INVARIANT: a forward calendar contains no past dates ----------------
    # This is the check that would have caught the completed_pending bug on day one. 188 rows
    # carried a catalyst_date up to 119 days in the past, and nothing complained, because every
    # gate we had was asking "is this row about a readout?" — never "is this date in the future?"
    # State the invariant, and assert it.
    dated = d[d.catalyst_date.astype(str).str.strip().ne('') &
              d.date_precision.ne('pending')].copy()
    def _ends(s):
        try:
            return period_bounds(str(s))[1]
        except Exception:
            return None
    dated['_end'] = dated.catalyst_date.map(_ends)
    stale = dated[dated._end.notna() & (dated._end < TODAY)]
    try:
        asked_back = dt.date.fromisoformat(a.d_from) < TODAY
    except Exception:
        asked_back = False
    print()
    if len(stale) and asked_back:
        # Not a violation — the operator explicitly asked for a window that opens in the past.
        # Say what it is instead of screaming. A check that cries wolf gets ignored, and an
        # ignored check is worse than no check.
        print(f'{len(stale)} dated rows lie before today — expected: you asked for --from {a.d_from}, '
              f'which opens {(TODAY - dt.date.fromisoformat(a.d_from)).days}d in the past.')
        print('   (run without --from, or with --from today, for a strictly forward calendar)')
    elif len(stale):
        print(f'invariant — no dated row may lie in the past: {len(stale)} VIOLATIONS '
              f'(of {len(dated)} dated rows)')
        print('   *** A DATE THAT HAS ALREADY PASSED IS ON A FORWARD CALENDAR. ***')
        for _, r in stale.head(8).iterrows():
            print(f'   {r.catalyst_date}  {str(r.ticker):6s} {r.date_basis}  {str(r.get("note"))[:44]}')
    else:
        print(f'invariant — no dated row lies in the past: clean ({len(dated)} dated rows, all ahead of us).')

    # ---------------- imminence breakdown: what's actually SOON vs merely upcoming ----------------
    if 'imminence' in d.columns:
        print()
        print('imminence (how soon is the readout):')
        order = ['IMMINENT', 'NEAR', 'SCHEDULED', 'DISTANT', 'OVERDUE', 'UNDATED', 'PAST']
        vc = d.imminence.value_counts()
        LBL = {'IMMINENT': '<=45d — coming soon', 'NEAR': '46-90d', 'SCHEDULED': '91-180d',
               'DISTANT': '>180d — merely stopped recruiting, NOT imminent',
               'OVERDUE': 'data locked, topline pending', 'UNDATED': 'no date',
               'PAST': 'window closed (should be 0)'}
        for t in order:
            if t in vc:
                print(f'   {t:10s} {int(vc[t]):4d}  {LBL.get(t,"")}')
        imm = d[d.imminence == 'IMMINENT'].sort_values('days_to_readout')
        if len(imm):
            print()
            print(f'the {len(imm)} IMMINENT readouts (<=45 days):')
            for _, r in imm.head(25).iterrows():
                nm = str(r.get('trial') or r.get('drug') or r.get('title') or '')[:34]
                print(f'   T-{int(r.days_to_readout):<3} {r.catalyst_date}  {str(r.ticker):6s} '
                      f'{str(r.date_basis):18s} {nm}')

    # A row that must not be published is only safe if the reason travels WITH it — and if we
    # say so out loud at the end of every run, not just in a comment nobody reads.
    if 'redistribute' in d.columns:
        blocked = d[d.redistribute == False]          # noqa: E712 — pandas mask, not a bool test
        if len(blocked):
            print()
            print(f'*** {len(blocked)} rows are marked redistribute=False — DO NOT PUBLISH ***')
            print('    source: FMP newswire. Their redistribution terms are UNVERIFIED (backlog P2-6).')
            print('    Use these as a private QA yardstick only — the slot BioPharmaCatalyst occupies.')
            print('    Nothing with redistribute=False may reach the site, the API, or the sitemap.')


if __name__ == '__main__':
    main()
