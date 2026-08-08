from __future__ import annotations

"""Byte-bounded LRU cache for computed signal outputs.

This cache is intentionally simple and auditable:
  - Keys are typically signal names (strings).
  - Values are `SignalOutput` objects.
  - Eviction is LRU by insertion/access.
  - Capacity is defined in *bytes* and can be dynamic (see RamBudgetPolicy).

Rationale:
Signal discovery workflows often re-compute the same signal outputs many times
(e.g., leave-one-out ablations). Caching can dramatically speed runs.

We keep the cache optional and bound its footprint to avoid destabilizing
co-located workloads.
"""

from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Dict, Generic, Optional, Tuple, TypeVar

import numpy as np

from .registry import SignalOutput
from .resources import RamBudgetPolicy


K = TypeVar("K")


def estimate_signaloutput_bytes(out: SignalOutput) -> int:
    """Estimate memory use of a SignalOutput.

    We count numpy array payload sizes (nbytes) and ignore python object
    overhead. This provides a conservative-enough bound for cache eviction.
    """
    total = 0
    if out.adjustment is not None:
        total += int(np.asarray(out.adjustment).nbytes)
    if out.base_override is not None:
        total += int(np.asarray(out.base_override).nbytes)
    if out.transformer:
        for _, arr in out.transformer.items():
            total += int(np.asarray(arr).nbytes)
    return int(total)


@dataclass
class CacheStats:
    hits: int = 0
    misses: int = 0
    sets: int = 0
    evictions: int = 0
    bytes_current: int = 0
    bytes_peak: int = 0


class ByteLRUCache(Generic[K]):
    def __init__(self, policy: RamBudgetPolicy) -> None:
        self._policy = policy
        self._data: "OrderedDict[K, Tuple[Any, int]]" = OrderedDict()
        self._bytes: int = 0
        self.stats = CacheStats()

    def budget_bytes(self) -> int:
        return int(self._policy.budget_bytes())

    def get(self, key: K) -> Optional[Any]:
        item = self._data.get(key)
        if item is None:
            self.stats.misses += 1
            return None
        # LRU: mark as recently used
        self._data.move_to_end(key)
        self.stats.hits += 1
        return item[0]

    def set(self, key: K, value: Any, size_bytes: int) -> None:
        self.stats.sets += 1

        # Replace existing entry (adjust bytes)
        if key in self._data:
            _, old_sz = self._data.pop(key)
            self._bytes -= int(old_sz)

        self._data[key] = (value, int(size_bytes))
        self._bytes += int(size_bytes)
        self.stats.bytes_current = int(self._bytes)
        self.stats.bytes_peak = int(max(self.stats.bytes_peak, self._bytes))

        self._evict_if_needed()

    def _evict_if_needed(self) -> None:
        # Budget can change over time in dynamic mode.
        budget = int(self.budget_bytes())
        if budget <= 0:
            # If budget is off, clear aggressively.
            if self._data:
                self.stats.evictions += len(self._data)
            self._data.clear()
            self._bytes = 0
            self.stats.bytes_current = 0
            return

        while self._bytes > budget and self._data:
            _, (_, sz) = self._data.popitem(last=False)  # pop oldest
            self._bytes -= int(sz)
            self.stats.evictions += 1
        self.stats.bytes_current = int(self._bytes)

    def snapshot(self) -> Dict[str, Any]:
        return {
            "budget_bytes": int(self.budget_bytes()),
            "budget_gb": float(self.budget_bytes()) / float(1024 ** 3),
            "entries": int(len(self._data)),
            "stats": {
                "hits": int(self.stats.hits),
                "misses": int(self.stats.misses),
                "sets": int(self.stats.sets),
                "evictions": int(self.stats.evictions),
                "bytes_current": int(self.stats.bytes_current),
                "bytes_peak": int(self.stats.bytes_peak),
            },
            "policy": self._policy.last_snapshot(),
        }
