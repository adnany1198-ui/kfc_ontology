#!/usr/bin/env bash
set -e

echo "=== KFC Pakistan AI Prototype — Full Data Pipeline ==="
echo ""

echo "Step 0: Confirming webhook receiver..."
python scripts/00_confirm_webhook.py
echo ""

echo "Step 1: Pulling POS data..."
python scripts/01_pull_pos.py
echo ""

echo "Step 2: Profiling POS data..."
python scripts/02_profile_pos.py
echo ""

echo "Step 3: Generating Prism observations..."
python scripts/03_gen_prism.py
echo ""

echo "Step 4: Generating inventory movements..."
python scripts/04_gen_inventory.py
echo ""

echo "Step 5: Generating procurement prices..."
python scripts/05_gen_procurement.py
echo ""

echo "Step 6: Loading DuckDB..."
python scripts/06_load_duckdb.py
echo ""

echo "=== Done. Start Claude Code with: claude ==="
