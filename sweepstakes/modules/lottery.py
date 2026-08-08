"""
lottery.py — Oregon Lottery scraper with Playwright network interception.
Captures JSON API responses the page makes, much more reliable than HTML parsing.
"""
import re, json, logging
from datetime import datetime

logger = logging.getLogger(__name__)
TAX_RATE = 0.37


def parse_money(s):
    if not s: return 0.0
    s = re.sub(r'[^\d.]', '', str(s).replace(',',''))
    try: return float(s)
    except: return 0.0

def parse_odds(s):
    if not s: return 999999.0
    m = re.search(r'1\s*(?:in|:)\s*([\d,\.]+)', str(s), re.I)
    if m:
        try: return float(m.group(1).replace(',',''))
        except: pass
    return 999999.0

def stars(score, star_t, super_t):
    if score >= super_t: return '🌟'
    if score >= star_t:  return '⭐'
    return ''


def find_games_in_json(data, depth=0):
    """Recursively walk JSON structure to find arrays of game-like objects."""
    if depth > 6: return []
    results = []
    if isinstance(data, list):
        # An array — check if these look like game objects
        if data and isinstance(data[0], dict):
            sample = data[0]
            keys = ' '.join(sample.keys()).lower()
            if any(k in keys for k in ['name','game','prize','ticket','price']):
                results.extend(data)
        # Also recurse
        for item in data:
            results.extend(find_games_in_json(item, depth+1))
    elif isinstance(data, dict):
        for v in data.values():
            results.extend(find_games_in_json(v, depth+1))
    return results


def parse_game_object(obj):
    """Try to extract game info from various JSON shapes."""
    if not isinstance(obj, dict): return None

    # Name — try many common key names
    name = None
    for k in ('name','gameName','title','game_name','displayName','displayTitle',
              'productName','game','gameTitle','GameName','Name'):
        if k in obj and obj[k]:
            name = str(obj[k]).strip()
            break
    if not name or len(name) < 2: return None

    # Price
    price = 0.0
    for k in ('price','ticketPrice','cost','priceAmount','ticket_price','Price',
              'ticketCost','gamePrice'):
        if k in obj and obj[k]:
            price = parse_money(obj[k])
            if price > 0: break

    # Top prize
    top = 0.0
    for k in ('topPrize','top_prize','maxPrize','grandPrize','prize','topPrizeAmount',
              'TopPrize','maxPrizeAmount','jackpot','highPrize'):
        if k in obj and obj[k]:
            top = parse_money(obj[k])
            if top > 0: break

    # Remaining top prizes
    rem = 0
    for k in ('remaining','remainingPrizes','topPrizesRemaining','prizesRemaining',
              'topPrizeRemaining','remainingTopPrizes','RemainingPrizes'):
        if k in obj and obj[k] is not None:
            try: rem = int(re.sub(r'\D','', str(obj[k])) or 0)
            except: rem = 0
            if rem > 0: break

    # Odds
    odds = 999999.0
    for k in ('odds','overallOdds','oddsOfWinning','odds_of_winning','OverallOdds'):
        if k in obj and obj[k]:
            odds = parse_odds(obj[k])
            if odds < 999999: break

    # Need at least price or top prize to be useful
    if price == 0 and top == 0: return None

    return {
        'name': name[:80], 'type': 'scratch',
        'price': price or 1.0, 'top_prize': top,
        'remaining_top': rem, 'overall_odds': odds,
    }


def scrape_oregon_scratch(log_cb=None):
    def L(msg):
        if log_cb: log_cb(f'  [OR Scratch] {msg}')
        logger.info(f'scratch: {msg}')

    games = []
    api_responses = []

    try:
        from playwright.sync_api import sync_playwright
        from bs4 import BeautifulSoup

        L('Launching headless Chromium...')

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # Intercept JSON responses
            def on_response(response):
                try:
                    ctype = response.headers.get('content-type', '')
                    if 'json' in ctype.lower():
                        body = response.json()
                        api_responses.append({'url': response.url, 'body': body})
                except Exception:
                    pass
            page.on('response', on_response)

            page.goto('https://www.oregonlottery.org/games/scratch-its/remaining-prizes',
                      timeout=60000, wait_until='domcontentloaded')
            page.wait_for_timeout(8000)  # wait for JS-loaded data

            L(f'Captured {len(api_responses)} JSON API responses')

            # First try: find game data in captured JSON
            for resp in api_responses:
                try:
                    candidates = find_games_in_json(resp['body'])
                    if candidates:
                        L(f'  {resp["url"][-50:]}: {len(candidates)} game-like objects')
                        # Debug: log the keys of the first object so we can see structure
                        if candidates and isinstance(candidates[0], dict):
                            sample_keys = list(candidates[0].keys())[:15]
                            L(f'  Sample keys: {sample_keys}')
                        for c in candidates:
                            parsed = parse_game_object(c)
                            if parsed: games.append(parsed)
                        L(f'  Parsed {sum(1 for g in games if g)} from this response')
                except Exception as e:
                    L(f'  JSON parse error: {e}')

            # Backup: parse rendered HTML
            if not games:
                L('No JSON game data found, trying HTML...')
                content = page.content()
                soup = BeautifulSoup(content, 'html.parser')

                tables = soup.find_all('table')
                cards  = soup.select('[class*="game"], [class*="ticket"], [class*="prize"]')
                L(f'HTML: {len(tables)} tables, {len(cards)} game-like elements')

                # Try table parsing
                for table in tables:
                    rows = table.find_all('tr')
                    for row in rows[1:]:
                        cols = [td.get_text(strip=True) for td in row.find_all(['td','th'])]
                        if len(cols) >= 3:
                            try:
                                price = parse_money(cols[1]) if len(cols) > 1 else 1.0
                                top   = parse_money(cols[2]) if len(cols) > 2 else 0.0
                                rem_str = re.sub(r'\D','', cols[3]) if len(cols) > 3 else ''
                                rem   = int(rem_str) if rem_str else 0
                                if cols[0] and (price or top):
                                    games.append({
                                        'name': cols[0], 'type': 'scratch',
                                        'price': price or 1.0, 'top_prize': top,
                                        'remaining_top': rem, 'overall_odds': 4.5,
                                    })
                            except: pass

            browser.close()
    except Exception as e:
        L(f'Scrape failed: {str(e)[:120]}')

    # Compute EV/ROI scores
    for g in games:
        price = g.get('price', 1) or 1
        top   = g.get('top_prize', 0) or 0
        odds  = g.get('overall_odds', 1) or 1
        rem   = g.get('remaining_top', 0) or 0
        g['ev_per_dollar']   = round((top / max(odds,1)) / max(price,1), 4)
        g['roi_score']       = round((rem / max(odds,1)) * (top / max(price,1)) / 1000, 2)
        g['remaining_pool']  = top * rem
        g['source']          = 'Oregon Lottery'
        g['updated']         = datetime.now().isoformat()

    if not games:
        L('No game data found anywhere — adding placeholder')
        games = [{
            'name': '(Oregon Lottery data unavailable — site may have changed)',
            'type': 'scratch', 'price': 0, 'top_prize': 0, 'remaining_top': 0,
            'overall_odds': 0, 'ev_per_dollar': 0, 'roi_score': 0, 'remaining_pool': 0,
            'source': 'Unavailable', 'updated': datetime.now().isoformat(),
        }]

    games.sort(key=lambda x: x.get('roi_score', 0), reverse=True)
    L(f'Final: {len([g for g in games if g["price"]>0])} games')
    return games


def scrape_jackpots(log_cb=None):
    def L(msg):
        if log_cb: log_cb(f'  [Jackpots] {msg}')
        logger.info(f'jackpots: {msg}')

    games = []
    sources = [
        {'name':'Powerball',     'url':'https://www.powerball.com/',     'odds':292_201_338, 'price':2.0},
        {'name':'Mega Millions', 'url':'https://www.megamillions.com/',  'odds':302_575_350, 'price':2.0},
    ]

    try:
        from playwright.sync_api import sync_playwright
        from bs4 import BeautifulSoup

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            for src in sources:
                try:
                    page = browser.new_page()
                    page.goto(src['url'], timeout=25000, wait_until='domcontentloaded')
                    page.wait_for_timeout(4000)
                    text = page.inner_text('body')[:5000]
                    page.close()

                    jackpot = _extract_jackpot(text)
                    if not jackpot:
                        L(f'{src["name"]}: jackpot not found, using fallback')
                        jackpot = 20_000_000

                    ev = (jackpot * (1 - TAX_RATE)) / src['odds'] / src['price']
                    games.append({
                        'name': src['name'], 'type': 'draw',
                        'price': src['price'], 'jackpot': jackpot,
                        'odds': src['odds'], 'ev_per_dollar': round(ev, 6),
                        'roi_score': jackpot / 1_000_000,
                        'source': src['url'], 'updated': datetime.now().isoformat(),
                    })
                    L(f'{src["name"]}: ${jackpot/1e6:.0f}M jackpot')
                except Exception as e:
                    L(f'{src["name"]}: {str(e)[:80]}')
                    games.append(_fallback(src['name'], src['price'], src['odds']))
            browser.close()
    except Exception as e:
        L(f'All jackpot scraping failed: {e}')
        for src in sources:
            games.append(_fallback(src['name'], src['price'], src['odds']))

    games += [
        {'name':'Lucky for Life','type':'draw','price':2.0,'jackpot':7_300_000,'odds':30_821_472,
         'ev_per_dollar':round(7_300_000*(1-TAX_RATE)/30_821_472/2,6),'roi_score':7.3,
         'source':'Static','updated':datetime.now().isoformat()},
    ]

    games.sort(key=lambda x: x.get('roi_score', 0), reverse=True)
    return games


def _extract_jackpot(text):
    m = re.search(r'\$([\d,\.]+)\s*(million|billion)', text, re.I)
    if m:
        val  = float(m.group(1).replace(',',''))
        mult = 1_000_000_000 if 'billion' in m.group(2).lower() else 1_000_000
        return val * mult
    return 0.0


def _fallback(name, price, odds):
    j = 20_000_000
    return {'name': name, 'type':'draw', 'price':price, 'jackpot':j, 'odds':odds,
            'ev_per_dollar': round(j*(1-TAX_RATE)/odds/price, 6),
            'roi_score': 20.0, 'source':'Fallback', 'updated':datetime.now().isoformat()}


def get_all_games(config, log_cb=None):
    opp  = config.get('opportunities', {})
    s_st = opp.get('scratch_roi_star', 0.45)
    s_ss = opp.get('scratch_roi_superstar', 0.65)
    j_st = opp.get('jackpot_star_millions', 200) * 1_000_000
    j_ss = opp.get('jackpot_superstar_millions', 500) * 1_000_000

    scratch_games = scrape_oregon_scratch(log_cb=log_cb)
    draw_games    = scrape_jackpots(log_cb=log_cb)

    for g in scratch_games:
        g['star'] = stars(g.get('ev_per_dollar', 0), s_st, s_ss)
        g['is_opportunity'] = g.get('ev_per_dollar', 0) >= s_st
    for g in draw_games:
        j = g.get('jackpot', 0)
        g['star'] = stars(j, j_st, j_ss)
        g['is_opportunity'] = j >= j_st

    opps = []
    for g in scratch_games:
        if g.get('is_opportunity'):
            opps.append({'name':g['name'],'category':'Scratch Ticket',
                         'summary':f"${g['price']:.0f} · ${g['top_prize']:,.0f} top · {g['remaining_top']} remaining",
                         'score':g.get('roi_score',0),'star':g['star']})
    for g in draw_games:
        if g.get('is_opportunity'):
            opps.append({'name':g['name'],'category':'Draw Game',
                         'summary':f"${g.get('jackpot',0)/1e6:.0f}M jackpot",
                         'score':g.get('roi_score',0),'star':g['star']})

    opps.sort(key=lambda x: x['score'], reverse=True)
    return {
        'scratch':scratch_games, 'draw':draw_games,
        'opportunities':opps,
        'stars': sum(1 for g in scratch_games+draw_games if g.get('star')),
        'updated': datetime.now().isoformat(),
    }
