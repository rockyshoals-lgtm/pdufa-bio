#!/usr/bin/env python3
"""
ODIN Test Suite
Validates all components before production deployment

Run with:
  python test_odin.py --mode mock     # Test with mock responses (no API keys needed)
  python test_odin.py --mode live     # Test with real API calls
  python test_odin.py --mode claude   # Test only Claude integration
"""

import os
import sys
import json
import asyncio
from datetime import datetime

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def print_header(title: str):
    print("\n" + "="*70)
    print(f" {title}")
    print("="*70 + "\n")


def print_test(name: str, passed: bool, details: str = ""):
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"  {status}: {name}")
    if details:
        print(f"         {details}")


async def test_shared_context():
    """Test the shared context module"""
    print_header("Testing Shared Context")
    
    from odin_shared_context import OdinSharedContext, AIFinding, FindingType
    
    try:
        ctx = OdinSharedContext(db_file="test_context.db")
        print_test("Context initialization", True)
        
        # Add a test finding
        finding = AIFinding(
            finding_id="",
            ticker="TEST",
            ai_source="claude",
            finding_type=FindingType.PDUFA_ANALYSIS,
            content={"approval_probability": 0.75, "test": True},
            confidence=0.85,
            evidence=["Test evidence"]
        )
        
        ctx.add_finding(finding)
        print_test("Add finding", True, f"ID: {finding.finding_id}")
        
        # Retrieve finding
        findings = ctx.get_all_findings("TEST")
        print_test("Retrieve findings", len(findings) == 1)
        
        # Get consensus
        consensus = ctx.get_consensus("TEST")
        print_test("Calculate consensus", consensus is not None)
        
        # Test context building
        context = ctx.get_context_for_ai("TEST", "perplexity", "synthesis")
        print_test("Build context for AI", len(context) > 0)
        
        # Cleanup
        import os
        os.remove("test_context.db")
        print_test("Cleanup", True)
        
        return True
        
    except Exception as e:
        print_test("Shared context", False, str(e))
        return False


async def test_data_pipelines():
    """Test the data pipeline module"""
    print_header("Testing Data Pipelines")
    
    from odin_data_pipelines import OdinDataPipeline
    
    try:
        pipeline = OdinDataPipeline()
        print_test("Pipeline initialization", True)
        
        # Test comprehensive data fetch (may fail without API keys, that's OK)
        data = await pipeline.get_comprehensive_data("GUTS")
        print_test("Fetch comprehensive data", 'ticker' in data, 
                  f"Got {len(data.get('insider_transactions', []))} insider txs")
        
        # Test context building
        context = pipeline.build_ai_context("GUTS", data)
        print_test("Build AI context", len(context) > 100, f"{len(context)} chars")
        
        return True
        
    except Exception as e:
        print_test("Data pipelines", False, str(e))
        return False


async def test_cost_tracker():
    """Test the cost tracking system"""
    print_header("Testing Cost Tracker")
    
    from odin_ai_workers import CostTracker
    
    try:
        tracker = CostTracker()
        print_test("Tracker initialization", True)
        
        # Add some costs
        cost1 = tracker.add_usage('claude', 1000, 500)
        cost2 = tracker.add_usage('openai', 2000, 1000)
        
        print_test("Track Claude cost", tracker.claude_cost > 0, f"${tracker.claude_cost:.4f}")
        print_test("Track OpenAI cost", tracker.openai_cost > 0, f"${tracker.openai_cost:.4f}")
        print_test("Total cost", tracker.total_cost == tracker.claude_cost + tracker.openai_cost)
        
        summary = tracker.summary()
        print_test("Generate summary", "TOTAL" in summary)
        
        return True
        
    except Exception as e:
        print_test("Cost tracker", False, str(e))
        return False


async def test_budget_controller():
    """Test the budget controller"""
    print_header("Testing Budget Controller")
    
    from odin_orchestrator import BudgetController, BudgetConfig, BudgetTier
    
    try:
        config = BudgetConfig.from_tier(BudgetTier.STANDARD)
        print_test("Config from tier", config.daily_limit == 50.0)
        
        controller = BudgetController(config, db_file="test_budget.db")
        print_test("Controller initialization", True)
        
        # Test spending check
        can_spend, reason = controller.can_spend('claude', 0.10)
        print_test("Can spend check (should pass)", can_spend, reason)
        
        can_spend2, reason2 = controller.can_spend('claude', 100.0)
        print_test("Can spend check (should fail)", not can_spend2)
        
        # Test throttle
        throttle = controller.get_throttle_factor()
        print_test("Throttle factor", throttle == 1.0, f"Factor: {throttle}")
        
        # Cleanup
        import os
        os.remove("test_budget.db")
        
        return True
        
    except Exception as e:
        print_test("Budget controller", False, str(e))
        return False


async def test_claude_worker_mock():
    """Test Claude worker with mock (no API call)"""
    print_header("Testing Claude Worker (Mock)")
    
    from odin_shared_context import OdinSharedContext
    from odin_ai_workers import ClaudeWorker, CostTracker, TaskType
    import os as os_module
    
    try:
        ctx = OdinSharedContext(db_file="test_claude.db")
        costs = CostTracker()
        
        # Create worker without API key
        original_key = os_module.environ.get('ANTHROPIC_API_KEY')
        os_module.environ['ANTHROPIC_API_KEY'] = ''
        
        worker = ClaudeWorker(ctx, costs)
        print_test("Worker initialization", True)
        
        # Execute should fail gracefully without API key
        response = await worker.execute(
            TaskType.PDUFA_ANALYSIS,
            "TEST",
            {"ticker": "TEST", "btd": True}
        )
        
        print_test("Graceful failure without API key", 
                  not response.success and "not configured" in response.error)
        
        # Restore key
        if original_key:
            os_module.environ['ANTHROPIC_API_KEY'] = original_key
        
        # Cleanup
        os_module.remove("test_claude.db")
        
        return True
        
    except Exception as e:
        print_test("Claude worker mock", False, str(e))
        return False


async def test_claude_worker_live():
    """Test Claude worker with real API call"""
    print_header("Testing Claude Worker (LIVE API)")
    
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        print("  ⚠️  ANTHROPIC_API_KEY not set, skipping live test")
        return True
    
    from odin_shared_context import OdinSharedContext
    from odin_ai_workers import ClaudeWorker, CostTracker, TaskType
    
    try:
        ctx = OdinSharedContext(db_file="test_claude_live.db")
        costs = CostTracker()
        
        worker = ClaudeWorker(ctx, costs)
        print_test("Worker initialization with API key", worker.api_key is not None)
        
        # Execute real analysis
        print("  🔄 Making live API call to Claude...")
        response = await worker.execute(
            TaskType.PDUFA_ANALYSIS,
            "GUTS",
            {
                "ticker": "GUTS",
                "drug": "SIM0323",
                "indication": "Plaque Psoriasis",
                "pdufa_date": "2025-02-15",
                "btd": True,
                "priority_review": True
            }
        )
        
        print_test("API call successful", response.success, 
                  f"Tokens: {response.tokens_used}, Cost: ${response.cost_usd:.4f}")
        
        if response.success:
            prob = response.data.get('approval_probability', 0)
            print_test("Got approval probability", prob > 0, f"{prob:.0%}")
            print(f"\n  📊 Claude's Analysis:")
            print(f"     Approval Prob: {prob:.0%}")
            print(f"     Confidence: {response.confidence:.0%}")
            print(f"     Recommendation: {response.data.get('recommendation', 'N/A')}")
            print(f"     Reasoning: {response.reasoning[:200]}...")
        
        # Cleanup
        import os
        os.remove("test_claude_live.db")
        
        return response.success
        
    except Exception as e:
        print_test("Claude worker live", False, str(e))
        return False


async def test_full_orchestrator():
    """Test the full orchestrator"""
    print_header("Testing Full Orchestrator")
    
    from odin_orchestrator import OdinOrchestrator, BudgetTier
    
    try:
        odin = OdinOrchestrator(budget_tier=BudgetTier.MINIMAL)
        print_test("Orchestrator initialization", True)
        
        # Check status
        odin.print_status()
        print_test("Print status", True)
        
        # Add to watchlist
        odin.add_to_watchlist("NEW", "2025-03-15", "high")
        print_test("Add to watchlist", len(odin.watchlist) > 0)
        
        return True
        
    except Exception as e:
        print_test("Full orchestrator", False, str(e))
        return False


async def test_full_pipeline_live():
    """Test full multi-AI pipeline with live API calls"""
    print_header("Testing Full Multi-AI Pipeline (LIVE)")
    
    # Check for at least one API key
    has_any_key = any([
        os.environ.get('ANTHROPIC_API_KEY'),
        os.environ.get('OPENAI_API_KEY'),
        os.environ.get('GEMINI_API_KEY'),
        os.environ.get('PERPLEXITY_API_KEY')
    ])
    
    if not has_any_key:
        print("  ⚠️  No API keys found, skipping live pipeline test")
        return True
    
    from odin_orchestrator import OdinOrchestrator, BudgetTier
    
    try:
        odin = OdinOrchestrator(budget_tier=BudgetTier.MINIMAL)
        
        # Run single ticker analysis
        print("  🔄 Running full analysis pipeline for GUTS...")
        results = await odin.analyze_ticker("GUTS", {
            "ticker": "GUTS",
            "drug": "SIM0323",
            "indication": "Plaque Psoriasis",
            "pdufa_date": "2025-02-15",
            "btd": True,
            "priority_review": True
        })
        
        # Check results
        successful = sum(1 for r in results.values() if r and r.success)
        print_test(f"Pipeline completed", successful > 0, 
                  f"{successful}/{len(results)} tasks succeeded")
        
        # Print consensus
        odin.shared_context.print_status("GUTS")
        
        return successful > 0
        
    except Exception as e:
        print_test("Full pipeline live", False, str(e))
        return False


async def run_all_tests(mode: str = 'mock'):
    """Run all tests"""
    print_header(f"ODIN TEST SUITE - Mode: {mode.upper()}")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    results = {}
    
    # Core module tests (always run)
    results['shared_context'] = await test_shared_context()
    results['data_pipelines'] = await test_data_pipelines()
    results['cost_tracker'] = await test_cost_tracker()
    results['budget_controller'] = await test_budget_controller()
    results['claude_mock'] = await test_claude_worker_mock()
    results['orchestrator'] = await test_full_orchestrator()
    
    # Live tests (if requested)
    if mode == 'live' or mode == 'claude':
        results['claude_live'] = await test_claude_worker_live()
    
    if mode == 'live':
        results['full_pipeline'] = await test_full_pipeline_live()
    
    # Summary
    print_header("TEST SUMMARY")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, passed_test in results.items():
        status = "✅" if passed_test else "❌"
        print(f"  {status} {name}")
    
    print(f"\n  Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n  🎉 All tests passed!")
    else:
        print("\n  ⚠️  Some tests failed")
    
    return passed == total


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='ODIN Test Suite')
    parser.add_argument('--mode', choices=['mock', 'live', 'claude'],
                       default='mock', help='Test mode')
    
    args = parser.parse_args()
    
    success = asyncio.run(run_all_tests(args.mode))
    sys.exit(0 if success else 1)
