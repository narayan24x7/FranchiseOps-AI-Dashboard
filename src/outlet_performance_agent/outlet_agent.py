import pandas as pd
from pathlib import Path


# =============================
# FILE PATHS
# =============================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "milestone1_clean_data.csv"
)

BENCHMARK_PATH = (
    PROJECT_ROOT
    / "benchmarking"
    / "benchmark_output.csv"
)

PERFORMANCE_PATH = (
    PROJECT_ROOT
    / "performance_score"
    / "performance_score_output.csv"
)


# =============================
# LOAD DATA
# =============================

def load_data():
    return pd.read_csv(DATA_PATH)


def load_benchmark():
    return pd.read_csv(BENCHMARK_PATH)


def load_performance_score():
    return pd.read_csv(PERFORMANCE_PATH)


# =============================
# ANALYZE OUTLET
# =============================

def analyze_outlet(df, outlet_id):

    outlet = df[df["Outlet_ID"] == outlet_id]

    if outlet.empty:
        return None

    analysis = {
        "Outlet_ID": outlet_id,
        "Records": len(outlet),
        "Total_Revenue": outlet["Sales_Revenue_INR"].sum(),
        "Total_Profit": outlet["Profit_INR"].sum(),
        "Total_Orders": outlet["Orders"].sum(),
        "Average_Conversion_Rate": outlet["Conversion_Rate_%"].mean(),
        "Average_Order_Value": outlet["Average_Order_Value_INR"].mean(),
        "Average_Profit_Margin": outlet["Profit_Margin_%"].mean(),
        "Average_Employee_Turnover": outlet["Employee_Turnover_%"].mean(),
        "Average_Customer_Satisfaction": outlet[
            "Customer_Satisfaction_1_5"
        ].mean(),
        "Total_Complaints": outlet["Complaints"].sum()
    }

    return analysis


# =============================
# GET BENCHMARK
# =============================

def get_benchmark(benchmark_df, outlet_id):

    benchmark = benchmark_df[
        benchmark_df["Outlet_ID"] == outlet_id
    ]

    if benchmark.empty:
        return None

    return benchmark.iloc[0]


# =============================
# GET PERFORMANCE SCORE
# =============================

def get_performance_score(performance_df, outlet_id):

    performance = performance_df[
        performance_df["Outlet_ID"] == outlet_id
    ]

    if performance.empty:
        return None

    return performance.iloc[0]


# =============================
# GENERATE INSIGHTS
# =============================

def generate_insights(analysis, benchmark, performance):

    insights = []
    recommendations = []

    # -------------------------
    # Overall Performance
    # -------------------------

    performance_score = performance["Performance_Score"]
    performance_rank = performance["Performance_Rank"]
    performance_category = performance["Performance_Category"]

    insights.append(
        f"Outlet {analysis['Outlet_ID']} has a performance score "
        f"of {performance_score} and is classified as "
        f"{performance_category}."
    )

    insights.append(
        f"The outlet has a performance rank of "
        f"{int(performance_rank)}."
    )

    # -------------------------
    # Benchmark
    # -------------------------

    benchmark_score = benchmark["Benchmark_Score"]
    benchmark_rank = benchmark["Benchmark_Rank"]

    insights.append(
        f"The outlet has a benchmark score of "
        f"{benchmark_score} and benchmark rank "
        f"{int(benchmark_rank)}."
    )

    # -------------------------
    # Profit Margin
    # -------------------------

    if analysis["Average_Profit_Margin"] < 15:

        insights.append(
            "Profit margin is relatively low."
        )

        recommendations.append(
            "Review operating costs and improve cost control."
        )

    else:

        insights.append(
            "Profit margin is healthy."
        )

    # -------------------------
    # Conversion Rate
    # -------------------------

    if analysis["Average_Conversion_Rate"] < 15:

        insights.append(
            "Conversion rate needs improvement."
        )

        recommendations.append(
            "Improve customer conversion through better offers, "
            "service quality, and staff engagement."
        )

    else:

        insights.append(
            "Conversion rate is performing well."
        )

    # -------------------------
    # Customer Satisfaction
    # -------------------------

    if analysis["Average_Customer_Satisfaction"] < 3.5:

        insights.append(
            "Customer satisfaction is below the desired level."
        )

        recommendations.append(
            "Investigate customer complaints and improve "
            "service quality."
        )

    else:

        insights.append(
            "Customer satisfaction is good."
        )

    # -------------------------
    # Employee Turnover
    # -------------------------

    if analysis["Average_Employee_Turnover"] > 10:

        insights.append(
            "Employee turnover is high."
        )

        recommendations.append(
            "Improve employee retention through training "
            "and better workforce management."
        )

    # -------------------------
    # Complaints
    # -------------------------

    if analysis["Total_Complaints"] > 800:

        insights.append(
            "The outlet has a high number of complaints."
        )

        recommendations.append(
            "Analyze complaint reasons and take corrective action."
        )

    return insights, recommendations


# =============================
# MAIN AGENT
# =============================

if __name__ == "__main__":

    print("Loading franchise data...")

    df = load_data()
    benchmark_df = load_benchmark()
    performance_df = load_performance_score()

    print("Dataset loaded successfully!")
    print("Total records:", len(df))

    # Outlet to analyze
    outlet_id = "OUT0706"

    # Analyze outlet
    analysis = analyze_outlet(df, outlet_id)

    # Get benchmark
    benchmark = get_benchmark(
        benchmark_df,
        outlet_id
    )

    # Get performance score
    performance = get_performance_score(
        performance_df,
        outlet_id
    )

    # -------------------------
    # Validation
    # -------------------------

    if analysis is None:

        print("Outlet not found.")

    elif benchmark is None:

        print("Benchmark information not found.")

    elif performance is None:

        print("Performance score information not found.")

    else:

        # Generate AI insights
        insights, recommendations = generate_insights(
            analysis,
            benchmark,
            performance
        )

        # -------------------------
        # OUTPUT
        # -------------------------

        print("\n================================")
        print("   OUTLET PERFORMANCE AGENT")
        print("================================")

        print("\nOutlet ID:", outlet_id)

        print("\n--- PERFORMANCE ---")

        print(
            "Total Revenue:",
            round(analysis["Total_Revenue"], 2)
        )

        print(
            "Total Profit:",
            round(analysis["Total_Profit"], 2)
        )

        print(
            "Total Orders:",
            round(analysis["Total_Orders"], 2)
        )

        print(
            "Conversion Rate:",
            round(analysis["Average_Conversion_Rate"], 2)
        )

        print(
            "Average Order Value:",
            round(analysis["Average_Order_Value"], 2)
        )

        print(
            "Profit Margin:",
            round(analysis["Average_Profit_Margin"], 2)
        )

        print(
            "Employee Turnover:",
            round(analysis["Average_Employee_Turnover"], 2)
        )

        print(
            "Customer Satisfaction:",
            round(
                analysis["Average_Customer_Satisfaction"],
                2
            )
        )

        print(
            "Total Complaints:",
            round(analysis["Total_Complaints"], 2)
        )

        # -------------------------
        # BENCHMARK
        # -------------------------

        print("\n--- BENCHMARK ---")

        print(
            "Benchmark Score:",
            benchmark["Benchmark_Score"]
        )

        print(
            "Benchmark Rank:",
            int(benchmark["Benchmark_Rank"])
        )

        print(
            "Benchmark Category:",
            benchmark["Benchmark_Category"]
        )

        # -------------------------
        # PERFORMANCE SCORE
        # -------------------------

        print("\n--- PERFORMANCE SCORE ---")

        print(
            "Performance Score:",
            performance["Performance_Score"]
        )

        print(
            "Performance Rank:",
            int(performance["Performance_Rank"])
        )

        print(
            "Performance Category:",
            performance["Performance_Category"]
        )

        # -------------------------
        # INSIGHTS
        # -------------------------

        print("\n--- AI INSIGHTS ---")

        for insight in insights:

            print("•", insight)

        # -------------------------
        # RECOMMENDATIONS
        # -------------------------

        print("\n--- RECOMMENDATIONS ---")

        for recommendation in recommendations:

            print("•", recommendation)