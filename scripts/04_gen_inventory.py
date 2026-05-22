"""
Generate synthetic inventory movements anchored to real POS sales.
One row per (store, date, sku) where actual sales occurred.
"""
import os
import hashlib
import numpy as np
import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
SEED     = 42

FOOD_COST_RATIOS = {
    "BEVERAGE":       0.15,
    "SOFT SERVE":     0.18,
    "ADD ON":         0.20,
    "SNACKS":         0.25,
    "ALA CARTE":      0.28,
    "EDV":            0.28,
    "MEAL BOX":       0.30,
    "MAKE IT A MEAL": 0.30,
    "SHARING":        0.32,
}
DEFAULT_FOOD_COST = 0.28

BASE_WASTE_PCT = {
    "BEVERAGE":       0.03,
    "SOFT SERVE":     0.05,
    "ADD ON":         0.04,
    "SNACKS":         0.06,
    "ALA CARTE":      0.07,
    "EDV":            0.06,
    "MEAL BOX":       0.08,
    "MAKE IT A MEAL": 0.08,
    "SHARING":        0.09,
}
DEFAULT_WASTE_PCT = 0.07


def store_waste_multiplier(store_id):
    h = int(hashlib.md5(f"waste_{store_id}".encode()).hexdigest(), 16)
    return 0.7 + (h % 1000) / 1000 * 0.7


def store_log_compliance(store_id):
    h = int(hashlib.md5(f"comp_{store_id}".encode()).hexdigest(), 16)
    return 0.4 + (h % 1000) / 1000 * 0.55


def main():
    menu_path = os.path.join(DATA_DIR, "menu_items.csv")
    item_path = os.path.join(DATA_DIR, "pos_line_items.csv")

    print("Loading data...")
    menu  = pd.read_csv(menu_path,  low_memory=False)
    items = pd.read_csv(item_path,  low_memory=False)

    items["quantity"]   = pd.to_numeric(items["quantity"],   errors="coerce").fillna(1)
    items["line_total"] = pd.to_numeric(items["line_total"], errors="coerce")
    items["unit_price"] = items["line_total"] / items["quantity"].replace(0, np.nan)

    # Top 30 SKUs by volume
    top30 = (
        items.groupby("product_id")["quantity"].sum()
        .nlargest(30)
        .index.tolist()
    )
    print(f"  Top-30 SKUs selected")

    # Load transactions for dates
    txn_path = os.path.join(DATA_DIR, "pos_transactions.csv")
    txns = pd.read_csv(txn_path, usecols=["transaction_id", "store_id", "timestamp"], low_memory=False)
    txns["timestamp"] = pd.to_datetime(txns["timestamp"], errors="coerce", utc=True)
    txns["date"]      = txns["timestamp"].dt.date

    # Build daily sales: (store, date, product_id) -> quantity sold
    items_with_date = items.merge(
        txns[["transaction_id", "date"]],
        on="transaction_id",
        how="left",
    )
    items_filtered = items_with_date[items_with_date["product_id"].isin(top30)].copy()

    daily_sales = (
        items_filtered
        .groupby(["store_id", "date", "product_id"])
        .agg(
            theoretical_sold=("quantity",   "sum"),
            avg_unit_price  =("unit_price", "mean"),
            category        =("category",   lambda s: s.mode().iloc[0] if len(s) > 0 else ""),
        )
        .reset_index()
    )

    print(f"  {len(daily_sales):,} (store, date, sku) combos to generate inventory for")

    rng = np.random.default_rng(SEED)
    rows = []
    for i, row in daily_sales.iterrows():
        if i % 20000 == 0:
            print(f"  Processing {i:,}/{len(daily_sales):,}...", end="\r")

        store_id = row["store_id"]
        sold     = float(row["theoretical_sold"])
        cat      = row.get("category", "")
        avg_px   = float(row.get("avg_unit_price", 200)) if not pd.isna(row.get("avg_unit_price", np.nan)) else 200

        food_cost_ratio = FOOD_COST_RATIOS.get(str(cat).upper(), DEFAULT_FOOD_COST)
        unit_cost       = avg_px * food_cost_ratio
        base_waste      = BASE_WASTE_PCT.get(str(cat).upper(), DEFAULT_WASTE_PCT)
        waste_mult      = store_waste_multiplier(store_id)
        compliance      = store_log_compliance(store_id)

        opening    = sold * rng.uniform(1.10, 1.35)
        received   = sold * rng.uniform(0.05, 0.20)
        waste_pct  = base_waste * waste_mult
        actual_waste = (opening + received - sold) * waste_pct
        waste_logged = actual_waste if rng.random() < compliance else 0.0
        counted_close = opening + received - sold - actual_waste + rng.normal(0, sold * 0.02)
        variance     = counted_close - (opening + received - sold - waste_logged)
        variance_pkr = variance * unit_cost

        rows.append({
            "movement_id":      f"INV-{store_id}-{row['date']}-{row['product_id']}",
            "store_id":         store_id,
            "date":             row["date"],
            "product_id":       row["product_id"],
            "category":         cat,
            "opening_qty":      round(opening,        2),
            "received_qty":     round(received,       2),
            "theoretical_sold": round(sold,           2),
            "actual_waste_qty": round(actual_waste,   2),
            "waste_logged_qty": round(waste_logged,   2),
            "counted_close_qty":round(counted_close,  2),
            "variance_qty":     round(variance,       2),
            "unit_cost_pkr":    round(unit_cost,      2),
            "variance_pkr":     round(variance_pkr,   2),
            "log_compliance":   round(compliance,     3),
        })

    out_path = os.path.join(DATA_DIR, "inventory_movements.csv")
    pd.DataFrame(rows).to_csv(out_path, index=False)
    print(f"\n  Generated {len(rows):,} inventory movement records")
    print(f"Saved: {out_path}")
    print("Done.")


if __name__ == "__main__":
    main()
