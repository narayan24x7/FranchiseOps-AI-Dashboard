"""Generate the auditable Milestone 1 processed dataset."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.analytics import calculate_performance_metrics  # noqa: E402
from src.data_loader import load_outlet_data  # noqa: E402


def main() -> None:
    source_path = ROOT / "data" / "raw" / "franchiseops_filtered_outlet_data.csv"
    output_path = ROOT / "data" / "processed" / "outlet_performance_intelligence.csv"
    source, report = load_outlet_data(source_path)
    processed = calculate_performance_metrics(source)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    processed.to_csv(output_path, index=False, date_format="%Y-%m-%d")
    print(
        f"Wrote {len(processed)} records for {report.outlets} outlets and "
        f"{report.months} months to {output_path.relative_to(ROOT)}"
    )


if __name__ == "__main__":
    main()
