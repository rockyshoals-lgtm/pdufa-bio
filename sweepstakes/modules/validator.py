"""
validator.py — Check sweepstake URLs are still active and accepting entries.
"""
import requests
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                  ' (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}

DEAD_PHRASES = [
    'sweepstakes has ended', 'contest has ended', 'has closed',
    'no longer accepting', 'entry period has ended', 'this promotion has ended',
    'winner has been selected', 'giveaway ended', 'expired',
]


def check_url(url: str, timeout: int = 10) -> dict:
    """
    Returns {'alive': bool, 'status_code': int, 'reason': str}
    """
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout,
                         allow_redirects=True)
        if r.status_code >= 400:
            return {'alive': False, 'status_code': r.status_code,
                    'reason': f'HTTP {r.status_code}'}

        text_lower = r.text.lower()
        for phrase in DEAD_PHRASES:
            if phrase in text_lower:
                return {'alive': False, 'status_code': r.status_code,
                        'reason': f'Page contains: "{phrase}"'}

        return {'alive': True, 'status_code': r.status_code, 'reason': 'OK'}

    except requests.exceptions.ConnectionError:
        return {'alive': False, 'status_code': 0, 'reason': 'Connection error'}
    except requests.exceptions.Timeout:
        return {'alive': False, 'status_code': 0, 'reason': 'Timeout'}
    except Exception as e:
        return {'alive': False, 'status_code': 0, 'reason': str(e)[:80]}


def validate_all(sweepstakes: list) -> list:
    """
    Accepts list of dicts with 'id','url'. Returns list with validation results added.
    """
    results = []
    for s in sweepstakes:
        result = check_url(s['url'])
        results.append({
            'id': s['id'],
            'url': s['url'],
            'alive': result['alive'],
            'reason': result['reason'],
            'checked_at': datetime.now().isoformat(),
        })
        logger.info(f"  [{('✓' if result['alive'] else '✗')}] {s.get('name','?')} — {result['reason']}")
    return results
