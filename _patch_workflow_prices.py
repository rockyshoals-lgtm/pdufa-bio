# One-off: point the rebuild workflow's price steps at price_source (FMP), audit 2026-11-09 §4.
import io, re
P = r"C:\Users\dcmoo\Documents\Python\9realms\.github\workflows\pdufa-rebuild.yml"
s = io.open(P, encoding="utf-8").read()
orig = s

s = s.replace(
    "#   POLYGON_API_KEY   (price/market-cap refresh)\n",
    "#   FMP_API_KEY       PRICES OF RECORD since 2026-11-10 (price_source.py): daily closes, batch quotes, market caps.\n"
    "#                     Paid FMP /stable/ plan on David's account (the plan's per-minute limit is set on that account;\n"
    "#                     one run makes ~50 calls for the forward slate plus one per run-up/readout series it extends).\n"
    "#   POLYGON_API_KEY   FALLBACK ONLY until 2026-11-17 (PRICE_POLYGON_FALLBACK); then the secret and code are removed.\n"
    "#   ALPACA_KEY_ID / ALPACA_SECRET_KEY  optional free fallback; price_source uses them only if both secrets exist.\n", 1)
s = s.replace("#   FMP_API_KEY       (optional; only if a step needs it)\n", "", 1)

old_step = ("      - name: Refresh prices / market caps (Polygon, forward catalysts only)\n"
            "        env:\n"
            "          POLYGON_API_KEY: ${{ secrets.POLYGON_API_KEY }}\n"
            "        run: python polygon_enrich.py\n")
new_step = ("      # 2026-11-10 (audit 11-09 §4): FMP via price_source.py, ~20 s (Polygon's free tier took ~25 min and a 429 on\n"
            "      # 10-22 froze three runs). Everything that refreshed is written; if any forward ticker not on\n"
            "      # _price_no_feed.json got no data, the step fails NAMING it and the next step opens one PRICES issue. The\n"
            "      # deploy continues on the kept values (a frozen night costs ~80% of the next day's Bing AI citations).\n"
            "      - name: Refresh prices / market caps (FMP, forward catalysts only)\n"
            "        id: prices\n"
            "        continue-on-error: true\n"
            "        env:\n"
            "          FMP_API_KEY: ${{ secrets.FMP_API_KEY }}\n"
            "          POLYGON_API_KEY: ${{ secrets.POLYGON_API_KEY }}\n"
            "          ALPACA_KEY_ID: ${{ secrets.ALPACA_KEY_ID }}\n"
            "          ALPACA_SECRET_KEY: ${{ secrets.ALPACA_SECRET_KEY }}\n"
            "        run: python polygon_enrich.py\n\n"
            "      - name: \"PRICES issue: a forward ticker got no price data (named)\"\n"
            "        if: steps.prices.outcome == 'failure'\n"
            "        env:\n"
            "          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}\n"
            "        run: |\n"
            "          python - <<'EOF'\n"
            "          import json, subprocess\n"
            "          m = json.load(open('_price_missing.json')).get('missing') or ['(price step failed before naming tickers)']\n"
            "          t = 'PRICES: no price data for ' + ', '.join(m)\n"
            "          body = ('@rockyshoals-lgtm The price step got nothing from FMP (or its fallbacks) for: ' + ', '.join(m) +\n"
            "                  '. Their previous price and market cap were kept and the site deployed. Fix the symbol, or add the '\n"
            "                  'ticker to _price_no_feed.json with a reason.')\n"
            "          out = subprocess.run(['gh', 'issue', 'list', '--state', 'open', '--search', 'PRICES: in:title', '--json', 'title'],\n"
            "                               capture_output=True, text=True).stdout\n"
            "          if not any(i['title'] == t for i in json.loads(out or '[]')):\n"
            "              subprocess.run(['gh', 'issue', 'create', '--title', t, '--body', body])\n"
            "          EOF\n")
assert old_step in s, "price step not found"
s = s.replace(old_step, new_step, 1)

# every step that reads prices gets the FMP key (price_source) next to the Polygon fallback key
n = 0
def add_fmp(m):
    global n
    block = m.group(0)
    if "FMP_API_KEY" in block:
        return block
    n += 1
    ind = m.group(1)
    return block + f"{ind}FMP_API_KEY: ${{{{ secrets.FMP_API_KEY }}}}\n"
s = re.sub(r"(?m)^( +)POLYGON_API_KEY: \$\{\{ secrets\.POLYGON_API_KEY \}\}\n(?:\1[A-Z_]+: .*\n)*", add_fmp, s)
io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("patched; FMP key added to", n, "more env blocks")
