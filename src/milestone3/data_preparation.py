"""Validated preparation for the Milestone 2 and 3 combined dataset."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


SHEET_NAME = "Combined_M2_M3_Data"
KEY_COLUMNS = ["Outlet_ID", "SKU_ID", "Month"]

CORE_COLUMNS = [
    "Record_ID",
    "Outlet_ID",
    "Outlet_Name",
    "Region",
    "Month",
    "Orders",
    "Conversion_Rate_%",
    "Average_Order_Value_INR",
    "Sales_Revenue_INR",
    "Marketing_Spend_INR",
    "Employees",
    "Employee_Turnover_%",
    "Customer_Satisfaction_1_5",
    "Complaints",
    "SKU_ID",
    "Stock_Status",
    "Recommended_Replenishment_Units",
    "Stock_Availability_%",
]

MILESTONE3_COLUMNS = [
    "Staff_Productivity_Score",
    "Attendance_Rate_%",
    "Staff_Performance_Score",
    "Staff_Performance_Category",
    "Workforce_Scheduling_Status",
    "Campaign_ID",
    "Campaign_Type",
    "Marketing_Reach",
    "Marketing_Conversions",
    "Customer_Engagement_Rate_%",
    "Campaign_ROI",
    "Marketing_Performance_Category",
]

NUMERIC_COLUMNS = [
    "Orders",
    "Conversion_Rate_%",
    "Average_Order_Value_INR",
    "Sales_Revenue_INR",
    "Marketing_Spend_INR",
    "Employees",
    "Employee_Turnover_%",
    "Customer_Satisfaction_1_5",
    "Complaints",
    "Recommended_Replenishment_Units",
    "Stock_Availability_%",
    "Staff_Productivity_Score",
    "Attendance_Rate_%",
    "Staff_Performance_Score",
    "Marketing_Reach",
    "Marketing_Conversions",
    "Customer_Engagement_Rate_%",
    "Campaign_ROI",
]

MILESTONE3_NUMERIC_COLUMNS = [
    "Staff_Productivity_Score",
    "Attendance_Rate_%",
    "Staff_Performance_Score",
    "Marketing_Reach",
    "Marketing_Conversions",
    "Customer_Engagement_Rate_%",
    "Campaign_ROI",
]


class Milestone3DataError(ValueError):
    """Raised when the Milestone 3 source cannot be prepared safely."""


def _validate_ranges(data: pd.DataFrame) -> None:
    bounded = {
        "Staff_Productivity_Score": (0, 100),
        "Attendance_Rate_%": (0, 100),
        "Staff_Performance_Score": (0, 100),
        "Customer_Engagement_Rate_%": (0, 100),
        "Stock_Availability_%": (0, 100),
    }
    for column, (minimum, maximum) in bounded.items():
        if not data[column].between(minimum, maximum).all():
            raise Milestone3DataError(
                f"{column} contains values outside {minimum}-{maximum}"
            )

    non_negative = [
        "Employees",
        "Marketing_Reach",
        "Marketing_Conversions",
        "Recommended_Replenishment_Units",
    ]
    for column in non_negative:
        if (data[column] < 0).any():
            raise Milestone3DataError(f"{column} contains negative values")

    if (data["Marketing_Conversions"] > data["Marketing_Reach"]).any():
        raise Milestone3DataError("Marketing conversions exceed campaign reach")

    engagement = (
        data["Marketing_Conversions"]
        / data["Marketing_Reach"].replace(0, pd.NA)
        * 100
    ).fillna(0)
    if (engagement - data["Customer_Engagement_Rate_%"]).abs().max() > 0.011:
        raise Milestone3DataError(
            "Customer engagement rate does not reconcile to conversions / reach"
        )


def _validate_categories(data: pd.DataFrame) -> None:
    allowed = {
        "Staff_Performance_Category": {
            "Top Performer",
            "Meets Expectations",
            "Needs Improvement",
        },
        "Workforce_Scheduling_Status": {
            "Understaffed",
            "Balanced",
            "Overstaffed",
        },
        "Marketing_Performance_Category": {
            "High Performing",
            "Moderate",
            "Needs Improvement",
        },
    }
    for column, valid_values in allowed.items():
        invalid = sorted(set(data[column]) - valid_values)
        if invalid:
            raise Milestone3DataError(
                f"{column} contains unknown values: {', '.join(invalid)}"
            )


def prepare_milestone3_data(
    source: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, int | str | float]]:
    """Validate, type, and deterministically deduplicate Milestone 3 records."""
    required_columns = CORE_COLUMNS + MILESTONE3_COLUMNS
    missing = sorted(set(required_columns) - set(source.columns))
    if missing:
        raise Milestone3DataError(
            "Milestone 3 source is missing required columns: " + ", ".join(missing)
        )

    data = source[required_columns].copy()
    source_rows = len(data)
    core_missing_cells = int(data[CORE_COLUMNS].isna().sum().sum())

    for column in ["Record_ID", "Outlet_ID", "Outlet_Name", "Region", "SKU_ID"]:
        data[column] = data[column].astype("string").str.strip()
    for column in [
        "Staff_Performance_Category",
        "Workforce_Scheduling_Status",
        "Campaign_ID",
        "Campaign_Type",
        "Marketing_Performance_Category",
        "Stock_Status",
    ]:
        data[column] = data[column].astype("string").str.strip()

    data["Month"] = pd.to_datetime(data["Month"], errors="coerce")
    for column in NUMERIC_COLUMNS:
        data[column] = pd.to_numeric(data[column], errors="coerce")

    required_keys = ["Record_ID", "Outlet_ID", "Outlet_Name", "Region", "SKU_ID", "Month"]
    if data[required_keys].isna().any().any():
        raise Milestone3DataError("Milestone 3 source contains invalid identity or date values")
    if data["Record_ID"].duplicated().any():
        raise Milestone3DataError("Milestone 3 source contains duplicate Record_ID values")
    if data[MILESTONE3_NUMERIC_COLUMNS].isna().any().any():
        raise Milestone3DataError("Milestone 3 measures contain missing or invalid values")
    if data[MILESTONE3_COLUMNS].isna().any().any():
        raise Milestone3DataError("Milestone 3 fields contain missing values")

    duplicate_key_rows = int(data.duplicated(KEY_COLUMNS, keep="first").sum())
    data = data.drop_duplicates(KEY_COLUMNS, keep="first").copy()
    data = data.sort_values(KEY_COLUMNS).reset_index(drop=True)

    _validate_ranges(data)
    _validate_categories(data)

    expected_months = data["Month"].nunique()
    monthly_coverage = data.groupby("Outlet_ID")["Month"].nunique()
    if not monthly_coverage.eq(expected_months).all():
        raise Milestone3DataError("Milestone 3 outlets do not have complete monthly coverage")

    quality: dict[str, int | str | float] = {
        "status": "Passed",
        "source_rows": source_rows,
        "prepared_rows": len(data),
        "duplicate_keys_removed": duplicate_key_rows,
        "record_id_duplicates": 0,
        "outlets": int(data["Outlet_ID"].nunique()),
        "months": int(expected_months),
        "campaigns": int(data["Campaign_ID"].nunique()),
        "core_missing_cells": core_missing_cells,
        "milestone3_missing_cells": 0,
        "engagement_max_error_pct": float(
            (
                data["Customer_Engagement_Rate_%"]
                - data["Marketing_Conversions"]
                / data["Marketing_Reach"].replace(0, pd.NA)
                * 100
            )
            .abs()
            .max()
        ),
    }
    return data, quality


def load_milestone3_source(
    path: str | Path,
) -> tuple[pd.DataFrame, dict[str, int | str | float]]:
    """Read and prepare the combined Milestone 2 and 3 workbook."""
    source_path = Path(path)
    if not source_path.exists():
        raise FileNotFoundError(f"Milestone 3 source workbook not found: {source_path}")
    source = pd.read_excel(source_path, sheet_name=SHEET_NAME)
    return prepare_milestone3_data(source)
