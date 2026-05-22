"""
Confirm the Railway POS receiver is alive and returning data.
Usage: python scripts/00_confirm_webhook.py [base_url]
"""
import sys
import json
import os
import requests

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "https://cv2-production-008f.up.railway.app"


def check_http():
    print(f"Checking HTTP receiver at {BASE_URL} ...")

    try:
        r = requests.get(f"{BASE_URL}/", timeout=15)
        r.raise_for_status()
        status = r.json()
        print(f"  / -> OK  ({r.status_code})")
        print(f"  Row count : {status.get('count', status.get('row_count', 'n/a'))}")
        print(f"  Latest txn: {status.get('latest_transaction', status.get('latest', 'n/a'))}")
    except requests.exceptions.ConnectionError:
        print("  UNREACHABLE — connection refused or DNS failure")
        return False
    except requests.exceptions.Timeout:
        print("  TIMEOUT — receiver may be overloaded")
        return False
    except Exception as e:
        print(f"  ERROR: {e}")
        return False

    try:
        r2 = requests.get(f"{BASE_URL}/latest", timeout=15)
        r2.raise_for_status()
        data = r2.json()
        txns = data if isinstance(data, list) else data.get("transactions", data.get("data", []))
        print(f"\n  /latest -> {len(txns)} transactions returned")
        if txns:
            t = txns[0]
            raw = t.get("raw", t)
            print(f"  Sample: store={raw.get('store_id')} ts={raw.get('timestamp')} basket={raw.get('basket_value')}")
    except Exception as e:
        print(f"  /latest ERROR: {e}")

    return True


def check_postgres():
    db_url = os.environ.get("RAILWAY_DB_URL")
    if not db_url:
        print("\nPostgres check: RAILWAY_DB_URL not set — skipping")
        return

    try:
        import psycopg2
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
        tables = [r[0] for r in cur.fetchall()]
        print(f"\nPostgres check: connected. Tables: {tables}")
        for t in tables:
            cur.execute(f"SELECT COUNT(*) FROM {t}")
            count = cur.fetchone()[0]
            print(f"  {t}: {count:,} rows")
        conn.close()
    except ImportError:
        print("\nPostgres check: psycopg2 not installed — skipping")
    except Exception as e:
        print(f"\nPostgres check ERROR: {e}")


if __name__ == "__main__":
    alive = check_http()
    check_postgres()
    if not alive:
        print("\nReceiver UNREACHABLE. Cannot proceed.")
        sys.exit(1)
    else:
        print("\nReceiver OK.")
