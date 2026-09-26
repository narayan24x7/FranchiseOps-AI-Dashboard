"""Validated loaders for Milestone 2 agent outputs."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


STAFF_COLUMNS = [
    "Outlet_ID",
    "Outlet_Name",
    "Avg_Employees",
    "Avg_Employee_Turnover",
    "Avg_Customer_Satisfaction",
    "Total_Complaints",
    "Staff_Status",
    "Insight",
    "Recommendation",
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
    "Marketing_Insights",
    "Recommendations",
]

INVENTORY_COLUMNS = [
    "Outlet_ID",
    "Outlet_Name",
    "Month",
    "Product_Category",
    "Product_Type",
    "SKU_ID",
    "Closing_Stock_Units",
    "Safety_Stock_Units",
    "Reorder_Point_Units",
    "Demand_Forecast_Next_Month_Units",
    "Stock_Status",
    "Replenishment_Required",
    "Recommended_Replenishment_Units",
    "Stock_Availability_%",
    "Inventory_Turnover_Ratio",
    "Wastage_Units",
    "Freshness_Rate_%",
    "Shelf_Life_Days",
    "Agent_Action",
    "Agent_Priority",
    "Agent_Explanation",
]

FORECAST_COLUMNS = [
    "Outlet_ID",
    "SKU_ID",
    "Month",
    "Inventory_Units_Sold",
    "Demand_Forecast_Next_Month_Units",
]

STAFF_NUMERIC_COLUMNS = [
    "Avg_Employees",
    "Avg_Employee_Turnover",
    "Avg_Customer_Satisfaction",
    "Total_Complaints",
]

MARKETING_NUMERIC_COLUMNS = [
    "Records",
    "Total_Marketing_Spend",
    "Total_Sales_Revenue",
    "Total_Orders",
    "Average_Conversion_Rate",
    "Revenue_Per_Marketing_Rupee",
    "Marketing_Spend_Percentage",
]

INVENTORY_NUMERIC_COLUMNS = [
    "Closing_Stock_Units",
    "Safety_Stock_Units",
    "Reorder_Point_Units",
    "Demand_Forecast_Next_Month_Units",
    "Recommended_Replenishment_Units",
    "Stock_Availability_%",
    "Inventory_Turnover_Ratio",
    "Wastage_Units",
    "Freshness_Rate_%",
    "Shelf_Life_Days",
]


class Milestone2DataError(ValueError):
    """Raised when an agent output cannot be safely displayed."""


def _load_agent_output(
    path: str | Path,
    required_columns: list[str],
    numeric_columns: list[str],
    label: str,
) -> pd.DataFrame:
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"{label} output not found: {source}")

    data = pd.read_csv(source)
    missing = sorted(set(required_columns) - set(data.columns))
    if missing:
        raise Milestone2DataError(
            f"{label} output is missing required columns: {', '.join(missing)}"
        )

    data = data[required_columns].copy()
    data["Outlet_ID"] = data["Outlet_ID"].astype("string").str.strip()
    for column in numeric_columns:
        data[column] = pd.to_numeric(data[column], errors="coerce")

    if data[required_columns].isna().any().any():
        raise Milestone2DataError(f"{label} output contains missing or invalid values")
    if data["Outlet_ID"].duplicated().any():
        raise Milestone2DataError(f"{label} output contains duplicate outlet IDs")

    return data.sort_values("Outlet_ID").reset_index(drop=True)


def load_staff_agent_output(path: str | Path) -> pd.DataFrame:
    """Load and validate the Staff Agent's outlet-level CSV output."""
    data = _load_agent_output(
        path,
        STAFF_COLUMNS,
        STAFF_NUMERIC_COLUMNS,
        "Staff Agent",
    )
    valid_statuses = {"Stable", "Needs Attention", "Critical"}
    invalid_statuses = sorted(set(data["Staff_Status"]) - valid_statuses)
    if invalid_statuses:
        raise Milestone2DataError(
            f"Staff Agent output contains unknown statuses: {', '.join(invalid_statuses)}"
        )
    return data


def load_marketing_agent_output(path: str | Path) -> pd.DataFrame:
    """Load and validate the Marketing Agent's outlet-level CSV output."""
    data = _load_agent_output(
        path,
        MARKETING_COLUMNS,
        MARKETING_NUMERIC_COLUMNS,
        "Marketing Agent",
    )
    valid_categories = {"High Performing", "Moderate", "Needs Improvement"}
    invalid_categories = sorted(set(data["Marketing_Category"]) - valid_categories)
    if invalid_categories:
        raise Milestone2DataError(
            "Marketing Agent output contains unknown categories: "
            + ", ".join(invalid_categories)
        )

    valid_alerts = {"High", "Medium", "Low"}
    invalid_alerts = sorted(set(data["Alert_Level"]) - valid_alerts)
    if invalid_alerts:
        raise Milestone2DataError(
            f"Marketing Agent output contains unknown alerts: {', '.join(invalid_alerts)}"
        )
    return data


def load_inventory_agent_output(path: str | Path) -> pd.DataFrame:
    """Load and validate the Inventory Agent's monthly SKU output."""
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"Inventory Agent output not found: {source}")

    data = pd.read_csv(source)
    missing = sorted(set(INVENTORY_COLUMNS) - set(data.columns))
    if missing:
        raise Milestone2DataError(
            "Inventory Agent output is missing required columns: " + ", ".join(missing)
        )

    data = data[INVENTORY_COLUMNS].copy()
    data["Outlet_ID"] = data["Outlet_ID"].astype("string").str.strip()
    data["SKU_ID"] = data["SKU_ID"].astype("string").str.strip()
    data["Month"] = pd.to_datetime(data["Month"], errors="coerce")
    for column in INVENTORY_NUMERIC_COLUMNS:
        data[column] = pd.to_numeric(data[column], errors="coerce")

    if data[INVENTORY_COLUMNS].isna().any().any():
        raise Milestone2DataError(
            "Inventory Agent output contains missing or invalid values"
        )
    key = ["Outlet_ID", "SKU_ID", "Month"]
    if data.duplicated(key).any():
        raise Milestone2DataError(
            "Inventory Agent output contains duplicate outlet/SKU/month rows"
        )

    allowed = {
        "Stock_Status": {"Critical", "Low", "Healthy", "Overstocked"},
        "Agent_Action": {
            "URGENT_REORDER",
            "REORDER",
            "REDUCE_STOCK",
            "MONITOR_WASTAGE",
            "NO_ACTION",
        },
        "Agent_Priority": {"High", "Medium", "Low"},
        "Replenishment_Required": {"Yes", "No"},
    }
    for column, valid_values in allowed.items():
        invalid = sorted(set(data[column]) - valid_values)
        if invalid:
            raise Milestone2DataError(
                f"Inventory Agent output contains unknown {column} values: "
                + ", ".join(invalid)
            )
    return data.sort_values(key).reset_index(drop=True)


def load_demand_forecast_output(path: str | Path) -> pd.DataFrame:
    """Load forecasting history; cold-start rows may have an empty forecast."""
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"Demand Forecast output not found: {source}")

    data = pd.read_csv(source)
    missing = sorted(set(FORECAST_COLUMNS) - set(data.columns))
    if missing:
        raise Milestone2DataError(
            "Demand Forecast output is missing required columns: " + ", ".join(missing)
        )

    data = data[FORECAST_COLUMNS].copy()
    data["Outlet_ID"] = data["Outlet_ID"].astype("string").str.strip()
    data["SKU_ID"] = data["SKU_ID"].astype("string").str.strip()
    data["Month"] = pd.to_datetime(data["Month"], errors="coerce")
    data["Inventory_Units_Sold"] = pd.to_numeric(
        data["Inventory_Units_Sold"], errors="coerce"
    )
    data["Demand_Forecast_Next_Month_Units"] = pd.to_numeric(
        data["Demand_Forecast_Next_Month_Units"], errors="coerce"
    )

    required_values = ["Outlet_ID", "SKU_ID", "Month", "Inventory_Units_Sold"]
    if data[required_values].isna().any().any():
        raise Milestone2DataError(
            "Demand Forecast output contains missing or invalid required values"
        )
    if (data["Inventory_Units_Sold"] < 0).any() or (
        data["Demand_Forecast_Next_Month_Units"].dropna() < 0
    ).any():
        raise Milestone2DataError("Demand Forecast output contains negative demand")

    key = ["Outlet_ID", "SKU_ID", "Month"]
    if data.duplicated(key).any():
        raise Milestone2DataError(
            "Demand Forecast output contains duplicate outlet/SKU/month rows"
        )
    return data.sort_values(key).reset_index(drop=True)


def load_milestone2_outputs(
    staff_path: str | Path,
    marketing_path: str | Path,
    inventory_path: str | Path,
    forecast_path: str | Path,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, int]]:
    """Load every Milestone 2 output and report end-to-end coverage."""
    staff = load_staff_agent_output(staff_path)
    marketing = load_marketing_agent_output(marketing_path)
    inventory = load_inventory_agent_output(inventory_path)
    forecast = load_demand_forecast_output(forecast_path)
    shared_outlets = (
        set(staff["Outlet_ID"])
        & set(marketing["Outlet_ID"])
        & set(inventory["Outlet_ID"])
        & set(forecast["Outlet_ID"])
    )
    return staff, marketing, inventory, forecast, {
        "staff_outlets": len(staff),
        "marketing_outlets": len(marketing),
        "inventory_outlets": int(inventory["Outlet_ID"].nunique()),
        "forecast_outlets": int(forecast["Outlet_ID"].nunique()),
        "inventory_records": len(inventory),
        "forecast_records": len(forecast),
        "forecast_skus": int(forecast["SKU_ID"].nunique()),
        "available_forecasts": int(
            forecast["Demand_Forecast_Next_Month_Units"].notna().sum()
        ),
        "shared_outlets": len(shared_outlets),
    }
