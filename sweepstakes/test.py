"""
test.py — Run this from your sweepstakes folder to diagnose what's working.
Usage: python test.py
"""
import requests, sys
from xml.etree import ElementTree as ET

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36'}

print("=" * 55)
print("  SWEEPRUNNER DIAGNOSTIC")
print("=" * 55)

# ── 1. Playwright ─────────────────────────────────────────────
print("\n[1] Playwright / Chromium")
try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        print("    Launching headless Chromium (no channel)...")
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://example.com", timeout=15000)
        title = page.title()
        browser.close()
        print(f"    ✓ Playwright OK — page title: {title}")
except Exception as e:
    print(f"    ✗ Playwright FAILED: {e}")

# ── 2. Reddit API ─────────────────────────────────────────────
print("\n[2] Reddit r/sweepstakes JSON API")
try:
    r = requests.get(
        'https://www.reddit.com/r/sweepstakes/new.json?limit=5',
        headers={**HEADERS, 'Accept': 'application/json'}, timeout=12
    )
    print(f"    Status: {r.status_code}")
    if r.status_code == 200:
        posts = r.json().get('data', {}).get('children', [])
        print(f"    ✓ Reddit OK — {len(posts)} posts found")
        if posts:
            print(f"      First: {posts[0]['data']['title'][:60]}")
    else:
        print(f"    ✗ Reddit returned {r.status_code}: {r.text[:100]}")
except Exception as e:
    print(f"    ✗ Reddit FAILED: {e}")

# ── 3. RSS Feeds ──────────────────────────────────────────────
feeds = [
    ('ContestGirl',       'https://www.contestgirl.com/feed/'),
    ('Sweeties Sweeps',   'https://www.sweetiessweeps.com/feed/'),
    ('Contest Queen',     'https://contestqueen.com/feed/'),
    ('Sweepstakes Lovers','https://sweepstakeslovers.com/feed/'),
]
print("\n[3] RSS Feeds")
working_feeds = []
for name, url in feeds:
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        ctype = r.headers.get('Content-Type','')
        if r.status_code == 200 and ('xml' in ctype or 'rss' in ctype or r.content[:5] in [b'<?xml', b'<rss ', b'<feed']):
            root = ET.fromstring(r.content)
            items = root.findall('.//item') or root.findall('.//{http://www.w3.org/2005/Atom}entry')
            print(f"    ✓ {name}: {len(items)} items")
            if items: working_feeds.append(name)
        else:
            print(f"    ✗ {name}: HTTP {r.status_code}, Content-Type: {ctype[:40]}")
    except Exception as e:
        print(f"    ✗ {name}: {str(e)[:60]}")

# ── 4. Oregon Lottery ─────────────────────────────────────────
print("\n[4] Oregon Lottery (requests only)")
try:
    r = requests.get('https://www.oregonlottery.org/games/scratch-its/remaining-prizes',
                     headers=HEADERS, timeout=12)
    print(f"    Status: {r.status_code}, Length: {len(r.content)} bytes")
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(r.text, 'html.parser')
    tables = soup.find_all('table')
    print(f"    Tables found: {len(tables)}")
    if tables:
        rows = tables[0].find_all('tr')
        print(f"    First table rows: {len(rows)}")
    else:
        print("    No tables — page is JS-rendered, needs Playwright")
except ImportError:
    print("    ✗ beautifulsoup4 not installed — run: pip install beautifulsoup4 lxml")
except Exception as e:
    print(f"    Error: {e}")

# ── Summary ───────────────────────────────────────────────────
print("\n" + "=" * 55)
print("  SUMMARY — paste this output into chat")
print("=" * 55)
