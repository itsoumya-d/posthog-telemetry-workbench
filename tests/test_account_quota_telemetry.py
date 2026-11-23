from __future__ import annotations

import pytest
from posthog_wb.account_quota_telemetry import (
    AccountQuotaEvaluator,
    AccountUsageRecord,
    QuotaTier,
)


@pytest.fixture
def enterprise_tier() -> QuotaTier:
    return QuotaTier(
        tier_name="enterprise-geospatial",
        monthly_tile_limit=1_000_000,
        monthly_api_queries_limit=100_000,
        max_polygon_area_sq_km=50_000.0,
    )


def test_healthy_account_usage(enterprise_tier: QuotaTier):
    usage = AccountUsageRecord(
        org_id="org_alpha_789",
        billing_cycle="2026-11",
        tiles_fetched=250_000,
        api_queries=30_000,
        largest_polygon_query_sq_km=12_000.0,
    )
    result = AccountQuotaEvaluator.evaluate_account_usage(enterprise_tier, usage)

    assert result.status == "healthy"
    assert result.is_over_quota is False
    assert result.tile_usage_pct == 25.0
    assert result.api_usage_pct == 30.0
    assert len(result.alerts) == 0


def test_warning_threshold_at_80_percent(enterprise_tier: QuotaTier):
    usage = AccountUsageRecord(
        org_id="org_beta_456",
        billing_cycle="2026-11",
        tiles_fetched=820_000,  # 82.0%
        api_queries=40_000,
        largest_polygon_query_sq_km=25_000.0,
    )
    result = AccountQuotaEvaluator.evaluate_account_usage(enterprise_tier, usage)

    assert result.status == "warning"
    assert result.is_over_quota is False
    assert any("warning threshold" in alert for alert in result.alerts)


def test_critical_threshold_at_90_percent(enterprise_tier: QuotaTier):
    usage = AccountUsageRecord(
        org_id="org_gamma_123",
        billing_cycle="2026-11",
        tiles_fetched=915_000,  # 91.5%
        api_queries=50_000,
        largest_polygon_query_sq_km=30_000.0,
    )
    result = AccountQuotaEvaluator.evaluate_account_usage(enterprise_tier, usage)

    assert result.status == "critical"
    assert result.is_over_quota is False
    assert any("nearing quota exhaustion" in alert for alert in result.alerts)


def test_throttled_when_quota_exceeded(enterprise_tier: QuotaTier):
    usage = AccountUsageRecord(
        org_id="org_delta_999",
        billing_cycle="2026-11",
        tiles_fetched=1_150_000,  # 115.0%
        api_queries=85_000,
        largest_polygon_query_sq_km=40_000.0,
    )
    result = AccountQuotaEvaluator.evaluate_account_usage(enterprise_tier, usage)

    assert result.status == "throttled"
    assert result.is_over_quota is True
    assert any("exceeded allocated quota" in alert for alert in result.alerts)


def test_polygon_area_exceeds_tier_limit(enterprise_tier: QuotaTier):
    usage = AccountUsageRecord(
        org_id="org_epsilon_555",
        billing_cycle="2026-11",
        tiles_fetched=100_000,
        api_queries=10_000,
        largest_polygon_query_sq_km=65_000.0,  # exceeds 50,000 max
    )
    result = AccountQuotaEvaluator.evaluate_account_usage(enterprise_tier, usage)

    assert any("Polygon area 65000.0 sq km exceeds max allowed" in alert for alert in result.alerts)


def test_invalid_tier_limits_reject():
    with pytest.raises(ValueError, match="strictly positive"):
        AccountQuotaEvaluator.evaluate_account_usage(
            QuotaTier("bad", 0, 100, 10.0),
            AccountUsageRecord("org", "2026-11", 10, 10, 1.0),
        )
