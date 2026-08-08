#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════╗
║  9REALMS — AI ADVISOR: LLM-in-the-Loop Training Optimizer              ║
║                                                                          ║
║  Periodically calls Perplexity API to analyze training state and         ║
║  generate intelligent optimization suggestions:                          ║
║    • Feature engineering ideas (new interactions to try)                 ║
║    • Hyperparameter adjustments (mutation, temperature, search width)    ║
║    • Feature gating (force-include proven, block dead-weight)           ║
║    • Strategy shifts (exploit vs explore, ensemble composition)          ║
║    • Discovery engine guidance (prioritize transform types)             ║
║                                                                          ║
║  Trigger conditions:                                                     ║
║    • Every N rounds (default 25)                                        ║
║    • On plateau detection (streak >= threshold)                         ║
║    • On new champion promotion (analyze what worked)                    ║
║                                                                          ║
║  Requires: PERPLEXITY_API_KEY environment variable or .env file         ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path

log = logging.getLogger("ai_advisor")

# ═══════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════
AI_ADVISOR_INTERVAL = 25          # Call AI every N rounds
AI_ADVISOR_PLATEAU_TRIGGER = 15   # Also call if streak >= this
AI_ADVISOR_ON_PROMOTION = True    # Call after every promotion
AI_ADVISOR_COOLDOWN_S = 120       # Min seconds between calls
AI_ADVISOR_MAX_TOKENS = 2048
AI_ADVISOR_TEMPERATURE = 0.3     # Low temp for structured recommendations

# State persistence
AI_ADVISOR_LOG_PATH = None        # Set at init
AI_ADVISOR_STATE_PATH = None      # Set at init

PERPLEXITY_BASE_URL = "https://api.perplexity.ai"
DEEPSEEK_BASE_URL   = "https://api.deepseek.com"

# Backend model names
MODELS = {
    "anthropic": "claude-haiku-4-5-20251001",   # Fast + cheap, great for structured JSON
    "deepseek":  "deepseek-chat",               # DeepSeek-V3 — OpenAI-compat, very cheap
    "perplexity": "sonar-pro",
    "openai": "gpt-4o-mini",
}


def _load_api_key():
    """Load API key from env var or .env file.

    Priority:
      1. ANTHROPIC_API_KEY  (claude-haiku — recommended, most reliable)
      2. PERPLEXITY_API_KEY / PPLX_API_KEY
      3. OPENAI_API_KEY

    Returns: (key, backend_name) tuple
    """
    # Check env vars in priority order
    checks = [
        ("ANTHROPIC_API_KEY",  "anthropic"),
        ("DEEPSEEK_API_KEY",   "deepseek"),
        ("PERPLEXITY_API_KEY", "perplexity"),
        ("PPLX_API_KEY",       "perplexity"),
        ("OPENAI_API_KEY",     "openai"),
    ]

    for env_name, backend in checks:
        key = os.environ.get(env_name)
        if key:
            return key, backend

    # Try .env files
    for env_path in [
        Path(__file__).resolve().parent.parent / ".env",
        Path(__file__).resolve().parent / ".env",
        Path.home() / ".env",
    ]:
        if env_path.exists():
            try:
                with open(env_path) as f:
                    lines = f.read().splitlines()
                for line in lines:
                    line = line.strip()
                    for env_name, backend in checks:
                        if line.startswith(f"{env_name}="):
                            val = line.split("=", 1)[1].strip().strip('"').strip("'")
                            if val:
                                return val, backend
            except Exception:
                pass

    return None, None


class AIAdvisor:
    """LLM-powered training optimization advisor."""

    def __init__(self, kaizen_dir: Path, model_name: str = "odin"):
        self.kaizen_dir = kaizen_dir
        self.model_name = model_name
        self.api_key, self.backend = _load_api_key()
        self.enabled = self.api_key is not None
        self.last_call_time = 0
        self.total_calls = 0
        self.total_suggestions_applied = 0

        # Set model name based on detected backend
        self.ai_model = MODELS.get(self.backend, "sonar-pro") if self.backend else "sonar-pro"

        # State paths
        self.log_path = kaizen_dir / "ai_advisor_log.jsonl"
        self.state_path = kaizen_dir / "ai_advisor_state.json"

        # Load persisted state
        self._load_state()

        if not self.enabled:
            log.warning("  🤖 AI Advisor: DISABLED — no API key found")
            log.warning("     Add ANTHROPIC_API_KEY=sk-ant-... to 9realms/.env (recommended)")
            log.warning("     Or PERPLEXITY_API_KEY=pplx-... (requires valid Perplexity Pro key)")
        else:
            log.info(f"  🤖 AI Advisor: ENABLED (backend={self.backend}, model={self.ai_model})")
            log.info(f"     Interval: every {AI_ADVISOR_INTERVAL} rounds, "
                     f"plateau trigger: {AI_ADVISOR_PLATEAU_TRIGGER} streak, "
                     f"on promotion: {AI_ADVISOR_ON_PROMOTION}")
            log.info(f"     Total calls so far: {self.total_calls}")

    def _load_state(self):
        """Load persisted advisor state."""
        if self.state_path.exists():
            try:
                with open(self.state_path) as f:
                    state = json.load(f)
                self.total_calls = state.get("total_calls", 0)
                self.total_suggestions_applied = state.get("total_suggestions_applied", 0)
                self.last_call_time = state.get("last_call_time", 0)
            except Exception:
                pass

    def _save_state(self):
        """Persist advisor state."""
        state = {
            "total_calls": self.total_calls,
            "total_suggestions_applied": self.total_suggestions_applied,
            "last_call_time": self.last_call_time,
            "last_saved": datetime.now().isoformat(),
        }
        try:
            with open(self.state_path, "w") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            log.warning(f"  🤖 AI Advisor: failed to save state: {e}")

    def _log_interaction(self, trigger, prompt_summary, response_summary, suggestions):
        """Append interaction to JSONL log."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "trigger": trigger,
            "call_number": self.total_calls,
            "prompt_chars": len(prompt_summary),
            "response_chars": len(response_summary),
            "suggestions_count": len(suggestions),
            "suggestions": suggestions,
        }
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            log.warning(f"  🤖 AI Advisor: failed to log interaction: {e}")

    def should_trigger(self, round_num, streak, promoted):
        """Determine if AI advisor should run this round."""
        if not self.enabled:
            return False, ""

        # Cooldown check
        elapsed = time.time() - self.last_call_time
        if elapsed < AI_ADVISOR_COOLDOWN_S:
            return False, ""

        # Trigger conditions
        if promoted and AI_ADVISOR_ON_PROMOTION:
            return True, "promotion"
        if streak >= AI_ADVISOR_PLATEAU_TRIGGER:
            return True, "plateau"
        if round_num % AI_ADVISOR_INTERVAL == 0 and round_num > 0:
            return True, "interval"

        return False, ""

    def consult(self, training_state: dict, trigger: str) -> dict:
        """Call AI API for optimization suggestions.

        Supports multiple backends in priority order:
          1. Anthropic (Claude) — most reliable, structured JSON output
          2. Perplexity (sonar-pro) — requires valid Perplexity Pro API key
          3. OpenAI (gpt-4o-mini) — fallback

        Args:
            training_state: Dict with current training metrics, features, params etc.
            trigger: Why we're calling ("promotion", "plateau", "interval")

        Returns:
            Dict with keys: feature_gate, feature_block, mutation_rate, temperature,
                           search_width, new_feature_ideas, strategy_notes
        """
        if not self.enabled:
            return {}

        prompt = self._build_prompt(training_state, trigger)
        log.info(f"  🤖 AI Advisor: Consulting {self.backend}/{self.ai_model} ({trigger} trigger)...")

        try:
            if self.backend == "anthropic":
                response_text = self._call_anthropic(prompt)
            else:
                response_text = self._call_openai_compat(prompt)

            if not response_text:
                return {}

            self.last_call_time = time.time()
            self.total_calls += 1

            suggestions = self._parse_response(response_text)
            self._log_interaction(trigger, prompt[:500], response_text[:500], suggestions)
            self._save_state()

            log.info(f"  🤖 AI Advisor: Got {len(suggestions)} actionable suggestions")
            return suggestions

        except Exception as e:
            log.error(f"  🤖 AI Advisor: API call failed: {e}")
            return {}

    def _call_anthropic(self, prompt: str) -> str:
        """Call Anthropic Claude API directly."""
        try:
            import anthropic
        except ImportError:
            log.warning("  🤖 Installing anthropic SDK...")
            os.system("pip install anthropic --break-system-packages -q")
            import anthropic

        client = anthropic.Anthropic(api_key=self.api_key)
        msg = client.messages.create(
            model=self.ai_model,
            max_tokens=AI_ADVISOR_MAX_TOKENS,
            system="You are an expert ML training optimizer. Respond ONLY with valid JSON, no prose.",
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text

    def _call_openai_compat(self, prompt: str) -> str:
        """Call OpenAI-compatible endpoint (Perplexity or OpenAI)."""
        try:
            from openai import OpenAI
        except ImportError:
            log.warning("  🤖 Installing openai SDK...")
            os.system("pip install openai --break-system-packages -q")
            from openai import OpenAI

        base_url_map = {
            "perplexity": PERPLEXITY_BASE_URL,
            "deepseek":   DEEPSEEK_BASE_URL,
        }
        base_url = base_url_map.get(self.backend)
        client = OpenAI(api_key=self.api_key, base_url=base_url)

        response = client.chat.completions.create(
            model=self.ai_model,
            max_tokens=AI_ADVISOR_MAX_TOKENS,
            temperature=AI_ADVISOR_TEMPERATURE,
            messages=[
                {"role": "system", "content": "You are an expert ML training optimizer. Respond ONLY with valid JSON, no prose."},
                {"role": "user", "content": prompt},
            ],
        )
        return response.choices[0].message.content

    def _build_prompt(self, state: dict, trigger: str) -> str:
        """Build the optimization prompt for Claude."""

        # Extract key metrics
        champion = state.get("champion", {})
        kaizen = state.get("kaizen", {})
        discovery = state.get("discovery", {})
        recent_rounds = state.get("recent_rounds", [])
        feature_importance = state.get("feature_importance", {})
        feature_hits = state.get("feature_hits", {})
        feature_appearances = state.get("feature_appearances", {})

        # Compute feature win rates
        win_rates = {}
        for feat, hits in feature_hits.items():
            apps = feature_appearances.get(feat, 1)
            win_rates[feat] = round(hits / max(apps, 1), 3)
        top_features = sorted(win_rates.items(), key=lambda x: x[1], reverse=True)[:15]
        dead_features = [f for f, wr in win_rates.items() if wr == 0 and feature_appearances.get(f, 0) >= 10]

        # Recent AUC trend
        recent_aucs = [r.get("wf_auc", 0) for r in recent_rounds[-20:]]
        auc_trend = "unknown"
        if len(recent_aucs) >= 6:
            first_half = sum(recent_aucs[:len(recent_aucs)//2]) / (len(recent_aucs)//2)
            second_half = sum(recent_aucs[len(recent_aucs)//2:]) / (len(recent_aucs) - len(recent_aucs)//2)
            diff = second_half - first_half
            if diff > 0.001:
                auc_trend = f"improving (+{diff:.4f})"
            elif diff < -0.001:
                auc_trend = f"degrading ({diff:.4f})"
            else:
                auc_trend = f"plateau (Δ={diff:.5f})"

        prompt = f"""You are the AI optimization advisor for the 9REALMS ODIN model — a LightGBM binary classifier predicting FDA PDUFA approval outcomes (APPROVAL vs CRL).

## TRIGGER: {trigger.upper()}
{f"A new champion was just promoted! Analyze what worked." if trigger == "promotion" else ""}
{f"Training is stuck in a plateau for {kaizen.get('streak', '?')} rounds. Help break through." if trigger == "plateau" else ""}
{f"Periodic check-in every {AI_ADVISOR_INTERVAL} rounds." if trigger == "interval" else ""}

## CURRENT STATE
- **Champion AUC**: {champion.get('wf_auc', 'N/A')}
- **Champion Brier**: {champion.get('wf_brier', 'N/A')}
- **Yearly AUCs**: {champion.get('yearly_aucs', [])}
- **Total Rounds**: {kaizen.get('total_rounds', 0)}
- **Total Promotions**: {kaizen.get('total_promotions', 0)}
- **Current Streak** (rounds since last promotion): {kaizen.get('streak', 0)}
- **Longest Streak**: {kaizen.get('longest_streak', 0)}
- **AUC Trend** (last 20 rounds): {auc_trend}
- **Ensemble In-Sample AUC**: {champion.get('ensemble_auc_insample', 'N/A')}

## ADAPTIVE PARAMETERS
- **Mutation Rate**: {kaizen.get('mutation_rate', 0.3)} (range: 0.10-0.65)
- **Temperature**: {kaizen.get('temperature', 1.0)} (range: 0.5-2.5)
- **Search Width**: {kaizen.get('search_width', 1.0)} (multiplier on Optuna trials, range: 0.5-3.5)

## CHAMPION FEATURES
- **Feature count**: {champion.get('n_features', '?')}
- **Engineered features in champion**: {champion.get('eng_features', [])}
- **Top importance** (by split count):
{json.dumps(dict(list(feature_importance.items())[:15]), indent=2) if feature_importance else "  N/A"}

## FEATURE WIN RATES (hits / appearances → win_rate)
Top performers:
{chr(10).join(f"  - {name}: {wr:.3f} ({feature_hits.get(name,0)}/{feature_appearances.get(name,1)})" for name, wr in top_features)}

Dead features (0% win rate, 10+ appearances):
{chr(10).join(f"  - {name} ({feature_appearances.get(name,0)} appearances)" for name in dead_features[:10]) if dead_features else "  None yet"}

## FEATURE DISCOVERY ENGINE
- **Pool size**: {discovery.get('pool_size', 0)} / {discovery.get('max_pool', 120)}
- **Transform types available**: product, ratio, diff, bool_and, bool_or, num_x_bool, log, square, sqrt
- **Numeric columns**: sponsor_prior_approvals, adcom_vote_pct, prior_crl_count, resubmission_class, ta_base_score, historical_crl_rate, s23_signal_strength, s6_signal_strength, social_sentiment_score, v1067_score, v1070_score, safety_signal_severity, ta_bucket_v2
- **Boolean columns**: btd, orphan, priority_review, fast_track, accelerated_approval, had_adcom, manufacturing_risk, prior_crl, form_483_issues, ema_cmc_flag, cmc_extension_flag, double_crl_flag, gene_therapy, psychedelics, surrogate_endpoint, single_arm_study, ppm_flag, ta_very_high_risk, s22_ped_pk_missing
{f"- **Top discovered features**: {json.dumps(discovery.get('top_discovered', []))}" if discovery.get('top_discovered') else "- No discovered features promoted yet"}

## HYPERPARAMETER SWEET SPOT (current champion)
{json.dumps(champion.get('params', {}), indent=2) if champion.get('params') else "  N/A"}

## YOUR TASK
Analyze the training state and provide optimization recommendations. Respond ONLY with valid JSON in this exact format:

```json
{{
  "analysis": "Brief (2-3 sentence) analysis of current training state",
  "strategy": "exploit" | "explore" | "balanced",
  "confidence": 0.0-1.0,
  "params": {{
    "mutation_rate": <float 0.10-0.65 or null to keep current>,
    "temperature": <float 0.5-2.5 or null to keep current>,
    "search_width": <float 0.5-3.5 or null to keep current>
  }},
  "feature_gate": ["list of feature names to FORCE include in next rounds, or empty"],
  "feature_block": ["list of feature names to EXCLUDE from next rounds, or empty"],
  "new_feature_ideas": [
    {{"name": "descriptive_name", "transform": "product|ratio|diff|num_x_bool|log|square|sqrt|bool_and|bool_or", "args": ["col1", "col2_or_omit_for_unary"], "rationale": "why this might help"}}
  ],
  "notes": "Any additional strategic notes for the training daemon"
}}
```

Be specific and actionable. Base feature ideas on domain knowledge of FDA approvals — e.g., interactions between regulatory designations and safety signals, sponsor track record × therapeutic area risk, etc."""

        return prompt

    def _parse_response(self, response_text: str) -> dict:
        """Parse Claude's response into actionable suggestions."""
        # Try to extract JSON from response
        text = response_text.strip()

        # Handle markdown code fences
        if "```json" in text:
            start = text.index("```json") + 7
            end = text.index("```", start)
            text = text[start:end].strip()
        elif "```" in text:
            start = text.index("```") + 3
            end = text.index("```", start)
            text = text[start:end].strip()

        try:
            result = json.loads(text)
        except json.JSONDecodeError:
            # Try to find JSON object in the text
            import re
            json_match = re.search(r'\{[\s\S]*\}', text)
            if json_match:
                try:
                    result = json.loads(json_match.group())
                except json.JSONDecodeError:
                    log.warning("  🤖 AI Advisor: Could not parse response as JSON")
                    return {"analysis": text[:500], "parse_error": True}
            else:
                log.warning("  🤖 AI Advisor: No JSON found in response")
                return {"analysis": text[:500], "parse_error": True}

        return result

    def apply_suggestions(self, suggestions: dict, kaizen_tracker, discovery_engine=None):
        """Apply AI suggestions to the training system.

        Returns dict of what was actually applied.
        """
        if not suggestions or suggestions.get("parse_error"):
            return {}

        applied = {}

        # 1. Log the analysis
        analysis = suggestions.get("analysis", "")
        strategy = suggestions.get("strategy", "balanced")
        confidence = suggestions.get("confidence", 0)
        log.info(f"  🤖 AI Analysis: {analysis}")
        log.info(f"  🤖 Strategy: {strategy} (confidence: {confidence})")

        # 2. Apply parameter adjustments via kaizen state override
        params = suggestions.get("params", {})
        if params and kaizen_tracker:
            state_path = kaizen_tracker.output_dir / "kaizen_state.json"
            try:
                with open(state_path) as f:
                    state = json.load(f)

                changed = False
                for key in ["mutation_rate", "temperature", "search_width"]:
                    val = params.get(key)
                    if val is not None:
                        ranges = {
                            "mutation_rate": (0.10, 0.65),
                            "temperature": (0.5, 2.5),
                            "search_width": (0.5, 3.5),
                        }
                        lo, hi = ranges[key]
                        clamped = max(lo, min(hi, float(val)))
                        state[key] = clamped
                        applied[key] = clamped
                        log.info(f"  🤖 Applied: {key} = {clamped:.3f}")
                        changed = True

                if changed:
                    state["last_ai_tune"] = datetime.now().isoformat()
                    state["last_ai_source"] = "ai_advisor"
                    with open(state_path, "w") as f:
                        json.dump(state, f, indent=2)

            except Exception as e:
                log.warning(f"  🤖 Failed to apply param overrides: {e}")

        # 3. Apply feature gate/block via config override file
        feature_gate = suggestions.get("feature_gate", [])
        feature_block = suggestions.get("feature_block", [])
        if feature_gate or feature_block:
            override_path = kaizen_tracker.output_dir / "ai_feature_override.json"
            override = {
                "feature_gate": feature_gate,
                "feature_block": feature_block,
                "applied_at": datetime.now().isoformat(),
                "source": "ai_advisor",
                "expires_rounds": 10,  # Override lasts 10 rounds
            }
            try:
                with open(override_path, "w") as f:
                    json.dump(override, f, indent=2)
                if feature_gate:
                    applied["feature_gate"] = feature_gate
                    log.info(f"  🤖 Feature GATE (force-include): {feature_gate}")
                if feature_block:
                    applied["feature_block"] = feature_block
                    log.info(f"  🤖 Feature BLOCK (exclude): {feature_block}")
            except Exception as e:
                log.warning(f"  🤖 Failed to write feature override: {e}")

        # 4. Inject new feature ideas into discovery engine
        new_ideas = suggestions.get("new_feature_ideas", [])
        if new_ideas and discovery_engine:
            injected = 0
            for idea in new_ideas[:6]:  # Max 6 new features per AI call
                name = idea.get("name", "")
                transform = idea.get("transform", "")
                args = idea.get("args", [])
                rationale = idea.get("rationale", "")

                if not name or not transform:
                    continue

                # Check if already in pool
                if name in discovery_engine.pool:
                    continue

                # Validate transform type
                from lgb_perpetual_daemon import _TRANSFORM_TYPES
                if transform not in _TRANSFORM_TYPES:
                    log.warning(f"  🤖 Unknown transform '{transform}' for {name} — skipping")
                    continue

                # Validate columns exist
                from lgb_perpetual_daemon import _NUMERIC_COLS, _BOOL_DISCOVERY_COLS
                all_cols = _NUMERIC_COLS + _BOOL_DISCOVERY_COLS
                valid = all(col in all_cols for col in args)
                if not valid:
                    log.warning(f"  🤖 Invalid columns for {name}: {args} — skipping")
                    continue

                # Build lambda and inject
                spec = _TRANSFORM_TYPES[transform]
                try:
                    if spec["arity"] == 1:
                        lam = spec["gen"](args[0])
                    else:
                        lam = spec["gen"](args[0], args[1])

                    discovery_engine.pool[name] = {
                        "transform": transform,
                        "args": args,
                        "lambda": lam,
                        "hits": 0,
                        "appearances": 0,
                        "round_added": -1,  # Mark as AI-injected
                        "source": "ai_advisor",
                        "rationale": rationale,
                    }
                    injected += 1
                    log.info(f"  🤖 Injected feature: {name} = {transform}({', '.join(args)}) — {rationale}")
                except Exception as e:
                    log.warning(f"  🤖 Failed to create lambda for {name}: {e}")

            if injected:
                applied["features_injected"] = injected
                discovery_engine.save()
                log.info(f"  🤖 Injected {injected} AI-suggested features into discovery pool")

        # 5. Notes
        notes = suggestions.get("notes", "")
        if notes:
            log.info(f"  🤖 Notes: {notes}")

        self.total_suggestions_applied += len(applied)
        self._save_state()

        return applied

    def get_training_state(self, ladder, kaizen_tracker, discovery_engine=None):
        """Gather current training state into a dict for the prompt."""
        champion = ladder.get("current_champion", {}) or {}
        state = {
            "champion": champion,
            "kaizen": {
                "total_rounds": kaizen_tracker.total_rounds if kaizen_tracker else 0,
                "total_promotions": kaizen_tracker.total_promotions if kaizen_tracker else 0,
                "streak": kaizen_tracker.current_streak if kaizen_tracker else 0,
                "longest_streak": kaizen_tracker.longest_streak if kaizen_tracker else 0,
                "mutation_rate": kaizen_tracker.mutation_rate if kaizen_tracker else 0.3,
                "temperature": kaizen_tracker.temperature if kaizen_tracker else 1.0,
                "search_width": kaizen_tracker.search_width if kaizen_tracker else 1.0,
            },
            "feature_importance": champion.get("feature_importance", {}),
            "feature_hits": kaizen_tracker.feature_hits if kaizen_tracker else {},
            "feature_appearances": kaizen_tracker.feature_appearances if kaizen_tracker else {},
            "recent_rounds": list(kaizen_tracker.auc_history)[-20:] if kaizen_tracker else [],
            "discovery": {},
        }

        if discovery_engine:
            top_disc = discovery_engine.get_feature_scores()[:10]
            state["discovery"] = {
                "pool_size": len(discovery_engine.pool),
                "max_pool": 120,
                "top_discovered": [
                    {"name": name, "win_rate": wr, "hits": h, "appearances": a}
                    for name, wr, h, a in top_disc if h > 0
                ],
            }

        return state


# ═══════════════════════════════════════════════════════════════
# FEATURE GATE/BLOCK READER (used by daemon's mutate_features)
# ═══════════════════════════════════════════════════════════════

def load_ai_feature_overrides(kaizen_dir: Path) -> dict:
    """Read AI feature gate/block overrides if fresh.

    Returns dict with 'feature_gate' and 'feature_block' lists,
    or empty dict if no fresh overrides exist.
    """
    override_path = kaizen_dir / "ai_feature_override.json"
    if not override_path.exists():
        return {}

    try:
        with open(override_path) as f:
            data = json.load(f)

        # Check if expired (based on rounds — caller tracks this)
        return {
            "feature_gate": data.get("feature_gate", []),
            "feature_block": data.get("feature_block", []),
            "expires_rounds": data.get("expires_rounds", 10),
            "applied_at": data.get("applied_at", ""),
        }
    except Exception:
        return {}


def clear_ai_feature_overrides(kaizen_dir: Path):
    """Remove expired feature overrides."""
    override_path = kaizen_dir / "ai_feature_override.json"
    if override_path.exists():
        try:
            override_path.unlink()
        except Exception:
            pass
