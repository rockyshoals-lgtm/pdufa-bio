# -*- coding: utf-8 -*-
"""extract_crl_headings.py -- the deficiency section headings of each FDA CRL, read from the PDF (audit 4.5).

We hold 458 Complete Response Letters (openFDA transparency release) and link nine decision pages to their
letters; the rest of the text sits unused. The corpus "text" field is OCR ("CORT125134-455!", "me)") and the
order is explicit: deficiency headings read from the PDF, never pasted from OCR. So for each letter this
downloads the FDA-hosted PDF (https://download.open.fda.gov/crl/{file_name}), reads its TEXT LAYER with
pdftotext, and keeps a line as a heading only when it stands alone, is set in capitals, and every word is
from the FDA's own section vocabulary (PRODUCT QUALITY MICROBIOLOGY, FACILITY INSPECTIONS, CLINICAL,
PRESCRIBING INFORMATION, CARTON AND CONTAINER LABELING, ...). A letter whose PDF has no text layer (a scan)
gets no headings and says so; nothing is ever inferred from the OCR field. Results cache in
_crl_headings.json (a letter is read once). Facts only: the headings name what the FDA wrote about, never why.

    python extract_crl_headings.py [--limit N]
"""
import argparse
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
OUT = os.path.join(HERE, "_crl_headings.json")
WORDS = set("""CLINICAL STATISTICAL STATISTICS PRODUCT QUALITY MICROBIOLOGY FACILITY FACILITIES INSPECTION INSPECTIONS
PRESCRIBING INFORMATION LABELING LABELLING CARTON CONTAINER NONCLINICAL PHARMACOLOGY TOXICOLOGY SAFETY UPDATE HUMAN
FACTORS DEVICE DEVICES BIOPHARMACEUTICS IMMUNOGENICITY RISK EVALUATION MITIGATION STRATEGY REMS PROPRIETARY NAME
CHEMISTRY MANUFACTURING CONTROLS CMC OTHER ADDITIONAL COMMENTS BIOEQUIVALENCE EFFICACY PEDIATRIC POSTMARKETING
REQUIREMENTS COMMITMENTS DRUG SUBSTANCE ASSAY STERILITY BIOANALYTICAL ABUSE DEPENDENCE INSTRUCTIONS FOR USE PATIENT
MEDICATION GUIDE PACKAGE INSERT AND OF THE TO A IN ON WITH STUDY STUDIES DATA INTEGRITY BIOMETRICS CLINICAL/STATISTICAL
REGULATORY SECTION PHARMACOKINETICS DOSING DOSE PRODUCT/CMC COMBINATION FINANCIAL DISCLOSURE ENVIRONMENTAL ASSESSMENT
ESTABLISHMENT ESTABLISHMENTS COMPLIANCE CURRENT GOOD PRACTICE CGMP NOMENCLATURE QUALITY/MICROBIOLOGY""".split())
SKIP = re.compile(r"^(NDA|BLA|ANDA|COMPLETE RESPONSE|CORRECTED|PAGE|REFERENCE|DEAR|ATTENTION|U\.S\.|FOOD AND DRUG)", re.I)


TITLE_OK = {"clinical and statistical", "clinical", "statistical", "product quality", "facility inspections",
            "clinical pharmacology", "nonclinical", "labeling", "safety update", "human factors", "microbiology",
            "product quality microbiology", "prescribing information", "carton and container labeling",
            "proprietary name", "additional comments", "other", "biopharmaceutics", "device", "immunogenicity",
            "clinical/statistical", "pharmacology/toxicology", "chemistry, manufacturing, and controls",
            "facilities", "risk evaluation and mitigation strategy", "medication guide", "data integrity"}
# sections that name a deficiency, as opposed to the administrative ones nearly every letter carries
SUBSTANTIVE = {"Clinical", "Clinical and Statistical", "Statistical", "Clinical/Statistical", "Product Quality",
               "Product Quality Microbiology", "Microbiology", "Facility Inspections", "Facilities",
               "Clinical Pharmacology", "Nonclinical", "Pharmacology/Toxicology", "Human Factors", "Device",
               "Biopharmaceutics", "Immunogenicity", "Chemistry, Manufacturing, and Controls", "Data Integrity",
               "Risk Evaluation and Mitigation Strategy", "Bioequivalence", "Drug Substance", "Sterility Assurance"}


def headings_from_text(txt):
    out = []
    for line in txt.splitlines():
        t = re.sub(r"\s+", " ", line).strip().rstrip(":")
        if t.lower() in TITLE_OK and t != t.upper():
            h = t[0].upper() + t[1:]
            if h.lower() not in {x.lower() for x in out}:
                out.append(h)
            continue
        s = t
        if not (4 <= len(s) <= 70) or s != s.upper() or not re.search(r"[A-Z]{3}", s) or SKIP.match(s):
            continue
        if re.search(r"\(B\)|\d", s):
            continue
        words = re.findall(r"[A-Z/]+", s)
        if words and all(w in WORDS for w in words) and any(len(w) >= 5 for w in words):
            h = s.title().replace(" And ", " and ").replace(" Of ", " of ").replace(" For ", " for ").replace("Cmc", "CMC").replace("Rems", "REMS")
            if h.lower() not in {x.lower() for x in out}:
                out.append(h)
    return out


def substantive_sections(file_name, cache=None):
    """The letter's deficiency sections (its own headings from the PDF text layer), administrative
    sections (labeling, safety update, proprietary name, other) left out. None when not read."""
    if cache is None:
        cache = json.load(io.open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
    rec = cache.get(file_name)
    if not rec or not rec.get("text_layer"):
        return None
    keep = []
    for h in rec.get("headings", []):
        hl = h.lower()
        if any(hl == x.lower() or hl.startswith(x.lower() + " ") for x in SUBSTANTIVE) or \
                re.search(r"clinical|statistic|quality|microbiolog|facilit|nonclinical|toxicolog|human factors|"
                          r"device|biopharm|immunogen|manufactur|data integrity|bioequival|sterility|regulatory", hl):
            if hl not in {k.lower() for k in keep}:
                keep.append(h)
    return keep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    import shutil
    if not shutil.which("pdftotext"):
        print("CRL headings: pdftotext (poppler-utils) not installed here; no letter read, cache unchanged")
        return 0
    from capture_crl_corpus import newest_corpus
    corpus = newest_corpus() or os.path.join(HERE, "CRL_corpus_openFDA_2026-08-29.json")
    letters = json.load(io.open(corpus, encoding="utf-8"))["results"]
    cache = json.load(io.open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
    done = 0
    for L in letters:
        fn = L.get("file_name")
        if not fn or fn in cache:
            continue
        if a.limit and done >= a.limit:
            break
        url = "https://download.open.fda.gov/crl/" + urllib.parse.quote(fn)
        rec = {"application_number": L.get("application_number"), "letter_date": L.get("letter_date")}
        try:
            data = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "pdufa.bio rockyshoals@gmail.com"}),
                                          timeout=60).read()
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tf:
                tf.write(data)
                tmp = tf.name
            txt = subprocess.run(["pdftotext", "-layout", tmp, "-"], capture_output=True, text=True, timeout=60).stdout
            os.unlink(tmp)
            letters_ = len(re.findall(r"[A-Za-z]", txt))
            rec["text_layer"] = letters_ > 400
            rec["headings"] = headings_from_text(txt) if rec["text_layer"] else []
        except Exception as e:  # noqa: BLE001
            rec["error"] = str(e)[:120]
        cache[fn] = rec
        done += 1
        if done % 20 == 0:
            io.open(OUT, "w", encoding="utf-8", newline="\n").write(json.dumps(cache, indent=1, sort_keys=True) + "\n")
            print(f"  {done} read", flush=True)
        time.sleep(0.2)
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(json.dumps(cache, indent=1, sort_keys=True) + "\n")
    tl = sum(1 for v in cache.values() if v.get("text_layer"))
    hh = sum(1 for v in cache.values() if v.get("headings"))
    print(f"CRL headings: {len(cache)} letter(s) read; {tl} with a text layer; {hh} with section headings")
    return 0


if __name__ == "__main__":
    sys.exit(main())
