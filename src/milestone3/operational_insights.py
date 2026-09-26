"""Cross-functional operational insights for Milestone 3."""

from __future__ import annotations

import pandas as pd


INVENTORY_SCORE = {
    "Healthy": 100.0,
    "Overstocked": 60.0,
    "Low": 35.0,
    "Critical": 10.0,
}
PRIORITY_ORDER = {"Low": 0, "Medium": 1, "High": 2}


def _operational_priority(row: pd.Series) -> str:
    weak_components = sum(
        value < 55
        for value in [
            row["Staff_Score"],
            row["Marketing_Score"],
            row["Inventory_Score"],
        ]
    )
    if (
        row["Inventory_Priority"] == "High"
        or row["Operational_Health_Score"] < 55
        or weak_components >= 2
    ):
        return "High"
    if (
        row["Inventory_Priority"] == "Medium"
        or row["Operational_Health_Score"] < 70
        or row["Cross_Functional_Risks"] > 0
    ):
        return "Medium"
    return "Low"


def _focus_area(row: pd.Series) -> str:
    components = {
        "Staff workforce": row["Staff_Score"],
        "Marketing": row["Marketing_Score"],
        "Inventory": row["Inventory_Score"],
    }
    return min(components, key=lambda component: (components[component], component))


def _insight(row: pd.Series) -> str:
    return (
        f"Operational health is {row['Operational_Health_Score']:.1f}/100 with "
        f"{int(row['Cross_Functional_Risks'])} component(s) below 70. "
        f"The weakest area is {str(row['Primary_Focus_Area']).lower()}; the current "
        f"inventory action is {str(row['Inventory_Action']).replace('_', ' ').lower()}."
    )


def _recommendation(row: pd.Series) -> str:
    focus = row["Primary_Focus_Area"]
    if focus == "Staff workforce":
        return (
            "Review the latest roster, attendance, and productivity together, then adjust "
            "shift coverage before the next operating period."
        )
    if focus == "Marketing":
        return (
            "Review campaign ROI and engagement by campaign type, and reallocate spend to "
            "the strongest conversion sources."
        )
    if row["Inventory_Action"] in {"URGENT_REORDER", "REORDER"}:
        return (
            f"Complete the inventory action and plan {int(row['Recommended_Replenishment_Units']):,} "
            "replenishment units before the next demand cycle."
        )
    return (
        "Review the stock position, reduce avoidable excess or wastage, and align purchasing "
        "with the latest demand forecast."
    )


def _inventory_outlet_summary(inventory: pd.DataFrame) -> pd.DataFrame:
    latest = (
        inventory.sort_values(["Outlet_ID", "SKU_ID", "Month"])
        .groupby(["Outlet_ID", "SKU_ID"], as_index=False, group_keys=False)
        .tail(1)
        .copy()
    )
    latest["_inventory_score"] = latest["Stock_Status"].map(INVENTORY_SCORE)
    latest["_priority_rank"] = latest["Agent_Priority"].map(PRIORITY_ORDER)
    latest["_high_risk"] = latest["Agent_Priority"].eq("High")

    summary = (
        latest.groupby("Outlet_ID", as_index=False)
        .agg(
            Inventory_Score=("_inventory_score", "mean"),
            Inventory_Priority_Rank=("_priority_rank", "max"),
            High_Risk_SKUs=("_high_risk", "sum"),
            Recommended_Replenishment_Units=("Recommended_Replenishment_Units", "sum"),
        )
    )
    priority_name = {value: key for key, value in PRIORITY_ORDER.items()}
    summary["Inventory_Priority"] = summary["Inventory_Priority_Rank"].map(priority_name)

    worst = (
        latest.sort_values(
            ["Outlet_ID", "_priority_rank", "_inventory_score", "SKU_ID"],
            ascending=[True, False, True, True],
        )
        .groupby("Outlet_ID", as_index=False, group_keys=False)
        .head(1)[["Outlet_ID", "Agent_Action", "Stock_Status"]]
        .rename(
            columns={
                "Agent_Action": "Inventory_Action",
                "Stock_Status": "Inventory_Status",
            }
        )
    )
    return summary.merge(worst, on="Outlet_ID", how="left", validate="one_to_one")


def build_operational_insights(
    workforce: pd.DataFrame,
    marketing: pd.DataFrame,
    inventory: pd.DataFrame,
) -> pd.DataFrame:
    """Combine workforce, marketing, and inventory into one action queue."""
    staff = workforce[
        [
            "Outlet_ID",
            "Outlet_Name",
            "Average_Staff_Performance_Score",
            "Workforce_Category",
            "Workforce_Alert_Level",
            "Latest_Scheduling_Status",
        ]
    ].rename(columns={"Average_Staff_Performance_Score": "Staff_Score"})
    campaigns = marketing[
        [
            "Outlet_ID",
            "Marketing_Effectiveness_Score",
            "Effectiveness_Category",
            "Alert_Level",
            "Average_Campaign_ROI",
        ]
    ].rename(
        columns={
            "Marketing_Effectiveness_Score": "Marketing_Score",
            "Alert_Level": "Marketing_Alert_Level",
        }
    )
    stock = _inventory_outlet_summary(inventory)

    output = staff.merge(campaigns, on="Outlet_ID", how="inner", validate="one_to_one")
    output = output.merge(stock, on="Outlet_ID", how="inner", validate="one_to_one")
    output["Operational_Health_Score"] = (
        output["Staff_Score"] * 0.35
        + output["Marketing_Score"] * 0.35
        + output["Inventory_Score"] * 0.30
    ).round(2)
    output["Cross_Functional_Risks"] = (
        output[["Staff_Score", "Marketing_Score", "Inventory_Score"]] < 70
    ).sum(axis=1)
    output["Primary_Focus_Area"] = output.apply(_focus_area, axis=1)
    output["Operational_Priority"] = output.apply(_operational_priority, axis=1)
    output["Operational_Insight"] = output.apply(_insight, axis=1)
    output["Recommended_Action"] = output.apply(_recommendation, axis=1)
    output = output.drop(columns=["Inventory_Priority_Rank"])
    return output.sort_values("Outlet_ID").reset_index(drop=True)
