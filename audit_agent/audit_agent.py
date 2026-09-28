"""
FranchiseOps AI - Milestone 4
Audit & Compliance Agent

Purpose:
- Monitor operational and franchise-standard compliance.
- Detect data-quality and operational issues.
- Calculate an explainable audit score and status.
- Assign severity and priority.
- Generate findings and corrective actions.
- Produce audit_agent_output.csv.

The rules below are PROJECT AUDIT STANDARDS based on the fields
available in the FranchiseOps AI dataset. They are not claimed to
represent an external company's official policies.
"""

from pathlib import Path
import pandas as pd
import numpy as np


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "FranchiseOps_AI_Milestone2_Inventory_Dataset.xlsx"
)

OUTPUT_DIR = PROJECT_ROOT / "audit_agent"
OUTPUT_FILE = OUTPUT_DIR / "audit_agent_output.csv"


# ============================================================
# PROJECT AUDIT STANDARDS
# ============================================================

RULES = {
    "employee_turnover": {
        "threshold": 10.0,
        "weight": 15,
        "description": "Employee turnover should remain below 10%."
    },
    "customer_satisfaction": {
        "threshold": 3.0,
        "weight": 15,
        "description": "Customer satisfaction should be at least 3.0/5."
    },
    "complaints": {
        "threshold": 50.0,
        "weight": 15,
        "description": "Monthly complaints should remain below 50."
    },
    "conversion_rate": {
        "threshold": 15.0,
        "weight": 10,
        "description": "Average conversion rate should be at least 15%."
    },
    "profit_margin": {
        "threshold": 10.0,
        "weight": 10,
        "description": "Average profit margin should be at least 10%."
    },
    "stock_availability": {
        "threshold": 90.0,
        "weight": 10,
        "description": "Stock availability should be at least 90%."
    },
    "freshness_rate": {
        "threshold": 90.0,
        "weight": 10,
        "description": "Freshness rate should be at least 90%."
    },
    "wastage": {
        "threshold": 20.0,
        "weight": 5,
        "description": "Monthly inventory wastage should remain below 20 units."
    },
    "replenishment": {
        "weight": 5,
        "description": "Required replenishment should be acted upon."
    },
    "data_quality": {
        "weight": 5,
        "description": "Required audit fields should contain valid data."
    }
}


REQUIRED_COLUMNS = [
    "Outlet_ID",
    "Outlet_Name",
    "Month",
    "Employees",
    "Employee_Turnover_%",
    "Customer_Satisfaction_1_5",
    "Complaints",
    "Conversion_Rate_%",
    "Profit_Margin_%",
    "Stock_Availability_%",
    "Freshness_Rate_%",
    "Wastage_Units",
    "Replenishment_Required",
]


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def safe_numeric(series):
    """Convert a series to numeric values safely."""
    return pd.to_numeric(series, errors="coerce")


def clean_boolean(value):
    """Convert common boolean representations to True/False."""
    if pd.isna(value):
        return False

    if isinstance(value, bool):
        return value

    text = str(value).strip().lower()

    return text in {
        "true",
        "1",
        "yes",
        "y",
        "required",
        "replenishment required",
    }


def severity_from_count(issue_count):
    """Assign severity based on number of audit issues."""
    if issue_count >= 4:
        return "Critical"

    if issue_count >= 2:
        return "High"

    if issue_count == 1:
        return "Medium"

    return "Low"


def priority_from_severity(severity):
    """Assign action priority from severity."""
    mapping = {
        "Critical": "P1",
        "High": "P2",
        "Medium": "P3",
        "Low": "P4",
    }

    return mapping.get(severity, "P4")


def status_from_score(score):
    """Convert audit score into an audit status."""
    if score >= 90:
        return "Compliant"

    if score >= 75:
        return "Needs Attention"

    return "Non-Compliant"


def add_issue(
    findings,
    actions,
    rule_name,
    finding,
    action,
):
    """Add an audit finding and corresponding corrective action."""
    findings.append(f"{rule_name}: {finding}")
    actions.append(action)


# ============================================================
# DATA LOADING
# ============================================================

def load_dataset():
    """Load the project dataset with validation."""
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Dataset not found: {INPUT_FILE}"
        )

    df = pd.read_excel(INPUT_FILE)

    if df.empty:
        raise ValueError("The input dataset is empty.")

    missing_columns = [
        column
        for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            "Required columns are missing: "
            + ", ".join(missing_columns)
        )

    return df


# ============================================================
# DATA PREPARATION
# ============================================================

def prepare_data(df):
    """
    Clean data and create one outlet-month operational view.

    The source dataset contains multiple product/SKU rows for an
    outlet-month. Complaint values can therefore repeat across rows.
    For complaints we use the first valid outlet-month value instead
    of summing duplicate values.
    """

    data = df.copy()

    # Convert date/month field
    data["Month"] = pd.to_datetime(
        data["Month"],
        errors="coerce"
    )

    # Numeric fields
    numeric_columns = [
        "Employees",
        "Employee_Turnover_%",
        "Customer_Satisfaction_1_5",
        "Complaints",
        "Conversion_Rate_%",
        "Profit_Margin_%",
        "Stock_Availability_%",
        "Freshness_Rate_%",
        "Wastage_Units",
    ]

    for column in numeric_columns:
        data[column] = safe_numeric(data[column])

    # Remove rows without an outlet ID or month
    data = data.dropna(
        subset=["Outlet_ID", "Month"]
    )

    if data.empty:
        raise ValueError(
            "No valid Outlet_ID and Month records remain after cleaning."
        )

    # Sort chronologically
    data = data.sort_values(
        ["Outlet_ID", "Month"]
    )

    # Aggregate to outlet-month level
    grouped_rows = []

    for (outlet_id, month), group in data.groupby(
        ["Outlet_ID", "Month"],
        dropna=False
    ):
        complaint_values = group["Complaints"].dropna()

        if len(complaint_values) > 0:
            complaint_value = float(
                complaint_values.iloc[0]
            )
        else:
            complaint_value = np.nan

        replenishment_required = any(
            clean_boolean(value)
            for value in group["Replenishment_Required"]
        )

        grouped_rows.append(
            {
                "Outlet_ID": outlet_id,
                "Outlet_Name": (
                    group["Outlet_Name"]
                    .dropna()
                    .astype(str)
                    .iloc[0]
                    if group["Outlet_Name"].notna().any()
                    else "Unknown Outlet"
                ),
                "Month": month,
                "Employees": group["Employees"].mean(),
                "Employee_Turnover_%": group[
                    "Employee_Turnover_%"
                ].mean(),
                "Customer_Satisfaction_1_5": group[
                    "Customer_Satisfaction_1_5"
                ].mean(),
                "Complaints": complaint_value,
                "Conversion_Rate_%": group[
                    "Conversion_Rate_%"
                ].mean(),
                "Profit_Margin_%": group[
                    "Profit_Margin_%"
                ].mean(),
                "Stock_Availability_%": group[
                    "Stock_Availability_%"
                ].mean(),
                "Freshness_Rate_%": group[
                    "Freshness_Rate_%"
                ].mean(),
                "Wastage_Units": group[
                    "Wastage_Units"
                ].sum(min_count=1),
                "Replenishment_Required": replenishment_required,
            }
        )

    result = pd.DataFrame(grouped_rows)

    return result


# ============================================================
# AUDIT ENGINE
# ============================================================

def audit_outlet(row):
    """
    Audit one outlet-month record.

    Returns an explainable audit result containing:
    - score
    - status
    - findings
    - severity
    - priority
    - corrective actions
    """

    findings = []
    actions = []
    failed_rules = []

    score = 100.0

    # --------------------------------------------------------
    # 1. Employee turnover
    # --------------------------------------------------------

    turnover = row["Employee_Turnover_%"]

    if pd.isna(turnover):
        score -= RULES["employee_turnover"]["weight"]
        failed_rules.append("employee_turnover")

        add_issue(
            findings,
            actions,
            "Employee Turnover",
            "Employee turnover data is missing or invalid.",
            "Review workforce records and update the turnover value."
        )

    elif turnover >= RULES["employee_turnover"]["threshold"]:
        score -= RULES["employee_turnover"]["weight"]
        failed_rules.append("employee_turnover")

        add_issue(
            findings,
            actions,
            "Employee Turnover",
            f"Turnover is {turnover:.2f}%, above the "
            f"{RULES['employee_turnover']['threshold']:.0f}% project standard.",
            "Review staffing conditions, retention issues and workforce planning."
        )

    # --------------------------------------------------------
    # 2. Customer satisfaction
    # --------------------------------------------------------

    satisfaction = row["Customer_Satisfaction_1_5"]

    if pd.isna(satisfaction):
        score -= RULES["customer_satisfaction"]["weight"]
        failed_rules.append("customer_satisfaction")

        add_issue(
            findings,
            actions,
            "Customer Satisfaction",
            "Customer satisfaction data is missing or invalid.",
            "Verify customer feedback records and update the audit data."
        )

    elif satisfaction < RULES["customer_satisfaction"]["threshold"]:
        score -= RULES["customer_satisfaction"]["weight"]
        failed_rules.append("customer_satisfaction")

        add_issue(
            findings,
            actions,
            "Customer Satisfaction",
            f"Average satisfaction is {satisfaction:.2f}/5, "
            f"below the {RULES['customer_satisfaction']['threshold']:.1f}/5 "
            "project standard.",
            "Review service quality and customer feedback and implement corrective training."
        )

    # --------------------------------------------------------
    # 3. Complaints
    # --------------------------------------------------------

    complaints = row["Complaints"]

    if pd.isna(complaints):
        score -= RULES["complaints"]["weight"]
        failed_rules.append("complaints")

        add_issue(
            findings,
            actions,
            "Complaints",
            "Complaint data is missing or invalid.",
            "Verify complaint records before completing the audit."
        )

    elif complaints >= RULES["complaints"]["threshold"]:
        score -= RULES["complaints"]["weight"]
        failed_rules.append("complaints")

        add_issue(
            findings,
            actions,
            "Complaints",
            f"Monthly complaints are {complaints:.0f}, "
            f"above the {RULES['complaints']['threshold']:.0f} "
            "project standard.",
            "Investigate complaint causes and implement a customer-service improvement plan."
        )

    # --------------------------------------------------------
    # 4. Conversion rate
    # --------------------------------------------------------

    conversion = row["Conversion_Rate_%"]

    if pd.isna(conversion):
        score -= RULES["conversion_rate"]["weight"]
        failed_rules.append("conversion_rate")

        add_issue(
            findings,
            actions,
            "Conversion Rate",
            "Conversion-rate data is missing or invalid.",
            "Verify footfall and order records and recalculate conversion performance."
        )

    elif conversion < RULES["conversion_rate"]["threshold"]:
        score -= RULES["conversion_rate"]["weight"]
        failed_rules.append("conversion_rate")

        add_issue(
            findings,
            actions,
            "Conversion Rate",
            f"Conversion rate is {conversion:.2f}%, "
            f"below the {RULES['conversion_rate']['threshold']:.0f}% "
            "project standard.",
            "Review customer conversion performance and improve sales-floor processes."
        )

    # --------------------------------------------------------
    # 5. Profit margin
    # --------------------------------------------------------

    margin = row["Profit_Margin_%"]

    if pd.isna(margin):
        score -= RULES["profit_margin"]["weight"]
        failed_rules.append("profit_margin")

        add_issue(
            findings,
            actions,
            "Profit Margin",
            "Profit-margin data is missing or invalid.",
            "Verify revenue, COGS and operating-cost records."
        )

    elif margin < RULES["profit_margin"]["threshold"]:
        score -= RULES["profit_margin"]["weight"]
        failed_rules.append("profit_margin")

        add_issue(
            findings,
            actions,
            "Profit Margin",
            f"Profit margin is {margin:.2f}%, "
            f"below the {RULES['profit_margin']['threshold']:.0f}% "
            "project standard.",
            "Review pricing, operating costs and product-level profitability."
        )

    # --------------------------------------------------------
    # 6. Stock availability
    # --------------------------------------------------------

    stock_availability = row["Stock_Availability_%"]

    if pd.isna(stock_availability):
        score -= RULES["stock_availability"]["weight"]
        failed_rules.append("stock_availability")

        add_issue(
            findings,
            actions,
            "Stock Availability",
            "Stock-availability data is missing or invalid.",
            "Verify inventory records and update stock-availability data."
        )

    elif stock_availability < RULES["stock_availability"]["threshold"]:
        score -= RULES["stock_availability"]["weight"]
        failed_rules.append("stock_availability")

        add_issue(
            findings,
            actions,
            "Stock Availability",
            f"Stock availability is {stock_availability:.2f}%, "
            f"below the {RULES['stock_availability']['threshold']:.0f}% "
            "project standard.",
            "Review stock levels and initiate replenishment for affected items."
        )

    # --------------------------------------------------------
    # 7. Freshness
    # --------------------------------------------------------

    freshness = row["Freshness_Rate_%"]

    if pd.isna(freshness):
        score -= RULES["freshness_rate"]["weight"]
        failed_rules.append("freshness_rate")

        add_issue(
            findings,
            actions,
            "Freshness Rate",
            "Freshness-rate data is missing or invalid.",
            "Verify product freshness records and update inventory monitoring."
        )

    elif freshness < RULES["freshness_rate"]["threshold"]:
        score -= RULES["freshness_rate"]["weight"]
        failed_rules.append("freshness_rate")

        add_issue(
            findings,
            actions,
            "Freshness Rate",
            f"Freshness rate is {freshness:.2f}%, "
            f"below the {RULES['freshness_rate']['threshold']:.0f}% "
            "project standard.",
            "Review stock rotation, storage practices and ageing inventory."
        )

    # --------------------------------------------------------
    # 8. Wastage
    # --------------------------------------------------------

    wastage = row["Wastage_Units"]

    if pd.isna(wastage):
        score -= RULES["wastage"]["weight"]
        failed_rules.append("wastage")

        add_issue(
            findings,
            actions,
            "Inventory Wastage",
            "Wastage data is missing or invalid.",
            "Verify inventory wastage records."
        )

    elif wastage > RULES["wastage"]["threshold"]:
        score -= RULES["wastage"]["weight"]
        failed_rules.append("wastage")

        add_issue(
            findings,
            actions,
            "Inventory Wastage",
            f"Wastage is {wastage:.0f} units, above the "
            f"{RULES['wastage']['threshold']:.0f}-unit "
            "project standard.",
            "Investigate wastage causes and improve stock rotation and handling."
        )

    # --------------------------------------------------------
    # 9. Replenishment
    # --------------------------------------------------------

    replenishment_required = row["Replenishment_Required"]

    if replenishment_required:
        score -= RULES["replenishment"]["weight"]
        failed_rules.append("replenishment")

        add_issue(
            findings,
            actions,
            "Replenishment",
            "Inventory replenishment is required for the outlet.",
            "Review reorder requirements and complete replenishment before stock risk increases."
        )

    # --------------------------------------------------------
    # Final score
    # --------------------------------------------------------

    score = max(0.0, min(100.0, score))

    status = status_from_score(score)

    issue_count = len(failed_rules)

    severity = severity_from_count(issue_count)

    priority = priority_from_severity(severity)

    if issue_count == 0:
        findings_text = "No audit issues detected."
        actions_text = "Continue routine monitoring and maintain current standards."
        severity = "Low"
        priority = "P4"

    else:
        findings_text = " | ".join(findings)
        actions_text = " | ".join(actions)

    return {
        "Audit_Score": round(score, 2),
        "Audit_Status": status,
        "Issue_Count": issue_count,
        "Severity": severity,
        "Priority": priority,
        "Findings": findings_text,
        "Corrective_Actions": actions_text,
        "Rules_Failed": ", ".join(failed_rules)
        if failed_rules
        else "No rules failed",
    }


# ============================================================
# AUDIT PIPELINE
# ============================================================

def run_audit():
    """Run the complete Audit & Compliance Agent."""

    print("Loading dataset...")

    raw_data = load_dataset()

    print(f"Dataset loaded successfully!")
    print(f"Rows: {len(raw_data)}")
    print(
        f"Total outlets: {raw_data['Outlet_ID'].nunique()}"
    )

    audit_data = prepare_data(raw_data)

    # --------------------------------------------------------
    # Audit only the latest available month for each outlet.
    # This creates a current operational compliance snapshot.
    # --------------------------------------------------------

    latest_records = (
        audit_data.sort_values(
            ["Outlet_ID", "Month"]
        )
        .groupby("Outlet_ID", as_index=False)
        .tail(1)
        .copy()
    )

    latest_records = latest_records.sort_values(
        "Outlet_ID"
    ).reset_index(drop=True)

    audit_results = []

    for _, row in latest_records.iterrows():

        result = audit_outlet(row)

        audit_results.append(
            {
                "Outlet_ID": row["Outlet_ID"],
                "Outlet_Name": row["Outlet_Name"],
                "Audit_Month": row["Month"].strftime("%Y-%m"),
                "Employees": round(
                    row["Employees"], 2
                )
                if pd.notna(row["Employees"])
                else np.nan,
                "Employee_Turnover_%": round(
                    row["Employee_Turnover_%"], 2
                )
                if pd.notna(row["Employee_Turnover_%"])
                else np.nan,
                "Customer_Satisfaction_1_5": round(
                    row["Customer_Satisfaction_1_5"], 2
                )
                if pd.notna(row["Customer_Satisfaction_1_5"])
                else np.nan,
                "Complaints": round(
                    row["Complaints"], 2
                )
                if pd.notna(row["Complaints"])
                else np.nan,
                "Conversion_Rate_%": round(
                    row["Conversion_Rate_%"], 2
                )
                if pd.notna(row["Conversion_Rate_%"])
                else np.nan,
                "Profit_Margin_%": round(
                    row["Profit_Margin_%"], 2
                )
                if pd.notna(row["Profit_Margin_%"])
                else np.nan,
                "Stock_Availability_%": round(
                    row["Stock_Availability_%"], 2
                )
                if pd.notna(row["Stock_Availability_%"])
                else np.nan,
                "Freshness_Rate_%": round(
                    row["Freshness_Rate_%"], 2
                )
                if pd.notna(row["Freshness_Rate_%"])
                else np.nan,
                "Wastage_Units": round(
                    row["Wastage_Units"], 2
                )
                if pd.notna(row["Wastage_Units"])
                else np.nan,
                "Replenishment_Required": bool(
                    row["Replenishment_Required"]
                ),
                **result,
            }
        )

    output = pd.DataFrame(audit_results)

    # --------------------------------------------------------
    # Save output
    # --------------------------------------------------------

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    output.to_csv(
        OUTPUT_FILE,
        index=False
    )

    # --------------------------------------------------------
    # Console summary
    # --------------------------------------------------------

    print("\nAudit Agent completed successfully!")

    print("\nAudit Status Distribution:")
    print(
        output["Audit_Status"]
        .value_counts()
    )

    print("\nSeverity Distribution:")
    print(
        output["Severity"]
        .value_counts()
    )

    print("\nAverage Audit Score:")
    print(
        round(
            output["Audit_Score"].mean(),
            2
        )
    )

    print("\nTop 10 Audit Results:")
    print(
        output[
            [
                "Outlet_ID",
                "Outlet_Name",
                "Audit_Score",
                "Audit_Status",
                "Issue_Count",
                "Severity",
                "Priority",
            ]
        ]
        .head(10)
        .to_string(index=False)
    )

    print("\nOutput file saved:")
    print(OUTPUT_FILE)

    return output


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    run_audit()