"""Milestone 3 marketing effectiveness and campaign analysis."""

from __future__ import annotations

import pandas as pd

from src.marketing_agent.marketing_agent import build_marketing_agent_output


def _effectiveness_category(score: float) -> str:
    if score >= 75:
        return "High Performing"
    if score <= 25:
        return "Needs Improvement"
    return "Moderate"


def _campaign_category(roi: float, low_threshold: float, high_threshold: float) -> str:
    if roi >= high_threshold:
        return "High Performing"
    if roi <= low_threshold:
        return "Needs Improvement"
    return "Moderate"


def _mode(series: pd.Series) -> str:
    modes = sorted(series.mode().astype(str).tolist())
    return modes[0] if modes else "Unknown"


def _insight(row: pd.Series) -> str:
    return (
        f"Marketing effectiveness is {row['Marketing_Effectiveness_Score']:.1f}/100 "
        f"({row['Effectiveness_Category']}). Campaign ROI averages "
        f"{row['Average_Campaign_ROI']:.2f}, with {row['Customer_Engagement_Rate']:.2f}% "
        f"engagement across {int(row['Campaign_Records'])} campaigns."
    )


def _recommendation(row: pd.Series) -> str:
    if row["Effectiveness_Category"] == "Needs Improvement" or row[
        "Campaign_Performance_Category"
    ] == "Needs Improvement":
        return (
            "Review low-ROI campaigns, narrow audience targeting, and move budget to "
            "campaign types with stronger conversion results."
        )
    if row["Alert_Level"] == "Medium":
        return (
            "Test campaign offers and targeting to improve conversion while protecting "
            "revenue per marketing rupee."
        )
    return (
        "Continue the strongest campaign mix and scale spend only where ROI and engagement "
        "remain above the network benchmark."
    )


def calculate_marketing_effectiveness(performance: pd.DataFrame) -> pd.DataFrame:
    """Apply the supplied Milestone 3 weighted effectiveness formula."""
    result = performance.copy()
    components = {
        "Revenue_Per_Marketing_Rupee": 0.40,
        "Average_Conversion_Rate": 0.35,
        "Total_Orders": 0.25,
    }
    score = pd.Series(0.0, index=result.index)
    for column, weight in components.items():
        maximum = float(result[column].max())
        if maximum > 0:
            score = score + result[column] / maximum * 100 * weight
    result["Marketing_Effectiveness_Score"] = score.round(2)
    result["Effectiveness_Category"] = result[
        "Marketing_Effectiveness_Score"
    ].apply(_effectiveness_category)
    return result


def build_marketing_effectiveness_outputs(
    data: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Create outlet and monthly campaign effectiveness outputs."""
    base = calculate_marketing_effectiveness(build_marketing_agent_output(data))

    campaign = data.copy()
    campaign["_high"] = campaign["Marketing_Performance_Category"].eq(
        "High Performing"
    )
    campaign["_needs"] = campaign["Marketing_Performance_Category"].eq(
        "Needs Improvement"
    )
    outlet_campaigns = (
        campaign.groupby("Outlet_ID", as_index=False)
        .agg(
            Campaign_Records=("Campaign_ID", "nunique"),
            Total_Marketing_Reach=("Marketing_Reach", "sum"),
            Total_Marketing_Conversions=("Marketing_Conversions", "sum"),
            Average_Campaign_ROI=("Campaign_ROI", "mean"),
            High_Performing_Campaigns=("_high", "sum"),
            Needs_Improvement_Campaigns=("_needs", "sum"),
            Primary_Campaign_Type=("Campaign_Type", _mode),
        )
    )
    outlet_campaigns["Customer_Engagement_Rate"] = (
        outlet_campaigns["Total_Marketing_Conversions"]
        / outlet_campaigns["Total_Marketing_Reach"].replace(0, pd.NA)
        * 100
    ).fillna(0)
    roi_low = float(outlet_campaigns["Average_Campaign_ROI"].quantile(0.25))
    roi_high = float(outlet_campaigns["Average_Campaign_ROI"].quantile(0.75))
    outlet_campaigns["Campaign_Performance_Category"] = outlet_campaigns[
        "Average_Campaign_ROI"
    ].apply(_campaign_category, args=(roi_low, roi_high))

    output = base.merge(outlet_campaigns, on="Outlet_ID", how="left", validate="one_to_one")
    output["Marketing_Effectiveness_Insight"] = output.apply(_insight, axis=1)
    output["Marketing_Effectiveness_Recommendation"] = output.apply(
        _recommendation, axis=1
    )

    monthly = (
        campaign.groupby("Month", as_index=False)
        .agg(
            Campaigns=("Campaign_ID", "nunique"),
            Marketing_Spend=("Marketing_Spend_INR", "sum"),
            Marketing_Reach=("Marketing_Reach", "sum"),
            Marketing_Conversions=("Marketing_Conversions", "sum"),
            Average_Campaign_ROI=("Campaign_ROI", "mean"),
            High_Performing_Campaigns=("_high", "sum"),
            Needs_Improvement_Campaigns=("_needs", "sum"),
        )
        .sort_values("Month")
    )
    monthly["Customer_Engagement_Rate"] = (
        monthly["Marketing_Conversions"]
        / monthly["Marketing_Reach"].replace(0, pd.NA)
        * 100
    ).fillna(0)

    numeric_columns = output.select_dtypes(include="number").columns
    output[numeric_columns] = output[numeric_columns].round(2)
    monthly[monthly.select_dtypes(include="number").columns] = monthly.select_dtypes(
        include="number"
    ).round(2)
    return output.sort_values("Outlet_ID").reset_index(drop=True), monthly.reset_index(
        drop=True
    )
