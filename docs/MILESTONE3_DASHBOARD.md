# Milestone 3 Dashboard Integration

## Objective

Milestone 3 turns detailed staff, campaign, and inventory results into one operational decision dashboard. A manager can see what is happening, which outlet needs attention, why it needs attention, and what action to take.

The existing dark Streamlit design remains unchanged. Milestone 3 uses the same cards, charts, tables, agent messages, filters, and downloads already used by Milestones 1 and 2.

## Overall project connection

```text
Milestone 1: outlet performance and benchmarking
Milestone 2: staff, marketing, inventory, and demand agents
Milestone 3: deeper workforce and campaign analysis
             + cross-functional operational decisions
```

The full decision flow is:

```text
Combined Excel data
  → Data Preparation
  → Staff Workforce + Marketing Effectiveness
  → join with latest Inventory Agent result
  → Operational health, priority, insight, and recommended action
  → Streamlit dashboard and CSV downloads
```

## Module 1: Data Preparation

### How it was built

1. Read the `Combined_M2_M3_Data` sheet from the combined Excel workbook.
2. Check all required identity, workforce, campaign, and inventory columns.
3. Convert dates and numeric fields to consistent types.
4. Validate score ranges, allowed categories, and campaign conversions.
5. Recalculate customer engagement as conversions divided by reach.
6. Remove duplicate Outlet ID + SKU ID + Month keys by keeping the first source record.
7. Create a data-quality output for the dashboard.

### Input and output

- Input: 30,120 combined Excel rows.
- Output: 30,000 unique analytical rows.
- Removed: 120 duplicate business keys.
- Coverage: 750 outlets, 40 months, and 30,000 unique campaigns.
- Missing Milestone 3 cells: 0.

### Why it is needed

Every later score depends on this step. Without consistent keys and validation, duplicate records could change totals, rankings, and recommendations.

## Module 2: Staff Workforce Intelligence

### How it was built

The module groups the prepared monthly data by outlet and calculates:

- average employees;
- average productivity score;
- average attendance rate;
- average staff performance score;
- top-performer and needs-improvement months;
- balanced, understaffed, and overstaffed months;
- latest staff category and scheduling status.

It then uses the observed staff-score quartiles to classify each outlet as Top Performer, Meets Expectations, or Needs Improvement. The alert becomes High when both performance and scheduling require attention, Medium when one requires attention, and Low when neither does.

### Output

- 750 outlet-level workforce records.
- 40 monthly network summaries.
- Workforce category and alert.
- Plain-English insight and recommendation.

### Why it is needed

The Milestone 2 Staff Agent identifies service and turnover risk. The Milestone 3 workforce view adds attendance, productivity, and scheduling, so the manager can understand whether staffing levels and staff execution are contributing to the problem.

## Module 3: Marketing Effectiveness

### How it was built

The supplied Milestone 3 score is implemented as:

```text
Marketing Effectiveness Score
  = Revenue per marketing rupee × 40%
  + Conversion effectiveness × 35%
  + Orders impact × 25%
```

Each component is converted to a 0-100 score against the best observed outlet. The module also adds the new Milestone 3 campaign fields:

- campaign reach;
- campaign conversions;
- customer engagement rate;
- campaign ROI;
- campaign performance category;
- primary campaign type.

### Output

- 750 outlet-level marketing-effectiveness records.
- 40 monthly campaign summaries.
- Effectiveness score and category.
- Campaign ROI category.
- Plain-English insight and recommendation.

### Why it is needed

The Milestone 2 Marketing Agent explains spend efficiency and sales conversion. Milestone 3 adds actual campaign reach, response, and ROI, which helps the business decide which campaign types to continue, change, or stop.

## Module 4: Operational Insights

### How it was built

The module joins the three decision areas by Outlet ID:

- Staff Workforce score;
- Marketing Effectiveness score;
- latest Inventory health score.

The operational score is:

```text
Operational Health
  = Staff score × 35%
  + Marketing score × 35%
  + Inventory score × 30%
```

The module counts how many components are below 70, identifies the lowest component as the primary focus area, raises the priority for urgent inventory actions, and generates an action for the weakest area.

### Output

- 750 cross-functional outlet records.
- Operational health score.
- High, Medium, or Low operational priority.
- Primary focus area.
- Operational insight and recommended action.

### Why it is needed

Separate agent reports can give different signals. Operational Insights combines them into one queue, so the manager knows which outlet to review first and which team should act.

## Dashboard output

Milestone 3 appears inside the existing dashboard pattern:

- Staff Agent tab: new workforce KPIs, trend, schedule mix, queue, and downloads.
- Marketing Agent tab: new effectiveness KPIs, campaign trend, category mix, queue, and downloads.
- Operational Insights tab: outlet drill-down, component comparison, priority mix, action queue, and download.
- Methodology & Quality tab: source rows, prepared rows, duplicate removal, campaign coverage, missing-field check, and formulas.

## Technology stack

- Python for module logic.
- Pandas for Excel/CSV loading, cleaning, grouping, joining, and validation.
- Streamlit for the dashboard.
- Plotly for interactive charts.
- Excel for the combined source data.
- CSV for validated module outputs.
- Pytest and Streamlit AppTest for automated checks.
- Git and GitHub feature branches for version control and integration.

No generative AI or external API is required. Insights and recommendations use deterministic, explainable rules.

## Verification result

- Source rows: 30,120.
- Prepared unique rows: 30,000.
- Duplicate business keys removed: 120.
- Shared workforce, marketing, and operations coverage: 750 outlets.
- Monthly coverage: 40 months.
- Unique campaigns: 30,000.
- Missing Milestone 3 values: 0.
- Engagement reconciliation maximum difference: 0.005 percentage points.
- Automated tests: 33 passed.
- Streamlit result: starts with no application exception and renders 20 charts, 11 downloads, and all Milestone 1, 2, and 3 views.

## Run and rebuild

```bash
pip install -r requirements.txt
python scripts/build_milestone3_outputs.py
streamlit run app.py
python -m pytest -q
```
