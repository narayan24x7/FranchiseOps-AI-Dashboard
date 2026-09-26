"""Benchmarking, scoring, alerts, and deterministic agent recommendations."""

from __future__ import annotations

from collections import OrderedDict

import numpy as np
import pandas as pd


SCORE_WEIGHTS = OrderedDict(
    [
        ("Revenue target achievement", 0.35),
        ("Month-over-month growth", 0.15),
        ("Customer rating", 0.20),
        ("Complaint control", 0.15),
        ("On-time service", 0.15),
    ]
)

COMPONENT_COLUMNS = OrderedDict(
    [
        ("Revenue target achievement", "revenue_component_score"),
        ("Month-over-month growth", "growth_component_score"),
        ("Customer rating", "rating_component_score"),
        ("Complaint control", "complaint_component_score"),
        ("On-time service", "service_component_score"),
    ]
)

HEALTH_ORDER = ["Excellent", "Good", "Needs Improvement", "Critical"]
HEALTH_COLORS = {
    "Excellent": "#20D9A2",
    "Good": "#60A5FA",
    "Needs Improvement": "#FBBF24",
    "Critical": "#FB7185",
}


def _safe_percentage(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    return np.where(denominator > 0, numerator / denominator * 100, 0.0)


def _health_category(score: pd.Series) -> pd.Series:
    return pd.Series(
        np.select(
            [score >= 85, score >= 70, score >= 55],
            ["Excellent", "Good", "Needs Improvement"],
            default="Critical",
        ),
        index=score.index,
        dtype="string",
    )


def _alert_level(df: pd.DataFrame) -> pd.Series:
    high = (
        (df["performance_score"] < 55)
        | ((df["target_achievement_pct"] < 75) & (df["revenue_growth_pct"] < -10))
        | (df["complaint_rate"] >= 7)
        | (df["on_time_service_pct"] < 70)
    )
    medium = (
        (df["performance_score"] < 70)
        | (df["target_achievement_pct"] < 90)
        | (df["complaint_rate"] >= 5)
        | (df["on_time_service_pct"] < 80)
    )
    return pd.Series(np.select([high, medium], ["High", "Medium"], default="Low"), index=df.index)


def _issues(row: pd.Series) -> list[str]:
    issues: list[str] = []
    if row["target_achievement_pct"] < 90:
        issues.append("revenue below 90% of target")
    elif row["target_achievement_pct"] < 100:
        issues.append("revenue below target")
    if row["revenue_growth_pct"] < -5:
        issues.append("declining monthly revenue")
    if row["customer_rating"] < 3.8:
        issues.append("low customer rating")
    if row["complaint_rate"] >= 5:
        issues.append("elevated complaint rate")
    if row["on_time_service_pct"] < 85:
        issues.append("service delays")
    return issues


def _recommendation(row: pd.Series) -> str:
    components = {
        "revenue": row["revenue_component_score"],
        "growth": row["growth_component_score"],
        "rating": row["rating_component_score"],
        "complaints": row["complaint_component_score"],
        "service": row["service_component_score"],
    }
    weakest = min(components, key=components.get)
    recommendations = {
        "revenue": "Review local conversion, product mix, and promotions; set a weekly recovery target against the revenue gap.",
        "growth": "Compare the latest sales mix with the prior month and replicate practices from the strongest peer outlet.",
        "rating": "Review recent customer feedback, coach the service team, and track the top two experience issues weekly.",
        "complaints": "Run a complaint root-cause review, assign owners to recurring issues, and verify closure within seven days.",
        "service": "Audit peak-hour staffing and order hand-offs, then monitor on-time service daily until it exceeds 90%.",
    }
    if row["health_category"] == "Excellent" and row["alert_level"] == "Low":
        return "Maintain the operating plan and document the outlet's strongest practice for replication across peers."
    return recommendations[weakest]


def _insight(row: pd.Series) -> str:
    issues = _issues(row)
    if row["health_category"] == "Excellent":
        return (
            f"{row['outlet_name']} is a leading outlet with a {row['performance_score']:.1f} score, "
            f"{row['target_achievement_pct']:.1f}% target achievement, and {row['revenue_growth_pct']:+.1f}% monthly growth."
        )
    if issues:
        return (
            f"{row['outlet_name']} needs attention due to {', '.join(issues[:2])}. "
            f"Its score is {row['performance_score']:.1f} and it ranks #{int(row['rank'])} for the month."
        )
    return (
        f"{row['outlet_name']} is stable with a {row['performance_score']:.1f} score and "
        f"{row['target_achievement_pct']:.1f}% target achievement; no major operating risk is detected."
    )


def calculate_performance_metrics(source: pd.DataFrame) -> pd.DataFrame:
    """Recompute all Milestone 1 derived measures from validated source values."""
    df = source.copy()

    # Preserve precomputed inputs for audit comparison, then replace them with one methodology.
    for column in ["performance_score", "rank", "benchmark_revenue", "benchmark_gap_pct"]:
        if column in df.columns:
            df[f"source_{column}"] = df[column]

    df["target_achievement_pct"] = _safe_percentage(df["revenue"], df["target_revenue"])
    df["revenue_growth_pct"] = np.where(
        df["previous_month_revenue"] > 0,
        (df["revenue"] / df["previous_month_revenue"] - 1) * 100,
        0.0,
    )
    df["benchmark_revenue"] = df.groupby("date")["revenue"].transform("mean")
    df["benchmark_gap_pct"] = _safe_percentage(
        df["revenue"] - df["benchmark_revenue"], df["benchmark_revenue"]
    )

    df["revenue_component_score"] = df["target_achievement_pct"].clip(0, 100)
    df["growth_component_score"] = (50 + 2.5 * df["revenue_growth_pct"]).clip(0, 100)
    df["rating_component_score"] = (df["customer_rating"] / 5 * 100).clip(0, 100)
    df["complaint_component_score"] = (100 - 10 * df["complaint_rate"]).clip(0, 100)
    df["service_component_score"] = df["on_time_service_pct"].clip(0, 100)

    df["performance_score"] = (
        SCORE_WEIGHTS["Revenue target achievement"] * df["revenue_component_score"]
        + SCORE_WEIGHTS["Month-over-month growth"] * df["growth_component_score"]
        + SCORE_WEIGHTS["Customer rating"] * df["rating_component_score"]
        + SCORE_WEIGHTS["Complaint control"] * df["complaint_component_score"]
        + SCORE_WEIGHTS["On-time service"] * df["service_component_score"]
    ).round(1)
    df["health_category"] = _health_category(df["performance_score"])
    df["alert_level"] = _alert_level(df)

    # Stable tie-breakers guarantee a unique 1..N ranking for every month.
    df = df.sort_values(
        ["date", "performance_score", "target_achievement_pct", "revenue", "outlet_id"],
        ascending=[True, False, False, False, True],
    )
    df["rank"] = df.groupby("date").cumcount() + 1

    df["issue_tags"] = df.apply(lambda row: ", ".join(_issues(row)) or "No major issue", axis=1)
    df["insight"] = df.apply(_insight, axis=1)
    df["recommendation"] = df.apply(_recommendation, axis=1)
    return df.sort_values(["date", "rank"]).reset_index(drop=True)


def rerank_snapshot(snapshot: pd.DataFrame) -> pd.DataFrame:
    """Rank the currently selected peer group without changing its underlying score."""
    ranked = snapshot.sort_values(
        ["performance_score", "target_achievement_pct", "revenue", "outlet_id"],
        ascending=[False, False, False, True],
    ).copy()
    ranked["peer_rank"] = np.arange(1, len(ranked) + 1)
    return ranked


def score_component_frame(row: pd.Series) -> pd.DataFrame:
    """Return one outlet's component scores and weights for visualization."""
    return pd.DataFrame(
        {
            "component": list(COMPONENT_COLUMNS.keys()),
            "score": [float(row[column]) for column in COMPONENT_COLUMNS.values()],
            "weight": [SCORE_WEIGHTS[name] for name in COMPONENT_COLUMNS],
        }
    )
