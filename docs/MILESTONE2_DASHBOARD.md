# Milestone 2 Dashboard Integration

## Objective

Extend the existing Outlet Performance Intelligence dashboard without changing its visual design. The Milestone 2 dashboard turns Staff, Marketing, Inventory, and Demand Forecasting outputs into outlet-level decisions while retaining every Milestone 1 view.

## Active modules

| Module | Owner | Input | Output | Dashboard use |
| --- | --- | --- | --- | --- |
| Staff Agent | Nandini | Milestone 2 outlet Excel data | `staff_agent/staff_agent_output.csv` | Staff status, people KPIs, insight, recommendation, risk view |
| Marketing Agent | RajaShri | Milestone 2 outlet Excel data | `data/processed/marketing_agent_output.csv` | Spend efficiency, conversion, category, alert, insight, recommendation |
| Inventory Agent | Nirma | Stock levels, reorder points, availability, freshness, wastage | `data/processed/inventory_agent_output.csv` | Stock status, action, priority, explanation, replenishment queue |
| Inventory Forecasting | Nirma | Monthly units sold per outlet/SKU | `data/processed/demand_forecast_output.csv` | Actual demand and moving-average forecast trend |
| Performance Dashboard | Narayanadas | Milestone 1 analytics plus all four Milestone 2 outputs | Interactive Streamlit dashboard and CSV downloads | One consistent decision interface |

## End-to-end flow

1. Milestone 1 source data is validated, benchmarked, scored, and converted into outlet performance recommendations.
2. Staff Agent groups the Milestone 2 dataset by outlet and evaluates employees, employee turnover, customer satisfaction, and complaints.
3. Marketing Agent groups the same dataset by outlet and evaluates spend, revenue, orders, conversion, and revenue generated per marketing rupee.
4. Inventory Agent checks stock state, replenishment requirement, and perishable wastage to create an action, priority, explanation, and replenishment quantity.
5. Demand Forecasting calculates each month's estimate from the prior three months of SKU demand.
6. Both inventory pipelines remove the 120 supplied duplicate outlet/SKU/month test rows, matching the project's existing first-record cleaning rule.
7. `src/milestone2_loader.py` validates all four outputs and confirms common coverage across 750 outlets.
8. `app.py` displays all modules using the existing theme, cards, charts, tables, filters, and download pattern.

## Current result

- Staff Agent output: 750 outlets.
- Marketing Agent output: 750 outlets.
- Inventory Agent output: 30,000 unique outlet/SKU/month rows.
- Demand Forecast output: 30,000 rows, 750 latest SKU forecasts, and 27,750 calculated historical forecasts after the three-month warm-up.
- Shared end-to-end coverage: 750 outlets.
- Data-quality result: 120 duplicate test rows detected and removed before inventory decisions and forecasting.

## Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

Run the checks with:

```bash
pytest -q
```
