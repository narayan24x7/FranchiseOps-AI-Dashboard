from pathlib import Path

import numpy as np

from src.analytics import SCORE_WEIGHTS, calculate_performance_metrics, rerank_snapshot
from src.data_loader import load_outlet_data


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "raw" / "franchiseops_filtered_outlet_data.csv"


def _processed():
    source, _ = load_outlet_data(DATA_PATH)
    return calculate_performance_metrics(source)


def test_score_weights_sum_to_one():
    assert np.isclose(sum(SCORE_WEIGHTS.values()), 1.0)


def test_calculated_scores_are_bounded_and_complete():
    data = _processed()
    assert data["performance_score"].between(0, 100).all()
    assert data[["health_category", "alert_level", "insight", "recommendation"]].notna().all().all()


def test_every_month_has_unique_complete_ranks():
    data = _processed()
    for _, group in data.groupby("date"):
        assert sorted(group["rank"].tolist()) == list(range(1, len(group) + 1))


def test_monthly_benchmark_equals_peer_mean():
    data = _processed()
    for _, group in data.groupby("date"):
        assert np.allclose(group["benchmark_revenue"], group["revenue"].mean())


def test_health_thresholds_and_alerts_are_consistent():
    data = _processed()
    assert (data.loc[data["performance_score"] >= 85, "health_category"] == "Excellent").all()
    assert (data.loc[data["performance_score"] < 55, "health_category"] == "Critical").all()
    assert (data.loc[data["health_category"] == "Critical", "alert_level"] == "High").all()


def test_filtered_peer_ranking_is_contiguous():
    data = _processed()
    snapshot = data[data["date"] == data["date"].max()].query("region == 'West'")
    ranked = rerank_snapshot(snapshot)
    assert ranked["peer_rank"].tolist() == list(range(1, len(ranked) + 1))
