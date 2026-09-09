# -*- coding: utf-8 -*-
"""State what a diagnostic actually is, on the event pages that already exist.

Audit 2026-09-09b item 2. Two days before its decision, /pdufa/TLX read "TLX101-Px is under
FDA review to treat recurrent or progressive glioma - an aggressive type of brain cancer."
TLX101-Px is Pixclara (floretyrosine F 18), a PET imaging agent submitted for the
CHARACTERISATION of recurrent or progressive glioma from treatment-related change. It treats
nothing. The therapeutic candidate TLX101, a separate Telix programme, is how the two were
conflated.

Why a separate script rather than a fix in the generator: build_pdufa_story_blocks.py skips
any page that already carries a story block ("already has story-v1 block"), and
build_pdufa_event_pages.py never overwrites an existing page, because the hand-grown ones
carry cards worth keeping. So the generator fix alone corrects new pages and leaves every
published one wrong. This corrects the published ones.

One owner: the DATASET decides what is a diagnostic (`_d.modality == "diagnostic"`, or the
diagnostic cues our own indication text uses). This script only renders that decision, is
idempotent, and is safe to run on every build.
"""
import glob
import html
import io
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")

CUE = re.compile(r"\b(?:PET imaging|imaging agent|radiodiagnostic|diagnostic agent|"
                 r"to characteris[ez]e|characteris[ez]ation of|companion diagnostic|"
                 r"-CDx\b|-Px\b|contrast agent)\b", re.I)
# The drug label is wrapped in <b>...</b> on the story card, so a capture group for it cannot
# cross the tag; match the phrase itself and leave whatever precedes it in place.
TREAT = re.compile(r"is under FDA review to treat ([^<]{3,200}?)\.")


def rows():
    src = io.open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
    return json.loads(src[src.index("["):src.rindex("]") + 1])


def main():
    n = 0
    for r in rows():
        d = r.get("_d") or {}
        name = str(r.get("name") or "")
        indication = str(d.get("indication") or "")
        is_dx = (str(d.get("modality", "")).lower() == "diagnostic"
                 or CUE.search(f"{name} {indication}"))
        if not is_dx or str(r.get("type") or "").upper() != "PDUFA":
            continue
        tk = str(r.get("t") or "").upper()
        if not tk:
            continue
        # the sentence we want, built from the row: what it is, what it is for, and the
        # explicit denial that it is a therapy, because that is the error being corrected
        # Do NOT lowercase an acronym: the first pass shipped "pET imaging".
        first = indication.split(" ", 1)[0] if indication else ""
        low = (indication if (len(first) > 1 and first.isupper())
               else indication[:1].lower() + indication[1:]) if indication else "the stated use"
        brand = ""
        bm = re.search(r"\(([A-Z][A-Za-z0-9\- ]{2,30})\)\s*$", name.strip())
        if bm:
            brand = bm.group(1).strip()
        # "marketed under the brand name" was the first pass and it is FALSE: a product under
        # review is not marketed, and the brand name is proposed until the FDA accepts it.
        sentence = (f"is under FDA review for {html.escape(low)}. "
                    + (f"It is a diagnostic, not a treatment; the proposed brand name is "
                       f"{html.escape(brand)}." if brand
                       else "It is a diagnostic, not a treatment."))
        # the bare label ("TLX101-Px" from "TLX101-Px (Pixclara)") identifies the product on
        # the page, so a ticker with several programmes is not rewritten from the wrong row
        bare = re.split(r"\s*\(", name.strip())[0].strip()
        for p in glob.glob(os.path.join(SITE, "pdufa", f"{tk}*", "index.html")):
            doc = io.open(p, encoding="utf-8", errors="replace").read()
            m = TREAT.search(doc)
            if not m or (bare and bare.lower() not in doc.lower()):
                continue
            new = doc[:m.start()] + sentence + doc[m.end():]
            if new != doc:
                io.open(p, "w", encoding="utf-8").write(new)
                n += 1
                print(f"  {os.path.relpath(p, SITE)}: therapy verb replaced "
                      f"({name} is a diagnostic)")
    print(f"diagnostic event pages: {n} sentence(s) corrected")
    return 0


if __name__ == "__main__":
    sys.exit(main())
