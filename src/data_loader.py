"""Data loading and validation for outlet performance intelligence."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd


BASE_COLUMNS = [
    "date",
    "outlet_id",
    "outlet_name",
    "city",
    "region",
    "revenue",
    "target_revenue",
    "previous_month_revenue",
    "orders",
    "avg_order_value",
    "customer_rating",
    "complaint_rate",
    "on_time_service_pct",
]

NUMERIC_COLUMNS = [
    "revenue",
    "target_revenue",
    "previous_month_revenue",
    "orders",
    "avg_order_value",
    "customer_rating",
    "complaint_rate",
    "on_time_service_pct",
]

OUTLET_DATA_CANDIDATES = (
    Path("data/raw/franchiseops_filtered_outlet_data.csv"),
    Path("data/processed/outlet_performance_intelligence.csv"),
)


class DataValidationError(ValueError):
    """Raised when source outlet data cannot be safely analyzed."""


def resolve_outlet_data_path(project_root: str | Path) -> Path:
    """Return the first packaged Milestone 1 dataset suitable for the dashboard."""
    root = Path(project_root)
    checked: list[Path] = []
    for relative_path in OUTLET_DATA_CANDIDATES:
        candidate = root / relative_path
        checked.append(candidate)
        if candidate.is_file():
            return candidate
    checked_paths = ", ".join(str(path) for path in checked)
    raise FileNotFoundError(
        f"No packaged outlet dataset was found. Checked: {checked_paths}"
    )


@dataclass(frozen=True)
class DataQualityReport:
    rows: int
    outlets: int
    months: int
    missing_cells: int
    duplicate_outlet_months: int
    identity_conflicts: int
    aov_reconciliation_max_error_pct: float
    status: str

    def to_dict(self) -> dict[str, int | float | str]:
        return asdict(self)


def _clean_text(series: pd.Series) -> pd.Series:
    return series.astype("string").str.strip()


def build_quality_report(df: pd.DataFrame) -> DataQualityReport:
    """Return compact, auditable data-quality statistics."""
    identity_counts = df.groupby("outlet_id")[["outlet_name", "city", "region"]].nunique()
    identity_conflicts = int((identity_counts > 1).any(axis=1).sum())

    expected_revenue = df["orders"] * df["avg_order_value"]
    denominator = df["revenue"].replace(0, np.nan)
    reconciliation = ((df["revenue"] - expected_revenue).abs() / denominator * 100).fillna(0)

    missing_cells = int(df[BASE_COLUMNS].isna().sum().sum())
    duplicates = int(df.duplicated(["date", "outlet_id"]).sum())
    status = "Passed" if missing_cells == 0 and duplicates == 0 and identity_conflicts == 0 else "Review"

    return DataQualityReport(
        rows=len(df),
        outlets=int(df["outlet_id"].nunique()),
        months=int(df["date"].nunique()),
        missing_cells=missing_cells,
        duplicate_outlet_months=duplicates,
        identity_conflicts=identity_conflicts,
        aov_reconciliation_max_error_pct=round(float(reconciliation.max()), 4),
        status=status,
    )


def validate_outlet_data(df: pd.DataFrame) -> DataQualityReport:
    """Validate schema, uniqueness, ranges, and outlet identity consistency."""
    issues: list[str] = []
    missing_columns = sorted(set(BASE_COLUMNS) - set(df.columns))
    if missing_columns:
        raise DataValidationError(f"Missing required columns: {', '.join(missing_columns)}")

    if df[BASE_COLUMNS].isna().any().any():
        issues.append("required fields contain missing values")
    if df.duplicated(["date", "outlet_id"]).any():
        issues.append("duplicate outlet-month records were found")
    if (df["revenue"] < 0).any() or (df["previous_month_revenue"] < 0).any():
        issues.append("revenue values cannot be negative")
    if (df["target_revenue"] <= 0).any():
        issues.append("target revenue must be greater than zero")
    if (df["orders"] < 0).any() or (df["avg_order_value"] < 0).any():
        issues.append("order values cannot be negative")
    if not df["customer_rating"].between(0, 5).all():
        issues.append("customer ratings must be between 0 and 5")
    if not df["complaint_rate"].between(0, 100).all():
        issues.append("complaint rate must be between 0 and 100")
    if not df["on_time_service_pct"].between(0, 100).all():
        issues.append("on-time service must be between 0 and 100")

    report = build_quality_report(df)
    if report.identity_conflicts:
        issues.append("an outlet ID maps to conflicting names, cities, or regions")

    if issues:
        raise DataValidationError("; ".join(issues))
    return report


def load_outlet_data(path: str | Path) -> tuple[pd.DataFrame, DataQualityReport]:
    """Load a CSV, normalize types, and return validated source measures."""
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"Outlet data file not found: {source}")

    df = pd.read_csv(source)
    missing_columns = sorted(set(BASE_COLUMNS) - set(df.columns))
    if missing_columns:
        raise DataValidationError(f"Missing required columns: {', '.join(missing_columns)}")

    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    for column in ["outlet_id", "outlet_name", "city", "region"]:
        df[column] = _clean_text(df[column])
    for column in NUMERIC_COLUMNS:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    report = validate_outlet_data(df)
    return df.sort_values(["date", "outlet_id"]).reset_index(drop=True), report
