import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

from inventory_agent.inventory_agent.inventory_agent import (
    load_inventory_data,
    build_inventory_agent_output,
)

from src.marketing_agent.marketing_agent import (
    load_data,
    build_marketing_agent_output,
)

from audit_agent.audit_agent import run_audit

from src.intelligence_engine.intelligence_engine import (
    build_intelligence,
)


class AgentOrchestrator:
    """
    Coordinates the execution of franchise agents.
    """

    def run(self):
        print("\n========== AGENT ORCHESTRATION ==========\n")

        results = {}

        # --------------------------------------------------
        # Load franchise dataset
        # --------------------------------------------------
        print("Loading franchise dataset...")
        inventory_data = load_inventory_data()

        # --------------------------------------------------
        # Inventory Agent
        # --------------------------------------------------
        print("\nRunning Inventory Agent...")
        inventory_result = build_inventory_agent_output(
            inventory_data
        )

        results["Inventory Agent"] = inventory_result

        # --------------------------------------------------
        # Marketing Agent
        # --------------------------------------------------
        print("\nRunning Marketing Agent...")
        marketing_data = load_data()

        marketing_result = build_marketing_agent_output(
            marketing_data
        )

        results["Marketing Agent"] = marketing_result

        # --------------------------------------------------
        # Audit Agent
        # --------------------------------------------------
        print("\nRunning Audit Agent...")
        audit_result = run_audit()

        results["Audit Agent"] = audit_result

        # --------------------------------------------------
        # Franchise Intelligence Engine
        # --------------------------------------------------
        print("\nRunning Franchise Intelligence Engine...")
        # Persist current results before the file-based intelligence engine reads them.
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        inventory_result.to_csv(PROCESSED_DIR / "inventory_agent_output.csv", index=False)
        marketing_result.to_csv(PROCESSED_DIR / "marketing_agent_output.csv", index=False)
        from intelligence.franchise_intelligence import prepare_engine_inputs
        prepare_engine_inputs(audit_result)
        build_intelligence()

        intelligence_output_file = (
            PROCESSED_DIR / "intelligence_output.csv"
        )

        intelligence_result = pd.read_csv(
            intelligence_output_file
        )

        results["Franchise Intelligence Engine"] = (
            intelligence_result
        )

        # --------------------------------------------------
        # Orchestration completed
        # --------------------------------------------------
        print("\n========== ORCHESTRATION COMPLETED ==========")

        print(
            f"Inventory output: {inventory_result.shape}"
        )

        print(
            f"Marketing output: {marketing_result.shape}"
        )

        print(
            f"Audit output: {audit_result.shape}"
        )

        print(
            f"Intelligence output: "
            f"{intelligence_result.shape}"
        )

        return results