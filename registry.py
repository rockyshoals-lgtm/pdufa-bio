
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Literal, Optional, Sequence, Tuple, Union

import numpy as np
import pandas as pd


SignalKind = Literal["adjustment", "base_override", "transformer"]
DataStatus = Literal["backtestable", "prospective_only", "needs_enrichment"]


@dataclass(frozen=True)
class SignalMeta:
    """Metadata to keep signals auditable and safely backtestable."""
    name: str
    description: str
    kind: SignalKind
    data_status: DataStatus
    expects_columns: Tuple[str, ...] = ()
    # Optional defaults for quick marginal tests (NOT optimization).
    default_weight: float = 1.0  # multiplier applied to the raw signal output
    default_cap: Optional[Tuple[float, float]] = None  # cap on post-weighted adjustment (min,max)
    tags: Tuple[str, ...] = ()


@dataclass
class SignalOutput:
    """Standard signal output. Only one of adjustment/base_override is typically used."""
    adjustment: Optional[np.ndarray] = None          # Δp per row
    base_override: Optional[np.ndarray] = None       # p_base per row (0..1), replaces baseline prior
    transformer: Optional[Dict[str, np.ndarray]] = None  # reserved for future use
    notes: Dict[str, Union[str, float, int]] = field(default_factory=dict)


SignalFn = Callable[[pd.DataFrame], SignalOutput]


@dataclass(frozen=True)
class Signal:
    meta: SignalMeta
    fn: SignalFn


class SignalRegistry:
    def __init__(self) -> None:
        self._signals: Dict[str, Signal] = {}

    def register(self, signal: Signal) -> None:
        name = signal.meta.name
        if name in self._signals:
            raise ValueError(f"Signal already registered: {name}")
        self._signals[name] = signal

    def get(self, name: str) -> Signal:
        return self._signals[name]

    def list_names(self) -> List[str]:
        return sorted(self._signals.keys())

    def list_signals(self) -> List[Signal]:
        return [self._signals[n] for n in self.list_names()]

    def computable_signals(self, df: pd.DataFrame, *, allow_prospective: bool = False) -> List[Signal]:
        """
        Return signals that can be computed from the provided dataframe *and* are safe to backtest.

        Safety default:
        - Excludes `data_status == "prospective_only"` unless explicitly overridden.
        """
        cols = set(df.columns)
        out: List[Signal] = []
        for s in self.list_signals():
            if not allow_prospective and s.meta.data_status == "prospective_only":
                continue
            if all(c in cols for c in s.meta.expects_columns):
                out.append(s)
        return out
