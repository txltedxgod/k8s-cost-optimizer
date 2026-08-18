from typing import Dict, Any, List

class CostAnalyzer:
    def analyze_pod(self, pod_name: str, cpu_request: float, cpu_actual: float, mem_request_mb: float, mem_actual_mb: float) -> Dict[str, Any]:
        cpu_waste = max(0.0, cpu_request - cpu_actual)
        mem_waste = max(0.0, mem_request_mb - mem_actual_mb)
        waste_percent = (cpu_waste / cpu_request * 100) if cpu_request > 0 else 0

        recommendation = "Optimal"
        if waste_percent > 40:
            recommendation = f"Rightsize CPU to {round(cpu_actual * 1.2, 2)} cores (-{round(waste_percent)}% cost)"

        return {
            "pod": pod_name,
            "cpu_waste_cores": round(cpu_waste, 2),
            "mem_waste_mb": round(mem_waste, 1),
            "recommendation": recommendation
        }
