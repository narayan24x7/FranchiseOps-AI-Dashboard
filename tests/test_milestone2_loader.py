from pathlib import Path

import pandas as pd
import pytest

from src.milestone2_loader import (
    Milestone2DataError,
    load_demand_forecast_output,
    load_inventory_agent_output,
    load_marketing_agent_output,
    load_milestone2_outputs,
    load_staff_agent_output,
)


ROOT = Path(__file__).resolve().parents[1]


def test_project_agent_outputs_are_valid_and_have_shared_coverage():
    staff, marketing, inventory, forecast, quality = load_milestone2_outputs(
        ROOT / "staff_agent" / "staff_agent_output.csv",
        ROOT / "data" / "processed" / "marketing_agent_output.csv",
        ROOT / "data" / "processed" / "inventory_agent_output.csv",
        ROOT / "data" / "processed" / "demand_forecast_output.csv",
    )
    assert len(staff) == 750
    assert len(marketing) == 750
    assert len(inventory) == 30_000
    assert len(forecast) == 30_000
    assert quality["staff_outlets"] == 750
    assert quality["marketing_outlets"] == 750
    assert quality["inventory_outlets"] == 750
    assert quality["forecast_outlets"] == 750
    assert quality["forecast_skus"] == 750
    assert quality["available_forecasts"] == 27_750
    assert quality["shared_outlets"] == 750
    assert "OUT0706" in set(staff["Outlet_ID"])
    assert "OUT0706" in set(marketing["Outlet_ID"])


def test_inventory_loader_rejects_duplicate_monthly_sku_rows(tmp_path):
    source = pd.read_csv(
        ROOT / "data" / "processed" / "inventory_agent_output.csv"
    ).head(1)
    duplicate_path = tmp_path / "inventory.csv"
    pd.concat([source, source], ignore_index=True).to_csv(duplicate_path, index=False)
    with pytest.raises(Milestone2DataError, match="duplicate outlet/SKU/month"):
        load_inventory_agent_output(duplicate_path)


def test_forecast_loader_allows_expected_cold_start_values():
    forecast = load_demand_forecast_output(
        ROOT / "data" / "processed" / "demand_forecast_output.csv"
    )
    assert forecast["Demand_Forecast_Next_Month_Units"].isna().sum() == 2_250
    assert not forecast.groupby(["Outlet_ID", "SKU_ID"])[
        "Demand_Forecast_Next_Month_Units"
    ].last().isna().any()


def test_staff_loader_rejects_duplicate_outlet_ids(tmp_path):
    source = pd.read_csv(ROOT / "staff_agent" / "staff_agent_output.csv").head(1)
    duplicate_path = tmp_path / "staff.csv"
    pd.concat([source, source], ignore_index=True).to_csv(duplicate_path, index=False)
    with pytest.raises(Milestone2DataError, match="duplicate outlet IDs"):
        load_staff_agent_output(duplicate_path)


def test_marketing_loader_rejects_unknown_category(tmp_path):
    source = pd.read_csv(
        ROOT / "data" / "processed" / "marketing_agent_output.csv"
    ).head(1)
    source.loc[0, "Marketing_Category"] = "Unknown"
    invalid_path = tmp_path / "marketing.csv"
    source.to_csv(invalid_path, index=False)
    with pytest.raises(Milestone2DataError, match="unknown categories"):
        load_marketing_agent_output(invalid_path)
