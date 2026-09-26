# FranchiseOps AI — Milestone 4

Executive dashboard with separate Python agents, Flask, vanilla JavaScript and SQLite. No Streamlit. Based on `Nishanth1405-max/FranchiseOps-AI`, branch `feature/m3-dashboard`, commit `fd0273a2020c755cb385bf0ba080d840c0160226`.

## Run locally

Use Python 3.12. From this folder:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/build_milestone4.py
python server.py
```

Windows activation: `.venv\Scripts\activate`. Open http://localhost:8000.
The downloadable package includes generated results and a database, so rebuilding is optional on first launch. Rebuild after changing source data. A source-only Git checkout must build first.

## Deploy on Render

Upload these project files to your repository, with `app.py`, `requirements.txt` and `render.yaml` at the repository root. Create a Render Blueprint from that repository, or create a Python Web Service with:

- Build command: `pip install -r requirements.txt && python scripts/build_milestone4.py`
- Start command: `python -m gunicorn app:app --workers 1 --threads 4 --bind 0.0.0.0:$PORT --timeout 180`
- Health check: `/api/status`
- Python version: `.python-version` pins 3.12.10.

The start command loads the actual Flask `app` object. `gunicorn` is included in requirements; do not use the placeholder `your_application.wsgi`.

Render's default filesystem is ephemeral. Rebuilds reproduce analytical results, but follow-up notes and run history need a persistent disk to survive replacement/redeploys. For a disk mounted at `/var/data`, set `FRANCHISEOPS_DATA_DIR=/var/data` and run the initial build from the runtime shell, or use this start command on its first deployment:

```bash
python scripts/build_milestone4.py && python -m gunicorn app:app --workers 1 --threads 4 --bind 0.0.0.0:$PORT --timeout 180
```

Persistent disks are mounted at runtime, not build time. One worker is required by the in-process orchestration lock. This is a single-instance project dashboard; authentication and multi-instance job scheduling are not included. Put an access layer in front of an internal deployment that contains private data.

## Dashboard pages

- **Executive dashboard:** revenue trend, combined score, priority outlets, audit workload and action queue.
- **Data & database:** validation evidence, source coverage and SQLite schema.
- **Audit agent:** rule, severity, threshold, measured value and recommended action. Open an outlet row to set an owner, note and follow-up status.
- **Franchise intelligence:** explainable five-driver weighted ranking and lowest-driver focus.
- **Agent orchestration:** persisted runs with each stage's status and errors. Run controls rebuild dependencies and refresh Milestone 4 results.
- **Earlier milestones:** all 12 existing agent views, filterable tables, record details and CSV exports.

Region/outlet filters apply to outlet dashboards. Data validation and run history are network-wide. M4 scores use the full period except latest-month financial/service audit checks and latest inventory signals; the underlying latest source month is April 2026. These are source-dataset results, not live operational feeds.

## Project structure

```text
app.py                         Flask application and APIs
server.py                      Local server entry point
pipeline.py                    Original agent adapters and chunked exports
render.yaml                    Render deployment configuration
dashboard/static/              HTML, CSS, JavaScript and generated JSON
src/milestone4/                 Final validation and data preparation
audit_agent/                   Evidence-backed operational audit rules
intelligence/                  Weighted franchise intelligence engine
orchestration/                 Dependency ordering and persisted run steps
database/schema.sql            Relational schema
database/store.py              SQLite connection and snapshot access
runtime/franchiseops.db         Generated database (ignored by Git)
scripts/build_milestone4.py     Full build entry point
tests/test_milestone4.py        M4 integration and validation checks
benchmarking/                  Existing project module
performance_score/             Existing project module
staff_agent/                   Existing project module
inventory_agent/               Existing project module
forecasting/                   Existing project module
recommendations/               Existing project module
src/milestone3/                Existing workforce/marketing/health agents
data/raw/                      Original workbooks
data/processed/                Canonical cleaned data and agent outputs
```

The existing agent folders and raw workbooks are retained. The old Streamlit app is replaced by the Flask entry point. No GitHub branch has been changed by generating this package.

## Validation, audit and scoring

Publication requires unique outlet/month sales keys, complete required columns, valid months, finite financial values, nonnegative revenue/orders, unique complete outlet coverage in all score inputs and driver scores between 0 and 100. Existing source adapters use median imputation for specified numeric gaps and deduplicate outlet/month rows. SQLite publishes outlet facts, sales facts and M4 snapshots in one transaction; validation failures preserve the previous M4 snapshot.

Audit rules are deterministic operational checks, not legal/compliance certification: latest-month profit below zero; latest-month satisfaction below 3/5; period attendance below 90%; period campaign ROI below zero; latest inventory score below 60. Audit score starts at 100, subtracts 20 per high and 10 per medium finding, and is bounded at zero. Stable finding IDs preserve follow-up status across reruns. A resolved status records a workflow decision; it does not override source evidence or alter the analytical score.

Intelligence score = 25% performance + 20% workforce + 20% marketing + 20% inventory + 15% audit. High priority is below 60, Medium is 60–74.99, and Monitor is 75+. Lowest driver determines focus. Weights and thresholds are explicit in the corresponding Python modules. No external LLM or API key is required.

Forecasts retain the supplied algorithm and are labelled **lagged estimates**: they average the preceding three observations and are not future projections.

Large JSON datasets are split into 2,500-row files. The browser reads a small manifest and validates the reconstructed row count. This removes the single large JSON response involved in the reported 10 MiB truncation error. Serve through Python, not by opening index.html as a local file.

## Verification

```bash
python -m pytest -q
node --check dashboard/static/app.js
node --check dashboard/static/m4.js
```

The database contains normalized outlets and monthly sales plus versioned-by-publication JSON snapshots, pipeline runs/steps and current finding follow-up state. It does not provide a historical change log for every follow-up edit. Restarted processes mark interrupted runs failed; start a new run to retry. Legacy CSV and JSON exports refresh before M4 validation; the M4 database transaction is the executive snapshot boundary.
