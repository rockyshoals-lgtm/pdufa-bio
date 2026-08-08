"""
ODIN Regime Detection Module
==============================
Detects biotech market regime (BULL/NORMAL/BEAR/CRISIS) to adjust position sizing.

Validated finding (Spec §3.2): Strategy shows near-zero or negative returns in 
bear markets (2021-2022). Regime detection should reduce position sizing during 
broad biotech drawdowns.

Regime multipliers (from Spec §10.3):
  BULL:    1.2x
  NORMAL:  1.0x
  BEAR:    0.5x
  CRISIS:  0.0x (no trades)

Signals used:
  1. XBI (SPDR S&P Biotech ETF) 50/200 day moving averages
  2. XBI drawdown from 52-week high
  3. XBI 30-day momentum
  4. VIX level (overall market stress)
"""

from datetime import datetime
from typing import Dict, Optional


def detect_regime_from_prices(
    xbi_price: float,
    xbi_50ma: float,
    xbi_200ma: float,
    xbi_52wk_high: float,
    vix: Optional[float] = None,
) -> Dict:
    """
    Detect biotech market regime from XBI technical data.

    Args:
        xbi_price: Current XBI price
        xbi_50ma: 50-day moving average
        xbi_200ma: 200-day moving average
        xbi_52wk_high: 52-week high
        vix: VIX level (optional, for crisis detection)

    Returns:
        dict with regime, confidence, multiplier, signals
    """
    signals = {}

    # Signal 1: Price vs MAs (death cross / golden cross)
    above_50 = xbi_price > xbi_50ma
    above_200 = xbi_price > xbi_200ma
    golden_cross = xbi_50ma > xbi_200ma  # 50MA above 200MA

    signals['price_above_50ma'] = above_50
    signals['price_above_200ma'] = above_200
    signals['golden_cross'] = golden_cross

    # Signal 2: Drawdown from 52-week high
    drawdown = (xbi_price / xbi_52wk_high) - 1.0 if xbi_52wk_high > 0 else 0
    signals['drawdown_from_52wk'] = round(drawdown, 4)

    # Signal 3: 50MA slope (approximated by price vs 50MA)
    ma_spread = (xbi_50ma / xbi_200ma) - 1.0 if xbi_200ma > 0 else 0
    signals['ma_spread'] = round(ma_spread, 4)

    # Signal 4: VIX
    vix_elevated = (vix or 20) > 30
    vix_crisis = (vix or 20) > 40
    signals['vix'] = vix
    signals['vix_elevated'] = vix_elevated

    # === Regime Classification ===
    # CRISIS: Deep drawdown + death cross + high VIX
    if drawdown < -0.30 and not golden_cross and vix_crisis:
        regime = 'CRISIS'
        confidence = 0.9
    # BEAR: Death cross + significant drawdown
    elif drawdown < -0.15 and not golden_cross:
        regime = 'BEAR'
        confidence = 0.8
    elif not above_200 and not golden_cross:
        regime = 'BEAR'
        confidence = 0.7
    # BULL: Golden cross + near highs
    elif golden_cross and above_50 and drawdown > -0.05:
        regime = 'BULL'
        confidence = 0.8
    elif golden_cross and above_200 and drawdown > -0.10:
        regime = 'BULL'
        confidence = 0.7
    # NORMAL: Everything else
    else:
        regime = 'NORMAL'
        confidence = 0.6

    REGIME_MULTS = {'BULL': 1.2, 'NORMAL': 1.0, 'BEAR': 0.5, 'CRISIS': 0.0}

    return {
        'regime': regime,
        'confidence': confidence,
        'multiplier': REGIME_MULTS[regime],
        'signals': signals,
    }


def fetch_regime_live() -> Dict:
    """
    Fetch current biotech regime using yfinance.
    Returns regime dict or NORMAL default on failure.
    """
    try:
        import yfinance as yf

        xbi = yf.Ticker("XBI")
        hist = xbi.history(period="1y", auto_adjust=True)

        if hist is None or len(hist) < 200:
            return {'regime': 'NORMAL', 'confidence': 0.3, 'multiplier': 1.0,
                    'signals': {'error': 'insufficient XBI history'}}

        closes = hist['Close']
        xbi_price = float(closes.iloc[-1])
        xbi_50ma = float(closes.iloc[-50:].mean())
        xbi_200ma = float(closes.mean())  # ~200 trading days in 1y
        xbi_52wk_high = float(closes.max())

        # Try to get VIX
        vix = None
        try:
            vix_ticker = yf.Ticker("^VIX")
            vix_info = vix_ticker.info or {}
            vix = vix_info.get('regularMarketPrice') or vix_info.get('previousClose')
        except Exception:
            pass

        result = detect_regime_from_prices(
            xbi_price=xbi_price,
            xbi_50ma=xbi_50ma,
            xbi_200ma=xbi_200ma,
            xbi_52wk_high=xbi_52wk_high,
            vix=vix,
        )

        result['xbi_price'] = xbi_price
        result['xbi_50ma'] = round(xbi_50ma, 2)
        result['xbi_200ma'] = round(xbi_200ma, 2)
        result['xbi_52wk_high'] = round(xbi_52wk_high, 2)

        return result

    except Exception as e:
        return {
            'regime': 'NORMAL',
            'confidence': 0.3,
            'multiplier': 1.0,
            'signals': {'error': str(e)},
        }


if __name__ == '__main__':
    result = fetch_regime_live()
    import json
    print(json.dumps(result, indent=2, default=str))
