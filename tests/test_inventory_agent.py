import pandas as pd

from inventory_agent.inventory_agent.inventory_agent import (
    build_inventory_agent_output,
)


def inventory_row(**updates):
    row = {
        "Outlet_ID": "OUT0001",
        "Outlet_Name": "Outlet 1",
        "Month": "2026-01",
        "Product_Category": "Food & Beverage",
        "Product_Type": "Perishable",
        "SKU_ID": "SKU-0001-01",
        "Closing_Stock_Units": 50,
        "Safety_Stock_Units": 100,
        "Supplier_Lead_Time_Days": 5,
        "Reorder_Point_Units": 150,
        "Demand_Forecast_Next_Month_Units": 300,
        "Stock_Status": "Critical",
        "Replenishment_Required": "Yes",
        "Recommended_Replenishment_Units": 350,
        "Stock_Availability_%": 16.7,
        "Inventory_Turnover_Ratio": 10.0,
        "Wastage_Units": 5,
        "Freshness_Rate_%": 95.0,
        "Shelf_Life_Days": 14,
    }
    row.update(updates)
    return row


def test_inventory_agent_removes_duplicate_test_rows_and_prioritizes_actions():
    source = pd.DataFrame(
        [
            inventory_row(),
            inventory_row(Closing_Stock_Units=75),
            inventory_row(
                Outlet_ID="OUT0002",
                Outlet_Name="Outlet 2",
                SKU_ID="SKU-0002-01",
                Stock_Status="Healthy",
                Replenishment_Required="No",
            ),
            inventory_row(
                Outlet_ID="OUT0003",
                Outlet_Name="Outlet 3",
                SKU_ID="SKU-0003-01",
                Product_Type="Non-Perishable",
                Stock_Status="Overstocked",
                Replenishment_Required="No",
                Wastage_Units=0,
            ),
        ]
    )
    result = build_inventory_agent_output(source)
    assert len(result) == 3
    assert result.iloc[0]["Agent_Action"] == "URGENT_REORDER"
    actions = result.set_index("Outlet_ID")["Agent_Action"].to_dict()
    assert actions["OUT0002"] == "MONITOR_WASTAGE"
    assert actions["OUT0003"] == "REDUCE_STOCK"
