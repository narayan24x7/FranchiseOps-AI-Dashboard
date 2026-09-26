from pathlib import Path

import pandas as pd
import pytest

from src.data_loader import (
    DataValidationError,
    load_outlet_data,
    resolve_outlet_data_path,
    validate_outlet_data,
)


ROOT = Path(__file__).resolve().parents[1]


def test_resolve_outlet_data_path_prefers_raw_runtime_csv(tmp_path):
    raw = tmp_path / "data" / "raw" / "franchiseops_filtered_outlet_data.csv"
    processed = tmp_path / "data" / "processed" / "outlet_performance_intelligence.csv"
    raw.parent.mkdir(parents=True)
    processed.parent.mkdir(parents=True)
    raw.write_text("raw", encoding="utf-8")
    processed.write_text("processed", encoding="utf-8")
    assert resolve_outlet_data_path(tmp_path) == raw


def test_resolve_outlet_data_path_falls_back_to_processed_file(tmp_path):
    processed = tmp_path / "data" / "processed" / "outlet_performance_intelligence.csv"
    processed.parent.mkdir(parents=True)
    processed.write_text("processed", encoding="utf-8")
    assert resolve_outlet_data_path(tmp_path) == processed
DATA_PATH = ROOT / "data" / "raw" / "franchiseops_filtered_outlet_data.csv"


def test_source_data_passes_quality_checks():
    data, report = load_outlet_data(DATA_PATH)
    assert len(data) == 96
    assert report.outlets == 12
    assert report.months == 8
    assert report.missing_cells == 0
    assert report.duplicate_outlet_months == 0
    assert report.identity_conflicts == 0
    assert report.aov_reconciliation_max_error_pct < 0.01
    assert report.status == "Passed"


def test_duplicate_outlet_month_is_rejected():
    data, _ = load_outlet_data(DATA_PATH)
    duplicated = pd.concat([data, data.iloc[[0]]], ignore_index=True)
    with pytest.raises(DataValidationError, match="duplicate"):
        validate_outlet_data(duplicated)


def test_invalid_customer_rating_is_rejected():
    data, _ = load_outlet_data(DATA_PATH)
    data.loc[0, "customer_rating"] = 5.5
    with pytest.raises(DataValidationError, match="ratings"):
        validate_outlet_data(data)
