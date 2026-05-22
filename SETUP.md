# Setup Guide

## Prerequisites

Python 3.9+. Install dependencies:

```bash
pip install duckdb pandas requests matplotlib seaborn numpy
```

## Step 0: Confirm webhook receiver

```bash
python scripts/00_confirm_webhook.py
```

Expected output: receiver alive, row count ~180k+, latest transaction shown.

If this fails, the Railway receiver is down. Check
https://cv2-production-008f.up.railway.app/ in a browser.

## Step 0b: (Optional) Deploy pagination patch

The receiver currently doesn't support pagination. To deploy the patch:

```bash
python scripts/00b_receiver_patch.py   # prints the patch code
```

Add the printed routes to your Railway receiver and redeploy. Once done,
01_pull_pos.py will use paginated fetching automatically.

Without the patch, 01_pull_pos.py falls back to per-store fetching.

## Step 1: Pull POS data

```bash
python scripts/01_pull_pos.py
```

Outputs:
- `data/pos_transactions.csv` — basket-level (~180k rows)
- `data/pos_line_items.csv` — one row per SKU per transaction

This takes 2-10 minutes depending on network and receiver load.

## Step 2: Profile POS data

```bash
python scripts/02_profile_pos.py
```

Outputs:
- `data/menu_items.csv` — unique SKU catalogue
- `data/store_summary.csv` — per-store rollup
- `data/pos_profile.json` — full statistics

Also adds `channel` column to `data/pos_transactions.csv`.

## Step 3: Generate synthetic Prism data

```bash
python scripts/03_gen_prism.py
```

Output: `data/prism_observations.csv` (~126k rows, ~70% of transactions)

## Step 4: Generate synthetic inventory data

```bash
python scripts/04_gen_inventory.py
```

Output: `data/inventory_movements.csv`

Requires `data/menu_items.csv` and `data/pos_line_items.csv` from steps 1-2.

## Step 5: Generate synthetic procurement prices

```bash
python scripts/05_gen_procurement.py
```

Output: `data/procurement_prices.csv`

## Step 6: Load DuckDB

```bash
python scripts/06_load_duckdb.py
```

Output: `data/kfc.duckdb`

Drops and recreates the database. Runs a sanity-check JOIN at the end.

## Or: Run everything at once

```bash
bash run_all.sh
```

## Step 7: Start Claude Code

```bash
claude
```

CLAUDE.md is automatically read by Claude Code. The agent will have full
access to the DuckDB substrate and all parametric models.

For the demo, screen-share and walk through `demo/questions.md`.

## Troubleshooting

**01_pull_pos.py hangs or returns partial data**
The receiver may be overloaded. Try per-store fetching by editing
`STRATEGY = "per_store"` at the top of the script.

**DuckDB errors in 06_load_duckdb.py**
Ensure all CSV files exist in `data/`. Run steps 1-5 first.

**Model import errors**
Run from the project root: `python -c "from models import ThroughputModel; print('OK')"`.
If it fails, check that `models/__init__.py` exists.

**Chart errors**
Ensure `demo/charts/` directory exists. The tools auto-create it but
check permissions if on a restricted filesystem.
