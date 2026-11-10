import pytest
from fastapi.testclient import TestClient
from finops.api import app

client = TestClient(app)


def test_healthz():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_api_analyze():
    payload = {
        "pod_name": "checkout-svc-xyz",
        "cpu_request": 4.0,
        "cpu_actual": 0.5,
        "mem_request_mb": 4096.0,
        "mem_actual_mb": 512.0,
        "provider": "aws",
    }
    response = client.post("/api/v1/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["pod"] == "checkout-svc-xyz"
    assert data["status"] == "OVER_PROVISIONED"
    assert data["monthly_savings_usd"] > 0
    assert "Rightsize" in data["recommendation"]


def test_api_analyze_fleet():
    payload = {
        "pods": [
            {
                "pod_name": "worker-1",
                "cpu_request": 2.0,
                "cpu_actual": 0.2,
                "mem_request_mb": 2048.0,
                "mem_actual_mb": 200.0,
            },
            {
                "pod_name": "worker-2",
                "cpu_request": 1.0,
                "cpu_actual": 0.95,
                "mem_request_mb": 1024.0,
                "mem_actual_mb": 950.0,
            },
        ],
        "provider": "gcp",
    }
    response = client.post("/api/v1/analyze/fleet", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["total_pods"] == 2
    assert "status_summary" in data
    assert data["total_current_monthly_cost_usd"] > 0


def test_api_pricing():
    response = client.get("/api/v1/pricing")
    assert response.status_code == 200
    data = response.json()
    assert "aws" in data
    assert "gcp" in data
    assert "azure" in data
    assert data["aws"]["cpu_core_hourly_usd"] > 0
