"""
FinOps Kubernetes Rightsizing & Risk Analyzer.
Detects over-provisioning (waste), under-provisioning (OOM/throttling risk), and idle workloads.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from finops.pricing import CloudProvider, PricingRate, get_pricing_rate
from optimizer.metrics import CostCalculator


class WorkloadHealthStatus(str, Enum):
    OPTIMAL = "OPTIMAL"
    OVER_PROVISIONED = "OVER_PROVISIONED"
    UNDER_PROVISIONED = "UNDER_PROVISIONED"
    CRITICAL_OOM_RISK = "CRITICAL_OOM_RISK"
    IDLE = "IDLE"


class CostAnalyzer:
    """Enterprise FinOps rightsizing analyzer for Kubernetes pods and workloads."""

    def __init__(
        self,
        default_buffer_ratio: float = 0.20,
        idle_cpu_threshold_ratio: float = 0.05,
    ):
        """
        :param default_buffer_ratio: Headroom buffer (default 20%) added to actual P95 usage.
        :param idle_cpu_threshold_ratio: Ratio below which a workload is flagged as idle (e.g. <5%).
        """
        self.default_buffer_ratio = default_buffer_ratio
        self.idle_cpu_threshold_ratio = idle_cpu_threshold_ratio

    def analyze_pod(
        self,
        pod_name: str,
        cpu_request: float,
        cpu_actual: float,
        mem_request_mb: float,
        mem_actual_mb: float,
        provider: CloudProvider | str = CloudProvider.AWS,
        buffer_ratio: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Analyze an individual Kubernetes pod's utilization vs requests.
        Returns a detailed FinOps breakdown preserving backward compatibility.
        """
        buffer = self.default_buffer_ratio if buffer_ratio is None else buffer_ratio
        rate: PricingRate = get_pricing_rate(provider)
        calc = CostCalculator(provider=provider)

        # Baseline waste calculations
        cpu_waste = max(0.0, cpu_request - cpu_actual)
        mem_waste = max(0.0, mem_request_mb - mem_actual_mb)
        waste_percent = (cpu_waste / cpu_request * 100.0) if cpu_request > 0 else 0.0

        # Safety buffer sizing: actual usage + headroom buffer
        recommended_cpu = round(max(0.05, cpu_actual * (1.0 + buffer)), 2)
        recommended_mem_mb = round(max(64.0, mem_actual_mb * (1.0 + buffer)), 1)

        # Current vs Recommended costs
        current_monthly_cost = calc.compute_monthly_cost(cpu_request, mem_request_mb / 1024.0)
        recommended_monthly_cost = calc.compute_monthly_cost(recommended_cpu, recommended_mem_mb / 1024.0)
        monthly_waste_usd = round(calc.calculate_monthly_waste(cpu_request, cpu_actual, mem_request_mb / 1024.0, mem_actual_mb / 1024.0), 2)
        monthly_savings_usd = round(max(0.0, current_monthly_cost - recommended_monthly_cost), 2)
        spot_savings_usd = round(recommended_monthly_cost * (1.0 - rate.spot_discount_ratio), 2)

        # Risk assessment and health categorization
        risk_alerts: List[str] = []
        status = WorkloadHealthStatus.OPTIMAL

        # Check for under-provisioning & OOM risks first
        if mem_request_mb > 0 and mem_actual_mb >= mem_request_mb * 0.90:
            status = WorkloadHealthStatus.CRITICAL_OOM_RISK
            risk_alerts.append(f"High risk of OOMKilled: memory usage ({mem_actual_mb}MB) is at {round(mem_actual_mb / mem_request_mb * 100)}% of request.")
        elif cpu_request > 0 and cpu_actual >= cpu_request * 0.95:
            status = WorkloadHealthStatus.UNDER_PROVISIONED
            risk_alerts.append(f"CPU throttling detected: usage ({cpu_actual} cores) reached {round(cpu_actual / cpu_request * 100)}% of limit/request.")

        # Check for idle workloads
        if status == WorkloadHealthStatus.OPTIMAL and cpu_request > 0:
            if (cpu_actual / cpu_request) <= self.idle_cpu_threshold_ratio and (mem_actual_mb / mem_request_mb if mem_request_mb > 0 else 0) <= 0.10:
                status = WorkloadHealthStatus.IDLE
                risk_alerts.append("Workload is idle (<5% CPU, <10% Mem). Consider scaling replicas to 0 or consolidating.")

        # Prioritized recommendation message formation
        if status == WorkloadHealthStatus.CRITICAL_OOM_RISK:
            recommendation = f"Increase memory to {recommended_mem_mb}MB to prevent container eviction"
        elif status == WorkloadHealthStatus.UNDER_PROVISIONED:
            recommendation = f"Increase CPU to {recommended_cpu} cores to alleviate throttling"
        elif status == WorkloadHealthStatus.IDLE:
            recommendation = "Idle workload detected: scale down or deprecate"
        elif waste_percent > 40:
            status = WorkloadHealthStatus.OVER_PROVISIONED
            recommendation = f"Rightsize CPU to {recommended_cpu} cores (-{round(waste_percent)}% cost)"
        else:
            recommendation = "Optimal"

        return {
            "pod": pod_name,
            "status": status.value,
            "cpu_waste_cores": round(cpu_waste, 2),
            "mem_waste_mb": round(mem_waste, 1),
            "waste_percent": round(waste_percent, 1),
            "recommended_cpu_cores": recommended_cpu,
            "recommended_mem_mb": recommended_mem_mb,
            "current_monthly_cost_usd": round(current_monthly_cost, 2),
            "projected_monthly_cost_usd": round(recommended_monthly_cost, 2),
            "monthly_waste_usd": monthly_waste_usd,
            "monthly_savings_usd": monthly_savings_usd,
            "spot_monthly_savings_usd": spot_savings_usd,
            "recommendation": recommendation,
            "risk_alerts": risk_alerts,
        }

    def analyze_fleet(
        self,
        pods: List[Dict[str, Any]],
        provider: CloudProvider | str = CloudProvider.AWS,
    ) -> Dict[str, Any]:
        """
        Aggregate fleet-level FinOps analysis for multiple pods or a full cluster.
        """
        results: List[Dict[str, Any]] = []
        total_current_cost = 0.0
        total_projected_cost = 0.0
        total_savings = 0.0
        status_counts: Dict[str, int] = {s.value: 0 for s in WorkloadHealthStatus}

        for p in pods:
            res = self.analyze_pod(
                pod_name=p["pod_name"],
                cpu_request=float(p.get("cpu_request", 0.0)),
                cpu_actual=float(p.get("cpu_actual", 0.0)),
                mem_request_mb=float(p.get("mem_request_mb", 0.0)),
                mem_actual_mb=float(p.get("mem_actual_mb", 0.0)),
                provider=provider,
            )
            results.append(res)
            total_current_cost += res["current_monthly_cost_usd"]
            total_projected_cost += res["projected_monthly_cost_usd"]
            total_savings += res["monthly_savings_usd"]
            status_counts[res["status"]] = status_counts.get(res["status"], 0) + 1

        overall_savings_pct = (
            round((total_savings / total_current_cost) * 100.0, 1)
            if total_current_cost > 0
            else 0.0
        )

        return {
            "total_pods": len(pods),
            "status_summary": status_counts,
            "total_current_monthly_cost_usd": round(total_current_cost, 2),
            "total_projected_monthly_cost_usd": round(total_projected_cost, 2),
            "total_monthly_savings_usd": round(total_savings, 2),
            "overall_savings_percent": overall_savings_pct,
            "cloud_provider": str(provider).lower(),
            "pod_details": results,
        }
