"""
A/B experiment guardrails and Sample Ratio Mismatch (SRM) diagnostics.
Evaluates traffic allocation integrity and monitors health guardrail metrics.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class SrmResult:
    observed_control: int
    observed_variant: int
    expected_ratio: float  # e.g. 0.5 for 50/50 split
    chi2_stat: float
    p_value: float
    srm_detected: bool  # True if p_value < 0.001


@dataclass
class GuardrailMetric:
    name: str
    control_value: float
    variant_value: float
    max_allowed_degradation_pct: float  # e.g. 5.0 for max 5% degradation
    is_lower_better: bool = True

    @property
    def relative_delta_pct(self) -> float:
        if self.control_value == 0:
            return 0.0
        return ((self.variant_value - self.control_value) / self.control_value) * 100.0

    @property
    def is_breached(self) -> bool:
        if self.is_lower_better:
            return self.relative_delta_pct > self.max_allowed_degradation_pct
        return self.relative_delta_pct < -self.max_allowed_degradation_pct


@dataclass
class ExperimentDecision:
    experiment_key: str
    srm: SrmResult
    guardrails: List[GuardrailMetric]
    status: str  # "HEALTHY", "WARNING_DEGRADED", "HALT_SRM_BREACH"
    recommendation: str


def check_sample_ratio_mismatch(
    observed_control: int,
    observed_variant: int,
    expected_ratio: float = 0.5,
    significance_alpha: float = 0.001,
) -> SrmResult:
    """Calculates Chi-Square statistic and p-value for 2-variant traffic allocation."""
    total = observed_control + observed_variant
    if total == 0:
        return SrmResult(0, 0, expected_ratio, 0.0, 1.0, False)

    expected_control = total * expected_ratio
    expected_variant = total * (1.0 - expected_ratio)

    chi2 = (
        ((observed_control - expected_control) ** 2) / expected_control
        + ((observed_variant - expected_variant) ** 2) / expected_variant
    )

    # 1 degree of freedom p-value via complementary error function
    p_value = math.erfc(math.sqrt(max(0.0, chi2) / 2.0))
    srm_detected = p_value < significance_alpha

    return SrmResult(
        observed_control=observed_control,
        observed_variant=observed_variant,
        expected_ratio=expected_ratio,
        chi2_stat=round(chi2, 4),
        p_value=round(p_value, 6),
        srm_detected=srm_detected,
    )


def evaluate_experiment_guardrails(
    experiment_key: str,
    observed_control: int,
    observed_variant: int,
    guardrails: List[GuardrailMetric],
    expected_ratio: float = 0.5,
) -> ExperimentDecision:
    """Combines SRM detection and guardrail evaluation into a rollout decision."""
    srm = check_sample_ratio_mismatch(observed_control, observed_variant, expected_ratio)
    breached = [g for g in guardrails if g.is_breached]

    if srm.srm_detected:
        status = "HALT_SRM_BREACH"
        rec = (
            f"Halt rollout immediately: Sample Ratio Mismatch detected (p={srm.p_value:.6f}, "
            f"chi2={srm.chi2_stat}). Traffic allocation is structurally biased."
        )
    elif breached:
        status = "WARNING_DEGRADED"
        names = ", ".join(f"{g.name} ({g.relative_delta_pct:+.1f}%)" for g in breached)
        rec = f"Pause staged rollout: guardrail metric(s) breached threshold: {names}."
    else:
        status = "HEALTHY"
        rec = "Experiment metrics healthy: no SRM detected and all guardrail metrics within tolerance."

    return ExperimentDecision(
        experiment_key=experiment_key,
        srm=srm,
        guardrails=guardrails,
        status=status,
        recommendation=rec,
    )
