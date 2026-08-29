# -*- coding: utf-8 -*-
"""build_drug_pages.py -- a page per drug, because drug names are the only queries we convert on.

The GSC click data settles this: over three months, every non-branded click the site earned came
from a drug-name query -- "deramiocel pdufa", "monalizumab", "miplyffa" -- at 50-100% CTR on one or
two impressions, and two of those three had NO dedicated page; Google was surfacing something
adjacent. Meanwhile ~250 impressions on head "pdufa calendar/date" terms produced zero clicks at
position ~20. The demand we can win is entity demand, and this builds the surface for it.

WHAT GETS A PAGE, AND WHAT DOES NOT

The dataset's name field is not clean: alongside "Cenerimod" it holds "LEVEL-2 readout" (a trial,
not a drug), "150ug CFA (Elonva) at stimulation day (SD) 1 an" (a truncated protocol description)
and "Annamycin readout" (a drug plus a descriptor). Publishing /drug/level-2-readout would be
exactly the junk-page problem the GSC audit says is suppressing our crawl budget, so a validator
gates every candidate and the build prints what it rejected and why. Descriptors are stripped
("Annamycin readout" -> Annamycin); strings that do not look like a drug name after cleaning are
dropped, not repaired into something we would be guessing at.

Every fact on the page is already published elsewhere on the site -- catalyst rows from the
dataset, outcomes from the decisions archive -- so these pages introduce no new claims, only a new
door. Each links its sources: the ticker hub, the event page, the decision page.

Idempotent: pages are regenerated from scratch each run, and a drug that disappears from the data
loses its page (a stale drug page asserting an upcoming catalyst that no longer exists would be a
false claim with a URL).

    python build_drug_pages.py [--dry-run]
"""
import argparse, datetime as dt, glob, html, json, os, re, shutil, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
OUT = os.path.join(SITE, "drug")
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")
BASE = "https://www.pdufa.bio"

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# Trailing descriptors that name an EVENT about the drug, not the drug.
#
# NO acronym group in here. The first version had (?:[A-Z]{2,6}\s+)? to strip trial acronyms, and
# because the whole pattern ran under re.I that character class matched lowercase word ENDINGS:
# "anifrolumab readout" lost "olumab readout" and published /drug/anifr; "Clinical readout" became
# /drug/cl. Five garbage pages from one careless flag. Trial-name tails are handled by the CORE
# reduction instead, which never removes characters from inside a word.
DESCRIPTOR = re.compile(
    r"\s*(?:Phase\s+[0-9][ab]?(?:/[0-9][ab]?)?\s*)?"
    r"(?:readout|topline|data|results?|interim|update|dose\s*\d*)\s*$", re.I)

# Words that are trial names or generic study vocabulary, not drugs. LEVEL-2 and REGAL are trials;
# "VGX-3100" and "A-101" are drugs; the difference a regex can see is that trial names are built on
# ordinary English words. Kept small and explicit rather than clever.
TRIAL_WORDS = {"level", "regal", "hope", "reset", "glow", "vanquish", "luminous", "clinical",
               "combined", "interim", "topline", "open-label", "pivotal", "registrational"}

# Organisation vocabulary ANYWHERE in the name means this is a conference, not a drug. The first
# pass checked only the first word and published /drug/american-society, /drug/eur-society,
# /drug/european-society and /drug/society-for -- four conference fragments wearing drug URLs.
ORG_WORDS = {"society", "congress", "association", "academy", "college", "meeting", "symposium",
             "conference", "annual", "committee", "convergence", "sessions"}

# Conference acronyms reject a MULTI-WORD name ("ACR Convergence", "AASLD The Liver Meeting") but
# never a hyphenated code: ACR-368 is a real Acrivon drug candidate, so the check requires a space.
# Both /drug/aasld-the and /drug/acr-convergence shipped before this existed.
CONF_ACRONYMS = {"aasld", "acr", "asco", "esmo", "aacr", "ash", "aan", "eha", "sitc", "easd",
                 "ada", "acc", "ers", "sno", "ectrims", "aha", "asn", "aua", "ata", "scai"}

# Hard rejections: strings that are trial names, dosing protocols or sentence fragments.
JUNK = re.compile(
    r"\breadout\b|\btopline\b|\bstimulation\b|\bday\s*\(|\bSD\)|μg|\bmg\b|\blow dose\b"
    r"|\bhigh dose\b|\bcohort\b|\barm\b|\bweek \d|\bn=\d|\bvs\.?\b|\bplus\b.*\bplus\b", re.I)


CORE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9'\u2019./-]*(?:\s+[A-Za-z0-9][A-Za-z0-9'\u2019./-]*)?)"
                  r"(\s*\([^()]{2,45}\))?")


def paren_rescue(raw):
    """The drug hiding inside a rejected string's parenthetical, if there is one.

    'REGAL Phase 3 (galinpepimut-S) topline, event-driven' is a trial description and is rightly
    rejected -- but galinpepimut-S is SELLAS's lead program and deserves its page. When the outer
    string fails validation, each parenthetical is tried as a candidate in its own right (once,
    no recursion), accepting only content with lowercase letters, so acronyms like (CTGTAC) or
    (HOPE-2) are not promoted into drugs.
    """
    for inner in re.findall(r"\(([^()]{3,45})\)", str(raw or "")):
        if not re.search(r"[a-z]", inner):
            continue
        got = clean_name(inner, rescue=False)
        if got:
            return got
    return None


def clean_name(raw, rescue=True):
    """The drug's CORE name, or None if this string does not confidently name a drug.

    Core means "Brand (generic)" or just the name -- one or two words plus an optional
    parenthetical. Everything after that is trial names, dose arms and indication acronyms:
    "Deramiocel (CAP-1002) HOPE-2" and "Deramiocel (CAP-1002) CTGTAC DMD" are the same drug, and
    the first run gave it two pages because the tails differ. Reducing to the core both dedupes
    and rescues names truncated mid-sentence at source ("Ameluz (aminolevulinic acid
    hydrochloride) topical gel in co" -> the brand form), which is better than rejecting a real
    drug because its row carried a broken tail.
    """
    s = re.sub(r"\s+", " ", str(raw or "")).strip(" -:\u2013")
    # Pronunciation guides ride along in caps parens with no digits: "MIPLYFFA (MY-PLY-FAH)
    # (arimoclomol)". Removing them BEFORE the core match lets the core keep the paren that
    # matters -- the generic name -- instead of spending its one parenthetical on the sound-out.
    s = re.sub(r"\(\s*[A-Z][A-Z' -]{2,}\s*\)", " ", s)
    # Modality descriptions ride BETWEEN the code name and the generic: "DTX401 AAV gene therapy
    # (pariglasgene brecaparvovec)". CORE's two words would take "DTX401 AAV" and never reach the
    # parenthetical, publishing /drug/dtx401-aav while /drug/dtx401 and the generic 404 (red team
    # 2026-08-10/11, Ultragenyx PDUFA T-12). The modality is a category, not a name -- remove it so
    # the core becomes "DTX401 (pariglasgene brecaparvovec)". Never matches inside a word.
    s = re.sub(r"\s+(?:AAV|rAAV\w*|lentiviral|mRNA|siRNA)?\s*\b(?:gene|cell)[ -]therapy\b", " ", s,
               flags=re.I)
    s = re.sub(r"\s+", " ", s).strip(" -:\u2013")
    prev = None
    while s != prev:
        prev = s
        s = DESCRIPTOR.sub("", s).strip(" -:\u2013")
    m = CORE.match(s)
    if not m:
        return None
    paren = m.group(2) or ""
    # A parenthetical in ALL CAPS is an advisory-committee or trial acronym riding along with the
    # name -- "Deramiocel (CTGTAC)" is Deramiocel at a CTGTAC meeting, not a drug called that. Drop
    # it so the entry merges with the drug's other rows instead of spawning a second page.
    inner = paren.strip(" ()")
    if inner and inner.isupper() and len(inner) >= 4 and "-" not in inner:
        paren = ""
    s = (m.group(1) + paren).strip()
    words = {w.lower() for w in re.findall(r"[A-Za-z][A-Za-z-]*", s)}
    first = re.split(r"[\s(-]", s, maxsplit=1)[0].lower()
    if first in TRIAL_WORDS or s.lower() in TRIAL_WORDS:
        return paren_rescue(raw) if rescue else None
    if words & ORG_WORDS:
        return paren_rescue(raw) if rescue else None
    if first in CONF_ACRONYMS and " " in s:
        return paren_rescue(raw) if rescue else None
    if s.isdigit() or len(re.sub(r"[^A-Za-z0-9]", "", s)) < 3:
        return None
    if not (2 <= len(s) <= 70):
        return None
    if JUNK.search(s):
        return paren_rescue(raw) if rescue else None
    if s.count("(") != s.count(")"):
        return None
    # Articles and prepositions as the first WORD mean a sentence fragment, but the boundary must
    # be whitespace: \b after "A" also matches "A-101", which is a real drug candidate and was
    # falsely rejected on the first run.
    if re.match(r"^(?:the|a|an|in|for|with)\s", s, re.I):
        return None
    return s


def slugify(name):
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s[:60].rstrip("-")


def pretty(d, dp="day"):
    y, m, day = int(d[:4]), int(d[5:7]), int(d[8:10])
    if dp == "day":
        return f"{MONTHS[m - 1]} {day}, {y}"
    if dp == "month":
        return f"{MONTHS[m - 1]} {y}"
    return f"Q{(m - 1) // 3 + 1} {y}"


def esc(s):
    return html.escape(str(s or ""), quote=True)


SHELL = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{canon}">
<meta property="og:title" content="{title}"><meta property="og:description" content="{desc}">
<link rel="preload" href="/fonts/SpaceGrotesk-700.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="/fonts/IBMPlexMono-600.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="/fonts/fonts.css">
<style>
:root{{--bg:#0b1017;--card:#111826;--line:#1f2a3c;--mut2:#8fa3bd;--gold:#e8b44c}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:#dfe9f7;
font:15px/1.65 "IBM Plex Mono",ui-monospace,monospace}}
.wrap{{max-width:880px;margin:0 auto;padding:18px 16px 60px}}
.top{{display:flex;justify-content:space-between;align-items:center;margin-bottom:22px}}
.brand{{font-family:"Space Grotesk",sans-serif;font-weight:700;font-size:20px;color:#fff;
text-decoration:none}}.brand b{{color:var(--gold)}}
.nav a{{color:var(--mut2);text-decoration:none;margin-left:14px;font-size:13px}}
h1{{font-family:"Space Grotesk",sans-serif;font-size:26px;margin:0 0 6px}}
h2{{font-family:"Space Grotesk",sans-serif;font-size:17px;margin:26px 0 8px}}
.row{{display:flex;flex-wrap:wrap;gap:10px;justify-content:space-between;padding:11px 0;
border-top:1px solid var(--line);color:inherit;text-decoration:none}}
.row:hover{{background:#141d2d}}
.t{{font-weight:600}}.d{{color:var(--mut2);font-size:13.5px}}
.ok{{color:#46d17f}}.bad{{color:#ff8f6b}}
a.lit{{color:#9ec5ff}}
.legal{{margin-top:40px;padding-top:14px;border-top:1px solid var(--line);color:var(--mut2);
font-size:12px;line-height:1.7}}
</style></head><body><div class="wrap">
<div class="top"><a class="brand" href="/">pdufa<b>.bio</b></a>
<div class="nav"><a href="/calendar">Calendar</a><a href="/decisions">Decisions</a>
<a href="/readouts">Readouts</a></div></div>
<h1>{h1}</h1>
{body}
<div class="legal">Facts and dates only; not investment advice. Verify against primary FDA, SEC
and company filings. pdufa.bio is not affiliated with the FDA.</div>
</div></body></html>
"""


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    rows = json.loads(re.search(r"export default (\[.*\])",
                                open(DATASET, encoding="utf-8", errors="replace").read(),
                                re.S).group(1))

    # outcome facts from the decisions archive
    arch = {}
    darch = os.path.join(SITE, "decisions", "index.html")
    if os.path.exists(darch):
        dh = open(darch, encoding="utf-8", errors="replace").read()
        for tk, day, frag in re.findall(
                r'<a class="row" href="/fda-decision/([A-Z]{1,6})-(\d{4}-\d{2}-\d{2})"[^>]*>(.*?)</a>',
                dh, re.S):
            txt = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", frag))).strip()
            outcome = ("Approved" if re.search(r"\bapproved\b", txt, re.I)
                       else "CRL" if re.search(r"\bcrl\b|complete response", txt, re.I) else "")
            arch.setdefault((tk, day), outcome)

    # SECOND SOURCE: the decision pages themselves. The dataset only carries live catalysts, so a
    # drug whose story is finished -- MIPLYFFA, one of exactly three queries with a documented
    # 100%-CTR click -- had no page because its only rows are in the archive. Each decision page's
    # title carries the full drug string ("MIPLYFFA (MY-PLY-FAH) (arimoclomol)") where the archive
    # row truncates it, so the titles are the source. A synthesized row points at the decision
    # page, which carries the outcome, the chart and the provenance: nothing new is claimed.
    T1 = re.compile(r"^([A-Z]{1,6}) FDA Decision ([^:]+): (Approved|Complete Response Letter)"
                    r"\s*-\s*(.+?)\s*\|", re.I)
    T2 = re.compile(r"^([A-Z]{1,6}) FDA Decision \(([^)]+)\):\s*(.+?):\s*"
                    r"(Approved|Complete Response Letter|CRL)\s*\|", re.I)
    arch_rows = []
    for dp_ in sorted(glob.glob(os.path.join(SITE, "fda-decision", "*", "index.html"))):
        slug_ = os.path.basename(os.path.dirname(dp_))
        md_ = re.match(r"([A-Z]{1,6})-(\d{4}-\d{2}-\d{2})$", slug_)
        if not md_:
            continue
        doc_ = open(dp_, encoding="utf-8", errors="replace").read()
        tm_ = re.search(r"<title[^>]*>(.*?)</title>", doc_, re.S)
        if not tm_:
            continue
        ttl_ = html.unescape(re.sub(r"\s+", " ", tm_.group(1))).strip()
        m1, m2 = T1.match(ttl_), T2.match(ttl_)
        drug_ = m1.group(4) if m1 else (m2.group(3) if m2 else "")
        if not drug_:
            continue
        # The title may carry a shortened form ("MIPLYFFA (MY-PLY-FAH)") while the page body holds
        # the full one with the generic name ("MIPLYFFA (MY-PLY-FAH) (arimoclomol)"). The generic
        # is what people search, so if the body extends the title's drug with a lowercase
        # parenthetical, take the extended form.
        ext_ = re.search(re.escape(drug_) + r"\s*\(([a-z][a-z0-9 -]{4,40})\)",
                         html.unescape(doc_))
        if ext_:
            drug_ = f"{drug_} ({ext_.group(1)})"
        arch_rows.append({"t": md_.group(1), "d": md_.group(2), "dp": "day", "type": "PDUFA",
                          "st": "Decided", "name": drug_,
                          "url": f"/fda-decision/{slug_}"})
    print(f"archive source: {len(arch_rows)} decided rows with a parseable drug name")

    # THIRD SOURCE (audit 2026-08-18c): curated under-review rows. AI grounding queries cite us
    # for drugs with a live FDA application but NO public action date ("pdufa date for
    # daraonrasib" -- 14 citations, 47 impressions, no page). No dataset row can honestly carry
    # them: a row needs a date and inventing one breaks the precision rules. These rows render
    # when_text where a date would be, and the honest answer -- "accepted on X, date not
    # public" -- IS the page. Every row carries its primary source.
    manual_rows = []
    try:
        manual_rows = json.load(open(os.path.join(HERE, "_drug_pages_manual.json"),
                                     encoding="utf-8")).get("rows", [])
        print(f"manual source: {len(manual_rows)} under-review row(s)")
    except Exception:
        pass

    # Confirmed readout outcomes: an event with a reported result must not be presented as an
    # upcoming catalyst on its drug page, and its row should link the company release.
    try:
        confirmed = {c.get("id"): c for c in json.load(
            open(os.path.join(HERE, "readout_reported_manual.json"), encoding="utf-8")
        ).get("reported", [])}
    except Exception:
        confirmed = {}

    drugs = {}
    rejected = []
    for r in rows + arch_rows + manual_rows:
        name = clean_name(r.get("name"))
        if not name:
            if str(r.get("name") or "").strip():
                rejected.append(str(r.get("name"))[:60])
            continue
        # Key on the brand token(s) alone, so "Deramiocel" and "Deramiocel (CAP-1002)" are one
        # page. The parenthetical stays in the DISPLAY name -- and the form whose parenthetical
        # looks like a generic (has lowercase) beats a bare name, because "Brand (generic)" is the
        # form both searchers and the FDA use.
        slug = slugify(re.split(r"\s*\(", name)[0])
        if not slug:
            continue
        d = drugs.setdefault(slug, {"name": name, "rows": []})
        cur_has = "(" in d["name"] and re.search(r"\([^)]*[a-z]", d["name"])
        new_has = "(" in name and re.search(r"\([^)]*[a-z]", name)
        if (new_has and not cur_has) or (bool(new_has) == bool(cur_has) and len(name) > len(d["name"])):
            d["name"] = name
        d["rows"].append(r)

    # GENERIC <-> BRAND ALIAS JOIN (2026-08-29). Keying on the brand token splits
    # "Ziihera (zanidatamab-hrii)" and "Zanidatamab" into separate pages, and the generic
    # page then sees none of the brand page's events. /drug/zanidatamab -- holder of the
    # only 100%-share AI grounding query on the property -- said "no FDA decisions are on
    # record" while the FDA had approved zanidatamab twice under Ziihera. That sentence was
    # false on its face. Where a brand page's parenthetical is the generic name of another
    # page (with or without the FDA's 4-letter suffix, -hrii and the like), the generic
    # page inherits the brand page's rows and states the marketing name. Events render with
    # their own links, so nothing is claimed twice.
    for slug in list(drugs):
        m = re.search(r"\(([a-z][a-z0-9-]{4,40})\)\s*$", drugs[slug]["name"])
        if not m:
            continue
        gen = slugify(re.sub(r"-[a-z]{4}$", "", m.group(1)))
        if gen and gen != slug and gen in drugs:
            g = drugs[gen]
            have = {(str(r.get("t") or ""), str(r.get("d") or "")) for r in g["rows"]}
            extra = [r for r in drugs[slug]["rows"]
                     if (str(r.get("t") or ""), str(r.get("d") or "")) not in have]
            if extra:
                g["rows"].extend(extra)
                g["marketed_as"] = (drugs[slug]["name"], slug)
                print(f"  alias join: /drug/{gen} inherits {len(extra)} event(s) from "
                      f"/drug/{slug} ({drugs[slug]['name']})")

    # regenerate from scratch: a vanished drug must lose its page.
    # Windows quirk (2026-08-12): synced folders set the ReadOnly attribute on directories, and
    # os.rmdir then fails with Access Denied. The onexc handler clears the attribute and retries,
    # so a local run behaves like the Linux CI run instead of dying on the first flagged dir.
    if not a.dry_run:
        if os.path.isdir(OUT):
            def _unlock(fn, path, _exc):
                os.chmod(path, 0o777)
                fn(path)
            try:
                shutil.rmtree(OUT, onexc=_unlock)          # Python >= 3.12
            except TypeError:
                shutil.rmtree(OUT, onerror=lambda f, p, e: (_unlock(f, p, e)))
        os.makedirs(OUT, exist_ok=True)

    today = dt.datetime.now(dt.timezone.utc).date().isoformat()
    written = 0
    index_items = []

    for slug, d in sorted(drugs.items()):
        name = d["name"]
        rs = sorted(d["rows"], key=lambda r: r.get("d") or "")
        tks = sorted({str(r.get("t") or "").upper() for r in rs if r.get("t")})
        comps = sorted({r.get("company") for r in rs if r.get("company")})
        inds = sorted({(r.get("_d") or {}).get("indication") for r in rs
                       if (r.get("_d") or {}).get("indication")})

        events = []
        n_dec = 0
        for r in rs:
            day = r.get("d") or ""
            dp = r.get("dp") or "day"
            typ = str(r.get("type") or "catalyst")
            typ = typ.upper() if typ.lower() == "pdufa" else typ
            tk = str(r.get("t") or "").upper()
            outcome = arch.get((tk, day), "")
            decided = str(r.get("st") or "").lower() == "decided"
            if decided and not outcome:
                outcome = "decided"
            if outcome and outcome not in ("decided",):
                n_dec += 1
            when = (r.get("when_text")
                    or (pretty(day, dp) if re.match(r"^\d{4}-\d{2}-\d{2}$", day) else day))
            conf = confirmed.get(r.get("id"))
            if conf:
                oc = str(conf.get("outcome", "")).lower()
                ocol = "ok" if oc == "positive" else "bad"
                when = pretty(conf.get("reported_date", day))
                badge = (f' <span class="{ocol}">&#10003; data reported'
                         + (f' &middot; {"+" if (conf.get("day_move_pct") or 0) >= 0 else ""}'
                            f'{conf["day_move_pct"]:.1f}%' if conf.get("day_move_pct") is not None
                            else "") + "</span>")
                events.append(
                    f'<a class="row" href="{esc(conf.get("source_url") or "#")}" rel="nofollow">'
                    f'<span class="t">{esc(typ)} &middot; {esc(when)}{badge}</span>'
                    f'<span class="d">{esc(tk)}</span></a>')
                continue
            badge = (f' <span class="ok">&#10003; Approved</span>' if outcome == "Approved"
                     else f' <span class="bad">CRL</span>' if outcome == "CRL" else "")
            href = (f"/fda-decision/{tk}-{day}" if outcome in ("Approved", "CRL")
                    else str(r.get("url") or f"/ticker/{tk}"))
            events.append(
                f'<a class="row" href="{esc(href)}"><span class="t">{esc(typ)} &middot; '
                f'{esc(when)}{badge}</span><span class="d">{esc(tk)}</span></a>')

        if not events:
            continue

        # answer-first lede, from the same rows the table shows
        up = [r for r in rs if ((r.get("d") or "") >= today or
                                str(r.get("st") or "").lower() == "under review")
              and str(r.get("st") or "").lower() != "decided"
              and r.get("id") not in confirmed]
        _dec = sorted(((r.get("d"), arch.get((str(r.get("t") or "").upper(), r.get("d") or "")))
                       for r in rs
                       if arch.get((str(r.get("t") or "").upper(), r.get("d") or ""))
                       in ("Approved", "CRL")), key=lambda x: x[0] or "")
        dec0 = _dec[-1] if _dec else None      # (date, outcome) of the latest real decision
        lede = f"{name} "
        if comps:
            lede += f"is a {esc(', '.join(comps[:2]))} program"
            if inds:
                lede += f" in {esc(inds[0])}"
            lede += ". "
        elif inds:
            lede += f"is in development for {esc(inds[0])}. "
        # THE ANSWER SENTENCE (2026-08-29 console read). Nine of sixteen AI grounding queries
        # are literally "{drug} pdufa date", and the pages answering them never contained
        # that phrase -- the lede said "its next catalyst is a PDUFA on ...", which a reader
        # parses and an extractor may not. The one page at 100% citation share resolves the
        # query in one clause. So: when the fact is a PDUFA date, say "PDUFA date", with the
        # date in the same sentence. Same fact, extractable phrasing.
        if up:
            n = up[0]
            if str(n.get("st") or "").lower() == "under review":
                lede += ("It is under FDA review; the agency's action date has not been "
                         "publicly disclosed. ")
            elif str(n.get("type") or "").upper() == "PDUFA":
                lede += (f"Its PDUFA date is "
                         f"<b>{esc(pretty(n['d'], n.get('dp') or 'day'))}</b>, the FDA's "
                         f"goal date to complete review of the application. ")
            else:
                lede += (f"Its next catalyst is a {esc(str(n.get('type') or 'catalyst'))} "
                         f"{'on' if (n.get('dp') or 'day') == 'day' else 'in'} "
                         f"{esc(pretty(n['d'], n.get('dp') or 'day'))}. ")
        elif dec0 is not None:
            # No upcoming event: lead with the decision itself, dated, in one sentence.
            lede += (f"The FDA {'approved it' if dec0[1] == 'Approved' else 'issued a Complete Response Letter'} "
                     f"on <b>{esc(pretty(dec0[0]))}</b>. ")
        if n_dec:
            lede += f"{n_dec} FDA decision{'s' if n_dec != 1 else ''} on record below. "
        lede += "Every date links its source."

        hubs = " &middot; ".join(
            f'<a class="lit" href="/ticker/{esc(t)}">{esc(t)} catalyst hub</a>' for t in tks
            if os.path.isdir(os.path.join(SITE, "ticker", t)))

        # ABOUT: only fields we actually hold. The audit's ask was 400-600 words; the ceiling on
        # honest length is the data, so every sentence below is a held fact and none is filler.
        about = []
        if d.get("marketed_as"):
            bn, bslug = d["marketed_as"]
            about.append(f'{name} is marketed as <a class="lit" href="/drug/{esc(bslug)}">'
                         f"{esc(bn)}</a>; the events below include those tracked under the "
                         f"brand name.")
        if inds:
            about.append(f"Indication{'s' if len(inds) > 1 else ''} under review: "
                         + "; ".join(esc(i) for i in inds[:3]) + ".")
        if comps:
            about.append(f"Sponsor: {esc(', '.join(comps[:2]))}"
                         + (f" ({esc(', '.join(tks))})" if tks else "") + ".")
        revs = [str((r.get("_d") or {}).get("review") or "") for r in rs
                if (r.get("_d") or {}).get("review")]
        if revs:
            about.append(f"Review status: {esc(revs[-1])}")
        # COMMON MISSPELLING (2026-08-24). "daraonrasib" -- the x dropped -- drives 47 Bing
        # impressions at position 7.26 with zero clicks and 14 AI citations at 8.43% share, and
        # the string appeared NOWHERE on the page that should own it, so neither an engine nor a
        # reader could confirm they had landed in the right place. Stated as a variant spelling of
        # one molecule, which is what it is; a separate page under the misspelling would be a thin
        # duplicate.
        alt = next((str((r.get("_d") or {}).get("also_searched") or "") for r in rs
                    if (r.get("_d") or {}).get("also_searched")), "")
        if alt:
            note = next((str((r.get("_d") or {}).get("also_searched_note") or "") for r in rs
                         if (r.get("_d") or {}).get("also_searched_note")), "")
            about.append(f"Also searched as <b>{esc(alt)}</b>. {esc(note)}")
        caps = sorted({str(r.get("cap") or "") for r in rs if r.get("cap")})
        if caps:
            about.append(f"Market-cap tier at the time we tracked it: {esc(caps[0])}.")
        n_up = len(up)
        about.append(
            f"We track {len(events)} catalyst event{'s' if len(events) != 1 else ''} for this "
            f"program: {n_up} upcoming and {len(events) - n_up} in the record. A PDUFA date is "
            f"the FDA's target date to complete review of a marketing application; a readout is "
            f"the sponsor's expected date for clinical trial results. "
            f'<a class="lit" href="/learn/what-is-a-pdufa-date">What a PDUFA date is</a> &middot; '
            f'<a class="lit" href="/learn/why-cross-trial-comparisons-mislead">why we do not '
            f"compare trial results across drugs</a>.")

        # FAQ: two questions, answered from the same rows the table shows, emitted as FAQPage
        # schema because drug-name queries are exactly where the AI-citation baseline (8) grows.
        q1 = f"When is {name}'s next FDA decision or readout?"
        if up:
            n0 = up[0]
            if str(n0.get("st") or "").lower() == "under review":
                a1 = (f"{name} is under FDA review, but no action date has been publicly "
                      f"disclosed"
                      + (f" ({n0['when_text']})" if n0.get("when_text") else "")
                      + ". The review status row below links the sponsor's own announcement; "
                        "this page updates when a date becomes public.")
            elif str(n0.get("type") or "").upper() == "PDUFA":
                a1 = (f"{name}'s PDUFA date is {pretty(n0['d'], n0.get('dp') or 'day')}. "
                      f"That is the FDA's goal date to complete review of the application; "
                      f"the agency can act earlier or extend it.")
            else:
                a1 = (f"The next tracked catalyst for {name} is a {n0.get('type', 'catalyst')} "
                      f"{'on' if (n0.get('dp') or 'day') == 'day' else 'in'} "
                      f"{pretty(n0['d'], n0.get('dp') or 'day')}.")
        else:
            just = [confirmed[r["id"]] for r in rs if r.get("id") in confirmed]
            if just:
                j = max(just, key=lambda c: c.get("reported_date") or "")
                a1 = (f"{name}'s most recent tracked catalyst has already reported: "
                      f"{j.get('outcome', 'results')} data on {pretty(j['reported_date'])}, "
                      f"per the company's own release (linked in the history below). No further "
                      f"catalyst is on our calendar yet.")
            else:
                a1 = (f"No upcoming catalyst is on our calendar for {name}; "
                      f"{n_dec if n_dec else 'no'} FDA decision"
                      f"{'s are' if n_dec != 1 else ' is'} on record below.")
        dec_rows = [r for r in rs if arch.get((str(r.get('t') or '').upper(), r.get('d') or ''))
                    in ("Approved", "CRL")]
        q2 = f"What happened at {name}'s most recent FDA decision?"
        if dec_rows:
            last = max(dec_rows, key=lambda r: r.get("d") or "")
            oc = arch.get((str(last.get('t') or '').upper(), last['d']))
            a2 = (f"On {pretty(last['d'])} the FDA "
                  + ("approved the application" if oc == "Approved"
                     else "issued a Complete Response Letter") +
                  f". The decision page carries the source document and the measured share-price "
                  f"reaction.")
        else:
            a2 = f"No FDA decision for {name} is in our archive yet."
        # 2026-08-12 audit: 2 Q&A per page = ~620 answerable queries across the index; 5-6 makes
        # it 1,800+ with zero new pages. Each extra question exists ONLY when we hold the fact --
        # a skipped question is honest, an empty answer is not.
        qa = [(q1, a1), (q2, a2)]
        if inds:
            qa.append((f"What is {name} used for?",
                       f"In our records {name} is under review or in development for "
                       + "; ".join(inds[:2]) + "."))
        if comps:
            qa.append((f"Who makes {name}?",
                       f"{', '.join(comps[:2])}"
                       + (f" ({', '.join(tks)})" if tks else "") + "."))
        if dec_rows:
            appr = [r for r in dec_rows
                    if arch.get((str(r.get('t') or '').upper(), r['d'])) == "Approved"]
            if appr:
                ad = max(appr, key=lambda r: r.get("d") or "")
                a5 = (f"Yes. The FDA approved an application for {name} on "
                      f"{pretty(ad['d'])}; the decision page linked above carries the source.")
            else:
                cd = max(dec_rows, key=lambda r: r.get("d") or "")
                a5 = (f"Not in our records. The FDA issued a Complete Response Letter on "
                      f"{pretty(cd['d'])}"
                      + (f"; the next tracked catalyst is "
                         f"{pretty(up[0]['d'], up[0].get('dp') or 'day')}." if up else "."))
            qa.append((f"Has {name} been approved by the FDA?", a5))
        qa.append(("Where does this data come from?",
                   "FDA announcements, sponsor press releases and SEC filings; every date on "
                   "this page links its source."))
        faq_html = "<h2>Questions</h2>" + "".join(
            f"<h3 style='font-size:15px;margin:14px 0 4px'>{esc(q)}</h3>"
            f"<p style='color:var(--mut2)'>{esc(a)}</p>" for q, a in qa)
        faq_ld = ('<script type="application/ld+json">' + json.dumps(
            {"@context": "https://schema.org", "@type": "FAQPage",
             "url": f"{BASE}/drug/{slug}",
             "mainEntity": [
                 {"@type": "Question", "name": q, "acceptedAnswer":
                     {"@type": "Answer", "text": re.sub(r"<[^>]+>", "", a)}}
                 for q, a in qa]},
            separators=(",", ":")) + "</script>")

        # /calendar carries 47% of Bing impressions at position 5.04 and the 08-29 ranking
        # map's finding is that almost nothing links it with descriptive anchor text -- the
        # nav word "Calendar" is boilerplate. One dated, descriptive anchor from every drug
        # page is the cheapest honest signal we can send it.
        cal_link = ('<p><a class="lit" href="/calendar">All upcoming FDA decision dates on '
                    'the 2026 PDUFA calendar</a></p>')
        body = (f'<p style="color:var(--mut2);max-width:72ch">{lede}</p>'
                + (f"<p>{hubs}</p>" if hubs else "")
                + cal_link
                + "<h2>About this program</h2>"
                + f'<p style="max-width:72ch">{" ".join(about)}</p>'
                + "<h2>Catalyst history</h2>" + "".join(events)
                + faq_html + faq_ld)

        title = f"{name}: FDA Decision Dates &amp; Catalyst History | pdufa.bio"
        if len(html.unescape(title)) > 100:
            title = f"{name} FDA Catalysts | pdufa.bio"
        # Clause-fitting, not slicing: desc[:158] cut two long drug names mid-word on the first
        # run ("...links its primary sourc"), which is the exact defect test_meta_lengths exists
        # to block. Clauses are dropped whole, never cut.
        desc = f"{name}: FDA catalyst dates and outcomes."
        for extra in ((f" For {', '.join(comps[:1])}." if comps else ""),
                      " Every date and decision links its primary source.",
                      " Facts only."):
            if extra and len(desc) + len(extra) <= 158:
                desc += extra

        page = SHELL.format(title=esc(html.unescape(title)), desc=esc(desc),
                            canon=f"{BASE}/drug/{slug}", h1=esc(name), body=body)
        if not a.dry_run:
            os.makedirs(os.path.join(OUT, slug), exist_ok=True)
            open(os.path.join(OUT, slug, "index.html"), "w", encoding="utf-8").write(page)
        written += 1
        index_items.append((name, slug, len(events)))

    # the index page: the crawl path in
    items = "".join(
        f'<a class="row" href="/drug/{esc(s)}"><span class="t">{esc(n)}</span>'
        f'<span class="d">{c} event{"s" if c != 1 else ""}</span></a>'
        for n, s, c in sorted(index_items, key=lambda x: x[0].lower()))
    idx_lede = (f"This page lists {written} drugs with an FDA decision date or clinical readout "
                f"we track, each with its full catalyst history and sourced outcomes.")
    idx = SHELL.format(
        title="FDA Drug Decision Index: Every Drug We Track | pdufa.bio",
        desc=esc(idx_lede[:158]),
        canon=f"{BASE}/drug", h1="Drugs we track",
        body=f'<p style="color:var(--mut2);max-width:72ch">{esc(idx_lede)}</p>' + items)
    if not a.dry_run:
        open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(idx)

    # ALIAS REDIRECTS: people search the generic name ("arimoclomol"), the page lives under the
    # brand ("miplyffa"). A 301 is honest routing, not a claim, and it consolidates authority on
    # one URL instead of splitting it. Managed as a deterministic block: every /drug/* redirect in
    # vercel.json is replaced wholesale by this computed, sorted set, so reruns cannot accumulate
    # strays and a drug that vanishes takes its alias with it.
    aliases = {}
    for slug, d in sorted(drugs.items()):
        m = re.search(r"\(([a-z][a-z0-9 -]{5,40})\)", d["name"])
        if not m:
            continue
        gslug = slugify(m.group(1))
        if gslug and gslug != slug and gslug not in drugs:
            aliases.setdefault(gslug, slug)
    vj = os.path.join(SITE, "vercel.json")
    if os.path.exists(vj) and not a.dry_run:
        cfg = json.load(open(vj, encoding="utf-8"))
        rd = [r for r in cfg.get("redirects", [])
              if not str(r.get("source", "")).startswith("/drug/")]
        for g, s in sorted(aliases.items()):
            rd.append({"source": f"/drug/{g}", "destination": f"/drug/{s}", "permanent": True})
        cfg["redirects"] = rd
        json.dump(cfg, open(vj, "w", encoding="utf-8"), indent=1)
    print(f"generic-name aliases: {len(aliases)} redirect(s) (e.g. "
          + ", ".join(f"/drug/{g}->{s}" for g, s in list(sorted(aliases.items()))[:3]) + ")")

    print(f"drug pages written: {written} (+ index)")
    print(f"rejected as not-a-drug-name: {len(rejected)}")
    for r in rejected[:8]:
        print(f"   {r!r}")
    if a.dry_run:
        print("DRY RUN -- nothing written.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
