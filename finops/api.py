from fastapi import FastAPI
from pydantic import BaseModel
from finops.analyzer import CostAnalyzer

app = FastAPI(title="K8s Cost Optimizer", version="0.1.0")
analyzer = CostAnalyzer()

class PodMetricsReq(BaseModel):
    pod_name: str
    cpu_request: float
    cpu_actual: float
    mem_request_mb: float
    mem_actual_mb: float

@app.post("/api/v1/analyze")
def analyze(req: PodMetricsReq):
    return analyzer.analyze_pod(req.pod_name, req.cpu_request, req.cpu_actual, req.mem_request_mb, req.mem_actual_mb)
