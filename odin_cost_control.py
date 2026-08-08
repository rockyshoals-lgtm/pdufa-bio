"""
ODIN Multi-AI Cost Monitoring & Control System
Autonomous budget management with real-time throttling
"""

import json
import asyncio
from datetime import datetime, timedelta
from enum import Enum
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple

class SpendingLevel(Enum):
    """Predefined spending profiles"""
    MINIMAL = "minimal"          # $15/day - testing only
    CONSERVATIVE = "conservative" # $50/day - light monitoring
    MODERATE = "moderate"         # $145/day - daily operations
    AGGRESSIVE = "aggressive"     # $465/day - full production
    CUSTOM = "custom"             # User-defined limits

class OdinCostController:
    """
    Master cost control system for all 4 AI APIs
    Tracks spending, enforces budgets, throttles API calls
    """
    
    def __init__(self, config_file: str = "odin_budget_config.json"):
        self.config_file = config_file
        self.db_file = "odin_spend_tracking.db"
        
        # Load or create config
        self.config = self._load_config()
        
        # Initialize database
        self._init_database()
        
        # Real-time tracking
        self.current_day_spend = 0.0
        self.current_week_spend = 0.0
        self.current_month_spend = 0.0
        self.daily_requests = {}  # Track per-AI requests today
        
        # API pricing (updated Jan 2026)
        self.pricing = {
            "openai": {
                "gpt4o": {"input": 2.50, "output": 10.00},  # per 1M tokens
                "gpt4_turbo": {"input": 10.00, "output": 30.00},
            },
            "claude": {
                "sonnet": {"input": 3.00, "output": 15.00},  # per 1M tokens
                "opus": {"input": 15.00, "output": 75.00},
            },
            "gemini": {
                "pro_25": {"input": 1.25, "output": 10.00},  # per 1M tokens
                "flash": {"input": 0.075, "output": 0.30},
            },
            "perplexity": {
                "sonar_pro": {"input": 3.00, "output": 15.00},  # per 1M tokens
                "search_request": 0.018,  # per request
            }
        }
        
        print(f"✅ ODIN Cost Controller initialized")
        print(f"   Budget Level: {self.config['spending_level']}")
        print(f"   Daily Limit: ${self.config['daily_limit']:.2f}")
        print(f"   Weekly Limit: ${self.config['weekly_limit']:.2f}")
        print(f"   Monthly Limit: ${self.config['monthly_limit']:.2f}")
    
    def _load_config(self) -> Dict:
        """Load budget config or create default"""
        if Path(self.config_file).exists():
            with open(self.config_file, 'r') as f:
                return json.load(f)
        else:
            default_config = {
                "spending_level": "moderate",
                "daily_limit": 145.00,
                "weekly_limit": 1015.00,
                "monthly_limit": 4350.00,
                "alert_threshold": 0.80,  # Alert at 80% of budget
                "auto_throttle": True,  # Pause calls if over budget
                "ai_daily_limits": {
                    "openai": 50.00,
                    "claude": 40.00,
                    "gemini": 20.00,
                    "perplexity": 35.00,
                },
                "enabled_ais": {
                    "openai": True,
                    "claude": True,
                    "gemini": True,
                    "perplexity": True,
                },
                "task_priority": {
                    "pdufa_monitoring": 1,  # Highest priority - must run
                    "options_analysis": 2,
                    "insider_detection": 3,
                    "catalyst_confirmation": 4,
                    "thesis_updates": 5,  # Lowest priority - cut first
                },
                "last_reset": {
                    "daily": datetime.now().isoformat(),
                    "weekly": datetime.now().isoformat(),
                    "monthly": datetime.now().isoformat(),
                }
            }
            self._save_config(default_config)
            return default_config
    
    def _save_config(self, config: Dict):
        """Persist config to file"""
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)
    
    def _init_database(self):
        """Create SQLite database for immutable spend tracking"""
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        
        # Main spend log
        c.execute('''
            CREATE TABLE IF NOT EXISTS spend_log (
                id INTEGER PRIMARY KEY,
                timestamp TEXT,
                ai_platform TEXT,
                model TEXT,
                task_type TEXT,
                input_tokens INTEGER,
                output_tokens INTEGER,
                search_requests INTEGER,
                cost REAL,
                status TEXT
            )
        ''')
        
        # Daily summaries
        c.execute('''
            CREATE TABLE IF NOT EXISTS daily_summary (
                date TEXT PRIMARY KEY,
                openai_cost REAL,
                claude_cost REAL,
                gemini_cost REAL,
                perplexity_cost REAL,
                total_cost REAL,
                api_calls INTEGER
            )
        ''')
        
        # Budget alerts
        c.execute('''
            CREATE TABLE IF NOT EXISTS budget_alerts (
                id INTEGER PRIMARY KEY,
                timestamp TEXT,
                alert_type TEXT,
                message TEXT,
                current_spend REAL,
                limit_exceeded REAL,
                action_taken TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def set_spending_level(self, level: str):
        """
        Quick budget presets
        
        Usage:
            controller.set_spending_level("aggressive")
            controller.set_spending_level("minimal")
        """
        presets = {
            "minimal": {
                "daily_limit": 15.00,
                "weekly_limit": 105.00,
                "monthly_limit": 450.00,
                "ai_daily_limits": {"openai": 5, "claude": 5, "gemini": 3, "perplexity": 2},
            },
            "conservative": {
                "daily_limit": 50.00,
                "weekly_limit": 350.00,
                "monthly_limit": 1500.00,
                "ai_daily_limits": {"openai": 15, "claude": 15, "gemini": 10, "perplexity": 10},
            },
            "moderate": {
                "daily_limit": 145.00,
                "weekly_limit": 1015.00,
                "monthly_limit": 4350.00,
                "ai_daily_limits": {"openai": 50, "claude": 40, "gemini": 20, "perplexity": 35},
            },
            "aggressive": {
                "daily_limit": 465.00,
                "weekly_limit": 3255.00,
                "monthly_limit": 14000.00,
                "ai_daily_limits": {"openai": 150, "claude": 120, "gemini": 60, "perplexity": 135},
            },
        }
        
        if level not in presets:
            print(f"❌ Unknown level: {level}. Use: {list(presets.keys())}")
            return False
        
        preset = presets[level]
        self.config["spending_level"] = level
        self.config["daily_limit"] = preset["daily_limit"]
        self.config["weekly_limit"] = preset["weekly_limit"]
        self.config["monthly_limit"] = preset["monthly_limit"]
        self.config["ai_daily_limits"] = preset["ai_daily_limits"]
        
        self._save_config(self.config)
        print(f"✅ Budget updated to {level.upper()}")
        print(f"   Daily: ${preset['daily_limit']:.2f}")
        print(f"   Weekly: ${preset['weekly_limit']:.2f}")
        print(f"   Monthly: ${preset['monthly_limit']:.2f}")
        return True
    
    def set_custom_budget(self, 
                         daily: Optional[float] = None,
                         weekly: Optional[float] = None,
                         monthly: Optional[float] = None,
                         ai_limits: Optional[Dict[str, float]] = None):
        """
        Set custom budget limits
        
        Usage:
            controller.set_custom_budget(
                daily=200,
                weekly=1200,
                monthly=5000,
                ai_limits={"openai": 75, "claude": 50, "gemini": 40, "perplexity": 35}
            )
        """
        if daily:
            self.config["daily_limit"] = daily
        if weekly:
            self.config["weekly_limit"] = weekly
        if monthly:
            self.config["monthly_limit"] = monthly
        if ai_limits:
            self.config["ai_daily_limits"].update(ai_limits)
        
        self.config["spending_level"] = "custom"
        self._save_config(self.config)
        
        print(f"✅ Custom budget set")
        print(f"   Daily: ${self.config['daily_limit']:.2f}")
        print(f"   Weekly: ${self.config['weekly_limit']:.2f}")
        print(f"   Monthly: ${self.config['monthly_limit']:.2f}")
        print(f"   Per-AI Daily: {self.config['ai_daily_limits']}")
    
    async def log_api_call(self, 
                           ai_platform: str,
                           model: str,
                           task_type: str,
                           input_tokens: int = 0,
                           output_tokens: int = 0,
                           search_requests: int = 0) -> Tuple[float, bool]:
        """
        Log API call and calculate cost
        Returns: (cost, was_allowed)
        
        Usage:
            cost, allowed = await controller.log_api_call(
                ai_platform="openai",
                model="gpt4o",
                task_type="pdufa_monitoring",
                input_tokens=5000,
                output_tokens=2000
            )
            if not allowed:
                print("Budget limit reached, call blocked")
        """
        
        # Calculate cost
        cost = self._calculate_cost(ai_platform, model, input_tokens, output_tokens, search_requests)
        
        # Check if within limits BEFORE executing
        allowed = await self._check_budget_before_call(ai_platform, cost)
        
        # Log regardless (for audit trail)
        status = "allowed" if allowed else "blocked"
        
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute('''
            INSERT INTO spend_log 
            (timestamp, ai_platform, model, task_type, input_tokens, output_tokens, search_requests, cost, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            ai_platform,
            model,
            task_type,
            input_tokens,
            output_tokens,
            search_requests,
            cost,
            status
        ))
        conn.commit()
        conn.close()
        
        # Update in-memory tracking
        if allowed:
            self.current_day_spend += cost
            self.current_week_spend += cost
            self.current_month_spend += cost
            if ai_platform not in self.daily_requests:
                self.daily_requests[ai_platform] = 0
            self.daily_requests[ai_platform] += 1
        
        return cost, allowed
    
    def _calculate_cost(self, 
                       ai_platform: str,
                       model: str,
                       input_tokens: int,
                       output_tokens: int,
                       search_requests: int) -> float:
        """Calculate cost for an API call"""
        cost = 0.0
        
        if ai_platform == "openai":
            pricing = self.pricing["openai"].get(model, self.pricing["openai"]["gpt4o"])
            cost = (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1_000_000
        
        elif ai_platform == "claude":
            pricing = self.pricing["claude"].get(model, self.pricing["claude"]["sonnet"])
            cost = (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1_000_000
        
        elif ai_platform == "gemini":
            pricing = self.pricing["gemini"].get(model, self.pricing["gemini"]["pro_25"])
            cost = (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1_000_000
        
        elif ai_platform == "perplexity":
            token_pricing = self.pricing["perplexity"]["sonar_pro"]
            token_cost = (input_tokens * token_pricing["input"] + output_tokens * token_pricing["output"]) / 1_000_000
            search_cost = search_requests * self.pricing["perplexity"]["search_request"]
            cost = token_cost + search_cost
        
        return cost
    
    async def _check_budget_before_call(self, ai_platform: str, cost: float) -> bool:
        """
        Check if API call is within budget
        Returns: True if allowed, False if blocked
        """
        
        # Check daily limit
        if self.current_day_spend + cost > self.config["daily_limit"]:
            if self.config["auto_throttle"]:
                await self._log_alert(
                    "daily_limit_exceeded",
                    f"Daily budget limit would be exceeded: ${self.current_day_spend + cost:.2f} > ${self.config['daily_limit']:.2f}",
                    self.current_day_spend + cost,
                    self.config["daily_limit"],
                    "blocked_call"
                )
                return False
        
        # Check per-AI daily limit
        ai_limit = self.config["ai_daily_limits"].get(ai_platform, float('inf'))
        daily_ai_spend = self._get_ai_daily_spend(ai_platform)
        
        if daily_ai_spend + cost > ai_limit:
            if self.config["auto_throttle"]:
                await self._log_alert(
                    "ai_limit_exceeded",
                    f"{ai_platform.upper()} daily limit exceeded: ${daily_ai_spend + cost:.2f} > ${ai_limit:.2f}",
                    daily_ai_spend + cost,
                    ai_limit,
                    "blocked_call"
                )
                return False
        
        # Check alert threshold (warning, not blocking)
        if self.current_day_spend + cost > self.config["daily_limit"] * self.config["alert_threshold"]:
            await self._log_alert(
                "budget_warning",
                f"Approaching daily budget (80%): ${self.current_day_spend + cost:.2f} of ${self.config['daily_limit']:.2f}",
                self.current_day_spend + cost,
                self.config["daily_limit"] * self.config["alert_threshold"],
                "warning_issued"
            )
        
        return True
    
    def _get_ai_daily_spend(self, ai_platform: str) -> float:
        """Get today's spending for specific AI"""
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        
        today = datetime.now().date().isoformat()
        c.execute('''
            SELECT SUM(cost) FROM spend_log 
            WHERE ai_platform = ? AND DATE(timestamp) = ? AND status = 'allowed'
        ''', (ai_platform, today))
        
        result = c.fetchone()[0]
        conn.close()
        
        return result if result else 0.0
    
    async def _log_alert(self, alert_type: str, message: str, current: float, limit: float, action: str):
        """Log budget alerts"""
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute('''
            INSERT INTO budget_alerts (timestamp, alert_type, message, current_spend, limit_exceeded, action_taken)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (datetime.now().isoformat(), alert_type, message, current, limit, action))
        conn.commit()
        conn.close()
        
        print(f"⚠️  {alert_type.upper()}: {message}")
    
    def get_daily_summary(self) -> Dict:
        """Get today's spending breakdown"""
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        
        today = datetime.now().date().isoformat()
        c.execute('''
            SELECT ai_platform, SUM(cost) as total_cost, COUNT(*) as api_calls
            FROM spend_log 
            WHERE DATE(timestamp) = ? AND status = 'allowed'
            GROUP BY ai_platform
        ''', (today,))
        
        results = c.fetchall()
        conn.close()
        
        summary = {
            "date": today,
            "by_ai": {},
            "total_cost": 0.0,
            "total_calls": 0,
            "daily_budget": self.config["daily_limit"],
            "remaining": self.config["daily_limit"] - self.current_day_spend,
            "percent_used": (self.current_day_spend / self.config["daily_limit"] * 100) if self.config["daily_limit"] > 0 else 0
        }
        
        for platform, cost, calls in results:
            summary["by_ai"][platform] = {
                "cost": cost,
                "calls": calls,
                "daily_limit": self.config["ai_daily_limits"].get(platform, 0)
            }
            summary["total_cost"] += cost
            summary["total_calls"] += calls
        
        return summary
    
    def get_weekly_summary(self) -> Dict:
        """Get this week's spending"""
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        
        week_ago = (datetime.now() - timedelta(days=7)).date().isoformat()
        c.execute('''
            SELECT SUM(cost) as total_cost, COUNT(*) as api_calls
            FROM spend_log 
            WHERE DATE(timestamp) > ? AND status = 'allowed'
        ''', (week_ago,))
        
        result = c.fetchone()
        conn.close()
        
        total_cost = result[0] if result[0] else 0.0
        total_calls = result[1] if result[1] else 0
        
        return {
            "period": "last 7 days",
            "total_cost": total_cost,
            "total_calls": total_calls,
            "weekly_budget": self.config["weekly_limit"],
            "remaining": self.config["weekly_limit"] - total_cost,
            "percent_used": (total_cost / self.config["weekly_limit"] * 100) if self.config["weekly_limit"] > 0 else 0
        }
    
    def get_monthly_summary(self) -> Dict:
        """Get this month's spending"""
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        
        month_ago = (datetime.now() - timedelta(days=30)).date().isoformat()
        c.execute('''
            SELECT SUM(cost) as total_cost, COUNT(*) as api_calls
            FROM spend_log 
            WHERE DATE(timestamp) > ? AND status = 'allowed'
        ''', (month_ago,))
        
        result = c.fetchone()
        conn.close()
        
        total_cost = result[0] if result[0] else 0.0
        total_calls = result[1] if result[1] else 0
        
        return {
            "period": "last 30 days",
            "total_cost": total_cost,
            "total_calls": total_calls,
            "monthly_budget": self.config["monthly_limit"],
            "remaining": self.config["monthly_limit"] - total_cost,
            "percent_used": (total_cost / self.config["monthly_limit"] * 100) if self.config["monthly_limit"] > 0 else 0
        }
    
    def print_dashboard(self):
        """Print real-time cost dashboard"""
        daily = self.get_daily_summary()
        weekly = self.get_weekly_summary()
        monthly = self.get_monthly_summary()
        
        print("\n" + "="*70)
        print("ODIN COST CONTROL DASHBOARD")
        print("="*70)
        
        print(f"\n📊 TODAY ({daily['date']})")
        print(f"   Spent: ${daily['total_cost']:.2f} / ${daily['daily_budget']:.2f}")
        print(f"   Remaining: ${daily['remaining']:.2f}")
        print(f"   Progress: {daily['percent_used']:.1f}%")
        for ai, data in daily['by_ai'].items():
            print(f"      {ai.upper()}: ${data['cost']:.2f} ({data['calls']} calls)")
        
        print(f"\n📈 THIS WEEK")
        print(f"   Spent: ${weekly['total_cost']:.2f} / ${weekly['weekly_budget']:.2f}")
        print(f"   Remaining: ${weekly['remaining']:.2f}")
        print(f"   Progress: {weekly['percent_used']:.1f}%")
        
        print(f"\n📅 THIS MONTH")
        print(f"   Spent: ${monthly['total_cost']:.2f} / ${monthly['monthly_budget']:.2f}")
        print(f"   Remaining: ${monthly['remaining']:.2f}")
        print(f"   Progress: {monthly['percent_used']:.1f}%")
        
        print("\n" + "="*70 + "\n")


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

async def main():
    """Example usage of cost controller"""
    
    controller = OdinCostController()
    
    # Set to moderate budget
    controller.set_spending_level("moderate")
    
    # Simulate some API calls
    print("\n🚀 Simulating API calls...\n")
    
    # Call 1: PDUFA monitoring with ChatGPT
    cost1, allowed1 = await controller.log_api_call(
        ai_platform="openai",
        model="gpt4o",
        task_type="pdufa_monitoring",
        input_tokens=5000,
        output_tokens=2000
    )
    print(f"ChatGPT PDUFA call: ${cost1:.4f} - {'✅ ALLOWED' if allowed1 else '❌ BLOCKED'}")
    
    # Call 2: Claude for biotech analysis
    cost2, allowed2 = await controller.log_api_call(
        ai_platform="claude",
        model="sonnet",
        task_type="biotech_analysis",
        input_tokens=8000,
        output_tokens=3000
    )
    print(f"Claude analysis: ${cost2:.4f} - {'✅ ALLOWED' if allowed2 else '❌ BLOCKED'}")
    
    # Call 3: Gemini for SEC filing parsing
    cost3, allowed3 = await controller.log_api_call(
        ai_platform="gemini",
        model="pro_25",
        task_type="sec_filing_parsing",
        input_tokens=12000,
        output_tokens=4000
    )
    print(f"Gemini SEC parsing: ${cost3:.4f} - {'✅ ALLOWED' if allowed3 else '❌ BLOCKED'}")
    
    # Call 4: Perplexity search
    cost4, allowed4 = await controller.log_api_call(
        ai_platform="perplexity",
        model="sonar_pro",
        task_type="fda_search",
        input_tokens=3000,
        output_tokens=1500,
        search_requests=5
    )
    print(f"Perplexity search: ${cost4:.4f} - {'✅ ALLOWED' if allowed4 else '❌ BLOCKED'}")
    
    # Print dashboard
    controller.print_dashboard()
    
    # Show how to change budgets
    print("\n💰 Changing budget level to AGGRESSIVE...\n")
    controller.set_spending_level("aggressive")
    controller.print_dashboard()
    
    print("\n💰 Setting CUSTOM budget...\n")
    controller.set_custom_budget(
        daily=300,
        weekly=2000,
        monthly=8000,
        ai_limits={"openai": 100, "claude": 80, "gemini": 50, "perplexity": 70}
    )
    controller.print_dashboard()


if __name__ == "__main__":
    asyncio.run(main())
