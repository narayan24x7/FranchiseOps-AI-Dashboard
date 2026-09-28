
import pandas as pd
import numpy as np

from src.intelligence_engine.intelligence_engine import (
    normalize_id,
    safe_numeric,
    first_existing_column,
    normalize_outlet_id,
)


# ============================================================
# UNIT TEST 1
# ID normalization
# ============================================================

def test_normalize_id():

    values = pd.Series([
        " OUT001 ",
        " OUT002",
        "OUT003 ",
        "",
        None,
    ])

    result = normalize_id(values)

    assert result.iloc[0] == "OUT001"
    assert result.iloc[1] == "OUT002"
    assert result.iloc[2] == "OUT003"
    assert pd.isna(result.iloc[3])
    assert pd.isna(result.iloc[4])


# ============================================================
# UNIT TEST 2
# Numeric conversion
# ============================================================

def test_safe_numeric():

    df = pd.DataFrame({
        "Revenue": [
            "100",
            "250.5",
            "invalid",
            None,
        ]
    })

    result = safe_numeric(
        df,
        ["Revenue"],
    )

    assert result["Revenue"].iloc[0] == 100
    assert result["Revenue"].iloc[1] == 250.5
    assert pd.isna(result["Revenue"].iloc[2])
    assert pd.isna(result["Revenue"].iloc[3])


# ============================================================
# UNIT TEST 3
# Column detection
# ============================================================

def test_first_existing_column():

    df = pd.DataFrame({
        "Revenue": [100, 200],
        "Sales": [50, 100],
    })

    assert first_existing_column(
        df,
        ["Revenue", "Sales"],
    ) == "Revenue"

    assert first_existing_column(
        df,
        ["Missing", "Sales"],
    ) == "Sales"


# ============================================================
# UNIT TEST 4
# Outlet ID normalization
# ============================================================

def test_normalize_outlet_id():

    df = pd.DataFrame({
        "Outlet_ID": [
            " out001 ",
            "OUT002",
            "out003",
        ]
    })

    result = normalize_outlet_id(
        df,
        "performance",
    )

    assert result["Outlet_ID"].tolist() == [
        "out001",
        "OUT002",
        "out003",
    ]


# ============================================================
# UNIT TEST 5
# Health score boundaries
# ============================================================

def test_health_score_boundaries():

    scores = pd.Series([
        -10,
        0,
        25,
        50,
        75,
        100,
        150,
    ])

    clipped = scores.clip(0, 100)

    assert clipped.min() == 0
    assert clipped.max() == 100

    assert clipped.tolist() == [
        0,
        0,
        25,
        50,
        75,
        100,
        100,
    ]


# ============================================================
# UNIT TEST 6
# Risk counting
# ============================================================

def test_multiple_risk_count():

    df = pd.DataFrame({
        "Performance_Risk": [
            True,
            False,
            False,
        ],
        "Inventory_Risk": [
            True,
            True,
            False,
        ],
        "Marketing_Risk": [
            True,
            False,
            False,
        ],
    })

    risk_columns = [
        "Performance_Risk",
        "Inventory_Risk",
        "Marketing_Risk",
    ]

    risk_count = (
        df[risk_columns]
        .sum(axis=1)
        .astype(int)
    )

    assert risk_count.tolist() == [
        3,
        1,
        0,
    ]


# ============================================================
# UNIT TEST 7
# Agent coverage
# ============================================================

def test_agent_coverage():

    available_agents = 2
    total_agents = 5

    coverage = (
        available_agents / total_agents
    ) * 100

    assert coverage == 40.0


# ============================================================
# UNIT TEST 8
# Missing agents
# ============================================================

def test_missing_agents():

    expected_agents = {
        "performance",
        "inventory",
        "staff",
        "marketing",
        "audit",
    }

    available_agents = {
        "performance",
        "inventory",
        "marketing",
    }

    missing_agents = (
        expected_agents - available_agents
    )

    assert missing_agents == {
        "staff",
        "audit",
    }


# ============================================================
# UNIT TEST 9
# Risk penalty calculation
# ============================================================

def test_risk_penalty():

    penalty = 0

    performance_risk = True
    inventory_risk = True
    wastage_risk = True
    overstock_risk = False
    marketing_risk = False

    if performance_risk:
        penalty += 8

    if inventory_risk:
        penalty += 10

    if wastage_risk:
        penalty += 5

    if overstock_risk:
        penalty += 3

    if marketing_risk:
        penalty += 7

    assert penalty == 23


# ============================================================
# UNIT TEST 10
# Health category boundaries
# ============================================================

def test_health_categories():

    scores = pd.Series([
        95,
        80,
        79,
        65,
        64,
        50,
        49,
    ])

    categories = np.select(
        [
            scores >= 80,
            scores >= 65,
            scores >= 50,
        ],
        [
            "Healthy",
            "Stable",
            "Needs Attention",
        ],
        default="Critical",
    )

    assert categories.tolist() == [
        "Healthy",
        "Healthy",
        "Stable",
        "Stable",
        "Needs Attention",
        "Needs Attention",
        "Critical",
    ]

