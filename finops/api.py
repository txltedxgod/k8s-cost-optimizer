from typing import Any, Dict, List, Optional
from fastapi import FastAPI, Query
from pydantic import BaseModel, Field
from finops.analyzer import CostAnalyzer
from finops.pricing import DEFAULT_PRICING_TABLE, CloudProvider

app = FastAPI(
    title="K8s FinOps Cost Optimizer",
    version="0.2.0",
    description="Kubernetes Resource Rightsizing, Cloud Cost Optimization & Anomaly Detection Daemon",
)
analyzer = CostAnalyzer()


class PodMetricsReq(BaseModel):
    pod_name: str = Field(..., description="Kubernetes pod or workload name")
    cpu_request: float = Field(..., ge=0.0, description="Allocated CPU cores request")
    cpu_actual: float = Field(..., ge=0.0, description="Actual observed CPU utilization (e.g. P95 cores)")
    mem_request_mb: float = Field(..., ge=0.0, description="Allocated memory request in MB")
    mem_actual_mb: float = Field(..., ge=0.0, description="Actual observed memory utilization (e.g. P95 MB)")
    provider: Optional[str] = Field(default="aws", description="Cloud provider (aws, gcp, azure, on_premise)")


class FleetAnalysisReq(BaseModel):
    pods: List[PodMetricsReq]
    provider: Optional[str] = Field(default="aws", description="Default cloud provider for fleet")


@app.get("/healthz", tags=["Health"])
def health_check() -> Dict[str, str]:
    """Health check probe endpoint for Kubernetes liveness/readiness."""
    return {"status": "ok", "version": "0.2.0"}


@app.post("/api/v1/analyze", tags=["FinOps"])
def analyze(req: PodMetricsReq) -> Dict[str, Any]:
    """Analyze single pod resource utilization and return rightsizing recommendations."""
    return analyzer.analyze_pod(
        pod_name=req.pod_name,
        cpu_request=req.cpu_request,
        cpu_actual=req.cpu_actual,
        mem_request_mb=req.mem_request_mb,
        mem_actual_mb=req.mem_actual_mb,
        provider=req.provider or "aws",
    )


@app.post("/api/v1/analyze/batch", tags=["FinOps"])
@app.post("/api/v1/analyze/fleet", tags=["FinOps"])
def analyze_fleet_endpoint(req: FleetAnalysisReq) -> Dict[str, Any]:
    """Analyze multiple pods across a cluster or namespace and generate aggregate savings."""
    pods_dict = [p.model_dump() for p in req.pods]
    return analyzer.analyze_fleet(pods=pods_dict, provider=req.provider or "aws")


@app.get("/api/v1/pricing", tags=["Pricing"])
def get_pricing_tables() -> Dict[str, Any]:
    """Return cloud compute unit pricing tables used for estimation."""
    return {
        provider.value: {
            "cpu_core_hourly_usd": rate.cpu_core_hourly,
            "mem_gb_hourly_usd": rate.mem_gb_hourly,
            "cpu_core_monthly_usd": round(rate.cpu_monthly, 2),
            "mem_gb_monthly_usd": round(rate.mem_gb_monthly, 2),
            "spot_discount_ratio": rate.spot_discount_ratio,
        }
        for provider, rate in DEFAULT_PRICING_TABLE.items()
    }
