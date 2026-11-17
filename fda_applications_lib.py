# -*- coding: utf-8 -*-
"""fda_applications_lib.py -- shared rules for the per-application pages (/fda-application/<appl>).

One page per FDA marketing application (NDA number) names the drug every way people search for it:
brand, ingredient, development code names, the FDA applicant of record, the company that owns it
today and its ticker, and earlier owners or partners. These mappings are the whole value of the page,
and a wrong one is a false claim with a URL, so the rules live here, in ONE place, and both the
builder (build_fda_application_pages.py) and the guard (tests/test_fda_application_pages.py) import
them. The builder drops whatever fails; the guard fails the build if anything that fails is on disk.

Two kinds of fact, two kinds of proof:

  * FDA facts (application number, brand, ingredient, applicant of record, approval dates, the
    products on the application) are NEVER typed by hand. They are read at build time from the FDA's
    Orange Book data files (_orange_book/products.txt, refreshed daily by fetch_orange_book.py).
  * Everything else (code names, today's owner and its ticker, earlier owners and partners) is
    curated in _fda_applications.json, and every mapping carries its own source: a URL on the FDA,
    SEC EDGAR, a newswire carrying the company's own release, or the company's own domain; the
    document's date; the date we read it; and a verbatim quote that itself contains the mapped value.
    A code-name quote must name the code AND the drug; an owner quote must contain the ticker.

Fail closed: if the FDA's applicant of record no longer matches the applicant we verified the owner
against, the owner, ticker and history are withheld (ownership may have moved) until re-verified.
"""
import io
import json
import os
import re
import datetime as dt
from urllib.parse import urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "_fda_applications.json")
OB_PRODUCTS = os.path.join(HERE, "_orange_book", "products.txt")
OB_ASOF = os.path.join(HERE, "_orange_book", "_as_of.txt")

# Domains that are primary for ANY mapping: the regulator, EDGAR, and the wires companies use to
# publish their own releases. Company domains are declared per publisher in the data file.
PRIMARY_DOMAINS = ("fda.gov", "sec.gov", "globenewswire.com", "businesswire.com", "prnewswire.com")

# Same list as tests/test_no_aggregator_sources.py, kept explicit here so a curated row can never
# point at a re-host even if someone adds the host to a company's domain list by mistake.
AGGREGATOR = re.compile(r"(stocktitan\.net|rttnews\.com|seekingalpha\.com|investing\.com|yahoo\.com|"
                        r"benzinga\.com|gurufocus\.com|marketbeat\.com|fool\.com|zacks\.com|tipranks\.com|"
                        r"marketwatch\.com|marketscreener\.com|biopharmawatch\.com|webull\.com|bitget\.com|"
                        r"msn\.com|simianx\.ai|allsci\.com|biopharmcatalyst\.com|wikipedia\.org|drugs\.com|"
                        r"fiercebiotech\.com|fiercepharma\.com|biospace\.com|endpts\.com)", re.I)

APPL_RE = re.compile(r"^(NDA) (\d{6})$")
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TICKER_RE = re.compile(r"^[A-Z]{1,5}$")
HISTORY_ROLES = {
    "sold_to_owner": "sold the product to the current owner",
    "originator": "originated the drug",
    "licensor": "licensed the drug to the current owner",
    "partner": "partner on the drug",
    "parent_of_applicant": "parent company of the FDA applicant",
    "acquired_by_owner": "acquired by the current owner",
    "minority_owner_of_applicant": "holds a minority stake in the FDA applicant",
}


def norm(s):
    return re.sub(r"[^a-z0-9]", "", str(s or "").lower())


def slug_for(appl):
    m = APPL_RE.match(appl)
    return f"{m.group(1).lower()}-{m.group(2)}" if m else ""


def load_data():
    with io.open(DATA, encoding="utf-8") as f:
        return json.load(f)


def ob_as_of():
    try:
        return io.open(OB_ASOF, encoding="utf-8").read().split()[0]
    except Exception:
        return ""


def load_orange_book():
    """{appl_no: [row dict, ...]} for NDA rows of the Orange Book products file."""
    out = {}
    with io.open(OB_PRODUCTS, encoding="utf-8", errors="replace") as f:
        hdr = f.readline().rstrip("\n").split("~")
        for line in f:
            r = dict(zip(hdr, line.rstrip("\n").split("~")))
            if r.get("Appl_Type") == "N":
                out.setdefault(r["Appl_No"], []).append(r)
    return out


def ob_date(s):
    """'Apr 5, 2022' -> '2022-04-05'; 'Approved Prior to Jan 1, 1982' -> ''."""
    try:
        return dt.datetime.strptime(s.strip(), "%b %d, %Y").date().isoformat()
    except Exception:
        return ""


def trade_base(name):
    """Orange Book trade names carry packaging tails: 'TRYNGOLZA (AUTOINJECTOR)' -> 'TRYNGOLZA'."""
    return re.sub(r"\s*\(.*?\)\s*$", "", str(name or "")).strip()


def fda_facts(appl, ob):
    """The FDA's own record for one application, or None when the Orange Book has no row for it."""
    m = APPL_RE.match(appl or "")
    if not m:
        return None
    rows = ob.get(m.group(2)) or []
    if not rows:
        return None
    brands = sorted({trade_base(r["Trade_Name"]) for r in rows})
    applicants = sorted({r["Applicant_Full_Name"].strip() for r in rows})
    ingredients = sorted({r["Ingredient"].strip() for r in rows})
    dates = sorted(d for d in (ob_date(r["Approval_Date"]) for r in rows) if d)
    products = sorted(({"no": r["Product_No"], "trade": r["Trade_Name"].strip(), "form": r["DF;Route"].strip(),
                        "strength": r["Strength"].strip(), "approved": ob_date(r["Approval_Date"]),
                        "rx": r["Type"].strip()} for r in rows), key=lambda p: p["no"])
    return {"brands": brands, "applicants": applicants, "ingredients": ingredients,
            "first_approval": dates[0] if dates else "", "products": products}


def source_problems(src, domains, must_contain=(), any_of=()):
    """Why a curated source is not good enough (empty list = good)."""
    probs = []
    if not isinstance(src, dict):
        return ["no source"]
    url = str(src.get("url") or "")
    host = (urlparse(url).hostname or "").lower()
    if not url.startswith("https://") or not host:
        probs.append(f"source url not https: {url!r}")
    elif AGGREGATOR.search(host):
        probs.append(f"aggregator source {host}")
    else:
        ok = any(host == d or host.endswith("." + d) for d in tuple(PRIMARY_DOMAINS) + tuple(domains))
        if not ok:
            probs.append(f"{host} is not the FDA, EDGAR, a newswire or the publisher's own domain")
    for k in ("publisher", "doc"):
        if not str(src.get(k) or "").strip():
            probs.append(f"source has no {k}")
    for k in ("doc_date", "read"):
        if not ISO.match(str(src.get(k) or "")):
            probs.append(f"source {k} not YYYY-MM-DD")
    q = str(src.get("quote") or "")
    if src.get("quote_2"):
        q = q + " " + str(src["quote_2"])
    if len(str(src.get("quote") or "").strip()) < 12:
        probs.append("no verbatim quote")
    if re.search(r"\bTODO\b|\bTBD\b|\bFIXME\b", " ".join(str(v) for v in src.values())):
        probs.append("source still has a TODO/TBD placeholder")
    nq = norm(q)
    for v in must_contain:
        if norm(v) and norm(v) not in nq:
            probs.append(f"quote does not contain {v!r}")
    if any_of and not any(norm(v) and norm(v) in nq for v in any_of):
        probs.append(f"quote names none of {list(any_of)!r}")
    return probs


def drug_words(entry, fda):
    """Words that name the drug in a source: brand(s) and the ingredient's leading word(s)."""
    out = [entry.get("brand", "")] + list(fda["brands"] if fda else [])
    for ing in (fda["ingredients"] if fda else []) + [entry.get("ingredient", "")]:
        for part in re.split(r";", ing):
            w = part.strip().split(" ")[0]
            if len(w) >= 5:
                out.append(w)
    return [w for w in out if w]


def validate(entry, ob, sponsor_domains):
    """Return (clean_entry_or_None, errors, notes).

    errors: curation flaws (a source that is not primary, a quote that does not contain the value, a brand
    or ingredient that is not the FDA's). The mapping or page is dropped, and the guard FAILS the build.
    notes: the FDA record moved under us (application no longer in the Orange Book, applicant changed).
    The page or owner is withheld (fail closed) and the build goes on; a person re-verifies."""
    probs, notes = [], []
    appl = entry.get("appl", "")
    fda = fda_facts(appl, ob)
    if fda is None:
        return None, [], [f"{appl}: not in the Orange Book (no FDA record to anchor the page); page withheld"]
    if norm(entry.get("brand")) not in {norm(b) for b in fda["brands"]}:
        return None, [f"{appl}: brand {entry.get('brand')!r} is not the FDA trade name {fda['brands']}"], []
    words = drug_words(entry, fda)
    ing = str(entry.get("ingredient") or "").strip()
    ob_words = set(re.findall(r"[a-z0-9]+", " ".join(fda["ingredients"]).lower()))
    stray = [w for w in re.findall(r"[a-z0-9]+", ing.lower()) if w not in ob_words and w not in {"and", "with"}]
    if not ing or stray:
        return None, [f"{appl}: ingredient {ing!r} is not the FDA ingredient {fda['ingredients']} (stray {stray})"], []
    clean = {"appl": appl, "slug": slug_for(appl), "brand": entry["brand"], "fda": fda,
             "ingredient": ing, "drug_pages": [str(x) for x in entry.get("drug_pages") or []],
             "code_names": [], "owner": None, "history": [], "withheld": []}

    def doms(src):
        return sponsor_domains.get(str((src or {}).get("publisher") or ""), [])

    for cn in entry.get("code_names") or []:
        p = source_problems(cn.get("src"), doms(cn.get("src")), must_contain=[cn.get("name")], any_of=words)
        if not re.match(r"^[A-Za-z0-9][A-Za-z0-9 \-/\.]{1,30}$", str(cn.get("name") or "")):
            p.append("code name has odd characters")
        if p:
            probs += [f"{appl} code name {cn.get('name')!r}: {x}" for x in p]
        else:
            clean["code_names"].append(cn)

    applicant_now = fda["applicants"]
    verified = entry.get("applicant_verified")
    if verified and sorted([verified] if isinstance(verified, str) else verified) != applicant_now:
        clean["withheld"].append(
            f"the FDA applicant of record is now {', '.join(applicant_now)}, not {verified}; owner, ticker and "
            f"history withheld until re-verified")
        return clean, probs, notes + [f"{appl}: applicant changed in the Orange Book; owner withheld"]
    if not verified:
        probs.append(f"{appl}: no applicant_verified, owner withheld")
        return clean, probs, notes

    own = entry.get("owner")
    if own:
        p = []
        if not str(own.get("company") or "").strip():
            p.append("owner has no company")
        if not TICKER_RE.match(str(own.get("ticker") or "")):
            p.append("owner ticker malformed")
        p += source_problems(own.get("src"), doms(own.get("src")), must_contain=[own.get("ticker")])
        if p:
            probs += [f"{appl} owner: {x}" for x in p]
        else:
            clean["owner"] = own
    for h in entry.get("history") or []:
        p = []
        if h.get("role") not in HISTORY_ROLES:
            p.append(f"history role {h.get('role')!r} not one of {sorted(HISTORY_ROLES)}")
        tk = str(h.get("ticker") or "")
        if tk and not TICKER_RE.match(tk):
            p.append("history ticker malformed")
        if h.get("date") and not ISO.match(str(h["date"])):
            p.append("history date not YYYY-MM-DD")
        first = str(h.get("company") or "").split(" ")[0]
        p += source_problems(h.get("src"), doms(h.get("src")),
                             any_of=[first] + ([tk] if tk else []))
        if tk:
            # a ticker printed on the page must itself be in the quote
            p += [x for x in source_problems(h.get("src"), doms(h.get("src")), must_contain=[tk])
                  if "does not contain" in x]
        if p:
            probs += [f"{appl} history {h.get('company')!r}: {x}" for x in p]
        else:
            clean["history"].append(h)
    return clean, probs, notes


def all_entries():
    """[(clean_entry, errors, notes)] for every curated application."""
    data = load_data()
    ob = load_orange_book()
    doms = data.get("sponsor_domains") or {}
    return [validate(e, ob, doms) for e in data.get("applications") or []]
