#!/usr/bin/env python3
"""
ODIN Exit Trigger Engine v3.0
=============================
Dynamic Exit Logic for Options Positions

Replaces mechanical T-7 exit with intelligent triggers:
- Trigger A: Profit-Taking (40%+ gain by T-21)
- Trigger B: IV Plateau (< 8 pts gain in 7 days)
- Trigger C: Earnings Conflict (earnings before PDUFA)
- Trigger D: Liquidity Cliff (bid-ask > 3%)
- Trigger E: Stock Drift Achieved (15%+ move in direction)
- Trigger F: Trailing Stop (-25% from peak)

Usage:
    engine = ExitTriggerEngine()
    triggers = engine.evaluate_all(position)
    
    if any(t.triggered for t in triggers):
        # EXIT POSITION
"""

import json
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from enum import Enum


class TriggerType(Enum):
    PROFIT_TAKING = "PROFIT_TAKING"
    IV_PLATEAU = "IV_PLATEAU"
    EARNINGS_CONFLICT = "EARNINGS_CONFLICT"
    LIQUIDITY_CLIFF = "LIQUIDITY_CLIFF"
    STOCK_DRIFT = "STOCK_DRIFT"
    TRAILING_STOP = "TRAILING_STOP"
    STANDARD_T7 = "STANDARD_T7"
    HOLIDAY_BUFFER = "HOLIDAY_BUFFER"


class ExitAction(Enum):
    HOLD = "HOLD"
    SELL_50_PCT = "SELL_50_PCT"
    SELL_75_PCT = "SELL_75_PCT"
    SELL_100_PCT = "SELL_100_PCT"
    URGENT_EXIT = "URGENT_EXIT"


@dataclass
class Position:
    """Options position data"""
    ticker: str
    entry_date: datetime
    entry_price: float
    entry_iv: float
    entry_stock_price: float
    
    current_price: float
    current_iv: float
    current_stock_price: float
    current_bid: float
    current_ask: float
    
    pdufa_date: datetime
    contracts: int
    
    # Historical tracking
    peak_price: float = None
    iv_7_days_ago: float = None
    
    def __post_init__(self):
        if self.peak_price is None:
            self.peak_price = max(self.entry_price, self.current_price)
    
    @property
    def days_to_pdufa(self) -> int:
        return (self.pdufa_date - datetime.now()).days
    
    @property
    def pnl_pct(self) -> float:
        return (self.current_price - self.entry_price) / self.entry_price
    
    @property
    def iv_change(self) -> float:
        return self.current_iv - self.entry_iv
    
    @property
    def stock_change_pct(self) -> float:
        return (self.current_stock_price - self.entry_stock_price) / self.entry_stock_price
    
    @property
    def bid_ask_spread_pct(self) -> float:
        mid = (self.current_bid + self.current_ask) / 2
        if mid == 0:
            return 1.0
        return (self.current_ask - self.current_bid) / mid
    
    @property
    def drawdown_from_peak(self) -> float:
        if self.peak_price == 0:
            return 0
        return (self.peak_price - self.current_price) / self.peak_price


@dataclass
class TriggerResult:
    """Result of a trigger evaluation"""
    trigger_type: TriggerType
    triggered: bool
    action: ExitAction
    urgency: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    sell_pct: float  # 0-100%
    reason: str
    details: Dict
    
    def to_dict(self) -> Dict:
        return {
            "trigger": self.trigger_type.value,
            "triggered": self.triggered,
            "action": self.action.value,
            "urgency": self.urgency,
            "sell_pct": self.sell_pct,
            "reason": self.reason,
            "details": self.details
        }


class ExitTriggerEngine:
    """
    ODIN Exit Trigger Engine
    
    Evaluates 6+ dynamic triggers to determine optimal exit timing.
    Replaces mechanical T-7 exit with intelligent decision-making.
    """
    
    # Holiday dates that require buffer (US markets)
    HOLIDAY_BUFFERS = {
        "thanksgiving": {"month": 11, "week": 4, "day": 3},  # 4th Thursday Nov
        "christmas": {"month": 12, "day": 25},
        "new_years": {"month": 1, "day": 1},
        "july_4": {"month": 7, "day": 4},
        "good_friday": None,  # Variable, check separately
    }
    
    # Thresholds
    PROFIT_TAKING_THRESHOLD = 0.40  # 40% gain
    PROFIT_TAKING_DAYS = 21  # By T-21
    IV_PLATEAU_THRESHOLD = 8  # < 8 points gain in 7 days
    LIQUIDITY_CLIFF_THRESHOLD = 0.03  # 3% bid-ask spread
    STOCK_DRIFT_THRESHOLD = 0.15  # 15% stock move
    TRAILING_STOP_THRESHOLD = 0.25  # 25% from peak
    STANDARD_EXIT_DAYS = 7  # T-7
    HOLIDAY_BUFFER_DAYS = 10  # T-10 near holidays
    
    def __init__(self, earnings_dates: Dict[str, datetime] = None):
        """
        Initialize exit trigger engine
        
        Args:
            earnings_dates: Dict mapping ticker to earnings date
        """
        self.earnings_dates = earnings_dates or {}
    
    def evaluate_all(self, position: Position) -> List[TriggerResult]:
        """
        Evaluate all exit triggers for a position
        
        Args:
            position: Current position data
            
        Returns:
            List of TriggerResult for each trigger type
        """
        triggers = []
        
        # Trigger A: Profit-Taking
        triggers.append(self._check_profit_taking(position))
        
        # Trigger B: IV Plateau
        triggers.append(self._check_iv_plateau(position))
        
        # Trigger C: Earnings Conflict
        triggers.append(self._check_earnings_conflict(position))
        
        # Trigger D: Liquidity Cliff
        triggers.append(self._check_liquidity_cliff(position))
        
        # Trigger E: Stock Drift Achieved
        triggers.append(self._check_stock_drift(position))
        
        # Trigger F: Trailing Stop
        triggers.append(self._check_trailing_stop(position))
        
        # Trigger G: Standard T-7 Exit
        triggers.append(self._check_standard_exit(position))
        
        # Trigger H: Holiday Buffer
        triggers.append(self._check_holiday_buffer(position))
        
        return triggers
    
    def get_recommendation(self, position: Position) -> Dict:
        """
        Get overall exit recommendation based on all triggers
        
        Args:
            position: Current position data
            
        Returns:
            Dict with recommendation and reasoning
        """
        triggers = self.evaluate_all(position)
        
        # Sort by urgency
        urgency_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        triggered = [t for t in triggers if t.triggered]
        triggered.sort(key=lambda x: urgency_order.get(x.urgency, 4))
        
        if not triggered:
            return {
                "action": "HOLD",
                "sell_pct": 0,
                "reason": "No triggers active",
                "days_to_pdufa": position.days_to_pdufa,
                "current_pnl_pct": round(position.pnl_pct * 100, 1),
                "triggers_evaluated": len(triggers),
                "next_check_date": self._get_next_check_date(position)
            }
        
        # Take highest urgency trigger
        primary = triggered[0]
        
        # Aggregate if multiple triggers
        total_sell_pct = min(100, sum(t.sell_pct for t in triggered))
        
        return {
            "action": primary.action.value,
            "sell_pct": total_sell_pct,
            "primary_trigger": primary.trigger_type.value,
            "primary_reason": primary.reason,
            "urgency": primary.urgency,
            "all_triggered": [t.to_dict() for t in triggered],
            "days_to_pdufa": position.days_to_pdufa,
            "current_pnl_pct": round(position.pnl_pct * 100, 1)
        }
    
    def _check_profit_taking(self, position: Position) -> TriggerResult:
        """
        Trigger A: Profit-Taking at T-21
        
        If up 40%+ by T-21, sell 50% to lock in gains.
        """
        triggered = False
        action = ExitAction.HOLD
        urgency = "LOW"
        sell_pct = 0
        reason = "No profit-taking trigger"
        
        pnl = position.pnl_pct
        days = position.days_to_pdufa
        
        if pnl >= self.PROFIT_TAKING_THRESHOLD and days <= self.PROFIT_TAKING_DAYS:
            triggered = True
            action = ExitAction.SELL_50_PCT
            urgency = "MEDIUM"
            sell_pct = 50
            reason = f"Up {pnl*100:.0f}% at T-{days}. Lock in gains."
        
        return TriggerResult(
            trigger_type=TriggerType.PROFIT_TAKING,
            triggered=triggered,
            action=action,
            urgency=urgency,
            sell_pct=sell_pct,
            reason=reason,
            details={
                "current_pnl_pct": round(pnl * 100, 1),
                "threshold_pct": self.PROFIT_TAKING_THRESHOLD * 100,
                "days_to_pdufa": days,
                "trigger_days": self.PROFIT_TAKING_DAYS
            }
        )
    
    def _check_iv_plateau(self, position: Position) -> TriggerResult:
        """
        Trigger B: IV Plateau
        
        If IV has risen less than 8 points in last 7 days, exit 100%.
        Market has priced in the event; further Vega gains unlikely.
        """
        triggered = False
        action = ExitAction.HOLD
        urgency = "LOW"
        sell_pct = 0
        reason = "IV still ramping"
        
        if position.iv_7_days_ago is None:
            return TriggerResult(
                trigger_type=TriggerType.IV_PLATEAU,
                triggered=False,
                action=ExitAction.HOLD,
                urgency="LOW",
                sell_pct=0,
                reason="Insufficient IV history",
                details={"note": "Need 7-day IV history"}
            )
        
        iv_gain_7d = (position.current_iv - position.iv_7_days_ago) * 100
        days = position.days_to_pdufa
        
        # Only trigger if within exit window (T-21 to T-7)
        if days <= 21 and iv_gain_7d < self.IV_PLATEAU_THRESHOLD:
            triggered = True
            action = ExitAction.SELL_100_PCT
            urgency = "HIGH"
            sell_pct = 100
            reason = f"IV plateau: Only +{iv_gain_7d:.1f} pts in 7 days. Event priced in."
        
        return TriggerResult(
            trigger_type=TriggerType.IV_PLATEAU,
            triggered=triggered,
            action=action,
            urgency=urgency,
            sell_pct=sell_pct,
            reason=reason,
            details={
                "iv_gain_7d_pts": round(iv_gain_7d, 1),
                "threshold_pts": self.IV_PLATEAU_THRESHOLD,
                "current_iv": round(position.current_iv * 100, 1),
                "iv_7d_ago": round(position.iv_7_days_ago * 100, 1)
            }
        )
    
    def _check_earnings_conflict(self, position: Position) -> TriggerResult:
        """
        Trigger C: Earnings Conflict
        
        If company reports earnings between T-14 and T-3, exit at T-14.
        Earnings IV crush will damage position.
        """
        triggered = False
        action = ExitAction.HOLD
        urgency = "LOW"
        sell_pct = 0
        reason = "No earnings conflict"
        
        earnings_date = self.earnings_dates.get(position.ticker)
        
        if earnings_date:
            days_to_earnings = (earnings_date - datetime.now()).days
            days_to_pdufa = position.days_to_pdufa
            
            # Earnings between T-14 and T-3
            if 3 <= days_to_earnings <= 14 and days_to_earnings < days_to_pdufa:
                triggered = True
                action = ExitAction.SELL_100_PCT
                urgency = "HIGH"
                sell_pct = 100
                reason = f"Earnings in {days_to_earnings} days before PDUFA. Exit to avoid double-event risk."
        
        return TriggerResult(
            trigger_type=TriggerType.EARNINGS_CONFLICT,
            triggered=triggered,
            action=action,
            urgency=urgency,
            sell_pct=sell_pct,
            reason=reason,
            details={
                "earnings_date": earnings_date.isoformat() if earnings_date else None,
                "pdufa_date": position.pdufa_date.isoformat()
            }
        )
    
    def _check_liquidity_cliff(self, position: Position) -> TriggerResult:
        """
        Trigger D: Liquidity Cliff
        
        If bid-ask spread > 3%, exit immediately.
        Slippage will kill Vega gains on exit.
        """
        triggered = False
        action = ExitAction.HOLD
        urgency = "LOW"
        sell_pct = 0
        reason = "Liquidity adequate"
        
        spread = position.bid_ask_spread_pct
        
        if spread > self.LIQUIDITY_CLIFF_THRESHOLD:
            triggered = True
            action = ExitAction.URGENT_EXIT
            urgency = "CRITICAL"
            sell_pct = 100
            reason = f"Liquidity cliff: Bid-ask spread {spread*100:.1f}%. Exit NOW."
        
        return TriggerResult(
            trigger_type=TriggerType.LIQUIDITY_CLIFF,
            triggered=triggered,
            action=action,
            urgency=urgency,
            sell_pct=sell_pct,
            reason=reason,
            details={
                "bid_ask_spread_pct": round(spread * 100, 2),
                "threshold_pct": self.LIQUIDITY_CLIFF_THRESHOLD * 100,
                "current_bid": position.current_bid,
                "current_ask": position.current_ask
            }
        )
    
    def _check_stock_drift(self, position: Position) -> TriggerResult:
        """
        Trigger E: Stock Drift Achieved
        
        If stock has moved 15%+ in expected direction, sell 50%.
        Lock in both delta and vega gains.
        """
        triggered = False
        action = ExitAction.HOLD
        urgency = "LOW"
        sell_pct = 0
        reason = "Stock within normal range"
        
        drift = position.stock_change_pct
        
        if abs(drift) >= self.STOCK_DRIFT_THRESHOLD:
            triggered = True
            action = ExitAction.SELL_50_PCT
            urgency = "MEDIUM"
            sell_pct = 50
            direction = "rallied" if drift > 0 else "dropped"
            reason = f"Stock {direction} {abs(drift)*100:.0f}%. Lock in delta + vega gains."
        
        return TriggerResult(
            trigger_type=TriggerType.STOCK_DRIFT,
            triggered=triggered,
            action=action,
            urgency=urgency,
            sell_pct=sell_pct,
            reason=reason,
            details={
                "stock_change_pct": round(drift * 100, 1),
                "threshold_pct": self.STOCK_DRIFT_THRESHOLD * 100,
                "entry_price": position.entry_stock_price,
                "current_price": position.current_stock_price
            }
        )
    
    def _check_trailing_stop(self, position: Position) -> TriggerResult:
        """
        Trigger F: Trailing Stop
        
        If position value drops 25% from peak, auto-sell.
        IV spike has reversed; preserve capital.
        """
        triggered = False
        action = ExitAction.HOLD
        urgency = "LOW"
        sell_pct = 0
        reason = "Within trailing stop range"
        
        drawdown = position.drawdown_from_peak
        
        if drawdown >= self.TRAILING_STOP_THRESHOLD:
            triggered = True
            action = ExitAction.SELL_100_PCT
            urgency = "HIGH"
            sell_pct = 100
            reason = f"Trailing stop: Position down {drawdown*100:.0f}% from peak. Preserve capital."
        
        return TriggerResult(
            trigger_type=TriggerType.TRAILING_STOP,
            triggered=triggered,
            action=action,
            urgency=urgency,
            sell_pct=sell_pct,
            reason=reason,
            details={
                "drawdown_pct": round(drawdown * 100, 1),
                "threshold_pct": self.TRAILING_STOP_THRESHOLD * 100,
                "peak_price": position.peak_price,
                "current_price": position.current_price
            }
        )
    
    def _check_standard_exit(self, position: Position) -> TriggerResult:
        """
        Trigger G: Standard T-7 Exit
        
        Default exit window: T-7 to T-5.
        Sell 75% of remaining position.
        """
        triggered = False
        action = ExitAction.HOLD
        urgency = "LOW"
        sell_pct = 0
        reason = f"T-{position.days_to_pdufa}: Not yet in exit window"
        
        days = position.days_to_pdufa
        
        if days <= self.STANDARD_EXIT_DAYS:
            triggered = True
            action = ExitAction.SELL_75_PCT
            urgency = "HIGH"
            sell_pct = 75
            reason = f"T-{days}: Standard exit window. Sell to avoid IV crush."
        
        return TriggerResult(
            trigger_type=TriggerType.STANDARD_T7,
            triggered=triggered,
            action=action,
            urgency=urgency,
            sell_pct=sell_pct,
            reason=reason,
            details={
                "days_to_pdufa": days,
                "exit_window_start": self.STANDARD_EXIT_DAYS
            }
        )
    
    def _check_holiday_buffer(self, position: Position) -> TriggerResult:
        """
        Trigger H: Holiday Buffer
        
        If PDUFA is within 2 weeks of major holiday, exit at T-10.
        Thin holiday trading destroys options.
        """
        triggered = False
        action = ExitAction.HOLD
        urgency = "LOW"
        sell_pct = 0
        reason = "No holiday conflict"
        
        # Check if PDUFA is near a holiday
        pdufa = position.pdufa_date
        days = position.days_to_pdufa
        
        holidays = [
            datetime(pdufa.year, 11, 28),  # Thanksgiving (approx)
            datetime(pdufa.year, 12, 25),  # Christmas
            datetime(pdufa.year, 1, 1),    # New Year
            datetime(pdufa.year, 7, 4),    # July 4
        ]
        
        near_holiday = False
        for holiday in holidays:
            delta = abs((pdufa - holiday).days)
            if delta <= 14:  # Within 2 weeks
                near_holiday = True
                break
        
        if near_holiday and days <= self.HOLIDAY_BUFFER_DAYS:
            triggered = True
            action = ExitAction.SELL_75_PCT
            urgency = "HIGH"
            sell_pct = 75
            reason = f"Holiday buffer: PDUFA near holiday. Exit at T-{days}."
        
        return TriggerResult(
            trigger_type=TriggerType.HOLIDAY_BUFFER,
            triggered=triggered,
            action=action,
            urgency=urgency,
            sell_pct=sell_pct,
            reason=reason,
            details={
                "pdufa_date": pdufa.isoformat(),
                "near_holiday": near_holiday,
                "buffer_days": self.HOLIDAY_BUFFER_DAYS
            }
        )
    
    def _get_next_check_date(self, position: Position) -> str:
        """Calculate next checkpoint date"""
        days = position.days_to_pdufa
        
        if days > 21:
            next_check = "T-21"
        elif days > 14:
            next_check = "T-14"
        elif days > 10:
            next_check = "T-10"
        elif days > 7:
            next_check = "T-7"
        else:
            next_check = "DAILY"
        
        return next_check


# ==================== MAIN ====================

if __name__ == "__main__":
    print("ODIN Exit Trigger Engine v3.0")
    print("=" * 50)
    
    # Example position
    position = Position(
        ticker="RCKT",
        entry_date=datetime(2026, 1, 26),
        entry_price=1.30,
        entry_iv=0.62,
        entry_stock_price=3.72,
        current_price=4.55,  # Simulated at T-21
        current_iv=0.95,
        current_stock_price=4.10,
        current_bid=4.40,
        current_ask=4.70,
        pdufa_date=datetime(2026, 3, 28),
        contracts=100,
        peak_price=4.80,
        iv_7_days_ago=0.85
    )
    
    print(f"\nPosition: {position.ticker}")
    print(f"  Entry: ${position.entry_price:.2f} on {position.entry_date.date()}")
    print(f"  Current: ${position.current_price:.2f}")
    print(f"  P&L: {position.pnl_pct*100:+.1f}%")
    print(f"  Days to PDUFA: T-{position.days_to_pdufa}")
    print(f"  Stock Change: {position.stock_change_pct*100:+.1f}%")
    print(f"  IV Change: {position.iv_change*100:+.1f} pts")
    print(f"  Drawdown from Peak: {position.drawdown_from_peak*100:.1f}%")
    
    # Create engine and evaluate
    engine = ExitTriggerEngine()
    
    print("\n" + "=" * 50)
    print("Trigger Evaluation:")
    print("-" * 50)
    
    triggers = engine.evaluate_all(position)
    for t in triggers:
        status = "🔴 TRIGGERED" if t.triggered else "⚪ inactive"
        print(f"  {t.trigger_type.value:20s} {status}")
        if t.triggered:
            print(f"      Action: {t.action.value}")
            print(f"      Urgency: {t.urgency}")
            print(f"      Sell %: {t.sell_pct}%")
            print(f"      Reason: {t.reason}")
    
    print("\n" + "=" * 50)
    print("Overall Recommendation:")
    rec = engine.get_recommendation(position)
    print(f"  Action: {rec['action']}")
    print(f"  Sell %: {rec['sell_pct']}%")
    if 'primary_trigger' in rec:
        print(f"  Primary Trigger: {rec['primary_trigger']}")
        print(f"  Reason: {rec['primary_reason']}")
    else:
        print(f"  Next Check: {rec.get('next_check_date', 'N/A')}")
