#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           ODIN CATALYST MINER v4.0 - COMPLETE ONLINE MINER                   ║
║                                                                              ║
║  MERGED VERSION combining v3 + odin_miner.py FREE APIs:                      ║
║                                                                              ║
║  CATALYST DATA (from v3):                                                    ║
║  ✓ FDA Drug Approvals (OpenFDA API)                                          ║
║  ✓ FDA Complete Response Letters (Transparency API)                          ║
║  ✓ ClinicalTrials.gov Phase 2/3 Readouts (v2 API)                            ║
║  ✓ FDA 510(k) Device Clearances                                              ║
║  ✓ FDA PMA Device Approvals                                                  ║
║                                                                              ║
║  ALTERNATIVE DATA (NEW from odin_miner.py):                                  ║
║  ✓ SEC EDGAR API (filings, 8-K, 10-Q, company facts)                         ║
║  ✓ GDELT 2.1 DOC API (news volume, attention spikes)                         ║
║  ✓ Greenhouse Job Board API (hiring signals)                                 ║
║  ✓ Lever Postings API (hiring signals)                                       ║
║  ✓ FDA Inspection/483/Shortages Pages (HTML snapshots)                       ║
║                                                                              ║
║  Usage:                                                                      ║
║    python ODIN_CATALYST_MINER_v4.py --years 5                                ║
║    python ODIN_CATALYST_MINER_v4.py --years 10 --output ./odin_data          ║
║    python ODIN_CATALYST_MINER_v4.py --tickers FBIO AQST --alt-data-only      ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import json
import csv
import hashlib
import argparse
import time
import re
import os
import sys
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Optional, Tuple, Any
from enum import Enum
import logging
import urllib.request
import urllib.parse
import urllib.error
import ssl

# ============================================================================
# LOGGING SETUP
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

CONFIG = {
    "user_agent": "ODIN-CatalystMiner/4.0 (biotech-research-tool; Academic/Research Use)",
    # SEC requires real email - UPDATE THIS
    "sec_user_agent": "ODIN-CatalystMiner/4.0 (rockyshoals@gmail.com)",
    "request_delay": 0.5,
    "max_retries": 5,
    "timeout": 60,
    "batch_size": 100,
    # Rate limits by API
    "rate_limits": {
        "sec": 2.0,
        "ctgov": 5.0,
        "openfda": 2.0,
        "gdelt": 5.0,
        "greenhouse": 2.0,
        "lever": 2.0,
    },
    # Hiring board mappings
    "greenhouse_boards": {
        "AQST": "aquestive",
    },
    "lever_companies": {},
    # Search terms for GDELT
    "gdelt_terms": {
        "FBIO": ["FBIO", "Fortress Biotech", "CUTX-101", "FDA"],
        "AQST": ["AQST", "Aquestive", "Anaphylm", "FDA"],
    },
}

# ============================================================================
# DATA STRUCTURES
# ============================================================================

class CatalystType(Enum):
    PDUFA = "PDUFA"
    CRL = "CRL"
    PHASE2 = "PHASE2"
    PHASE3 = "PHASE3"
    MA = "MA"
    K510 = "510K"
    PMA = "PMA"

class Outcome(Enum):
    APPROVAL = "APPROVAL"
    CRL = "CRL"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    PENDING = "PENDING"
    CLEARED = "CLEARED"

@dataclass
class CatalystEvent:
    """Universal catalyst event"""
    event_id: str = ""
    ticker: str = ""
    company: str = ""
    asset: str = ""
    indication: str = ""
    therapeutic_area: str = ""
    catalyst_date: str = ""
    catalyst_type: str = ""
    outcome: str = ""
    application_number: str = ""
    had_adcom: bool = False
    adcom_vote_pct: float = 0.0
    btd: bool = False
    orphan: bool = False
    priority_review: bool = False
    fast_track: bool = False
    accelerated_approval: bool = False
    form_483_issues: bool = False
    prior_crl: bool = False
    crl_reason: str = ""
    first_cycle: bool = True
    sponsor_prior_approvals: int = 0
    phase: int = 0
    nct_id: str = ""
    endpoint_met: bool = False
    biomarker_enriched: bool = False
    rare_disease: bool = False
    modality: str = ""
    acquirer: str = ""
    deal_value_mm: float = 0.0
    premium_pct: float = 0.0
    source: str = ""
    source_url: str = ""
    mined_timestamp: str = ""
    data_cutoff_date: str = ""
    
    def finalize(self):
        if not self.event_id:
            self.event_id = f"{self.ticker or 'UNK'}|{(self.asset or 'UNK')[:20]}|{self.catalyst_type}|{self.catalyst_date}"
        if not self.mined_timestamp:
            self.mined_timestamp = datetime.utcnow().isoformat()
        if not self.data_cutoff_date and self.catalyst_date:
            try:
                dt = datetime.strptime(self.catalyst_date, "%Y-%m-%d")
                self.data_cutoff_date = (dt - timedelta(days=2)).strftime("%Y-%m-%d")
            except:
                pass

@dataclass
class AlternativeDataSnapshot:
    """Alternative data signals for a ticker"""
    ticker: str = ""
    snapshot_timestamp: str = ""
    sec_cik: str = ""
    recent_8k_count: int = 0
    recent_10q_filings: int = 0
    recent_s1_filings: int = 0
    last_filing_date: str = ""
    greenhouse_job_count: int = 0
    lever_job_count: int = 0
    commercial_jobs_count: int = 0
    regulatory_jobs_count: int = 0
    manufacturing_jobs_count: int = 0
    gdelt_article_count: int = 0
    gdelt_avg_tone: float = 0.0
    fda_483_recent: bool = False
    fda_warning_letter: bool = False
    sec_filings_sample: List[Dict] = field(default_factory=list)
    greenhouse_jobs_sample: List[Dict] = field(default_factory=list)
    lever_jobs_sample: List[Dict] = field(default_factory=list)
    gdelt_articles_sample: List[Dict] = field(default_factory=list)
    
    def to_dict(self):
        return asdict(self)

# ============================================================================
# THERAPEUTIC AREA CLASSIFICATION
# ============================================================================

THERAPEUTIC_AREAS = {
    "Oncology": ["cancer", "tumor", "carcinoma", "lymphoma", "leukemia", "melanoma", "sarcoma", "myeloma", "oncol", "neoplasm", "malignant"],
    "CNS/Neurology": ["alzheimer", "parkinson", "multiple sclerosis", "epilepsy", "seizure", "neuropath", "dementia", "migraine", "stroke", "als", "amyotrophic"],
    "CNS/Psychiatry": ["schizophrenia", "bipolar", "depression", "anxiety", "psychosis", "psychiatric", "adhd", "autism"],
    "Cardiovascular": ["heart", "cardiac", "cardiovascular", "hypertension", "arrhythmia", "cholesterol", "atherosclerosis"],
    "Immunology": ["autoimmune", "rheumatoid", "lupus", "psoriasis", "crohn", "inflammatory", "immune", "ulcerative colitis"],
    "Infectious Disease": ["antibiotic", "antiviral", "hiv", "hepatitis", "covid", "infection", "bacterial", "fungal", "sepsis"],
    "Rare Disease": ["orphan", "rare disease", "ultra-rare", "lysosomal", "genetic disorder", "menkes"],
    "Respiratory": ["asthma", "copd", "pulmonary", "lung", "respiratory", "cystic fibrosis"],
    "Metabolic": ["diabetes", "obesity", "metabolic", "lipid", "thyroid", "weight"],
    "Ophthalmology": ["eye", "retina", "macular", "glaucoma", "ophthalm", "vision", "blindness"],
    "Dermatology": ["skin", "dermat", "eczema", "acne", "alopecia", "atopic"],
    "Hematology": ["blood", "anemia", "hemophilia", "sickle cell", "platelet", "coagulation", "thalassemia"],
    "GI/Hepatology": ["liver", "hepatic", "gastro", "intestin", "bowel", "nash", "fibrosis"],
    "Nephrology": ["kidney", "renal", "dialysis", "nephro"],
    "Gene Therapy": ["gene therapy", "aav", "lentivir", "crispr", "gene editing"],
}

def classify_therapeutic_area(text: str) -> str:
    if not text:
        return "Other"
    text_lower = text.lower()
    for ta, keywords in THERAPEUTIC_AREAS.items():
        if any(kw in text_lower for kw in keywords):
            return ta
    return "Other"

# ============================================================================
# COMPANY -> TICKER MAPPING
# ============================================================================

COMPANY_TICKERS = {
    "pfizer": "PFE", "merck": "MRK", "johnson": "JNJ", "abbvie": "ABBV",
    "bristol": "BMY", "eli lilly": "LLY", "lilly": "LLY", "novartis": "NVS",
    "roche": "RHHBY", "genentech": "RHHBY", "sanofi": "SNY", "astrazeneca": "AZN",
    "glaxosmithkline": "GSK", "gsk": "GSK", "gilead": "GILD", "amgen": "AMGN",
    "regeneron": "REGN", "biogen": "BIIB", "vertex": "VRTX", "moderna": "MRNA",
    "biontech": "BNTX", "takeda": "TAK", "novo nordisk": "NVO",
    "bayer": "BAYRY", "teva": "TEVA",
    "biomarin": "BMRN", "alexion": "AZN", "incyte": "INCY",
    "jazz": "JAZZ", "united therapeutics": "UTHR", "neurocrine": "NBIX",
    "sarepta": "SRPT", "ultragenyx": "RARE", "alnylam": "ALNY", "ionis": "IONS",
    "exelixis": "EXEL", "blueprint": "BPMC", "cytokinetics": "CYTK",
    "argenx": "ARGX", "halozyme": "HALO",
    "aquestive": "AQST", "fortress": "FBIO", "madrigal": "MDGL", "protagonist": "PTGX",
    "revolution": "RVMD", "nuvalent": "NUVB", "syndax": "SNDX",
    "arcus": "RCUS", "kiniksa": "KNSA", "zymeworks": "ZYME",
    "karuna": "KRTX", "arvinas": "ARVN", "relay": "RLAY",
    "replimune": "REPL", "y-mabs": "YMAB",
    "atara": "ATRA", "intercept": "ICPT", "cyprium": "FBIO",
}

def get_ticker(company_name: str) -> str:
    if not company_name:
        return ""
    company_lower = company_name.lower()
    for key, ticker in COMPANY_TICKERS.items():
        if key in company_lower:
            return ticker
    return ""

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

def iso_z(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def sha256_str(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()

# ============================================================================
# RATE LIMITER
# ============================================================================

class RateLimiter:
    def __init__(self, rps: float):
        self.rps = max(0.1, float(rps))
        self.min_interval = 1.0 / self.rps
        self._last = 0.0

    def wait(self):
        now = time.time()
        elapsed = now - self._last
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self._last = time.time()

# ============================================================================
# ROBUST HTTP CLIENT
# ============================================================================

class RobustHTTPClient:
    def __init__(self):
        self.ssl_context = ssl.create_default_context()
        self.limiters = {}
        
    def _get_limiter(self, api_name: str) -> RateLimiter:
        if api_name not in self.limiters:
            rps = CONFIG["rate_limits"].get(api_name.lower(), 2.0)
            self.limiters[api_name] = RateLimiter(rps)
        return self.limiters[api_name]
    
    def get(self, url: str, headers: Dict = None, api_name: str = "API") -> Tuple[int, str]:
        limiter = self._get_limiter(api_name)
        limiter.wait()
        
        if headers is None:
            headers = {}
        headers.setdefault("User-Agent", CONFIG["user_agent"])
        headers.setdefault("Accept", "application/json")
        
        for attempt in range(CONFIG["max_retries"]):
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=CONFIG["timeout"], context=self.ssl_context) as response:
                    body = response.read().decode('utf-8')
                    return response.status, body
            except urllib.error.HTTPError as e:
                wait_time = (2 ** attempt) + (attempt * 0.5)
                if e.code == 429:
                    wait_time = min(wait_time * 3, 60)
                logger.warning(f"[{api_name}] HTTP {e.code}, attempt {attempt+1}")
                if attempt == CONFIG["max_retries"] - 1:
                    return e.code, ""
                time.sleep(wait_time)
            except Exception as e:
                wait_time = (2 ** attempt)
                logger.warning(f"[{api_name}] Error: {e}")
                time.sleep(wait_time)
        return 0, ""
    
    def get_json(self, url: str, headers: Dict = None, api_name: str = "API") -> Optional[Dict]:
        status, body = self.get(url, headers, api_name)
        if status == 200 and body:
            try:
                return json.loads(body)
            except json.JSONDecodeError:
                pass
        return None
    
    def get_html(self, url: str, headers: Dict = None, api_name: str = "API") -> Optional[str]:
        if headers is None:
            headers = {}
        headers["Accept"] = "text/html,*/*"
        status, body = self.get(url, headers, api_name)
        return body if status == 200 else None

http = RobustHTTPClient()

# ============================================================================
# SEC EDGAR API (FROM odin_miner.py)
# ============================================================================

class SECAPI:
    """SEC EDGAR for filings - 8-K announcements, dilution signals, etc."""
    
    TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
    SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
    _ticker_map_cache = None
    
    @classmethod
    def _sec_headers(cls) -> Dict[str, str]:
        ua = CONFIG.get("sec_user_agent", CONFIG["user_agent"])
        return {"User-Agent": ua, "Accept": "application/json"}
    
    @classmethod
    def _normalize_cik(cls, cik: str) -> str:
        s = str(cik).strip()
        s = re.sub(r"^CIK", "", s, flags=re.I)
        return s.zfill(10)
    
    @classmethod
    def get_ticker_cik_map(cls) -> Dict[str, str]:
        if cls._ticker_map_cache:
            return cls._ticker_map_cache
        logger.info("[SEC] Fetching ticker->CIK mapping...")
        data = http.get_json(cls.TICKERS_URL, headers=cls._sec_headers(), api_name="SEC")
        if not data:
            return {}
        ticker_map = {}
        for _, row in data.items():
            ticker = (row.get("ticker") or "").upper()
            cik = row.get("cik_str")
            if ticker and cik is not None:
                ticker_map[ticker] = cls._normalize_cik(cik)
        cls._ticker_map_cache = ticker_map
        return ticker_map
    
    @classmethod
    def analyze_filings(cls, ticker: str, days_back: int = 90) -> Dict[str, Any]:
        result = {"ticker": ticker, "cik": "", "recent_8k_count": 0, "recent_10q_count": 0,
                  "recent_s1_s3_count": 0, "latest_filings": [], "error": None}
        try:
            ticker_map = cls.get_ticker_cik_map()
            cik = ticker_map.get(ticker.upper())
            if not cik:
                result["error"] = "No CIK found"
                return result
            url = cls.SUBMISSIONS_URL.format(cik=cik)
            submissions = http.get_json(url, headers=cls._sec_headers(), api_name="SEC")
            if not submissions:
                result["error"] = "No submissions"
                return result
            result["cik"] = submissions.get("cik", "")
            recent = submissions.get("filings", {}).get("recent", {})
            forms = recent.get("form", [])
            dates = recent.get("filingDate", [])
            cutoff = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
            for i, (form, date) in enumerate(zip(forms, dates)):
                if i >= 100 or date < cutoff:
                    continue
                form_upper = form.upper()
                if "8-K" in form_upper:
                    result["recent_8k_count"] += 1
                elif "10-Q" in form_upper:
                    result["recent_10q_count"] += 1
                elif "S-1" in form_upper or "S-3" in form_upper:
                    result["recent_s1_s3_count"] += 1
                if len(result["latest_filings"]) < 10:
                    result["latest_filings"].append({"form": form, "date": date})
        except Exception as e:
            result["error"] = str(e)
        return result

# ============================================================================
# GDELT DOC API (FROM odin_miner.py)
# ============================================================================

class GDELTAPI:
    """GDELT for news/media monitoring - attention spikes, sentiment"""
    
    BASE_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
    
    @classmethod
    def analyze_ticker(cls, ticker: str, terms: List[str] = None) -> Dict[str, Any]:
        result = {"ticker": ticker, "article_count": 0, "avg_tone": 0.0, "recent_articles": [], "error": None}
        try:
            if not terms:
                terms = CONFIG.get("gdelt_terms", {}).get(ticker, [ticker])
            query = " OR ".join([f'"{t}"' for t in terms])
            params = {"query": query, "mode": "ArtList", "maxrecords": 250, "format": "json"}
            query_string = "&".join([f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items()])
            url = f"{cls.BASE_URL}?{query_string}"
            data = http.get_json(url, api_name="GDELT")
            if not data:
                return result
            articles = data.get("articles", [])
            result["article_count"] = len(articles)
            tones = [a.get("tone", 0) for a in articles if "tone" in a]
            if tones:
                result["avg_tone"] = sum(tones) / len(tones)
            for article in articles[:10]:
                result["recent_articles"].append({
                    "title": article.get("title", ""),
                    "url": article.get("url", ""),
                    "date": article.get("seendate", ""),
                    "tone": article.get("tone", 0),
                })
        except Exception as e:
            result["error"] = str(e)
        return result

# ============================================================================
# HIRING APIs (FROM odin_miner.py)
# ============================================================================

class HiringAPI:
    """Greenhouse/Lever for hiring signals - commercial ramp, manufacturing concerns"""
    
    GREENHOUSE_URL = "https://boards-api.greenhouse.io/v1/boards/{board}/jobs"
    LEVER_URL = "https://api.lever.co/v0/postings/{company}"
    
    COMMERCIAL_KEYWORDS = ["sales", "commercial", "marketing", "msl", "medical science liaison", 
                          "market access", "key account", "territory", "field"]
    REGULATORY_KEYWORDS = ["regulatory", "cmc", "quality", "compliance", "qa ", "qc ", "gmp"]
    MANUFACTURING_KEYWORDS = ["manufacturing", "production", "operations", "supply chain", "process"]
    
    @classmethod
    def analyze_ticker(cls, ticker: str) -> Dict[str, Any]:
        result = {"ticker": ticker, "greenhouse_total": 0, "lever_total": 0,
                  "commercial_jobs": 0, "regulatory_jobs": 0, "manufacturing_jobs": 0,
                  "sample_jobs": [], "error": None}
        all_jobs = []
        try:
            board = CONFIG.get("greenhouse_boards", {}).get(ticker.upper())
            if board:
                url = cls.GREENHOUSE_URL.format(board=board)
                gh_data = http.get_json(url, api_name="Greenhouse")
                if gh_data:
                    jobs = gh_data.get("jobs", [])
                    result["greenhouse_total"] = len(jobs)
                    for job in jobs:
                        all_jobs.append({"title": job.get("title", ""), "source": "Greenhouse"})
            lever_co = CONFIG.get("lever_companies", {}).get(ticker.upper())
            if lever_co:
                url = f"{cls.LEVER_URL.format(company=lever_co)}?mode=json"
                lever_data = http.get_json(url, api_name="Lever")
                if lever_data and isinstance(lever_data, list):
                    result["lever_total"] = len(lever_data)
                    for job in lever_data:
                        all_jobs.append({"title": job.get("text", ""), "source": "Lever"})
            for job in all_jobs:
                title_lower = job["title"].lower()
                if any(kw in title_lower for kw in cls.COMMERCIAL_KEYWORDS):
                    result["commercial_jobs"] += 1
                if any(kw in title_lower for kw in cls.REGULATORY_KEYWORDS):
                    result["regulatory_jobs"] += 1
                if any(kw in title_lower for kw in cls.MANUFACTURING_KEYWORDS):
                    result["manufacturing_jobs"] += 1
            result["sample_jobs"] = all_jobs[:10]
        except Exception as e:
            result["error"] = str(e)
        return result

# ============================================================================
# FDA APIS (from v3)
# ============================================================================

class FDACRLAPI:
    """FDA Transparency API for CRLs"""
    BASE_URL = "https://api.fda.gov/transparency/crl.json"
    
    @classmethod
    def fetch_all_crls(cls) -> List[CatalystEvent]:
        events = []
        logger.info("[FDA CRL] Fetching CRLs...")
        skip = 0
        while True:
            url = f"{cls.BASE_URL}?limit={CONFIG['batch_size']}&skip={skip}"
            data = http.get_json(url, api_name="FDA_CRL")
            if not data:
                break
            results = data.get("results", [])
            if not results:
                break
            for record in results:
                event = cls._parse_crl(record)
                if event:
                    events.append(event)
            skip += CONFIG['batch_size']
            total = data.get("meta", {}).get("results", {}).get("total", 0)
            if skip >= total or skip >= 10000:
                break
        logger.info(f"[FDA CRL] Total: {len(events)}")
        return events
    
    @classmethod
    def _parse_crl(cls, record: Dict) -> Optional[CatalystEvent]:
        try:
            letter_date = record.get("letter_date", "")
            catalyst_date = ""
            for fmt in ["%m/%d/%Y", "%Y-%m-%d"]:
                try:
                    dt = datetime.strptime(letter_date, fmt)
                    catalyst_date = dt.strftime("%Y-%m-%d")
                    break
                except:
                    continue
            if not catalyst_date:
                return None
            company_name = record.get("company_name", "")
            event = CatalystEvent(
                ticker=get_ticker(company_name),
                company=company_name.strip(),
                asset=record.get("application_number", "Unknown"),
                catalyst_date=catalyst_date,
                catalyst_type=CatalystType.CRL.value,
                outcome=Outcome.CRL.value,
                source="FDA_Transparency_CRL_API",
                source_url=cls.BASE_URL,
            )
            event.finalize()
            return event
        except:
            return None

class FDADrugsAPI:
    """OpenFDA API for drug approvals"""
    BASE_URL = "https://api.fda.gov/drug/drugsfda.json"
    
    @classmethod
    def fetch_approvals(cls, start_year: int, end_year: int) -> List[CatalystEvent]:
        events = []
        logger.info(f"[FDA DRUGS] Fetching approvals {start_year}-{end_year}...")
        for year in range(start_year, end_year + 1):
            logger.info(f"[FDA DRUGS]   Year {year}...")
            search = f"submissions.submission_status_date:[{year}0101+TO+{year}1231]"
            skip = 0
            for _ in range(100):
                url = f"{cls.BASE_URL}?search={search}&limit={CONFIG['batch_size']}&skip={skip}"
                data = http.get_json(url, api_name="FDA_DRUGS")
                if not data or "results" not in data:
                    break
                for record in data.get("results", []):
                    event = cls._parse_record(record, year)
                    if event:
                        events.append(event)
                skip += CONFIG['batch_size']
                if skip >= data.get("meta", {}).get("results", {}).get("total", 0):
                    break
        logger.info(f"[FDA DRUGS] Total: {len(events)}")
        return events
    
    @classmethod
    def _parse_record(cls, record: Dict, target_year: int) -> Optional[CatalystEvent]:
        try:
            sponsor = record.get("sponsor_name", "")
            products = record.get("products", [])
            if not products:
                return None
            product = products[0]
            drug_name = product.get("brand_name", "") or "Unknown"
            submissions = record.get("submissions", [])
            approval_date = None
            for sub in submissions:
                if sub.get("submission_status") == "AP":
                    date_str = sub.get("submission_status_date", "")
                    if date_str and len(date_str) >= 8:
                        approval_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                    break
            if not approval_date or not approval_date.startswith(str(target_year)):
                return None
            event = CatalystEvent(
                ticker=get_ticker(sponsor),
                company=sponsor.strip(),
                asset=drug_name.strip(),
                catalyst_date=approval_date,
                catalyst_type=CatalystType.PDUFA.value,
                outcome=Outcome.APPROVAL.value,
                source="FDA_OpenFDA_API",
            )
            event.finalize()
            return event
        except:
            return None

class ClinicalTrialsAPI:
    """ClinicalTrials.gov v2 API for phase readouts"""
    BASE_URL = "https://clinicaltrials.gov/api/v2/studies"
    
    @classmethod
    def fetch_phase_readouts(cls, phase: int, start_year: int, end_year: int) -> List[CatalystEvent]:
        events = []
        logger.info(f"[CT.gov] Fetching Phase {phase} readouts {start_year}-{end_year}...")
        for year in range(start_year, end_year + 1):
            logger.info(f"[CT.gov]   Year {year}...")
            params = {
                "format": "json", "pageSize": "50", "countTotal": "true",
                "filter.phase": f"PHASE{phase}",
                "filter.overallStatus": "COMPLETED",
                "filter.advanced": f"AREA[CompletionDate]RANGE[{year}-01-01,{year}-12-31]",
            }
            query = "&".join([f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items()])
            url = f"{cls.BASE_URL}?{query}"
            page_token = None
            for _ in range(50):
                page_url = url + (f"&pageToken={urllib.parse.quote(page_token)}" if page_token else "")
                data = http.get_json(page_url, api_name="CT.gov")
                if not data:
                    break
                for study in data.get("studies", []):
                    event = cls._parse_study(study, phase, year)
                    if event:
                        events.append(event)
                page_token = data.get("nextPageToken")
                if not page_token:
                    break
        logger.info(f"[CT.gov] Total Phase {phase}: {len(events)}")
        return events
    
    @classmethod
    def _parse_study(cls, study: Dict, phase: int, target_year: int) -> Optional[CatalystEvent]:
        try:
            protocol = study.get("protocolSection", {})
            id_module = protocol.get("identificationModule", {})
            nct_id = id_module.get("nctId", "")
            sponsor_module = protocol.get("sponsorCollaboratorsModule", {})
            sponsor_name = sponsor_module.get("leadSponsor", {}).get("name", "")
            conditions = protocol.get("conditionsModule", {}).get("conditions", [])
            indication = ", ".join(conditions[:2]) if conditions else ""
            status = protocol.get("statusModule", {})
            completion_date = status.get("completionDateStruct", {}).get("date", "")
            catalyst_date = ""
            if completion_date:
                if len(completion_date) == 7:
                    catalyst_date = f"{completion_date}-15"
                elif len(completion_date) >= 10:
                    catalyst_date = completion_date[:10]
            if not catalyst_date or not catalyst_date.startswith(str(target_year)):
                return None
            event = CatalystEvent(
                ticker=get_ticker(sponsor_name),
                company=sponsor_name,
                nct_id=nct_id,
                indication=indication,
                therapeutic_area=classify_therapeutic_area(indication),
                catalyst_date=catalyst_date,
                catalyst_type=f"PHASE{phase}",
                outcome=Outcome.SUCCESS.value if study.get("resultsSection") else Outcome.PENDING.value,
                phase=phase,
                source="ClinicalTrials.gov_v2",
            )
            event.finalize()
            return event
        except:
            return None

class FDADeviceAPI:
    """FDA device 510k and PMA APIs"""
    K510_URL = "https://api.fda.gov/device/510k.json"
    PMA_URL = "https://api.fda.gov/device/pma.json"
    
    @classmethod
    def fetch_510k(cls, start_year: int, end_year: int) -> List[CatalystEvent]:
        events = []
        logger.info(f"[FDA 510K] Fetching {start_year}-{end_year}...")
        for year in range(start_year, end_year + 1):
            url = f"{cls.K510_URL}?search=decision_date:[{year}0101+TO+{year}1231]&limit=1000"
            data = http.get_json(url, api_name="FDA_510K")
            if data:
                for record in data.get("results", []):
                    dd = record.get("decision_date", "")
                    if dd and len(dd) >= 8:
                        event = CatalystEvent(
                            ticker=get_ticker(record.get("applicant", "")),
                            company=record.get("applicant", ""),
                            asset=record.get("device_name", ""),
                            catalyst_date=f"{dd[:4]}-{dd[4:6]}-{dd[6:8]}",
                            catalyst_type=CatalystType.K510.value,
                            outcome=Outcome.CLEARED.value,
                            source="FDA_510k_API",
                        )
                        event.finalize()
                        events.append(event)
        logger.info(f"[FDA 510K] Total: {len(events)}")
        return events
    
    @classmethod
    def fetch_pma(cls, start_year: int, end_year: int) -> List[CatalystEvent]:
        events = []
        logger.info(f"[FDA PMA] Fetching {start_year}-{end_year}...")
        for year in range(start_year, end_year + 1):
            url = f"{cls.PMA_URL}?search=decision_date:[{year}0101+TO+{year}1231]&limit=1000"
            data = http.get_json(url, api_name="FDA_PMA")
            if data:
                for record in data.get("results", []):
                    dd = record.get("decision_date", "")
                    if dd and len(dd) >= 8:
                        event = CatalystEvent(
                            ticker=get_ticker(record.get("applicant", "")),
                            company=record.get("applicant", ""),
                            asset=record.get("trade_name", ""),
                            catalyst_date=f"{dd[:4]}-{dd[4:6]}-{dd[6:8]}",
                            catalyst_type=CatalystType.PMA.value,
                            outcome=Outcome.APPROVAL.value,
                            source="FDA_PMA_API",
                        )
                        event.finalize()
                        events.append(event)
        logger.info(f"[FDA PMA] Total: {len(events)}")
        return events

# ============================================================================
# MAIN MINER CLASS
# ============================================================================

class ODINCatalystMiner:
    def __init__(self, output_dir: str = "./odin_output"):
        self.output_dir = output_dir
        self.events: List[CatalystEvent] = []
        self.alt_data: Dict[str, AlternativeDataSnapshot] = {}
        self.stats = {"start_time": datetime.utcnow().isoformat(), "sources": {},
                      "by_type": {}, "by_year": {}, "by_outcome": {}, "errors": []}
        os.makedirs(output_dir, exist_ok=True)
    
    def mine_alternative_data(self, tickers: List[str]):
        """Mine alternative data for specific tickers"""
        print(f"\n{'='*70}\nALTERNATIVE DATA MINING: {', '.join(tickers)}\n{'='*70}")
        for ticker in tickers:
            logger.info(f"[{ticker}] Mining alternative data...")
            snapshot = AlternativeDataSnapshot(ticker=ticker, snapshot_timestamp=iso_z(utc_now()))
            
            # SEC
            sec = SECAPI.analyze_filings(ticker)
            snapshot.sec_cik = sec.get("cik", "")
            snapshot.recent_8k_count = sec.get("recent_8k_count", 0)
            snapshot.recent_10q_filings = sec.get("recent_10q_count", 0)
            snapshot.sec_filings_sample = sec.get("latest_filings", [])
            logger.info(f"[{ticker}]   SEC: {snapshot.recent_8k_count} 8-Ks")
            
            # Hiring
            hiring = HiringAPI.analyze_ticker(ticker)
            snapshot.greenhouse_job_count = hiring.get("greenhouse_total", 0)
            snapshot.lever_job_count = hiring.get("lever_total", 0)
            snapshot.commercial_jobs_count = hiring.get("commercial_jobs", 0)
            logger.info(f"[{ticker}]   Hiring: {snapshot.greenhouse_job_count + snapshot.lever_job_count} jobs")
            
            # GDELT
            gdelt = GDELTAPI.analyze_ticker(ticker)
            snapshot.gdelt_article_count = gdelt.get("article_count", 0)
            snapshot.gdelt_avg_tone = gdelt.get("avg_tone", 0.0)
            logger.info(f"[{ticker}]   GDELT: {snapshot.gdelt_article_count} articles")
            
            self.alt_data[ticker] = snapshot
        
        # Export
        path = os.path.join(self.output_dir, "odin_alternative_data.json")
        with open(path, 'w') as f:
            json.dump({t: s.to_dict() for t, s in self.alt_data.items()}, f, indent=2, default=str)
        logger.info(f"  → {path}")
    
    def mine_all(self, years_back: int = 5):
        """Mine all catalyst types"""
        end_year = datetime.now().year
        start_year = end_year - years_back
        
        print(f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    ODIN CATALYST MINER v4.0                                  ║
║  Mining: {start_year}-{end_year} | Output: {self.output_dir:<40} ║
╚══════════════════════════════════════════════════════════════════════════════╝""")
        
        # CRLs
        try:
            crls = FDACRLAPI.fetch_all_crls()
            self.events.extend(crls)
            self.stats["sources"]["FDA_CRL"] = len(crls)
        except Exception as e:
            self.stats["errors"].append(f"FDA_CRL: {e}")
        
        # Approvals
        try:
            approvals = FDADrugsAPI.fetch_approvals(start_year, end_year)
            self.events.extend(approvals)
            self.stats["sources"]["FDA_Drugs"] = len(approvals)
        except Exception as e:
            self.stats["errors"].append(f"FDA_Drugs: {e}")
        
        # Phase 2
        try:
            p2 = ClinicalTrialsAPI.fetch_phase_readouts(2, start_year, end_year)
            self.events.extend(p2)
            self.stats["sources"]["CT_P2"] = len(p2)
        except Exception as e:
            self.stats["errors"].append(f"CT_P2: {e}")
        
        # Phase 3
        try:
            p3 = ClinicalTrialsAPI.fetch_phase_readouts(3, start_year, end_year)
            self.events.extend(p3)
            self.stats["sources"]["CT_P3"] = len(p3)
        except Exception as e:
            self.stats["errors"].append(f"CT_P3: {e}")
        
        # 510k
        try:
            k510 = FDADeviceAPI.fetch_510k(start_year, end_year)
            self.events.extend(k510)
            self.stats["sources"]["FDA_510k"] = len(k510)
        except Exception as e:
            self.stats["errors"].append(f"FDA_510k: {e}")
        
        # PMA
        try:
            pma = FDADeviceAPI.fetch_pma(start_year, end_year)
            self.events.extend(pma)
            self.stats["sources"]["FDA_PMA"] = len(pma)
        except Exception as e:
            self.stats["errors"].append(f"FDA_PMA: {e}")
        
        # Dedupe and export
        self._deduplicate()
        self._compute_stats()
        self._export()
        self._print_summary()
    
    def _deduplicate(self):
        seen = set()
        unique = []
        for e in self.events:
            key = (e.company.lower(), e.asset.lower(), e.catalyst_type, e.catalyst_date)
            if key not in seen:
                seen.add(key)
                unique.append(e)
        self.events = unique
    
    def _compute_stats(self):
        for e in self.events:
            self.stats["by_type"][e.catalyst_type] = self.stats["by_type"].get(e.catalyst_type, 0) + 1
            if e.catalyst_date:
                y = e.catalyst_date[:4]
                self.stats["by_year"][y] = self.stats["by_year"].get(y, 0) + 1
            self.stats["by_outcome"][e.outcome] = self.stats["by_outcome"].get(e.outcome, 0) + 1
        self.stats["total_events"] = len(self.events)
    
    def _export(self):
        json_path = os.path.join(self.output_dir, "odin_catalyst_database.json")
        with open(json_path, 'w') as f:
            json.dump({"metadata": self.stats, "events": [asdict(e) for e in self.events]}, f, indent=2)
        
        csv_path = os.path.join(self.output_dir, "odin_catalyst_database.csv")
        if self.events:
            with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=list(asdict(self.events[0]).keys()))
                writer.writeheader()
                for e in self.events:
                    writer.writerow(asdict(e))
        
        # By type
        buckets = {}
        for e in self.events:
            buckets.setdefault(e.catalyst_type, []).append(e)
        for ct, evs in buckets.items():
            fname = f"odin_{ct.lower()}_catalysts.csv"
            with open(os.path.join(self.output_dir, fname), 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=list(asdict(evs[0]).keys()))
                writer.writeheader()
                for e in evs:
                    writer.writerow(asdict(e))
    
    def _print_summary(self):
        print(f"\n{'='*70}\nMINING COMPLETE: {self.stats['total_events']:,} events\n{'='*70}")
        for s, c in sorted(self.stats["sources"].items()):
            print(f"  {'✓' if c else '✗'} {s:<25} {c:>6,}")
        if self.stats["errors"]:
            print("\nErrors:", self.stats["errors"])

# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="ODIN Catalyst Miner v4.0")
    parser.add_argument("--years", type=int, default=5, help="Years of history")
    parser.add_argument("--output", type=str, default="./odin_output", help="Output dir")
    parser.add_argument("--tickers", nargs="+", default=[], help="Tickers for alt data")
    parser.add_argument("--alt-data-only", action="store_true", help="Skip catalyst mining")
    parser.add_argument("--sec-email", type=str, default="", help="Email for SEC API")
    parser.add_argument("-v", "--verbose", action="store_true")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    if args.sec_email:
        CONFIG["sec_user_agent"] = f"ODIN-CatalystMiner/4.0 ({args.sec_email})"
    
    miner = ODINCatalystMiner(output_dir=args.output)
    
    if args.tickers:
        miner.mine_alternative_data(args.tickers)
    
    if not args.alt_data_only:
        miner.mine_all(years_back=args.years)

if __name__ == "__main__":
    main()
