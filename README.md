# KFC Pakistan AI Intelligence Prototype

An AI-driven retail intelligence demo for KFC Pakistan, modelled on
Palantir's ontology-first approach to operational data integration, with
a parametric simulation layer on top.

## What This Demonstrates

When fragmented operational data is unified into a single ontology AND
parametric simulation models sit on top, an AI analyst can answer
historical questions AND run what-if simulations that ripple across the
business — in seconds, every parameter transparent.

## Architecture

```
Layer 1: Substrate
  Real POS data (Railway receiver) + Synthetic Prism/Inventory/Procurement
  → data/kfc.duckdb

Layer 2: Derived objects
  SQL views computed on demand (EnrichedTransaction, ChannelMargin, etc.)

Layer 3: Parametric models
  models/throughput.py, margin.py, demand_shock.py, labour.py,
  waste_recovery.py, channel_mix.py, promotion.py
  + models/ripple.py orchestrator
```

## Quick Start

See SETUP.md for full instructions. Short version:

```bash
pip install duckdb pandas requests matplotlib seaborn
python scripts/00_confirm_webhook.py    # confirm live POS receiver
python scripts/01_pull_pos.py           # pull real POS data
python scripts/02_profile_pos.py        # channel extraction + rollups
python scripts/03_gen_prism.py          # synthetic CV demographics
python scripts/04_gen_inventory.py      # synthetic inventory
python scripts/05_gen_procurement.py    # synthetic procurement prices
python scripts/06_load_duckdb.py        # load all into DuckDB
claude                                  # start Claude Code
```

## Data

- **Real**: 180k+ POS transactions from 16+ KFC Pakistan stores, live
- **Synthetic**: Prism observations, inventory movements, procurement prices
  (all anchored to real transaction IDs and store IDs, seed 42)

## File Structure

```
scripts/    Data pipeline (00-06)
models/     Parametric simulation models + ripple orchestrator
tools/      kfc_tools.py — DuckDB query + chart helpers
data/       Generated data files (gitignored)
demo/       Demo questions + charts (charts gitignored)
```

## Models

| Model | Question it answers |
|-------|-------------------|
| ThroughputModel | Peak transactions/hour given till + kitchen config |
| MarginModel | Gross margin given basket mix and food costs |
| DemandShockModel | Impact of commodity price spike on COGS + margin |
| LabourModel | Optimal staffing given demand curve |
| WasteRecoveryModel | PKR recovery from improving waste compliance |
| ChannelMixModel | Impact of shifting from Foodpanda to own delivery |
| PromotionModel | Net impact of SKU discounting |

See `models/README.md` for parameter details and ripple connections.
