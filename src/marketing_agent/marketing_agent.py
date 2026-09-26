import pandas as pd
from pathlib import Path


# ============================================================
# FILE PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "FranchiseOps_AI_Milestone2_Inventory_Dataset.xlsx"
)

OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"
OUTPUT_PATH = OUTPUT_DIR / "marketing_agent_output.csv"


# ============================================================
# LOAD DATA
# ============================================================

def load_data():
    """Load the Milestone 2 outlet dataset."""

    return pd.read_excel(
        DATA_PATH,
        sheet_name="Raw_Outlet_Data"
    )


# ============================================================
# PREPARE MARKETING DATA
# ============================================================

def prepare_marketing_data(df):
    """Select and clean the columns required by the Marketing Agent."""

    required_columns = [
        "Outlet_ID",
        "Month",
        "Marketing_Spend_INR",
        "Sales_Revenue_INR",
        "Orders",
        "Conversion_Rate_%"
    ]

    data = df[required_columns].copy()

    numeric_columns = [
        "Marketing_Spend_INR",
        "Sales_Revenue_INR",
        "Orders",
        "Conversion_Rate_%"
    ]

    for column in numeric_columns:
        data[column] = pd.to_numeric(
            data[column],
            errors="coerce"
        )

    data["Month"] = pd.to_datetime(
        data["Month"],
        errors="coerce"
    )

    # Remove rows where essential marketing information is missing
    data = data.dropna(
        subset=[
            "Outlet_ID",
            "Month",
            "Marketing_Spend_INR",
            "Sales_Revenue_INR",
            "Orders",
            "Conversion_Rate_%"
        ]
    )

    # Marketing spend and sales cannot be negative
    data = data[
        (data["Marketing_Spend_INR"] >= 0)
        & (data["Sales_Revenue_INR"] >= 0)
        & (data["Orders"] >= 0)
    ]

    return data


# ============================================================
# CALCULATE OUTLET MARKETING PERFORMANCE
# ============================================================

def calculate_marketing_performance(data):
    """Calculate marketing KPIs for every outlet."""

    grouped = (
        data.groupby("Outlet_ID")
        .agg(
            Records=("Outlet_ID", "size"),
            Total_Marketing_Spend=(
                "Marketing_Spend_INR",
                "sum"
            ),
            Total_Sales_Revenue=(
                "Sales_Revenue_INR",
                "sum"
            ),
            Total_Orders=(
                "Orders",
                "sum"
            ),
            Average_Conversion_Rate=(
                "Conversion_Rate_%",
                "mean"
            )
        )
        .reset_index()
    )

    # Revenue generated for every ₹1 spent on marketing
    grouped["Revenue_Per_Marketing_Rupee"] = (
        grouped["Total_Sales_Revenue"]
        / grouped["Total_Marketing_Spend"].replace(0, pd.NA)
    )

    grouped["Revenue_Per_Marketing_Rupee"] = (
        grouped["Revenue_Per_Marketing_Rupee"]
        .fillna(0)
    )

    # Marketing spend as percentage of sales
    grouped["Marketing_Spend_Percentage"] = (
        grouped["Total_Marketing_Spend"]
        / grouped["Total_Sales_Revenue"].replace(0, pd.NA)
    ) * 100

    grouped["Marketing_Spend_Percentage"] = (
        grouped["Marketing_Spend_Percentage"]
        .fillna(0)
    )

    return grouped


# ============================================================
# CREATE DATA-DRIVEN PERFORMANCE CATEGORIES
# ============================================================

def add_performance_categories(performance):
    """Classify outlets using quartiles calculated from the dataset."""

    efficiency_q25 = performance[
        "Revenue_Per_Marketing_Rupee"
    ].quantile(0.25)

    efficiency_q75 = performance[
        "Revenue_Per_Marketing_Rupee"
    ].quantile(0.75)

    conversion_q25 = performance[
        "Average_Conversion_Rate"
    ].quantile(0.25)

    conversion_q75 = performance[
        "Average_Conversion_Rate"
    ].quantile(0.75)

    performance["Marketing_Category"] = "Moderate"

    # High performing outlets
    high_condition = (
        (performance["Revenue_Per_Marketing_Rupee"] >= efficiency_q75)
        & (
            performance["Average_Conversion_Rate"]
            >= conversion_q75
        )
    )

    performance.loc[
        high_condition,
        "Marketing_Category"
    ] = "High Performing"

    # Outlets needing improvement
    low_condition = (
        (performance["Revenue_Per_Marketing_Rupee"] <= efficiency_q25)
        | (
            performance["Average_Conversion_Rate"]
            <= conversion_q25
        )
    )

    performance.loc[
        low_condition,
        "Marketing_Category"
    ] = "Needs Improvement"

    # Alert level
    performance["Alert_Level"] = "Low"

    high_alert_condition = (
        (performance["Revenue_Per_Marketing_Rupee"] <= efficiency_q25)
        & (
            performance["Average_Conversion_Rate"]
            <= conversion_q25
        )
    )

    medium_alert_condition = (
        (performance["Revenue_Per_Marketing_Rupee"] <= efficiency_q25)
        | (
            performance["Average_Conversion_Rate"]
            <= conversion_q25
        )
    )

    performance.loc[
        medium_alert_condition,
        "Alert_Level"
    ] = "Medium"

    performance.loc[
        high_alert_condition,
        "Alert_Level"
    ] = "High"

    return performance


# ============================================================
# GENERATE INSIGHTS AND RECOMMENDATIONS
# ============================================================

def generate_insights(row, performance):
    """Generate rule-based insights and recommendations."""

    insights = []
    recommendations = []

    efficiency = row["Revenue_Per_Marketing_Rupee"]
    conversion = row["Average_Conversion_Rate"]
    spend_percentage = row["Marketing_Spend_Percentage"]

    efficiency_q25 = performance[
        "Revenue_Per_Marketing_Rupee"
    ].quantile(0.25)

    efficiency_q75 = performance[
        "Revenue_Per_Marketing_Rupee"
    ].quantile(0.75)

    conversion_q25 = performance[
        "Average_Conversion_Rate"
    ].quantile(0.25)

    conversion_q75 = performance[
        "Average_Conversion_Rate"
    ].quantile(0.75)

    # -------------------------
    # Marketing efficiency
    # -------------------------

    if efficiency <= efficiency_q25:

        insights.append(
            "Marketing efficiency is below the "
            "lower-performing outlet range."
        )

        recommendations.append(
            "Review marketing campaigns and redirect "
            "spending toward better-performing activities."
        )

    elif efficiency >= efficiency_q75:

        insights.append(
            "Marketing efficiency is among the "
            "stronger outlet results."
        )

        recommendations.append(
            "Continue monitoring successful campaigns "
            "and consider scaling effective activities."
        )

    else:

        insights.append(
            "Marketing efficiency is within the "
            "middle range of outlet performance."
        )

    # -------------------------
    # Conversion rate
    # -------------------------

    if conversion <= conversion_q25:

        insights.append(
            "Conversion rate is below the lower-performing "
            "outlet range."
        )

        recommendations.append(
            "Improve campaign targeting, customer engagement, "
            "offers, and conversion-focused activities."
        )

    elif conversion >= conversion_q75:

        insights.append(
            "Conversion rate is among the stronger "
            "outlet results."
        )

    else:

        insights.append(
            "Conversion rate is within the middle range "
            "of outlet performance."
        )

    # -------------------------
    # Marketing spend ratio
    # -------------------------

    if spend_percentage > 15:

        insights.append(
            "Marketing spend represents a relatively high "
            "percentage of sales revenue."
        )

        recommendations.append(
            "Review marketing costs and prioritize activities "
            "with stronger revenue generation."
        )

    else:

        insights.append(
            "Marketing spend represents a relatively lower "
            "proportion of sales revenue."
        )

    # -------------------------
    # Final recommendation
    # -------------------------

    if not recommendations:

        recommendations.append(
            "Continue monitoring marketing performance and "
            "optimize campaigns using sales and conversion trends."
        )

    return (
        " ".join(insights),
        " ".join(recommendations)
    )


# ============================================================
# BUILD FINAL MARKETING AGENT OUTPUT
# ============================================================

def build_marketing_agent_output(df):
    """Run the complete Marketing Agent pipeline."""

    data = prepare_marketing_data(df)

    if data.empty:
        return pd.DataFrame()

    performance = calculate_marketing_performance(data)

    performance = add_performance_categories(
        performance
    )

    insights_list = []
    recommendations_list = []

    for _, row in performance.iterrows():

        insights, recommendations = generate_insights(
            row,
            performance
        )

        insights_list.append(insights)
        recommendations_list.append(recommendations)

    performance["Marketing_Insights"] = insights_list

    performance["Recommendations"] = (
        recommendations_list
    )

    return performance


# ============================================================
# SAVE OUTPUT
# ============================================================

def save_output(output):
    """Save Marketing Agent results for dashboard integration."""

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    output.to_csv(
        OUTPUT_PATH,
        index=False
    )


# ============================================================
# MAIN MARKETING AGENT
# ============================================================

if __name__ == "__main__":

    print("Loading Milestone 2 franchise data...")

    df = load_data()

    print("Dataset loaded successfully!")
    print("Total records:", len(df))

    print("\nRunning Marketing Agent...")

    output = build_marketing_agent_output(df)

    if output.empty:

        print("No valid marketing data found.")

    else:

        save_output(output)

        print("\n================================")
        print("       MARKETING AGENT")
        print("================================")

        print(
            "\nTotal outlets analyzed:",
            len(output)
        )

        print(
            "Output file:",
            OUTPUT_PATH
        )

        print("\n--- MARKETING CATEGORY SUMMARY ---")

        print(
            output["Marketing_Category"]
            .value_counts()
            .to_string()
        )

        print("\n--- ALERT SUMMARY ---")

        print(
            output["Alert_Level"]
            .value_counts()
            .to_string()
        )

        print("\n--- SAMPLE OUTLET ---")

        sample = output[
            output["Outlet_ID"] == "OUT0706"
        ]

        if not sample.empty:

            row = sample.iloc[0]

            print(
                "\nOutlet ID:",
                row["Outlet_ID"]
            )

            print(
                "Total Marketing Spend:",
                round(
                    row["Total_Marketing_Spend"],
                    2
                )
            )

            print(
                "Total Sales Revenue:",
                round(
                    row["Total_Sales_Revenue"],
                    2
                )
            )

            print(
                "Total Orders:",
                round(
                    row["Total_Orders"],
                    2
                )
            )

            print(
                "Average Conversion Rate:",
                round(
                    row["Average_Conversion_Rate"],
                    2
                )
            )

            print(
                "Revenue Per Marketing Rupee:",
                round(
                    row["Revenue_Per_Marketing_Rupee"],
                    2
                )
            )

            print(
                "Marketing Spend Percentage:",
                round(
                    row["Marketing_Spend_Percentage"],
                    2
                ),
                "%"
            )

            print(
                "Marketing Category:",
                row["Marketing_Category"]
            )

            print(
                "Alert Level:",
                row["Alert_Level"]
            )

            print(
                "\nInsight:",
                row["Marketing_Insights"]
            )

            print(
                "\nRecommendation:",
                row["Recommendations"]
            )

        print(
            "\nMarketing Agent completed successfully!"
        )