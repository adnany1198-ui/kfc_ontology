"""
Generate synthetic procurement price data for 6 commodities.
Weekly observations spanning POS date range + 90 days of history.
Embedded shocks: Poultry +32% at ~40% through, Oil +25% at ~75%.
"""
import os
import numpy as np
import pandas as pd
from datetime import date, timedelta

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
SEED     = 42

COMMODITIES = [
    {"id": "POULTRY_WHL", "name": "Whole Poultry",      "base_pkr": 480, "unit": "kg",     "vol": 0.06, "shock_idx": 0},
    {"id": "POULTRY_BST", "name": "Poultry Breast",     "base_pkr": 720, "unit": "kg",     "vol": 0.07, "shock_idx": 0},
    {"id": "COOK_OIL",    "name": "Cooking Oil",         "base_pkr": 580, "unit": "litre",  "vol": 0.04, "shock_idx": 1},
    {"id": "FLOUR_RFD",   "name": "Refined Flour",       "base_pkr": 140, "unit": "kg",     "vol": 0.03, "shock_idx": -1},
    {"id": "RICE_BSM",    "name": "Basmati Rice",        "base_pkr": 320, "unit": "kg",     "vol": 0.03, "shock_idx": -1},
    {"id": "BEV_CONC",    "name": "Beverage Concentrate","base_pkr": 850, "unit": "litre",  "vol": 0.02, "shock_idx": -1},
]

SHOCKS = [
    {"commodity_idx": 0, "trigger_pct": 0.40, "magnitude": 0.32, "decay_weeks": 8},  # Poultry +32%
    {"commodity_idx": 1, "trigger_pct": 0.75, "magnitude": 0.25, "decay_weeks": 6},  # Oil +25%
]

ANNUAL_DRIFT = 0.14  # 14% annual price drift
CONTRACT_SPREAD_PCT = 0.06  # contract price ~ 6% below spot on average


def generate_price_series(base_price, n_weeks, vol, shock_cfg, rng):
    """Random walk with annual drift and an optional price shock."""
    weekly_drift = (1 + ANNUAL_DRIFT) ** (1 / 52) - 1
    prices = [base_price]
    for w in range(1, n_weeks):
        shock_mult = 1.0
        for shock in shock_cfg:
            trigger_week = int(shock["trigger_pct"] * n_weeks)
            if w >= trigger_week:
                elapsed = w - trigger_week
                decay   = max(0, 1 - elapsed / shock["decay_weeks"])
                shock_mult *= (1 + shock["magnitude"] * decay)

        ret = weekly_drift + rng.normal(0, vol / np.sqrt(52))
        prices.append(prices[-1] * (1 + ret) * shock_mult)
    return prices


def main():
    txn_path = os.path.join(DATA_DIR, "pos_transactions.csv")
    txns = pd.read_csv(txn_path, usecols=["timestamp"], low_memory=False)
    txns["timestamp"] = pd.to_datetime(txns["timestamp"], errors="coerce", utc=True)
    pos_start = txns["timestamp"].min().date()
    pos_end   = txns["timestamp"].max().date()

    history_start = pos_start - timedelta(days=90)
    history_start = history_start - timedelta(days=history_start.weekday())  # align to Monday
    n_weeks = ((pos_end - history_start).days // 7) + 1

    print(f"Generating procurement prices: {history_start} to {pos_end} ({n_weeks} weeks)")

    rng = np.random.default_rng(SEED)
    rows = []

    for c in COMMODITIES:
        shock_cfg = [s for s in SHOCKS if s["commodity_idx"] == c["shock_idx"]]
        spot_prices = generate_price_series(c["base_pkr"], n_weeks, c["vol"], shock_cfg, rng)

        for w, spot in enumerate(spot_prices):
            week_start = history_start + timedelta(weeks=w)
            contract   = spot * (1 - CONTRACT_SPREAD_PCT + rng.normal(0, 0.01))
            exposure   = rng.uniform(0.55, 0.85)  # fraction of volume on spot

            rows.append({
                "commodity_id":            c["id"],
                "commodity_name":          c["name"],
                "supplier_id":             f"SUP-{c['id'][:3]}-{(int(hashlib.md5(c['id'].encode()).hexdigest(), 16) % 5) + 1:02d}",
                "week_starting":           week_start.isoformat(),
                "spot_price_pkr":          round(spot, 2),
                "contract_price_pkr":      round(contract, 2),
                "unit":                    c["unit"],
                "exposure_pct_vs_contract":round(exposure, 3),
            })

    out_path = os.path.join(DATA_DIR, "procurement_prices.csv")
    pd.DataFrame(rows).to_csv(out_path, index=False)
    print(f"  Generated {len(rows):,} procurement price records")
    print(f"Saved: {out_path}")
    print("Done.")


import hashlib  # noqa: E402 — used in supplier_id generation above

if __name__ == "__main__":
    main()
