"""
Documentation: code to add to the Railway receiver to support pagination.

Run this script to print both Flask and FastAPI versions of the patch.
Add the appropriate routes to your Railway receiver and redeploy.

New endpoints added:
  GET /stats              — row count, date range, stores
  GET /schema             — column names and types
  GET /transactions?limit=N&offset=N  — paginated dump
  GET /sample?n=N         — random sample of N rows
"""

FLASK_PATCH = '''
# ── PAGINATION PATCH (Flask) ──────────────────────────────────────────────────
# Add these routes to your existing Flask app.
# Assumes you have a `get_db_connection()` helper and a `transactions` table.

from flask import jsonify, request

@app.route("/stats")
def stats():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            COUNT(*)                        AS total_rows,
            MIN(timestamp)                  AS earliest,
            MAX(timestamp)                  AS latest,
            COUNT(DISTINCT store_id)        AS n_stores,
            COUNT(DISTINCT transaction_id)  AS n_transactions
        FROM transactions
    """)
    row = cur.fetchone()
    cols = [d[0] for d in cur.description]
    conn.close()
    return jsonify(dict(zip(cols, row)))


@app.route("/schema")
def schema():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'transactions'
        ORDER BY ordinal_position
    """)
    rows = cur.fetchall()
    conn.close()
    return jsonify([{"column": r[0], "type": r[1]} for r in rows])


@app.route("/transactions")
def transactions_paginated():
    limit  = min(int(request.args.get("limit",  5000)), 10000)
    offset = int(request.args.get("offset", 0))
    store_id = request.args.get("store_id")
    till_id  = request.args.get("till_id")

    conn = get_db_connection()
    cur  = conn.cursor()

    where_clauses = []
    params = []
    if store_id:
        where_clauses.append("store_id = %s")
        params.append(store_id)
    if till_id:
        where_clauses.append("till_id = %s")
        params.append(till_id)

    where = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
    params += [limit, offset]

    cur.execute(f"""
        SELECT * FROM transactions
        {where}
        ORDER BY timestamp
        LIMIT %s OFFSET %s
    """, params)

    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]

    cur.execute(f"SELECT COUNT(*) FROM transactions {where}", params[:-2])
    total = cur.fetchone()[0]

    conn.close()
    return jsonify({
        "total":  total,
        "limit":  limit,
        "offset": offset,
        "count":  len(rows),
        "data":   rows,
    })


@app.route("/sample")
def sample():
    n = min(int(request.args.get("n", 100)), 1000)
    conn = get_db_connection()
    cur  = conn.cursor()
    cur.execute("SELECT * FROM transactions ORDER BY RANDOM() LIMIT %s", (n,))
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    conn.close()
    return jsonify(rows)
# ── END PAGINATION PATCH (Flask) ─────────────────────────────────────────────
'''

FASTAPI_PATCH = '''
# ── PAGINATION PATCH (FastAPI) ────────────────────────────────────────────────
# Add these routes to your existing FastAPI app.

from fastapi import Query
from typing import Optional

@app.get("/stats")
async def stats(db=Depends(get_db)):
    result = await db.fetch_one("""
        SELECT
            COUNT(*)                        AS total_rows,
            MIN(timestamp)                  AS earliest,
            MAX(timestamp)                  AS latest,
            COUNT(DISTINCT store_id)        AS n_stores,
            COUNT(DISTINCT transaction_id)  AS n_transactions
        FROM transactions
    """)
    return dict(result)


@app.get("/schema")
async def schema(db=Depends(get_db)):
    rows = await db.fetch_all("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = \'transactions\'
        ORDER BY ordinal_position
    """)
    return [{"column": r["column_name"], "type": r["data_type"]} for r in rows]


@app.get("/transactions")
async def transactions_paginated(
    limit:    int = Query(default=5000, le=10000),
    offset:   int = Query(default=0, ge=0),
    store_id: Optional[str] = None,
    till_id:  Optional[str] = None,
    db=Depends(get_db),
):
    filters = []
    values  = {}
    if store_id:
        filters.append("store_id = :store_id")
        values["store_id"] = store_id
    if till_id:
        filters.append("till_id = :till_id")
        values["till_id"] = till_id

    where = ("WHERE " + " AND ".join(filters)) if filters else ""
    values.update({"limit": limit, "offset": offset})

    rows = await db.fetch_all(
        f"SELECT * FROM transactions {where} ORDER BY timestamp LIMIT :limit OFFSET :offset",
        values=values,
    )
    total_row = await db.fetch_one(
        f"SELECT COUNT(*) AS c FROM transactions {where}",
        values={k: v for k, v in values.items() if k not in ("limit", "offset")},
    )
    return {
        "total":  total_row["c"],
        "limit":  limit,
        "offset": offset,
        "count":  len(rows),
        "data":   [dict(r) for r in rows],
    }


@app.get("/sample")
async def sample(n: int = Query(default=100, le=1000), db=Depends(get_db)):
    rows = await db.fetch_all(
        "SELECT * FROM transactions ORDER BY RANDOM() LIMIT :n", values={"n": n}
    )
    return [dict(r) for r in rows]
# ── END PAGINATION PATCH (FastAPI) ───────────────────────────────────────────
'''

if __name__ == "__main__":
    print("=" * 72)
    print("FLASK VERSION")
    print("=" * 72)
    print(FLASK_PATCH)
    print()
    print("=" * 72)
    print("FASTAPI VERSION")
    print("=" * 72)
    print(FASTAPI_PATCH)
    print()
    print("Add the appropriate block to your Railway receiver and redeploy.")
    print("Then 01_pull_pos.py will use paginated fetching automatically.")
