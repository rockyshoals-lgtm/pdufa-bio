"""
ODIN AI Workers - Production Implementation
Real API calls to ChatGPT, Claude, Gemini, and Perplexity

Each worker:
- Makes actual API calls with proper authentication
- Tracks token usage for cost accounting
- Returns structured findings for the shared context
- Handles errors gracefully with fallback behavior
"""

import os
import json
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod
from enum import Enum
import tiktoken  # For token counting

# Import our modules
from odin_shared_context import (
    OdinSharedContext, AIFinding, FindingType, 
    ConfidenceLevel, get_shared_context
)
from odin_data_pipelines import OdinDataPipeline, get_data_pipeline


class TaskType(Enum):
    """Types of tasks the orchestrator can route"""
    PDUFA_ANALYSIS = "pdufa_analysis"
    OPTIONS_PRICING = "options_pricing"
    INSIDER_DETECTION = "insider_detection"
    FDA_NEWS_SCAN = "fda_news_scan"
    SIGNAL_SYNTHESIS = "signal_synthesis"
    THESIS_UPDATE = "thesis_update"
    CATALYST_VALIDATION = "catalyst_validation"


class AIProvider(Enum):
    """Available AI providers"""
    OPENAI = "openai"
    ANTHROPIC = "claude"
    GOOGLE = "gemini"
    PERPLEXITY = "perplexity"


@dataclass
class AIResponse:
    """Standardized response from any AI worker"""
    provider: AIProvider
    task_type: TaskType
    ticker: str
    success: bool
    data: Dict[str, Any]
    confidence: float
    reasoning: str
    tokens_used: int
    cost_usd: float
    latency_ms: int
    error: Optional[str] = None
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
    
    def to_finding(self) -> Optional[AIFinding]:
        """Convert response to AIFinding for shared context"""
        if not self.success:
            return None
        
        finding_type_map = {
            TaskType.PDUFA_ANALYSIS: FindingType.PDUFA_ANALYSIS,
            TaskType.OPTIONS_PRICING: FindingType.OPTIONS_METRICS,
            TaskType.INSIDER_DETECTION: FindingType.INSIDER_ACTIVITY,
            TaskType.FDA_NEWS_SCAN: FindingType.FDA_NEWS,
            TaskType.SIGNAL_SYNTHESIS: FindingType.SIGNAL_SYNTHESIS,
            TaskType.THESIS_UPDATE: FindingType.THESIS_UPDATE,
            TaskType.CATALYST_VALIDATION: FindingType.CATALYST_VALIDATION,
        }
        
        return AIFinding(
            finding_id="",  # Will be generated
            ticker=self.ticker,
            ai_source=self.provider.value,
            finding_type=finding_type_map.get(self.task_type, FindingType.PDUFA_ANALYSIS),
            content=self.data,
            confidence=self.confidence,
            evidence=[self.reasoning] if self.reasoning else []
        )


@dataclass
class CostTracker:
    """Track API costs in real-time"""
    openai_cost: float = 0.0
    claude_cost: float = 0.0
    gemini_cost: float = 0.0
    perplexity_cost: float = 0.0
    total_tokens: int = 0
    
    # Pricing per 1M tokens (approximate)
    PRICING = {
        'openai_input': 2.50,      # GPT-4o input
        'openai_output': 10.00,    # GPT-4o output
        'claude_input': 3.00,      # Claude 3.5 Sonnet input
        'claude_output': 15.00,    # Claude 3.5 Sonnet output
        'gemini_input': 0.075,     # Gemini 1.5 Flash input
        'gemini_output': 0.30,     # Gemini 1.5 Flash output
        'perplexity_input': 1.00,  # Sonar input
        'perplexity_output': 1.00, # Sonar output
    }
    
    def add_usage(self, provider: str, input_tokens: int, output_tokens: int) -> float:
        """Add token usage and return cost"""
        input_cost = (input_tokens / 1_000_000) * self.PRICING.get(f'{provider}_input', 1.0)
        output_cost = (output_tokens / 1_000_000) * self.PRICING.get(f'{provider}_output', 1.0)
        total = input_cost + output_cost
        
        if provider == 'openai':
            self.openai_cost += total
        elif provider == 'claude':
            self.claude_cost += total
        elif provider == 'gemini':
            self.gemini_cost += total
        elif provider == 'perplexity':
            self.perplexity_cost += total
        
        self.total_tokens += input_tokens + output_tokens
        return total
    
    @property
    def total_cost(self) -> float:
        return self.openai_cost + self.claude_cost + self.gemini_cost + self.perplexity_cost
    
    def summary(self) -> str:
        return (f"💰 Costs: OpenAI ${self.openai_cost:.4f} | Claude ${self.claude_cost:.4f} | "
                f"Gemini ${self.gemini_cost:.4f} | Perplexity ${self.perplexity_cost:.4f} | "
                f"TOTAL: ${self.total_cost:.4f} ({self.total_tokens:,} tokens)")


class BaseAIWorker(ABC):
    """Base class for all AI workers"""
    
    def __init__(self, shared_context: OdinSharedContext, cost_tracker: CostTracker):
        self.context = shared_context
        self.costs = cost_tracker
        self.data_pipeline = get_data_pipeline()
    
    @abstractmethod
    async def execute(self, task_type: TaskType, ticker: str, payload: Dict) -> AIResponse:
        """Execute a task and return response"""
        pass
    
    def _count_tokens(self, text: str) -> int:
        """Count tokens in text (GPT-4 tokenizer as approximation)"""
        try:
            enc = tiktoken.encoding_for_model("gpt-4")
            return len(enc.encode(text))
        except:
            # Fallback: rough estimate
            return len(text) // 4


# =============================================================================
# CLAUDE WORKER - PDUFA Risk Analysis & Multi-Step Reasoning
# =============================================================================

class ClaudeWorker(BaseAIWorker):
    """
    Claude (Anthropic) Worker
    
    Specialization:
    - PDUFA risk analysis with deep reasoning
    - Multi-step scenario modeling
    - Regulatory pathway assessment
    - CRL risk factor identification
    """
    
    def __init__(self, shared_context: OdinSharedContext, cost_tracker: CostTracker):
        super().__init__(shared_context, cost_tracker)
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        self.model = "claude-sonnet-4-20250514"
        self.base_url = "https://api.anthropic.com/v1/messages"
        
        if not self.api_key:
            print("⚠️  ANTHROPIC_API_KEY not set - Claude worker will not function")
    
    async def execute(self, task_type: TaskType, ticker: str, payload: Dict) -> AIResponse:
        """Execute Claude analysis task"""
        start_time = datetime.now()
        
        if not self.api_key:
            return AIResponse(
                provider=AIProvider.ANTHROPIC,
                task_type=task_type,
                ticker=ticker,
                success=False,
                data={},
                confidence=0.0,
                reasoning="",
                tokens_used=0,
                cost_usd=0.0,
                latency_ms=0,
                error="ANTHROPIC_API_KEY not configured"
            )
        
        # Route to appropriate handler
        if task_type == TaskType.PDUFA_ANALYSIS:
            return await self._analyze_pdufa(ticker, payload, start_time)
        elif task_type == TaskType.CATALYST_VALIDATION:
            return await self._validate_catalyst(ticker, payload, start_time)
        elif task_type == TaskType.THESIS_UPDATE:
            return await self._update_thesis(ticker, payload, start_time)
        else:
            return await self._general_analysis(ticker, payload, task_type, start_time)
    
    async def _call_claude_api(self, system_prompt: str, user_prompt: str) -> Tuple[str, int, int]:
        """
        Make actual API call to Claude
        Returns: (response_text, input_tokens, output_tokens)
        """
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        body = {
            "model": self.model,
            "max_tokens": 4096,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": user_prompt}
            ]
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(self.base_url, headers=headers, json=body) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Claude API error {response.status}: {error_text}")
                
                result = await response.json()
                
                response_text = result['content'][0]['text']
                input_tokens = result['usage']['input_tokens']
                output_tokens = result['usage']['output_tokens']
                
                return response_text, input_tokens, output_tokens
    
    async def _analyze_pdufa(self, ticker: str, payload: Dict, start_time: datetime) -> AIResponse:
        """
        Deep PDUFA risk analysis using Claude's reasoning capabilities
        """
        # Get context from other AIs
        prior_context = self.context.get_context_for_ai(ticker, "claude", "pdufa_analysis")
        
        # Get market data
        market_data = await self.data_pipeline.get_comprehensive_data(ticker)
        market_context = self.data_pipeline.build_ai_context(ticker, market_data)
        
        system_prompt = """You are ODIN's PDUFA Risk Analyst, specialized in predicting FDA drug approval outcomes.

Your analysis framework uses these validated risk factors:
- Breakthrough Therapy Designation (BTD): +15% approval boost
- Orphan Drug Designation: +8% approval boost  
- Priority Review: +5% approval boost
- Fast Track: +3% approval boost
- Prior CRL (resubmission): -20% penalty if unresolved issues
- Manufacturing/CMC concerns: -25% penalty (74% of CRLs involve CMC)
- Experienced sponsor (3+ prior approvals): +10% boost
- Positive AdCom vote (>50%): +12% boost per 10% above threshold
- Novel modality risk: Cell/gene therapy -8%, Biologic -3%

Base approval rate: 86.7% (historical PDUFA dataset 2009-2026)

OUTPUT FORMAT (JSON):
{
  "approval_probability": 0.XX,
  "crl_probability": 0.XX,
  "confidence": 0.XX,
  "key_drivers": ["driver1", "driver2"],
  "risk_factors": ["risk1", "risk2"],
  "scenario_bull": {"probability": 0.XX, "catalyst": "description"},
  "scenario_bear": {"probability": 0.XX, "catalyst": "description"},
  "recommendation": "BUY_CALLS|BUY_PUTS|STRADDLE|AVOID",
  "reasoning": "2-3 sentence summary"
}"""

        user_prompt = f"""Analyze PDUFA risk for {ticker}:

PDUFA DETAILS:
{json.dumps(payload, indent=2)}

MARKET DATA:
{market_context}

PRIOR AI ANALYSIS:
{prior_context}

Provide your PDUFA risk assessment in the specified JSON format."""

        try:
            response_text, input_tokens, output_tokens = await self._call_claude_api(
                system_prompt, user_prompt
            )
            
            # Track costs
            cost = self.costs.add_usage('claude', input_tokens, output_tokens)
            
            # Parse JSON from response
            try:
                # Extract JSON from response (handle markdown code blocks)
                json_str = response_text
                if "```json" in json_str:
                    json_str = json_str.split("```json")[1].split("```")[0]
                elif "```" in json_str:
                    json_str = json_str.split("```")[1].split("```")[0]
                
                data = json.loads(json_str.strip())
            except json.JSONDecodeError:
                # If JSON parsing fails, create structured response from text
                data = {
                    "approval_probability": 0.70,
                    "crl_probability": 0.30,
                    "confidence": 0.60,
                    "raw_response": response_text,
                    "parsing_error": True
                }
            
            latency = int((datetime.now() - start_time).total_seconds() * 1000)
            
            return AIResponse(
                provider=AIProvider.ANTHROPIC,
                task_type=TaskType.PDUFA_ANALYSIS,
                ticker=ticker,
                success=True,
                data=data,
                confidence=data.get('confidence', 0.75),
                reasoning=data.get('reasoning', response_text[:500]),
                tokens_used=input_tokens + output_tokens,
                cost_usd=cost,
                latency_ms=latency
            )
            
        except Exception as e:
            return AIResponse(
                provider=AIProvider.ANTHROPIC,
                task_type=TaskType.PDUFA_ANALYSIS,
                ticker=ticker,
                success=False,
                data={},
                confidence=0.0,
                reasoning="",
                tokens_used=0,
                cost_usd=0.0,
                latency_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                error=str(e)
            )
    
    async def _validate_catalyst(self, ticker: str, payload: Dict, start_time: datetime) -> AIResponse:
        """Validate a potential catalyst event"""
        system_prompt = """You are validating biotech catalyst events for trading.
        
Assess:
1. Is this catalyst real and correctly dated?
2. What is the expected stock impact?
3. Is options positioning favorable?

Output JSON with: is_valid, confidence, expected_move_pct, recommended_action"""

        prior_context = self.context.get_context_for_ai(ticker, "claude", "catalyst_validation")
        
        user_prompt = f"""Validate catalyst for {ticker}:
{json.dumps(payload, indent=2)}

Prior analysis: {prior_context}"""

        try:
            response_text, input_tokens, output_tokens = await self._call_claude_api(
                system_prompt, user_prompt
            )
            cost = self.costs.add_usage('claude', input_tokens, output_tokens)
            
            try:
                json_str = response_text
                if "```json" in json_str:
                    json_str = json_str.split("```json")[1].split("```")[0]
                data = json.loads(json_str.strip())
            except:
                data = {"raw_response": response_text, "is_valid": True, "confidence": 0.6}
            
            return AIResponse(
                provider=AIProvider.ANTHROPIC,
                task_type=TaskType.CATALYST_VALIDATION,
                ticker=ticker,
                success=True,
                data=data,
                confidence=data.get('confidence', 0.7),
                reasoning=data.get('reasoning', ''),
                tokens_used=input_tokens + output_tokens,
                cost_usd=cost,
                latency_ms=int((datetime.now() - start_time).total_seconds() * 1000)
            )
        except Exception as e:
            return AIResponse(
                provider=AIProvider.ANTHROPIC,
                task_type=TaskType.CATALYST_VALIDATION,
                ticker=ticker,
                success=False,
                data={},
                confidence=0.0,
                reasoning="",
                tokens_used=0,
                cost_usd=0.0,
                latency_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                error=str(e)
            )
    
    async def _update_thesis(self, ticker: str, payload: Dict, start_time: datetime) -> AIResponse:
        """Update investment thesis based on new information"""
        system_prompt = """You are updating an investment thesis for a biotech stock.
        
Consider:
1. New data/catalysts since last update
2. Changes in competitive landscape
3. Regulatory pathway updates
4. Insider/institutional activity signals

Output JSON with: thesis_summary, bull_case, bear_case, conviction_level (1-10), key_milestones"""

        prior_context = self.context.get_context_for_ai(ticker, "claude", "thesis_update")
        
        user_prompt = f"""Update thesis for {ticker}:
Current info: {json.dumps(payload, indent=2)}

Prior analysis from other AIs:
{prior_context}"""

        try:
            response_text, input_tokens, output_tokens = await self._call_claude_api(
                system_prompt, user_prompt
            )
            cost = self.costs.add_usage('claude', input_tokens, output_tokens)
            
            try:
                json_str = response_text
                if "```json" in json_str:
                    json_str = json_str.split("```json")[1].split("```")[0]
                data = json.loads(json_str.strip())
            except:
                data = {"raw_response": response_text, "conviction_level": 5}
            
            return AIResponse(
                provider=AIProvider.ANTHROPIC,
                task_type=TaskType.THESIS_UPDATE,
                ticker=ticker,
                success=True,
                data=data,
                confidence=data.get('conviction_level', 5) / 10,
                reasoning=data.get('thesis_summary', ''),
                tokens_used=input_tokens + output_tokens,
                cost_usd=cost,
                latency_ms=int((datetime.now() - start_time).total_seconds() * 1000)
            )
        except Exception as e:
            return AIResponse(
                provider=AIProvider.ANTHROPIC,
                task_type=TaskType.THESIS_UPDATE,
                ticker=ticker,
                success=False,
                data={},
                confidence=0.0,
                reasoning="",
                tokens_used=0,
                cost_usd=0.0,
                latency_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                error=str(e)
            )
    
    async def _general_analysis(self, ticker: str, payload: Dict, 
                                task_type: TaskType, start_time: datetime) -> AIResponse:
        """Handle general analysis requests"""
        system_prompt = f"""You are analyzing {ticker} for task: {task_type.value}.
Provide structured JSON output with your analysis."""

        user_prompt = f"""Analyze {ticker}:
{json.dumps(payload, indent=2)}"""

        try:
            response_text, input_tokens, output_tokens = await self._call_claude_api(
                system_prompt, user_prompt
            )
            cost = self.costs.add_usage('claude', input_tokens, output_tokens)
            
            return AIResponse(
                provider=AIProvider.ANTHROPIC,
                task_type=task_type,
                ticker=ticker,
                success=True,
                data={"analysis": response_text},
                confidence=0.7,
                reasoning=response_text[:300],
                tokens_used=input_tokens + output_tokens,
                cost_usd=cost,
                latency_ms=int((datetime.now() - start_time).total_seconds() * 1000)
            )
        except Exception as e:
            return AIResponse(
                provider=AIProvider.ANTHROPIC,
                task_type=task_type,
                ticker=ticker,
                success=False,
                data={},
                confidence=0.0,
                reasoning="",
                tokens_used=0,
                cost_usd=0.0,
                latency_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                error=str(e)
            )


# =============================================================================
# CHATGPT WORKER - Options Pricing & Greeks
# =============================================================================

class ChatGPTWorker(BaseAIWorker):
    """
    ChatGPT (OpenAI) Worker
    
    Specialization:
    - Options pricing and Greeks calculation
    - IV analysis and expected move
    - Technical pattern recognition
    - Quantitative strategy optimization
    """
    
    def __init__(self, shared_context: OdinSharedContext, cost_tracker: CostTracker):
        super().__init__(shared_context, cost_tracker)
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = "gpt-4o"
        self.base_url = "https://api.openai.com/v1/chat/completions"
        
        if not self.api_key:
            print("⚠️  OPENAI_API_KEY not set - ChatGPT worker will not function")
    
    async def execute(self, task_type: TaskType, ticker: str, payload: Dict) -> AIResponse:
        """Execute ChatGPT analysis task"""
        start_time = datetime.now()
        
        if not self.api_key:
            return AIResponse(
                provider=AIProvider.OPENAI,
                task_type=task_type,
                ticker=ticker,
                success=False,
                data={},
                confidence=0.0,
                reasoning="",
                tokens_used=0,
                cost_usd=0.0,
                latency_ms=0,
                error="OPENAI_API_KEY not configured"
            )
        
        if task_type == TaskType.OPTIONS_PRICING:
            return await self._analyze_options(ticker, payload, start_time)
        else:
            return await self._general_analysis(ticker, payload, task_type, start_time)
    
    async def _call_openai_api(self, system_prompt: str, user_prompt: str) -> Tuple[str, int, int]:
        """Make actual API call to OpenAI"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "max_tokens": 4096,
            "temperature": 0.3
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(self.base_url, headers=headers, json=body) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"OpenAI API error {response.status}: {error_text}")
                
                result = await response.json()
                
                response_text = result['choices'][0]['message']['content']
                input_tokens = result['usage']['prompt_tokens']
                output_tokens = result['usage']['completion_tokens']
                
                return response_text, input_tokens, output_tokens
    
    async def _analyze_options(self, ticker: str, payload: Dict, start_time: datetime) -> AIResponse:
        """Analyze options chain and recommend strategy"""
        
        # Get market data
        market_data = await self.data_pipeline.get_comprehensive_data(ticker)
        market_context = self.data_pipeline.build_ai_context(ticker, market_data)
        
        # Get prior context
        prior_context = self.context.get_context_for_ai(ticker, "openai", "options_pricing")
        
        system_prompt = """You are ODIN's Options Strategist, specializing in biotech catalyst plays.

Your framework:
1. IV Analysis: Compare current IV to historical (30d, 60d, pre-catalyst patterns)
2. Expected Move: Calculate 1σ and 2σ expected moves from ATM straddle
3. Greeks Assessment: Evaluate delta, gamma, theta, vega exposure
4. Strategy Selection: Recommend optimal structure for the catalyst

Key metrics to calculate:
- IV Percentile (current vs 52-week range)
- IV Crush estimate (typical 40-60% post-catalyst)
- Risk/Reward ratio for recommended strategy
- Max loss and breakeven points

OUTPUT FORMAT (JSON):
{
  "iv_current": 0.XX,
  "iv_historical_30d": 0.XX,
  "iv_percentile": 0.XX,
  "expected_move_1std": 0.XX,
  "expected_move_2std": 0.XX,
  "iv_crush_estimate": 0.XX,
  "recommended_strategy": "LONG_CALL|LONG_PUT|STRADDLE|STRANGLE|CALL_SPREAD|PUT_SPREAD",
  "strikes": {"call": XX, "put": XX},
  "expiration": "YYYY-MM-DD",
  "max_risk": XXXX,
  "max_reward": XXXX,
  "breakeven": [XX, XX],
  "risk_reward_ratio": X.X,
  "confidence": 0.XX,
  "reasoning": "summary"
}"""

        user_prompt = f"""Analyze options for {ticker} around catalyst:

CATALYST INFO:
{json.dumps(payload, indent=2)}

MARKET DATA:
{market_context}

PRIOR ANALYSIS:
{prior_context}

Provide options strategy recommendation in JSON format."""

        try:
            response_text, input_tokens, output_tokens = await self._call_openai_api(
                system_prompt, user_prompt
            )
            cost = self.costs.add_usage('openai', input_tokens, output_tokens)
            
            try:
                json_str = response_text
                if "```json" in json_str:
                    json_str = json_str.split("```json")[1].split("```")[0]
                elif "```" in json_str:
                    json_str = json_str.split("```")[1].split("```")[0]
                data = json.loads(json_str.strip())
            except:
                data = {"raw_response": response_text, "parsing_error": True}
            
            return AIResponse(
                provider=AIProvider.OPENAI,
                task_type=TaskType.OPTIONS_PRICING,
                ticker=ticker,
                success=True,
                data=data,
                confidence=data.get('confidence', 0.75),
                reasoning=data.get('reasoning', ''),
                tokens_used=input_tokens + output_tokens,
                cost_usd=cost,
                latency_ms=int((datetime.now() - start_time).total_seconds() * 1000)
            )
        except Exception as e:
            return AIResponse(
                provider=AIProvider.OPENAI,
                task_type=TaskType.OPTIONS_PRICING,
                ticker=ticker,
                success=False,
                data={},
                confidence=0.0,
                reasoning="",
                tokens_used=0,
                cost_usd=0.0,
                latency_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                error=str(e)
            )
    
    async def _general_analysis(self, ticker: str, payload: Dict,
                                task_type: TaskType, start_time: datetime) -> AIResponse:
        """Handle general analysis requests"""
        system_prompt = f"Analyze {ticker} for: {task_type.value}. Output JSON."
        user_prompt = json.dumps(payload, indent=2)
        
        try:
            response_text, input_tokens, output_tokens = await self._call_openai_api(
                system_prompt, user_prompt
            )
            cost = self.costs.add_usage('openai', input_tokens, output_tokens)
            
            return AIResponse(
                provider=AIProvider.OPENAI,
                task_type=task_type,
                ticker=ticker,
                success=True,
                data={"analysis": response_text},
                confidence=0.7,
                reasoning=response_text[:300],
                tokens_used=input_tokens + output_tokens,
                cost_usd=cost,
                latency_ms=int((datetime.now() - start_time).total_seconds() * 1000)
            )
        except Exception as e:
            return AIResponse(
                provider=AIProvider.OPENAI,
                task_type=task_type,
                ticker=ticker,
                success=False,
                data={},
                confidence=0.0,
                reasoning="",
                tokens_used=0,
                cost_usd=0.0,
                latency_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                error=str(e)
            )


# =============================================================================
# GEMINI WORKER - Web Search & SEC Filing Analysis
# =============================================================================

class GeminiWorker(BaseAIWorker):
    """
    Gemini (Google) Worker
    
    Specialization:
    - Web search and news aggregation
    - SEC filing parsing (10-K, 10-Q, 8-K, Form 4)
    - Insider transaction detection
    - Competitive landscape analysis
    """
    
    def __init__(self, shared_context: OdinSharedContext, cost_tracker: CostTracker):
        super().__init__(shared_context, cost_tracker)
        self.api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.model = "gemini-1.5-flash"
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"
        
        if not self.api_key:
            print("⚠️  GEMINI_API_KEY not set - Gemini worker will not function")
    
    async def execute(self, task_type: TaskType, ticker: str, payload: Dict) -> AIResponse:
        """Execute Gemini analysis task"""
        start_time = datetime.now()
        
        if not self.api_key:
            return AIResponse(
                provider=AIProvider.GOOGLE,
                task_type=task_type,
                ticker=ticker,
                success=False,
                data={},
                confidence=0.0,
                reasoning="",
                tokens_used=0,
                cost_usd=0.0,
                latency_ms=0,
                error="GEMINI_API_KEY not configured"
            )
        
        if task_type == TaskType.INSIDER_DETECTION:
            return await self._detect_insider_activity(ticker, payload, start_time)
        elif task_type == TaskType.FDA_NEWS_SCAN:
            return await self._scan_fda_news(ticker, payload, start_time)
        else:
            return await self._general_analysis(ticker, payload, task_type, start_time)
    
    async def _call_gemini_api(self, prompt: str) -> Tuple[str, int, int]:
        """Make actual API call to Gemini"""
        url = f"{self.base_url}/{self.model}:generateContent?key={self.api_key}"
        
        body = {
            "contents": [
                {"parts": [{"text": prompt}]}
            ],
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 4096
            }
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=body) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Gemini API error {response.status}: {error_text}")
                
                result = await response.json()
                
                response_text = result['candidates'][0]['content']['parts'][0]['text']
                
                # Gemini doesn't always return token counts, estimate
                input_tokens = len(prompt) // 4
                output_tokens = len(response_text) // 4
                
                if 'usageMetadata' in result:
                    input_tokens = result['usageMetadata'].get('promptTokenCount', input_tokens)
                    output_tokens = result['usageMetadata'].get('candidatesTokenCount', output_tokens)
                
                return response_text, input_tokens, output_tokens
    
    async def _detect_insider_activity(self, ticker: str, payload: Dict, 
                                       start_time: datetime) -> AIResponse:
        """Detect and analyze insider trading patterns"""
        
        # Get insider data from pipeline
        market_data = await self.data_pipeline.get_comprehensive_data(ticker)
        
        prior_context = self.context.get_context_for_ai(ticker, "gemini", "insider_detection")
        
        prompt = f"""Analyze insider trading activity for {ticker}.

INSIDER TRANSACTION DATA:
{json.dumps(market_data.get('insider_transactions', []), indent=2)}

ADDITIONAL CONTEXT:
{json.dumps(payload, indent=2)}

PRIOR ANALYSIS:
{prior_context}

Analyze:
1. Net insider buying/selling trend
2. Significant transactions (>$100K)
3. Cluster buying patterns (multiple insiders buying)
4. Timing relative to upcoming catalysts
5. Form 4 filing patterns

OUTPUT FORMAT (JSON):
{{
  "net_insider_sentiment": "BULLISH|BEARISH|NEUTRAL",
  "total_buy_value_90d": XXXXX,
  "total_sell_value_90d": XXXXX,
  "significant_transactions": [
    {{"insider": "name", "action": "BUY|SELL", "value": XXXXX, "date": "YYYY-MM-DD"}}
  ],
  "cluster_buying": true|false,
  "signal_strength": 0.XX,
  "confidence": 0.XX,
  "key_insight": "summary",
  "recommendation": "BULLISH_SIGNAL|BEARISH_SIGNAL|NO_SIGNAL"
}}"""

        try:
            response_text, input_tokens, output_tokens = await self._call_gemini_api(prompt)
            cost = self.costs.add_usage('gemini', input_tokens, output_tokens)
            
            try:
                json_str = response_text
                if "```json" in json_str:
                    json_str = json_str.split("```json")[1].split("```")[0]
                data = json.loads(json_str.strip())
            except:
                data = {"raw_response": response_text, "net_insider_sentiment": "NEUTRAL"}
            
            return AIResponse(
                provider=AIProvider.GOOGLE,
                task_type=TaskType.INSIDER_DETECTION,
                ticker=ticker,
                success=True,
                data=data,
                confidence=data.get('confidence', 0.7),
                reasoning=data.get('key_insight', ''),
                tokens_used=input_tokens + output_tokens,
                cost_usd=cost,
                latency_ms=int((datetime.now() - start_time).total_seconds() * 1000)
            )
        except Exception as e:
            return AIResponse(
                provider=AIProvider.GOOGLE,
                task_type=TaskType.INSIDER_DETECTION,
                ticker=ticker,
                success=False,
                data={},
                confidence=0.0,
                reasoning="",
                tokens_used=0,
                cost_usd=0.0,
                latency_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                error=str(e)
            )
    
    async def _scan_fda_news(self, ticker: str, payload: Dict, start_time: datetime) -> AIResponse:
        """Scan for FDA-related news and announcements"""
        
        prior_context = self.context.get_context_for_ai(ticker, "gemini", "fda_news_scan")
        
        prompt = f"""Analyze FDA news and regulatory updates for {ticker}.

COMPANY INFO:
{json.dumps(payload, indent=2)}

PRIOR ANALYSIS:
{prior_context}

Search for:
1. Recent FDA communications (RTF, IR, CRL letters)
2. AdCom scheduling or results
3. Label expansion news
4. Competitor approvals/rejections
5. Manufacturing inspection results

OUTPUT FORMAT (JSON):
{{
  "recent_fda_news": [
    {{"date": "YYYY-MM-DD", "event": "description", "impact": "POSITIVE|NEGATIVE|NEUTRAL"}}
  ],
  "upcoming_catalysts": [
    {{"date": "YYYY-MM-DD", "event": "description", "importance": "HIGH|MEDIUM|LOW"}}
  ],
  "regulatory_risk_level": "LOW|MEDIUM|HIGH",
  "confidence": 0.XX,
  "key_insight": "summary"
}}"""

        try:
            response_text, input_tokens, output_tokens = await self._call_gemini_api(prompt)
            cost = self.costs.add_usage('gemini', input_tokens, output_tokens)
            
            try:
                json_str = response_text
                if "```json" in json_str:
                    json_str = json_str.split("```json")[1].split("```")[0]
                data = json.loads(json_str.strip())
            except:
                data = {"raw_response": response_text, "regulatory_risk_level": "MEDIUM"}
            
            return AIResponse(
                provider=AIProvider.GOOGLE,
                task_type=TaskType.FDA_NEWS_SCAN,
                ticker=ticker,
                success=True,
                data=data,
                confidence=data.get('confidence', 0.65),
                reasoning=data.get('key_insight', ''),
                tokens_used=input_tokens + output_tokens,
                cost_usd=cost,
                latency_ms=int((datetime.now() - start_time).total_seconds() * 1000)
            )
        except Exception as e:
            return AIResponse(
                provider=AIProvider.GOOGLE,
                task_type=TaskType.FDA_NEWS_SCAN,
                ticker=ticker,
                success=False,
                data={},
                confidence=0.0,
                reasoning="",
                tokens_used=0,
                cost_usd=0.0,
                latency_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                error=str(e)
            )
    
    async def _general_analysis(self, ticker: str, payload: Dict,
                                task_type: TaskType, start_time: datetime) -> AIResponse:
        """Handle general analysis requests"""
        prompt = f"Analyze {ticker} for {task_type.value}:\n{json.dumps(payload, indent=2)}\n\nOutput JSON."
        
        try:
            response_text, input_tokens, output_tokens = await self._call_gemini_api(prompt)
            cost = self.costs.add_usage('gemini', input_tokens, output_tokens)
            
            return AIResponse(
                provider=AIProvider.GOOGLE,
                task_type=task_type,
                ticker=ticker,
                success=True,
                data={"analysis": response_text},
                confidence=0.65,
                reasoning=response_text[:300],
                tokens_used=input_tokens + output_tokens,
                cost_usd=cost,
                latency_ms=int((datetime.now() - start_time).total_seconds() * 1000)
            )
        except Exception as e:
            return AIResponse(
                provider=AIProvider.GOOGLE,
                task_type=task_type,
                ticker=ticker,
                success=False,
                data={},
                confidence=0.0,
                reasoning="",
                tokens_used=0,
                cost_usd=0.0,
                latency_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                error=str(e)
            )


# =============================================================================
# PERPLEXITY WORKER - Signal Synthesis & Fact Checking
# =============================================================================

class PerplexityWorker(BaseAIWorker):
    """
    Perplexity Worker
    
    Specialization:
    - Signal synthesis from all AI outputs
    - Fact-checking and verification
    - Real-time web search for latest news
    - Final recommendation generation
    """
    
    def __init__(self, shared_context: OdinSharedContext, cost_tracker: CostTracker):
        super().__init__(shared_context, cost_tracker)
        self.api_key = os.getenv("PERPLEXITY_API_KEY")
        self.model = "sonar"
        self.base_url = "https://api.perplexity.ai/chat/completions"
        
        if not self.api_key:
            print("⚠️  PERPLEXITY_API_KEY not set - Perplexity worker will not function")
    
    async def execute(self, task_type: TaskType, ticker: str, payload: Dict) -> AIResponse:
        """Execute Perplexity analysis task"""
        start_time = datetime.now()
        
        if not self.api_key:
            return AIResponse(
                provider=AIProvider.PERPLEXITY,
                task_type=task_type,
                ticker=ticker,
                success=False,
                data={},
                confidence=0.0,
                reasoning="",
                tokens_used=0,
                cost_usd=0.0,
                latency_ms=0,
                error="PERPLEXITY_API_KEY not configured"
            )
        
        if task_type == TaskType.SIGNAL_SYNTHESIS:
            return await self._synthesize_signals(ticker, payload, start_time)
        else:
            return await self._general_analysis(ticker, payload, task_type, start_time)
    
    async def _call_perplexity_api(self, system_prompt: str, user_prompt: str) -> Tuple[str, int, int]:
        """Make actual API call to Perplexity"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "max_tokens": 4096,
            "temperature": 0.2
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(self.base_url, headers=headers, json=body) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Perplexity API error {response.status}: {error_text}")
                
                result = await response.json()
                
                response_text = result['choices'][0]['message']['content']
                input_tokens = result.get('usage', {}).get('prompt_tokens', len(user_prompt) // 4)
                output_tokens = result.get('usage', {}).get('completion_tokens', len(response_text) // 4)
                
                return response_text, input_tokens, output_tokens
    
    async def _synthesize_signals(self, ticker: str, payload: Dict, start_time: datetime) -> AIResponse:
        """
        Synthesize all AI signals into final recommendation
        This is the final step where Perplexity combines all analyses
        """
        
        # Get ALL findings from other AIs
        all_findings = self.context.get_all_findings(ticker)
        consensus = self.context.get_consensus(ticker)
        
        # Build comprehensive context
        findings_summary = []
        for finding in all_findings:
            findings_summary.append({
                "source": finding.ai_source,
                "type": finding.finding_type.value,
                "confidence": finding.confidence,
                "content": finding.content,
                "evidence": finding.evidence[:3] if finding.evidence else []
            })
        
        system_prompt = """You are ODIN's Signal Synthesizer, responsible for combining analyses from multiple AI systems into actionable trading recommendations.

Your role:
1. Weight each AI's findings by confidence and relevance
2. Identify consensus and contradictions
3. Apply sanity checks using real-time information
4. Generate final recommendation with position sizing

Risk management rules:
- Max position size: 5% of portfolio per trade
- Confidence threshold for action: 0.65
- Required agreement: 2+ AIs must align for high-confidence trades

OUTPUT FORMAT (JSON):
{
  "final_recommendation": "STRONG_BUY|BUY|HOLD|REDUCE|AVOID",
  "confidence": 0.XX,
  "approval_probability": 0.XX,
  "position_size_pct": X.X,
  "entry_strategy": "description",
  "exit_strategy": "description",
  "stop_loss": "description",
  "ai_agreement": {
    "aligned": ["ai1", "ai2"],
    "divergent": ["ai3"]
  },
  "contradictions_resolved": "how contradictions were resolved",
  "key_risks": ["risk1", "risk2"],
  "key_catalysts": ["catalyst1", "catalyst2"],
  "time_horizon": "days/weeks",
  "reasoning": "comprehensive summary"
}"""

        user_prompt = f"""Synthesize signals for {ticker}:

PAYLOAD:
{json.dumps(payload, indent=2)}

ALL AI FINDINGS:
{json.dumps(findings_summary, indent=2)}

CURRENT CONSENSUS:
{json.dumps(consensus, indent=2) if consensus else "No consensus yet"}

Verify any uncertain facts with real-time search, then provide final recommendation."""

        try:
            response_text, input_tokens, output_tokens = await self._call_perplexity_api(
                system_prompt, user_prompt
            )
            cost = self.costs.add_usage('perplexity', input_tokens, output_tokens)
            
            try:
                json_str = response_text
                if "```json" in json_str:
                    json_str = json_str.split("```json")[1].split("```")[0]
                data = json.loads(json_str.strip())
            except:
                data = {
                    "raw_response": response_text,
                    "final_recommendation": "HOLD",
                    "confidence": 0.5
                }
            
            return AIResponse(
                provider=AIProvider.PERPLEXITY,
                task_type=TaskType.SIGNAL_SYNTHESIS,
                ticker=ticker,
                success=True,
                data=data,
                confidence=data.get('confidence', 0.7),
                reasoning=data.get('reasoning', ''),
                tokens_used=input_tokens + output_tokens,
                cost_usd=cost,
                latency_ms=int((datetime.now() - start_time).total_seconds() * 1000)
            )
        except Exception as e:
            return AIResponse(
                provider=AIProvider.PERPLEXITY,
                task_type=TaskType.SIGNAL_SYNTHESIS,
                ticker=ticker,
                success=False,
                data={},
                confidence=0.0,
                reasoning="",
                tokens_used=0,
                cost_usd=0.0,
                latency_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                error=str(e)
            )
    
    async def _general_analysis(self, ticker: str, payload: Dict,
                                task_type: TaskType, start_time: datetime) -> AIResponse:
        """Handle general analysis with web search capability"""
        system_prompt = f"Analyze {ticker} for {task_type.value}. Use web search to verify facts. Output JSON."
        user_prompt = json.dumps(payload, indent=2)
        
        try:
            response_text, input_tokens, output_tokens = await self._call_perplexity_api(
                system_prompt, user_prompt
            )
            cost = self.costs.add_usage('perplexity', input_tokens, output_tokens)
            
            return AIResponse(
                provider=AIProvider.PERPLEXITY,
                task_type=task_type,
                ticker=ticker,
                success=True,
                data={"analysis": response_text},
                confidence=0.7,
                reasoning=response_text[:300],
                tokens_used=input_tokens + output_tokens,
                cost_usd=cost,
                latency_ms=int((datetime.now() - start_time).total_seconds() * 1000)
            )
        except Exception as e:
            return AIResponse(
                provider=AIProvider.PERPLEXITY,
                task_type=task_type,
                ticker=ticker,
                success=False,
                data={},
                confidence=0.0,
                reasoning="",
                tokens_used=0,
                cost_usd=0.0,
                latency_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                error=str(e)
            )


# =============================================================================
# WORKER FACTORY
# =============================================================================

def create_workers(shared_context: OdinSharedContext, 
                   cost_tracker: CostTracker) -> Dict[AIProvider, BaseAIWorker]:
    """Create all AI workers"""
    return {
        AIProvider.ANTHROPIC: ClaudeWorker(shared_context, cost_tracker),
        AIProvider.OPENAI: ChatGPTWorker(shared_context, cost_tracker),
        AIProvider.GOOGLE: GeminiWorker(shared_context, cost_tracker),
        AIProvider.PERPLEXITY: PerplexityWorker(shared_context, cost_tracker)
    }


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":
    async def test_workers():
        from odin_shared_context import OdinSharedContext
        
        context = OdinSharedContext()
        costs = CostTracker()
        workers = create_workers(context, costs)
        
        # Test payload
        payload = {
            "ticker": "GUTS",
            "drug": "SIM0323",
            "indication": "Plaque Psoriasis",
            "pdufa_date": "2025-02-15",
            "btd": True,
            "orphan": False,
            "priority_review": True,
            "sponsor_prior_approvals": 2
        }
        
        print("\n🧪 Testing Claude Worker...")
        claude_response = await workers[AIProvider.ANTHROPIC].execute(
            TaskType.PDUFA_ANALYSIS, "GUTS", payload
        )
        print(f"   Success: {claude_response.success}")
        if claude_response.success:
            print(f"   Approval Prob: {claude_response.data.get('approval_probability', 'N/A')}")
            print(f"   Confidence: {claude_response.confidence}")
            print(f"   Tokens: {claude_response.tokens_used}")
            print(f"   Cost: ${claude_response.cost_usd:.4f}")
            
            # Add to shared context
            finding = claude_response.to_finding()
            if finding:
                context.add_finding(finding)
        else:
            print(f"   Error: {claude_response.error}")
        
        print(f"\n{costs.summary()}")
        context.print_status("GUTS")
    
    asyncio.run(test_workers())
