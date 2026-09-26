"""Build every Milestone 3 dashboard output from the combined workbook."""

from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.milestone2_loader import load_inventory_agent_output
from src.milestone3.data_preparation import load_milestone3_source
from src.milestone3.marketing_effectiveness import (
    build_marketing_effectiveness_outputs,
)
from src.milestone3.operational_insights import build_operational_insights
from src.milestone3.staff_workforce import build_staff_workforce_outputs


SOURCE_PATH = (
    ROOT
    / "data"
    / "raw"
    / "FranchiseOps_AI_Milestone2_Milestone3_Combined_Dataset.xlsx"
)
PROCESSED = ROOT / "data" / "processed"
INVENTORY_PATH = PROCESSED / "inventory_agent_output.csv"


def main() -> None:
    prepared, quality = load_milestone3_source(SOURCE_PATH)
    workforce, workforce_monthly = build_staff_workforce_outputs(prepared)
    marketing, marketing_monthly = build_marketing_effectiveness_outputs(prepared)
    inventory = load_inventory_agent_output(INVENTORY_PATH)
    operations = build_operational_insights(workforce, marketing, inventory)

    PROCESSED.mkdir(parents=True, exist_ok=True)
    workforce.to_csv(PROCESSED / "m3_staff_workforce_output.csv", index=False)
    workforce_monthly.to_csv(
        PROCESSED / "m3_staff_monthly_summary.csv",
        index=False,
        date_format="%Y-%m",
    )
    marketing.to_csv(PROCESSED / "m3_marketing_effectiveness_output.csv", index=False)
    marketing_monthly.to_csv(
        PROCESSED / "m3_marketing_monthly_summary.csv",
        index=False,
        date_format="%Y-%m",
    )
    operations.to_csv(PROCESSED / "m3_operational_insights.csv", index=False)
    pd.DataFrame([quality]).to_csv(PROCESSED / "m3_data_quality.csv", index=False)

    print("Milestone 3 outputs created successfully")
    print(f"Prepared records: {quality['prepared_rows']:,}")
    print(f"Duplicate keys removed: {quality['duplicate_keys_removed']:,}")
    print(f"Outlets with shared operational coverage: {len(operations):,}")


if __name__ == "__main__":
    main()
