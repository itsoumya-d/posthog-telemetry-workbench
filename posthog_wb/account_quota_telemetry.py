from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Literal


@dataclass(frozen=True)
class QuotaTier:
    tier_name: str
    monthly_tile_limit: int
    monthly_api_queries_limit: int
    max_polygon_area_sq_km: float


@dataclass(frozen=True)
class AccountUsageRecord:
    org_id: str
    billing_cycle: str
    tiles_fetched: int
    api_queries: int
    largest_polygon_query_sq_km: float


@dataclass(frozen=True)
class QuotaEvaluation:
    org_id: str
    tier_name: str
    tile_usage_pct: float
    api_usage_pct: float
    is_over_quota: bool
    status: Literal["healthy", "warning", "critical", "throttled"]
    alerts: tuple[str, ...]


class AccountQuotaEvaluator:
    """
    Evaluates customer account telemetry and geospatial query quotas.
    Generates threshold alerts (80%, 90%, 100%) and throttles accounts exceeding tier limits.
    """

    @staticmethod
    def evaluate_account_usage(
        tier: QuotaTier,
        usage: AccountUsageRecord,
    ) -> QuotaEvaluation:
        if tier.monthly_tile_limit <= 0 or tier.monthly_api_queries_limit <= 0:
            raise ValueError("Quota tier limits must be strictly positive")

        tile_pct = round((usage.tiles_fetched / tier.monthly_tile_limit) * 100.0, 2)
        api_pct = round((usage.api_queries / tier.monthly_api_queries_limit) * 100.0, 2)

        alerts: List[str] = []
        is_over_quota = False

        if usage.largest_polygon_query_sq_km > tier.max_polygon_area_sq_km:
            alerts.append(
                f"Polygon area {usage.largest_polygon_query_sq_km} sq km exceeds max allowed {tier.max_polygon_area_sq_km} sq km"
            )

        max_pct = max(tile_pct, api_pct)

        if max_pct > 100.0:
            status = "throttled"
            is_over_quota = True
            alerts.append(f"Account exceeded allocated quota limits (peak usage: {max_pct}%)")
        elif max_pct >= 90.0:
            status = "critical"
            alerts.append(f"Account nearing quota exhaustion: {max_pct}% consumed")
        elif max_pct >= 80.0:
            status = "warning"
            alerts.append(f"Account usage reached warning threshold: {max_pct}% consumed")
        else:
            status = "healthy"

        return QuotaEvaluation(
            org_id=usage.org_id,
            tier_name=tier.tier_name,
            tile_usage_pct=tile_pct,
            api_usage_pct=api_pct,
            is_over_quota=is_over_quota,
            status=status,
            alerts=tuple(alerts),
        )
