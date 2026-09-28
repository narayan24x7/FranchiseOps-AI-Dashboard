
"""
M4 Franchise Intelligence Engine

Flow:
    Agent Outputs
        ↓
    Normalize + Validate
        ↓
    Agent-level Intelligence
        ↓
    Merge by Outlet_ID
        ↓
    Health Score
        ↓
    Cross-agent Risks
        ↓
    Opportunities
        ↓
    Strategic Recommendations
        ↓
    Priority + Confidence
        ↓
    intelligence_output.csv

Supported agent files:

    data/processed/
        outlet_performance_intelligence.csv
        inventory_agent_output.csv
        marketing_agent_output.csv
        staff_agent_output.csv       # optional
        audit_agent_output.csv       # optional

Missing Staff/Audit outputs are handled safely.
"""

from pathlib import Path
import numpy as np
import pandas as pd


# ============================================================
# 1. PATHS
# ============================================================

# intelligence_engine.py is inside:
# FranchiseOps-AI/src/intelligence_engine.py
#
# parents[0] = src
# parents[1] = FranchiseOps-AI

PROJECT_ROOT = Path(__file__).resolve().parents[2]

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

OUTPUT_FILE = PROCESSED_DIR / "intelligence_output.csv"


# ============================================================
# 2. EXACT AGENT FILES
# ============================================================

AGENT_FILES = {
    "performance": PROCESSED_DIR / "outlet_performance_intelligence.csv",
    "inventory": PROCESSED_DIR / "inventory_agent_output.csv",
    "staff": PROCESSED_DIR / "staff_agent_output.csv",
    "marketing": PROCESSED_DIR / "marketing_agent_output.csv",
    "audit": PROCESSED_DIR / "audit_agent_output.csv",
}


# ============================================================
# 3. HEALTH WEIGHTS
# ============================================================

BASE_WEIGHTS = {
    "performance": 0.30,
    "inventory": 0.25,
    "staff": 0.15,
    "marketing": 0.15,
    "audit": 0.15,
}


EXPECTED_OUTLETS = 750


# ============================================================
# 4. GENERAL HELPERS
# ============================================================

def normalize_id(series):
    """
    Normalize Outlet IDs without converting valid IDs incorrectly.
    """
    return (
        series.astype("string")
        .str.strip()
        .replace({"": pd.NA, "nan": pd.NA, "None": pd.NA})
    )


def safe_numeric(df, columns):
    """
    Convert available columns to numeric safely.
    Invalid values become NaN.
    """
    for column in columns:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    return df


def first_existing_column(df, candidates):
    """
    Return first matching column from candidates.
    """
    for column in candidates:
        if column in df.columns:
            return column

    return None


def require_columns(df, required, agent_name):
    """
    Validate required columns.
    """
    missing = [column for column in required if column not in df.columns]

    if missing:
        raise ValueError(
            f"{agent_name} agent is missing required columns: {missing}"
        )


def normalize_outlet_id(df, agent_name):
    """
    Convert common Outlet ID column names into Outlet_ID.
    """

    id_column = first_existing_column(
        df,
        [
            "Outlet_ID",
            "outlet_id",
            "OutletID",
            "outletId",
        ],
    )

    if id_column is None:
        raise ValueError(
            f"{agent_name} agent does not contain an Outlet ID column."
        )

    if id_column != "Outlet_ID":
        df = df.rename(columns={id_column: "Outlet_ID"})

    df["Outlet_ID"] = normalize_id(df["Outlet_ID"])

    df = df[df["Outlet_ID"].notna()].copy()

    return df


# ============================================================
# 5. LOAD AGENT
# ============================================================

def load_agent(agent_name, file_path):
    """
    Load an agent CSV.

    Missing optional agents are safely ignored.
    Required/core agents must exist.
    """

    if not file_path.exists():

        if agent_name in {"staff", "audit"}:
            print(
                f"[INFO] {agent_name.capitalize()} output not found. "
                f"Continuing without it."
            )
            return None

        raise FileNotFoundError(
            f"Required {agent_name} output not found:\n{file_path}"
        )

    try:
        df = pd.read_csv(file_path)
    except Exception as exc:
        raise RuntimeError(
            f"Could not read {agent_name} file:\n{file_path}\n{exc}"
        ) from exc

    if df.empty:
        print(
            f"[WARNING] {agent_name.capitalize()} output is empty. "
            f"Continuing without it."
        )
        return None

    df = normalize_outlet_id(df, agent_name)

    return df


# ============================================================
# 6. PERFORMANCE PREPARATION
# ============================================================

def prepare_performance(df):
    """
    Prepare actual Performance agent output.

    Actual file:
        outlet_performance_intelligence.csv

    Actual important columns:
        outlet_id
        performance_score
        health_category
        alert_level
        benchmark_gap_pct
        target_achievement_pct
        revenue_growth_pct
        customer_rating
        complaint_rate
        on_time_service_pct
    """

    if df is None:
        return None

    required = [
        "Outlet_ID",
        "performance_score",
        "health_category",
        "alert_level",
    ]

    require_columns(df, required, "Performance")

    numeric_columns = [
        "performance_score",
        "benchmark_gap_pct",
        "target_achievement_pct",
        "revenue_growth_pct",
        "customer_rating",
        "complaint_rate",
        "on_time_service_pct",
        "revenue",
        "target_revenue",
        "previous_month_revenue",
        "orders",
        "avg_order_value",
    ]

    df = safe_numeric(df.copy(), numeric_columns)

    # --------------------------------------------------------
    # Handle duplicate outlet records
    # --------------------------------------------------------

    if "date" in df.columns:

        df["date"] = pd.to_datetime(
            df["date"],
            errors="coerce"
        )

        # Keep latest available performance record per outlet.
        df = (
            df.sort_values(
                ["Outlet_ID", "date"],
                ascending=[True, False]
            )
            .drop_duplicates(
                subset=["Outlet_ID"],
                keep="first"
            )
        )

    else:

        df = df.drop_duplicates(
            subset=["Outlet_ID"],
            keep="last"
        )

    # --------------------------------------------------------
    # Performance health
    # --------------------------------------------------------

    health_map = {
        "Excellent": 95,
        "Good": 80,
        "Critical": 35,
    }

    df["Performance_Health"] = (
        df["health_category"]
        .astype("string")
        .str.strip()
        .map(health_map)
    )

    # If health_category is missing/unknown,
    # use performance_score when available.
    score = df["performance_score"]

    fallback_health = np.where(
        score.notna(),
        np.clip(score, 0, 100),
        50,
    )

    df["Performance_Health"] = (
        df["Performance_Health"]
        .fillna(pd.Series(fallback_health, index=df.index))
        .clip(0, 100)
    )

    # --------------------------------------------------------
    # Performance risk
    # --------------------------------------------------------

    alert = (
        df["alert_level"]
        .astype("string")
        .str.strip()
        .str.title()
    )

    health = (
        df["health_category"]
        .astype("string")
        .str.strip()
        .str.title()
    )

    df["Performance_Risk"] = (
        alert.isin(["High", "Medium"])
        | health.eq("Critical")
    )

    df["Performance_Risk_Level"] = np.select(
        [
            health.eq("Critical") | alert.eq("High"),
            alert.eq("Medium"),
        ],
        [
            "High",
            "Medium",
        ],
        default="Low",
    )

    # --------------------------------------------------------
    # Performance opportunity
    # --------------------------------------------------------

    df["Performance_Opportunity"] = (
        (
            df["revenue_growth_pct"].fillna(0) > 0
        )
        &
        (
            df["benchmark_gap_pct"].fillna(-999) >= 0
        )
    )

    return df


# ============================================================
# 7. INVENTORY PREPARATION
# ============================================================

def prepare_inventory(df):
    """
    Prepare Inventory agent output.

    Important actual values:

        Stock_Status:
            Healthy
            Low
            Critical
            Overstocked

        Agent_Priority:
            Low
            Medium
            High
    """

    if df is None:
        return None

    required = [
        "Outlet_ID",
        "Stock_Status",
        "Agent_Priority",
        "Wastage_Units",
        "Freshness_Rate_%",
        "Recommended_Replenishment_Units",
    ]

    require_columns(df, required, "Inventory")

    numeric_columns = [
        "Closing_Stock_Units",
        "Safety_Stock_Units",
        "Reorder_Point_Units",
        "Demand_Forecast_Next_Month_Units",
        "Recommended_Replenishment_Units",
        "Stock_Availability_%",
        "Inventory_Turnover_Ratio",
        "Wastage_Units",
        "Freshness_Rate_%",
        "Shelf_Life_Days",
    ]

    df = safe_numeric(df.copy(), numeric_columns)

    # --------------------------------------------------------
    # Normalize text
    # --------------------------------------------------------

    df["Stock_Status"] = (
        df["Stock_Status"]
        .astype("string")
        .str.strip()
        .str.title()
    )

    df["Agent_Priority"] = (
        df["Agent_Priority"]
        .astype("string")
        .str.strip()
        .str.title()
    )

    # --------------------------------------------------------
    # Inventory flags
    # --------------------------------------------------------

    df["Critical_Stock_Flag"] = (
        df["Stock_Status"] == "Critical"
    )

    df["Low_Stock_Flag"] = (
        df["Stock_Status"] == "Low"
    )

    df["Overstock_Flag"] = (
        df["Stock_Status"] == "Overstocked"
    )

    df["High_Priority_Flag"] = (
        df["Agent_Priority"] == "High"
    )

    df["Wastage_Flag"] = (
        df["Wastage_Units"].fillna(0) > 0
    )

    # --------------------------------------------------------
    # Inventory health
    # --------------------------------------------------------

    stock_health_map = {
        "Healthy": 95,
        "Low": 60,
        "Critical": 30,
        "Overstocked": 70,
    }

    df["Inventory_Row_Health"] = (
        df["Stock_Status"]
        .map(stock_health_map)
        .fillna(50)
    )

    # --------------------------------------------------------
    # Aggregate product/SKU records to outlet level
    # --------------------------------------------------------

    grouped = (
        df.groupby("Outlet_ID", as_index=False)
        .agg(
            Inventory_Health=("Inventory_Row_Health", "mean"),

            Critical_Stock_Count=(
                "Critical_Stock_Flag",
                "sum"
            ),

            Low_Stock_Count=(
                "Low_Stock_Flag",
                "sum"
            ),

            Overstock_Count=(
                "Overstock_Flag",
                "sum"
            ),

            High_Priority_Count=(
                "High_Priority_Flag",
                "sum"
            ),

            Wastage_Count=(
                "Wastage_Flag",
                "sum"
            ),

            Avg_Stock_Availability=(
                "Stock_Availability_%",
                "mean"
            ),

            Avg_Freshness_Rate=(
                "Freshness_Rate_%",
                "mean"
            ),

            Total_Wastage_Units=(
                "Wastage_Units",
                "sum"
            ),

            Total_Replenishment_Units=(
                "Recommended_Replenishment_Units",
                "sum"
            ),

            Avg_Inventory_Turnover=(
                "Inventory_Turnover_Ratio",
                "mean"
            ),
        )
    )

    # --------------------------------------------------------
    # Inventory risk
    # --------------------------------------------------------

    grouped["Inventory_Risk"] = (
        (
            grouped["Critical_Stock_Count"] > 0
        )
        |
        (
            grouped["High_Priority_Count"] > 0
        )
    )

    # Wastage is a separate operational issue.
    grouped["Inventory_Wastage_Risk"] = (
        grouped["Wastage_Count"] > 0
    )

    grouped["Inventory_Overstock_Risk"] = (
        grouped["Overstock_Count"] > 0
    )

    return grouped


# ============================================================
# 8. MARKETING PREPARATION
# ============================================================

def prepare_marketing(df):
    """
    Prepare actual Marketing agent output.

    Actual columns include:

        Alert_Level
        Marketing_Category
        Average_Conversion_Rate
        Revenue_Per_Marketing_Rupee
        Marketing_Spend_Percentage
        Total_Marketing_Spend
        Total_Sales_Revenue
        Total_Orders
    """

    if df is None:
        return None

    required = [
        "Outlet_ID",
        "Alert_Level",
        "Marketing_Category",
        "Average_Conversion_Rate",
        "Revenue_Per_Marketing_Rupee",
        "Marketing_Spend_Percentage",
    ]

    require_columns(df, required, "Marketing")

    numeric_columns = [
        "Records",
        "Total_Marketing_Spend",
        "Total_Sales_Revenue",
        "Total_Orders",
        "Average_Conversion_Rate",
        "Revenue_Per_Marketing_Rupee",
        "Marketing_Spend_Percentage",
    ]

    df = safe_numeric(df.copy(), numeric_columns)

    df["Alert_Level"] = (
        df["Alert_Level"]
        .astype("string")
        .str.strip()
        .str.title()
    )

    df["Marketing_Category"] = (
        df["Marketing_Category"]
        .astype("string")
        .str.strip()
    )

    # --------------------------------------------------------
    # Alert risk
    # --------------------------------------------------------

    df["Marketing_Risk"] = (
        df["Alert_Level"].isin(["High", "Medium"])
        |
        df["Marketing_Category"].eq("Needs Improvement")
    )

    # --------------------------------------------------------
    # Marketing health
    # --------------------------------------------------------

    alert_health = {
        "Low": 90,
        "Medium": 65,
        "High": 35,
    }

    category_health = {
        "High Performing": 95,
        "Moderate": 70,
        "Needs Improvement": 40,
    }

    df["Marketing_Alert_Health"] = (
        df["Alert_Level"].map(alert_health)
    )

    df["Marketing_Category_Health"] = (
        df["Marketing_Category"].map(category_health)
    )

    df["Marketing_Health"] = (
        (
            df["Marketing_Alert_Health"]
            + df["Marketing_Category_Health"]
        )
        / 2
    ).fillna(50)

    # --------------------------------------------------------
    # Marketing opportunity
    # --------------------------------------------------------

    df["Marketing_Opportunity"] = (
        df["Marketing_Category"].eq("High Performing")
        |
        (
            df["Average_Conversion_Rate"].fillna(0) > 0
        )
        &
        (
            df["Revenue_Per_Marketing_Rupee"].fillna(0) > 1
        )
    )

    # --------------------------------------------------------
    # If multiple rows per outlet exist,
    # aggregate safely.
    # --------------------------------------------------------

    grouped = (
        df.groupby("Outlet_ID", as_index=False)
        .agg(
            Marketing_Health=("Marketing_Health", "mean"),

            Marketing_Risk=("Marketing_Risk", "max"),

            Average_Conversion_Rate=(
                "Average_Conversion_Rate",
                "mean"
            ),

            Revenue_Per_Marketing_Rupee=(
                "Revenue_Per_Marketing_Rupee",
                "mean"
            ),

            Marketing_Spend_Percentage=(
                "Marketing_Spend_Percentage",
                "mean"
            ),

            Total_Marketing_Spend=(
                "Total_Marketing_Spend",
                "sum"
            ),

            Total_Marketing_Revenue=(
                "Total_Sales_Revenue",
                "sum"
            ),

            Marketing_Opportunity=(
                "Marketing_Opportunity",
                "max"
            ),
        )
    )

    return grouped


# ============================================================
# 9. GENERIC STAFF / AUDIT PREPARATION
# ============================================================

def prepare_generic_agent(df, agent_name):
    """
    Safe fallback preparation for Staff and Audit.

    The exact Staff/Audit schemas may vary, so this function
    searches for common risk/priority columns.
    """

    if df is None:
        return None

    priority_column = first_existing_column(
        df,
        [
            "Agent_Priority",
            "Priority",
            "Alert_Level",
            "Risk_Level",
            "Risk",
            "Status",
        ],
    )

    risk_score_column = first_existing_column(
        df,
        [
            "Risk_Score",
            "Operational_Risk_Score",
            "RiskScore",
        ],
    )

      # --------------------------------------------------------
    # Staff-specific status handling
    # --------------------------------------------------------

    if agent_name.lower() == "staff" and "Staff_Status" in df.columns:

        status = (
            df["Staff_Status"]
            .astype("string")
            .str.strip()
            .str.title()
        )

        health_map = {
            "Stable": 85,
            "Needs Attention": 60,
            "Critical": 25,
        }

        result = (
            df[["Outlet_ID"]]
            .drop_duplicates()
            .copy()
        )

        result[f"{agent_name.capitalize()}_Health"] = (
            status.map(health_map)
            .fillna(50)
            .astype(float)
        )

        result[f"{agent_name.capitalize()}_Risk"] = (
            status.eq("Critical")
        )

        return result
    # --------------------------------------------------------
    # Risk score
    # --------------------------------------------------------

    if risk_score_column is not None:

        df[risk_score_column] = pd.to_numeric(
            df[risk_score_column],
            errors="coerce",
        )

        score = df[risk_score_column].clip(0, 100)

        health = 100 - score

        risk = score >= 50

    else:

        priority = (
            df[priority_column]
            .astype("string")
            .str.strip()
            .str.title()
        )

        priority_map = {
            "Low": 1,
            "Medium": 2,
            "High": 3,
            "Critical": 4,
        }

        priority_score = priority.map(priority_map)

        health = (
            100
            - (priority_score.fillna(2) / 4 * 70)
        )

        risk = priority.isin(
            ["High", "Critical"]
        )

    result = (
        pd.DataFrame(
            {
                "Outlet_ID": df["Outlet_ID"],
                f"{agent_name.capitalize()}_Health": health,
                f"{agent_name.capitalize()}_Risk": risk,
            }
        )
        .groupby("Outlet_ID", as_index=False)
        .agg(
            {
                f"{agent_name.capitalize()}_Health": "mean",
                f"{agent_name.capitalize()}_Risk": "max",
            }
        )
    )

    return result


# ============================================================
# 10. MAIN ENGINE
# ============================================================

def build_intelligence():

    print("\n" + "=" * 70)
    print("M4 FRANCHISE INTELLIGENCE ENGINE")
    print("=" * 70)

    # --------------------------------------------------------
    # Load agents
    # --------------------------------------------------------

    raw_agents = {}

    for agent_name, file_path in AGENT_FILES.items():

        raw_agents[agent_name] = load_agent(
            agent_name,
            file_path,
        )

    # --------------------------------------------------------
    # Prepare agents
    # --------------------------------------------------------

    prepared = {}

    if raw_agents["performance"] is not None:
        prepared["performance"] = prepare_performance(
            raw_agents["performance"]
        )

    if raw_agents["inventory"] is not None:
        prepared["inventory"] = prepare_inventory(
            raw_agents["inventory"]
        )

    if raw_agents["marketing"] is not None:
        prepared["marketing"] = prepare_marketing(
            raw_agents["marketing"]
        )

    if raw_agents["staff"] is not None:
        prepared["staff"] = prepare_generic_agent(
            raw_agents["staff"],
            "staff",
        )

    if raw_agents["audit"] is not None:
        prepared["audit"] = prepare_generic_agent(
            raw_agents["audit"],
            "audit",
        )

    # --------------------------------------------------------
    # Build master outlet list
    # --------------------------------------------------------

    outlet_frames = []

    for agent_df in prepared.values():

        if agent_df is not None and "Outlet_ID" in agent_df.columns:

            outlet_frames.append(
                agent_df[["Outlet_ID"]]
            )

    if not outlet_frames:
        raise RuntimeError(
            "No usable agent output files were found."
        )

    outlets = (
        pd.concat(outlet_frames, ignore_index=True)
        .drop_duplicates("Outlet_ID")
        .reset_index(drop=True)
    )

    # --------------------------------------------------------
    # Merge all agent outputs
    # --------------------------------------------------------

    for agent_name, agent_df in prepared.items():

        if agent_df is None:
            continue

        outlets = outlets.merge(
            agent_df,
            on="Outlet_ID",
            how="left",
            validate="one_to_one",
        )

    # --------------------------------------------------------
    # Agent presence / outlet-level coverage
    # --------------------------------------------------------

    presence_columns = []

    for agent_name in BASE_WEIGHTS:

        health_column = (
            f"{agent_name.capitalize()}_Health"
        )

        if health_column in outlets.columns:

            presence_column = (
                f"{agent_name.capitalize()}_Present"
            )

            outlets[presence_column] = (
                outlets[health_column].notna()
            )

            presence_columns.append(
                presence_column
            )

    if presence_columns:

        outlets["Agents_Available"] = (
            outlets[presence_columns]
            .sum(axis=1)
            .astype(int)
        )

    else:

        outlets["Agents_Available"] = 0

    outlets["Agent_Coverage_%"] = (
        outlets["Agents_Available"]
        / len(BASE_WEIGHTS)
        * 100
    )
        # --------------------------------------------------------
    # Safely convert pandas NA/boolean values
    # --------------------------------------------------------

    def is_true(value):
        if pd.isna(value):
            return False
        return bool(value)

    # --------------------------------------------------------
    # Health score
    # --------------------------------------------------------

    health_components = []
    health_weights = []

    for agent_name, weight in BASE_WEIGHTS.items():

        health_column = (
            f"{agent_name.capitalize()}_Health"
        )

        if health_column not in outlets.columns:
            continue

        present = outlets[health_column].notna()

        if not present.any():
            continue

        health_value = pd.to_numeric(
            outlets[health_column],
            errors="coerce"
        )

        health_value = health_value.clip(0, 100)

        health_components.append(
            health_value.fillna(0) * weight
        )

        health_weights.append(
            present.astype(float) * weight
        )

    if not health_components:

        outlets["Health_Score"] = 50.0

    else:

        weighted_sum = sum(health_components)
        weighted_weights = sum(health_weights)

        outlets["Health_Score"] = np.where(
            weighted_weights > 0,
            weighted_sum / weighted_weights,
            50.0,
        )

    outlets["Health_Score"] = (
        pd.to_numeric(
            outlets["Health_Score"],
            errors="coerce"
        )
        .fillna(50.0)
        .clip(0, 100)
        .round(2)
    )

    # ========================================================
    # RISK-BASED HEALTH ADJUSTMENT
    # ========================================================

    def calculate_risk_penalty(row):

        penalty = 0.0

        if is_true(row.get("Performance_Risk", False)):
            penalty += 8

        if is_true(row.get("Inventory_Risk", False)):
            penalty += 10

        if is_true(row.get("Inventory_Wastage_Risk", False)):
            penalty += 5

        if is_true(row.get("Inventory_Overstock_Risk", False)):
            penalty += 3

        if is_true(row.get("Marketing_Risk", False)):
            penalty += 7

        if is_true(row.get("Staff_Risk", False)):
            penalty += 7

        if is_true(row.get("Audit_Risk", False)):
            penalty += 10

        return penalty

    outlets["Health_Risk_Penalty"] = outlets.apply(
        calculate_risk_penalty,
        axis=1,
    )

    outlets["Health_Score"] = (
        outlets["Health_Score"]
        - outlets["Health_Risk_Penalty"]
    ).clip(0, 100).round(2)

    # ========================================================
    # MULTI-RISK CONTROL
    # ========================================================

    major_risk_columns = [
        "Performance_Risk",
        "Inventory_Risk",
        "Marketing_Risk",
        "Staff_Risk",
        "Audit_Risk",
    ]

    existing_major_risk_columns = [
        column
        for column in major_risk_columns
        if column in outlets.columns
    ]

    if existing_major_risk_columns:

        for column in existing_major_risk_columns:

            outlets[column] = (
                outlets[column]
                .fillna(False)
                .astype(bool)
            )

        major_risk_count = (
            outlets[existing_major_risk_columns]
            .sum(axis=1)
        )

        # 3 or more major risks
        outlets.loc[
            major_risk_count >= 3,
            "Health_Score"
        ] = np.minimum(
            outlets.loc[
                major_risk_count >= 3,
                "Health_Score"
            ],
            59.0
        )

        # 2 major risks
        outlets.loc[
            major_risk_count == 2,
            "Health_Score"
        ] = np.minimum(
            outlets.loc[
                major_risk_count == 2,
                "Health_Score"
            ],
            69.0
        )

        # 1 major risk
        outlets.loc[
            major_risk_count == 1,
            "Health_Score"
        ] = np.minimum(
            outlets.loc[
                major_risk_count == 1,
                "Health_Score"
            ],
            84.0
        )

    outlets["Health_Score"] = (
        outlets["Health_Score"]
        .clip(0, 100)
        .round(2)
    )

    # --------------------------------------------------------
    # Health category
    # --------------------------------------------------------

    outlets["Health_Category"] = np.select(
        [
            outlets["Health_Score"] >= 80,
            outlets["Health_Score"] >= 65,
            outlets["Health_Score"] >= 50,
        ],
        [
            "Healthy",
            "Stable",
            "Needs Attention",
        ],
        default="Critical",
    )

    # ========================================================
    # 11. CROSS-AGENT RISKS
    # ========================================================

    risk_columns = []

    for agent_name in BASE_WEIGHTS:

        column = f"{agent_name.capitalize()}_Risk"

        if column in outlets.columns:

            outlets[column] = (
                outlets[column]
                .fillna(False)
                .astype(bool)
            )

            risk_columns.append(column)

    if risk_columns:

        outlets["Risk_Count"] = (
            outlets[risk_columns]
            .sum(axis=1)
            .astype(int)
        )

    else:

        outlets["Risk_Count"] = 0

    # --------------------------------------------------------
    # Additional inventory risks
    # --------------------------------------------------------

    additional_risks = []

    if "Inventory_Wastage_Risk" in outlets.columns:

        outlets["Inventory_Wastage_Risk"] = (
            outlets["Inventory_Wastage_Risk"]
            .fillna(False)
            .astype(bool)
        )

        additional_risks.append(
            outlets["Inventory_Wastage_Risk"]
        )

    if "Inventory_Overstock_Risk" in outlets.columns:

        outlets["Inventory_Overstock_Risk"] = (
            outlets["Inventory_Overstock_Risk"]
            .fillna(False)
            .astype(bool)
        )

        additional_risks.append(
            outlets["Inventory_Overstock_Risk"]
        )

    if additional_risks:

        outlets["Operational_Issue_Count"] = (
            outlets["Risk_Count"]
            + sum(
                item.astype(int)
                for item in additional_risks
            )
        )

    else:

        outlets["Operational_Issue_Count"] = (
            outlets["Risk_Count"]
        )
      
    # --------------------------------------------------------
    # Additional inventory risks
    # --------------------------------------------------------

    additional_risks = []

    if "Inventory_Wastage_Risk" in outlets.columns:

        outlets["Inventory_Wastage_Risk"] = (
            outlets["Inventory_Wastage_Risk"]
            .fillna(False)
            .astype(bool)
        )

        additional_risks.append(
            outlets["Inventory_Wastage_Risk"]
        )

    if "Inventory_Overstock_Risk" in outlets.columns:

        outlets["Inventory_Overstock_Risk"] = (
            outlets["Inventory_Overstock_Risk"]
            .fillna(False)
            .astype(bool)
        )

        additional_risks.append(
            outlets["Inventory_Overstock_Risk"]
        )

    if additional_risks:

        outlets["Operational_Issue_Count"] = (
            outlets["Risk_Count"]
            + sum(
                item.astype(int)
                for item in additional_risks
            )
        )

    else:

        outlets["Operational_Issue_Count"] = (
            outlets["Risk_Count"]
        )

 

    # --------------------------------------------------------
    # Risk descriptions
    # --------------------------------------------------------

    def build_risk_text(row):

        risks = []

        if is_true(row.get("Performance_Risk", False)):
            risks.append("Performance")

        if is_true(row.get("Inventory_Risk", False)):
            risks.append("Inventory")

        if is_true(row.get("Inventory_Wastage_Risk", False)):
            risks.append("Inventory Wastage")

        if is_true(row.get("Inventory_Overstock_Risk", False)):
            risks.append("Inventory Overstock")

        if is_true(row.get("Marketing_Risk", False)):
            risks.append("Marketing")

        if is_true(row.get("Staff_Risk", False)):
            risks.append("Staff")

        if is_true(row.get("Audit_Risk", False)):
            risks.append("Audit")

        return ", ".join(risks) if risks else "No Major Risk"

    outlets["Risk_Areas"] = outlets.apply(
        build_risk_text,
        axis=1,
    )
    # ========================================================
    # 12. OPPORTUNITIES
    # ========================================================

    opportunity_columns = []

    # --------------------------------------------------------
    # Performance opportunity
    # --------------------------------------------------------

    if "Performance_Opportunity" in outlets.columns:

        performance_opportunity = (
            outlets["Performance_Opportunity"]
            .fillna(False)
        )

        opportunity_columns.append(
            pd.Series(
                np.where(
                    performance_opportunity,
                    "Performance Growth",
                    "",
                ),
                index=outlets.index,
            )
        )

    # --------------------------------------------------------
    # Marketing opportunity
    # --------------------------------------------------------

    if "Marketing_Opportunity" in outlets.columns:

        marketing_opportunity = (
            outlets["Marketing_Opportunity"]
            .fillna(False)
        )

        opportunity_columns.append(
            pd.Series(
                np.where(
                    marketing_opportunity,
                    "Marketing Growth",
                    "",
                ),
                index=outlets.index,
            )
        )

    # --------------------------------------------------------
    # Inventory opportunity
    # --------------------------------------------------------

    if "Inventory_Health" in outlets.columns:

        inventory_opportunity = (
            outlets["Inventory_Health"].fillna(0) >= 85
        )

        opportunity_columns.append(
            pd.Series(
                np.where(
                    inventory_opportunity,
                    "Healthy Inventory",
                    "",
                ),
                index=outlets.index,
            )
        )

    # --------------------------------------------------------
    # Combine opportunities
    # --------------------------------------------------------

    if opportunity_columns:

        opportunity_df = pd.concat(
            opportunity_columns,
            axis=1,
        )

        outlets["Opportunities"] = (
            opportunity_df
            .replace("", np.nan)
            .apply(
                lambda row: ", ".join(
                    row.dropna().astype(str)
                ),
                axis=1,
            )
            .replace("", "None Identified")
        )

    else:

        outlets["Opportunities"] = "None Identified"

    # ========================================================
    # 13. PRIORITY
    # ========================================================

    outlets["Priority"] = np.select(
        [
            (
                outlets["Operational_Issue_Count"] >= 3
            )
            |
            (
                outlets["Health_Score"] < 40
            ),

            (
                outlets["Operational_Issue_Count"] >= 2
            )
            |
            (
                outlets["Health_Score"] < 55
            ),

            (
                outlets["Operational_Issue_Count"] >= 1
            )
            |
            (
                outlets["Health_Score"] < 70
            ),
        ],
        [
            "Critical",
            "High",
            "Medium",
        ],
        default="Low",
    )

   
    # ========================================================
    # 14. STRATEGIC RECOMMENDATIONS
    # ========================================================

    def recommendation(row):

        priority = row.get("Priority", "Low")
        risk_areas = row.get("Risk_Areas", "No Major Risk")

        if pd.isna(priority):
            priority = "Low"

        if pd.isna(risk_areas):
            risk_areas = "No Major Risk"

        priority = str(priority)
        risk_areas = str(risk_areas)

        recommendations = []

        # ----------------------------------------------------
        # Performance
        # ----------------------------------------------------

        performance_risk = row.get(
            "Performance_Risk",
            False
        )

        if pd.isna(performance_risk):
            performance_risk = False

        if bool(performance_risk):
            recommendations.append(
                "Review outlet performance and revenue drivers"
            )

        # ----------------------------------------------------
        # Inventory
        # ----------------------------------------------------

        inventory_risk = row.get(
            "Inventory_Risk",
            False
        )

        if pd.isna(inventory_risk):
            inventory_risk = False

        if bool(inventory_risk):
            recommendations.append(
                "Review inventory levels and replenishment"
            )

        # ----------------------------------------------------
        # Inventory wastage
        # ----------------------------------------------------

        wastage_risk = row.get(
            "Inventory_Wastage_Risk",
            False
        )

        if pd.isna(wastage_risk):
            wastage_risk = False

        if bool(wastage_risk):
            recommendations.append(
                "Reduce inventory wastage and improve stock rotation"
            )

        # ----------------------------------------------------
        # Inventory overstock
        # ----------------------------------------------------

        overstock_risk = row.get(
            "Inventory_Overstock_Risk",
            False
        )

        if pd.isna(overstock_risk):
            overstock_risk = False

        if bool(overstock_risk):
            recommendations.append(
                "Reduce excess inventory and avoid unnecessary replenishment"
            )

        # ----------------------------------------------------
        # Marketing
        # ----------------------------------------------------

        marketing_risk = row.get(
            "Marketing_Risk",
            False
        )

        if pd.isna(marketing_risk):
            marketing_risk = False

        if bool(marketing_risk):
            recommendations.append(
                "Review marketing effectiveness and conversion performance"
            )

        # ----------------------------------------------------
        # Staff
        # ----------------------------------------------------

        staff_risk = row.get(
            "Staff_Risk",
            False
        )

        if pd.isna(staff_risk):
            staff_risk = False

        if bool(staff_risk):
            recommendations.append(
                "Review staffing levels and operational efficiency"
            )

        # ----------------------------------------------------
        # Audit
        # ----------------------------------------------------

        audit_risk = row.get(
            "Audit_Risk",
            False
        )

        if pd.isna(audit_risk):
            audit_risk = False

        if bool(audit_risk):
            recommendations.append(
                "Review audit findings and compliance issues"
            )

        # ----------------------------------------------------
        # No specific risk
        # ----------------------------------------------------

        if not recommendations:
            recommendations.append(
                "Maintain current performance and monitor key metrics"
            )

        # ----------------------------------------------------
        # Priority-specific action
        # ----------------------------------------------------

        if priority == "Critical":

            recommendations.insert(
                0,
                "Immediate management intervention required"
            )

        elif priority == "High":

            recommendations.insert(
                0,
                "Prioritize corrective action"
            )

        return " | ".join(recommendations)

    # --------------------------------------------------------
    # Generate Strategic Recommendation column
    # --------------------------------------------------------

    outlets["Strategic_Recommendation"] = outlets.apply(
        recommendation,
        axis=1,
    )

    # --------------------------------------------------------
    # Final safety check
    # --------------------------------------------------------

    outlets["Strategic_Recommendation"] = (
        outlets["Strategic_Recommendation"]
        .fillna(
            "Maintain current performance and monitor key metrics"
        )
        .astype(str)
    )
   
    # ========================================================
    # 15. INTELLIGENCE SUMMARY
    # ========================================================

    def intelligence_summary(row):

        health = row.get("Health_Category", "Unknown")
        risk = row.get("Risk_Areas", "No Major Risk")
        recommendation = row.get(
            "Strategic_Recommendation",
            "Maintain current performance and monitor key metrics"
        )

        if pd.isna(health):
            health = "Unknown"

        if pd.isna(risk):
            risk = "No Major Risk"

        if pd.isna(recommendation):
            recommendation = (
                "Maintain current performance and monitor key metrics"
            )

        return (
            f"Health: {health} | "
            f"Risk Areas: {risk} | "
            f"Recommendation: {recommendation}"
        )

    outlets["Intelligence_Summary"] = outlets.apply(
        intelligence_summary,
        axis=1,
    )

    # ========================================================
    # 16. DATA CONFIDENCE
    # ========================================================

    outlets["Data_Confidence"] = np.select(
        [
            outlets["Agent_Coverage_%"] >= 80,
            outlets["Agent_Coverage_%"] >= 60,
            outlets["Agent_Coverage_%"] >= 40,
        ],
        [
            "High",
            "Medium",
            "Low",
        ],
        default="Very Low",
    )

    # ========================================================
    # 17. FINAL OUTPUT
    # ========================================================

    output_columns = [
        "Outlet_ID",
        "Health_Score",
        "Health_Category",
        "Priority",
        "Agents_Available",
        "Agent_Coverage_%",
        "Data_Confidence",
        "Risk_Count",
        "Operational_Issue_Count",
        "Risk_Areas",
        "Opportunities",
        "Strategic_Recommendation",
        "Intelligence_Summary",
    ]

    # Optional useful Performance metrics

    optional_columns = [
        "performance_score",
        "health_category",
        "alert_level",
        "benchmark_gap_pct",
        "target_achievement_pct",
        "revenue_growth_pct",
        "customer_rating",
        "complaint_rate",
        "on_time_service_pct",
    ]

    # Optional Inventory metrics

    optional_columns += [
        "Inventory_Health",
        "Critical_Stock_Count",
        "Low_Stock_Count",
        "Overstock_Count",
        "Wastage_Count",
        "Avg_Stock_Availability",
        "Avg_Freshness_Rate",
        "Total_Wastage_Units",
        "Total_Replenishment_Units",
        "Avg_Inventory_Turnover",
    ]

    # Optional Marketing metrics

    optional_columns += [
        "Marketing_Health",
        "Average_Conversion_Rate",
        "Revenue_Per_Marketing_Rupee",
        "Marketing_Spend_Percentage",
        "Total_Marketing_Spend",
        "Total_Marketing_Revenue",
    ]

    final_columns = output_columns + [
        column
        for column in optional_columns
        if column in outlets.columns
    ]

    output = outlets[final_columns].copy()

    # ========================================================
    # 18. CORRECT PRIORITY SORTING
    # ========================================================

    priority_type = pd.CategoricalDtype(
        categories=[
            "Critical",
            "High",
            "Medium",
            "Low",
        ],
        ordered=True,
    )

    output["Priority"] = (
        output["Priority"]
        .astype(priority_type)
    )

    output = (
        output.sort_values(
            ["Priority", "Health_Score"],
            ascending=[True, True],
        )
        .reset_index(drop=True)
    )

    # ========================================================
    # 19. FINAL VALIDATION
    # ========================================================

    # No duplicate outlets.

    if output["Outlet_ID"].duplicated().any():

        duplicates = (
            output.loc[
                output["Outlet_ID"].duplicated(),
                "Outlet_ID",
            ]
            .tolist()
        )

        raise ValueError(
            f"Duplicate Outlet_ID values found: {duplicates[:10]}"
        )

    # No missing IDs.

    if output["Outlet_ID"].isna().any():

        raise ValueError(
            "Final output contains missing Outlet_ID values."
        )

    # Health score range.

    if (
        output["Health_Score"].min() < 0
        or output["Health_Score"].max() > 100
    ):

        raise ValueError(
            "Health_Score contains values outside 0-100."
        )

    # Expected outlet count.

    actual_outlets = len(output)

    if actual_outlets != EXPECTED_OUTLETS:

        print(
            f"[WARNING] Expected approximately "
            f"{EXPECTED_OUTLETS} outlets, but generated "
            f"{actual_outlets}."
        )

    # Required columns.

    required_output_columns = [
        "Outlet_ID",
        "Health_Score",
        "Health_Category",
        "Priority",
        "Risk_Areas",
        "Opportunities",
        "Strategic_Recommendation",
    ]

    missing_output_columns = [
        column
        for column in required_output_columns
        if column not in output.columns
    ]

    if missing_output_columns:

        raise ValueError(
            f"Missing final output columns: "
            f"{missing_output_columns}"
        )

    # ========================================================
    # 20. SAVE
    # ========================================================

    PROCESSED_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    # ========================================================
    # 21. SUMMARY
    # ========================================================

    print("\n" + "=" * 70)
    print("M4 INTELLIGENCE ENGINE COMPLETED")
    print("=" * 70)

    print(f"Output file : {OUTPUT_FILE}")
    print(f"Outlets     : {len(output)}")

    print("\nPriority distribution:")
    print(
        output["Priority"]
        .value_counts()
        .reindex(
            [
                "Critical",
                "High",
                "Medium",
                "Low",
            ],
            fill_value=0,
        )
    )

    print("\nHealth distribution:")
    print(
        output["Health_Category"]
        .value_counts()
    )

    print("\nData confidence:")
    print(
        output["Data_Confidence"]
        .value_counts()
    )

    print("\nRisk areas:")
    print(
        output["Risk_Areas"]
        .value_counts()
        .head(10)
    )

    print("\nAgent coverage:")
    print(
        output["Agent_Coverage_%"]
        .describe()
    )

    print("\nSaved successfully.")


# ============================================================
# 22. ENTRY POINT
# ============================================================

if __name__ == "__main__":
    build_intelligence()

