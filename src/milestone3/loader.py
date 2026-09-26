"""Validated loaders for Milestone 3 dashboard outputs."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


WORKFORCE_COLUMNS = [
    "Outlet_ID",
    "Outlet_Name",
    "Records",
    "Average_Employees",
    "Average_Productivity_Score",
    "Average_Attendance_Rate",
    "Average_Staff_Performance_Score",
    "Top_Performer_Months",
    "Needs_Improvement_Months",
    "Balanced_Months",
    "Understaffed_Months",
    "Overstaffed_Months",
    "Latest_Month",
    "Latest_Staff_Performance_Score",
    "Latest_Staff_Category",
    "Latest_Scheduling_Status",
    "Workforce_Category",
    "Workforce_Alert_Level",
    "Workforce_Insight",
    "Workforce_Recommendation",
]

WORKFORCE_MONTHLY_COLUMNS = [
    "Month",
    "Outlets_Recorded",
    "Average_Employees",
    "Average_Productivity_Score",
    "Average_Attendance_Rate",
    "Average_Staff_Performance_Score",
    "Balanced_Outlets",
    "Understaffed_Outlets",
    "Overstaffed_Outlets",
]

MARKETING_COLUMNS = [
    "Outlet_ID",
    "Records",
    "Total_Marketing_Spend",
    "Total_Sales_Revenue",
    "Total_Orders",
    "Average_Conversion_Rate",
    "Revenue_Per_Marketing_Rupee",
    "Marketing_Spend_Percentage",
    "Marketing_Category",
    "Alert_Level",
    "Marketing_Effectiveness_Score",
    "Effectiveness_Category",
    "Campaign_Records",
    "Total_Marketing_Reach",
    "Total_Marketing_Conversions",
    "Average_Campaign_ROI",
    "High_Performing_Campaigns",
    "Needs_Improvement_Campaigns",
    "Primary_Campaign_Type",
    "Customer_Engagement_Rate",
    "Campaign_Performance_Category",
    "Marketing_Effectiveness_Insight",
    "Marketing_Effectiveness_Recommendation",
]

MARKETING_MONTHLY_COLUMNS = [
    "Month",
    "Campaigns",
    "Marketing_Spend",
    "Marketing_Reach",
    "Marketing_Conversions",
    "Average_Campaign_ROI",
    "High_Performing_Campaigns",
    "Needs_Improvement_Campaigns",
    "Customer_Engagement_Rate",
]

OPERATIONS_COLUMNS = [
    "Outlet_ID",
    "Outlet_Name",
    "Staff_Score",
    "Workforce_Category",
    "Workforce_Alert_Level",
    "Latest_Scheduling_Status",
    "Marketing_Score",
    "Effectiveness_Category",
    "Marketing_Alert_Level",
    "Average_Campaign_ROI",
    "Inventory_Score",
    "High_Risk_SKUs",
    "Recommended_Replenishment_Units",
    "Inventory_Priority",
    "Inventory_Action",
    "Inventory_Status",
    "Operational_Health_Score",
    "Cross_Functional_Risks",
    "Primary_Focus_Area",
    "Operational_Priority",
    "Operational_Insight",
    "Recommended_Action",
]


class Milestone3OutputError(ValueError):
    """Raised when a Milestone 3 output cannot be displayed safely."""


def _read(path: str | Path, columns: list[str], label: str) -> pd.DataFrame:
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"{label} output not found: {source}")
    data = pd.read_csv(source)
    missing = sorted(set(columns) - set(data.columns))
    if missing:
        raise Milestone3OutputError(
            f"{label} output is missing required columns: {', '.join(missing)}"
        )
    return data[columns].copy()


def _validate_outlet_output(
    data: pd.DataFrame,
    label: str,
    numeric_columns: list[str],
) -> pd.DataFrame:
    data["Outlet_ID"] = data["Outlet_ID"].astype("string").str.strip()
    for column in numeric_columns:
        data[column] = pd.to_numeric(data[column], errors="coerce")
    if data.isna().any().any():
        raise Milestone3OutputError(f"{label} output contains missing or invalid values")
    if data["Outlet_ID"].duplicated().any():
        raise Milestone3OutputError(f"{label} output contains duplicate outlet IDs")
    return data.sort_values("Outlet_ID").reset_index(drop=True)


def load_workforce_outputs(
    outlet_path: str | Path, monthly_path: str | Path
) -> tuple[pd.DataFrame, pd.DataFrame]:
    workforce = _read(outlet_path, WORKFORCE_COLUMNS, "Staff Workforce")
    workforce["Latest_Month"] = pd.to_datetime(
        workforce["Latest_Month"], errors="coerce"
    )
    workforce = _validate_outlet_output(
        workforce,
        "Staff Workforce",
        [
            "Records",
            "Average_Employees",
            "Average_Productivity_Score",
            "Average_Attendance_Rate",
            "Average_Staff_Performance_Score",
            "Top_Performer_Months",
            "Needs_Improvement_Months",
            "Balanced_Months",
            "Understaffed_Months",
            "Overstaffed_Months",
            "Latest_Staff_Performance_Score",
        ],
    )
    allowed = {
        "Workforce_Category": {
            "Top Performer",
            "Meets Expectations",
            "Needs Improvement",
        },
        "Workforce_Alert_Level": {"High", "Medium", "Low"},
        "Latest_Scheduling_Status": {"Understaffed", "Balanced", "Overstaffed"},
    }
    for column, values in allowed.items():
        invalid = sorted(set(workforce[column]) - values)
        if invalid:
            raise Milestone3OutputError(
                f"Staff Workforce output contains unknown {column} values"
            )

    monthly = _read(monthly_path, WORKFORCE_MONTHLY_COLUMNS, "Monthly Workforce")
    monthly["Month"] = pd.to_datetime(monthly["Month"], errors="coerce")
    for column in WORKFORCE_MONTHLY_COLUMNS[1:]:
        monthly[column] = pd.to_numeric(monthly[column], errors="coerce")
    if monthly.isna().any().any() or monthly["Month"].duplicated().any():
        raise Milestone3OutputError("Monthly Workforce output contains invalid rows")
    return workforce, monthly.sort_values("Month").reset_index(drop=True)


def load_marketing_outputs(
    outlet_path: str | Path, monthly_path: str | Path
) -> tuple[pd.DataFrame, pd.DataFrame]:
    marketing = _read(outlet_path, MARKETING_COLUMNS, "Marketing Effectiveness")
    numeric = [
        column
        for column in MARKETING_COLUMNS
        if column
        not in {
            "Outlet_ID",
            "Marketing_Category",
            "Alert_Level",
            "Effectiveness_Category",
            "Primary_Campaign_Type",
            "Campaign_Performance_Category",
            "Marketing_Effectiveness_Insight",
            "Marketing_Effectiveness_Recommendation",
        }
    ]
    marketing = _validate_outlet_output(marketing, "Marketing Effectiveness", numeric)
    for column in ["Marketing_Category", "Effectiveness_Category", "Campaign_Performance_Category"]:
        invalid = sorted(
            set(marketing[column])
            - {"High Performing", "Moderate", "Needs Improvement"}
        )
        if invalid:
            raise Milestone3OutputError(
                f"Marketing Effectiveness output contains unknown {column} values"
            )
    if not set(marketing["Alert_Level"]).issubset({"High", "Medium", "Low"}):
        raise Milestone3OutputError("Marketing Effectiveness output has invalid alerts")

    monthly = _read(monthly_path, MARKETING_MONTHLY_COLUMNS, "Monthly Marketing")
    monthly["Month"] = pd.to_datetime(monthly["Month"], errors="coerce")
    for column in MARKETING_MONTHLY_COLUMNS[1:]:
        monthly[column] = pd.to_numeric(monthly[column], errors="coerce")
    if monthly.isna().any().any() or monthly["Month"].duplicated().any():
        raise Milestone3OutputError("Monthly Marketing output contains invalid rows")
    return marketing, monthly.sort_values("Month").reset_index(drop=True)


def load_operational_insights(path: str | Path) -> pd.DataFrame:
    operations = _read(path, OPERATIONS_COLUMNS, "Operational Insights")
    numeric = [
        "Staff_Score",
        "Marketing_Score",
        "Average_Campaign_ROI",
        "Inventory_Score",
        "High_Risk_SKUs",
        "Recommended_Replenishment_Units",
        "Operational_Health_Score",
        "Cross_Functional_Risks",
    ]
    operations = _validate_outlet_output(operations, "Operational Insights", numeric)
    if not set(operations["Operational_Priority"]).issubset({"High", "Medium", "Low"}):
        raise Milestone3OutputError("Operational Insights output has invalid priorities")
    return operations


def load_quality_output(path: str | Path) -> dict[str, int | str | float]:
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"Milestone 3 quality output not found: {source}")
    data = pd.read_csv(source)
    if len(data) != 1 or str(data.iloc[0].get("status")) != "Passed":
        raise Milestone3OutputError("Milestone 3 data-quality checks did not pass")
    return data.iloc[0].to_dict()


def load_milestone3_outputs(
    workforce_path: str | Path,
    workforce_monthly_path: str | Path,
    marketing_path: str | Path,
    marketing_monthly_path: str | Path,
    operations_path: str | Path,
    quality_path: str | Path,
) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    dict[str, int | str | float],
]:
    workforce, workforce_monthly = load_workforce_outputs(
        workforce_path, workforce_monthly_path
    )
    marketing, marketing_monthly = load_marketing_outputs(
        marketing_path, marketing_monthly_path
    )
    operations = load_operational_insights(operations_path)
    quality = load_quality_output(quality_path)
    shared = set(workforce["Outlet_ID"]) & set(marketing["Outlet_ID"]) & set(
        operations["Outlet_ID"]
    )
    if len(shared) != len(workforce) or len(shared) != len(marketing):
        raise Milestone3OutputError("Milestone 3 outputs do not share full outlet coverage")
    quality["shared_outlets"] = len(shared)
    return (
        workforce,
        workforce_monthly,
        marketing,
        marketing_monthly,
        operations,
        quality,
    )
