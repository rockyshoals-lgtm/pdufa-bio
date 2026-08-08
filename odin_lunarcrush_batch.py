#!/usr/bin/env python3
"""
ODIN LunarCrush Batch Enrichment Script
========================================
Queries all ODIN tickers at 10/minute rate limit.
Saves progress after each query (crash-safe).

Usage: python3 odin_lunarcrush_batch.py

Time estimate: ~28 minutes for 275 remaining tickers
"""

import requests
import json
import time
import sys
from datetime import datetime, timezone
from pathlib import Path

# Configuration
API_KEY = "wyy0sr5cpo91napnt6cz6rtynmkmurndcr9bbdtd"
CACHE_FILE = Path("lunarcrush_cache.json")  # Same directory as script
RATE_LIMIT = 10  # requests per minute
DELAY = 6.5  # seconds between requests (slightly over 6 to be safe)

# All 294 unique tickers from ODIN dataset
ALL_TICKERS = [
    'ABBV', 'ABCL', 'ABEO', 'ABOS', 'ACAD', 'ACOG', 'ADAP', 'ADCT', 'ADMA', 'ADMP',
    'ADPT', 'ADTX', 'AGEN', 'AGIO', 'AIM', 'AKBA', 'ALC', 'ALDX', 'ALKS', 'ALNY',
    'ALPMY', 'ALVO', 'AMGN', 'AMLX', 'AMPH', 'AMRN', 'AMRX', 'ANAB', 'ANIP', 'APLIF',
    'APLS', 'APLT', 'APRE', 'APTO', 'AQST', 'ARDX', 'ARGX', 'ARQT', 'ARWR', 'ASND',
    'ASRT', 'ATNXQ', 'ATRA', 'ATXI', 'AUPH', 'AUTL', 'AVDL', 'AXGN', 'AXSM', 'AZN',
    'BAYRY', 'BBIO', 'BCAB', 'BCLI', 'BCRX', 'BCTX', 'BFRI', 'BGNE', 'BHC', 'BHVN',
    'BIIB', 'BLCO', 'BLRX', 'BLUE', 'BMRN', 'BMY', 'BNTX', 'BPMC', 'BTAI', 'BYSI',
    'CALT', 'CAPR', 'CARM', 'CERS', 'CHRS', 'CKPT', 'CLPT', 'CLSD', 'CMND', 'CMPX',
    'CMRX', 'CNTX', 'COCP', 'CORT', 'CPIX', 'CPRX', 'CRMD', 'CRNX', 'CRSP', 'CSLLY',
    'CTXR', 'CVM', 'CYTK', 'DARE', 'DAWN', 'DBVT', 'DCPH', 'DCTH', 'DERM', 'DSNKY',
    'DVAX', 'EBS', 'EGRX', 'EIGR', 'ELVN', 'ENDP', 'ENSC', 'ENTA', 'EPZM', 'ESPR',
    'ETON', 'EVFM', 'EVOK', 'EWTX', 'EXAI', 'EXEL', 'FBIO', 'FENC', 'FGEN', 'FOLD',
    'GEHC', 'GERN', 'GILD', 'GKOS', 'GLPG', 'GLSI', 'GMAB', 'GMDA', 'GNFT', 'GOVX',
    'GRTX', 'GSK', 'HALO', 'HCM', 'HRMY', 'HRTX', 'HUMA', 'IBRX', 'IGXT', 'IMCR',
    'IMPL', 'INCY', 'INDV', 'INSM', 'INVA', 'IONS', 'IOVA', 'IPSEY', 'IRD', 'IRWD',
    'ITRM', 'IVVD', 'IXHL', 'JAGX', 'JAZZ', 'JNJ', 'KALA', 'KALV', 'KNSA', 'KPTI',
    'KRYS', 'KURA', 'LEGN', 'LENZ', 'LGND', 'LIAN', 'LLY', 'LNTH', 'LPCN', 'LQDA',
    'LUMO', 'LXRX', 'MACK', 'MCRB', 'MDGL', 'MDWD', 'MESO', 'MGNX', 'MIRA', 'MIRM',
    'MIST', 'MNKD', 'MNKKQ', 'MOLN', 'MRK', 'MRNA', 'MRNS', 'MRUS', 'NBIX', 'NERV',
    'NNVC', 'NOVN', 'NUVB', 'NVAX', 'NVCR', 'NVO', 'NVS', 'OCGN', 'OCUL', 'OGN',
    'OLMA', 'OMER', 'ONC', 'ONCY', 'ONVO', 'OPK', 'OPNT', 'OPTN', 'OTLK', 'OYST',
    'PBLA', 'PBYI', 'PCRX', 'PCSA', 'PDSB', 'PFE', 'PGEN', 'PHAR', 'PHAT', 'PHRRF',
    'PLUR', 'PLX', 'PRTA', 'PRTC', 'PTCT', 'PTHS', 'QTRX', 'QURE', 'RARE', 'RCKT',
    'RDHL', 'REGN', 'REPL', 'RHHBY', 'RIGL', 'RLFTF', 'RMTI', 'RNAZ', 'ROIV', 'RXRX',
    'RYTM', 'SAGE', 'SCLX', 'SCYX', 'SIGA', 'SLGL', 'SLNO', 'SNDX', 'SNY', 'SPPI',
    'SPRO', 'SPRY', 'SRPT', 'SRRK', 'SUPN', 'SWTX', 'SXTP', 'TAK', 'TARS', 'TBPH',
    'TCDA', 'TEVA', 'TGTX', 'TLX', 'TNXP', 'TRVN', 'TSVT', 'TVRD', 'TVTX', 'UNCY',
    'URGN', 'UTHR', 'VALN', 'VBIV', 'VCEL', 'VERU', 'VIR', 'VNDA', 'VRCA', 'VRTX',
    'VSTM', 'VTRS', 'VYNE', 'WHWK', 'WVE', 'XERS', 'XFOR', 'XNCR', 'XOMA', 'YMAB',
    'ZLAB', 'ZLDPF', 'ZVRA', 'ZYME'
]


def load_cache():
    """Load existing cache or return empty dict"""
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text())
        except:
            return {}
    return {}


def save_cache(cache):
    """Save cache to file"""
    CACHE_FILE.write_text(json.dumps(cache, indent=2))


def calculate_signals(data):
    """
    Calculate ODIN social signals from LunarCrush data
    
    S17: Social Sentiment (+0.03 bullish, -0.02 bearish)
    S18: Engagement Spike (+0.02 if 2x avg with bullish sentiment)
    S19: Social Silence (-0.01 if engagements < 30% of avg)
    S20: Smart Money Divergence (-0.02 if low galaxy + low sentiment)
    """
    sentiment = data.get('sentiment_score')
    galaxy = data.get('galaxy_score')
    engagements = data.get('engagements_24h') or 0
    eng_avg = data.get('engagements_daily_avg') or 1
    
    s17 = s18 = s19 = s20 = 0.0
    
    # S17: Social Sentiment
    if sentiment is not None:
        if sentiment >= 75:
            s17 = 0.03
        elif sentiment >= 70:
            s17 = 0.01
        elif sentiment <= 40:
            s17 = -0.02
        elif sentiment <= 50:
            s17 = -0.01
    
    # S18: Engagement Spike (with bullish sentiment)
    if eng_avg > 0 and engagements > 0:
        ratio = engagements / eng_avg
        if ratio >= 2.0 and sentiment and sentiment >= 70:
            s18 = 0.02
        elif ratio >= 3.0:  # Major spike even without strong sentiment
            s18 = 0.01
    
    # S19: Social Silence (bearish signal)
    if eng_avg > 0 and engagements > 0:
        if engagements < eng_avg * 0.3:
            s19 = -0.01
    
    # S20: Smart Money Divergence
    if galaxy is not None and sentiment is not None:
        if galaxy < 40 and sentiment < 50:
            s20 = -0.02
    
    total = round(s17 + s18 + s19 + s20, 2)
    
    if total >= 0.03:
        classification = "BULLISH"
    elif total <= -0.02:
        classification = "BEARISH"
    else:
        classification = "NEUTRAL"
    
    return {
        's17_social_sentiment': s17,
        's18_engagement_spike': s18,
        's19_social_silence': s19,
        's20_smart_money_divergence': s20,
        'social_total': total,
        'social_classification': classification
    }


def query_ticker(ticker):
    """Query LunarCrush API for a single ticker"""
    
    # Try with $ prefix first (stock format)
    url = f"https://lunarcrush.com/api4/public/topic/${ticker.lower()}/v1"
    
    try:
        response = requests.get(
            url,
            headers={"Authorization": f"Bearer {API_KEY}"},
            timeout=30
        )
        
        if response.status_code == 200:
            json_data = response.json()
            data = json_data.get('data', {})
            
            # Check if we got meaningful data
            has_data = data.get('sentiment') is not None or data.get('interactions_24h') is not None
            
            result = {
                'ticker': ticker,
                'query_timestamp': datetime.now(timezone.utc).isoformat(),
                'sentiment_score': data.get('sentiment'),
                'engagements_24h': data.get('interactions_24h'),
                'engagements_daily_avg': data.get('average_interactions'),
                'mentions_24h': data.get('posts_24h'),
                'mentions_daily_avg': data.get('average_posts'),
                'creators_24h': data.get('contributors_24h'),
                'creators_daily_avg': data.get('average_contributors'),
                'galaxy_score': data.get('galaxy_score'),
                'alt_rank': data.get('alt_rank'),
                'sentiment_delta_7d_pct': data.get('percent_change_sentiment_7d'),
                'engagements_delta_7d_pct': data.get('percent_change_interactions_7d'),
                'key_insight': None,
                'top_theme_bullish': None,
                'top_theme_bearish': None,
                'status': 'SUCCESS' if has_data else 'NO_DATA'
            }
            
            # Calculate ODIN signals
            signals = calculate_signals(result)
            result.update(signals)
            
            return result
            
        elif response.status_code == 429:
            return {'ticker': ticker, 'status': 'RATE_LIMITED', 'social_classification': 'NEUTRAL'}
        else:
            return {'ticker': ticker, 'status': f'HTTP_{response.status_code}', 'social_classification': 'NEUTRAL'}
            
    except requests.exceptions.Timeout:
        return {'ticker': ticker, 'status': 'TIMEOUT', 'social_classification': 'NEUTRAL'}
    except requests.exceptions.RequestException as e:
        return {'ticker': ticker, 'status': 'ERROR', 'error': str(e), 'social_classification': 'NEUTRAL'}
    except Exception as e:
        return {'ticker': ticker, 'status': 'ERROR', 'error': str(e), 'social_classification': 'NEUTRAL'}


def print_progress_bar(current, total, width=40):
    """Print a progress bar"""
    pct = current / total
    filled = int(width * pct)
    bar = '█' * filled + '░' * (width - filled)
    return f"[{bar}] {current}/{total} ({pct*100:.1f}%)"


def main():
    print("=" * 60)
    print("ODIN LunarCrush Batch Enrichment")
    print("=" * 60)
    
    # Load existing cache
    cache = load_cache()
    cached_tickers = set(cache.keys())
    
    # Determine remaining tickers
    remaining = [t for t in ALL_TICKERS if t not in cached_tickers]
    
    print(f"Total tickers:     {len(ALL_TICKERS)}")
    print(f"Already cached:    {len(cached_tickers)}")
    print(f"Remaining:         {len(remaining)}")
    print(f"Rate limit:        {RATE_LIMIT}/minute")
    print(f"Delay:             {DELAY}s between requests")
    print(f"Estimated time:    {len(remaining) * DELAY / 60:.1f} minutes")
    print("-" * 60)
    
    if not remaining:
        print("✓ All tickers already cached!")
        return
    
    # Confirm start
    print(f"Starting in 3 seconds... (Ctrl+C to cancel)")
    time.sleep(3)
    
    start_time = time.time()
    success_count = 0
    no_data_count = 0
    error_count = 0
    
    for i, ticker in enumerate(remaining, 1):
        # Query the ticker
        result = query_ticker(ticker)
        cache[ticker] = result
        
        # Track stats
        status = result.get('status', 'UNKNOWN')
        classification = result.get('social_classification', 'N/A')
        
        if status == 'SUCCESS':
            success_count += 1
            sentiment = result.get('sentiment_score', 'N/A')
            status_str = f"✓ {classification} (sent: {sentiment})"
        elif status == 'NO_DATA':
            no_data_count += 1
            status_str = "○ NO_DATA"
        else:
            error_count += 1
            status_str = f"✗ {status}"
        
        # Progress output
        progress = print_progress_bar(i, len(remaining), 30)
        elapsed = time.time() - start_time
        rate = i / elapsed * 60 if elapsed > 0 else 0
        eta = (len(remaining) - i) * DELAY / 60
        
        print(f"{progress} | {ticker:6s} | {status_str:20s} | ETA: {eta:.1f}m")
        
        # Save after each query (crash-safe)
        save_cache(cache)
        
        # Rate limit delay (except for last item)
        if i < len(remaining):
            time.sleep(DELAY)
    
    # Final summary
    elapsed_total = (time.time() - start_time) / 60
    print("-" * 60)
    print("COMPLETE!")
    print(f"Time elapsed:      {elapsed_total:.1f} minutes")
    print(f"Total cached:      {len(cache)}")
    print(f"This run:          {len(remaining)} queries")
    print(f"  - Success:       {success_count}")
    print(f"  - No Data:       {no_data_count}")
    print(f"  - Errors:        {error_count}")
    print("-" * 60)
    
    # Signal distribution
    classifications = {'BULLISH': 0, 'NEUTRAL': 0, 'BEARISH': 0}
    for data in cache.values():
        c = data.get('social_classification', 'NEUTRAL')
        if c in classifications:
            classifications[c] += 1
    
    print("Signal Distribution:")
    for cls, count in classifications.items():
        pct = count / len(cache) * 100
        print(f"  {cls:10s}: {count:3d} ({pct:.1f}%)")
    
    print("=" * 60)
    print(f"Cache saved to: {CACHE_FILE}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted! Progress has been saved.")
        sys.exit(0)
