"""
Profile POS data: extract channels, build menu_items and store_summary,
emit pos_profile.json. Also patches channel back into pos_transactions.csv.
"""
import os
import json
import re
import pandas as pd
import numpy as np

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

CHANNEL_PATTERNS = {
    "DRIVE THRU": re.compile(r"DRIVE[\s_]?THRU", re.I),
    "EAT IN":     re.compile(r"EAT[\s_]?IN", re.I),
    "EAT OUT":    re.compile(r"EAT[\s_]?OUT", re.I),
    "DELIVERY":   re.compile(r"DELIVERY", re.I),
}


def extract_channel(product_name):
    if not isinstance(product_name, str):
        return "UNKNOWN"
    for ch, pat in CHANNEL_PATTERNS.items():
        if pat.search(product_name):
            return ch
    return "UNKNOWN"


def dominant_channel(channels):
    if hasattr(channels, "tolist"):
        channels = channels.tolist()
    if not channels:
        return "UNKNOWN"
    counts = {}
    for c in channels:
        counts[c] = counts.get(c, 0) + 1
    return max(counts, key=counts.get)


def main():
    txn_path  = os.path.join(DATA_DIR, "pos_transactions.csv")
    item_path = os.path.join(DATA_DIR, "pos_line_items.csv")

    print("Loading CSVs...")
    txns  = pd.read_csv(txn_path,  low_memory=False)
    items = pd.read_csv(item_path, low_memory=False)

    print("Extracting channels from line items...")
    items["channel"] = items["product_name"].apply(extract_channel)

    txn_channel = (
        items.groupby("transaction_id")["channel"]
        .apply(dominant_channel)
        .reset_index()
        .rename(columns={"channel": "channel"})
    )
    txns = txns.drop(columns=["channel"], errors="ignore")
    txns = txns.merge(txn_channel, on="transaction_id", how="left")
    txns["channel"] = txns["channel"].fillna("UNKNOWN")
    txns.to_csv(txn_path, index=False)
    print(f"  Channel distribution:\n{txns['channel'].value_counts().to_string()}")

    print("\nBuilding menu_items.csv...")
    items["quantity"] = pd.to_numeric(items["quantity"], errors="coerce").fillna(1)
    items["line_total"] = pd.to_numeric(items["line_total"], errors="coerce")
    items["unit_price"] = items["line_total"] / items["quantity"].replace(0, np.nan)

    menu = (
        items.groupby("product_id")
        .agg(
            product_name=("product_name", lambda s: s.mode().iloc[0] if not s.mode().empty else ""),
            category    =("category",     lambda s: s.mode().iloc[0] if not s.mode().empty else ""),
            channel     =("channel",      lambda s: s.mode().iloc[0] if len(s) > 0 else "UNKNOWN"),
            n_sold      =("quantity",     "sum"),
            avg_price_pkr=("unit_price",  "mean"),
            min_price_pkr=("unit_price",  "min"),
            max_price_pkr=("unit_price",  "max"),
        )
        .reset_index()
    )
    menu_path = os.path.join(DATA_DIR, "menu_items.csv")
    menu.to_csv(menu_path, index=False)
    print(f"  {len(menu):,} unique SKUs saved to {menu_path}")

    print("\nBuilding store_summary.csv...")
    txns["timestamp"] = pd.to_datetime(txns["timestamp"], errors="coerce", utc=True)
    txns["date"]      = txns["timestamp"].dt.date

    def channel_pct(grp, ch):
        return (grp["channel"] == ch).mean()

    store_grp = txns.groupby("store_id")
    summary = store_grp.agg(
        n_transactions=("transaction_id", "count"),
        n_active_days =("date",           "nunique"),
        avg_basket_pkr=("basket_value",   "mean"),
    ).reset_index()
    summary["txn_per_day"] = summary["n_transactions"] / summary["n_active_days"].replace(0, np.nan)

    for ch in ["EAT IN", "EAT OUT", "DRIVE THRU", "DELIVERY"]:
        col = "pct_" + ch.lower().replace(" ", "_")
        summary[col] = summary["store_id"].map(
            txns.groupby("store_id")["channel"].apply(lambda g: (g == ch).mean())
        )
    summary["pct_unknown_channel"] = summary["store_id"].map(
        txns.groupby("store_id")["channel"].apply(lambda g: (g == "UNKNOWN").mean())
    )

    summary_path = os.path.join(DATA_DIR, "store_summary.csv")
    summary.to_csv(summary_path, index=False)
    print(f"  {len(summary):,} stores saved to {summary_path}")

    print("\nBuilding pos_profile.json...")
    txns["hour"]    = txns["timestamp"].dt.hour
    txns["weekday"] = txns["timestamp"].dt.dayofweek
    txns["basket_value"] = pd.to_numeric(txns["basket_value"], errors="coerce")
    txns["item_count"]   = pd.to_numeric(txns["item_count"],   errors="coerce")

    if "received_at" in txns.columns:
        txns["received_at"] = pd.to_datetime(txns["received_at"], errors="coerce", utc=True)
        latency = (txns["received_at"] - txns["timestamp"]).dt.total_seconds() * 1000
        latency_stats = {
            "p50_ms": float(latency.quantile(0.50)) if not latency.isna().all() else None,
            "p95_ms": float(latency.quantile(0.95)) if not latency.isna().all() else None,
            "p99_ms": float(latency.quantile(0.99)) if not latency.isna().all() else None,
        }
    else:
        latency_stats = {}

    profile = {
        "n_transactions":       int(len(txns)),
        "n_line_items":         int(len(items)),
        "n_stores":             int(txns["store_id"].nunique()),
        "n_unique_skus":        int(items["product_id"].nunique()),
        "date_range": {
            "earliest": str(txns["date"].dropna().min()) if "date" in txns.columns else None,
            "latest":   str(txns["date"].dropna().max()) if "date" in txns.columns else None,
        },
        "basket_value": {
            "mean": float(txns["basket_value"].mean()),
            "p25":  float(txns["basket_value"].quantile(0.25)),
            "p50":  float(txns["basket_value"].quantile(0.50)),
            "p75":  float(txns["basket_value"].quantile(0.75)),
            "p95":  float(txns["basket_value"].quantile(0.95)),
        },
        "item_count": {
            "mean": float(txns["item_count"].mean()),
            "p50":  float(txns["item_count"].quantile(0.50)),
            "p95":  float(txns["item_count"].quantile(0.95)),
        },
        "hourly_distribution": txns["hour"].value_counts().sort_index().to_dict(),
        "weekday_distribution": txns["weekday"].value_counts().sort_index().to_dict(),
        "payment_mix": txns["payment_method"].value_counts(dropna=False).to_dict(),
        "channel_mix": txns["channel"].value_counts().to_dict(),
        "top_categories": items.groupby("category")["quantity"].sum().nlargest(15).to_dict(),
        "receipt_latency_ms": latency_stats,
    }

    profile_path = os.path.join(DATA_DIR, "pos_profile.json")
    with open(profile_path, "w") as f:
        json.dump(profile, f, indent=2, default=str)
    print(f"  Profile saved to {profile_path}")
    print("\nDone.")


if __name__ == "__main__":
    main()
