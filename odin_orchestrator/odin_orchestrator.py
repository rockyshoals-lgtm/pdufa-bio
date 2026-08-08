"""
ODIN Multi-AI Orchestrator
Production-ready autonomous system for biotech trading signals

This orchestrator:
1. Routes tasks to the most appropriate AI based on expertise
2. Maintains shared context for inter-AI collaboration
3. Runs autonomous monitoring loops for real-time signals
4. Enforces budget limits and cost controls
5. Generates actionable trading recommendations
"""

import os
import json
import asyncio
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, asdict, field
from enum import Enum
from pathlib import Path
import signal
import sys

# Import our modules
from odin_shared_context import (
    OdinSharedContext, AIFinding, FindingType, get_shared_context
)
from odin_data_pipelines import OdinDataPipeline, get_data_pipeline
from odin_ai_workers import (
    TaskType, AIProvider, AIResponse, CostTracker,
    ClaudeWorker, ChatGPTWorker, GeminiWorker, PerplexityWorker,
    create_workers, BaseAIWorker
)


# =============================================================================
# BUDGET CONTROLLER
# =============================================================================

class BudgetTier(Enum):
    """Predefined budget tiers"""
    MINIMAL = "minimal"       # $15/day - thesis updates only
    STANDARD = "standard"     # $50/day - core monitoring
    AGGRESSIVE = "aggressive" # $150/day - full autonomous mode
    UNLIMITED = "unlimited"   # $500/day - no throttling


@dataclass
class BudgetConfig:
    """Budget configuration"""
    tier: BudgetTier
    daily_limit: float
    weekly_limit: float
    monthly_limit: float
    per_ai_limits: Dict[str, float]  # Per-AI daily limits
    critical_reserve: float = 5.0     # Reserve for PDUFA-critical tasks
    auto_throttle: bool = True
    
    @classmethod
    def from_tier(cls, tier: BudgetTier) -> 'BudgetConfig':
        """Create config from preset tier"""
        configs = {
            BudgetTier.MINIMAL: {
                'daily_limit': 15.0,
                'weekly_limit': 75.0,
                'monthly_limit': 250.0,
                'per_ai_limits': {'claude': 5.0, 'openai': 4.0, 'gemini': 3.0, 'perplexity': 3.0}
            },
            BudgetTier.STANDARD: {
                'daily_limit': 50.0,
                'weekly_limit': 250.0,
                'monthly_limit': 800.0,
                'per_ai_limits': {'claude': 20.0, 'openai': 15.0, 'gemini': 8.0, 'perplexity': 7.0}
            },
            BudgetTier.AGGRESSIVE: {
                'daily_limit': 150.0,
                'weekly_limit': 750.0,
                'monthly_limit': 2500.0,
                'per_ai_limits': {'claude': 60.0, 'openai': 45.0, 'gemini': 25.0, 'perplexity': 20.0}
            },
            BudgetTier.UNLIMITED: {
                'daily_limit': 500.0,
                'weekly_limit': 2500.0,
                'monthly_limit': 8000.0,
                'per_ai_limits': {'claude': 200.0, 'openai': 150.0, 'gemini': 75.0, 'perplexity': 75.0}
            }
        }
        
        cfg = configs[tier]
        return cls(
            tier=tier,
            daily_limit=cfg['daily_limit'],
            weekly_limit=cfg['weekly_limit'],
            monthly_limit=cfg['monthly_limit'],
            per_ai_limits=cfg['per_ai_limits']
        )


class BudgetController:
    """
    Controls spending across all AI providers
    
    Features:
    - Real-time cost tracking
    - Per-AI and total budget limits
    - Auto-throttling when approaching limits
    - Critical task prioritization
    """
    
    def __init__(self, config: BudgetConfig, db_file: str = "odin_budget.db"):
        self.config = config
        self.db_file = db_file
        self.cost_tracker = CostTracker()
        self._init_database()
        self._load_today_costs()
        
        print(f"💰 Budget Controller initialized: {config.tier.value} tier")
        print(f"   Daily limit: ${config.daily_limit:.2f}")
    
    def _init_database(self):
        """Initialize cost tracking database"""
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS cost_log (
                id INTEGER PRIMARY KEY,
                timestamp TEXT,
                provider TEXT,
                task_type TEXT,
                ticker TEXT,
                tokens INTEGER,
                cost REAL
            )
        ''')
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS daily_summary (
                date TEXT PRIMARY KEY,
                total_cost REAL,
                openai_cost REAL,
                claude_cost REAL,
                gemini_cost REAL,
                perplexity_cost REAL,
                total_tokens INTEGER,
                task_count INTEGER
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _load_today_costs(self):
        """Load today's costs from database"""
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        
        today = datetime.now().strftime('%Y-%m-%d')
        c.execute('''
            SELECT provider, SUM(cost) FROM cost_log 
            WHERE date(timestamp) = ? GROUP BY provider
        ''', (today,))
        
        for provider, cost in c.fetchall():
            if provider == 'openai':
                self.cost_tracker.openai_cost = cost
            elif provider == 'claude':
                self.cost_tracker.claude_cost = cost
            elif provider == 'gemini':
                self.cost_tracker.gemini_cost = cost
            elif provider == 'perplexity':
                self.cost_tracker.perplexity_cost = cost
        
        conn.close()
    
    def log_cost(self, provider: str, task_type: str, ticker: str, 
                 tokens: int, cost: float):
        """Log a cost entry"""
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        
        c.execute('''
            INSERT INTO cost_log (timestamp, provider, task_type, ticker, tokens, cost)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (datetime.now().isoformat(), provider, task_type, ticker, tokens, cost))
        
        conn.commit()
        conn.close()
    
    def can_spend(self, provider: str, estimated_cost: float, 
                  is_critical: bool = False) -> Tuple[bool, str]:
        """
        Check if we can afford a task
        
        Returns: (can_spend, reason)
        """
        # Get current costs
        current_total = self.cost_tracker.total_cost
        
        provider_costs = {
            'openai': self.cost_tracker.openai_cost,
            'claude': self.cost_tracker.claude_cost,
            'gemini': self.cost_tracker.gemini_cost,
            'perplexity': self.cost_tracker.perplexity_cost
        }
        current_provider = provider_costs.get(provider, 0)
        
        # Critical tasks can use reserve
        effective_limit = self.config.daily_limit
        if is_critical:
            effective_limit += self.config.critical_reserve
        
        # Check total daily limit
        if current_total + estimated_cost > effective_limit:
            return False, f"Would exceed daily limit (${current_total:.2f}/${effective_limit:.2f})"
        
        # Check per-AI limit
        ai_limit = self.config.per_ai_limits.get(provider, 10.0)
        if current_provider + estimated_cost > ai_limit:
            return False, f"Would exceed {provider} limit (${current_provider:.2f}/${ai_limit:.2f})"
        
        return True, "OK"
    
    def get_remaining_budget(self) -> Dict[str, float]:
        """Get remaining budget for each AI"""
        return {
            'total': self.config.daily_limit - self.cost_tracker.total_cost,
            'openai': self.config.per_ai_limits.get('openai', 0) - self.cost_tracker.openai_cost,
            'claude': self.config.per_ai_limits.get('claude', 0) - self.cost_tracker.claude_cost,
            'gemini': self.config.per_ai_limits.get('gemini', 0) - self.cost_tracker.gemini_cost,
            'perplexity': self.config.per_ai_limits.get('perplexity', 0) - self.cost_tracker.perplexity_cost
        }
    
    def get_throttle_factor(self) -> float:
        """
        Get throttle factor based on budget consumption
        Returns 1.0 for normal, <1.0 to reduce task frequency
        """
        if not self.config.auto_throttle:
            return 1.0
        
        usage_pct = self.cost_tracker.total_cost / self.config.daily_limit
        
        if usage_pct < 0.5:
            return 1.0  # Full speed
        elif usage_pct < 0.75:
            return 0.75  # Slight reduction
        elif usage_pct < 0.9:
            return 0.5  # Moderate reduction
        else:
            return 0.25  # Heavy throttling
    
    def summary(self) -> str:
        """Get budget summary"""
        remaining = self.get_remaining_budget()
        throttle = self.get_throttle_factor()
        
        return (
            f"💰 Budget Status ({self.config.tier.value})\n"
            f"   Spent Today: ${self.cost_tracker.total_cost:.2f} / ${self.config.daily_limit:.2f}\n"
            f"   Remaining: ${remaining['total']:.2f}\n"
            f"   By AI: Claude ${remaining['claude']:.2f} | OpenAI ${remaining['openai']:.2f} | "
            f"Gemini ${remaining['gemini']:.2f} | Perplexity ${remaining['perplexity']:.2f}\n"
            f"   Throttle Factor: {throttle:.0%}"
        )


# =============================================================================
# TASK ROUTER
# =============================================================================

class TaskRouter:
    """
    Routes tasks to the most appropriate AI based on:
    - Task type and complexity
    - AI expertise/specialization
    - Budget availability
    - Current workload
    """
    
    # Task-to-AI routing table (primary and fallback)
    ROUTING_TABLE = {
        TaskType.PDUFA_ANALYSIS: [AIProvider.ANTHROPIC, AIProvider.OPENAI],
        TaskType.OPTIONS_PRICING: [AIProvider.OPENAI, AIProvider.ANTHROPIC],
        TaskType.INSIDER_DETECTION: [AIProvider.GOOGLE, AIProvider.ANTHROPIC],
        TaskType.FDA_NEWS_SCAN: [AIProvider.GOOGLE, AIProvider.PERPLEXITY],
        TaskType.SIGNAL_SYNTHESIS: [AIProvider.PERPLEXITY, AIProvider.ANTHROPIC],
        TaskType.THESIS_UPDATE: [AIProvider.ANTHROPIC, AIProvider.PERPLEXITY],
        TaskType.CATALYST_VALIDATION: [AIProvider.ANTHROPIC, AIProvider.GOOGLE]
    }
    
    # Estimated costs per task type (for budget checks)
    ESTIMATED_COSTS = {
        TaskType.PDUFA_ANALYSIS: 0.08,
        TaskType.OPTIONS_PRICING: 0.05,
        TaskType.INSIDER_DETECTION: 0.02,
        TaskType.FDA_NEWS_SCAN: 0.02,
        TaskType.SIGNAL_SYNTHESIS: 0.04,
        TaskType.THESIS_UPDATE: 0.06,
        TaskType.CATALYST_VALIDATION: 0.04
    }
    
    # Task priority (higher = more important, PDUFA is critical)
    PRIORITY = {
        TaskType.PDUFA_ANALYSIS: 100,
        TaskType.OPTIONS_PRICING: 80,
        TaskType.SIGNAL_SYNTHESIS: 70,
        TaskType.CATALYST_VALIDATION: 60,
        TaskType.FDA_NEWS_SCAN: 50,
        TaskType.INSIDER_DETECTION: 40,
        TaskType.THESIS_UPDATE: 20
    }
    
    def __init__(self, budget_controller: BudgetController, 
                 workers: Dict[AIProvider, BaseAIWorker]):
        self.budget = budget_controller
        self.workers = workers
    
    def route(self, task_type: TaskType, is_critical: bool = False) -> Optional[AIProvider]:
        """
        Determine which AI should handle a task
        
        Returns: AIProvider or None if no AI available
        """
        candidates = self.ROUTING_TABLE.get(task_type, [AIProvider.ANTHROPIC])
        estimated_cost = self.ESTIMATED_COSTS.get(task_type, 0.05)
        
        for provider in candidates:
            provider_name = provider.value
            can_afford, reason = self.budget.can_spend(
                provider_name, estimated_cost, is_critical
            )
            
            if can_afford:
                return provider
            else:
                print(f"   ⚠️  {provider_name} unavailable: {reason}")
        
        return None
    
    def get_priority(self, task_type: TaskType) -> int:
        """Get task priority"""
        return self.PRIORITY.get(task_type, 50)


# =============================================================================
# ODIN ORCHESTRATOR
# =============================================================================

@dataclass
class ScheduledTask:
    """A task scheduled for execution"""
    ticker: str
    task_type: TaskType
    payload: Dict
    priority: int
    scheduled_at: str = None
    is_critical: bool = False
    
    def __post_init__(self):
        if self.scheduled_at is None:
            self.scheduled_at = datetime.now().isoformat()


class OdinOrchestrator:
    """
    Master orchestrator for the ODIN multi-AI system
    
    Features:
    - Autonomous monitoring loops
    - Budget-aware task routing
    - Inter-AI collaboration via shared context
    - Real-time signal generation
    - Graceful shutdown handling
    """
    
    def __init__(self, 
                 budget_tier: BudgetTier = BudgetTier.STANDARD,
                 watchlist_file: str = "watchlist.json"):
        
        print("\n" + "="*70)
        print("🤖 ODIN Multi-AI Orchestrator Initializing...")
        print("="*70)
        
        # Initialize components
        self.shared_context = OdinSharedContext()
        self.data_pipeline = get_data_pipeline()
        
        # Budget and cost tracking
        budget_config = BudgetConfig.from_tier(budget_tier)
        self.budget = BudgetController(budget_config)
        
        # AI Workers
        self.workers = create_workers(self.shared_context, self.budget.cost_tracker)
        
        # Task routing
        self.router = TaskRouter(self.budget, self.workers)
        
        # Task queue
        self.task_queue: List[ScheduledTask] = []
        
        # Watchlist
        self.watchlist = self._load_watchlist(watchlist_file)
        
        # Control flags
        self._running = False
        self._shutdown_requested = False
        
        # Loop intervals (seconds)
        self.intervals = {
            'pdufa_monitor': 15 * 60,    # 15 minutes
            'options_scan': 5 * 60,       # 5 minutes
            'insider_check': 24 * 60 * 60, # Daily
            'thesis_update': 7 * 24 * 60 * 60  # Weekly
        }
        
        print(f"✅ Orchestrator ready")
        print(f"   Watchlist: {len(self.watchlist)} tickers")
        print(f"   Workers: Claude, ChatGPT, Gemini, Perplexity")
        print(self.budget.summary())
    
    def _load_watchlist(self, file_path: str) -> List[Dict]:
        """Load ticker watchlist"""
        if Path(file_path).exists():
            with open(file_path, 'r') as f:
                return json.load(f)
        
        # Default watchlist for testing
        return [
            {"ticker": "GUTS", "pdufa_date": "2025-02-15", "priority": "high"},
            {"ticker": "AQST", "pdufa_date": "2025-01-31", "priority": "critical"},
            {"ticker": "VNDA", "pdufa_date": "2025-02-28", "priority": "medium"}
        ]
    
    def add_to_watchlist(self, ticker: str, pdufa_date: str = None, 
                         priority: str = "medium"):
        """Add a ticker to the watchlist"""
        self.watchlist.append({
            "ticker": ticker,
            "pdufa_date": pdufa_date,
            "priority": priority,
            "added_at": datetime.now().isoformat()
        })
    
    async def execute_task(self, task: ScheduledTask) -> Optional[AIResponse]:
        """Execute a single task"""
        # Route to appropriate AI
        provider = self.router.route(task.task_type, task.is_critical)
        
        if provider is None:
            print(f"   ❌ No available AI for {task.task_type.value} on {task.ticker}")
            return None
        
        worker = self.workers[provider]
        
        print(f"   🔄 {task.ticker} → {provider.value} ({task.task_type.value})")
        
        # Execute
        response = await worker.execute(task.task_type, task.ticker, task.payload)
        
        # Log cost
        if response.success:
            self.budget.log_cost(
                provider.value,
                task.task_type.value,
                task.ticker,
                response.tokens_used,
                response.cost_usd
            )
            
            # Add finding to shared context
            finding = response.to_finding()
            if finding:
                self.shared_context.add_finding(finding)
            
            print(f"   ✅ {task.ticker}: confidence={response.confidence:.0%}, "
                  f"cost=${response.cost_usd:.4f}")
        else:
            print(f"   ❌ {task.ticker}: {response.error}")
        
        return response
    
    async def analyze_ticker(self, ticker: str, 
                            pdufa_info: Dict = None) -> Dict[str, AIResponse]:
        """
        Run full multi-AI analysis pipeline for a ticker
        
        Pipeline:
        1. Claude: PDUFA risk analysis
        2. ChatGPT: Options pricing analysis
        3. Gemini: Insider detection + FDA news
        4. Perplexity: Signal synthesis
        """
        print(f"\n📊 Full Analysis Pipeline for {ticker}")
        print("-" * 50)
        
        results = {}
        
        # Prepare payload
        payload = pdufa_info or {}
        payload['ticker'] = ticker
        
        # Fetch market data
        market_data = await self.data_pipeline.get_comprehensive_data(ticker)
        payload['market_data'] = market_data
        
        # Step 1: Claude - PDUFA Analysis (critical)
        task1 = ScheduledTask(
            ticker=ticker,
            task_type=TaskType.PDUFA_ANALYSIS,
            payload=payload,
            priority=100,
            is_critical=True
        )
        results['pdufa_analysis'] = await self.execute_task(task1)
        
        # Brief pause to avoid rate limits
        await asyncio.sleep(1)
        
        # Step 2: ChatGPT - Options Analysis
        task2 = ScheduledTask(
            ticker=ticker,
            task_type=TaskType.OPTIONS_PRICING,
            payload=payload,
            priority=80
        )
        results['options_analysis'] = await self.execute_task(task2)
        
        await asyncio.sleep(1)
        
        # Step 3: Gemini - Insider Detection
        task3 = ScheduledTask(
            ticker=ticker,
            task_type=TaskType.INSIDER_DETECTION,
            payload=payload,
            priority=40
        )
        results['insider_analysis'] = await self.execute_task(task3)
        
        await asyncio.sleep(1)
        
        # Step 4: Perplexity - Signal Synthesis (uses all prior findings)
        task4 = ScheduledTask(
            ticker=ticker,
            task_type=TaskType.SIGNAL_SYNTHESIS,
            payload=payload,
            priority=70
        )
        results['signal_synthesis'] = await self.execute_task(task4)
        
        # Print summary
        print(f"\n📋 Analysis Complete for {ticker}")
        consensus = self.shared_context.get_consensus(ticker)
        if consensus:
            print(f"   Consensus: {consensus.get('consensus_action', 'N/A')}")
            print(f"   Approval Prob: {consensus.get('weighted_approval_probability', 0):.0%}")
            print(f"   Contributing AIs: {', '.join(consensus.get('contributing_ais', []))}")
        
        return results
    
    # =========================================================================
    # AUTONOMOUS MONITORING LOOPS
    # =========================================================================
    
    async def _pdufa_monitor_loop(self):
        """
        Monitor upcoming PDUFA dates for watchlist tickers
        Runs every 15 minutes (configurable)
        """
        while self._running:
            try:
                print(f"\n⏰ PDUFA Monitor Loop - {datetime.now().strftime('%H:%M:%S')}")
                
                # Check throttle
                throttle = self.budget.get_throttle_factor()
                if throttle < 0.5:
                    print("   ⚠️  Budget throttle active, reducing frequency")
                
                # Process high-priority tickers
                for item in self.watchlist:
                    if self._shutdown_requested:
                        break
                    
                    if item.get('priority') in ['critical', 'high']:
                        ticker = item['ticker']
                        
                        # Check if PDUFA is within 14 days
                        pdufa_date = item.get('pdufa_date')
                        if pdufa_date:
                            days_to_pdufa = (
                                datetime.strptime(pdufa_date, '%Y-%m-%d') - datetime.now()
                            ).days
                            
                            if 0 <= days_to_pdufa <= 14:
                                print(f"   🎯 {ticker}: {days_to_pdufa} days to PDUFA")
                                
                                task = ScheduledTask(
                                    ticker=ticker,
                                    task_type=TaskType.PDUFA_ANALYSIS,
                                    payload=item,
                                    priority=100,
                                    is_critical=True
                                )
                                await self.execute_task(task)
                                await asyncio.sleep(2)  # Rate limit
                
                # Adjust interval based on throttle
                interval = self.intervals['pdufa_monitor'] / throttle
                await asyncio.sleep(interval)
                
            except Exception as e:
                print(f"   ❌ PDUFA monitor error: {e}")
                await asyncio.sleep(60)
    
    async def _options_scan_loop(self):
        """
        Scan options chain for IV/flow signals
        Runs every 5 minutes
        """
        while self._running:
            try:
                print(f"\n📈 Options Scan Loop - {datetime.now().strftime('%H:%M:%S')}")
                
                throttle = self.budget.get_throttle_factor()
                
                # Process tickers with upcoming catalysts
                for item in self.watchlist[:5]:  # Limit to top 5
                    if self._shutdown_requested:
                        break
                    
                    ticker = item['ticker']
                    
                    task = ScheduledTask(
                        ticker=ticker,
                        task_type=TaskType.OPTIONS_PRICING,
                        payload=item,
                        priority=80
                    )
                    await self.execute_task(task)
                    await asyncio.sleep(1)
                
                interval = self.intervals['options_scan'] / throttle
                await asyncio.sleep(interval)
                
            except Exception as e:
                print(f"   ❌ Options scan error: {e}")
                await asyncio.sleep(60)
    
    async def _insider_check_loop(self):
        """
        Check for insider transactions (daily)
        """
        while self._running:
            try:
                print(f"\n👤 Insider Check Loop - {datetime.now().strftime('%H:%M:%S')}")
                
                for item in self.watchlist:
                    if self._shutdown_requested:
                        break
                    
                    ticker = item['ticker']
                    
                    task = ScheduledTask(
                        ticker=ticker,
                        task_type=TaskType.INSIDER_DETECTION,
                        payload=item,
                        priority=40
                    )
                    await self.execute_task(task)
                    await asyncio.sleep(2)
                
                await asyncio.sleep(self.intervals['insider_check'])
                
            except Exception as e:
                print(f"   ❌ Insider check error: {e}")
                await asyncio.sleep(3600)  # 1 hour on error
    
    async def _thesis_update_loop(self):
        """
        Update investment theses (weekly)
        """
        while self._running:
            try:
                print(f"\n📝 Thesis Update Loop - {datetime.now().strftime('%H:%M:%S')}")
                
                # Only run if budget allows (low priority)
                remaining = self.budget.get_remaining_budget()
                if remaining['total'] < 5.0:
                    print("   ⚠️  Insufficient budget for thesis updates")
                    await asyncio.sleep(3600)
                    continue
                
                for item in self.watchlist:
                    if self._shutdown_requested:
                        break
                    
                    ticker = item['ticker']
                    
                    task = ScheduledTask(
                        ticker=ticker,
                        task_type=TaskType.THESIS_UPDATE,
                        payload=item,
                        priority=20
                    )
                    await self.execute_task(task)
                    await asyncio.sleep(5)
                
                await asyncio.sleep(self.intervals['thesis_update'])
                
            except Exception as e:
                print(f"   ❌ Thesis update error: {e}")
                await asyncio.sleep(3600)
    
    async def run_autonomous(self):
        """
        Start all autonomous monitoring loops
        """
        print("\n🚀 Starting Autonomous Mode...")
        print("   Press Ctrl+C to stop\n")
        
        self._running = True
        
        # Setup signal handlers
        def handle_shutdown(signum, frame):
            print("\n\n🛑 Shutdown requested...")
            self._shutdown_requested = True
            self._running = False
        
        signal.signal(signal.SIGINT, handle_shutdown)
        signal.signal(signal.SIGTERM, handle_shutdown)
        
        try:
            # Start all loops concurrently
            await asyncio.gather(
                self._pdufa_monitor_loop(),
                self._options_scan_loop(),
                self._insider_check_loop(),
                self._thesis_update_loop(),
                return_exceptions=True
            )
        except asyncio.CancelledError:
            pass
        finally:
            self._running = False
            print("\n✅ Orchestrator stopped gracefully")
            print(self.budget.summary())
    
    async def run_once(self, ticker: str = None):
        """Run a single analysis cycle (for testing)"""
        if ticker:
            return await self.analyze_ticker(ticker)
        
        # Analyze all watchlist
        results = {}
        for item in self.watchlist:
            ticker = item['ticker']
            results[ticker] = await self.analyze_ticker(ticker, item)
        
        return results
    
    def print_status(self):
        """Print current system status"""
        print("\n" + "="*70)
        print("ODIN SYSTEM STATUS")
        print("="*70)
        
        print("\n📊 Watchlist:")
        for item in self.watchlist:
            print(f"   {item['ticker']}: PDUFA {item.get('pdufa_date', 'N/A')} "
                  f"[{item.get('priority', 'medium')}]")
        
        print(f"\n{self.budget.summary()}")
        
        print("\n🤖 AI Workers:")
        for provider, worker in self.workers.items():
            api_status = "✅" if getattr(worker, 'api_key', None) else "❌ No API key"
            print(f"   {provider.value}: {api_status}")
        
        self.shared_context.print_status()


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

async def main():
    """Main entry point for ODIN"""
    import argparse
    
    parser = argparse.ArgumentParser(description='ODIN Multi-AI Orchestrator')
    parser.add_argument('--mode', choices=['autonomous', 'single', 'status'],
                       default='status', help='Operation mode')
    parser.add_argument('--ticker', type=str, help='Ticker for single analysis')
    parser.add_argument('--budget', choices=['minimal', 'standard', 'aggressive', 'unlimited'],
                       default='standard', help='Budget tier')
    
    args = parser.parse_args()
    
    # Map budget string to enum
    budget_map = {
        'minimal': BudgetTier.MINIMAL,
        'standard': BudgetTier.STANDARD,
        'aggressive': BudgetTier.AGGRESSIVE,
        'unlimited': BudgetTier.UNLIMITED
    }
    
    # Initialize orchestrator
    odin = OdinOrchestrator(budget_tier=budget_map[args.budget])
    
    if args.mode == 'status':
        odin.print_status()
    
    elif args.mode == 'single':
        ticker = args.ticker or 'GUTS'
        results = await odin.run_once(ticker)
        print("\n📋 Results:")
        for name, response in results.items():
            if response and response.success:
                print(f"\n{name}:")
                print(json.dumps(response.data, indent=2)[:500])
    
    elif args.mode == 'autonomous':
        await odin.run_autonomous()


if __name__ == "__main__":
    asyncio.run(main())
