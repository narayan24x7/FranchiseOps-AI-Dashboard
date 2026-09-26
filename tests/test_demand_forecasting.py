import pandas as pd

from forecasting.demand_forecasting import calculate_forecast, get_latest_forecast


def test_forecast_uses_prior_three_months_and_removes_duplicate_test_rows():
    source = pd.DataFrame(
        {
            "Outlet_ID": ["OUT0001"] * 6,
            "SKU_ID": ["SKU-0001-01"] * 6,
            "Month": ["2026-01", "2026-02", "2026-03", "2026-03", "2026-04", "2026-05"],
            "Inventory_Units_Sold": [100, 200, 300, 999, 400, 500],
        }
    )
    result = calculate_forecast(source)
    assert len(result) == 5
    april = result[result["Month"] == pd.Timestamp("2026-04-01")].iloc[0]
    assert april["Demand_Forecast_Next_Month_Units"] == 200


def test_latest_forecast_returns_latest_record_for_each_sku():
    source = pd.DataFrame(
        {
            "Outlet_ID": ["OUT0001", "OUT0001", "OUT0002", "OUT0002"],
            "SKU_ID": ["SKU-1", "SKU-1", "SKU-2", "SKU-2"],
            "Month": pd.to_datetime(["2026-01", "2026-02", "2026-01", "2026-03"]),
            "Inventory_Units_Sold": [10, 20, 30, 40],
            "Demand_Forecast_Next_Month_Units": [pd.NA, pd.NA, pd.NA, pd.NA],
        }
    )
    latest = get_latest_forecast(source)
    assert len(latest) == 2
    assert set(latest["Month"]) == {
        pd.Timestamp("2026-02-01"),
        pd.Timestamp("2026-03-01"),
    }
