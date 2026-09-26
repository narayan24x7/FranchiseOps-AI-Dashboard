import pandas as pd

from src.marketing_agent.marketing_agent import (
    prepare_marketing_data,
    calculate_marketing_performance,
    add_performance_categories,
    generate_insights,
    build_marketing_agent_output,
)


def test_prepare_marketing_data():

    df = pd.DataFrame({
        "Outlet_ID": ["OUT001", "OUT002"],
        "Month": ["2026-01", "2026-02"],
        "Marketing_Spend_INR": [10000, 20000],
        "Sales_Revenue_INR": [100000, 150000],
        "Orders": [100, 150],
        "Conversion_Rate_%": [10, 20],
    })

    result = prepare_marketing_data(df)

    assert len(result) == 2
    assert "Marketing_Spend_INR" in result.columns
    assert "Sales_Revenue_INR" in result.columns


def test_calculate_marketing_performance():

    df = pd.DataFrame({
        "Outlet_ID": ["OUT001", "OUT001"],
        "Month": pd.to_datetime(["2026-01", "2026-02"]),
        "Marketing_Spend_INR": [10000, 20000],
        "Sales_Revenue_INR": [100000, 200000],
        "Orders": [100, 200],
        "Conversion_Rate_%": [10, 20],
    })

    result = calculate_marketing_performance(df)

    assert len(result) == 1
    assert result.iloc[0]["Total_Marketing_Spend"] == 30000
    assert result.iloc[0]["Total_Sales_Revenue"] == 300000


def test_add_performance_categories():

    df = pd.DataFrame({
        "Outlet_ID": ["OUT001", "OUT002", "OUT003", "OUT004"],
        "Total_Marketing_Spend": [10000, 20000, 30000, 40000],
        "Total_Sales_Revenue": [50000, 100000, 300000, 500000],
        "Total_Orders": [100, 200, 300, 400],
        "Average_Conversion_Rate": [10, 15, 25, 30],
        "Revenue_Per_Marketing_Rupee": [5, 5, 10, 12.5],
        "Marketing_Spend_Percentage": [20, 20, 10, 8],
    })

    result = add_performance_categories(df)

    assert "Marketing_Category" in result.columns
    assert "Alert_Level" in result.columns

    assert set(result["Marketing_Category"]).issubset({
        "High Performing",
        "Moderate",
        "Needs Improvement",
    })

    assert set(result["Alert_Level"]).issubset({
        "High",
        "Medium",
        "Low",
    })


def test_generate_insights():

    performance = pd.DataFrame({
        "Revenue_Per_Marketing_Rupee": [5, 10, 15],
        "Average_Conversion_Rate": [10, 20, 30],
    })

    row = pd.Series({
        "Revenue_Per_Marketing_Rupee": 5,
        "Average_Conversion_Rate": 10,
        "Marketing_Spend_Percentage": 20,
    })

    insights, recommendations = generate_insights(
        row,
        performance
    )

    assert len(insights) > 0
    assert len(recommendations) > 0


def test_build_marketing_agent_output():

    df = pd.DataFrame({
        "Outlet_ID": [
            "OUT001",
            "OUT001",
            "OUT002",
            "OUT002",
        ],
        "Month": [
            "2026-01",
            "2026-02",
            "2026-01",
            "2026-02",
        ],
        "Marketing_Spend_INR": [
            10000,
            12000,
            20000,
            22000,
        ],
        "Sales_Revenue_INR": [
            100000,
            120000,
            150000,
            160000,
        ],
        "Orders": [
            100,
            120,
            150,
            160,
        ],
        "Conversion_Rate_%": [
            10,
            12,
            20,
            22,
        ],
    })

    result = build_marketing_agent_output(df)

    assert len(result) == 2
    assert "Marketing_Category" in result.columns
    assert "Alert_Level" in result.columns
    assert "Marketing_Insights" in result.columns
    assert "Recommendations" in result.columns