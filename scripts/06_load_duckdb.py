"""
Load all CSV files into data/kfc.duckdb.
Drops and recreates the database. Runs a sanity-check JOIN at the end.
"""
import os
import sys
import duckdb

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
DB_PATH  = os.path.join(DATA_DIR, "kfc.duckdb")

TABLES = {
    "pos_transactions":  "pos_transactions.csv",
    "pos_line_items":    "pos_line_items.csv",
    "menu_items":        "menu_items.csv",
    "store_summary":     "store_summary.csv",
    "prism_observations":"prism_observations.csv",
    "inventory_movements":"inventory_movements.csv",
    "procurement_prices":"procurement_prices.csv",
}


def main():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"Dropped existing {DB_PATH}")

    con = duckdb.connect(DB_PATH)
    print(f"Created {DB_PATH}")

    for table, csv_file in TABLES.items():
        csv_path = os.path.join(DATA_DIR, csv_file)
        if not os.path.exists(csv_path):
            print(f"  SKIP {table}: {csv_path} not found")
            continue
        con.execute(f"""
            CREATE TABLE {table} AS
            SELECT * FROM read_csv_auto('{csv_path}', sample_size=-1)
        """)
        count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  Loaded {table}: {count:,} rows")

    print("\nRunning sanity-check JOIN (POS ⨝ Prism by age_band)...")
    try:
        result = con.execute("""
            SELECT
                p.age_band,
                COUNT(*)                         AS n_observations,
                ROUND(AVG(t.basket_value), 2)    AS avg_basket_pkr,
                ROUND(AVG(t.item_count),   2)    AS avg_items
            FROM prism_observations p
            JOIN pos_transactions t
              ON p.transaction_id = t.transaction_id
             AND p.store_id       = t.store_id
            GROUP BY p.age_band
            ORDER BY p.age_band
        """).fetchdf()
        print(result.to_string(index=False))
    except Exception as e:
        print(f"  Sanity-check failed: {e}")

    print("\nTable summary:")
    for table in TABLES:
        try:
            count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"  {table:<25} {count:>10,} rows")
        except Exception:
            print(f"  {table:<25} not loaded")

    con.close()
    print(f"\nDone. Database at {DB_PATH}")


if __name__ == "__main__":
    main()
