from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

import pytest

from docgen.budget import BudgetExceeded, BudgetLedger, Pricing


def pricing():
    return Pricing(
        model="gemini-3.8-flash",
        input_usd_per_million=0.75,
        output_usd_per_million=3.75,
        usd_pln=4,
        verified_on=date.today(),
        valid_until=date.today(),
        exchange_date=date.today(),
        pricing_source="https://ai.google.dev/gemini-api/docs/pricing",
        exchange_source="https://api.nbp.pl",
    )


def test_budget_reservations_survive_restart_and_unknown_failure(tmp_path):
    path = tmp_path / "budget.sqlite"
    ledger = BudgetLedger(path, 10)
    first = ledger.reserve("a", "extract", 6, pricing())
    assert BudgetLedger(path, 10).summary()["remaining_pln"] == 4
    with pytest.raises(BudgetExceeded):
        ledger.reserve("b", "verify", 5, pricing())
    ledger.settle(first, None, {"failure": "timeout"})
    ledger.settle(first, 0, {})
    assert ledger.summary()["charged_pln"] == 6
    second = ledger.reserve("a", "verify", 4, pricing())
    ledger.settle(second, 2, {"tokens": 10})
    assert ledger.summary()["remaining_pln"] == 2


def test_concurrent_budget_cannot_overspend(tmp_path):
    ledger = BudgetLedger(tmp_path / "budget.sqlite", 10)

    def reserve(_):
        try:
            ledger.reserve("run", "extract", 6, pricing())
            return True
        except BudgetExceeded:
            return False

    with ThreadPoolExecutor(max_workers=4) as pool:
        assert sum(pool.map(reserve, range(4))) == 1


def test_stale_exchange_rejected():
    stale = pricing().model_copy(update={"exchange_date": date.today() - timedelta(days=8)})
    with pytest.raises(ValueError, match="exchange rate"):
        stale.validate_current()
