"""Milestone 3 staff performance and workforce scheduling analysis."""

from __future__ import annotations

import pandas as pd


def _category_from_score(score: float, low_threshold: float, high_threshold: float) -> str:
    if score >= high_threshold:
        return "Top Performer"
    if score <= low_threshold:
        return "Needs Improvement"
    return "Meets Expectations"


def _alert_level(row: pd.Series) -> str:
    performance_risk = row["Workforce_Category"] == "Needs Improvement"
    schedule_risk = row["Latest_Scheduling_Status"] != "Balanced"
    if performance_risk and schedule_risk:
        return "High"
    if performance_risk or schedule_risk:
        return "Medium"
    return "Low"


def _insight(row: pd.Series) -> str:
    return (
        f"Average staff performance is {row['Average_Staff_Performance_Score']:.1f}/100 "
        f"with {row['Average_Attendance_Rate']:.1f}% attendance. "
        f"The latest workforce schedule is {str(row['Latest_Scheduling_Status']).lower()}, "
        f"and {int(row['Needs_Improvement_Months'])} of {int(row['Records'])} months "
        "were classified as needing improvement."
    )


def _recommendation(row: pd.Series) -> str:
    schedule = row["Latest_Scheduling_Status"]
    if row["Workforce_Alert_Level"] == "High":
        if schedule == "Understaffed":
            return (
                "Add shift coverage, review attendance gaps, and provide targeted coaching "
                "for low-productivity periods."
            )
        return (
            "Rebalance excess shift coverage and use coaching or role changes to improve "
            "staff productivity."
        )
    if schedule == "Understaffed":
        return "Review demand-based rosters and add coverage during peak periods."
    if schedule == "Overstaffed":
        return "Align staffing hours with demand and move spare capacity to busier periods."
    return "Maintain the current schedule and continue monitoring attendance and productivity."


def build_staff_workforce_outputs(
    data: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Create outlet and monthly workforce outputs from prepared records."""
    ordered = data.sort_values(["Outlet_ID", "Month", "Record_ID"]).copy()
    low_threshold = float(ordered["Staff_Performance_Score"].quantile(0.25))
    high_threshold = float(ordered["Staff_Performance_Score"].quantile(0.75))

    ordered["_top"] = ordered["Staff_Performance_Category"].eq("Top Performer")
    ordered["_needs"] = ordered["Staff_Performance_Category"].eq("Needs Improvement")
    ordered["_balanced"] = ordered["Workforce_Scheduling_Status"].eq("Balanced")
    ordered["_under"] = ordered["Workforce_Scheduling_Status"].eq("Understaffed")
    ordered["_over"] = ordered["Workforce_Scheduling_Status"].eq("Overstaffed")

    outlets = (
        ordered.groupby(["Outlet_ID", "Outlet_Name"], as_index=False)
        .agg(
            Records=("Month", "nunique"),
            Average_Employees=("Employees", "mean"),
            Average_Productivity_Score=("Staff_Productivity_Score", "mean"),
            Average_Attendance_Rate=("Attendance_Rate_%", "mean"),
            Average_Staff_Performance_Score=("Staff_Performance_Score", "mean"),
            Top_Performer_Months=("_top", "sum"),
            Needs_Improvement_Months=("_needs", "sum"),
            Balanced_Months=("_balanced", "sum"),
            Understaffed_Months=("_under", "sum"),
            Overstaffed_Months=("_over", "sum"),
        )
    )

    latest = (
        ordered.groupby("Outlet_ID", as_index=False, group_keys=False)
        .tail(1)[
            [
                "Outlet_ID",
                "Month",
                "Staff_Performance_Score",
                "Staff_Performance_Category",
                "Workforce_Scheduling_Status",
            ]
        ]
        .rename(
            columns={
                "Month": "Latest_Month",
                "Staff_Performance_Score": "Latest_Staff_Performance_Score",
                "Staff_Performance_Category": "Latest_Staff_Category",
                "Workforce_Scheduling_Status": "Latest_Scheduling_Status",
            }
        )
    )
    outlets = outlets.merge(latest, on="Outlet_ID", how="left", validate="one_to_one")
    outlets["Workforce_Category"] = outlets["Average_Staff_Performance_Score"].apply(
        _category_from_score,
        args=(low_threshold, high_threshold),
    )
    outlets["Workforce_Alert_Level"] = outlets.apply(_alert_level, axis=1)
    outlets["Workforce_Insight"] = outlets.apply(_insight, axis=1)
    outlets["Workforce_Recommendation"] = outlets.apply(_recommendation, axis=1)

    monthly = (
        ordered.groupby("Month", as_index=False)
        .agg(
            Outlets_Recorded=("Outlet_ID", "nunique"),
            Average_Employees=("Employees", "mean"),
            Average_Productivity_Score=("Staff_Productivity_Score", "mean"),
            Average_Attendance_Rate=("Attendance_Rate_%", "mean"),
            Average_Staff_Performance_Score=("Staff_Performance_Score", "mean"),
            Balanced_Outlets=("_balanced", "sum"),
            Understaffed_Outlets=("_under", "sum"),
            Overstaffed_Outlets=("_over", "sum"),
        )
        .sort_values("Month")
    )

    numeric_columns = outlets.select_dtypes(include="number").columns
    outlets[numeric_columns] = outlets[numeric_columns].round(2)
    monthly[monthly.select_dtypes(include="number").columns] = monthly.select_dtypes(
        include="number"
    ).round(2)
    return outlets.sort_values("Outlet_ID").reset_index(drop=True), monthly.reset_index(
        drop=True
    )
