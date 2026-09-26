# Milestone 1 Handoff

## Problem statement

Franchise chains struggle to compare locations consistently because sales, service, and customer-experience measures are often reviewed in separate reports. Milestone 1 solves this by integrating outlet measures, benchmarking every location, calculating an explainable health score, flagging underperformance, and presenting prioritized actions in one dashboard.

## Module ownership and outputs

| Work area | Implemented output |
| --- | --- |
| Sales & Outlet Data | Validated source loader, range checks, duplicate checks, identity checks, and processed CSV |
| Outlet Benchmarking | Monthly mean benchmark, benchmark gap, filtered peer comparison, and unique ranking |
| Performance Score | Five weighted component scores, overall score, four health categories, and alert severity |
| Outlet Performance Agent | Issue detection, explainable findings, and action recommendations without an API key |
| Performance Dashboard | Five interactive views, filters, charts, KPI cards, tables, and CSV downloads |
| Integration & Testing | 11 automated tests covering data, calculations, rankings, app startup, and filter behavior |

## Recommended demonstration flow

1. Open **Overview** and explain the latest network KPIs.
2. Change the **Region** filter to show that outlet scope and peer ranking update together.
3. Open **Benchmarking** and compare rank, score, target achievement, and peer gap.
4. Open **Outlet Analysis** and select a low-performing outlet to explain its score drivers.
5. Open **Agent Insights** to show prioritized findings and recommended actions.
6. Open **Methodology & Quality** to demonstrate transparent weights, thresholds, and validation.

## Verified dataset state

- 96 outlet-month records
- 12 outlets and 8 monthly periods
- 0 required-field gaps
- 0 duplicate outlet-month rows
- 0 outlet identity conflicts
- Complete, unique ranks from 1 to 12 in every month
- Performance scores bounded between 0 and 100

Run `pytest -q` before the final demonstration. The current project passes all 11 tests.
