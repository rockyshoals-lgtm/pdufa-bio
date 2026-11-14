# One-off 2026-11-13 (David: "make sure we are using FMP for our stock prices"; remove Polygon now).
import io, os, re
H = r"C:\Users\dcmoo\Documents\Python\9realms"
def rw(f, fn):
    p = os.path.join(H, f); s = io.open(p, encoding="utf-8").read(); o = s; s = fn(s)
    if s != o:
        io.open(p, "w", encoding="utf-8", newline="").write(s); print("patched", f)
    else:
        print("UNCHANGED", f)

# 1. price_source: FMP only (+ dormant Alpaca); no Polygon path
def ps(s):
    s = s.replace("""  fallback  Polygon, ONLY while PRICE_POLYGON_FALLBACK is not "0" and POLYGON_API_KEY is set. Kept for one week after
            the 2026-11-10 cutover, then deleted (see the workflow header).
""", """  Polygon   REMOVED 2026-11-13 (David). Closes Polygon recorded before the 2026-11-10 cutover stay in the caches as
            the series of record; nothing fetches from Polygon any more (tests/test_prices_fmp_only.py).
""")
    s = s.replace('-> "FMP" | "Polygon" | "Alpaca" | None', '-> "FMP" | "Alpaca" | None')
    s = re.sub(r"\ndef _polygon_daily\(t, start, end\):.*?\n\n\n", "\n", s, flags=re.S)
    s = s.replace('for name, fn in (("FMP", _fmp_daily), ("Polygon", _polygon_daily), ("Alpaca", _alpaca_daily)):',
                  'for name, fn in (("FMP", _fmp_daily), ("Alpaca", _alpaca_daily)):')
    s = s.replace("""        if name != "Polygon":
            rows = _apply_recorded(ticker, rows)""", """        rows = _apply_recorded(ticker, rows)""")
    s = s.replace('STATS = {"FMP": 0, "Polygon": 0, "Alpaca": 0, "miss": 0, "calls": 0}', 'STATS = {"FMP": 0, "Alpaca": 0, "miss": 0, "calls": 0}')
    s = s.replace("""    return (f"price_source: {STATS['FMP']} series from FMP, {STATS['Polygon']} Polygon fallback, "
            f"{STATS['Alpaca']} Alpaca fallback, {STATS['miss']} with no data; {STATS['calls']} HTTP calls")""",
                  """    return (f"price_source: {STATS['FMP']} series from FMP, {STATS['Alpaca']} Alpaca fallback, "
            f"{STATS['miss']} with no data; {STATS['calls']} HTTP calls")""")
    return s
rw("price_source.py", ps)

# 2. polygon_enrich: drop the dead Polygon client and key loader
def pe(s):
    s = re.sub(r"\nclass Poly:.*?\n\n\ndef read_slate", "\n\ndef read_slate", s, flags=re.S)
    s = re.sub(r"\ndef load_key\(\):.*?\n\n\n", "\n\n", s, flags=re.S)
    s = s.replace("BASE = 'https://api.polygon.io'\n", "")
    s = s.replace('"""polygon_enrich.py', '"""polygon_enrich.py (name kept for workflow history; FMP only since 2026-11-10, Polygon code removed 2026-11-13)')
    return s
rw("polygon_enrich.py", pe)

# 3. scripts whose load_key() only gated "is there a price key": the key is FMP's now
for f in ("extend_runup_study.py", "add_t120_baseline.py", "build_home_board.py", "build_readout_results.py",
          "build_sls_hub.py", "build_sls_deepdive.py", "build_vktx_hub.py", "build_retail_pages.py", "build_stock_runup.py"):
    rw(f, lambda s: s.replace('return os.environ.get("POLYGON_API_KEY")',
                              'return os.environ.get("FMP_API_KEY")   # 2026-11-13: prices come from price_source (FMP)'))

# 4. add_decision_chart: its own Polygon fetch -> price_source
def adc(s):
    s = s.replace('return os.environ.get("POLYGON_API_KEY")', 'return os.environ.get("FMP_API_KEY")   # 2026-11-13: FMP via price_source')
    s = s.replace('raise SystemExit("no POLYGON_API_KEY -> leaving the honest no-chart note in place")',
                  'raise SystemExit("no FMP_API_KEY -> leaving the honest no-chart note in place")')
    s = s.replace("no Polygon data for", "no price data (FMP) for")
    s = s.replace("REAL Polygon daily closes", "REAL daily closes (FMP via price_source; Polygon before 2026-11-10)")
    s = s.replace("If Polygon has no data", "If FMP has no data")
    return s
rw("add_decision_chart.py", adc)

# 5. workflow: no Polygon secret anywhere
def wf(s):
    s = re.sub(r"\n +POLYGON_API_KEY: \$\{\{ secrets\.POLYGON_API_KEY \}\}[^\n]*", "", s)
    s = s.replace("#   POLYGON_API_KEY   FALLBACK ONLY until 2026-11-17 (PRICE_POLYGON_FALLBACK); then the secret and code are removed.\n",
                  "#   POLYGON_API_KEY   REMOVED 2026-11-13; no step reads it (tests/test_prices_fmp_only.py). Delete the repo secret.\n")
    return s
rw(".github/workflows/pdufa-rebuild.yml", wf)
