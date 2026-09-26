import pandas as pd
from pathlib import Path

# --------------------------------------------------
# Performance Score - Milestone 1
# --------------------------------------------------

project_root = Path(__file__).resolve().parent.parent

input_file = (
    project_root
    / "benchmarking"
    / "benchmark_output.csv"
)

output_file = (
    project_root
    / "performance_score"
    / "performance_score_output.csv"
)

# Load corrected benchmarking output
df = pd.read_csv(input_file)

print("Benchmark records:", len(df))

# --------------------------------------------------
# Score components
# --------------------------------------------------

max_rank = df["Benchmark_Rank"].max()

df["Sales_Score"] = (
    (max_rank - df["Sales_Rank"] + 1) / max_rank * 100
)

df["Profit_Score"] = (
    (max_rank - df["Profit_Rank"] + 1) / max_rank * 100
)

df["Margin_Score"] = (
    (max_rank - df["Margin_Rank"] + 1) / max_rank * 100
)

df["Conversion_Score"] = (
    (max_rank - df["Conversion_Rank"] + 1) / max_rank * 100
)

df["AOV_Score"] = (
    (max_rank - df["AOV_Rank"] + 1) / max_rank * 100
)

df["Satisfaction_Score"] = (
    (max_rank - df["Satisfaction_Rank"] + 1) / max_rank * 100
)

# Fewer complaints = better performance
complaint_rank = df["Total_Complaints"].rank(
    ascending=True,
    method="min"
)

df["Complaint_Score"] = (
    (max_rank - complaint_rank + 1) / max_rank * 100
)

# --------------------------------------------------
# Overall Performance Score
# --------------------------------------------------

df["Performance_Score"] = (
    df["Sales_Score"] * 0.20
    + df["Profit_Score"] * 0.20
    + df["Margin_Score"] * 0.15
    + df["Conversion_Score"] * 0.15
    + df["AOV_Score"] * 0.10
    + df["Satisfaction_Score"] * 0.10
    + df["Complaint_Score"] * 0.10
)

df["Performance_Score"] = (
    df["Performance_Score"].round(2)
)

# --------------------------------------------------
# Performance Health Category
# --------------------------------------------------

def classify_performance(score):
    if score >= 80:
        return "Excellent"
    elif score >= 65:
        return "Good"
    elif score >= 50:
        return "Needs Improvement"
    else:
        return "Critical"


df["Performance_Category"] = (
    df["Performance_Score"].apply(classify_performance)
)

# --------------------------------------------------
# Performance Rank
# --------------------------------------------------

df["Performance_Rank"] = (
    df["Performance_Score"]
    .rank(method="min", ascending=False)
    .astype(int)
)

# --------------------------------------------------
# Final output
# --------------------------------------------------

output_columns = [
    "Outlet_ID",
    "Outlet_Name",
    "Benchmark_Score",
    "Benchmark_Rank",
    "Benchmark_Category",
    "Performance_Score",
    "Performance_Rank",
    "Performance_Category",
]

performance_output = (
    df[output_columns]
    .sort_values("Performance_Rank")
    .reset_index(drop=True)
)

output_file.parent.mkdir(parents=True, exist_ok=True)
performance_output.to_csv(output_file, index=False)

print("Performance Score calculation completed.")
print(f"Total outlets scored: {len(performance_output)}")
print(f"Output saved to: {output_file}")

print("\nPerformance Category Distribution:")
print(
    performance_output["Performance_Category"]
    .value_counts()
    .sort_index()
)

print("\nTop 10 Performing Outlets:")
print(
    performance_output.head(10).to_string(index=False)
)
