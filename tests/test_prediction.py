from datetime import date
from decimal import Decimal

from core.prediction import project_periods
from core.periods import financial_period_for


def test_new_actual_snapshot_becomes_next_projection_opening_balance():
    period = financial_period_for(date(2026, 8, 13))
    output = project_periods(
        {"main": Decimal("90000")}, period, 2, 13, [], [], [],
        {date(2026, 9, 13): {"main": Decimal("94000")}},
    )
    assert output[0][1]["main"].worst_case == Decimal("90000")
    assert output[1][1]["main"].worst_case == Decimal("94000")

