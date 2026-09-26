import pandas as pd
from pathlib import Path


# -----------------------------------
# LOAD DATASET
# -----------------------------------

project_root = Path(__file__).resolve().parent.parent

dataset_path = (
    project_root
    / "data"
    / "raw"
    / "FranchiseOps_AI_Milestone2_Inventory_Dataset.xlsx"
)

df = pd.read_excel(dataset_path)

print("Dataset loaded successfully!")
print("Rows:", len(df))


# -----------------------------------
# STAFF DATA ANALYSIS
# -----------------------------------

staff_data = df.groupby(
    ["Outlet_ID", "Outlet_Name"]
).agg(
    Avg_Employees=("Employees", "mean"),
    Avg_Employee_Turnover=("Employee_Turnover_%", "mean"),
    Avg_Customer_Satisfaction=("Customer_Satisfaction_1_5", "mean"),
    Total_Complaints=("Complaints", "sum")
).reset_index()

staff_data = staff_data.round(2)

print("Total outlets:", len(staff_data))


# -----------------------------------
# CALCULATE THRESHOLDS
# -----------------------------------

high_turnover_threshold = (
    staff_data["Avg_Employee_Turnover"].quantile(0.75)
)

low_satisfaction_threshold = (
    staff_data["Avg_Customer_Satisfaction"].quantile(0.25)
)

high_complaints_threshold = (
    staff_data["Total_Complaints"].quantile(0.75)
)


# -----------------------------------
# STAFF STATUS LOGIC
# -----------------------------------

def get_staff_status(row):

    high_turnover = (
        row["Avg_Employee_Turnover"] >= high_turnover_threshold
    )

    low_satisfaction = (
        row["Avg_Customer_Satisfaction"] <= low_satisfaction_threshold
    )

    high_complaints = (
        row["Total_Complaints"] >= high_complaints_threshold
    )

    if high_turnover and low_satisfaction and high_complaints:
        return "Critical"

    elif high_turnover or low_satisfaction or high_complaints:
        return "Needs Attention"

    else:
        return "Stable"


staff_data["Staff_Status"] = staff_data.apply(
    get_staff_status,
    axis=1
)


# -----------------------------------
# GENERATE INSIGHTS
# -----------------------------------

def generate_insight(row):

    if row["Staff_Status"] == "Critical":
        return (
            "High employee turnover, low customer satisfaction "
            "and high complaints indicate significant staff-related issues."
        )

    elif row["Staff_Status"] == "Needs Attention":
        return (
            "Staff performance requires attention due to concerns "
            "related to turnover, customer satisfaction or complaints."
        )

    else:
        return (
            "Staff performance appears stable with healthy "
            "customer service indicators."
        )


staff_data["Insight"] = staff_data.apply(
    generate_insight,
    axis=1
)


# -----------------------------------
# GENERATE RECOMMENDATIONS
# -----------------------------------

def generate_recommendation(row):

    if row["Staff_Status"] == "Critical":
        return (
            "Review employee retention strategies, workload distribution "
            "and provide targeted staff training."
        )

    elif row["Staff_Status"] == "Needs Attention":
        return (
            "Monitor employee turnover and improve staff training "
            "and customer service practices."
        )

    else:
        return (
            "Maintain current staff management practices and "
            "continue monitoring staff performance."
        )


staff_data["Recommendation"] = staff_data.apply(
    generate_recommendation,
    axis=1
)


# -----------------------------------
# SAVE FINAL OUTPUT
# -----------------------------------

output_path = (
    project_root
    / "staff_agent"
    / "staff_agent_output.csv"
)

staff_data.to_csv(output_path, index=False)


# -----------------------------------
# DISPLAY RESULTS
# -----------------------------------

print("\nStaff Agent completed successfully!")

print("\nStatus Distribution:")
print(staff_data["Staff_Status"].value_counts())

print("\nTop 10 Results:")
print(
    staff_data[
        [
            "Outlet_ID",
            "Outlet_Name",
            "Avg_Employees",
            "Avg_Employee_Turnover",
            "Avg_Customer_Satisfaction",
            "Total_Complaints",
            "Staff_Status"
        ]
    ].head(10)
)

print(f"\nOutput saved to: {output_path}")