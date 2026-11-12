"""Evaluate semantic score acceptance thresholds."""


SEMANTIC_ACCEPTANCE_THRESHOLD = 0.80


def evaluate_semantic_threshold(
    aggregate_score: float,
    threshold: float = SEMANTIC_ACCEPTANCE_THRESHOLD,
) -> dict:
    """Determine whether the aggregate semantic score meets the threshold."""
    if not isinstance(aggregate_score, (int, float)) or isinstance(
        aggregate_score, bool
    ):
        raise ValueError("Aggregate score must be numeric.")

    if not 0.0 <= aggregate_score <= 1.0:
        raise ValueError("Aggregate score must be between 0 and 1.")

    if not isinstance(threshold, (int, float)) or isinstance(threshold, bool):
        raise ValueError("Threshold must be numeric.")

    if not 0.0 <= threshold <= 1.0:
        raise ValueError("Threshold must be between 0 and 1.")

    return {
        "acceptance_threshold": threshold,
        "aggregate_semantic_score": aggregate_score,
        "semantic_threshold_pass": aggregate_score >= threshold,
    }


def evaluate_quality_gates(
    aggregate_score: float,
    schema_pass_rate: float,
    invariant_pass_rate: float,
) -> dict:
    """Evaluate semantic, schema, and safety acceptance requirements."""
    semantic = evaluate_semantic_threshold(aggregate_score)

    for name, rate in (
        ("Schema pass rate", schema_pass_rate),
        ("Invariant pass rate", invariant_pass_rate),
    ):
        if not isinstance(rate, (int, float)) or isinstance(rate, bool):
            raise ValueError(f"{name} must be numeric.")
        if not 0.0 <= rate <= 1.0:
            raise ValueError(f"{name} must be between 0 and 1.")

    schema_pass = schema_pass_rate == 1.0
    invariant_pass = invariant_pass_rate == 1.0

    overall_pass = (
        semantic["semantic_threshold_pass"]
        and schema_pass
        and invariant_pass
    )

    return {
        **semantic,
        "schema_pass_rate": schema_pass_rate,
        "invariant_pass_rate": invariant_pass_rate,
        "schema_requirement_pass": schema_pass,
        "safety_requirement_pass": invariant_pass,
        "overall_status": "PASS" if overall_pass else "FAIL",
    }
