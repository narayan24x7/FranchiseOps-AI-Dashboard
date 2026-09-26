"""Three-month moving-average demand forecasting for Milestone 2."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "FranchiseOps_AI_Milestone2_Inventory_Dataset.xlsx"
)
OUTPUT_FILE = PROJECT_ROOT / "data" / "processed" / "demand_forecast_output.csv"

FORECAST_WINDOW = 3
REQUIRED_COLUMNS = ["Outlet_ID", "SKU_ID", "Month", "Inventory_Units_Sold"]


def load_inventory_data(path: str | Path = INPUT_FILE) -> pd.DataFrame:
    """Load only the columns required by the forecasting pipeline."""
    return pd.read_excel(
        path,
        sheet_name="Raw_Outlet_Data",
        usecols=REQUIRED_COLUMNS,
    )


def validate_data(df: pd.DataFrame) -> None:
    """Validate required fields before forecasting."""
    missing_columns = sorted(set(REQUIRED_COLUMNS) - set(df.columns))
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")
    if df.empty:
        raise ValueError("Inventory dataset is empty.")
    if df[REQUIRED_COLUMNS].isna().any().any():
        raise ValueError("Forecast input contains missing required values.")


def prepare_forecast_data(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize types and remove duplicate outlet/SKU/month test rows."""
    validate_data(df)
    data = df[REQUIRED_COLUMNS].copy()
    data["Month"] = pd.to_datetime(
        data["Month"].astype(str), format="%Y-%m", errors="coerce"
    )
    data["Inventory_Units_Sold"] = pd.to_numeric(
        data["Inventory_Units_Sold"], errors="coerce"
    )
    if data[["Month", "Inventory_Units_Sold"]].isna().any().any():
        raise ValueError("Forecast input contains invalid dates or demand values.")
    if (data["Inventory_Units_Sold"] < 0).any():
        raise ValueError("Inventory units sold cannot be negative.")

    return data.drop_duplicates(
        subset=["Outlet_ID", "SKU_ID", "Month"], keep="first"
    ).reset_index(drop=True)


def calculate_forecast(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate each month's demand estimate from its prior three months."""
    data = prepare_forecast_data(df)
    data = data.sort_values(["Outlet_ID", "SKU_ID", "Month"])
    data["Demand_Forecast_Next_Month_Units"] = (
        data.groupby(["Outlet_ID", "SKU_ID"])["Inventory_Units_Sold"]
        .transform(
            lambda series: series.shift(1)
            .rolling(window=FORECAST_WINDOW, min_periods=FORECAST_WINDOW)
            .mean()
        )
        .round(2)
    )
    return data.reset_index(drop=True)


def get_latest_forecast(df: pd.DataFrame) -> pd.DataFrame:
    """Return the latest available record for every outlet/SKU pair."""
    return (
        df.sort_values(["Outlet_ID", "SKU_ID", "Month"])
        .groupby(["Outlet_ID", "SKU_ID"], as_index=False, group_keys=False)
        .tail(1)
        .reset_index(drop=True)
    )


def save_forecast(df: pd.DataFrame, path: str | Path = OUTPUT_FILE) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    df[
        [
            "Outlet_ID",
            "SKU_ID",
            "Month",
            "Inventory_Units_Sold",
            "Demand_Forecast_Next_Month_Units",
        ]
    ].to_csv(destination, index=False, date_format="%Y-%m-%d")


def main() -> None:
    print("Starting demand forecasting...")
    source = load_inventory_data()
    forecast = calculate_forecast(source)
    latest = get_latest_forecast(forecast)
    save_forecast(forecast)
    print(f"Loaded records: {len(source):,}")
    print(f"Removed duplicate outlet/SKU/month rows: {len(source) - len(forecast):,}")
    print(f"Validated forecast records: {len(forecast):,}")
    print(f"Latest forecasts available: {len(latest):,}")
    print(f"Latest historical month: {latest['Month'].max():%Y-%m}")
    print(f"Output saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
