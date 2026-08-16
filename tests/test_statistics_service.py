from datetime import date

from services.statistics import StatisticsService


def test_statistical_forecast_requires_six_actual_periods():
    data = StatisticsService().build(accounts=[], snapshots=[], payday=13, today=date(2026, 8, 16))
    assert data.forecast == ()
    assert data.trend_delta is None
