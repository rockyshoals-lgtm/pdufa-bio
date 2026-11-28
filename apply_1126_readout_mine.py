# -*- coding: utf-8 -*-
"""apply_1126_readout_mine.py -- more exact, newer and new sourced readout dates, red-teamed 2026-11-26.

David 2026-11-26: "continue to increase our moat, find more CRLs, mine for more detailed phase readout dates".
Same rules and actions as apply_1125_readout_mine.py, plus: status "tighten" (the company now states a more exact
window) is applied like "moved"; "stopped" (program or trial discontinued by the company) is applied like
"guidance_dropped"; a "new" record may name the registry estimate it supersedes (supersedes_id), which then leaves
the estimated table so the readout is listed once, with the company's own timing. The dataset is edited row by row
in place (text spans), never re-serialised, so the diff holds only the rows that changed.

Input: odin_cowork_dropbox/2026-11-26_readout_mine.json. Every record there was collected from the
company's own words (its press release on a newswire / IR site, or its SEC filing) and then re-opened by an
independent red-team pass that checked the quote, the program, the timing words and the source date. Only
records with rt_verdict CONFIRMED or FIX are applied (FIX = corrected field values read from the page). Every
DROP and NOT_CHECKED record is listed in the dropbox note and touches nothing.

What it does, per record:
  existing Guided row, status reported      -> st=Reported on the day of the company's release, review = the
                                               release headline verbatim; readout_reported_manual.json entry.
                                               No outcome is inferred (outcome "reported").
  existing Guided row, still_guided/moved   -> re-sourced to the company's NEWEST statement; window, precision,
                                               quote and link refreshed; a date_history entry when the date moves.
  existing Guided row, guidance_dropped     -> window passed: resolution no_topline (dated, with what was read)
                                               plus an ack. Window ahead: the row leaves the guided list (the
                                               company acquired, the trial ended, or the "readout" was never
                                               one); the reason and source are in the dropbox note.
  new                                       -> a new Guided row, unless the site already holds the same ticker
                                               + program + window.
Windows are kept exactly as the company gave them. Half-year and looser wording publishes at YEAR precision
(the schema has no half) with the company's own words in _d.guided_label, which /readouts prints.
Idempotent. Facts only, not investment advice. RULE 1: every date here is a calendar date as printed by the
company; "today" is the Eastern date.

    python apply_1125_readout_mine.py [--dry-run]
"""
import argparse
import collections
import datetime as dt
import io
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from site_dates import eastern_today  # noqa: E402
from text_hygiene import join_phrases  # noqa: E402

DATASET = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")
MANUAL = os.path.join(HERE, "readout_reported_manual.json")
ACK = os.path.join(HERE, "_readout_watch_ack.json")
MINE = os.path.join(HERE, "odin_cowork_dropbox", os.environ.get("READOUT_MINE_FILE", "2026-11-26_readout_mine.json"))
MINED_ON = "2026-11-26"
TODAY = eastern_today().isoformat()
NOW = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
USE = {"CONFIRMED", "FIX"}
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
# Records that are mis-extractions in the site's earlier guided set (the "readout" was a trial start or a
# preclinical item). They are removed from the guided list rather than marked withdrawn: the company never
# guided a readout, so "withdrawn" would misstate it. Filled from the input's own notes below.
NOT_A_READOUT_HINTS = ("trial start", "not a clinical readout", "preclinical", "phase 2 start", "initiation",
                       "not really clinical readouts", "was a trial start", "ind ")


def eff(rec):
    """The record with the red team's corrections applied."""
    r = dict(rec)
    for k, v in (rec.get("rt_fix") or {}).items():
        if k in r or k in ("quote", "timing_stated", "precision", "window_start", "window_end", "drug",
                            "indication", "trial", "readout", "source_date", "source_url", "reported_date",
                            "date_quote"):
            r[k] = v
    if r.get("status") == "reported" and r.get("reported_url"):
        r["source_url"] = r["reported_url"]
    if r.get("status") in ("moved", "tighten"):
        r["status"] = "window_moved"
    if r.get("status") == "stopped":
        r["status"] = "guidance_dropped"
        r["was_stopped"] = True  # 2026-11-27: a passed window the company STOPPED is not "no topline" (see below)
    return r


def site_window(r):
    """(d, dp, dm, guided_precision, guided_window) from the record's mechanical window."""
    p = str(r.get("precision") or "").lower()
    ws, we = str(r.get("window_start") or "")[:10], str(r.get("window_end") or "")[:10]
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", we):
        return None
    y = we[:4]
    if p == "day":
        return we, "day", None, "day", we
    if p == "month":
        return we, "month", we[:7], "month", we[:7]
    if p == "quarter":
        return we, "quarter", we[:7], "quarter", f"{y}-Q{(int(we[5:7]) - 1) // 3 + 1}"
    if p == "half":
        return we, "year", None, "half", f"{y}-H{1 if we[5:7] <= '06' else 2}"
    if p == "window" and ws[:7] == we[:7]:
        return we, "month", we[:7], "window", f"{ws}..{we}"
    if p == "window":
        return we, "year", None, "window", f"{ws}..{we}"
    return we, "year", None, "year", y


def short(s, n):
    s = re.sub(r"\s+", " ", str(s or "")).strip()
    return s if len(s) <= n else s[: n - 1].rsplit(" ", 1)[0] + "…"


def row_name(r):
    drug = str(r.get("drug") or "").strip()
    trial = str(r.get("trial") or "").strip()
    rd = str(r.get("readout") or "").strip()
    parts = [drug]
    if trial and trial.lower() not in drug.lower():
        # 2026-11-27: "divesiran SANRECO Phase 2" made build_drug_pages publish /drug/divesiran-sanreco (its core
        # keeps two words) and drop /drug/divesiran, which /ticker/SLN linked: the rebuild's dead-link guard
        # blocked. The phase goes right after the drug ("divesiran Phase 2 SANRECO"); with no phase, a comma
        # ends the drug's name ("STX-1150, first-in-human study").
        m = re.search(r"\bPhase\s*[0-9IV][0-9IVab/]*\b", trial)
        if m and m.start() > 0:
            trial = re.sub(r"\s+", " ", f"{m.group(0)} {trial[:m.start()]} {trial[m.end():]}")
            trial = re.sub(r"\(\s*\)", "", re.sub(r"\(\s*,\s*", "(", re.sub(r"\s*,\s*\)", ")", trial)))
            trial = re.sub(r"\s+", " ", trial).strip(" ,")
            # the readout often repeats the phase ("Phase 2 results"): keep it once
            if rd.lower().startswith(m.group(0).lower()):
                rd = rd[len(m.group(0)):].strip() or rd
        elif not m:
            parts[0] = drug + ","
        parts.append(trial)
    if rd and rd.lower() not in " ".join(parts).lower():
        parts.append(rd)
    # 2026-11-20: "TP-04" + "Kore Phase 2" + "Phase 2 topline" was written "TP-04 Kore Phase 2 Phase 2 topline" (60
    # rows). join_phrases writes a phrase shared at a seam once. Guard: tests/test_no_repeated_phrases.py.
    return short(join_phrases(p for p in parts if p), 90)


def prog_token(s):
    s = re.sub(r"\([^)]*\)", " ", str(s or "")).strip(" -").lower()
    return re.sub(r"[^a-z0-9]", "", s.split()[0]) if s.split() else ""


def prog_names(s):
    """Every name a drug goes by in one row: the first word, the first word in each parenthesis, and the first
    word of each drug in a combination. Self-heal (2026-11-27): the mine keyed duplicates on prog_token alone, so
    "tambiciclib (SLS009)" did not match "SLS009 (tambiciclib)", nor "resmetirom (Rezdiffra)" match
    "Rezdiffra (resmetirom)", and four readouts went up twice. tests/test_readout_no_duplicates.py guards it."""
    s = str(s or "").lower()
    out = {prog_token(s)}
    for inner in re.findall(r"\(([^)]*)\)", s):
        if inner.split():
            out.add(re.sub(r"[^a-z0-9]", "", inner.split()[0]))
    for part in re.split(r"\s*(?:\+|/|\bplus\b|\bwith\b|,)\s*", re.sub(r"\([^)]*\)", " ", s)):
        if part.split():
            out.add(re.sub(r"[^a-z0-9]", "", part.split()[0]))
    return {w for w in out if len(w) >= 4 and w not in _GENERIC_NAMES}


_GENERIC_NAMES = {"sirna", "oral", "antibody", "partnered", "subcutaneous", "intravenous", "monotherapy",
                  "combination", "inhaled", "topical", "vaccine", "program", "phase", "formerly", "standard",
                  "placebo", "dexamethasone", "azacitidine", "venetoclax", "rituximab", "pembrolizumab",
                  "chemotherapy"}


def source_label(url):
    return "company guidance (SEC filing)" if "sec.gov" in str(url or "") else "company guidance (company release)"


def hist_add(dd, rid, new_d, why):
    hist = dd.get("date_history") or []
    if not hist:
        m = re.search(r"(\d{4}-\d{2}-\d{2})", rid)
        hist.append({"date": m.group(1) if m else new_d, "note": "date the row was keyed on when created"})
    hist.append({"date": new_d, "changed": TODAY, "why": why})
    dd["date_history"] = hist


def site_label(r, w):
    """The company's own timing words for /readouts, with relative words ("next year") made absolute
    and lead-in clauses dropped, so the label still reads right after the year turns."""
    t = re.sub(r"\s+", " ", str(r.get("timing_stated") or "")).strip()
    t = re.sub(r"^(either sequentially or together,?\s*|plans to share data from this study in\s*)", "", t,
               flags=re.I)
    y = w[0][:4]
    t = re.sub(r"\b(next|this) year\b", y, t, flags=re.I)
    return short(t, 60)


def guidance_fields(r, w):
    d, dp, dm, gp, gw = w
    return {"guided_precision": gp, "guided_window": gw, "guided_label": site_label(r, w),
            "guided_form": r.get("source_type"), "guided_filed": r.get("source_date"),
            "guidance_text": short(r.get("quote"), 600), "source_url": r.get("source_url"),
            "source": source_label(r.get("source_url")),
            "readout_described": short(r.get("readout"), 120),
            **({"date_quote": short(r.get("date_quote"), 200)} if r.get("date_quote") else {}),
            "red_team": f"{MINED_ON}: source re-opened by an independent red-team pass; quote, program, timing and "
                        f"date checked. {short(r.get('rt_reason'), 300)}"}


def _row_text(row):
    return "\n".join(" " + ln for ln in json.dumps(row, indent=1, ensure_ascii=False).split("\n"))


def splice(src, rows, orig_ids, remove):
    """Rewrite only the rows that changed, by their text span; drop removed rows; append new rows before the
    closing bracket. Unchanged rows keep their bytes, so the diff is the change and nothing else."""
    dec = json.JSONDecoder()
    spans, k = [], src.index("[") + 1
    while True:
        m = re.compile(r"\s*\{").match(src, k)
        if not m:
            break
        st = m.end() - 1
        obj, end = dec.raw_decode(src, st)
        spans.append((st, end, obj))
        c = re.compile(r"\s*,").match(src, end)
        if not c:
            break
        k = c.end()
    assert [o["id"] for _, _, o in spans] == orig_ids, "dataset row order changed under the splice"
    by = {r["id"]: r for r in rows}
    out, pos, first = [], 0, True
    head = src[:spans[0][0]]
    body = []
    for st, end, obj in spans:
        if obj["id"] in remove:
            continue
        new = by[obj["id"]]
        body.append(src[st:end] if new == obj else _row_text(new).lstrip())
    seen = {o["id"] for _, _, o in spans}
    for r in rows:
        if r["id"] not in seen and r["id"] not in remove:
            body.append(_row_text(r).lstrip())
    tail = src[spans[-1][1]:]
    out = head + ",\n ".join(body) + tail
    json.loads(out[out.index("["):out.rindex("]") + 1])
    return out


def publish_gate(orig_rows, new_rows, recs):
    """Self-heal guard (2026-11-27). Two rebuilds were blocked by rows this script wrote:
    a company named "X (TICKER)" printed the ticker twice (test_no_repeated_phrases), and a name
    starting "drug TRIAL ..." moved /drug/<drug> to /drug/<drug-trial> and left a dead link
    (test_internal_links_resolve). Refuse to write either, so the CI guards never see them."""
    import build_drug_pages as bdp
    probs = []
    for r in new_rows:
        t = str(r.get("t") or "")
        if t and re.search(r"\(\s*" + re.escape(t) + r"\s*\)", str(r.get("company") or "")):
            probs.append(f"{r['id']}: company carries its own ticker: {r.get('company')!r}")

    def slugs(rows):
        out = {}
        for r in rows:
            n = bdp.clean_name(r.get("name"))
            if not n:
                continue
            sl = bdp.slugify(re.split(r"\s*\(", n)[0])
            if sl and not bdp.JUNK_SLUG.search(sl):
                out.setdefault(sl, r["id"])
        return out

    before, after = slugs(orig_rows), slugs(new_rows)
    known = set()
    for fn, key in (("_drug_pages_retired.json", "pages"), ("_drug_slug_folds.json", "folds")):
        try:
            known |= set(json.load(io.open(os.path.join(HERE, fn), encoding="utf-8")).get(key, {}))
        except Exception:
            pass
    for sl in sorted(set(before) - set(after) - known):
        probs.append(f"/drug/{sl} would stop being built (was from {before[sl]}): rename the row so the drug "
                     f"name comes first, or add a redirect to _drug_pages_retired.json / _drug_slug_folds.json")
    words = set()
    for x in recs:
        drug = str(x.get("drug") or "").lower()
        for w in re.findall(r"[A-Z][A-Z0-9-]{3,}", str(x.get("trial") or "")):
            if w.lower() not in drug:  # "UBT251 (obesity)": a drug code in the trial field is still the drug
                words.add(w.lower())
    words -= {"phase", "part", "study", "trial"}
    for sl in sorted(set(after) - set(before)):
        if any(w in sl.split("-") for w in words):
            probs.append(f"/drug/{sl} (from {after[sl]}) is named for a trial, not a drug")
    return probs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    recs = json.load(io.open(MINE, encoding="utf-8"))["rows"]
    src = io.open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
    i, j = src.index("["), src.rindex("]") + 1
    rows = json.loads(src[i:j])
    orig_ids = [r["id"] for r in rows]
    by = {r["id"]: r for r in rows}
    man = json.load(io.open(MANUAL, encoding="utf-8"))
    have_man = {m["id"] for m in man["reported"]}
    ack = json.load(io.open(ACK, encoding="utf-8"))
    ack_ids = {x["id"] for x in ack["acks"]}
    log = {"reported": [], "refreshed": [], "moved": [], "no_topline": [], "withdrawn": [], "removed": [],
           "added": [], "dup": [], "skipped": []}
    remove = set()

    use = [eff(x) for x in recs if x.get("rt_verdict") in USE]
    checked = []  # (row id, source url, verdict): the red team opened each source before this apply
    # ---------------------------------------------------------------- existing rows
    for r in use:
        rid = r.get("existing_row_id")
        if not rid:
            continue
        row = by.get(rid)
        if not row:
            log["skipped"].append(f"{rid}: not in dataset")
            continue
        dd = row.setdefault("_d", {})
        st = r.get("status")
        if st == "reported":
            rdate = str(r.get("reported_date") or "")[:10]
            head = short(r.get("reported_headline") or r.get("quote"), 300)
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", rdate):
                log["skipped"].append(f"{rid}: reported without a date")
                continue
            if row.get("st") != "Reported" or row.get("d") != rdate:
                old = f"{row.get('d')} ({row.get('dp')})"
                hist_add(dd, rid, rdate, f"The company's release of {rdate} reports this readout; a reported row "
                                         f"carries the day it was reported. Was {old}.")
            review = (f"{r.get('company') or row.get('company')} reported this readout on {rdate}: "
                      f"“{head}” ({r.get('source_type') or 'company release'}).")
            row.update({"st": "Reported", "d": rdate, "dp": "day", "url": r.get("source_url") or row.get("url"),
                        "ua": NOW})
            row.pop("dm", None)
            dd["review"] = review
            dd["reported_source_url"] = r.get("source_url")
            dd.pop("resolution", None)
            if r.get("drug") and not dd.get("program"):
                dd["program"] = r.get("drug")
            if rid not in have_man:
                man["reported"].append({"id": rid, "t": row["t"], "drug": dd.get("program") or row["name"],
                                        "reported_date": rdate, "outcome": "reported", "summary": review,
                                        "source_url": r.get("source_url"),
                                        "guided_window": dd.get("guided_window") or row.get("dm") or "",
                                        "note": f"readout mine {MINED_ON}, red-teamed against the company's release"})
                have_man.add(rid)
            log["reported"].append(f"{rid} -> Reported {rdate}")
        elif st in ("still_guided", "window_moved"):
            w = site_window(r)
            if (not w or w[0] < TODAY) and str(row.get("d") or "") < TODAY:
                # Window passed, the company's newest statement gives no new window and no data: say so, dated.
                note = short(r.get("notes") or r.get("rt_reason"), 240)
                dd["resolution"] = {"state": "no_topline", "checked": TODAY, "reviewed": TODAY,
                                    "searched": short(f"Company's newest statement ({r.get('source_type')} "
                                                      f"{r.get('source_date')}) read {MINED_ON}: no results for this "
                                                      f"readout. {note}", 300)}
                if rid not in ack_ids:
                    ack["acks"].append({"id": rid, "reason": f"{MINED_ON} readout check: {short(note, 240)}"})
                    ack_ids.add(rid)
                log["no_topline"].append(rid)
                continue
            if not w or w[0] < TODAY:
                log["skipped"].append(f"{rid}: window {r.get('window_end')} not ahead")
                continue
            d, dp, dm = w[0], w[1], w[2]
            moved = (row.get("d") != d or row.get("dp") != dp)
            if moved:
                old = f"{row.get('d')} ({row.get('dp')})"
                hist_add(dd, rid, d, f"Re-sourced to the company's newest statement ({r.get('source_type')} "
                                     f"{r.get('source_date')}): “{short(r.get('timing_stated'), 60)}”. Was {old}.")
            row.update({"d": d, "dp": dp, "st": "Guided", "url": r.get("source_url"), "ua": NOW,
                        "name": row_name(r) or row.get("name")})
            if dm:
                row["dm"] = dm
            else:
                row.pop("dm", None)
            dd.update(guidance_fields(r, w))
            dd["program"] = r.get("drug") or dd.get("program")
            if r.get("indication"):
                dd["indication"] = r.get("indication")
            if r.get("nct_id"):
                dd["nct_stated"] = r.get("nct_id")
            dd.pop("resolution", None)
            (log["moved"] if moved else log["refreshed"]).append(f"{rid} -> {d} ({dp}) {short(r.get('timing_stated'), 40)}")
        elif st == "retire_estimate":
            # A registry estimate the company's own record has overtaken: the trial already read out, it was
            # stopped, or the company was acquired and no longer guides. An estimate is never marked Reported
            # (it was never the company's date); it leaves the forward list.
            if row.get("st") != "Estimated":
                log["skipped"].append(f"{rid}: retire_estimate on a {row.get('st')} row")
                continue
            remove.add(rid)
            log["removed"].append(f"{rid}: estimate overtaken: {short(r.get('notes') or r.get('rt_reason'), 120)}")
        elif st == "guidance_dropped":
            note = short(r.get("notes") or r.get("rt_reason"), 300)
            if str(row.get("d") or "") < TODAY and r.get("was_stopped") and r.get("source_url") and r.get("source_date"):
                # 2026-11-27 (Aardvark ARD-101 HERO): a red-teamed "stopped" record on a passed window was written
                # as no_topline, so the site said "no topline announced" for a trial the company had terminated.
                # It is the company stopping the trial: company_stopped with the company's own date, link and words.
                # Guard: tests/test_readout_mine_stopped_applied.py.
                dd["resolution"] = {"state": "company_stopped", "date": str(r.get("source_date"))[:10],
                                    "url": r.get("source_url"), "quote": short(r.get("quote"), 300),
                                    "checked": TODAY, "reviewed": TODAY}
                log["no_topline"].append(rid)
            elif str(row.get("d") or "") < TODAY:
                dd["resolution"] = {"state": "no_topline", "checked": TODAY, "reviewed": TODAY,
                                    "searched": short(f"Company's newest release ({r.get('source_type')} "
                                                      f"{r.get('source_date')}) read {MINED_ON}: no results and no "
                                                      f"timing for this readout. {note}", 300)}
                if rid not in ack_ids:
                    ack["acks"].append({"id": rid, "reason": f"{MINED_ON} readout mine: {short(note, 240)}"})
                    ack_ids.add(rid)
                log["no_topline"].append(rid)
            elif any(h in (note or "").lower() for h in NOT_A_READOUT_HINTS):
                remove.add(rid)
                log["removed"].append(f"{rid}: {short(note, 120)}")
            else:
                # st "Withdrawn" is the FDA-application status (tests/test_no_withdrawn_upcoming.py); a readout
                # whose guidance ended simply leaves the forward list.
                remove.add(rid)
                log["removed"].append(f"{rid}: guidance ended: {short(note, 120)}")

    # ---------------------------------------------------------------- new rows
    # one spelling per company: a new row takes the name the site already uses for its ticker
    canon = {}
    for row in rows:
        canon.setdefault(row.get("t"), collections.Counter())[row.get("company")] += 1
    existing_keys = {}
    for row in rows:
        if row.get("type") == "Readout" and row.get("st") == "Guided" and row["id"] not in remove:
            for p in prog_names((row.get("_d") or {}).get("program") or row.get("name")):
                existing_keys.setdefault((row["t"], p), []).append(row)
    seen = set()
    for r in use:
        if r.get("existing_row_id") or r.get("status") != "new":
            continue
        w = site_window(r)
        if not w or w[0] < TODAY:
            log["skipped"].append(f"{r.get('ticker')} {r.get('drug')}: window not ahead")
            continue
        tk = str(r.get("ticker") or "").upper()
        d, dp, dm = w[0], w[1], w[2]
        p = prog_token(r.get("drug"))
        k = (tk, p, d, short(r.get("trial"), 30).lower(), short(r.get("readout"), 30).lower())
        if k in seen:
            log["dup"].append(f"{tk} {r.get('drug')} {d}: duplicate record")
            continue
        seen.add(k)
        same = list({e["id"]: e for q in (prog_names(r.get("drug")) | {p})
                     for e in existing_keys.get((tk, q), []) if e.get("d") == d}.values())
        # 2026-11-26: the same drug can have two readouts due the same day in different trials (Incyte's povorcitinib:
        # prurigo nodularis Phase 3 and asthma Phase 2, both "Q4 2026"). A record that names the row it was checked
        # against in "distinct_from" is not a duplicate of that row.
        same = [e for e in same if e["id"] != r.get("distinct_from")]
        if same:
            log["dup"].append(f"{tk} {r.get('drug')} {d}: already on site as {same[0]['id']}")
            sup = r.get("supersedes_id")
            if sup and sup in by and by[sup].get("st") == "Estimated" and by[sup].get("t") == tk:
                # the company's own timing for this trial is already listed: the registry estimate is a second
                # listing of the same readout, so it leaves the estimated table
                remove.add(sup)
                log["removed"].append(f"{sup}: registry estimate already listed with the company's own timing "
                                      f"({same[0]['id']})")
            continue
        rid = f"readout_{tk.lower()}_{d}"
        if rid in by:
            rid = f"{rid}-{(p or 'x')[:10]}"
        n = 2
        base = rid
        while rid in by:
            rid = f"{base}-{n}"; n += 1
        row = {"id": rid, "t": tk, "company": (canon[tk].most_common(1)[0][0] if canon.get(tk)
                                                       else re.sub(r"\s*\(\s*" + re.escape(tk) + r"\s*\)\s*$", "", r.get("company") or "") or tk), "d": d, "dp": dp, "name": row_name(r),
               "type": "Readout", "ta": "", "cap": "", "st": "Guided", "url": r.get("source_url"), "ua": NOW,
               "_d": {"nct_id": None, "indication": r.get("indication") or None, "market_cap_usd": None,
                      "program": r.get("drug"), "trial": r.get("trial")}}
        canon.setdefault(tk, collections.Counter())[row["company"]] += 1
        if dm:
            row["dm"] = dm
        row["_d"].update(guidance_fields(r, w))
        if r.get("nct_id"):
            row["_d"]["nct_stated"] = r.get("nct_id")
        row["_d"]["date_history"] = [{"date": d, "note": f"created {MINED_ON} from the company's own statement "
                                                         f"({r.get('source_type')} {r.get('source_date')})"}]
        sup = r.get("supersedes_id")
        if sup and sup in by and by[sup].get("st") == "Estimated" and by[sup].get("t") == tk:
            remove.add(sup)
            row["_d"]["supersedes_estimate"] = sup
            log["removed"].append(f"{sup}: registry estimate replaced by the company's own timing ({rid})")
        rows.append(row)
        by[rid] = row
        checked.append((rid, r.get("source_url"), r.get("rt_verdict")))
        log["added"].append(f"{rid}: {row['name']} | {short(r.get('timing_stated'), 40)}")

    rows = [x for x in rows if x["id"] not in remove]
    for k, v in log.items():
        print(f"{k}: {len(v)}")
        for x in v:
            print("   " + x)
    orig_rows = json.loads(src[i:j])
    probs = publish_gate(orig_rows, rows, use)
    if probs:
        print("REFUSED: these rows would break the site build:")
        for x in probs:
            print("   " + x)
        return 2
    if a.dry_run:
        print("dry run: nothing written")
        return 0
    io.open(DATASET, "w", encoding="utf-8", newline="").write(splice(src, rows, orig_ids, remove))
    io.open(MANUAL, "w", encoding="utf-8").write(json.dumps(man, indent=1, ensure_ascii=False))
    io.open(ACK, "w", encoding="utf-8").write(json.dumps(ack, indent=1, ensure_ascii=False))
    # Self-heal 2026-11-27 (rebuild 45940203634): two rows from batch I-L (OLMA, BCTX, Dec 11) crossed into the
    # 14-day window the morning after they were added and blocked the rebuild as "checked: never", though the red
    # team had opened both sources the day before. A row this script adds was just read against its source, so its
    # first entry in the date-check ledger is written here (tests/test_date_checks_current.py reads it).
    if checked:
        import record_date_check as rdc
        led = rdc.load()
        for rid, url, verdict in checked:
            if url and rid not in led.get("checks", {}):
                rdc.record(led, rid, "CONFIRMED", url, f"red team {verdict} before apply", by="red_team_at_apply")
        rdc.save(led)
        print(f"date checks recorded: {sum(1 for rid, _, _ in checked if led['checks'].get(rid, {}).get('by') == 'red_team_at_apply')}")
    print("written.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
