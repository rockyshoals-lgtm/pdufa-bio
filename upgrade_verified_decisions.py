# -*- coding: utf-8 -*-
"""upgrade_verified_decisions.py -- price-inferred pages become primary-sourced pages.

Consumes _decision_verification.json (written by verify_decisions.py). For every record whose
outcome now has a primary source -- a Drugs@FDA application with an action date, or an SEC
filing -- the page stops hedging and starts citing:

  - title/h1/badge say the outcome, because now we can show why
  - the 'Unverified record' banner is removed
  - the Validation row links the primary source a reader can open
  - the drug's name appears (joined from the research dataset; price-only pages never had it)
  - noindex lifts: a sourced decision page is exactly what the site exists to index

CONTRADICTIONS -- where the evidence disagrees with what the price implied -- get the evidenced
outcome plus a visible correction note. The price was wrong; the page says so. This is the class
of error the owner asked us to hunt ('sometimes that doesn't pan out'), and the false SELLAS CRL
proved.

Records with no evidence keep their honest banner untouched. Idempotent; safe to re-run as
verify_decisions.py finds more.

    python upgrade_verified_decisions.py [--dry-run]
"""
import argparse, csv, datetime as dt, html, json, os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
RES_P = os.path.join(HERE, "_decision_verification.json")
ODIN_CSV = os.path.join(HERE, "ODIN_MODEL_READY_v1071_T1_2015on_ENRICHED.csv")
TODAY = dt.datetime.now(dt.timezone.utc).date().isoformat()

BANNER_RE = re.compile(
    r'<div style="background:rgba\(240,200,106,\.09\);[^"]*">.*?Unverified record\..*?</div>',
    re.S)


def esc(s):
    return html.escape(str(s or ""), quote=True)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    res = json.load(open(RES_P, encoding="utf-8"))["results"]
    with open(ODIN_CSV, encoding="utf-8", errors="replace") as f:
        odin = {(str(r["ticker"]).upper(), str(r["catalyst_date"])[:10]): r
                for r in csv.DictReader(f)}

    upgraded = contradictions = skipped = 0
    for slug, r in sorted(res.items()):
        if r["status"] not in ("verified_approved", "verified_crl", "CONTRADICTION"):
            continue
        p = os.path.join(SITE, "fda-decision", slug, "index.html")
        if not os.path.exists(p):
            continue
        doc = open(p, encoding="utf-8", errors="replace").read()
        low = doc.lower()
        if "price-only" not in low and "outcome unverified" not in low:
            skipped += 1
            continue                       # already upgraded on a previous run
            # (case-insensitive: the pretty-format titles say 'Price-only' with a capital P,
            # and the case-sensitive first version of this check skipped exactly those pages)
        ev = r["evidence"]
        if not ev or not ev.get("source_url"):
            continue

        if r["status"] == "CONTRADICTION":
            outcome = "Approved" if ev["kind"] == "approval" else "CRL"
        else:
            outcome = "Approved" if r["status"] == "verified_approved" else "CRL"
        row = odin.get((r["ticker"], r["date"]), {})
        asset = re.sub(r"\s+", " ", str(row.get("asset") or "")).strip()
        indic = re.sub(r"\s+", " ", str(row.get("indication") or "")).strip()

        o = doc
        # titles -- TWO formats exist: the relabel-era ISO form ('2025-12-09: outcome
        # unverified') and the original pretty form ('Feb 7, 2025: Approved - Price-only'),
        # which the relabel script's regex never matched and so kept its tier suffix. Both
        # must end up as a plain outcome title, or the provenance count keeps reading the
        # page as price-inferred off its own <title>.
        doc = doc.replace(": outcome unverified |", f": {outcome} |")
        doc = re.sub(r'(content="[A-Z]+ FDA Decision \d{4}-\d{2}-\d{2}): outcome unverified',
                     rf"\1: {outcome}", doc)
        doc = doc.replace(" - Price-only |", " |")
        doc = doc.replace(" - Price-only&quot;", "&quot;")
        doc = re.sub(r"( content=\"[^\"]{0,120}) - Price-only([\"|])", r"\1\2", doc)
        # pretty-format meta descriptions carry their own 'Approved. Price-only.' sentence
        src_word = ("Verified against Drugs@FDA." if ev["kind"] == "approval"
                    else "Verified against the company's SEC filing.")
        doc = doc.replace(": Approved. Price-only.", f": Approved. {src_word}")
        doc = doc.replace(": CRL. Price-only.", f": CRL. {src_word}")
        doc = re.sub(r"\bPrice-only\.", src_word, doc)
        # h1
        doc = re.sub(r'<span class="g"[^>]*>outcome unverified</span>',
                     f'<span class="g">{outcome}</span>', doc)
        # outcome badge
        doc = doc.replace(
            '<span class="badge amb">Unconfirmed &middot; price consistent with approval</span>',
            '<span class="badge app">&#10003; Approved</span>' if outcome == "Approved"
            else '<span class="badge crl">&#10007; CRL</span>')
        doc = doc.replace(
            '<span class="badge amb">Unconfirmed &middot; price consistent with a CRL</span>',
            '<span class="badge crl">&#10007; CRL</span>' if outcome == "CRL"
            else '<span class="badge app">&#10003; Approved</span>')
        # tier badge
        doc = doc.replace('<span class="badge amb">~ price-only (validating)</span>',
                          '<span class="badge app">primary-sourced</span>')
        # banner
        doc = BANNER_RE.sub("", doc)
        # validation row -> the source, linked
        doc = doc.replace(
            "<b>Outcome consistent with price; primary-source verification in progress.</b>",
            f'<b>Verified {TODAY}: <a href="{esc(ev["source_url"])}" rel="nofollow noopener">'
            f'{esc(ev["source_label"])}</a></b>')
        # meta description
        short_src = ("Drugs@FDA" if ev["kind"] == "approval"
                     else "the company's SEC filing")
        doc = re.sub(
            r'(content="On \d{4}-\d{2}-\d{2} the FDA decision for [A-Z]+ \([^)]*\) was )'
            r"not verified against a primary source\.[^\"]*",
            lambda m: (m.group(1) + ("Approved" if outcome == "Approved"
                                     else "a Complete Response Letter")
                       + f". Verified against {short_src}; source linked on the page.\""),
            doc)
        # drug + indication rows, once, after the decision-date row
        if asset and "<span>Drug</span>" not in doc:
            ins = f'<div class="kv"><span>Drug</span><b>{esc(asset[:90])}</b></div>'
            if indic:
                ins += (f'<div class="kv"><span>Indication</span>'
                        f'<b>{esc(indic[:90])}</b></div>')
            doc = re.sub(r'(<div class="kv"><span>FDA decision date</span><b>[^<]*</b></div>)',
                         r"\1" + ins, doc, count=1)
        # contradiction: say what changed, visibly
        if r["status"] == "CONTRADICTION":
            note = (f'<div style="background:rgba(255,143,143,.08);border:1px solid #6e2020;'
                    f'border-radius:10px;padding:12px 14px;margin:14px 0;font-size:13.5px;'
                    f'line-height:1.6;color:#f0c8c8"><b>Correction ({TODAY}).</b> An earlier '
                    f'version of this page inferred '
                    f'{"a CRL" if r["claimed"] == "crl" else "an approval"} from the share-price '
                    f'reaction. The primary source shows the outcome was '
                    f'{"approval" if outcome == "Approved" else "a Complete Response Letter"}; '
                    f'the price read was wrong, which is why this site no longer publishes '
                    f'price-inferred outcomes as fact.</div>')
            doc = doc.replace("<h1", note + "<h1", 1)
        # lift noindex
        doc = doc.replace('<meta name="robots" content="noindex,follow">',
                          '<meta name="robots" content="index,follow">')

        if doc != o and not a.dry_run:
            open(p, "w", encoding="utf-8").write(doc)
        if r["status"] == "CONTRADICTION":
            contradictions += 1
            print(f"  !! CORRECTED {slug}: claimed {r['claimed']}, source shows {outcome}"
                  f"  [{ev['source_label'][:60]}]")
        else:
            upgraded += 1

    # /decisions listing rows: verified entries said 'Approved: price-only'. That text is both
    # user-facing AND the source fix_meta_lengths derives decision titles from -- which is how
    # 'Price-only' kept resurrecting in titles after every pipeline run. The row now names the
    # drug instead, which is what a reader scanning the archive actually wants.
    lp = os.path.join(SITE, "decisions", "index.html")
    if os.path.exists(lp):
        ld = open(lp, encoding="utf-8", errors="replace").read()
        o = ld
        for slug, r in res.items():
            if r["status"] not in ("verified_approved", "verified_crl"):
                continue
            row = odin.get((r["ticker"], r["date"]), {})
            asset = re.sub(r"\s+", " ", str(row.get("asset") or "")).strip()
            label = esc(re.split(r"\s*[(-]", asset)[0].strip()[:40]) if asset \
                else "primary-sourced"
            ld = ld.replace(
                f'href="/fda-decision/{slug}"><div class="t">{r["ticker"]} &middot; '
                f'{r["date"]} <span class="ok">&#10003;</span></div><div class="d">'
                f'<span class="ok">Approved</span>: price-only</div>',
                f'href="/fda-decision/{slug}"><div class="t">{r["ticker"]} &middot; '
                f'{r["date"]} <span class="ok">&#10003;</span></div><div class="d">'
                f'<span class="ok">Approved</span>: {label}</div>')
            # rows are stored unescaped in the file; handle the literal form too.
            # Approved rows use class "ok"; CRL rows use class "no" (checked in the file,
            # after guessing "bad" left the 7 CRL rows tagged and their titles regressing).
            for oc_html, oc_ok in (("Approved", "ok"), ("CRL", "no")):
                ld = re.sub(
                    rf'(href="/fda-decision/{slug}">.{{0,160}}?<span class="{oc_ok}">'
                    rf'{oc_html}</span>): price-only</div>',
                    rf"\1: {label}</div>", ld)
        if ld != o and not a.dry_run:
            open(lp, "w", encoding="utf-8").write(ld)
            print("  /decisions listing rows: price-only tags replaced with drug names")

    print(f"\nupgraded: {upgraded}; corrected contradictions: {contradictions}; "
          f"already done: {skipped}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
