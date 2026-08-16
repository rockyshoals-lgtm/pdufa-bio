# -*- coding: utf-8 -*-
"""conference_presenter_miner.py -- find who has SAID they are presenting, from their own filings.

The /conferences page could only name 10 presenting companies across 41 meetings, which made it look
as though biotech had lost interest in ESMO. The real reason is that conference organisers embargo
abstract titles until a few weeks before the meeting, so the programme genuinely does not exist yet
in public.

But companies announce it themselves, long before the organiser does, because it is material news:
"will present data at the ESMO Congress 2026" appears in 8-Ks and press releases months ahead. That
is a primary source, it is dated, and it is exactly the kind of claim we are willing to publish.

This mines those statements. Same discipline as readout_miner: SIC-gated to actual drug developers
before any document is fetched, every row carries the filing URL and the sentence it was taken from,
and a hit is only kept when the sentence names both the conference and something recognisable as a
program or data set. A company saying it will "attend" an investor day at a conference is not a
company presenting clinical data.

Output is append-only to catalysts_out/conference_presenters_mined.csv. Nothing is published
directly: build_conferences.py reads the file, and the page states plainly that a list built this way
is not the full programme.

    python conference_presenter_miner.py [--days 240] [--limit-confs N] [--dry-run]
"""
import argparse, csv, datetime as dt, json, os, re, sys, time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import readout_miner as RM                                              # noqa: E402

DATA = os.path.join(HERE, "conferences.json")
OUT = os.path.join(HERE, "catalysts_out", "conference_presenters_mined.csv")
COLS = ["ticker", "cik", "company", "conference", "conf_start", "drug", "pres_type",
        "edition_year", "confidence", "form",
        "filing_url", "accession", "filed", "matched_sentence", "retrieved_at"]

# The sentence must say the company is presenting, not merely attending.
PRESENT = re.compile(r"\b(present(?:s|ed|ing|ation[s]?)?|report(?:s|ed|ing)?|showcase[sd]?|"
                     r"share[sd]?|unveil(?:s|ed)?|feature[sd]?)\b", re.I)
# FORWARD COMMITMENT (red team 2026-08-12c, section 3.5 rule 2): of 102 mined rows, fewer than
# 10% were about an UPCOMING conference -- 10-K Business sections recite years of history in
# the same 'presented at X' phrasing. A row is only high-confidence when the clause COMMITS:
FORWARD = re.compile(r"\bwill (?:be )?(?:present|report|shar|featur|highlight|unveil)\w*|"
                     r"\bto be presented\b|\bexpect\w* to (?:be )?present\w*|"
                     r"\bplans? to present\b|\bselected for\b|\baccepted for\b|"
                     r"\babstract accepted\b|\blook forward to (?:present|report|shar)\w*|"
                     r"\bwill be (?:shared|highlighted)\b", re.I)
# PAST-TENSE GOVERNORS (rule 3): 'we presented', 'was presented', 'recently featured' -- the
# company is citing history, not committing to an edition.
PAST_GOV = re.compile(r"\b(?:we|company)\s+(?:recently\s+)?present\w*|\bwas presented\b|"
                      r"\bwere presented\b|\brecently (?:presented|featured)\b|"
                      r"\bpreviously presented\b", re.I)
# rule 8: 'plenary poster' was tagged oral because ORAL matched 'plenary'; 'oral session'
# was missed entirely. POSTER now wins over plenary; ORAL covers sessions.
ORAL = re.compile(r"\b(late[- ]break\w*|oral (?:presentation|session)|proffered paper)\b", re.I)
POSTER = re.compile(r"\b(?:plenary )?poster\b", re.I)
# Signals the sentence is about clinical data rather than a fireside chat.
DATA_WORD = re.compile(r"\b(data|results|analys[ie]s|findings|abstract[s]?|efficacy|safety|"
                       r"phase\s*(?:1|2|3|i{1,3})\b|interim|topline|cohort)\b", re.I)
NOISE = re.compile(r"\b(investor day|fireside|non[- ]deal|roadshow|corporate update call|"
                   r"webcast of|attend)\b", re.I)
MONTHS_RX = ("january|february|march|april|may|june|july|august|september|october|"
             "november|december")


def edition_ok(sentence, conf_code, conf_name, conf_start):
    """Rule 1, the Bug-B killer: the sentence must mean THIS edition. Within +/-200 chars of
    the conference mention, require the edition's own year, or an in-window month with no
    conflicting year; reject on any OTHER 4-digit year near the mention. ZYME's 'ASCO GI data
    presented January 8, 2026' was filed under ASCO GI 2027 by the name-only matcher."""
    year = str(conf_start)[:4]
    low = sentence.lower()
    i = low.find(conf_code.lower())
    if i < 0:
        i = low.find(conf_name.lower()[:22])
    if i < 0:
        return False
    win = sentence[max(0, i - 200):i + 200]
    years = set(re.findall(r"\b(20\d{2})\b", win))
    if years - {year}:
        return False                      # a conflicting year near the mention: wrong edition
    if year in years:
        return True
    # no year at all: accept only an in-window month mention (same-year phrasing like
    # 'at CTAD in November')
    try:
        import datetime as _dt
        sm = _dt.date.fromisoformat(str(conf_start)).month
        month_name = ("january february march april may june july august september october "
                      "november december").split()[sm - 1]
        return bool(re.search(rf"\b{month_name}\b", win, re.I))
    except Exception:
        return False


def sentences(text):
    return re.split(r"(?<=[.!?])\s+", text)


def mine(conf, days, verbose=True):
    """Rows for one conference, from EDGAR full-text search over its own filings."""
    code, name = conf["code"], conf["name"]
    end = dt.date.today()
    start = end - dt.timedelta(days=days)
    # Two phrasings cover most releases; the code alone is far too noisy ("ACC" and "ADA" in
    # particular collide with ordinary English and with other organisations).
    phrases = [f"at the {name}", f"at {name}"]
    if len(code) >= 4 and code.isalpha():
        phrases.append(f"at {code} 2026")

    hits, seen_acc = [], set()
    for phrase in phrases:
        res = RM._fts(phrase, start.isoformat(), end.isoformat())
        if not res:
            continue
        for h in (res.get("hits", {}).get("hits") or []):
            src = h.get("_source", {})
            adsh = (src.get("adsh") or "").strip()
            ciks = src.get("ciks") or []
            if not adsh or not ciks or adsh in seen_acc:
                continue
            seen_acc.add(adsh)
            hits.append((adsh, ciks, src, h.get("_id", "")))
    if not hits:
        return []

    # SIC gate BEFORE fetching any document, exactly as readout_miner does.
    allciks = {str(c).lstrip("0") for _, ciks, _, _ in hits for c in ciks}
    sicmap = RM.sic_for(sorted(allciks), verbose=False)

    rows, seen_co = [], set()
    for adsh, ciks, src, _id in hits:
        cik = str(ciks[0]).lstrip("0")
        sic, _desc = sicmap.get(cik, ("", ""))
        if sic not in RM.DRUG_SIC:
            continue
        fname = (_id.split(":", 1)[1] if ":" in _id else "")
        if not fname:
            continue
        text = RM._doc_text(cik, adsh, fname)
        if not text:
            continue

        form = (src.get("root_forms") or [src.get("form", "")])[0]
        for s in sentences(text):
            if code.lower() not in s.lower() and name.lower()[:22] not in s.lower():
                continue
            if not PRESENT.search(s) or not DATA_WORD.search(s) or NOISE.search(s):
                continue
            if len(s) > 700:
                continue
            # 3.5 rules 1-4: edition anchoring, forward commitment, past-tense rejection,
            # verb proximity. Confidence is computed, and build_conferences publishes only
            # 'high' -- the raw file stays append-only evidence either way.
            if PAST_GOV.search(s):
                continue
            fwd = FORWARD.search(s)
            # rule 4 (the LYEL 'fair presentation' lesson): the committing verb must sit near
            # the conference name, not anywhere in a long sentence
            near_verb = False
            if fwd:
                ci = s.lower().find(code.lower())
                if ci < 0:
                    ci = s.lower().find(name.lower()[:22])
                near_verb = ci >= 0 and abs(fwd.start() - ci) <= 180
            ed_ok = edition_ok(s, code, name, conf["start"])
            confidence = ("high" if (fwd and near_verb and ed_ok
                                     and form not in ("10-K", "10-Q", "20-F"))
                          else "low")
            # extract_program returns (name, kind), not a string. Taking it whole wrote the literal
            # text "(None, None)" into the drug column, which would have shipped as a drug name.
            drug = ""
            try:
                got = RM.extract_program(s)
                if isinstance(got, (tuple, list)):
                    got = got[0] if got else None
                drug = got or ""
            except Exception:
                drug = ""
            # rule 8: poster wins over plenary (ENTX's 'plenary poster' is a poster)
            ptype = ("poster" if POSTER.search(s)
                     else "oral/late-breaker" if ORAL.search(s) else "presentation")
            company = (src.get("display_names") or [""])[0]
            tick = ""
            m = RM.TICK.search(company)
            if m:
                tick = m.group(1)
            # rule 6: no ticker, no row -- 14 of 102 rows had none and cannot be traded,
            # linked, or deduped reliably
            if not tick:
                continue
            # One row per company per conference. A company that files three 8-Ks mentioning ESMO
            # is presenting at ESMO once, and listing it three times would overstate the programme.
            ident = (tick or re.sub(r"\s*\(.*", "", company).lower())
            if ident in seen_co:
                break
            seen_co.add(ident)
            rows.append({
                "ticker": tick, "cik": cik, "company": re.sub(r"\s*\(.*", "", company),
                "conference": code, "conf_start": conf["start"], "drug": drug,
                "pres_type": ptype,
                "edition_year": str(conf["start"])[:4], "confidence": confidence,
                "form": form,
                "filing_url": f"https://www.sec.gov/Archives/edgar/data/{cik}/"
                              f"{adsh.replace('-', '')}/{fname}",
                "accession": adsh, "filed": (src.get("file_date") or ""),
                "matched_sentence": re.sub(r"\s+", " ", s)[:400],
                "retrieved_at": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"})
            break                                   # one row per filing is enough
        time.sleep(0.12)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=240)
    ap.add_argument("--limit-confs", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    data = json.load(open(DATA, encoding="utf-8"))
    today = dt.date.today().isoformat()
    horizon = (dt.date.today() + dt.timedelta(days=200)).isoformat()
    confs = [c for c in data["conferences"] if today <= c["start"] <= horizon]
    confs.sort(key=lambda c: c["start"])
    if a.limit_confs:
        confs = confs[:a.limit_confs]

    existing = set()
    if os.path.exists(OUT):
        for r in csv.DictReader(open(OUT, encoding="utf-8-sig", errors="replace")):
            existing.add((r.get("accession"), r.get("conference")))

    def flush(rows):
        """Append after EACH conference, not at the end.

        The first version accumulated everything in memory and wrote once at the end. That run took
        well over ten minutes against EDGAR, and anything that killed it, a timeout or a rate-limit
        wobble, would have thrown away every row. Same lesson as the T-120 cache: a long job that
        writes once is a job that loses all its work.
        """
        if not rows or a.dry_run:
            return
        new_file = not os.path.exists(OUT)
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        with open(OUT, "a", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=COLS)
            if new_file:
                w.writeheader()
            for r in rows:
                w.writerow(r)

    total = 0
    for c in confs:
        try:
            rows = mine(c, a.days)
        except Exception as e:
            print(f"  {c['code']:<11} error {type(e).__name__}")
            continue
        fresh = [r for r in rows if (r["accession"], r["conference"]) not in existing]
        for r in fresh:
            existing.add((r["accession"], r["conference"]))
        flush(fresh)
        total += len(fresh)
        print(f"  {c['code']:<11} {c['start']}  {len(rows):>3} matched, {len(fresh):>3} new")
        if a.dry_run:
            for r in fresh[:3]:
                print(f"      {(r['ticker'] or r['company'][:16]):<18} {r['pres_type']:<18} "
                      f"{r['drug'][:24]}")

    print(f"\n{total} new presenter row(s) across {len(confs)} conference(s)"
          + (" [dry run, nothing written]" if a.dry_run else
             f" -> {os.path.relpath(OUT, HERE)}"))


if __name__ == "__main__":
    main()
