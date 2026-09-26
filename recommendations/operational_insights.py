import pandas as pd
import numpy as np
from pathlib import Path


# --------------------------------------------------
# Operational Insights - Milestone 3
# --------------------------------------------------
# Purpose:
# Convert monthly outlet data into one actionable operational
# insight record per outlet.
#
# Design principles:
# 1. Remove duplicate test records before aggregation.
# 2. Aggregate once at outlet/month level, then once at outlet level.
# 3. Use vectorized NumPy/Pandas logic instead of row-wise apply.
# 4. Detect multiple issues simultaneously; do not overwrite one
#    issue with another.
# 5. Use recent 3-month trends so insights reflect current operations.
# 6. Produce an explainable risk score and primary action.
# --------------------------------------------------


PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "FranchiseOps_AI_Milestone2_Inventory_Dataset.xlsx"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "operational_insights_output.csv"
)

# --------------------------------------------------
# Configuration
# --------------------------------------------------

RECENT_MONTHS = 3

REQUIRED_COLUMNS = [
    "Record_ID",
    "Outlet_ID",
    "Outlet_Name",
    "Outlet_Type",
    "City",
    "State",
    "Region",
    "Month",
    "Footfall",
    "Orders",
    "Conversion_Rate_%",
    "Sales_Revenue_INR",
    "Profit_INR",
    "Profit_Margin_%",
    "Employees",
    "Employee_Turnover_%",
    "Customer_Satisfaction_1_5",
    "Complaints",
    "Inventory_Units_Sold",
    "Closing_Stock_Units",
    "Wastage_Units",
    "Freshness_Rate_%",
]


# --------------------------------------------------
# Load
# --------------------------------------------------
df = pd.read_excel(
    INPUT_FILE,
    sheet_name="Raw_Outlet_Data",
)

print(f"Raw records: {len(df):,}")


# --------------------------------------------------
# Validate schema
# --------------------------------------------------

missing = sorted(set(REQUIRED_COLUMNS) - set(df.columns))

if missing:
    raise ValueError(
        f"Missing required columns: {missing}"
    )


# --------------------------------------------------
# Remove duplicate test records
# --------------------------------------------------
# Dataset_Info states that duplicate test rows were added.
# Record_ID is the record-level identifier, so keeping the first
# occurrence prevents duplicate rows from inflating KPIs.

before = len(df)

df = df.drop_duplicates(
    subset="Record_ID",
    keep="first",
).copy()

duplicates_removed = before - len(df)

print(f"Duplicate records removed: {duplicates_removed:,}")


# --------------------------------------------------
# Data preparation
# --------------------------------------------------

df["Month"] = pd.to_datetime(
    df["Month"].astype(str),
    format="%Y-%m",
    errors="coerce",
)

numeric_columns = [
    "Footfall",
    "Orders",
    "Conversion_Rate_%",
    "Sales_Revenue_INR",
    "Profit_INR",
    "Profit_Margin_%",
    "Employees",
    "Employee_Turnover_%",
    "Customer_Satisfaction_1_5",
    "Complaints",
    "Inventory_Units_Sold",
    "Closing_Stock_Units",
    "Wastage_Units",
    "Freshness_Rate_%",
]

df[numeric_columns] = df[numeric_columns].apply(
    pd.to_numeric,
    errors="coerce",
)

# Replace impossible denominators with NaN.
df.loc[df["Footfall"] < 0, "Footfall"] = np.nan

df.loc[df["Orders"] < 0, "Orders"] = np.nan


# --------------------------------------------------
# Monthly outlet aggregation
# --------------------------------------------------
# This preserves the time dimension and allows recent-trend
# calculations without processing every raw row repeatedly.

monthly = (
    df.groupby(
        [
            "Outlet_ID",
            "Outlet_Name",
            "Outlet_Type",
            "City",
            "State",
            "Region",
            "Month",
        ],
        as_index=False,
    )
    .agg(
        Footfall=("Footfall", "sum"),
        Orders=("Orders", "sum"),
        Sales=("Sales_Revenue_INR", "sum"),
        Profit=("Profit_INR", "sum"),
        Complaints=("Complaints", "sum"),
        Units_Sold=("Inventory_Units_Sold", "sum"),
        Wastage=("Wastage_Units", "sum"),
        Avg_Satisfaction=(
            "Customer_Satisfaction_1_5",
            "mean",
        ),
        Avg_Employee_Turnover=(
            "Employee_Turnover_%",
            "mean",
        ),
        Avg_Freshness=(
            "Freshness_Rate_%",
            "mean",
        ),
        Avg_Closing_Stock=(
            "Closing_Stock_Units",
            "mean",
        ),
    )
)


def safe_divide(numerator, denominator):
    return np.divide(
        numerator,
        denominator,
        out=np.full_like(
            numerator,
            np.nan,
            dtype=float,
        ),
        where=denominator != 0,
    )


monthly["Conversion_Rate_%"] = (
    safe_divide(
        monthly["Orders"].to_numpy(),
        monthly["Footfall"].to_numpy(),
    )
    * 100
)

monthly["Profit_Margin_%"] = (
    safe_divide(
        monthly["Profit"].to_numpy(),
        monthly["Sales"].to_numpy(),
    )
    * 100
)

wastage_base = (
    monthly["Units_Sold"]
    + monthly["Wastage"]
)

monthly["Wastage_Rate_%"] = (
    safe_divide(
        monthly["Wastage"].to_numpy(),
        wastage_base.to_numpy(),
    )
    * 100
)
# --------------------------------------------------
# Recent-period selection
# --------------------------------------------------

latest_month = monthly["Month"].max()

recent_months = (
    monthly["Month"]
    .dropna()
    .drop_duplicates()
    .nlargest(RECENT_MONTHS)
    .sort_values()
)

recent = monthly[
    monthly["Month"].isin(recent_months)
].copy()

print(
    "Latest month:",
    latest_month.strftime("%Y-%m")
)

print(
    "Recent months:",
    ", ".join(
        month.strftime("%Y-%m")
        for month in recent_months
    )
)


# --------------------------------------------------
# Recent outlet metrics
# --------------------------------------------------
# Aggregating the recent period gives stable operational
# indicators instead of reacting to one abnormal month.

recent_summary = (
    recent.groupby(
        [
            "Outlet_ID",
            "Outlet_Name",
            "Outlet_Type",
            "City",
            "State",
            "Region",
        ],
        as_index=False,
    )
    .agg(
        Recent_Sales=("Sales", "sum"),
        Recent_Profit=("Profit", "sum"),
        Recent_Footfall=("Footfall", "sum"),
        Recent_Orders=("Orders", "sum"),
        Recent_Complaints=("Complaints", "sum"),
        Recent_Units_Sold=("Units_Sold", "sum"),
        Recent_Wastage=("Wastage", "sum"),
        Avg_Satisfaction=(
            "Avg_Satisfaction",
            "mean",
        ),
        Avg_Employee_Turnover=(
            "Avg_Employee_Turnover",
            "mean",
        ),
        Avg_Freshness=(
            "Avg_Freshness",
            "mean",
        ),
        Avg_Closing_Stock=(
            "Avg_Closing_Stock",
            "mean",
        ),
    )
)

recent_summary["Conversion_Rate_%"] = (
    safe_divide(
        recent_summary["Recent_Orders"].to_numpy(),
        recent_summary["Recent_Footfall"].to_numpy(),
    )
    * 100
)

recent_summary["Profit_Margin_%"] = (
    safe_divide(
        recent_summary["Recent_Profit"].to_numpy(),
        recent_summary["Recent_Sales"].to_numpy(),
    )
    * 100
)

recent_summary["Complaints_Per_1000_Orders"] = (
    safe_divide(
        recent_summary["Recent_Complaints"].to_numpy(),
        recent_summary["Recent_Orders"].to_numpy(),
    )
    * 1000
)

recent_wastage_base = (
    recent_summary["Recent_Units_Sold"]
    + recent_summary["Recent_Wastage"]
)

recent_summary["Wastage_Rate_%"] = (
    safe_divide(
        recent_summary["Recent_Wastage"].to_numpy(),
        recent_wastage_base.to_numpy(),
    )
    * 100
)


# --------------------------------------------------
# --------------------------------------------------
# Recent vs previous period trend
# --------------------------------------------------
# Compare the latest 3 months against the 3 months
# immediately before them. This is more stable than
# comparing only the first and last recent month.

all_months = (
    monthly["Month"]
    .dropna()
    .drop_duplicates()
    .sort_values()
    .tolist()
)

if len(all_months) < RECENT_MONTHS * 2:
    raise ValueError(
        "At least 6 months of valid data are required "
        "for operational trend analysis."
    )

recent_months = all_months[-RECENT_MONTHS:]
previous_months = all_months[
    -RECENT_MONTHS * 2 : -RECENT_MONTHS
]

recent_trend = (
    monthly[
        monthly["Month"].isin(recent_months)
    ]
    .groupby("Outlet_ID", as_index=False)
    .agg(
        Recent_Trend_Sales=("Sales", "mean"),
        Recent_Trend_Profit=("Profit", "mean"),
        Recent_Trend_Orders=("Orders", "mean"),
    )
)

previous_trend = (
    monthly[
        monthly["Month"].isin(previous_months)
    ]
    .groupby("Outlet_ID", as_index=False)
    .agg(
        Previous_Trend_Sales=("Sales", "mean"),
        Previous_Trend_Profit=("Profit", "mean"),
        Previous_Trend_Orders=("Orders", "mean"),
    )
)

trend = recent_trend.merge(
    previous_trend,
    on="Outlet_ID",
    how="left",
)


def safe_pct_change(current, previous):
    denominator = previous.abs()

    return np.where(
        denominator > 1e-9,
        (current - previous)
        / denominator
        * 100,
        np.nan,
    )


trend["Sales_Trend_%"] = safe_pct_change(
    trend["Recent_Trend_Sales"],
    trend["Previous_Trend_Sales"],
)

trend["Profit_Trend_%"] = safe_pct_change(
    trend["Recent_Trend_Profit"],
    trend["Previous_Trend_Profit"],
)

trend["Orders_Trend_%"] = safe_pct_change(
    trend["Recent_Trend_Orders"],
    trend["Previous_Trend_Orders"],
)

trend = trend[
    [
        "Outlet_ID",
        "Sales_Trend_%",
        "Profit_Trend_%",
        "Orders_Trend_%",
    ]
]

# --------------------------------------------------
# Combine operational metrics + trends
# --------------------------------------------------

outlet = recent_summary.merge(
    trend,
    on="Outlet_ID",
    how="left",
)


# --------------------------------------------------
# Peer benchmarks
# --------------------------------------------------
# Median is used because it is robust to extreme outlets.
# Benchmarks are calculated across the same recent period.

benchmark_columns = [
    "Conversion_Rate_%",
    "Profit_Margin_%",
    "Complaints_Per_1000_Orders",
    "Wastage_Rate_%",
    "Avg_Employee_Turnover",
    "Avg_Satisfaction",
]

benchmarks = outlet[benchmark_columns].median()


# --------------------------------------------------
# Issue detection
# --------------------------------------------------
# Each issue is independent. Multiple issues can therefore be
# detected for the same outlet.

outlet["Issue_Low_Conversion"] = (
    outlet["Conversion_Rate_%"]
    < benchmarks["Conversion_Rate_%"]
    * 0.85
)

outlet["Issue_Profit_Deterioration"] = (
    (
        outlet["Profit_Trend_%"] < -10
    )
    |
    (
        outlet["Profit_Margin_%"]
        < benchmarks["Profit_Margin_%"]
        * 0.85
    )
)

outlet["Issue_Customer_Complaints"] = (
    outlet["Complaints_Per_1000_Orders"]
    > benchmarks["Complaints_Per_1000_Orders"]
    * 1.25
)

outlet["Issue_Employee_Turnover"] = (
    outlet["Avg_Employee_Turnover"]
    > benchmarks["Avg_Employee_Turnover"]
    * 1.25
)

outlet["Issue_Customer_Satisfaction"] = (
    outlet["Avg_Satisfaction"] < 3.0
)

outlet["Issue_Wastage"] = (
    outlet["Wastage_Rate_%"]
    > benchmarks["Wastage_Rate_%"]
    * 1.25
)

outlet["Issue_Sales_Deterioration"] = (
    outlet["Sales_Trend_%"] < -10
)




# --------------------------------------------------
# Issue summary
# --------------------------------------------------

issue_columns = [
    "Issue_Low_Conversion",
    "Issue_Profit_Deterioration",
    "Issue_Customer_Complaints",
    "Issue_Employee_Turnover",
    "Issue_Customer_Satisfaction",
    "Issue_Wastage",
    "Issue_Sales_Deterioration",
]

outlet["Issue_Count"] = (
    outlet[issue_columns]
    .sum(axis=1)
)

issue_labels = {
    "Issue_Low_Conversion": "Conversion",
    "Issue_Profit_Deterioration": "Profitability",
    "Issue_Customer_Complaints": "Customer Complaints",
    "Issue_Employee_Turnover": "Employee Turnover",
    "Issue_Customer_Satisfaction": "Customer Satisfaction",
    "Issue_Wastage": "Inventory Wastage",
    "Issue_Sales_Deterioration": "Sales Decline",
}

detected_issue_frame = (
    outlet[issue_columns]
    .rename(columns=issue_labels)
)

outlet["Detected_Issues"] = (
    detected_issue_frame
    .where(detected_issue_frame, "")
    .astype(str)
    .apply(
        lambda row: ", ".join(
            value
            for value in row
            if value
        ),
        axis=1,
    )
)



# --------------------------------------------------
# Risk score
# --------------------------------------------------
# Weighted scoring makes serious customer/financial issues
# contribute more than lower-impact operational signals.

outlet["Operational_Risk_Score"] = (
    outlet["Issue_Profit_Deterioration"].astype(int) * 2
    + outlet["Issue_Sales_Deterioration"].astype(int) * 2
    + outlet["Issue_Low_Conversion"].astype(int)
    + outlet["Issue_Customer_Complaints"].astype(int)
    + outlet["Issue_Employee_Turnover"].astype(int)
    + outlet["Issue_Customer_Satisfaction"].astype(int)
    + outlet["Issue_Wastage"].astype(int)
)


# --------------------------------------------------
# Risk category
# --------------------------------------------------

outlet["Operational_Risk"] = np.select(
    [
        outlet["Operational_Risk_Score"] >= 5,
        outlet["Operational_Risk_Score"] >= 3,
        outlet["Operational_Risk_Score"] >= 1,
    ],
    [
        "High",
        "Medium",
        "Watch",
    ],
    default="Low",
)


# --------------------------------------------------
# Primary issue
# --------------------------------------------------
# Select the issue with the strongest relative deviation
# from its benchmark.

severity = pd.DataFrame(index=outlet.index)

severity["Profitability"] = np.maximum(
    np.maximum(
        (
            benchmarks["Profit_Margin_%"]
            - outlet["Profit_Margin_%"]
        )
        / max(benchmarks["Profit_Margin_%"], 1e-9),
        (
            -outlet["Profit_Trend_%"]
        ) / 100,
    ),
    0,
)

severity["Sales Decline"] = (
    np.maximum(
        -outlet["Sales_Trend_%"] / 100,
        0,
    )
)

severity["Customer Complaints"] = (
    np.maximum(
        outlet["Complaints_Per_1000_Orders"]
        / max(
            benchmarks["Complaints_Per_1000_Orders"],
            1e-9,
        )
        - 1,
        0,
    )
)

severity["Employee Turnover"] = (
    np.maximum(
        outlet["Avg_Employee_Turnover"]
        / max(
            benchmarks["Avg_Employee_Turnover"],
            1e-9,
        )
        - 1,
        0,
    )
)

severity["Customer Satisfaction"] = (
    np.maximum(
        3.0 - outlet["Avg_Satisfaction"],
        0,
    )
)

severity["Conversion"] = (
    np.maximum(
        benchmarks["Conversion_Rate_%"]
        - outlet["Conversion_Rate_%"],
        0,
    )
    / max(
        benchmarks["Conversion_Rate_%"],
        1e-9,
    )
)

severity["Inventory Wastage"] = (
    np.maximum(
        outlet["Wastage_Rate_%"]
        / max(
            benchmarks["Wastage_Rate_%"],
            1e-9,
        )
        - 1,
        0,
    )
)

outlet["Primary_Operational_Issue"] = (
    severity.idxmax(axis=1)
)

outlet.loc[
    outlet["Issue_Count"] == 0,
    "Primary_Operational_Issue",
] = "No Major Issue"

# --------------------------------------------------
# Action
# --------------------------------------------------

# --------------------------------------------------
# Recommended action
# --------------------------------------------------

action_map = {
    "Profitability":
        "Review costs, pricing and product profitability",

    "Sales Decline":
        "Investigate declining demand and outlet sales drivers",

    "Customer Satisfaction":
        "Review service quality and customer experience",

    "Customer Complaints":
        "Investigate complaint drivers and service bottlenecks",

    "Conversion":
        "Improve footfall-to-order conversion",

    "Inventory Wastage":
        "Review stock handling, demand planning and shelf-life management",

    "Employee Turnover":
        "Review staffing stability and retention factors",

    "No Major Issue":
        "Continue monitoring",
}

outlet["Recommended_Action"] = (
    outlet["Primary_Operational_Issue"]
    .map(action_map)
    .fillna("Continue monitoring")
)


# --------------------------------------------------
# Human-readable insight
# --------------------------------------------------

outlet["Operational_Insight"] = (
    outlet["Primary_Operational_Issue"]
    + " | "
    + outlet["Recommended_Action"]
)


# --------------------------------------------------
# Final output
# --------------------------------------------------

output_columns = [
    "Outlet_ID",
    "Outlet_Name",
    "Outlet_Type",
    "City",
    "State",
    "Region",
    "Recent_Sales",
    "Recent_Profit",
    "Profit_Margin_%",
    "Conversion_Rate_%",
    "Recent_Orders",
    "Complaints_Per_1000_Orders",
    "Avg_Satisfaction",
    "Avg_Employee_Turnover",
    "Wastage_Rate_%",
    "Avg_Freshness",
    "Sales_Trend_%",
    "Profit_Trend_%",
    "Orders_Trend_%",
    "Operational_Risk_Score",
    "Operational_Risk",
    "Issue_Count",
    "Detected_Issues",
    "Primary_Operational_Issue",
    "Recommended_Action",
    "Operational_Insight",
]


output = (
    outlet[output_columns]
    .sort_values(
        [
            "Operational_Risk_Score",
            "Recent_Profit",
        ],
        ascending=[False, True],
    )
    .reset_index(drop=True)
)


# --------------------------------------------------
# Save
# --------------------------------------------------

OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True,
)
# Final numeric validation
numeric_output = output.select_dtypes(
    include=np.number
)

if np.isinf(numeric_output.to_numpy()).any():
    raise ValueError(
        "Infinite values detected in operational insights output."
    )

output.to_csv(
    OUTPUT_FILE,
    index=False,
)


# --------------------------------------------------
# Validation
# --------------------------------------------------
if output["Outlet_ID"].nunique() != len(output):
    raise ValueError(
        "Output contains duplicate Outlet_ID records."
    )
print("\nOperational Insights completed.")
print(f"Clean records used: {len(df):,}")
print(f"Outlets analyzed: {output['Outlet_ID'].nunique():,}")
print(f"Output records: {len(output):,}")
print(f"Output saved to: {OUTPUT_FILE}")

print("\nRisk distribution:")
print(output["Operational_Risk"].value_counts())

print("\nPrimary issue distribution:")
print(output["Primary_Operational_Issue"].value_counts())

print("\nTop operational issues:")
print(
    output[
        [
            "Outlet_ID",
            "Outlet_Name",
            "Operational_Risk_Score",
            "Operational_Risk",
            "Primary_Operational_Issue",
            "Recommended_Action",
        ]
    ]
    .head(10)
    .to_string(index=False)
)
