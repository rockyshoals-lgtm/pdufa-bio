# -*- coding: utf-8 -*-
"""enrich_ticker_hubs.py -- make every ticker page name the company, and stop it repeating
unverified outcomes as fact.

Two problems, same 209 pages.

1. ENTITY. Every hub was titled "SLS FDA Calendar: PDUFA Dates & Decision History" -- ticker only,
   no company, no drug, no indication. There was nothing for a search engine to bind to the
   biotech, which is why Google's "people also search for" on SLS returns SLS mortgage, SLS Dubai
   and SLS toothpaste. The fix is to say who the company is, in the title, the H1, the description
   and in Organization JSON-LD with tickerSymbol and a sameAs pointing at the company's SEC filing
   index. Company names come from SEC's own ticker file, so they are authoritative, not guessed.

2. UNVERIFIED OUTCOMES, AGAIN. The hubs list decision history with the same green tick / red cross
   used for primary-sourced records, including for the 307 price-inferred ones. We just spent a
   commit removing exactly that from the decision pages themselves; leaving it on the hubs would
   defeat the point. Inferred rows are relabelled here too.

Thin pages: a hub whose only content is unverified, or which has no catalysts at all, is set
noindex. It stays for internal navigation, but we do not ask Google to rank a page that tells a
reader nothing we have checked.

    python enrich_ticker_hubs.py [--dry-run]
"""
import argparse, collections, glob, json, os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
TMAP = os.path.join(HERE, "bpc_data", "_edgar_ticker_map.json")

SUFFIX = re.compile(r",?\s+(inc|corp|corporation|ltd|limited|plc|llc|co|company|holdings|group|"
                    r"sa|nv|ag|ab|as|oyj|therapeutics inc)\.?$", re.I)


def pretty_company(name):
    """SEC writes some names in caps ("NVIDIA CORP"). Title-case only the shouted ones, and never
    touch names that already look hand-cased, so 'SELLAS Life Sciences Group, Inc.' survives."""
    if not name:
        return ""
    letters = [c for c in name if c.isalpha()]
    if letters and sum(c.isupper() for c in letters) / len(letters) > 0.85:
        name = " ".join(w if len(w) <= 3 and w.isupper() else w.capitalize() for w in name.split())
        name = re.sub(r"\bInc\b\.?", "Inc.", name)
    return name.strip()


def load_events():
    p = os.path.join(SITE, "api", "v1", "dataset.mjs")
    src = open(p, encoding="utf-8", errors="replace").read().replace("\x00", "")
    arr, _ = json.JSONDecoder().raw_decode(src[src.find("["):])
    by = collections.defaultdict(list)
    for r in arr:
        if r.get("t"):
            by[r["t"]].append(r)
    return by


def decision_facts():
    """{ticker: {'verified': [...], 'inferred': [...], 'drugs': set, 'inds': set}} from the pages
    themselves, which is the only place the sourced/inferred distinction actually lives."""
    out = collections.defaultdict(lambda: {"verified": [], "inferred": [], "drugs": set(),
                                           "inds": set()})
    for p in glob.glob(os.path.join(SITE, "fda-decision", "*", "index.html")):
        slug = os.path.basename(os.path.dirname(p))
        m = re.match(r"([A-Z]+)-(\d{4}-\d{2}-\d{2})$", slug)
        if not m:
            continue
        tk, d = m.group(1), m.group(2)
        t = open(p, encoding="utf-8", errors="replace").read()
        rec = out[tk]
        (rec["inferred"] if "price-only" in t else rec["verified"]).append(d)
        if "price-only" not in t:
            dm = re.search(r"<span>Drug / candidate</span><b>([^<]{2,90})</b>", t)
            im = re.search(r"<span>Indication</span><b>([^<]{2,90})</b>", t)
            if dm:
                rec["drugs"].add(re.sub(r"\s+", " ", dm.group(1)).strip())
            if im:
                rec["inds"].add(re.sub(r"\s+", " ", im.group(1)).strip())
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    tmap = {}
    if os.path.exists(TMAP):
        tmap = {k.upper(): v for k, v in json.load(open(TMAP, encoding="utf-8")).items()}
    events = load_events()
    dfacts = decision_facts()

    changed = noindexed = named = 0
    for p in sorted(glob.glob(os.path.join(SITE, "ticker", "*", "index.html"))):
        tk = os.path.basename(os.path.dirname(p))
        t = open(p, encoding="utf-8", errors="replace").read()
        o = t
        evs = events.get(tk, [])
        df = dfacts.get(tk, {"verified": [], "inferred": [], "drugs": set(), "inds": set()})

        company = pretty_company(
            next((e.get("company") for e in evs if (e.get("company") or "").strip()), "")
            or tmap.get(tk, ""))
        # names arrive as "mRNA-1010 - (P304)" or "Deramiocel (CAP-1002) - (HOPE-2)": drop the
        # trial/programme parenthetical and any punctuation it leaves behind.
        drugs = {re.sub(r"[\s\-,:;]+$", "", re.sub(r"\s*[\(\[].*$", "", (e.get("name") or "")).strip())
                 for e in evs}
        drugs |= df["drugs"]
        drugs = sorted({d for d in drugs if 2 < len(d) < 60})[:4]
        inds = sorted({i for i in df["inds"] if 3 < len(i) < 70})[:2]
        upcoming = [e for e in evs if (e.get("st") or "") in ("Upcoming", "Guided", "Awaiting")]

        # ---- 1. name the company everywhere the search engine looks -------------------------
        if company:
            named += 1
            # Keep the visible part under ~62 chars so Google does not truncate the company name,
            # which is the whole point of the rewrite. Drop assets before dropping the entity.
            base = f"{company} ({tk}) FDA Catalysts"
            title = base
            for n in (2, 1):
                cand = base + ": " + ", ".join(d[:28] for d in drugs[:n]) if drugs[:n] else base
                if len(cand) <= 62:
                    title = cand
                    break
            title = title[:62].rstrip(" ,:-") + " | pdufa.bio"
            # lambda, not a template string: a company name containing a backslash would
            # otherwise be parsed as a regex escape and blow up the run.
            _title = "<title>" + title.replace("&", "&amp;") + "</title>"
            t = re.sub(r"<title>.*?</title>", lambda m: _title, t, count=1, flags=re.S)
            t = re.sub(r'(<meta property="og:title" content=")[^"]*(")',
                       lambda m: m.group(1) + title.replace('"', "").replace("&", "&amp;") + m.group(2), t)
            # 2026-08-20: this string was unbounded and broke THREE CI runs -- long drug names +
            # a long indication pushed /ticker/IRD to 249 chars and test_meta_lengths (max 160)
            # went red for two days. Degrade gracefully: full form, then drop the indication,
            # then fewer drugs, then a word-boundary cut. Never emit >158.
            tail = (f". {len(df['verified'])} verified FDA decision(s) on file. "
                    f"Facts and dates only; verify against primary filings.")
            head = (f"{company} ({tk}) FDA catalyst hub: PDUFA dates, advisory committee "
                    f"meetings and clinical readouts we track")
            desc = ""
            for nd, use_ind in ((3, True), (3, False), (1, False), (0, False)):
                cand = (head + (f" for {', '.join(drugs[:nd])}" if drugs[:nd] else "")
                        + (f" in {inds[0]}" if use_ind and inds else "") + tail)
                if len(cand) <= 158:
                    desc = cand
                    break
            if not desc:
                desc = (head + tail)[:158].rsplit(" ", 1)[0].rstrip(",;:") + "."
            t = re.sub(r'(<meta name="description" content=")[^"]*(")',
                       lambda m: m.group(1) + desc.replace('"', "") + m.group(2), t, count=1)
            t = re.sub(r'(<meta property="og:description" content=")[^"]*(")',
                       lambda m: m.group(1) + desc.replace('"', "") + m.group(2), t, count=1)
            _h1 = (f'<h1>{company} <span class="g">({tk})</span> FDA catalysts '
                   f'&amp; readout calendar</h1>')
            t = re.sub(r"<h1>[A-Z.\-]+ <span class=\"g\">FDA calendar</span> &amp; decision history</h1>",
                       lambda m: _h1, t, count=1)

        # ---- 2. inferred decisions must not wear the verified badge -------------------------
        if df["inferred"]:
            for d in df["inferred"]:
                t = re.sub(r'(<a class="row" href="/fda-decision/' + tk + r'-' + d +
                           r'">\s*<span class="t">[^<]*)<span class="badge (?:crl|app)">[^<]*</span>',
                           r'\1<span class="badge amb">unverified</span>', t)
            t = t.replace('<span class="d">FDA decision</span>',
                          '<span class="d">FDA decision</span>')

        # ---- 3. Organization JSON-LD so the ticker resolves to the company -----------------
        if company and "\"@type\":\"Organization\"" not in t:
            cik = None
            org = {"@context": "https://schema.org", "@type": "Organization",
                   "name": company, "tickerSymbol": tk, "alternateName": tk,
                   "url": f"https://www.pdufa.bio/ticker/{tk}",
                   "sameAs": [f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany"
                              f"&company={tk}&type=&dateb=&owner=include&count=40"]}
            t = t.replace("</head>", "<script type=\"application/ld+json\">"
                          + json.dumps(org, separators=(",", ":")) + "</script></head>", 1)

        # ---- 4. thin / unverified-only hubs should not be offered to search -----------------
        substantive = bool(df["verified"]) or bool(upcoming)
        if not substantive:
            t = re.sub(r'(<meta name="robots" content=")[^"]*(")', r"\1noindex,follow\2", t, count=1)
            if "nothing we have verified" not in t:
                t = t.replace("</h1>", "</h1><p class=\"note\" style=\"color:#f0c86a\">"
                              "We do not currently track a confirmed FDA catalyst for "
                              f"{company or tk}. Any decision listed below was inferred from share-price "
                              "behaviour and has not been checked against a filing, so there is "
                              "nothing we have verified to show here yet.</p>", 1)
            noindexed += 1

        if t != o:
            changed += 1
            if not a.dry_run:
                open(p, "w", encoding="utf-8").write(t)

    print(f"{'would update' if a.dry_run else 'updated'} {changed} ticker hub(s); "
          f"{named} now name the company; {noindexed} set noindex (no verified catalyst)")


if __name__ == "__main__":
    main()
