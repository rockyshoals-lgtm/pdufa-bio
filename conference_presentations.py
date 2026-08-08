#!/usr/bin/env python3
"""
ConferencePresentation — catalyst type for `catalyst_crawler.py`.

WHY THIS EXISTS
The live pipeline had no Conference type at all. It harvested readouts, PDUFAs, earnings,
devices and AdComms — but nothing captured *who presents where*. So the conference dataset
was a one-off manual exercise that decayed: ASCO26 had 6 events, EHA26/ADA26 had zero.
A dataset that only updates when someone remembers is a snapshot, not a moat.

HOW IT WORKS
A conference presentation is a different extraction shape from every other catalyst:
the press release says "XYZ to present Phase 2 data at ASCO 2026" but almost never states
a date. The DATE comes from the conference, not the filing. So:

  1. detect the conference from the filing text (alias table)
  2. detect the presentation type (oral / late-breaking / poster) — a FACT, not a weight
  3. resolve the date from conf_registry.json (derived from our own 1,425-event history)
  4. emit ConferencePresentation with an honest date_precision

We never guess a date we don't have: if the conference/year isn't in the registry and we
can't project it, we emit month precision or drop the row. No fabricated dates.

Facts only — no scores, no weights, no win rates. (Conference Overlay v1.0 is RETIRED/REFUTED.)
"""
import os, re, json, datetime as dt
from pathlib import Path

REG_PATH = Path(__file__).parent / "conf_registry.json"

# alias -> canonical code. Longest alias wins (checked longest-first).
ALIASES = {
    "american society of clinical oncology": "ASCO", "asco annual meeting": "ASCO", "asco": "ASCO",
    "asco gastrointestinal": "ASCO-GI", "asco gi": "ASCO-GI", "gastrointestinal cancers symposium": "ASCO-GI",
    "asco genitourinary": "ASCO-GU", "asco gu": "ASCO-GU", "genitourinary cancers symposium": "ASCO-GU",
    "american society of hematology": "ASH", "ash annual meeting": "ASH", "ash": "ASH",
    "european society for medical oncology": "ESMO", "esmo congress": "ESMO", "esmo": "ESMO",
    "american association for cancer research": "AACR", "aacr": "AACR",
    "european hematology association": "EHA", "eha congress": "EHA", "eha": "EHA",
    "society for immunotherapy of cancer": "SITC", "sitc": "SITC",
    "american academy of neurology": "AAN", "aan": "AAN",
    "san antonio breast cancer": "SABCS", "sabcs": "SABCS",
    "american heart association": "AHA", "aha scientific sessions": "AHA",
    "american college of cardiology": "ACC", "acc.": "ACC",
    "american diabetes association": "ADA", "ada scientific sessions": "ADA",
    "aasld": "AASLD", "the liver meeting": "AASLD",
    "easl": "EASL", "international liver congress": "EASL",
    "american society of nephrology": "ASN", "kidney week": "ASN",
    "endocrine society": "ENDO", "endo 20": "ENDO",
    "world conference on lung cancer": "WCLC", "wclc": "WCLC",
    "american college of rheumatology": "ACR", "acr convergence": "ACR",
    "ectrims": "ECTRIMS", "eular": "EULAR", "ctad": "CTAD",
    "american thoracic society": "ATS", "ats 20": "ATS",
    "american academy of dermatology": "AAD",
    "american academy of allergy": "AAAAI", "aaaai": "AAAAI",
    "american society of gene": "ASGCT", "asgct": "ASGCT",
    "society for neuro-oncology": "SNO",
    "alzheimer's association international": "AAIC", "aaic": "AAIC",
    "isth": "ISTH", "american academy of ophthalmology": "AAO",
    "aacr-nci-eortc": "ANE", "triple meeting": "ANE",
    "acaai": "ACAAI",
    "acnp": "ACNP",
    "ad/pd": "ADPD",
    "adpd": "ADPD",
    "advanced technologies and treatments for diabetes": "ATTD",
    "alzheimer's association international conference": "AAIC",
    "american academy of allergy, asthma": "AAAAI",
    "american college of allergy, asthma": "ACAAI",
    "american college of neuropsychopharmacology": "ACNP",
    "american society for radiation oncology": "ASTRO",
    "american society of gene & cell therapy": "ASGCT",
    "american society of gene and cell therapy": "ASGCT",
    "arvo": "ARVO",
    "association for research in vision and ophthalmology": "ARVO",
    "astro": "ASTRO",
    "attd": "ATTD",
    "clinical trials on alzheimer's disease": "CTAD",
    "conference on retroviruses and opportunistic infections": "CROI",
    "croi": "CROI",
    "ddw": "DDW",
    "digestive disease week": "DDW",
    "esmo breast": "ESMO-B",
    "esmo breast cancer": "ESMO-B",
    "european alliance of associations for rheumatology": "EULAR",
    "european association for the study of the liver": "EASL",
    "european committee for treatment and research in multiple sclerosis": "ECTRIMS",
    "european respiratory society": "ERS",
    "international conference on alzheimer's and parkinson's diseases": "ADPD",
    "international society on thrombosis and haemostasis": "ISTH",
    "obesity week": "OBESITYWEEK",
    "obesityweek": "OBESITYWEEK",
    "aacr-nci-eortc international conference on molecular targets and cancer therapeutics": "ENA",
    "aacr-nci-eortc international conference": "ENA",
    "eortc-nci-aacr molecular targets and cancer therapeutics symposium": "ENA",
    "eortc-nci-aacr": "ENA",
    "molecular targets and cancer therapeutics": "ENA",
}
_ALIAS_ORDER = sorted(ALIASES, key=len, reverse=True)   # longest first — "asco gi" before "asco"

# Presentation type = a FACT about selectivity. We record it; we do NOT weight it.
PRES_PATTERNS = [
    ("late-breaking", re.compile(r'late[\s-]?break', re.I)),
    ("oral",          re.compile(r'\boral\s+(?:presentation|abstract|session)|\bpodium\b', re.I)),
    ("plenary",       re.compile(r'\bplenary\b', re.I)),
    ("poster",        re.compile(r'\bposter\b', re.I)),
]

# The filing must actually be about presenting — not merely mention a conference in passing.
PRESENT_VERB = re.compile(
    r'\b(?:to\s+present|will\s+present|presents?|presented|presenting|showcase|'
    r'featured?\s+in|selected\s+for\s+(?:oral|poster|presentation)|'
    r'accepted\s+for\s+(?:oral|poster|presentation)|abstracts?\s+accepted)\b', re.I)

# SEC full-text phrases. Anchor on the CONFERENCE NAME, not on "to present at" —
# the generic verb pulls in every investor-conference 8-K on EDGAR (Liberty Media, Labcorp,
# insurance carriers...). Searching the meeting name returns almost exclusively biotech PRs.
SEARCH_PHRASES = [
    # oncology / heme (original 8)
    "American Society of Clinical Oncology",
    "American Society of Hematology",
    "European Society for Medical Oncology",
    "American Association for Cancer Research",
    "European Hematology Association",
    "Society for Immunotherapy of Cancer",
    "San Antonio Breast Cancer Symposium",
    "World Conference on Lung Cancer",
    # oncology sub-meetings (NEW)
    "Gastrointestinal Cancers Symposium",
    "Genitourinary Cancers Symposium",
    "Society for Neuro-Oncology",
    "ESMO Breast Cancer",
    "American Society for Radiation Oncology",
    # neuro / CNS (NEW: CTAD, AAIC, ECTRIMS, ADPD, ACNP)
    "American Academy of Neurology",
    "Clinical Trials on Alzheimer's Disease",
    "Alzheimer's Association International Conference",
    "European Committee for Treatment and Research in Multiple Sclerosis",
    "International Conference on Alzheimer's and Parkinson's Diseases",
    "American College of Neuropsychopharmacology",
    # cell & gene (NEW: ASGCT)
    "American Society of Gene and Cell Therapy",
    # hepatology / GI (NEW: EASL is the single biggest gap, n=35)
    "The Liver Meeting",
    "European Association for the Study of the Liver",
    "Digestive Disease Week",
    # immunology / rheum / derm (NEW)
    "American College of Rheumatology",
    "European Alliance of Associations for Rheumatology",
    "American Academy of Dermatology",
    "American Academy of Allergy, Asthma",
    "American College of Allergy, Asthma",
    # metabolic / endocrine (NEW)
    "American Diabetes Association",
    "Endocrine Society",
    "Advanced Technologies and Treatments for Diabetes",
    "ObesityWeek",
    # cardio / renal / resp (NEW)
    "American Heart Association",
    "American College of Cardiology",
    "Kidney Week",
    "American Thoracic Society",
    "European Respiratory Society",
    # ophthalmology (NEW)
    "American Academy of Ophthalmology",
    "Association for Research in Vision and Ophthalmology",
    # thrombosis (NEW)
    "International Society on Thrombosis and Haemostasis",
    # generic fallbacks — weak net, NOT the workhorse
    "late-breaking abstract",
    "oral presentation at",
    "poster presentation at",
    "Molecular Targets and Cancer Therapeutics",
]

def load_registry(path=REG_PATH):
    if not os.path.exists(path):
        return {}
    return json.load(open(path, encoding="utf-8"))


def detect_conference(text):
    """Return canonical conference code, or None. Longest alias wins."""
    low = " " + re.sub(r'\s+', ' ', text.lower()) + " "
    for a in _ALIAS_ORDER:
        # word-ish boundary so 'ash' doesn't match 'cash'/'washington'
        if re.search(r'(?<![a-z])' + re.escape(a) + r'(?![a-z])', low):
            return ALIASES[a]
    return None


def detect_pres_type(text):
    for label, rx in PRES_PATTERNS:
        if rx.search(text):
            return label
    return "unspecified"


# ---------------------------------------------------------------------------
# Prospectivity. THE bug this guards against:
#
#   A 2026 press release says "Presented data at ESMO 2025". The old detect_year()
#   fell back to `filed_dt.year` when it couldn't read a year, stamped it 2026,
#   and projected a FUTURE date. Result: a conference presentation that already
#   happened was published on the forward calendar as an upcoming catalyst.
#   74 of 121 projected rows were history sold as future. One reached 2027.
#
# The invariant: NEVER emit a date after the filing date unless the text actually
# says the company is GOING TO present. A conference being mentioned is not a
# commitment to attend it.
# ---------------------------------------------------------------------------
FUTURE_CUE = re.compile(
    r"\b(will\s+(?:be\s+)?present\w*|to\s+be\s+presented|to\s+present|plans?\s+to\s+present|"
    r"accepted\s+for\s+(?:oral\s+|poster\s+|late-breaking\s+)?present\w*|scheduled\s+to\s+present|"
    r"will\s+(?:feature|report|showcase)|upcoming\b|forthcoming\b)", re.I)
PAST_CUE = re.compile(
    r"\b(presented|were\s+presented|was\s+presented|reported|featured|highlighted|showcased|"
    r"presentation\s+of\s+(?:the\s+)?(?:data|results))\b", re.I)

# Semantic version of the EXTRACTION RULES. Bump this whenever a change could alter the
# date/conference/inclusion decision for a filing we have already seen.
#   1 = original
#   2 = prospectivity gate: a past-tense mention can no longer become a future catalyst
EXTRACTOR_VERSION = 2


def prospectivity(window):
    """'future' | 'past' | 'unknown' — is this a commitment to present, or a memory of one?"""
    f = bool(FUTURE_CUE.search(window))
    p = bool(PAST_CUE.search(window))
    if f:   return "future"          # an explicit future cue always wins
    if p:   return "past"
    return "unknown"


# ---------------------------------------------------------------- RULE 1: a STATED year wins
# The fabrication mechanism the audit named: the crawler resolves a conference NAME to that
# conference's NEXT occurrence, ignoring the year written right next to it. A 2026 filing that
# says "data presented at ASH 2025" gets resolved to ASH *2026*. Five phantoms came from this:
#   AUTL/COGT -> ASH 2026, CRBP -> ESMO 2026, CTMX -> SITC 2026, CELC -> SABCS 2026
# all extracted from 2025 source text.
#
# The rule: a year written ADJACENT to the conference name is authoritative. It beats the filing
# year, it beats the "next occurrence", it beats everything. If the text says 2025, it is 2025 —
# and a past year can never produce a future event.
_YEAR_NEAR = re.compile(r'\b(20[12]\d)\b')

def stated_year(text, conf, aliases):
    """The year written next to the conference name, or None. Authoritative when present."""
    names = [a for a in aliases if aliases[a] == conf]
    best = None
    for a in sorted(names, key=len, reverse=True):
        for m in re.finditer(re.escape(a), text, re.I):
            # look tight: 40 chars either side of the conference name. "ASH 2025", "2025 ASH"
            lo, hi = max(0, m.start() - 40), min(len(text), m.end() + 40)
            for ym in _YEAR_NEAR.finditer(text[lo:hi]):
                y = int(ym.group(1))
                if best is None or y < best:      # the EARLIEST stated year wins: safest
                    best = y
        if best is not None:
            return best
    return None


def detect_year(text, filed_dt=None, mode="unknown"):
    """Year of the conference. Prefer an explicit 20xx near the conference mention."""
    yrs = [int(y) for y in re.findall(r'\b(20[2-3]\d)\b', text)]
    fy = filed_dt.year if filed_dt else None

    if mode == "past":
        # It already happened. The conference year cannot be after the filing.
        past = [y for y in yrs if fy is None or y <= fy]
        if past:
            return max(past)
        return None                      # no defensible past year -> refuse to guess

    if mode == "future":
        if yrs and fy is not None:
            fwd = [y for y in yrs if y >= fy]
            if fwd:
                return min(fwd)
        if yrs:
            return max(set(yrs), key=yrs.count)
        return fy                        # "will present at ASCO" with no year -> the next one

    # mode == "unknown": we have no tense signal. Require an EXPLICIT year in the text.
    # Defaulting to the filing year is exactly how history became future.
    if yrs:
        return max(set(yrs), key=yrs.count)
    return None


def resolve_date(conf, year, registry, mode="unknown"):
    """(iso_date, precision, basis) or (None, None, None). NEVER fabricate a specific day."""
    r = registry.get(conf)
    if not r or not year:
        return None, None, None
    exact = r.get("dates", {}).get(str(year))
    if exact:
        return exact, "day", "observed"
    # No observed date for that conference-year. We may only PROJECT one when the filing
    # actually promises a future presentation. Projecting a month onto a past mention is
    # how a 2025 presentation became a 2026 catalyst.
    if mode != "future":
        return None, None, None
    doy = r.get("doy")
    if doy:
        # project from the conference's typical day-of-year -> month precision only.
        # We know ASCO is early June; we do NOT claim to know it's June 2nd.
        d = dt.date(int(year), 1, 1) + dt.timedelta(days=int(doy) - 1)
        return d.strftime("%Y-%m"), "month", "projected"
    return None, None, None


def _best_snippet(window):
    """Centre the snippet on the sentence that actually states the presentation —
    not on wherever the conference name happened to appear."""
    m = PRESENT_VERB.search(window)
    if not m:
        return re.sub(r'\s+', ' ', window[:200]).strip()
    s = max(0, m.start() - 90)
    return re.sub(r'\s+', ' ', window[s:m.start() + 150]).strip()


def extract(text, filed_dt=None, registry=None):
    """Extract a conference presentation from filing text. Returns dict or None."""
    registry = registry if registry is not None else load_registry()
    if not PRESENT_VERB.search(text):
        return None
    conf = detect_conference(text)
    if not conf:
        return None
    # the presentation verb must be reasonably near the conference mention (same neighbourhood)
    m = re.search(r'(?<![a-z])' + '|'.join(re.escape(a) for a in _ALIAS_ORDER if ALIASES[a] == conf) + r'(?![a-z])',
                  text, re.I)
    if m:
        window = text[max(0, m.start() - 300): m.start() + 300]
        if not PRESENT_VERB.search(window):
            return None
    else:
        window = text
    mode = prospectivity(window)

    # RULE 1 — a year stated NEXT TO the conference name is authoritative.
    sy = stated_year(window, conf, ALIASES)
    if sy is not None:
        year = sy
        # RULE 2 — a stated PAST year can never produce a future event, whatever the tense.
        if filed_dt is not None and sy < filed_dt.year:
            mode = "past"
    else:
        year = detect_year(window, filed_dt, mode)
    iso, prec, basis = resolve_date(conf, year, registry, mode)
    if not iso:
        return None

    # Final backstop, independent of everything above: a date AFTER the filing date is only
    # legitimate if the filing says the company will present. Otherwise it is a memory, not
    # a catalyst, and we drop it rather than put a fiction on the calendar.
    if filed_dt is not None and mode != "future":
        _d = iso if len(iso) == 10 else iso + "-28"
        try:
            if dt.date.fromisoformat(_d) > filed_dt:
                return None
        except Exception:
            return None
    abst = re.search(r'\babstract\s*(?:number|no\.?|#)?\s*([A-Z]{0,3}\d{2,6})', window, re.I)
    return dict(
        conference=conf,
        catalyst_date=iso,
        date_precision=prec,
        date_basis=basis,                      # observed | projected  <- honesty, surfaced downstream
        pres_type=detect_pres_type(window),
        abstract=(abst.group(1) if abst else None),
        year=year,
        snippet=_best_snippet(window),
    )


if __name__ == "__main__":
    # This file is a LIBRARY (the extractor). Running it directly used to do nothing at all
    # and drop straight back to the prompt — which is exactly how a silent no-op hides.
    import sys
    _named = [p for p in SEARCH_PHRASES if not p.startswith(("late-", "oral", "poster"))]
    print(__doc__ or "conference_presentations — ConferencePresentation extractor (library)")
    print(f"\nLoaded OK: {len(_named)} named conference searches, {len(ALIASES)} aliases, "
          f"{len(load_registry())} registry conferences.")
    print("\nThis module does not crawl on its own. To actually run a crawl:\n")
    print("    python run_conference_crawl.py                 # conference-only (fast)")
    print("    python catalyst_crawler.py --tickers <file>    # full catalyst crawl\n")
    sys.exit(0)
