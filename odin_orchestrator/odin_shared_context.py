"""
ODIN Shared Context System
Inter-AI communication, memory, and collaborative reasoning

This module enables all 4 AIs to share findings, build on each other's
analysis, and maintain persistent context across tasks.
"""

import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
from pathlib import Path
import hashlib


class FindingType(Enum):
    """Types of findings that AIs can contribute"""
    PDUFA_ANALYSIS = "pdufa_analysis"
    OPTIONS_METRICS = "options_metrics"
    INSIDER_ACTIVITY = "insider_activity"
    FDA_NEWS = "fda_news"
    CATALYST_VALIDATION = "catalyst_validation"
    THESIS_UPDATE = "thesis_update"
    SIGNAL_SYNTHESIS = "signal_synthesis"
    MARKET_DATA = "market_data"
    RISK_ASSESSMENT = "risk_assessment"


class ConfidenceLevel(Enum):
    """Confidence calibration levels"""
    VERY_LOW = 0.2
    LOW = 0.4
    MODERATE = 0.6
    HIGH = 0.8
    VERY_HIGH = 0.95


@dataclass
class AIFinding:
    """A single finding from an AI analysis"""
    finding_id: str
    ticker: str
    ai_source: str  # openai, claude, gemini, perplexity
    finding_type: FindingType
    content: Dict[str, Any]
    confidence: float
    evidence: List[str]  # Sources/reasoning that support this finding
    contradicts: List[str] = field(default_factory=list)  # IDs of findings this contradicts
    supports: List[str] = field(default_factory=list)  # IDs of findings this supports
    timestamp: str = None
    expires_at: str = None  # When this finding becomes stale
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
        if self.expires_at is None:
            # Default: findings expire after 24 hours
            self.expires_at = (datetime.now() + timedelta(hours=24)).isoformat()
    
    def to_dict(self) -> Dict:
        d = asdict(self)
        d['finding_type'] = self.finding_type.value
        return d
    
    @classmethod
    def from_dict(cls, d: Dict) -> 'AIFinding':
        d['finding_type'] = FindingType(d['finding_type'])
        return cls(**d)
    
    def is_expired(self) -> bool:
        return datetime.now() > datetime.fromisoformat(self.expires_at)


@dataclass
class TickerContext:
    """Complete context for a single ticker"""
    ticker: str
    findings: Dict[str, AIFinding] = field(default_factory=dict)
    consensus: Optional[Dict[str, Any]] = None
    last_updated: str = None
    
    def __post_init__(self):
        if self.last_updated is None:
            self.last_updated = datetime.now().isoformat()
    
    def add_finding(self, finding: AIFinding):
        """Add or update a finding"""
        self.findings[finding.finding_id] = finding
        self.last_updated = datetime.now().isoformat()
    
    def get_findings_by_ai(self, ai_source: str) -> List[AIFinding]:
        """Get all findings from a specific AI"""
        return [f for f in self.findings.values() 
                if f.ai_source == ai_source and not f.is_expired()]
    
    def get_findings_by_type(self, finding_type: FindingType) -> List[AIFinding]:
        """Get all findings of a specific type"""
        return [f for f in self.findings.values() 
                if f.finding_type == finding_type and not f.is_expired()]
    
    def get_active_findings(self) -> List[AIFinding]:
        """Get all non-expired findings"""
        return [f for f in self.findings.values() if not f.is_expired()]
    
    def build_context_prompt(self, for_ai: str, task_type: str) -> str:
        """
        Build a context string for an AI to use as input.
        Includes relevant findings from OTHER AIs (not itself).
        """
        active = self.get_active_findings()
        other_ai_findings = [f for f in active if f.ai_source != for_ai]
        
        if not other_ai_findings:
            return f"No prior analysis available for {self.ticker}."
        
        context_parts = [
            f"=== PRIOR ANALYSIS FOR {self.ticker} ===",
            f"Total findings from other AIs: {len(other_ai_findings)}",
            ""
        ]
        
        # Group by AI source
        by_ai = {}
        for f in other_ai_findings:
            if f.ai_source not in by_ai:
                by_ai[f.ai_source] = []
            by_ai[f.ai_source].append(f)
        
        for ai, findings in by_ai.items():
            context_parts.append(f"--- From {ai.upper()} ---")
            for f in findings:
                context_parts.append(f"Type: {f.finding_type.value}")
                context_parts.append(f"Confidence: {f.confidence:.0%}")
                context_parts.append(f"Content: {json.dumps(f.content, indent=2)}")
                if f.evidence:
                    context_parts.append(f"Evidence: {'; '.join(f.evidence[:3])}")
                context_parts.append("")
        
        return "\n".join(context_parts)


class OdinSharedContext:
    """
    Central hub for inter-AI communication and shared memory.
    
    Features:
    - Store and retrieve findings from all 4 AIs
    - Build context prompts for each AI
    - Track consensus and contradictions
    - Persist to SQLite for durability
    - Support for prediction tracking and accuracy measurement
    """
    
    def __init__(self, db_file: str = "odin_shared_context.db"):
        self.db_file = db_file
        self.tickers: Dict[str, TickerContext] = {}
        self._init_database()
        self._load_from_database()
    
    def _init_database(self):
        """Initialize SQLite for persistent context storage"""
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        
        # Findings table
        c.execute('''
            CREATE TABLE IF NOT EXISTS findings (
                finding_id TEXT PRIMARY KEY,
                ticker TEXT,
                ai_source TEXT,
                finding_type TEXT,
                content TEXT,
                confidence REAL,
                evidence TEXT,
                contradicts TEXT,
                supports TEXT,
                timestamp TEXT,
                expires_at TEXT
            )
        ''')
        
        # Predictions table (for accuracy tracking)
        c.execute('''
            CREATE TABLE IF NOT EXISTS predictions (
                prediction_id TEXT PRIMARY KEY,
                ticker TEXT,
                predicted_outcome TEXT,
                predicted_probability REAL,
                predicted_by TEXT,
                prediction_date TEXT,
                event_date TEXT,
                actual_outcome TEXT,
                was_correct INTEGER,
                brier_score REAL
            )
        ''')
        
        # Consensus table
        c.execute('''
            CREATE TABLE IF NOT EXISTS consensus (
                ticker TEXT PRIMARY KEY,
                consensus_action TEXT,
                consensus_confidence REAL,
                contributing_ais TEXT,
                contradictions TEXT,
                created_at TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _load_from_database(self):
        """Load recent findings from database"""
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        
        # Load non-expired findings from last 7 days
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        c.execute('''
            SELECT * FROM findings WHERE timestamp > ? AND expires_at > ?
        ''', (week_ago, datetime.now().isoformat()))
        
        for row in c.fetchall():
            finding = AIFinding(
                finding_id=row[0],
                ticker=row[1],
                ai_source=row[2],
                finding_type=FindingType(row[3]),
                content=json.loads(row[4]),
                confidence=row[5],
                evidence=json.loads(row[6]),
                contradicts=json.loads(row[7]) if row[7] else [],
                supports=json.loads(row[8]) if row[8] else [],
                timestamp=row[9],
                expires_at=row[10]
            )
            
            if finding.ticker not in self.tickers:
                self.tickers[finding.ticker] = TickerContext(ticker=finding.ticker)
            self.tickers[finding.ticker].add_finding(finding)
        
        conn.close()
        print(f"✅ Loaded {sum(len(tc.findings) for tc in self.tickers.values())} findings for {len(self.tickers)} tickers")
    
    def add_finding(self, finding: AIFinding) -> str:
        """
        Add a new finding from an AI.
        Returns the finding_id.
        """
        # Generate finding ID if not provided
        if not finding.finding_id or finding.finding_id == "":
            finding.finding_id = self._generate_finding_id(finding)
        
        # Create ticker context if needed
        if finding.ticker not in self.tickers:
            self.tickers[finding.ticker] = TickerContext(ticker=finding.ticker)
        
        # Add to in-memory store
        self.tickers[finding.ticker].add_finding(finding)
        
        # Persist to database
        self._save_finding(finding)
        
        # Check for contradictions with existing findings
        self._detect_contradictions(finding)
        
        return finding.finding_id
    
    def _generate_finding_id(self, finding: AIFinding) -> str:
        """Generate unique finding ID"""
        content_hash = hashlib.md5(
            f"{finding.ticker}{finding.ai_source}{finding.finding_type.value}{finding.timestamp}".encode()
        ).hexdigest()[:12]
        return f"{finding.ai_source}_{finding.ticker}_{content_hash}"
    
    def _save_finding(self, finding: AIFinding):
        """Persist finding to database"""
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        
        c.execute('''
            INSERT OR REPLACE INTO findings 
            (finding_id, ticker, ai_source, finding_type, content, confidence, 
             evidence, contradicts, supports, timestamp, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            finding.finding_id,
            finding.ticker,
            finding.ai_source,
            finding.finding_type.value,
            json.dumps(finding.content),
            finding.confidence,
            json.dumps(finding.evidence),
            json.dumps(finding.contradicts),
            json.dumps(finding.supports),
            finding.timestamp,
            finding.expires_at
        ))
        
        conn.commit()
        conn.close()
    
    def _detect_contradictions(self, new_finding: AIFinding):
        """
        Check if new finding contradicts existing findings.
        Updates both findings' contradicts/supports lists.
        """
        if new_finding.ticker not in self.tickers:
            return
        
        existing = self.tickers[new_finding.ticker].get_active_findings()
        
        for existing_finding in existing:
            if existing_finding.finding_id == new_finding.finding_id:
                continue
            
            # Same type from different AI = potential contradiction
            if existing_finding.finding_type == new_finding.finding_type:
                # Check for numerical contradictions
                contradiction = self._check_contradiction(new_finding, existing_finding)
                if contradiction:
                    new_finding.contradicts.append(existing_finding.finding_id)
                    existing_finding.contradicts.append(new_finding.finding_id)
                    self._save_finding(existing_finding)
    
    def _check_contradiction(self, f1: AIFinding, f2: AIFinding) -> bool:
        """
        Check if two findings contradict each other.
        Returns True if significant disagreement detected.
        """
        # Check approval probability disagreement
        prob1 = f1.content.get('approval_probability')
        prob2 = f2.content.get('approval_probability')
        
        if prob1 is not None and prob2 is not None:
            # More than 30% disagreement = contradiction
            if abs(prob1 - prob2) > 0.30:
                return True
        
        # Check recommendation disagreement
        rec1 = f1.content.get('recommendation', '').upper()
        rec2 = f2.content.get('recommendation', '').upper()
        
        contradicting_pairs = [
            ('BUY', 'SELL'), ('BULLISH', 'BEARISH'), 
            ('APPROVE', 'CRL'), ('LONG', 'SHORT')
        ]
        
        for a, b in contradicting_pairs:
            if (a in rec1 and b in rec2) or (b in rec1 and a in rec2):
                return True
        
        return False
    
    def get_context_for_ai(self, ticker: str, ai_name: str, task_type: str = None) -> str:
        """
        Get context prompt for a specific AI working on a ticker.
        Includes findings from OTHER AIs, not its own previous findings.
        """
        if ticker not in self.tickers:
            return f"No prior analysis available for {ticker}. This is a fresh analysis."
        
        return self.tickers[ticker].build_context_prompt(ai_name, task_type)
    
    def get_all_findings(self, ticker: str) -> List[AIFinding]:
        """Get all active findings for a ticker"""
        if ticker not in self.tickers:
            return []
        return self.tickers[ticker].get_active_findings()
    
    def get_consensus(self, ticker: str) -> Optional[Dict]:
        """
        Calculate consensus from all AI findings.
        Returns aggregated view with confidence-weighted average.
        """
        if ticker not in self.tickers:
            return None
        
        findings = self.tickers[ticker].get_active_findings()
        if not findings:
            return None
        
        # Aggregate approval probabilities (weighted by confidence)
        approval_probs = []
        total_weight = 0
        
        for f in findings:
            if 'approval_probability' in f.content:
                weight = f.confidence
                approval_probs.append((f.content['approval_probability'], weight, f.ai_source))
                total_weight += weight
        
        if approval_probs:
            weighted_prob = sum(p * w for p, w, _ in approval_probs) / total_weight if total_weight > 0 else 0
        else:
            weighted_prob = None
        
        # Collect recommendations
        recommendations = {}
        for f in findings:
            rec = f.content.get('recommendation')
            if rec:
                if rec not in recommendations:
                    recommendations[rec] = []
                recommendations[rec].append(f.ai_source)
        
        # Find contradictions
        contradictions = []
        for f in findings:
            if f.contradicts:
                contradictions.append({
                    'finding': f.finding_id,
                    'contradicts': f.contradicts,
                    'ai': f.ai_source
                })
        
        consensus = {
            'ticker': ticker,
            'total_findings': len(findings),
            'contributing_ais': list(set(f.ai_source for f in findings)),
            'weighted_approval_probability': weighted_prob,
            'approval_breakdown': [(p, w, ai) for p, w, ai in approval_probs] if approval_probs else [],
            'recommendations': recommendations,
            'contradictions': contradictions,
            'consensus_confidence': total_weight / len(findings) if findings else 0,
            'generated_at': datetime.now().isoformat()
        }
        
        # Determine overall action
        if weighted_prob is not None:
            if weighted_prob >= 0.75:
                consensus['consensus_action'] = 'STRONG_BUY'
            elif weighted_prob >= 0.60:
                consensus['consensus_action'] = 'BUY'
            elif weighted_prob >= 0.40:
                consensus['consensus_action'] = 'HOLD'
            elif weighted_prob >= 0.25:
                consensus['consensus_action'] = 'REDUCE'
            else:
                consensus['consensus_action'] = 'AVOID'
        
        return consensus
    
    def record_prediction(self, ticker: str, predicted_outcome: str, 
                         probability: float, predicted_by: List[str],
                         event_date: str) -> str:
        """Record a prediction for later accuracy tracking"""
        prediction_id = f"pred_{ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        
        c.execute('''
            INSERT INTO predictions 
            (prediction_id, ticker, predicted_outcome, predicted_probability,
             predicted_by, prediction_date, event_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            prediction_id,
            ticker,
            predicted_outcome,
            probability,
            json.dumps(predicted_by),
            datetime.now().isoformat(),
            event_date
        ))
        
        conn.commit()
        conn.close()
        
        return prediction_id
    
    def record_outcome(self, prediction_id: str, actual_outcome: str):
        """Record actual outcome and calculate accuracy metrics"""
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        
        # Get prediction
        c.execute('SELECT predicted_outcome, predicted_probability FROM predictions WHERE prediction_id = ?',
                 (prediction_id,))
        row = c.fetchone()
        
        if row:
            predicted_outcome, probability = row
            was_correct = 1 if predicted_outcome.upper() == actual_outcome.upper() else 0
            
            # Calculate Brier score (for binary outcomes)
            if actual_outcome.upper() in ['APPROVED', 'APPROVE', 'YES', '1']:
                actual_prob = 1.0
            else:
                actual_prob = 0.0
            brier_score = (probability - actual_prob) ** 2
            
            c.execute('''
                UPDATE predictions 
                SET actual_outcome = ?, was_correct = ?, brier_score = ?
                WHERE prediction_id = ?
            ''', (actual_outcome, was_correct, brier_score, prediction_id))
            
            conn.commit()
        
        conn.close()
    
    def get_accuracy_stats(self, ai_source: str = None) -> Dict:
        """Get prediction accuracy statistics"""
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        
        if ai_source:
            c.execute('''
                SELECT COUNT(*), SUM(was_correct), AVG(brier_score)
                FROM predictions 
                WHERE actual_outcome IS NOT NULL AND predicted_by LIKE ?
            ''', (f'%{ai_source}%',))
        else:
            c.execute('''
                SELECT COUNT(*), SUM(was_correct), AVG(brier_score)
                FROM predictions 
                WHERE actual_outcome IS NOT NULL
            ''')
        
        row = c.fetchone()
        conn.close()
        
        total = row[0] or 0
        correct = row[1] or 0
        avg_brier = row[2] or 0
        
        return {
            'total_predictions': total,
            'correct_predictions': correct,
            'accuracy': correct / total if total > 0 else 0,
            'avg_brier_score': avg_brier,
            'ai_filter': ai_source
        }
    
    def clear_expired(self):
        """Remove expired findings from memory and database"""
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        
        c.execute('DELETE FROM findings WHERE expires_at < ?', 
                 (datetime.now().isoformat(),))
        deleted = c.rowcount
        
        conn.commit()
        conn.close()
        
        # Clear from memory
        for ticker_ctx in self.tickers.values():
            expired_ids = [f.finding_id for f in ticker_ctx.findings.values() if f.is_expired()]
            for fid in expired_ids:
                del ticker_ctx.findings[fid]
        
        return deleted
    
    def print_status(self, ticker: str = None):
        """Print current context status"""
        print("\n" + "="*70)
        print("ODIN SHARED CONTEXT STATUS")
        print("="*70)
        
        if ticker:
            tickers_to_show = [ticker] if ticker in self.tickers else []
        else:
            tickers_to_show = list(self.tickers.keys())[:5]  # Top 5
        
        for t in tickers_to_show:
            ctx = self.tickers[t]
            active = ctx.get_active_findings()
            print(f"\n📊 {t}")
            print(f"   Active Findings: {len(active)}")
            
            by_ai = {}
            for f in active:
                if f.ai_source not in by_ai:
                    by_ai[f.ai_source] = 0
                by_ai[f.ai_source] += 1
            
            for ai, count in by_ai.items():
                print(f"      {ai}: {count} findings")
            
            consensus = self.get_consensus(t)
            if consensus and consensus.get('weighted_approval_probability'):
                print(f"   Consensus: {consensus.get('consensus_action', 'N/A')} "
                      f"({consensus['weighted_approval_probability']:.0%} approval prob)")
        
        stats = self.get_accuracy_stats()
        print(f"\n📈 Overall Accuracy: {stats['accuracy']:.1%} "
              f"({stats['correct_predictions']}/{stats['total_predictions']} predictions)")
        print("="*70 + "\n")


# Singleton instance for easy import
_shared_context: Optional[OdinSharedContext] = None

def get_shared_context() -> OdinSharedContext:
    """Get the singleton shared context instance"""
    global _shared_context
    if _shared_context is None:
        _shared_context = OdinSharedContext()
    return _shared_context


if __name__ == "__main__":
    # Test the shared context
    ctx = OdinSharedContext()
    
    # Add test findings
    claude_finding = AIFinding(
        finding_id="",
        ticker="GUTS",
        ai_source="claude",
        finding_type=FindingType.PDUFA_ANALYSIS,
        content={
            "approval_probability": 0.72,
            "crl_probability": 0.28,
            "key_risks": ["CMC concerns", "Comparator selection"],
            "recommendation": "BUY_CALLS"
        },
        confidence=0.85,
        evidence=["Strong Phase 3 data", "Positive AdCom vote", "Unmet medical need"]
    )
    
    ctx.add_finding(claude_finding)
    print(f"Added finding: {claude_finding.finding_id}")
    
    # Add another finding from different AI
    chatgpt_finding = AIFinding(
        finding_id="",
        ticker="GUTS",
        ai_source="openai",
        finding_type=FindingType.OPTIONS_METRICS,
        content={
            "iv_current": 0.85,
            "iv_historical": 0.45,
            "expected_move": 0.35,
            "recommendation": "HIGH_IV_PLAY"
        },
        confidence=0.92,
        evidence=["IV 89% above historical", "Options flow bullish"]
    )
    
    ctx.add_finding(chatgpt_finding)
    
    # Get context for Perplexity to synthesize
    perplexity_context = ctx.get_context_for_ai("GUTS", "perplexity", "signal_synthesis")
    print("\n--- Context for Perplexity ---")
    print(perplexity_context)
    
    # Get consensus
    consensus = ctx.get_consensus("GUTS")
    print("\n--- Consensus ---")
    print(json.dumps(consensus, indent=2))
    
    ctx.print_status("GUTS")
