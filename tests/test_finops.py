import pytest
from finops.analyzer import CostAnalyzer, WorkloadHealthStatus
from finops.pricing import CloudProvider, get_pricing_rate


def test_cost_analysis():
    """Verify backward compatibility of test_cost_analysis."""
    a = CostAnalyzer()
    res = a.analyze_pod("web-app-1", cpu_request=4.0, cpu_actual=0.5, mem_request_mb=4096, mem_actual_mb=512)
    assert "Rightsize" in res["recommendation"]
    assert res["status"] == WorkloadHealthStatus.OVER_PROVISIONED.value
    assert res["monthly_savings_usd"] > 0


def test_optimal_workload():
    a = CostAnalyzer()
    res = a.analyze_pod("db-service", cpu_request=2.0, cpu_actual=1.6, mem_request_mb=2048, mem_actual_mb=1500)
    assert res["recommendation"] == "Optimal"
    assert res["status"] == WorkloadHealthStatus.OPTIMAL.value
    assert len(res["risk_alerts"]) == 0


def test_critical_oom_risk_detection():
    a = CostAnalyzer()
    res = a.analyze_pod("ingest-worker", cpu_request=2.0, cpu_actual=1.0, mem_request_mb=1000, mem_actual_mb=950)
    assert res["status"] == WorkloadHealthStatus.CRITICAL_OOM_RISK.value
    assert "OOMKilled" in res["risk_alerts"][0]
    assert "Increase memory" in res["recommendation"]


def test_cpu_throttling_detection():
    a = CostAnalyzer()
    res = a.analyze_pod("api-gateway", cpu_request=1.0, cpu_actual=0.98, mem_request_mb=2048, mem_actual_mb=800)
    assert res["status"] == WorkloadHealthStatus.UNDER_PROVISIONED.value
    assert "throttling" in res["risk_alerts"][0].lower()
    assert "Increase CPU" in res["recommendation"]


def test_idle_workload_detection():
    a = CostAnalyzer()
    res = a.analyze_pod("cron-idle", cpu_request=2.0, cpu_actual=0.04, mem_request_mb=2048, mem_actual_mb=100)
    assert res["status"] == WorkloadHealthStatus.IDLE.value
    assert "idle" in res["recommendation"].lower()
    assert any("idle" in alert.lower() for alert in res["risk_alerts"])


def test_multi_cloud_pricing():
    a = CostAnalyzer()
    res_aws = a.analyze_pod("app", cpu_request=4.0, cpu_actual=1.0, mem_request_mb=4096, mem_actual_mb=1024, provider=CloudProvider.AWS)
    res_gcp = a.analyze_pod("app", cpu_request=4.0, cpu_actual=1.0, mem_request_mb=4096, mem_actual_mb=1024, provider=CloudProvider.GCP)
    
    assert res_aws["current_monthly_cost_usd"] > 0
    assert res_gcp["current_monthly_cost_usd"] > 0
    # GCP compute pricing is slightly lower than AWS standard list
    assert res_aws["current_monthly_cost_usd"] != res_gcp["current_monthly_cost_usd"]


def test_fleet_analysis():
    a = CostAnalyzer()
    pods = [
        {"pod_name": "pod-1", "cpu_request": 4.0, "cpu_actual": 0.5, "mem_request_mb": 4096, "mem_actual_mb": 512},
        {"pod_name": "pod-2", "cpu_request": 2.0, "cpu_actual": 1.5, "mem_request_mb": 2048, "mem_actual_mb": 1500},
        {"pod_name": "pod-3", "cpu_request": 1.0, "cpu_actual": 0.99, "mem_request_mb": 1024, "mem_actual_mb": 980},
    ]
    summary = a.analyze_fleet(pods, provider=CloudProvider.AWS)
    assert summary["total_pods"] == 3
    assert summary["total_monthly_savings_usd"] > 0
    assert summary["overall_savings_percent"] > 0
    assert summary["status_summary"]["OVER_PROVISIONED"] == 1
    assert summary["status_summary"]["CRITICAL_OOM_RISK"] == 1
