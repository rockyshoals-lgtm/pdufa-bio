"""Red team pass 3: full text index of both CRL drops -> _crl_letter_index.json.
Company per letter, readability, and presence/absence of the sponsors we track."""
import json, os, re

try:
    from pypdf import PdfReader
except ImportError:
    from PyPDF2 import PdfReader

BASE = os.path.join("odin_cowork_dropbox")
SETS = {"unapproved": os.path.join(BASE, "unapproved_CRLs (1)"),
        "approved": os.path.join(BASE, "approved_CRLs (2)")}

# sponsors of every 2025-2026 CRL in OUR archive (from the decisions listing)
WATCH = ["Achieve", "Lantheus", "Unicycive", "REGENXBIO", "Replimune", "Corcept",
         "Capricor", "Aquestive", "Atara", "Alvotech", "Fortress", "Disc Medicine",
         "Outlook", "Telix", "Milestone", "PTC ", "Zealand", "Vanda", "Tarsus",
         "Novavax", "Ultragenyx", "Applied Therapeutics", "Sarepta"]

idx = []
unreadable = 0
for setname, d in SETS.items():
    for f in sorted(os.listdir(d)):
        if not f.lower().endswith(".pdf"):
            continue
        p = os.path.join(d, f)
        try:
            r = PdfReader(p)
            t = re.sub(r"\s+", " ", " ".join((pg.extract_text() or "")
                                             for pg in r.pages[:3]))
        except Exception:
            t = ""
        if len(t) < 80:
            unreadable += 1
        m = re.search(r"(?:COMPLETE RESPONSE|OtherAction)?\s*"
                      r"((?:January|February|March|April|May|June|July|August|"
                      r"September|October|November|December)\s+\d{1,2},\s+\d{4})", t)
        comp = re.search(r"(?:RESPONSE|Redacted)?\s*([A-Z][A-Za-z0-9 .,&()'/-]{3,60}?)"
                         r"\s+Attention:", t)
        app = re.search(r"(?:BLA|NDA|BL|STN[: ]+B?L?)\s*#?\s*(\d{6})", t) or \
              re.search(r"(\d{6})", f)
        idx.append({"set": setname, "file": f,
                    "app": app.group(1) if app else None,
                    "letter_date_text": m.group(1) if m else None,
                    "company": comp.group(1).strip() if comp else None,
                    "chars": len(t), "head": t[:200]})

json.dump(idx, open("_crl_letter_index.json", "w", encoding="utf-8"),
          indent=1, ensure_ascii=False)
print(f"indexed {len(idx)} letters ({unreadable} with <80 chars extractable)")

blob = " ".join((x["head"] or "") + " " + (x["company"] or "") for x in idx)
# deeper scan for watch sponsors across FULL text of unmatched ones is expensive;
# heads usually carry the addressee, which is the sponsor.
full_hits = {}
for w in WATCH:
    n = sum(1 for x in idx if w.lower() in ((x["company"] or "") + " " + x["head"]).lower())
    full_hits[w] = n
print("\nsponsors of OUR tracked CRLs, present in the drop (by letter head):")
for w, n in sorted(full_hits.items(), key=lambda kv: -kv[1]):
    print(f"  {'FOUND' if n else '  -- ':5} {w.strip():22} x{n}")
