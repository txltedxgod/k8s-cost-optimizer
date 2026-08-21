# 💰 Kubernetes Cost Optimizer

```mermaid
flowchart TD
    K8sAPI[(Kubernetes Metrics API)] --> Daemon[FinOps Rightsizing Daemon]
    Prometheus[(Prometheus Time-Series)] --> Daemon
    
    Daemon --> Analyzer[P95 CPU & Memory Analyzer]
    Analyzer --> CostCalc[Cloud Cost Waste Estimator]
    CostCalc --> Recs[Rightsizing Recommendations]
    Recs --> Dashboard[Grafana FinOps Dashboard]
    Recs --> Slack[Slack / Webhook Alerts]
```


[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Kubernetes](https://img.shields.io/badge/kubernetes-v1.28+-326CE5.svg?logo=kubernetes&logoColor=white)](https://kubernetes.io/)
[![FinOps](https://img.shields.io/badge/FinOps-Ready-00C49F.svg)](https://www.finops.org/)


Kubernetes resource rightsizing & FinOps cost optimization daemon in Python & Docker.