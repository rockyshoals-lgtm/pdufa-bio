"""
app.py — SweepRunner main application.
"""
import json, sqlite3, threading, logging
from datetime import datetime, timedelta
from pathlib import Path
from flask import Flask, jsonify, request, render_template
from apscheduler.schedulers.background import BackgroundScheduler

app    = Flask(__name__)
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

ROOT        = Path(__file__).parent
DB_PATH     = ROOT / 'sweepstakes.db'
CONFIG_PATH = ROOT / 'config.json'

with open(CONFIG_PATH) as f:
    CONFIG = json.load(f)

automation_status = {'running': False, 'current': None, 'log': []}
lottery_cache     = {}
opportunity_count = {'count': 0, 'superstars': 0}
verify_state      = {'pending': None, 'response': None}


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS sweepstakes (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                name          TEXT NOT NULL,
                url           TEXT NOT NULL,
                frequency     TEXT NOT NULL DEFAULT 'once',
                category      TEXT DEFAULT 'General',
                notes         TEXT DEFAULT '',
                prize_value   REAL DEFAULT 0,
                prize_text    TEXT DEFAULT '',
                end_date      TEXT DEFAULT '',
                source        TEXT DEFAULT 'manual',
                active        INTEGER DEFAULT 1,
                url_alive     INTEGER DEFAULT 1,
                verified_at   TEXT DEFAULT '',
                created_at    TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS entries (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                sweepstake_id INTEGER NOT NULL,
                entered_at    TEXT DEFAULT (datetime('now')),
                status        TEXT DEFAULT 'pending',
                notes         TEXT DEFAULT '',
                FOREIGN KEY (sweepstake_id) REFERENCES sweepstakes(id)
            );
            CREATE TABLE IF NOT EXISTS wins (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                sweepstake_id INTEGER NOT NULL,
                won_at        TEXT DEFAULT (datetime('now')),
                prize         TEXT DEFAULT '',
                value         REAL DEFAULT 0,
                notes         TEXT DEFAULT '',
                FOREIGN KEY (sweepstake_id) REFERENCES sweepstakes(id)
            );
            CREATE TABLE IF NOT EXISTS discovered (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL,
                url         TEXT NOT NULL UNIQUE,
                prize_value REAL DEFAULT 0,
                prize_text  TEXT DEFAULT '',
                end_date    TEXT DEFAULT '',
                frequency   TEXT DEFAULT 'once',
                category    TEXT DEFAULT 'General',
                source      TEXT DEFAULT '',
                found_at    TEXT DEFAULT (datetime('now')),
                status      TEXT DEFAULT 'pending'
            );
            CREATE TABLE IF NOT EXISTS lottery_snapshots (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_at TEXT DEFAULT (datetime('now')),
                data        TEXT NOT NULL
            );
        """)
        existing = [row[1] for row in conn.execute("PRAGMA table_info(sweepstakes)").fetchall()]
        for col, typedef in [
            ('prize_value','REAL DEFAULT 0'), ('prize_text','TEXT DEFAULT ""'),
            ('end_date','TEXT DEFAULT ""'),   ('source','TEXT DEFAULT "manual"'),
            ('url_alive','INTEGER DEFAULT 1'),('verified_at','TEXT DEFAULT ""'),
        ]:
            if col not in existing:
                conn.execute(f'ALTER TABLE sweepstakes ADD COLUMN {col} {typedef}')
    logger.info('Database ready.')


def log_auto(msg):
    automation_status['log'].append({'time': datetime.now().strftime('%H:%M:%S'), 'msg': msg})
    if len(automation_status['log']) > 300:
        automation_status['log'] = automation_status['log'][-300:]
    logger.info(msg)


def is_eligible(sid, frequency):
    with get_db() as conn:
        last = conn.execute(
            "SELECT entered_at FROM entries WHERE sweepstake_id=? AND status='success' ORDER BY entered_at DESC LIMIT 1",
            (sid,)).fetchone()
    if not last: return True
    last_dt = datetime.fromisoformat(last['entered_at'])
    now = datetime.now()
    if frequency == 'once':    return False
    if frequency == 'daily':   return last_dt.date() < now.date()
    if frequency == 'weekly':  return (now - last_dt) > timedelta(weeks=1)
    if frequency == 'monthly': return (now.year, now.month) > (last_dt.year, last_dt.month)
    return True


def next_eligible_str(sid, frequency):
    with get_db() as conn:
        last = conn.execute(
            "SELECT entered_at FROM entries WHERE sweepstake_id=? AND status='success' ORDER BY entered_at DESC LIMIT 1",
            (sid,)).fetchone()
    if not last: return 'Now'
    last_dt = datetime.fromisoformat(last['entered_at'])
    if frequency == 'once': return 'Never'
    if frequency == 'daily':
        nxt = (last_dt + timedelta(days=1)).replace(hour=0,minute=0,second=0)
        return 'Now' if nxt <= datetime.now() else nxt.strftime('%b %d')
    if frequency == 'weekly':
        nxt = last_dt + timedelta(weeks=1)
        return 'Now' if nxt <= datetime.now() else nxt.strftime('%b %d')
    if frequency == 'monthly':
        m = last_dt.month % 12 + 1
        y = last_dt.year + (1 if last_dt.month == 12 else 0)
        nxt = last_dt.replace(year=y, month=m, day=1)
        return 'Now' if nxt <= datetime.now() else nxt.strftime('%b %Y')
    return 'Now'


def sweepstake_star(prize_value):
    opps = CONFIG.get('opportunities', {})
    if prize_value >= opps.get('sweepstakes_prize_superstar', 50000): return '🌟'
    if prize_value >= opps.get('sweepstakes_prize_star', 10000):      return '⭐'
    return ''


def run_entry(sid, url, name):
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWT
    except ImportError:
        log_auto('Playwright not installed. Run SETUP.bat'); return 'error'

    profile  = CONFIG['profile']
    settings = CONFIG['settings']
    field_map = {
        'first':profile['first_name'],'fname':profile['first_name'],'firstname':profile['first_name'],
        'last':profile['last_name'],'lname':profile['last_name'],'lastname':profile['last_name'],
        'fullname':profile['full_name'],'name':profile['full_name'],
        'email':profile['email'],'phone':profile['phone'],'telephone':profile['phone'],
        'mobile':profile['phone'],'address':profile['address1'],'address1':profile['address1'],
        'street':profile['address1'],'city':profile['city'],'state':profile['state'],
        'zip':profile['zip'],'postal':profile['zip'],'zipcode':profile['zip'],
        'dob':profile['dob'],'birthdate':profile['dob'],'gender':profile['gender'],
        'country':profile['country'],
    }
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=settings.get('headless',False), channel='chrome')
        page    = browser.new_context().new_page()
        try:
            log_auto(f'Navigating: {url}')
            page.goto(url, timeout=30000)
            page.wait_for_load_state('networkidle', timeout=15000)

            # Hop through intro/landing pages to reach the actual form (max 3 hops)
            intro_button_selectors = [
                "a:has-text('I want to enter')",      "button:has-text('I want to enter')",
                "a:has-text('Enter to Win')",         "button:has-text('Enter to Win')",
                "a:has-text('Enter Now')",            "button:has-text('Enter Now')",
                "a:has-text('Enter Today')",          "button:has-text('Enter Today')",
                "a:has-text('Enter Sweepstakes')",    "button:has-text('Enter Sweepstakes')",
                "a:has-text('Enter Contest')",        "button:has-text('Enter Contest')",
                "a:has-text('Enter Here')",           "button:has-text('Enter Here')",
                "a:has-text('Click to Enter')",       "button:has-text('Click to Enter')",
                "a:has-text('Click Here to Enter')",  "button:has-text('Click Here to Enter')",
                "a:has-text('Get Started')",          "button:has-text('Get Started')",
                "a:has-text('Continue')",             "button:has-text('Continue')",
                "a.enter-button", "a.entry-button", "button.enter-button", "button.entry-button",
                "a[href*='enter']:not([href*='enterprise'])",
            ]
            for hop in range(3):
                form_inputs = page.query_selector_all(
                    "input[type='text'], input[type='email'], input[type='tel'], "
                    "input[type='number'], input:not([type]), textarea"
                )
                if len(form_inputs) >= 3:
                    log_auto(f'  Form found ({len(form_inputs)} fields)')
                    break
                log_auto(f'  Intro page (only {len(form_inputs)} fields) — looking for entry link...')
                clicked = False
                for selector in intro_button_selectors:
                    try:
                        btn = page.query_selector(selector)
                        if btn and btn.is_visible():
                            href = btn.get_attribute('href') or ''
                            log_auto(f'  → Clicking: {selector}')
                            # If it opens new tab, capture it
                            ctx = page.context
                            try:
                                with ctx.expect_page(timeout=5000) as new_page_info:
                                    btn.click()
                                new_page = new_page_info.value
                                page.close()
                                page = new_page
                                page.wait_for_load_state('networkidle', timeout=15000)
                            except Exception:
                                # Same-tab navigation
                                btn.click()
                                page.wait_for_load_state('networkidle', timeout=15000)
                            page.wait_for_timeout(2000)
                            clicked = True
                            break
                    except Exception:
                        continue
                if not clicked:
                    log_auto('  No entry link found — proceeding with current page')
                    break

            inputs = page.query_selector_all("input:not([type=hidden]):not([type=submit]):not([type=button]):not([type=checkbox]):not([type=radio])")
            filled = 0
            for inp in inputs:
                try:
                    combined = ' '.join(filter(None,[inp.get_attribute('id') or '',inp.get_attribute('name') or '',inp.get_attribute('placeholder') or ''])).lower()
                    for key,val in field_map.items():
                        if key in combined:
                            inp.fill(str(val)); page.wait_for_timeout(settings.get('delay_between_fields_ms',300)); filled+=1; break
                except: pass
            log_auto(f'Filled {filled} fields')
            for sel in page.query_selector_all('select'):
                try:
                    combined = ((sel.get_attribute('id') or '')+(sel.get_attribute('name') or '')).lower()
                    if 'state' in combined:
                        try: sel.select_option(value=profile['state'])
                        except: sel.select_option(label=profile['state_full'])
                    elif 'gender' in combined:
                        try: sel.select_option(value='male')
                        except: sel.select_option(label='Male')
                    elif 'country' in combined:
                        try: sel.select_option(value=profile['country'])
                        except: sel.select_option(label=profile['country_full'])
                except: pass

            # Comment/textarea fields — "tell us why you want to win" style
            try:
                from modules.comments import generate_comment, is_comment_field
                comment_text = generate_comment(name)
                comments_filled = 0
                # Textareas
                for ta in page.query_selector_all('textarea'):
                    try:
                        combined = ' '.join(filter(None,[
                            ta.get_attribute('id') or '',
                            ta.get_attribute('name') or '',
                            ta.get_attribute('placeholder') or '',
                            ta.get_attribute('aria-label') or '',
                        ]))
                        if is_comment_field(combined) or combined.strip() == '':
                            ta.fill(comment_text)
                            page.wait_for_timeout(settings.get('delay_between_fields_ms',300))
                            comments_filled += 1
                    except: pass
                # Long text inputs with comment-like names
                for inp in page.query_selector_all("input[type='text']"):
                    try:
                        combined = ' '.join(filter(None,[
                            inp.get_attribute('id') or '',
                            inp.get_attribute('name') or '',
                            inp.get_attribute('placeholder') or '',
                        ]))
                        if is_comment_field(combined):
                            inp.fill(comment_text)
                            page.wait_for_timeout(settings.get('delay_between_fields_ms',300))
                            comments_filled += 1
                    except: pass
                if comments_filled:
                    log_auto(f'Comment ({comments_filled}x): "{comment_text}"')
            except Exception as e:
                log_auto(f'Comment fill skipped: {str(e)[:80]}')
            captcha_sels = ["iframe[src*='recaptcha']","iframe[src*='hcaptcha']",".g-recaptcha",".h-captcha","[data-sitekey]"]
            if any(page.query_selector(s) for s in captcha_sels):
                log_auto('CAPTCHA detected — waiting up to 2 min...')
                try:
                    page.wait_for_function("()=>document.querySelector('.g-recaptcha-response')&&document.querySelector('.g-recaptcha-response').value.length>0",timeout=settings.get('captcha_timeout_seconds',120)*1000)
                    log_auto('CAPTCHA solved')
                except PWT:
                    log_auto('CAPTCHA timeout — skipped'); browser.close(); return 'captcha_timeout'
            submit = (page.query_selector("input[type=submit]") or page.query_selector("button[type=submit]") or
                      page.query_selector("button:has-text('Enter Now')") or page.query_selector("button:has-text('Enter')") or
                      page.query_selector("button:has-text('Submit')"))
            if submit:
                submit.click(); page.wait_for_timeout(settings.get('delay_between_entries_ms',2000))
                log_auto(f'Submitted: {name}')

                # Verify mode — wait for user to confirm before closing
                if settings.get('verify_mode', True):
                    import time
                    verify_state['pending'] = {'name': name, 'id': sid, 'started_at': datetime.now().isoformat()}
                    verify_state['response'] = None
                    log_auto(f'⏸ Browser staying open — verify entry then click button in dashboard')
                    timeout = settings.get('verify_timeout_seconds', 180)
                    elapsed = 0
                    while verify_state['response'] is None and elapsed < timeout:
                        time.sleep(1); elapsed += 1
                    result = verify_state['response'] or 'manual'
                    verify_state['pending'] = None
                    verify_state['response'] = None
                    log_auto(f'   → marked as {result}')
                    browser.close()
                    return result
                else:
                    browser.close()
                    return 'success'
            else:
                log_auto('No submit button found'); page.wait_for_timeout(8000); browser.close(); return 'manual'
        except Exception as e:
            log_auto(f'Error on {name}: {str(e)[:120]}')
            try: browser.close()
            except: pass
            return 'error'


def run_due_entries():
    if automation_status['running']: return
    with threading.Lock():
        automation_status['running'] = True
        log_auto('Starting due-entries run...')
        with get_db() as conn:
            rows = conn.execute("SELECT id,name,url,frequency FROM sweepstakes WHERE active=1 AND url_alive=1").fetchall()
        for row in rows:
            if is_eligible(row['id'], row['frequency']):
                automation_status['current'] = row['name']
                status = run_entry(row['id'], row['url'], row['name'])
                with get_db() as conn:
                    conn.execute("INSERT INTO entries (sweepstake_id,status) VALUES (?,?)",(row['id'],status))
        automation_status['running'] = False
        automation_status['current'] = None
        log_auto('Run complete.')


def job_refresh_lottery():
    log_auto('Refreshing lottery data...')
    try:
        from modules.lottery import get_all_games
        from modules.notifier import notify_opportunities
        data = get_all_games(CONFIG, log_cb=log_auto)
        lottery_cache.update(data)
        lottery_cache['fetched'] = datetime.now().isoformat()
        with get_db() as conn:
            conn.execute("INSERT INTO lottery_snapshots (data) VALUES (?)", (json.dumps(data),))
        opportunity_count['count']      = data.get('stars', 0)
        opportunity_count['superstars'] = sum(1 for o in data.get('opportunities',[]) if '🌟' in o.get('star',''))
        log_auto(f'Lottery refreshed — {opportunity_count["count"]} starred')
        if CONFIG.get('opportunities',{}).get('notify_on_superstar') and opportunity_count['superstars']:
            notify_opportunities([o for o in data['opportunities'] if '🌟' in o.get('star','')])
    except Exception as e:
        log_auto(f'Lottery refresh error: {e}')


def job_discover():
    log_auto('Discovering new sweepstakes...')
    try:
        from modules.finder import discover_all
        with get_db() as conn:
            existing = {row[0] for row in conn.execute("SELECT url FROM sweepstakes").fetchall()}
            existing |= {row[0] for row in conn.execute("SELECT url FROM discovered").fetchall()}
        found = discover_all(existing_urls=existing, log_cb=log_auto)
        with get_db() as conn:
            for item in found:
                try:
                    conn.execute("""INSERT OR IGNORE INTO discovered
                        (name,url,prize_value,prize_text,end_date,frequency,category,source)
                        VALUES (?,?,?,?,?,?,?,?)""",
                        (item['name'],item['url'],item.get('prize_value',0),item.get('prize_text',''),
                         item.get('end_date',''),item.get('frequency','once'),item.get('category','General'),item.get('source','')))
                except: pass
        log_auto(f'Discovery: {len(found)} new sweepstakes queued')
    except Exception as e:
        log_auto(f'Discovery error: {e}')


def job_validate():
    log_auto('Validating sweepstake URLs...')
    try:
        from modules.validator import validate_all
        with get_db() as conn:
            rows = conn.execute("SELECT id,name,url FROM sweepstakes WHERE active=1").fetchall()
        results = validate_all([dict(r) for r in rows])
        with get_db() as conn:
            for r in results:
                conn.execute("UPDATE sweepstakes SET url_alive=?,verified_at=? WHERE id=?",
                             (1 if r['alive'] else 0, r['checked_at'], r['id']))
        log_auto(f'Validation done — {sum(1 for r in results if not r["alive"])} dead URLs')
    except Exception as e:
        log_auto(f'Validation error: {e}')


@app.route('/')
def index(): return render_template('index.html')

@app.route('/api/sweepstakes', methods=['GET'])
def list_sweepstakes():
    sort = request.args.get('sort','created')
    filt = request.args.get('filter','active')
    order = {'prize':'prize_value DESC','ends':"CASE WHEN end_date='' THEN '9999' ELSE end_date END ASC",'name':'name ASC','created':'created_at DESC'}.get(sort,'created_at DESC')
    where = {'active':'WHERE active=1','all':'','inactive':'WHERE active=0'}.get(filt,'WHERE active=1')
    with get_db() as conn:
        rows = conn.execute(f"SELECT * FROM sweepstakes {where} ORDER BY {order}").fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d['eligible']      = is_eligible(r['id'], r['frequency'])
        d['next_eligible'] = next_eligible_str(r['id'], r['frequency'])
        d['star']          = sweepstake_star(r['prize_value'] or 0)
        with get_db() as conn:
            d['entry_count'] = conn.execute("SELECT COUNT(*) FROM entries WHERE sweepstake_id=? AND status='success'",(r['id'],)).fetchone()[0]
        result.append(d)
    return jsonify(result)

@app.route('/api/sweepstakes', methods=['POST'])
def add_sweepstake():
    d = request.json
    with get_db() as conn:
        conn.execute("INSERT INTO sweepstakes (name,url,frequency,category,notes,prize_value,prize_text,end_date,source) VALUES (?,?,?,?,?,?,?,?,?)",
            (d['name'],d['url'],d.get('frequency','once'),d.get('category','General'),d.get('notes',''),d.get('prize_value',0),d.get('prize_text',''),d.get('end_date',''),d.get('source','manual')))
    return jsonify({'ok':True})

@app.route('/api/sweepstakes/<int:sid>', methods=['PUT'])
def update_sweepstake(sid):
    d = request.json
    with get_db() as conn:
        conn.execute("UPDATE sweepstakes SET name=?,url=?,frequency=?,category=?,notes=?,prize_value=?,prize_text=?,end_date=?,active=? WHERE id=?",
            (d['name'],d['url'],d['frequency'],d.get('category','General'),d.get('notes',''),d.get('prize_value',0),d.get('prize_text',''),d.get('end_date',''),d.get('active',1),sid))
    return jsonify({'ok':True})

@app.route('/api/sweepstakes/<int:sid>', methods=['DELETE'])
def delete_sweepstake(sid):
    with get_db() as conn:
        conn.execute("DELETE FROM sweepstakes WHERE id=?", (sid,))
        conn.execute("DELETE FROM entries WHERE sweepstake_id=?", (sid,))
    return jsonify({'ok':True})

@app.route('/api/entries')
def list_entries():
    with get_db() as conn:
        rows = conn.execute("SELECT e.*,s.name as sweepstake_name,s.frequency FROM entries e JOIN sweepstakes s ON e.sweepstake_id=s.id ORDER BY e.entered_at DESC LIMIT 300").fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/api/wins')
def list_wins():
    with get_db() as conn:
        rows = conn.execute("SELECT w.*,s.name as sweepstake_name FROM wins w JOIN sweepstakes s ON w.sweepstake_id=s.id ORDER BY w.won_at DESC").fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/api/wins', methods=['POST'])
def log_win():
    d = request.json
    with get_db() as conn:
        conn.execute("INSERT INTO wins (sweepstake_id,prize,value,notes) VALUES (?,?,?,?)",
                     (d['sweepstake_id'],d.get('prize',''),d.get('value',0),d.get('notes','')))
    return jsonify({'ok':True})

@app.route('/api/run', methods=['POST'])
def run_all():
    if automation_status['running']: return jsonify({'ok':False,'msg':'Already running'})
    threading.Thread(target=run_due_entries, daemon=True).start()
    return jsonify({'ok':True})

@app.route('/api/run/single/<int:sid>', methods=['POST'])
def run_single(sid):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM sweepstakes WHERE id=?", (sid,)).fetchone()
    if not row: return jsonify({'ok':False})
    def do_run():
        automation_status['running']=True; automation_status['current']=row['name']
        status = run_entry(row['id'],row['url'],row['name'])
        with get_db() as conn:
            conn.execute("INSERT INTO entries (sweepstake_id,status) VALUES (?,?)",(row['id'],status))
        automation_status['running']=False; automation_status['current']=None
    threading.Thread(target=do_run, daemon=True).start()
    return jsonify({'ok':True})

@app.route('/api/verify/<status>', methods=['POST'])
def verify_entry(status):
    if status not in ('success', 'error', 'manual'):
        return jsonify({'ok': False, 'msg': 'Invalid status'})
    verify_state['response'] = status
    return jsonify({'ok': True})

@app.after_request
def add_cors_headers(response):
    # Only enable CORS for bookmarklet endpoints so it can be called from any site
    if request.path in ('/api/profile', '/api/generate_comment'):
        response.headers['Access-Control-Allow-Origin']  = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response


@app.route('/api/profile')
def get_profile():
    """Returns the profile for the bookmarklet to fill into forms."""
    return jsonify({'profile': CONFIG['profile']})


@app.route('/api/generate_comment')
def get_comment():
    """Returns a contextual comment for the bookmarklet based on page title."""
    title = request.args.get('title', '')
    try:
        from modules.comments import generate_comment
        return jsonify({'comment': generate_comment(title)})
    except Exception as e:
        return jsonify({'comment': "I'd love to win!"})


@app.route('/api/run_adhoc', methods=['POST'])
def run_adhoc():
    """Fill an arbitrary URL not tied to a saved sweepstakes."""
    d = request.json or {}
    url  = (d.get('url') or '').strip()
    name = (d.get('name') or 'Ad-hoc entry').strip()
    if not url or not url.startswith('http'):
        return jsonify({'ok': False, 'msg': 'Invalid URL'})
    if automation_status['running']:
        return jsonify({'ok': False, 'msg': 'Automation already running'})
    def do_run():
        automation_status['running'] = True
        automation_status['current'] = name
        try:
            run_entry(0, url, name)  # id=0 means don't record entry
        finally:
            automation_status['running'] = False
            automation_status['current'] = None
    threading.Thread(target=do_run, daemon=True).start()
    return jsonify({'ok': True})


@app.route('/api/status')
def get_status():
    with get_db() as conn:
        active       = conn.execute("SELECT COUNT(*) FROM sweepstakes WHERE active=1").fetchone()[0]
        today        = conn.execute("SELECT COUNT(*) FROM entries WHERE DATE(entered_at)=DATE('now') AND status='success'").fetchone()[0]
        total        = conn.execute("SELECT COUNT(*) FROM entries WHERE status='success'").fetchone()[0]
        wins         = conn.execute("SELECT COUNT(*) FROM wins").fetchone()[0]
        win_val      = conn.execute("SELECT COALESCE(SUM(value),0) FROM wins").fetchone()[0]
        pending_disc = conn.execute("SELECT COUNT(*) FROM discovered WHERE status='pending'").fetchone()[0]
        dead_urls    = conn.execute("SELECT COUNT(*) FROM sweepstakes WHERE url_alive=0 AND active=1").fetchone()[0]
    return jsonify({**automation_status,'opportunity_count':opportunity_count,'verify':verify_state['pending'],'stats':{'active_sweepstakes':active,'entries_today':today,'total_entries':total,'wins':wins,'win_value':win_val,'pending_discovery':pending_disc,'dead_urls':dead_urls}})

@app.route('/api/log')
def get_log(): return jsonify(automation_status['log'])

@app.route('/api/lottery')
def get_lottery():
    if not lottery_cache: return jsonify({'scratch':[],'draw':[],'opportunities':[],'stars':0,'fetched':None})
    return jsonify(lottery_cache)

@app.route('/api/lottery/refresh', methods=['POST'])
def refresh_lottery():
    threading.Thread(target=job_refresh_lottery, daemon=True).start()
    return jsonify({'ok':True})

@app.route('/api/discovered')
def list_discovered():
    sort = request.args.get('sort','prize')
    order = 'prize_value DESC' if sort=='prize' else 'found_at DESC'
    with get_db() as conn:
        rows = conn.execute(f"SELECT * FROM discovered WHERE status='pending' ORDER BY {order}").fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/api/discovered/<int:did>/add', methods=['POST'])
def add_discovered(did):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM discovered WHERE id=?", (did,)).fetchone()
        if not row: return jsonify({'ok':False})
        conn.execute("INSERT INTO sweepstakes (name,url,frequency,category,prize_value,prize_text,end_date,source) VALUES (?,?,?,?,?,?,?,?)",
            (row['name'],row['url'],row['frequency'],row['category'],row['prize_value'],row['prize_text'],row['end_date'],row['source']))
        conn.execute("UPDATE discovered SET status='added' WHERE id=?", (did,))
    return jsonify({'ok':True})

@app.route('/api/discovered/<int:did>/dismiss', methods=['POST'])
def dismiss_discovered(did):
    with get_db() as conn:
        conn.execute("UPDATE discovered SET status='dismissed' WHERE id=?", (did,))
    return jsonify({'ok':True})

@app.route('/api/discover/run', methods=['POST'])
def run_discovery():
    threading.Thread(target=job_discover, daemon=True).start()
    return jsonify({'ok':True})

@app.route('/api/discovered/cleanup', methods=['POST'])
def cleanup_discovered():
    def do_cleanup():
        log_auto('Cleaning up expired/dead discovered items...')
        try:
            from modules.finder import validate_pending
            with get_db() as conn:
                rows = conn.execute("SELECT id,url,end_date FROM discovered WHERE status='pending'").fetchall()
            items = [dict(r) for r in rows]
            log_auto(f'  {len(items)} pending items to check')
            to_remove = validate_pending(items, log_cb=log_auto)
            if to_remove:
                with get_db() as conn:
                    placeholders = ','.join('?' * len(to_remove))
                    conn.execute(f"UPDATE discovered SET status='dismissed' WHERE id IN ({placeholders})", to_remove)
            log_auto(f'Cleanup done — removed {len(to_remove)} items')
        except Exception as e:
            log_auto(f'Cleanup error: {e}')
    threading.Thread(target=do_cleanup, daemon=True).start()
    return jsonify({'ok':True})

@app.route('/api/validate/run', methods=['POST'])
def run_validation():
    threading.Thread(target=job_validate, daemon=True).start()
    return jsonify({'ok':True})

if __name__ == '__main__':
    init_db()
    sched_cfg = CONFIG.get('schedule',{})
    s = BackgroundScheduler()
    s.add_job(job_refresh_lottery,'cron',hour=sched_cfg.get('lottery_refresh_hour',7))
    s.add_job(job_discover,       'cron',hour=sched_cfg.get('discover_hour',8))
    s.add_job(job_validate,       'cron',hour=sched_cfg.get('validate_hour',9))
    s.add_job(run_due_entries,    'cron',hour=sched_cfg.get('entry_run_hour',9),minute=sched_cfg.get('entry_run_minute',30))
    s.start()
    threading.Thread(target=job_refresh_lottery, daemon=True).start()
    logger.info('SweepRunner on http://localhost:5050')
    app.run(debug=False, port=5050, use_reloader=False)
