"""
FinOps Resource Utilization & Cost Estimation Metrics.
Calculates statistical percentiles (P50, P90, P95, P99) and financial metrics.
"""

from dataclasses import dataclass
import math
from typing import Sequence
from finops.pricing import CloudProvider, PricingRate, get_pricing_rate


def calculate_percentile(values: Sequence[float], percentile: float) -> float:
    """
    Calculate the given percentile (0 to 100) using linear interpolation.
    Returns 0.0 if the sequence is empty.
    """
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    if n == 1:
        return float(sorted_vals[0])
    
    k = (percentile / 100.0) * (n - 1)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return float(sorted_vals[int(k)])
    d0 = sorted_vals[int(f)] * (c - k)
    d1 = sorted_vals[int(c)] * (k - f)
    return float(round(d0 + d1, 4))


@dataclass(frozen=True)
class MetricStats:
    """Aggregated statistical view of resource utilization over time."""
    min_val: float
    max_val: float
    avg_val: float
    p50: float
    p90: float
    p95: float
    p99: float

    @classmethod
    def from_series(cls, series: Sequence[float]) -> "MetricStats":
        if not series:
            return cls(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        return cls(
            min_val=round(min(series), 4),
            max_val=round(max(series), 4),
            avg_val=round(sum(series) / len(series), 4),
            p50=calculate_percentile(series, 50),
            p90=calculate_percentile(series, 90),
            p95=calculate_percentile(series, 95),
            p99=calculate_percentile(series, 99),
        )


class CostCalculator:
    """Calculates compute and memory financial costs, waste, and projected savings."""

    def __init__(
        self,
        cpu_hourly_rate: float = 0.04,
        mem_gb_hourly_rate: float = 0.005,
        provider: CloudProvider | str | None = None,
    ):
        if provider:
            rate = get_pricing_rate(provider)
            self.cpu_rate = rate.cpu_core_hourly
            self.mem_rate = rate.mem_gb_hourly
        else:
            self.cpu_rate = cpu_hourly_rate
            self.mem_rate = mem_gb_hourly_rate

    def calculate_monthly_waste(
        self,
        cpu_request: float,
        cpu_actual_p95: float,
        mem_gb_request: float,
        mem_gb_actual_p95: float,
    ) -> float:
        wasted_cpu = max(0.0, cpu_request - cpu_actual_p95)
        wasted_mem = max(0.0, mem_gb_request - mem_gb_actual_p95)
        monthly_hours = 730
        return (wasted_cpu * self.cpu_rate + wasted_mem * self.mem_rate) * monthly_hours

    def compute_monthly_cost(self, cpu_cores: float, mem_gb: float) -> float:
        """Total monthly cost of specified resource footprint."""
        return (cpu_cores * self.cpu_rate + mem_gb * self.mem_rate) * 730.0
