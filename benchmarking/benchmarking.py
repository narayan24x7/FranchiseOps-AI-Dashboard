import pandas as pd
from pathlib import Path

# Load cleaned Milestone 1 dataset
project_root = Path(__file__).resolve().parent.parent
dataset_path = project_root / "data" / "processed" / "milestone1_clean_data.csv"

df = pd.read_csv(dataset_path)

print("Rows:", len(df))
print("Columns:", len(df.columns))
print("Unique outlets:", df["Outlet_ID"].nunique())
print("Unique months:", df["Month"].nunique())

# -----------------------------
# KPI Calculation
# -----------------------------

outlet_kpis = df.groupby(["Outlet_ID", "Outlet_Name"]).agg(
    Total_Sales=("Sales_Revenue_INR", "sum"),
    Total_Profit=("Profit_INR", "sum"),
    Avg_Profit_Margin=("Profit_Margin_%", "mean"),
    Total_Orders=("Orders", "sum"),
    Total_Footfall=("Footfall", "sum"),
    Avg_Conversion_Rate=("Conversion_Rate_%", "mean"),
    Avg_Order_Value=("Average_Order_Value_INR", "mean"),
    Avg_Customer_Satisfaction=("Customer_Satisfaction_1_5", "mean"),
    Total_Complaints=("Complaints", "sum"),
    Months_Recorded=("Month", "nunique")
).reset_index()

outlet_kpis["Avg_Monthly_Sales"] = (
    outlet_kpis["Total_Sales"] / outlet_kpis["Months_Recorded"]
)

outlet_kpis = outlet_kpis.round(2)

# -----------------------------
# STEP 3: Rankings
# -----------------------------

outlet_kpis["Sales_Rank"] = (
    outlet_kpis["Total_Sales"]
    .rank(ascending=False, method="min")
    .astype(int)
)

outlet_kpis["Profit_Rank"] = (
    outlet_kpis["Total_Profit"]
    .rank(ascending=False, method="min")
    .astype(int)
)

outlet_kpis["Margin_Rank"] = (
    outlet_kpis["Avg_Profit_Margin"]
    .rank(ascending=False, method="min")
    .astype(int)
)

outlet_kpis["Conversion_Rank"] = (
    outlet_kpis["Avg_Conversion_Rate"]
    .rank(ascending=False, method="min")
    .astype(int)
)

outlet_kpis["AOV_Rank"] = (
    outlet_kpis["Avg_Order_Value"]
    .rank(ascending=False, method="min")
    .astype(int)
)

outlet_kpis["Satisfaction_Rank"] = (
    outlet_kpis["Avg_Customer_Satisfaction"]
    .rank(ascending=False, method="min")
    .astype(int)
)

# -----------------------------
# Overall Benchmark Score
# -----------------------------

def normalize(col):
    denominator = col.max() - col.min()
    if denominator == 0:
        return pd.Series(0.0, index=col.index)
    return (col - col.min()) / denominator


outlet_kpis["norm_sales"] = normalize(outlet_kpis["Total_Sales"])
outlet_kpis["norm_profit"] = normalize(outlet_kpis["Total_Profit"])
outlet_kpis["norm_margin"] = normalize(outlet_kpis["Avg_Profit_Margin"])
outlet_kpis["norm_conversion"] = normalize(outlet_kpis["Avg_Conversion_Rate"])
outlet_kpis["norm_aov"] = normalize(outlet_kpis["Avg_Order_Value"])
outlet_kpis["norm_satisfaction"] = normalize(
    outlet_kpis["Avg_Customer_Satisfaction"]
)

outlet_kpis["Benchmark_Score"] = (
    outlet_kpis["norm_sales"] * 0.25
    + outlet_kpis["norm_profit"] * 0.25
    + outlet_kpis["norm_margin"] * 0.15
    + outlet_kpis["norm_conversion"] * 0.15
    + outlet_kpis["norm_aov"] * 0.10
    + outlet_kpis["norm_satisfaction"] * 0.10
) * 100

outlet_kpis["Benchmark_Score"] = (
    outlet_kpis["Benchmark_Score"].round(2)
)

outlet_kpis["Benchmark_Rank"] = (
    outlet_kpis["Benchmark_Score"]
    .rank(ascending=False, method="min")
    .astype(int)
)

# -----------------------------
# STEP 4: Benchmark Categories
# -----------------------------

def categorize(score, series):
    p75 = series.quantile(0.75)
    p50 = series.quantile(0.50)
    p25 = series.quantile(0.25)

    if score >= p75:
        return "Top Performer"
    elif score >= p50:
        return "Above Average"
    elif score >= p25:
        return "Average"
    else:
        return "Below Average"


outlet_kpis["Benchmark_Category"] = outlet_kpis["Benchmark_Score"].apply(
    lambda x: categorize(x, outlet_kpis["Benchmark_Score"])
)

# Remove temporary normalized columns
outlet_kpis = outlet_kpis.drop(
    columns=[
        "norm_sales",
        "norm_profit",
        "norm_margin",
        "norm_conversion",
        "norm_aov",
        "norm_satisfaction",
    ]
)

# Sort by benchmark rank
outlet_kpis = (
    outlet_kpis
    .sort_values("Benchmark_Rank")
    .reset_index(drop=True)
)

print("\nFinal benchmarking table (top 10 outlets):")
print(
    outlet_kpis.head(10)[
        [
            "Outlet_ID",
            "Outlet_Name",
            "Benchmark_Score",
            "Benchmark_Rank",
            "Benchmark_Category",
        ]
    ]
)

print("\nCategory distribution:")
print(outlet_kpis["Benchmark_Category"].value_counts())

# Save KPI output
kpi_output_path = (
    project_root / "benchmarking" / "outlet_kpis.csv"
)
outlet_kpis.to_csv(kpi_output_path, index=False)

# Save final benchmark output
final_output_path = (
    project_root / "benchmarking" / "benchmark_output.csv"
)
outlet_kpis.to_csv(final_output_path, index=False)

print(f"\nSaved KPI output to: {kpi_output_path}")
print(f"Saved benchmark output to: {final_output_path}")
