# ODIN Multi-AI Orchestrator

**Outcome Determination Intelligence Network** - A production-ready autonomous system that coordinates 4 AI platforms (Claude, ChatGPT, Gemini, Perplexity) for biotech trading signal generation.

## 🎯 Overview

ODIN orchestrates multiple AI systems to analyze PDUFA (FDA drug approval) events and generate actionable trading signals. Each AI specializes in different aspects:

| AI | Specialization | Primary Tasks |
|---|---|---|
| **Claude** (Anthropic) | Deep reasoning, risk analysis | PDUFA probability, scenario modeling, thesis updates |
| **ChatGPT** (OpenAI) | Quantitative analysis | Options pricing, Greeks, IV analysis, strategy selection |
| **Gemini** (Google) | Information retrieval | SEC filings, insider transactions, FDA news scanning |
| **Perplexity** | Synthesis & verification | Signal aggregation, fact-checking, final recommendations |

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    ODIN ORCHESTRATOR                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │   Budget    │  │    Task     │  │   Autonomous        │ │
│  │  Controller │  │   Router    │  │   Loops             │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│ Shared Context│  │ Data Pipelines│  │  AI Workers   │
│ (Inter-AI     │  │ (FinBrain,   │  │ (Claude,      │
│  Memory)      │  │  LunarCrush) │  │  GPT, Gemini, │
└───────────────┘  └───────────────┘  │  Perplexity)  │
                                      └───────────────┘
```

## 📁 Project Structure

```
odin_orchestrator/
├── odin_orchestrator.py      # Main orchestrator (autonomous loops, task routing)
├── odin_ai_workers.py        # AI worker implementations with real API calls
├── odin_shared_context.py    # Inter-AI communication and memory system
├── odin_data_pipelines.py    # Data sources (FinBrain, LunarCrush, OpenFDA)
├── test_odin.py              # Test suite
├── watchlist.json            # Tickers to monitor
├── requirements.txt          # Python dependencies
├── .env.example              # API key template
└── README.md                 # This file
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure API Keys

Copy `.env.example` to `.env` and add your API keys:

```bash
cp .env.example .env
# Edit .env with your keys
```

Required keys for full functionality:
- `ANTHROPIC_API_KEY` - Claude API (primary reasoning)
- `OPENAI_API_KEY` - ChatGPT API (options analysis)
- `GEMINI_API_KEY` - Gemini API (information retrieval)
- `PERPLEXITY_API_KEY` - Perplexity API (signal synthesis)

Optional data source keys:
- `FINBRAIN_API_KEY` - Insider transactions, options flow
- `LUNARCRUSH_API_KEY` - Social sentiment

### 3. Run Tests

```bash
# Mock tests (no API keys needed)
python test_odin.py --mode mock

# Live test with Claude only
python test_odin.py --mode claude

# Full pipeline test
python test_odin.py --mode live
```

### 4. Start ODIN

```bash
# Check system status
python odin_orchestrator.py --mode status

# Single ticker analysis
python odin_orchestrator.py --mode single --ticker GUTS

# Full autonomous mode (runs continuously)
python odin_orchestrator.py --mode autonomous --budget standard
```

## 💰 Budget Tiers

ODIN includes built-in cost control to manage API spending:

| Tier | Daily Limit | Use Case |
|---|---|---|
| `minimal` | $15/day | Development, thesis updates only |
| `standard` | $50/day | Core monitoring, recommended for most users |
| `aggressive` | $150/day | Full autonomous mode, multiple tickers |
| `unlimited` | $500/day | Production trading, no throttling |

Budget is automatically distributed across AIs with per-AI limits and critical task reserves.

## 🔄 Autonomous Loops

When running in autonomous mode, ODIN maintains 4 monitoring loops:

| Loop | Interval | Purpose |
|---|---|---|
| **PDUFA Monitor** | 15 min | Track imminent PDUFA dates, analyze high-priority tickers |
| **Options Scan** | 5 min | Monitor IV, unusual activity, expected moves |
| **Insider Check** | Daily | Detect Form 4 filings, cluster buying patterns |
| **Thesis Update** | Weekly | Update investment theses, validate catalysts |

## 🧠 Inter-AI Collaboration

The **Shared Context** system enables AIs to build on each other's work:

```python
# Claude analyzes PDUFA risk
claude_finding = {
    "approval_probability": 0.72,
    "key_risks": ["CMC concerns"]
}

# ChatGPT sees Claude's analysis, factors into options strategy
chatgpt_prompt = f"""
Prior analysis from Claude: {context.get_context_for_ai(ticker, "openai")}
Recommend options strategy...
"""

# Perplexity synthesizes all findings
perplexity_prompt = f"""
All AI findings: {context.get_all_findings(ticker)}
Generate final recommendation...
"""
```

## 📊 Output Example

```
📊 Full Analysis Pipeline for GUTS
--------------------------------------------------
   🔄 GUTS → claude (pdufa_analysis)
   ✅ GUTS: confidence=85%, cost=$0.0847
   🔄 GUTS → openai (options_pricing)
   ✅ GUTS: confidence=78%, cost=$0.0523
   🔄 GUTS → gemini (insider_detection)
   ✅ GUTS: confidence=72%, cost=$0.0084
   🔄 GUTS → perplexity (signal_synthesis)
   ✅ GUTS: confidence=81%, cost=$0.0156

📋 Analysis Complete for GUTS
   Consensus: STRONG_BUY
   Approval Prob: 74%
   Contributing AIs: claude, openai, gemini, perplexity
```

## 🛠️ Customization

### Adding New Tickers

Edit `watchlist.json`:

```json
{
  "ticker": "NEW",
  "pdufa_date": "2025-06-15",
  "priority": "high",
  "btd": true,
  "notes": "First-in-class mechanism"
}
```

### Custom Analysis Pipeline

```python
from odin_orchestrator import OdinOrchestrator, BudgetTier

odin = OdinOrchestrator(budget_tier=BudgetTier.STANDARD)

# Run full pipeline for a ticker
results = await odin.analyze_ticker("GUTS", {
    "ticker": "GUTS",
    "drug": "SIM0323",
    "btd": True,
    "priority_review": True
})

# Access consensus
consensus = odin.shared_context.get_consensus("GUTS")
print(f"Action: {consensus['consensus_action']}")
print(f"Approval Probability: {consensus['weighted_approval_probability']:.0%}")
```

## 📈 Integration with ODIN Core

This orchestrator is designed to complement the main ODIN prediction system:

1. **Core ODIN** uses the enriched PDUFA dataset (1,349 events) for baseline predictions
2. **Multi-AI Orchestrator** adds real-time signals: options flow, insider activity, social sentiment
3. **Combined Signal** merges historical patterns with current market dynamics

## ⚠️ Disclaimers

- This is for educational and research purposes
- Not financial advice - always do your own due diligence
- API costs can accumulate - monitor your usage
- FDA decisions are inherently unpredictable

## 🔧 Troubleshooting

**"API key not configured"**
- Check your `.env` file contains the correct keys
- Ensure keys don't have extra whitespace

**"Budget limit exceeded"**
- Increase budget tier or wait for daily reset
- Critical PDUFA tasks use reserve budget

**"Rate limit error"**
- Built-in delays prevent most rate limits
- For persistent issues, increase inter-task delays

## 📜 License

MIT License - See LICENSE file for details

---

Built for the ODIN project by David | 2026
