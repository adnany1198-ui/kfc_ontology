"""
Pull POS data from Railway receiver into data/pos_transactions.csv and
data/pos_line_items.csv.

Strategies (set PULL_STRATEGY env var or edit STRATEGY below):
  stream    — stream /transactions, parse complete objects before connection drops,
              run N_PASSES to approach full coverage (default, no server changes needed)
  paginated — use /transactions?limit=N&offset=N (requires pagination patch deployed)
  postgres  — query Railway Postgres directly via RAILWAY_DB_URL env var
"""
import sys
import os
import json
import time
import requests
import pandas as pd

BASE_URL   = os.environ.get("KFC_RECEIVER_URL", "https://cv2-production-008f.up.railway.app")
DATA_DIR   = os.path.join(os.path.dirname(__file__), "..", "data")
PAGE_SIZE  = 5000
STRATEGY   = os.environ.get("PULL_STRATEGY", "stream")
N_PASSES   = int(os.environ.get("STREAM_PASSES", "4"))   # streaming passes for dedup coverage
CHUNK_SIZE = 1024 * 256                                   # 256 KB read chunks


def parse_transaction(raw_obj):
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


def parse_all(records, seen_ids=None):
    if seen_ids is None:
        seen_ids = set()
    transactions = []
    line_items   = []
    for rec in records:
        t, items = parse_transaction(rec)
        tid = t["transaction_id"]
        if not tid or tid in seen_ids:
            continue
        seen_ids.add(tid)
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
    return transactions, line_items, seen_ids


def extract_complete_objects(buf: bytes) -> list:
    """
    Extract all complete top-level JSON objects from a partial JSON array.
    Uses bracket-depth tracking so nested line_items arrays don't confuse us.
    Works regardless of whether the response is `[{...}]` or `{"data":[{...}]}`.
    """
    text = buf.decode("utf-8", errors="replace")

    # Peek at structure to find where the array of transactions starts
    peek = text[:500].lstrip()
    if peek.startswith("{"):
        # Wrapped response — find the array value
        array_start = text.find("[")
    else:
        array_start = text.find("[")

    if array_start == -1:
        print(f"    [debug] no '[' found in first 200 chars: {repr(text[:200])}", flush=True)
        return []

    objects = []
    i          = array_start + 1
    obj_start  = -1
    depth      = 0
    in_string  = False
    n          = len(text)

    while i < n:
        c = text[i]
        if in_string:
            if c == "\\":
                i += 2
                continue
            if c == '"':
                in_string = False
        else:
            if c == '"':
                in_string = True
            elif c == "{":
                if depth == 0:
                    obj_start = i
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0 and obj_start != -1:
                    try:
                        obj = json.loads(text[obj_start : i + 1])
                        objects.append(obj)
                    except json.JSONDecodeError:
                        pass
                    obj_start = -1
            elif c == "]" and depth == 0:
                break  # clean end of array
        i += 1

    return objects


def stream_pass(pass_num: int) -> list:
    """Single streaming pass: read until connection drops, parse what we got."""
    print(f"  Pass {pass_num}: opening stream...", flush=True)
    buf = bytearray()
    try:
        with requests.get(f"{BASE_URL}/transactions", stream=True, timeout=180) as resp:
            resp.raise_for_status()
            for chunk in resp.iter_content(chunk_size=CHUNK_SIZE):
                if chunk:
                    buf.extend(chunk)
            # Clean close — use same extractor for consistency
            records = extract_complete_objects(bytes(buf))
            mb = len(buf) / 1_000_000
            print(f"  Pass {pass_num}: clean finish — {mb:.1f} MB, {len(records):,} records", flush=True)
            return records
    except Exception as e:
        mb = len(buf) / 1_000_000
        print(f"  Pass {pass_num}: connection dropped at {mb:.1f} MB ({e.__class__.__name__}) — parsing partial", flush=True)
        records = extract_complete_objects(bytes(buf))
        print(f"  Pass {pass_num}: recovered {len(records):,} records from partial", flush=True)
        return records


def try_streaming(seen_ids: set = None) -> list:
    """Run N_PASSES streaming fetches and deduplicate against seen_ids."""
    print(f"Streaming strategy: {N_PASSES} passes with deduplication "
          f"(already have {len(seen_ids):,} unique IDs)", flush=True)
    if seen_ids is None:
        seen_ids = set()
    all_records   = []
    session_seen  = set(seen_ids)  # copy so we don't mutate caller's set
    for i in range(1, N_PASSES + 1):
        records = stream_pass(i)
        new_this_pass = 0
        for r in records:
            raw = r.get("raw", r)
            tid = raw.get("transaction_id") or r.get("transaction_id")
            if tid and tid not in session_seen:
                session_seen.add(tid)
                all_records.append(r)
                new_this_pass += 1
        print(f"  Pass {i}: +{new_this_pass:,} new | session unique: {len(session_seen):,}", flush=True)
        if i < N_PASSES:
            time.sleep(2)
    return all_records


def try_paginated() -> list:
    print("Paginated strategy: fetching via limit/offset...", flush=True)
    test = requests.get(f"{BASE_URL}/transactions", params={"limit": 1, "offset": 0}, timeout=20)
    test.raise_for_status()
    data = test.json()
    if not isinstance(data, dict) or "total" not in data:
        raise RuntimeError("Paginated endpoint not available — deploy 00b patch first")
    total = data["total"]
    print(f"  Total records: {total:,}", flush=True)
    all_records = []
    offset = 0
    while offset < total:
        resp = requests.get(f"{BASE_URL}/transactions",
                            params={"limit": PAGE_SIZE, "offset": offset}, timeout=60)
        resp.raise_for_status()
        page    = resp.json()
        records = page.get("data", page.get("transactions", []))
        all_records.extend(records)
        offset += len(records)
        print(f"  {offset:,}/{total:,}", end="\r", flush=True)
        if not records:
            break
        time.sleep(0.1)
    print(f"\n  Total fetched: {len(all_records):,}", flush=True)
    return all_records


def try_postgres() -> list:
    db_url = os.environ.get("RAILWAY_DB_URL")
    if not db_url:
        raise RuntimeError("RAILWAY_DB_URL not set")
    import psycopg2, psycopg2.extras
    print("Postgres strategy: connecting directly...", flush=True)
    conn = psycopg2.connect(db_url)
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT COUNT(*) AS n FROM transactions")
    total = cur.fetchone()["n"]
    print(f"  {total:,} rows in transactions table", flush=True)
    cur.execute("SELECT * FROM transactions ORDER BY timestamp")
    rows = cur.fetchall()
    conn.close()
    # Wrap each row as a flat dict (no raw wrapper needed)
    return [dict(r) for r in rows]


def load_existing(txn_path, item_path):
    """Load previously saved CSVs and return existing seen_ids set."""
    seen_ids = set()
    transactions = []
    line_items   = []
    if os.path.exists(txn_path):
        df = pd.read_csv(txn_path, low_memory=False)
        transactions = df.to_dict("records")
        seen_ids     = set(df["transaction_id"].dropna().astype(str).tolist())
        print(f"Loaded {len(transactions):,} existing transactions from disk", flush=True)
    if os.path.exists(item_path):
        df = pd.read_csv(item_path, low_memory=False)
        line_items = df.to_dict("records")
        print(f"Loaded {len(line_items):,} existing line items from disk", flush=True)
    return transactions, line_items, seen_ids


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    txn_path  = os.path.join(DATA_DIR, "pos_transactions.csv")
    item_path = os.path.join(DATA_DIR, "pos_line_items.csv")

    if STRATEGY == "postgres":
        records = try_postgres()
        existing_txns, existing_items, seen_ids = [], [], set()
    elif STRATEGY == "paginated":
        records = try_paginated()
        existing_txns, existing_items, seen_ids = [], [], set()
    else:
        # Incremental streaming: load what we already have, then add more passes
        existing_txns, existing_items, seen_ids = load_existing(txn_path, item_path)
        records = try_streaming(seen_ids=seen_ids)

    if not records and not existing_txns:
        print("ERROR: No records fetched.", flush=True)
        sys.exit(1)

    new_txns, new_items, seen_ids = parse_all(records, seen_ids=set() if STRATEGY != "stream" else seen_ids)
    all_txns  = existing_txns + new_txns
    all_items = existing_items + new_items
    print(f"\nTotal: {len(all_txns):,} transactions, {len(all_items):,} line items "
          f"(+{len(new_txns):,} new this run)", flush=True)

    pd.DataFrame(all_txns ).to_csv(txn_path,  index=False)
    pd.DataFrame(all_items).to_csv(item_path, index=False)
    print(f"Saved: {txn_path}")
    print(f"Saved: {item_path}")
    print("Done.")


if __name__ == "__main__":
    main()
