"""
finder.py — RSS + Reddit discovery with age filter and expired-date filter.
"""
import requests, re, logging
from datetime import datetime, timedelta
from xml.etree import ElementTree as ET
from email.utils import parsedate_to_datetime

logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}

MAX_AGE_DAYS = 180  # skip RSS/Reddit posts older than this

RSS_FEEDS = [
    {'url': 'https://www.sweetiessweeps.com/feed/', 'source': 'Sweeties Sweeps'},
    {'url': 'https://contestqueen.com/feed/',       'source': 'Contest Queen'},
]


def parse_prize(s):
    if not s: return 0.0
    m = re.search(r'([\d,\.]+)\s*(million|billion)?', s.lower().replace('$','').replace(',',''))
    if not m: return 0.0
    try:
        val = float(m.group(1))
        if m.group(2) == 'million':  val *= 1_000_000
        elif m.group(2) == 'billion': val *= 1_000_000_000
        return val
    except: return 0.0


def parse_end_date(s):
    """Try multiple date formats. Returns ISO date string or ''."""
    if not s: return ''
    s = s.strip().rstrip('.,!?')
    formats = [
        '%m/%d/%Y', '%m/%d/%y', '%m-%d-%Y', '%m-%d-%y',
        '%B %d, %Y', '%b %d, %Y', '%B %d %Y', '%b %d %Y',
        '%d %B %Y', '%d %b %Y',
        '%Y-%m-%d', '%B %Y', '%b %Y',
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(s, fmt)
            # If year looks 2-digit and very old, bump it
            if dt.year < 2000:
                dt = dt.replace(year=dt.year + 2000)
            return dt.date().isoformat()
        except: continue
    return ''


def parse_pub_date(s):
    """Parse RFC822 RSS pubDate. Returns datetime or None."""
    if not s: return None
    try:
        return parsedate_to_datetime(s).replace(tzinfo=None)
    except:
        pass
    for fmt in ['%Y-%m-%dT%H:%M:%S', '%Y-%m-%d', '%a, %d %b %Y %H:%M:%S']:
        try: return datetime.strptime(s.split('+')[0].strip(), fmt)
        except: continue
    return None


def guess_frequency(text):
    t = text.lower()
    if any(w in t for w in ['daily','once per day','each day','every day']): return 'daily'
    if any(w in t for w in ['weekly','once per week','each week']):          return 'weekly'
    if any(w in t for w in ['monthly','once per month','each month']):       return 'monthly'
    return 'once'


def guess_category(text):
    t = text.lower()
    cats = {
        'Cash':          ['cash','gift card','prize money'],
        'Travel':        ['trip','travel','vacation','cruise','flight','hotel','resort'],
        'Home':          ['home','house','furniture','appliance','kitchen'],
        'Auto':          ['car','truck','vehicle','suv','motorcycle'],
        'Electronics':   ['iphone','ipad','laptop','tv','tech','gaming','ps5','xbox'],
        'Food & Bev':    ['food','restaurant','dining','wine','beer','coffee','grocery'],
        'Entertainment': ['ticket','concert','movie','show','theme park','disney','sports'],
    }
    for cat, keywords in cats.items():
        if any(k in t for k in keywords): return cat
    return 'General'


def extract_link(item, ns):
    """Try multiple ways to get an http URL from an RSS/Atom item."""
    candidates = []
    for link_el in list(item.findall('link')) + list(item.findall('atom:link', ns)):
        if link_el.text and link_el.text.strip().startswith('http'):
            candidates.append(link_el.text.strip())
        href = link_el.get('href', '')
        if href and href.startswith('http'):
            candidates.append(href)
    guid = item.find('guid')
    if guid is not None and guid.text and guid.text.strip().startswith('http'):
        candidates.append(guid.text.strip())
    return candidates[0] if candidates else None


def looks_like_sweepstakes(title, desc, url):
    """Heuristic filter — does this look like an actual enterable sweepstakes?"""
    title_l = (title or '').lower().strip()
    combined = f'{title} {desc}'.lower()

    # Exclusions — articles/tips/news rather than entry pages
    bad_starts = ['how to', 'how do', 'tips for', 'tips to', 'guide to', "guide for", 'best ',
                  'why ', 'what ', 'when ', 'where ', 'who ', 'should i',
                  'top 10', 'top 5', 'top 20', 'list of', 'review of', 'review:',
                  '5 ', '7 ', '10 ', 'the best', 'a guide', 'an overview']
    if any(title_l.startswith(s) for s in bad_starts):
        return False
    if title_l.endswith('?'):
        return False

    # Bad phrases anywhere — past-tense / news / opinion content
    bad_phrases = [
        'winner of', 'won the', 'has won', 'congratulations to',
        'results from', 'has ended', 'recap of', 'recap:',
        'tutorial', 'beginner', 'getting started', 'introduction to',
        'thoughts on', 'opinion', 'review',
        'sweepstakes 101', 'sweepstakes basics', 'sweepstakes tips',
        'how-to', 'discussion', 'megathread',
    ]
    if any(p in combined for p in bad_phrases):
        return False

    # Reddit self-posts that are clearly discussion (no external URL)
    if 'reddit.com' in url:
        bad_reddit_tags = ['help', 'advice', 'question', 'discuss', 'rant', 'vent',
                           'newbie', 'first', 'beginner']
        if any(t in title_l for t in bad_reddit_tags):
            return False

    # Inclusions — must have at least one signal it's an enterable contest
    good_signals = [
        'win a ', 'win an ', 'win the ', 'win $', 'win ',
        'giveaway', 'sweepstakes', 'sweeps ', 'contest',
        'enter to', 'enter for', 'enter the', 'enter our',
        'chance to win', 'chance at', 'opportunity to win',
        'prize pack', 'grand prize',
    ]
    if any(s in combined for s in good_signals):
        return True

    # Dollar amount alone isn't enough — could be an article about winnings
    return False
    candidates = []
    for link_el in list(item.findall('link')) + list(item.findall('atom:link', ns)):
        if link_el.text and link_el.text.strip().startswith('http'):
            candidates.append(link_el.text.strip())
        href = link_el.get('href', '')
        if href and href.startswith('http'):
            candidates.append(href)
    guid = item.find('guid')
    if guid is not None and guid.text and guid.text.strip().startswith('http'):
        candidates.append(guid.text.strip())
    return candidates[0] if candidates else None


def is_expired(end_date_iso, today=None):
    if not end_date_iso: return False
    try:
        end = datetime.strptime(end_date_iso, '%Y-%m-%d').date()
        return end < (today or datetime.now().date())
    except: return False


def scrape_rss(feed_url, source, log_cb=None, max_age_days=MAX_AGE_DAYS):
    def L(msg):
        if log_cb: log_cb(f'  [{source}] {msg}')
        logger.info(f'{source}: {msg}')

    found = []
    today = datetime.now().date()
    cutoff = datetime.now() - timedelta(days=max_age_days)

    try:
        r = requests.get(feed_url, headers=HEADERS, timeout=12)
        if r.status_code != 200:
            L(f'HTTP {r.status_code}'); return found

        root = ET.fromstring(r.content)
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        items = root.findall('.//item') or root.findall('.//atom:entry', ns)
        L(f'{len(items)} items in feed')

        skipped_notitle = skipped_nolink = skipped_old = skipped_expired = skipped_quality = 0
        errors_caught = []
        for item in items:
            try:
                # Title (explicit None check — ElementTree gotcha)
                title_el = item.find('title')
                if title_el is None: title_el = item.find('atom:title', ns)
                title = (title_el.text or '').strip() if title_el is not None else ''
                if not title or len(title) < 5:
                    skipped_notitle += 1; continue

                # Publication date — skip very old posts
                pub_el = item.find('pubDate')
                if pub_el is None: pub_el = item.find('published')
                if pub_el is None: pub_el = item.find('atom:published', ns)
                pub_dt = parse_pub_date(pub_el.text) if pub_el is not None else None
                if pub_dt and pub_dt < cutoff:
                    skipped_old += 1; continue

                link = extract_link(item, ns)
                if not link:
                    skipped_nolink += 1; continue

                desc_el = item.find('description')
                if desc_el is None: desc_el = item.find('summary')
                if desc_el is None: desc_el = item.find('{http://purl.org/rss/1.0/modules/content/}encoded')
                desc = re.sub(r'<[^>]+>', ' ', desc_el.text) if (desc_el is not None and desc_el.text) else ''

                combined = f'{title} {desc}'

                # Prize
                prize_match = re.search(r'\$[\d,]+(?:\.\d+)?(?:\s*(?:million|billion))?', combined, re.I)
                prize_str = prize_match.group(0) if prize_match else ''

                # End date — try several phrasings
                end_date = ''
                for pattern in [
                    r'(?:ends?|expires?|deadline|closes?|until)[:\s]+([A-Za-z]+\.?\s+\d{1,2},?\s+\d{2,4})',
                    r'(?:ends?|expires?|deadline|closes?|until)[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                    r'(?:ends?|expires?|deadline|closes?|until)[:\s]+(\d{1,2}[/-]\d{1,2})',
                ]:
                    m = re.search(pattern, combined, re.I)
                    if m:
                        end_date = parse_end_date(m.group(1).strip())
                        if end_date: break

                # Skip if it doesn't look like an actual sweepstakes
                if not looks_like_sweepstakes(title, desc, link):
                    skipped_quality = skipped_quality + 1
                    continue

                # Skip if explicitly expired
                if is_expired(end_date, today):
                    skipped_expired += 1; continue

                found.append({
                    'name':        title[:120],
                    'url':         link,
                    'prize_value': parse_prize(prize_str),
                    'prize_text':  prize_str,
                    'end_date':    end_date,
                    'pub_date':    pub_dt.isoformat() if pub_dt else '',
                    'frequency':   guess_frequency(combined),
                    'category':    guess_category(combined),
                    'source':      source,
                    'found_at':    datetime.now().isoformat(),
                })
            except Exception as e:
                errors_caught.append(f'{type(e).__name__}: {str(e)[:120]}')

        L(f'kept {len(found)} | skipped: {skipped_notitle} no-title, '
          f'{skipped_nolink} no-link, {skipped_old} too-old, {skipped_quality} not-a-sweepstake, {skipped_expired} expired, {len(errors_caught)} errors')
        for i, err in enumerate(errors_caught[:3]):
            L(f'  ERROR #{i+1}: {err}')
    except Exception as e:
        L(f'failed: {str(e)[:80]}')
    return found


def scrape_reddit(log_cb=None, max_age_days=MAX_AGE_DAYS):
    def L(msg):
        if log_cb: log_cb(f'  [r/sweepstakes] {msg}')
        logger.info(f'reddit: {msg}')

    found = []
    today = datetime.now().date()
    # No age filter for Reddit — let the quality filter and URL validation do the work

    try:
        r = requests.get(
            'https://www.reddit.com/r/sweepstakes/new.json?limit=50',
            headers={**HEADERS, 'Accept': 'application/json'}, timeout=12
        )
        if r.status_code != 200:
            L(f'HTTP {r.status_code}'); return found

        posts = r.json().get('data', {}).get('children', [])
        L(f'{len(posts)} posts returned')

        skipped = skipped_old = skipped_expired = skipped_quality = 0
        reddit_errors = []
        for post in posts:
            try:
                p = post.get('data', {})
                title = (p.get('title') or '').strip()
                created_utc = p.get('created_utc', 0)
                url_dest = p.get('url') or ''
                selftext = p.get('selftext') or ''

                # Skip age filter for Reddit — but skip clearly stale (>1 year)
                if created_utc and created_utc < (datetime.now().timestamp() - 365 * 86400):
                    skipped_old += 1; continue

                if not url_dest.startswith('http'):
                    permalink = p.get('permalink', '')
                    url_dest = 'https://www.reddit.com' + permalink if permalink else ''
                if not title or not url_dest:
                    skipped += 1; continue

                combined = f'{title} {selftext}'
                prize_match = re.search(r'\$[\d,]+(?:\.\d+)?(?:\s*(?:million|billion))?', combined, re.I)
                prize_str = prize_match.group(0) if prize_match else ''

                end_date = ''
                for pattern in [
                    r'(?:ends?|expires?|deadline|closes?|until)[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                    r'(?:ends?|expires?|deadline)\s+(\d{1,2}[/-]\d{1,2})',
                    r'\((\d{1,2}/\d{1,2}/\d{2,4})\)',
                ]:
                    m = re.search(pattern, combined, re.I)
                    if m:
                        end_date = parse_end_date(m.group(1).strip())
                        if end_date: break

                if is_expired(end_date, today):
                    skipped_expired += 1; continue

                # Quality filter — only actual sweepstakes
                if not looks_like_sweepstakes(title, selftext, url_dest):
                    skipped_quality += 1; continue

                found.append({
                    'name':        title[:120],
                    'url':         url_dest,
                    'prize_value': parse_prize(prize_str),
                    'prize_text':  prize_str,
                    'end_date':    end_date,
                    'pub_date':    datetime.fromtimestamp(created_utc).isoformat() if created_utc else '',
                    'frequency':   guess_frequency(combined),
                    'category':    guess_category(combined),
                    'source':      'r/sweepstakes',
                    'found_at':    datetime.now().isoformat(),
                })
            except Exception as e:
                reddit_errors.append(f'{type(e).__name__}: {str(e)[:120]}')

        L(f'kept {len(found)} | skipped: {skipped} bad, {skipped_old} too-old, {skipped_quality} not-a-sweepstake, {skipped_expired} expired, {len(reddit_errors)} errors')
        for i, err in enumerate(reddit_errors[:3]):
            L(f'  ERROR #{i+1}: {err}')
    except Exception as e:
        L(f'failed: {str(e)[:80]}')
    return found


def discover_all(existing_urls=None, log_cb=None):
    existing_urls = existing_urls or set()
    if log_cb: log_cb(f'  Known URLs: {len(existing_urls)} (max age: {MAX_AGE_DAYS} days)')

    all_found = []
    for feed in RSS_FEEDS:
        all_found.extend(scrape_rss(feed['url'], feed['source'], log_cb=log_cb))
    all_found.extend(scrape_reddit(log_cb=log_cb))

    if log_cb: log_cb(f'  Total fresh items: {len(all_found)}')

    seen, unique = set(), []
    dup_dedup = dup_existing = 0
    for item in all_found:
        u = item['url']
        if u in seen: dup_dedup += 1
        elif u in existing_urls: dup_existing += 1
        else: seen.add(u); unique.append(item)

    if log_cb: log_cb(f'  After dedup: {len(unique)} new ({dup_dedup} dupes, {dup_existing} already known)')
    unique.sort(key=lambda x: x.get('prize_value', 0), reverse=True)
    return unique


def validate_pending(discovered_items, log_cb=None):
    """
    Re-validate URLs in the pending discovered queue.
    Returns list of ids to remove (dead URLs, expired by date, or not-a-sweepstake).
    """
    def L(msg):
        if log_cb: log_cb(f'  [Cleanup] {msg}')

    from modules.validator import check_url
    today = datetime.now().date()
    to_remove = []
    checked = dead = expired = noise = 0

    for item in discovered_items:
        # Quality filter — content doesn't look like an actual sweepstakes
        if not looks_like_sweepstakes(item.get('name',''), '', item.get('url','')):
            to_remove.append(item['id']); noise += 1; continue

        # Check parsed end_date first
        if is_expired(item.get('end_date'), today):
            to_remove.append(item['id']); expired += 1; continue

        # Check the URL
        result = check_url(item['url'], timeout=8)
        checked += 1
        if not result['alive']:
            to_remove.append(item['id']); dead += 1

    L(f'Checked {checked} URLs — {dead} dead, {expired} expired, {noise} not-sweepstakes — removing {len(to_remove)} total')
    return to_remove
