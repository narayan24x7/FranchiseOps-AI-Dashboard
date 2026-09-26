from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.milestone3.data_preparation import (
    Milestone3DataError,
    load_milestone3_source,
    prepare_milestone3_data,
)
from src.milestone3.loader import load_milestone3_outputs


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
SOURCE = (
    ROOT
    / "data"
    / "raw"
    / "FranchiseOps_AI_Milestone2_Milestone3_Combined_Dataset.xlsx"
)


def load_outputs():
    return load_milestone3_outputs(
        PROCESSED / "m3_staff_workforce_output.csv",
        PROCESSED / "m3_staff_monthly_summary.csv",
        PROCESSED / "m3_marketing_effectiveness_output.csv",
        PROCESSED / "m3_marketing_monthly_summary.csv",
        PROCESSED / "m3_operational_insights.csv",
        PROCESSED / "m3_data_quality.csv",
    )


def test_milestone3_source_preparation_removes_only_duplicate_business_keys():
    prepared, quality = load_milestone3_source(SOURCE)
    assert len(prepared) == 30_000
    assert quality["source_rows"] == 30_120
    assert quality["duplicate_keys_removed"] == 120
    assert quality["outlets"] == 750
    assert quality["months"] == 40
    assert quality["campaigns"] == 30_000
    assert quality["milestone3_missing_cells"] == 0
    assert quality["engagement_max_error_pct"] <= 0.0051
    assert not prepared.duplicated(["Outlet_ID", "SKU_ID", "Month"]).any()


def test_milestone3_outputs_have_full_shared_coverage_and_months():
    workforce, workforce_monthly, marketing, marketing_monthly, operations, quality = (
        load_outputs()
    )
    assert len(workforce) == len(marketing) == len(operations) == 750
    assert len(workforce_monthly) == len(marketing_monthly) == 40
    assert quality["shared_outlets"] == 750
    assert workforce["Records"].eq(40).all()
    assert workforce["Latest_Month"].eq(pd.Timestamp("2026-04-01")).all()
    assert set(workforce["Outlet_ID"]) == set(marketing["Outlet_ID"]) == set(
        operations["Outlet_ID"]
    )


def test_marketing_effectiveness_and_engagement_formulas_reconcile():
    _, _, marketing, _, _, _ = load_outputs()
    expected = (
        marketing["Revenue_Per_Marketing_Rupee"]
        / marketing["Revenue_Per_Marketing_Rupee"].max()
        * 100
        * 0.40
        + marketing["Average_Conversion_Rate"]
        / marketing["Average_Conversion_Rate"].max()
        * 100
        * 0.35
        + marketing["Total_Orders"]
        / marketing["Total_Orders"].max()
        * 100
        * 0.25
    )
    engagement = (
        marketing["Total_Marketing_Conversions"]
        / marketing["Total_Marketing_Reach"]
        * 100
    )
    assert np.allclose(marketing["Marketing_Effectiveness_Score"], expected, atol=0.021)
    assert np.allclose(marketing["Customer_Engagement_Rate"], engagement, atol=0.011)


def test_operational_score_reconciles_to_documented_weights():
    _, _, _, _, operations, _ = load_outputs()
    expected = (
        operations["Staff_Score"] * 0.35
        + operations["Marketing_Score"] * 0.35
        + operations["Inventory_Score"] * 0.30
    )
    assert np.allclose(operations["Operational_Health_Score"], expected, atol=0.011)
    assert operations["Cross_Functional_Risks"].between(0, 3).all()
    assert set(operations["Primary_Focus_Area"]).issubset(
        {"Staff workforce", "Marketing", "Inventory"}
    )


def test_data_preparation_rejects_invalid_engagement_rate():
    source = pd.read_excel(SOURCE, sheet_name="Combined_M2_M3_Data").head(2)
    source.loc[source.index[0], "Customer_Engagement_Rate_%"] = 99.0
    with pytest.raises(Milestone3DataError, match="engagement rate"):
        prepare_milestone3_data(source)
