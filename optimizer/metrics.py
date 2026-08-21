"""
FinOps Resource Utilization & Cost Estimation Metrics
"""

class CostCalculator:
    def __init__(self, cpu_hourly_rate: float = 0.04, mem_gb_hourly_rate: float = 0.005):
        self.cpu_rate = cpu_hourly_rate
        self.mem_rate = mem_gb_hourly_rate

    def calculate_monthly_waste(self, cpu_request: float, cpu_actual_p95: float, mem_gb_request: float, mem_gb_actual_p95: float) -> float:
        wasted_cpu = max(0.0, cpu_request - cpu_actual_p95)
        wasted_mem = max(0.0, mem_gb_request - mem_gb_actual_p95)
        monthly_hours = 730
        return (wasted_cpu * self.cpu_rate + wasted_mem * self.mem_rate) * monthly_hours
