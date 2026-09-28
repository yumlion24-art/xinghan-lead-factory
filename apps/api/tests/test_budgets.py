import pytest

from lead_factory.services.budgets import BudgetExceeded, BudgetKind, BudgetLedger, BudgetLimits


def test_budget_ledger_stops_before_exceeding_each_count_limit() -> None:
    ledger = BudgetLedger(BudgetLimits(pages=2, domains=1, ai_calls=1, elapsed_seconds=60))

    ledger.consume(BudgetKind.PAGE)
    ledger.consume(BudgetKind.PAGE)
    ledger.consume(BudgetKind.DOMAIN)
    ledger.consume(BudgetKind.AI_CALL)

    with pytest.raises(BudgetExceeded, match="pages"):
        ledger.consume(BudgetKind.PAGE)
    with pytest.raises(BudgetExceeded, match="domains"):
        ledger.consume(BudgetKind.DOMAIN)
    with pytest.raises(BudgetExceeded, match="ai_calls"):
        ledger.consume(BudgetKind.AI_CALL)
    assert ledger.snapshot() == {"pages": 2, "domains": 1, "ai_calls": 1}


def test_budget_ledger_stops_when_elapsed_time_is_exhausted() -> None:
    times = iter([100.0, 111.0])
    ledger = BudgetLedger(
        BudgetLimits(pages=2, domains=2, ai_calls=2, elapsed_seconds=10),
        clock=lambda: next(times),
    )

    with pytest.raises(BudgetExceeded, match="elapsed_seconds"):
        ledger.consume(BudgetKind.PAGE)

