"""
Multi-cloud pricing models and cost calculation for Kubernetes resources.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict


class CloudProvider(str, Enum):
    AWS = "aws"
    GCP = "gcp"
    AZURE = "azure"
    ON_PREMISE = "on_premise"


@dataclass(frozen=True)
class PricingRate:
    """Hourly and monthly pricing rates per compute unit."""
    cpu_core_hourly: float
    mem_gb_hourly: float
    spot_discount_ratio: float = 0.30  # Spot instance costs ~30% of On-Demand (70% savings)

    @property
    def cpu_monthly(self) -> float:
        return self.cpu_core_hourly * 730.0

    @property
    def mem_gb_monthly(self) -> float:
        return self.mem_gb_hourly * 730.0


# Standard On-Demand list rates (based on general-purpose compute tiers e.g. m6i / e2-standard / D-series)
DEFAULT_PRICING_TABLE: Dict[CloudProvider, PricingRate] = {
    CloudProvider.AWS: PricingRate(
        cpu_core_hourly=0.04048,
        mem_gb_hourly=0.004445,
        spot_discount_ratio=0.30,
    ),
    CloudProvider.GCP: PricingRate(
        cpu_core_hourly=0.031611,
        mem_gb_hourly=0.004237,
        spot_discount_ratio=0.35,
    ),
    CloudProvider.AZURE: PricingRate(
        cpu_core_hourly=0.03800,
        mem_gb_hourly=0.00410,
        spot_discount_ratio=0.32,
    ),
    CloudProvider.ON_PREMISE: PricingRate(
        cpu_core_hourly=0.02000,
        mem_gb_hourly=0.00250,
        spot_discount_ratio=1.00,
    ),
}


def get_pricing_rate(provider: CloudProvider | str) -> PricingRate:
    """Retrieve pricing rate for a given cloud provider."""
    if isinstance(provider, str):
        try:
            provider = CloudProvider(provider.lower())
        except ValueError:
            provider = CloudProvider.AWS
    return DEFAULT_PRICING_TABLE.get(provider, DEFAULT_PRICING_TABLE[CloudProvider.AWS])
