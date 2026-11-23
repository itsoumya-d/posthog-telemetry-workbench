"""Unit tests for A/B experiment SRM detection and guardrail metric evaluation."""

from posthog_wb.experiment_guardrails import (
    GuardrailMetric,
    check_sample_ratio_mismatch,
    evaluate_experiment_guardrails,
)


def test_balanced_traffic_passes_srm_check():
    # 5000 vs 5050 in a 50/50 split -> chi2 is very small, p-value high
    srm = check_sample_ratio_mismatch(5000, 5050, expected_ratio=0.5)
    assert not srm.srm_detected
    assert srm.p_value > 0.05
    assert srm.chi2_stat < 3.84


def test_skewed_traffic_detects_srm():
    # 6000 vs 4000 in a 50/50 split -> massive bias, p < 0.0001
    srm = check_sample_ratio_mismatch(6000, 4000, expected_ratio=0.5)
    assert srm.srm_detected
    assert srm.p_value < 0.001
    assert srm.chi2_stat > 10.0


def test_guardrail_metric_breach_detection():
    # Baseline error rate: 1.0%, Variant: 1.2% -> +20% relative increase
    metric = GuardrailMetric(
        name="checkout_api_error_rate",
        control_value=0.010,
        variant_value=0.012,
        max_allowed_degradation_pct=10.0,
        is_lower_better=True,
    )
    assert metric.relative_delta_pct == 20.0
    assert metric.is_breached


def test_experiment_decision_halts_on_srm():
    decision = evaluate_experiment_guardrails(
        experiment_key="growth_checkout_upsell_v2",
        observed_control=10000,
        observed_variant=8000,
        guardrails=[],
        expected_ratio=0.5,
    )
    assert decision.status == "HALT_SRM_BREACH"
    assert "Sample Ratio Mismatch" in decision.recommendation


def test_experiment_decision_warns_on_guardrail_breach():
    guardrails = [
        GuardrailMetric("latency_p95", 120.0, 145.0, max_allowed_degradation_pct=15.0),
    ]
    decision = evaluate_experiment_guardrails(
        experiment_key="growth_reorder_carousel",
        observed_control=5000,
        observed_variant=5010,
        guardrails=guardrails,
        expected_ratio=0.5,
    )
    assert decision.status == "WARNING_DEGRADED"
    assert "latency_p95" in decision.recommendation


def test_healthy_experiment_decision():
    guardrails = [
        GuardrailMetric("latency_p95", 120.0, 122.0, max_allowed_degradation_pct=10.0),
    ]
    decision = evaluate_experiment_guardrails(
        experiment_key="growth_free_delivery_banner",
        observed_control=5000,
        observed_variant=5020,
        guardrails=guardrails,
        expected_ratio=0.5,
    )
    assert decision.status == "HEALTHY"
