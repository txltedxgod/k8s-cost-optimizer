import pytest
from optimizer.metrics import CostCalculator, MetricStats, calculate_percentile
from finops.pricing import CloudProvider


def test_calculate_percentile_empty():
    assert calculate_percentile([], 95) == 0.0


def test_calculate_percentile_single():
    assert calculate_percentile([4.2], 90) == 4.2


def test_calculate_percentile_multi():
    data = [10.0, 20.0, 30.0, 40.0, 50.0]
    assert calculate_percentile(data, 50) == 30.0
    assert calculate_percentile(data, 0) == 10.0
    assert calculate_percentile(data, 100) == 50.0
    assert calculate_percentile(data, 90) == 46.0


def test_metric_stats():
    series = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    stats = MetricStats.from_series(series)
    assert stats.min_val == 1.0
    assert stats.max_val == 10.0
    assert stats.avg_val == 5.5
    assert stats.p50 == 5.5
    assert stats.p95 == 9.55


def test_metric_stats_empty():
    stats = MetricStats.from_series([])
    assert stats.min_val == 0.0
    assert stats.max_val == 0.0
    assert stats.p99 == 0.0


def test_cost_calculator():
    calc = CostCalculator(cpu_hourly_rate=0.04, mem_gb_hourly_rate=0.005)
    # 4 CPU requested, 1 actual -> 3 wasted. 4GB requested, 1GB actual -> 3GB wasted
    # monthly = (3 * 0.04 + 3 * 0.005) * 730 = (0.12 + 0.015) * 730 = 0.135 * 730 = 98.55
    waste = calc.calculate_monthly_waste(4.0, 1.0, 4.0, 1.0)
    assert round(waste, 2) == 98.55


def test_cost_calculator_with_provider():
    calc = CostCalculator(provider=CloudProvider.AWS)
    cost = calc.compute_monthly_cost(2.0, 4.0)
    assert cost > 0
