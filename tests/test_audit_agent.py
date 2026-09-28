import pandas as pd

from audit_agent.audit_agent import audit_outlet


def make_test_row(**changes):
    row = {
        "Employee_Turnover_%": 5.0,
        "Customer_Satisfaction_1_5": 4.0,
        "Complaints": 10.0,
        "Conversion_Rate_%": 20.0,
        "Profit_Margin_%": 20.0,
        "Stock_Availability_%": 95.0,
        "Freshness_Rate_%": 95.0,
        "Wastage_Units": 5.0,
        "Replenishment_Required": False,
    }

    row.update(changes)
    return pd.Series(row)


def test_compliant_outlet():
    result = audit_outlet(make_test_row())

    assert result["Audit_Score"] == 100
    assert result["Audit_Status"] == "Compliant"
    assert result["Issue_Count"] == 0


def test_employee_turnover_violation():
    result = audit_outlet(
        make_test_row(**{"Employee_Turnover_%": 15.0})
    )

    assert result["Issue_Count"] == 1
    assert "employee_turnover" in result["Rules_Failed"]
    assert "Employee Turnover" in result["Findings"]


def test_multiple_audit_issues():
    result = audit_outlet(
        make_test_row(
            **{
                "Employee_Turnover_%": 15.0,
                "Stock_Availability_%": 50.0,
                "Wastage_Units": 30.0,
            }
        )
    )

    assert result["Issue_Count"] == 3
    assert result["Severity"] == "High"
    assert result["Priority"] == "P2"


def test_missing_value_is_handled():
    result = audit_outlet(
        make_test_row(**{"Employee_Turnover_%": float("nan")})
    )

    assert result["Issue_Count"] >= 1
    assert "Employee Turnover" in result["Findings"]


def test_replenishment_issue():
    result = audit_outlet(
        make_test_row(Replenishment_Required=True)
    )

    assert result["Issue_Count"] >= 1
    assert "replenishment" in result["Rules_Failed"]
    assert "replenishment" in result["Corrective_Actions"].lower()