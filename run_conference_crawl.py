#!/usr/bin/env python3
"""
Conference-only crawl. Runs JUST the ConferencePresentation pass — much faster than the
full catalyst_crawler, which also does PDUFA/CRL/readout/dilution work you don't need
when you're only deepening the conference study.

    python run_conference_crawl.py                       # default universe (conf_study/tickers.txt)
    python run_conference_crawl.py --tickers my.txt
    python run_conference_crawl.py --since 2025-11-01    # backfill window
    python run_conference_crawl.py --max-docs 1200       # dig deeper (slower)

Writes/append-dedupes:  catalysts_out/conference_presentations_history.csv
"""
import os, sys, argparse, datetime as dt
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path: sys.path.insert(0, HERE)

import csv as _csv

def sanitize_for_csv(df, text_cols=('snippet', 'title', 'company', 'indication', 'drug')):
    """A raw press-release snippet WILL contain a double-quote. Written unescaped it breaks the
    CSV from that row to EOF — pandas dies with "EOF inside string starting at row 225" and the
    file becomes unreadable for every downstream consumer. Normalise the text, then QUOTE_ALL."""
    df = df.copy()
    for c in text_cols:
        if c in df.columns:
            df[c] = (df[c].astype(str)
                     .str.replace(r'[\r\n\t]+', ' ', regex=True)   # newlines break rows
                     .str.replace('"', "'", regex=False)             # kill the quote entirely
                     .str.replace(r'\s+', ' ', regex=True)
                     .str.strip())
    return df

def write_csv_verified(df, path):
    """Write, then READ IT BACK with a strict parser and assert the row count round-trips.
    A file that cannot be re-read is not a file. This is the CI guard the audit asked for."""
    df = sanitize_for_csv(df)
    df.to_csv(path, index=False, quoting=_csv.QUOTE_ALL)
    back = pd.read_csv(path)                                   # strict: will raise if malformed
    if len(back) != len(df):
        raise RuntimeError(f'CSV ROUND-TRIP FAILED: wrote {len(df)} rows, read back {len(back)}. '
                           f'{path} is corrupt — refusing to declare success.')
    with open(path, newline='', encoding='utf-8') as f:
        rows = list(_csv.reader(f))
    hdr = len(rows[0])
    ragged = [i for i, r in enumerate(rows) if len(r) != hdr]
    if ragged:
        raise RuntimeError(f'CSV has {len(ragged)} ragged rows (first at {ragged[0]}), header={hdr} fields.')
    print(f'  csv round-trip verified: {len(back)} rows, {hdr} fields, 0 ragged')
    return back


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tickers", default=os.path.join(HERE, "conf_study", "tickers.txt"))
    ap.add_argument("--out",     default=os.path.join(HERE, "catalysts_out"))
    ap.add_argument("--since",   default="2024-01-01")
    ap.add_argument("--ua",      default="pdufa.bio catalyst research contact@pdufa.bio")
    ap.add_argument("--max-docs", dest="max_docs", type=int, default=900)
    ap.add_argument("--rebuild", action="store_true",
                    help="Re-derive the history file from scratch instead of appending. USE THIS whenever "
                         "the extractor's semantics change: a fix that changes a row's DATE produces a new "
                         "dedupe key, so an append would keep the old (wrong) row AND add the corrected one.")
    args = ap.parse_args()

    # deferred import: catalyst_crawler imports THIS package's sibling module, so importing
    # it at module scope would risk a cycle.
    import catalyst_crawler as CC
    import conference_presentations as CP

    named = [p for p in CP.SEARCH_PHRASES if not p.startswith(("late-", "oral", "poster"))]
    print(f"conference crawl · {len(named)} named conference searches · {len(CP.ALIASES)} aliases "
          f"· {len(CP.load_registry())} registry conferences")
    print("mode: REBUILD (file re-derived from scratch)" if args.rebuild else "mode: APPEND (dedupe onto existing file)")
    if hasattr(CP, "prospectivity"):
        print("extractor: prospectivity gate ACTIVE — a past-tense mention can no longer become a future catalyst")
    else:
        print("WARNING: extractor has NO prospectivity gate — it can fabricate future events. Update it.")

    if not os.path.exists(args.tickers):
        sys.exit(f"ERROR: ticker file not found: {args.tickers}\n"
                 f"       pass --tickers <file>, one symbol per line.")
    tickers = [l.strip().upper() for l in open(args.tickers) if l.strip() and not l.startswith("#")]
    print(f"universe: {len(tickers)} tickers  <- {args.tickers}")

    print("resolving SEC CIKs ...")
    t2c, _ = CC.sec_cik_map(args.ua)
    c2t = {v: k for k, v in t2c.items()}
    cik_set = {t2c[t] for t in tickers if t in t2c}
    print(f"  {len(cik_set)}/{len(tickers)} tickers resolved to CIKs")
    if not cik_set:
        sys.exit("ERROR: empty CIK set — nothing to crawl. (This is the silent-no-op trap.)")

    print(f"searching EDGAR full-text since {args.since} (max_docs={args.max_docs}) ...")
    rows = CC.sec_conference_presentations(cik_set, args.ua, args.since,
                                           max_docs=args.max_docs, include_past=True)
    if not rows:
        print("no conference presentations found. Try a wider --since or a bigger --max-docs.")
        return
    for r in rows:                       # the cik->ticker fill lives in catalyst_crawler.main()
        r["ticker"] = c2t.get(r.get("cik"), "") or r.get("ticker", "")
        r["extractor_version"] = getattr(CP, "EXTRACTOR_VERSION", 1)

    os.makedirs(args.out, exist_ok=True)
    path = os.path.join(args.out, "conference_presentations_history.csv")
    new = pd.DataFrame(rows)

    # ---- merge: append + dedupe, with a guard that this can never SHRINK the file ----
    # The old key was (ticker, conference, catalyst_date, drug). `drug` is 100% null in this
    # feed and `ticker` was blank in pre-fix files -- and pandas treats NaN == NaN in
    # drop_duplicates, so two null key columns silently collapsed 229 rows to 58.
    # Dedupe on source_url (genuinely per-filing) and refuse to write a smaller file.
    # ---- HARD GUARD: never append across an extractor-semantics change --------------------
    # This is the failure that bit us: the extractor was fixed so that a past-tense mention no
    # longer becomes a future catalyst. That fix CHANGES A ROW'S DATE, which changes its dedupe
    # key -- so an append kept the old wrong row AND added the corrected one. Both, side by side.
    # A version mismatch is not a warning. It is a refusal.
    cur_ver = getattr(CP, "EXTRACTOR_VERSION", 1)
    if os.path.exists(path) and not args.rebuild:
        prev = pd.read_csv(path)
        file_ver = int(prev["extractor_version"].dropna().max()) if "extractor_version" in prev.columns and prev["extractor_version"].notna().any() else 1
        if file_ver != cur_ver:
            sys.exit(
                f"\nREFUSING TO APPEND.\n"
                f"  file was built by extractor v{file_ver}; this is extractor v{cur_ver}.\n"
                f"  The rules changed, so the same filing can now produce a DIFFERENT date --\n"
                f"  which is a different dedupe key. Appending would keep the old wrong rows\n"
                f"  AND add the corrected ones. You would hold both.\n\n"
                f"  Re-run with --rebuild (menu option [1]).\n")

    if args.rebuild and os.path.exists(path):
        stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        keep = path.replace(".csv", f".pre_rebuild_{stamp}.csv")
        pd.read_csv(path).to_csv(keep, index=False)
        print(f"REBUILD: existing file archived -> {os.path.basename(keep)}")
        old = pd.DataFrame()
    else:
        old = pd.read_csv(path) if os.path.exists(path) else pd.DataFrame()
    before = len(old)
    merged = pd.concat([old, new], ignore_index=True) if before else new

    KEY = [c for c in ("source_url", "conference", "catalyst_date") if c in merged.columns]
    for c in KEY:                                  # never let NaN act as a matchable value
        merged[c] = merged[c].astype(str).fillna("").str.strip()
    nullish = [c for c in KEY if (merged[c].isin(["", "nan", "None"])).mean() > 0.5]
    if nullish:
        sys.exit(f"ABORT: dedupe key columns {nullish} are >50% empty — refusing to dedupe on "
                 f"a key that would collapse distinct rows. Nothing written.")
    merged = merged.drop_duplicates(subset=KEY, keep="first")

    if len(merged) < before and not args.rebuild:
        sys.exit(f"ABORT: merge would shrink the file ({before} -> {len(merged)}). "
                 f"That is data loss, not dedupe. Nothing written. "
                 f"(If you changed the extractor and WANT a clean re-derive, pass --rebuild.)")

    if before:                                     # keep a rollback copy
        pd.read_csv(path).to_csv(path + ".bak", index=False)
    write_csv_verified(merged, path)

    added = len(merged) - before
    print(f"\n{len(rows)} rows scraped · file {before} -> {len(merged)} (+{added} new, deduped on {KEY})")
    print(f"  -> {path}")
    if before: print(f"  rollback copy -> {path}.bak")
    if "conference" in merged.columns:
        print("\nby conference:")
        for c, n in merged.conference.value_counts().items():
            print(f"    {c:12s} {n:4d}")
    if "ticker" in merged.columns:
        miss = int((merged.ticker.astype(str).str.strip().isin(["", "nan"])).sum())
        print(f"\nrows missing ticker: {miss}  (should be 0)")

if __name__ == "__main__":
    main()
