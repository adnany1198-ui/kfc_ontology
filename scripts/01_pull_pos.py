"""
Pull POS data from Railway receiver into data/pos_transactions.csv and
data/pos_line_items.csv.

Strategy:
  1. Try paginated fetch via /transactions?limit=5000&offset=N
  2. If pagination not available, fall back to per-store fetching
"""
import sys
import os
import json
import time
import requests
import pandas as pd

BASE_URL = os.environ.get("KFC_RECEIVER_URL", "https://cv2-production-008f.up.railway.app")
DATA_DIR  = os.path.join(os.path.dirname(__file__), "..", "data")
PAGE_SIZE = 5000

KNOWN_STORES = [
    "0019", "0030", "0047", "0062", "0151", "0157",
    "0174", "0184", "0210", "0219", "0221", "0223",
    "0244", "0245", "0249", "0251",
]


def parse_transaction(raw_obj):
    """Extract transaction fields from a receiver record (handles raw wrapper)."""
    raw = raw_obj.get("raw", raw_obj)
    t = {
        "transaction_id": raw.get("transaction_id") or raw_obj.get("transaction_id"),
        "store_id":        raw.get("store_id")        or raw_obj.get("store_id"),
        "till_id":         raw.get("till_id")         or raw_obj.get("till_id"),
        "operator_id":     raw.get("operator_id")     or raw_obj.get("operator_id"),
        "timestamp":       raw.get("timestamp")       or raw_obj.get("timestamp"),
        "basket_value":    raw.get("basket_value")    or raw_obj.get("basket_value"),
        "item_count":      raw.get("item_count")      or raw_obj.get("item_count"),
        "payment_method":  raw.get("payment_method")  or raw_obj.get("payment_method"),
        "received_at":     raw_obj.get("received_at") or raw.get("received_at"),
    }
    line_items = raw.get("line_items") or raw_obj.get("line_items") or []
    return t, line_items


def parse_all(records):
    transactions = []
    line_items   = []
    seen_txn_ids = set()

    for rec in records:
        t, items = parse_transaction(rec)
        tid = t["transaction_id"]
        if not tid or tid in seen_txn_ids:
            continue
        seen_txn_ids.add(tid)
        transactions.append(t)

        for item in items:
            line_items.append({
                "transaction_id": tid,
                "store_id":       t["store_id"],
                "product_id":     item.get("product_id"),
                "product_name":   item.get("product_name"),
                "category":       item.get("category"),
                "quantity":       item.get("quantity"),
                "line_total":     item.get("line_total"),
            })

    return transactions, line_items


def try_paginated():
    """Return list of all records via paginated /transactions endpoint."""
    print("Trying paginated fetch...")
    test = requests.get(f"{BASE_URL}/transactions", params={"limit": 1, "offset": 0}, timeout=20)
    if test.status_code != 200:
        print(f"  Paginated endpoint returned {test.status_code} — falling back")
        return None
    data = test.json()
    if not isinstance(data, dict) or "total" not in data:
        print("  Paginated endpoint not available (no 'total' field) — falling back")
        return None

    total = data["total"]
    print(f"  Total records: {total:,}")
    all_records = []
    offset = 0
    while offset < total:
        resp = requests.get(
            f"{BASE_URL}/transactions",
            params={"limit": PAGE_SIZE, "offset": offset},
            timeout=60,
        )
        resp.raise_for_status()
        page = resp.json()
        records = page.get("data", page.get("transactions", []))
        all_records.extend(records)
        offset += len(records)
        print(f"  Fetched {offset:,}/{total:,}", end="\r")
        if not records:
            break
        time.sleep(0.1)

    print(f"\n  Total fetched: {len(all_records):,}")
    return all_records


def try_per_store():
    """Return list of all records via per-store /transactions?store_id=X fetching."""
    print("Falling back to per-store fetching...")
    all_records = []
    for store in KNOWN_STORES:
        try:
            resp = requests.get(
                f"{BASE_URL}/transactions",
                params={"store_id": store},
                timeout=120,
            )
            if resp.status_code == 200:
                data = resp.json()
                records = data if isinstance(data, list) else data.get("data", data.get("transactions", []))
                all_records.extend(records)
                print(f"  Store {store}: {len(records):,} records")
            else:
                print(f"  Store {store}: HTTP {resp.status_code} — skipping")
        except Exception as e:
            print(f"  Store {store}: ERROR {e} — skipping")
        time.sleep(0.2)
    return all_records


def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    records = try_paginated()
    if records is None:
        records = try_per_store()

    if not records:
        print("ERROR: No records fetched. Check receiver connectivity.")
        sys.exit(1)

    transactions, line_items = parse_all(records)
    print(f"\nParsed {len(transactions):,} transactions, {len(line_items):,} line items")

    txn_path  = os.path.join(DATA_DIR, "pos_transactions.csv")
    item_path = os.path.join(DATA_DIR, "pos_line_items.csv")

    pd.DataFrame(transactions).to_csv(txn_path,  index=False)
    pd.DataFrame(line_items  ).to_csv(item_path, index=False)

    print(f"Saved: {txn_path}")
    print(f"Saved: {item_path}")
    print("Done.")


if __name__ == "__main__":
    main()
