"""Guard (2026-11-27): one company-stated readout must be listed once.

Four ASH presentations and one Phase 3 outcomes readout were each listed twice after the Nov 26 mine: the
second copy named the drug the other way round ("tambiciclib (SLS009)" against "SLS009 (tambiciclib)",
"resmetirom (Rezdiffra)" against "Rezdiffra (resmetirom)"), so the mine's duplicate check, which keyed on the
first word of the drug name, missed it. Two copies of one event read as two catalysts.

A pair is a duplicate when the ticker and date match, the drug names share a name (either order, code or
brand), and the rows quote the same statement: the same abstract number, the same session time, or the
same guidance sentence. Rows that are two trials of one drug on one day differ in the session time or
the quote, so they pass.
"""
import io, itertools, json, os, re, sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")


def names(s):
    s = str(s or "").lower()
    out = set()
    outside = re.sub(r"\([^)]*\)", " ", s).split()
    if outside:
        out.add(re.sub(r"[^a-z0-9]", "", outside[0]))
    for inner in re.findall(r"\(([^)]*)\)", s):
        w = inner.split()
        if w:
            out.add(re.sub(r"[^a-z0-9]", "", w[0]))
    # every drug in a combination counts ("ZYNLONTA + glofitamab" and "loncastuximab tesirine + glofitamab")
    for part in re.split(r"\s*(?:\+|/|\bplus\b|\bwith\b|,)\s*", re.sub(r"\([^)]*\)", " ", s)):
        w = part.split()
        if w:
            out.add(re.sub(r"[^a-z0-9]", "", w[0]))
    return {w for w in out if len(w) >= 4 and w not in GENERIC}


GENERIC = {"sirna", "oral", "antibody", "partnered", "subcutaneous", "intravenous", "monotherapy", "combination",
           "inhaled", "topical", "vaccine", "program", "phase", "formerly", "standard", "placebo",
           "dexamethasone", "azacitidine", "venetoclax", "rituximab", "pembrolizumab", "chemotherapy"}


def trial_codes(r):
    d = r.get("_d") or {}
    txt = f"{d.get('trial') or ''} {r.get('name') or ''}"
    drug = names(d.get("program") or r.get("name"))
    codes = {norm(m) for m in re.findall(r"\b\d?[A-Z][A-Z0-9]{2,}(?:-[A-Z0-9]+)*(?:\s\d{1,2}\b)?", txt)}
    return {c for c in codes if c not in drug and c not in {"phase", "data", "ash", "asco", "topline"}}


def norm(s):
    return re.sub(r"[^a-z0-9]", "", str(s or "").lower())


def abstract_no(r):
    m = re.search(r"abstract\s*#?\s*(\d{3,6})", json.dumps(r, ensure_ascii=False).lower())
    return m.group(1) if m else None


def session_times(d):
    # a session time ("December 14, 2026, 3:00 - 3:15 p.m."); "Q4 2026" or "late 2027" has none
    lab = f"{d.get('guided_label') or ''} {d.get('date_quote') or ''}"
    t = tuple(sorted(set(re.findall(r"\d{1,2}:\d\d", lab))))
    return t or None


def duplicates(rows):
    rs = [r for r in rows if r.get("type") == "Readout" and r.get("st") in ("Guided", "Estimated")]
    by = {}
    for r in rs:
        by.setdefault((r.get("t"), r.get("d")), []).append(r)
    out = []
    for grp in by.values():
        for a, b in itertools.combinations(grp, 2):
            da, db = a.get("_d") or {}, b.get("_d") or {}
            if not (names(da.get("program") or a.get("name")) & names(db.get("program") or b.get("name"))):
                continue
            ca, cb = trial_codes(a), trial_codes(b)
            if ca - cb and cb - ca:
                continue  # two named trials of one drug (ECLIPSE 2 and ECLIPSE 3), even when one sentence guides both
            ab = abstract_no(a)
            sa = session_times(da)
            qa, qb = norm(da.get("guidance_text"))[:80], norm(db.get("guidance_text"))[:80]
            if (ab and ab == abstract_no(b)) or (sa and sa == session_times(db)) or (len(qa) >= 30 and qa == qb):
                out.append((a["id"], b["id"]))
    return out


def main():
    src = io.open(DATASET, encoding="utf-8").read()
    rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    dups = duplicates(rows)
    for a, b in dups:
        print(f"FAIL: {a} and {b} list the same company statement twice")
    if dups:
        sys.exit(1)
    print(f"OK: no readout listed twice ({sum(1 for r in rows if r.get('type') == 'Readout')} readout rows)")


if __name__ == "__main__":
    main()
