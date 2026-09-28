from __future__ import annotations

import enum
import time
from collections.abc import Callable
from dataclasses import dataclass


class BudgetKind(str, enum.Enum):
    PAGE = "pages"
    DOMAIN = "domains"
    AI_CALL = "ai_calls"


class BudgetExceeded(RuntimeError):
    pass


@dataclass(frozen=True)
class BudgetLimits:
    pages: int
    domains: int
    ai_calls: int
    elapsed_seconds: float


class BudgetLedger:
    def __init__(self, limits: BudgetLimits, clock: Callable[[], float] = time.monotonic) -> None:
        self.limits = limits
        self.clock = clock
        self.started_at = clock()
        self._counts = {kind.value: 0 for kind in BudgetKind}

    def consume(self, kind: BudgetKind, amount: int = 1) -> None:
        if self.clock() - self.started_at > self.limits.elapsed_seconds:
            raise BudgetExceeded("elapsed_seconds budget exhausted")
        limit = getattr(self.limits, kind.value)
        if self._counts[kind.value] + amount > limit:
            raise BudgetExceeded(f"{kind.value} budget exhausted")
        self._counts[kind.value] += amount

    def snapshot(self) -> dict[str, int]:
        return dict(self._counts)

