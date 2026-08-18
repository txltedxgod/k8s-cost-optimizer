from finops.analyzer import CostAnalyzer

def test_cost_analysis():
    a = CostAnalyzer()
    res = a.analyze_pod("web-app-1", cpu_request=4.0, cpu_actual=0.5, mem_request_mb=4096, mem_actual_mb=512)
    assert "Rightsize" in res["recommendation"]
