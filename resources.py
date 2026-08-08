from __future__ import annotations

"""Resource / capacity helpers for ODIN.

Primary goal (v38+): provide a **dynamic RAM budget** that can scale up/down
based on *current* system memory pressure, enabling optional caches that are:

  - fast when RAM is available
  - well-behaved when the system is under load

Design notes:
  - Uses `psutil` when available (it is commonly installed).
  - Falls back to `/proc/meminfo` if `psutil` isn't present.
  - Budget is computed in bytes.
  - Dynamic mode recomputes periodically and can shrink budget under pressure.
"""

from dataclasses import asdict, dataclass
from time import monotonic
from typing import Any, Dict, Literal, Optional, Tuple


RamMode = Literal["off", "fixed", "dynamic"]


def _gb_to_bytes(gb: float) -> int:
    return int(gb * (1024 ** 3))


def _bytes_to_gb(b: int) -> float:
    return float(b) / float(1024 ** 3)


def _read_meminfo_linux() -> Optional[Tuple[int, int]]:
    """Return (total_bytes, available_bytes) from /proc/meminfo when possible."""
    try:
        total_kb = None
        avail_kb = None
        with open("/proc/meminfo", "r") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    total_kb = int(line.split()[1])
                elif line.startswith("MemAvailable:"):
                    avail_kb = int(line.split()[1])
                if total_kb is not None and avail_kb is not None:
                    break
        if total_kb is None or avail_kb is None:
            return None
        return total_kb * 1024, avail_kb * 1024
    except Exception:
        return None


def get_memory_bytes() -> Dict[str, Any]:
    """Best-effort RAM stats.

    Returns:
      - total_bytes
      - available_bytes
      - used_percent (0..1) when known else None
      - source
    """
    try:
        import psutil  # type: ignore

        vm = psutil.virtual_memory()
        return {
            "total_bytes": int(vm.total),
            "available_bytes": int(vm.available),
            "used_percent": float(vm.percent) / 100.0,
            "source": "psutil",
        }
    except Exception:
        mi = _read_meminfo_linux()
        if mi is None:
            return {
                "total_bytes": None,
                "available_bytes": None,
                "used_percent": None,
                "source": "unknown",
            }
        total_b, avail_b = mi
        used_percent = 1.0 - (float(avail_b) / float(total_b)) if total_b else None
        return {
            "total_bytes": int(total_b),
            "available_bytes": int(avail_b),
            "used_percent": float(used_percent) if used_percent is not None else None,
            "source": "/proc/meminfo",
        }


def _interp_scale(x: float, lo: float, hi: float, y_lo: float, y_hi: float) -> float:
    if x <= lo:
        return y_lo
    if x >= hi:
        return y_hi
    # linear interpolation
    t = (x - lo) / (hi - lo)
    return y_lo + t * (y_hi - y_lo)


@dataclass
class RamBudgetPolicy:
    """Controls RAM budget selection for caches / chunking.

    Modes:
      - off: budget=0
      - fixed: budget=fixed_gb
      - dynamic: budget is a fraction of *currently available* RAM, reduced
        under high memory pressure (used_percent near 1.0)
    """

    mode: RamMode = "off"

    # fixed mode
    fixed_gb: float = 2.0

    # dynamic mode (uses available RAM after reserving reserve_gb)
    frac_available: float = 0.25  # 25% of available RAM (after reserve)
    reserve_gb: float = 2.0       # always try to leave this much free
    min_gb: float = 0.25          # never go below this (unless off)
    max_gb: float = 32.0          # never exceed this

    # memory pressure shaping (used_percent = 0..1)
    pressure_lo: float = 0.65
    pressure_hi: float = 0.85
    pressure_scale_hi: float = 0.50  # at/above pressure_hi, multiply budget by this

    # avoid recomputing on every call
    recompute_every_s: float = 1.0

    # internal cache
    _last_check_t: float = 0.0
    _last_budget_bytes: int = 0
    _last_mem_snapshot: Optional[Dict[str, Any]] = None

    def budget_bytes(self) -> int:
        if self.mode == "off":
            self._last_budget_bytes = 0
            self._last_mem_snapshot = get_memory_bytes()
            return 0

        now = monotonic()
        if (now - self._last_check_t) < float(self.recompute_every_s):
            return int(self._last_budget_bytes)

        self._last_check_t = now
        mem = get_memory_bytes()
        self._last_mem_snapshot = mem

        if self.mode == "fixed":
            b = _gb_to_bytes(float(self.fixed_gb))
            self._last_budget_bytes = b
            return int(b)

        # dynamic
        total_b = mem.get("total_bytes")
        avail_b = mem.get("available_bytes")
        used_pct = mem.get("used_percent")

        # If we can't read memory, fall back to fixed_gb.
        if avail_b is None:
            b = _gb_to_bytes(float(self.fixed_gb))
            self._last_budget_bytes = b
            return int(b)

        reserve_b = _gb_to_bytes(float(self.reserve_gb))
        avail_after_reserve = max(0, int(avail_b) - int(reserve_b))

        base = int(float(self.frac_available) * float(avail_after_reserve))

        # Additional down-scaling under high pressure.
        scale = 1.0
        if isinstance(used_pct, (int, float)):
            scale = _interp_scale(
                float(used_pct),
                float(self.pressure_lo),
                float(self.pressure_hi),
                1.0,
                float(self.pressure_scale_hi),
            )

        b = int(float(base) * float(scale))

        # Clamp
        b = max(b, _gb_to_bytes(float(self.min_gb)))
        b = min(b, _gb_to_bytes(float(self.max_gb)))

        # Never exceed available_after_reserve (avoid swapping ourselves)
        b = min(b, int(avail_after_reserve))

        self._last_budget_bytes = int(b)
        return int(b)

    def last_snapshot(self) -> Dict[str, Any]:
        """Return the most recent memory snapshot and computed budget."""
        mem = self._last_mem_snapshot or get_memory_bytes()
        b = int(self._last_budget_bytes)
        return {
            "policy": {k: v for k, v in asdict(self).items() if not k.startswith("_")},
            "mem": {
                "total_gb": _bytes_to_gb(mem["total_bytes"]) if mem.get("total_bytes") else None,
                "available_gb": _bytes_to_gb(mem["available_bytes"]) if mem.get("available_bytes") else None,
                "used_percent": mem.get("used_percent"),
                "source": mem.get("source"),
            },
            "budget_gb": _bytes_to_gb(b),
            "budget_bytes": b,
        }
