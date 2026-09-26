"""Rule-based Inventory Agent for FranchiseOps AI Milestone 2."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "FranchiseOps_AI_Milestone2_Inventory_Dataset.xlsx"
)
OUTPUT_FILE = PROJECT_ROOT / "data" / "processed" / "inventory_agent_output.csv"

REQUIRED_COLUMNS = [
    "Outlet_ID",
    "Outlet_Name",
    "Month",
    "Product_Category",
    "Product_Type",
    "SKU_ID",
    "Closing_Stock_Units",
    "Safety_Stock_Units",
    "Supplier_Lead_Time_Days",
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
]

OUTPUT_COLUMNS = [
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

NUMERIC_COLUMNS = [
    "Closing_Stock_Units",
    "Safety_Stock_Units",
    "Supplier_Lead_Time_Days",
    "Reorder_Point_Units",
    "Demand_Forecast_Next_Month_Units",
    "Recommended_Replenishment_Units",
    "Stock_Availability_%",
    "Inventory_Turnover_Ratio",
    "Wastage_Units",
    "Freshness_Rate_%",
    "Shelf_Life_Days",
]


def load_inventory_data(path: str | Path = INPUT_FILE) -> pd.DataFrame:
    """Load the Milestone 2 inventory sheet."""
    return pd.read_excel(path, sheet_name="Raw_Outlet_Data")


def prepare_inventory_data(df: pd.DataFrame) -> pd.DataFrame:
    """Validate inventory fields and remove the supplied duplicate test rows."""
    missing_columns = sorted(set(REQUIRED_COLUMNS) - set(df.columns))
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    data = df[REQUIRED_COLUMNS].copy()
    data["Month"] = pd.to_datetime(data["Month"], format="%Y-%m", errors="coerce")
    for column in NUMERIC_COLUMNS:
        data[column] = pd.to_numeric(data[column], errors="coerce")

    if data[REQUIRED_COLUMNS].isna().any().any():
        raise ValueError("Inventory data contains missing or invalid required values.")

    non_negative = [
        "Closing_Stock_Units",
        "Safety_Stock_Units",
        "Supplier_Lead_Time_Days",
        "Reorder_Point_Units",
        "Demand_Forecast_Next_Month_Units",
        "Recommended_Replenishment_Units",
        "Inventory_Turnover_Ratio",
        "Wastage_Units",
        "Shelf_Life_Days",
    ]
    if (data[non_negative] < 0).any().any():
        raise ValueError("Inventory quantities and rates cannot be negative.")
    if not data["Stock_Availability_%"].between(0, 100).all():
        raise ValueError("Stock availability must be between 0 and 100.")
    if not data["Freshness_Rate_%"].between(0, 100).all():
        raise ValueError("Freshness rate must be between 0 and 100.")

    return data.drop_duplicates(
        subset=["Outlet_ID", "SKU_ID", "Month"], keep="first"
    ).reset_index(drop=True)


def generate_inventory_action(row: pd.Series) -> str:
    if row["Stock_Status"] == "Critical":
        return "URGENT_REORDER"
    if row["Stock_Status"] == "Low":
        return "REORDER"
    if row["Stock_Status"] == "Overstocked":
        return "REDUCE_STOCK"
    if row["Product_Type"] == "Perishable" and row["Wastage_Units"] > 0:
        return "MONITOR_WASTAGE"
    if row["Replenishment_Required"] == "Yes":
        return "REORDER"
    return "NO_ACTION"


def generate_priority(row: pd.Series) -> str:
    if row["Stock_Status"] == "Critical":
        return "High"
    if row["Stock_Status"] in {"Low", "Overstocked"}:
        return "Medium"
    if row["Product_Type"] == "Perishable" and row["Wastage_Units"] > 0:
        return "Medium"
    return "Low"


def generate_explanation(row: pd.Series) -> str:
    if row["Stock_Status"] == "Critical":
        return (
            "Stock is critically low compared with inventory requirements. "
            "Immediate replenishment is recommended."
        )
    if row["Stock_Status"] == "Low":
        return (
            "Stock is below the desired inventory level. "
            "Replenishment should be planned."
        )
    if row["Stock_Status"] == "Overstocked":
        return (
            "Inventory is higher than the required level. "
            "Reduce or delay replenishment to avoid excess stock."
        )
    if row["Product_Type"] == "Perishable" and row["Wastage_Units"] > 0:
        return (
            "Inventory is currently adequate, but wastage is present. "
            "Monitor stock usage and freshness."
        )
    return "Inventory level is currently healthy. No immediate action is required."


def build_inventory_agent_output(df: pd.DataFrame) -> pd.DataFrame:
    """Run cleaning, rules, prioritization, and explanation generation."""
    output = prepare_inventory_data(df)
    output["Agent_Action"] = output.apply(generate_inventory_action, axis=1)
    output["Agent_Priority"] = output.apply(generate_priority, axis=1)
    output["Agent_Explanation"] = output.apply(generate_explanation, axis=1)

    priority_order = pd.CategoricalDtype(
        categories=["High", "Medium", "Low"], ordered=True
    )
    output["Agent_Priority"] = output["Agent_Priority"].astype(priority_order)
    return (
        output[OUTPUT_COLUMNS]
        .sort_values(
            ["Agent_Priority", "Outlet_ID", "SKU_ID", "Month"],
            ascending=[True, True, True, True],
        )
        .reset_index(drop=True)
    )


def save_output(output: pd.DataFrame, path: str | Path = OUTPUT_FILE) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(destination, index=False, date_format="%Y-%m")


def main() -> None:
    print("Starting Inventory Agent...")
    source = load_inventory_data()
    output = build_inventory_agent_output(source)
    save_output(output)
    print(f"Loaded records: {len(source):,}")
    print(f"Removed duplicate outlet/SKU/month rows: {len(source) - len(output):,}")
    print(f"Validated inventory records: {len(output):,}")
    print(f"Output saved to: {OUTPUT_FILE}")
    print("\nAgent action distribution:")
    print(output["Agent_Action"].value_counts().to_string())
    print("\nAgent priority distribution:")
    print(output["Agent_Priority"].value_counts().to_string())


if __name__ == "__main__":
    main()
