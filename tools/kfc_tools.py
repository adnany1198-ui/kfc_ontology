"""
KFC Pakistan AI Prototype — query and chart helpers.

Usage:
  from tools.kfc_tools import describe_schema, run_sql, list_stores, sample_rows, chart

CLI:
  python tools/kfc_tools.py schema [table]
  python tools/kfc_tools.py stores
  python tools/kfc_tools.py sample TABLE [n]
  python tools/kfc_tools.py sql 'SELECT ...'
"""
import os
import sys
import json
import duckdb

DATA_DIR   = os.path.join(os.path.dirname(__file__), "..", "data")
CHARTS_DIR = os.path.join(os.path.dirname(__file__), "..", "demo", "charts")
DB_PATH    = os.path.join(DATA_DIR, "kfc.duckdb")

READONLY_KEYWORDS = {"INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER", "TRUNCATE"}


def _connect():
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(
            f"Database not found at {DB_PATH}. Run scripts/06_load_duckdb.py first."
        )
    return duckdb.connect(DB_PATH, read_only=True)


def describe_schema(table=None):
    """Return markdown schema for all tables or a single table."""
    con = _connect()
    if table:
        cols = con.execute(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_name = ? ORDER BY ordinal_position",
            [table],
        ).fetchall()
        if not cols:
            con.close()
            return f"Table `{table}` not found."
        lines = [f"## {table}\n", "| column | type |", "|--------|------|"]
        for col, dtype in cols:
            lines.append(f"| {col} | {dtype} |")
        con.close()
        return "\n".join(lines)

    tables = con.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'main' ORDER BY table_name"
    ).fetchall()
    output = []
    for (tbl,) in tables:
        cols = con.execute(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_name = ? ORDER BY ordinal_position",
            [tbl],
        ).fetchall()
        output.append(f"## {tbl}\n")
        output.append("| column | type |")
        output.append("|--------|------|")
        for col, dtype in cols:
            output.append(f"| {col} | {dtype} |")
        output.append("")
    con.close()
    return "\n".join(output)


def run_sql(query, limit=100):
    """Execute a read-only SQL query. Returns {columns, rows, row_count, truncated}."""
    upper = query.strip().upper()
    for kw in READONLY_KEYWORDS:
        if kw in upper.split():
            raise ValueError(f"Mutating SQL not allowed ({kw}). Only SELECT queries permitted.")

    con = _connect()
    try:
        result = con.execute(query).fetchdf()
    finally:
        con.close()

    row_count = len(result)
    truncated = row_count > limit
    result    = result.head(limit)

    return {
        "columns":   list(result.columns),
        "rows":      result.values.tolist(),
        "row_count": row_count,
        "truncated": truncated,
    }


def list_stores():
    """Return stores with transaction counts."""
    return run_sql(
        "SELECT store_id, COUNT(*) AS n_transactions "
        "FROM pos_transactions GROUP BY store_id ORDER BY n_transactions DESC",
        limit=50,
    )


def sample_rows(table, n=5):
    """Return n sample rows from a table."""
    return run_sql(f"SELECT * FROM {table} USING SAMPLE {int(n)}", limit=n)


def chart(query, kind, title, x, y, filename):
    """
    Run query and save a chart to demo/charts/.
    kind: bar | line | scatter | hist
    x, y: column names (y can be a list for multi-series)
    filename: output filename (without path)
    Returns the full path to the saved file.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import pandas as pd

    os.makedirs(CHARTS_DIR, exist_ok=True)

    con = _connect()
    df  = con.execute(query).fetchdf()
    con.close()

    fig, ax = plt.subplots(figsize=(10, 5))
    y_cols = [y] if isinstance(y, str) else y

    if kind == "bar":
        for col in y_cols:
            ax.bar(df[x].astype(str), df[col], label=col, alpha=0.8)
        ax.set_xlabel(x)
        plt.xticks(rotation=45, ha="right")
    elif kind == "line":
        for col in y_cols:
            ax.plot(df[x].astype(str), df[col], marker="o", label=col)
        ax.set_xlabel(x)
        plt.xticks(rotation=45, ha="right")
    elif kind == "scatter":
        y_col = y_cols[0]
        ax.scatter(df[x], df[y_col], alpha=0.5)
        ax.set_xlabel(x)
        ax.set_ylabel(y_col)
    elif kind == "hist":
        ax.hist(df[x].dropna(), bins=30, edgecolor="black")
        ax.set_xlabel(x)
        ax.set_ylabel("Count")
    else:
        raise ValueError(f"Unknown chart kind: {kind}. Use bar/line/scatter/hist.")

    if len(y_cols) > 1:
        ax.legend()
    ax.set_title(title)
    ax.set_ylabel(y_cols[0] if kind != "hist" else "Count")
    plt.tight_layout()

    out_path = os.path.join(CHARTS_DIR, filename)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def _print_result(result):
    cols = result["columns"]
    rows = result["rows"]
    col_widths = [max(len(str(c)), max((len(str(r[i])) for r in rows), default=0))
                  for i, c in enumerate(cols)]
    sep  = " | ".join("-" * w for w in col_widths)
    header = " | ".join(str(c).ljust(w) for c, w in zip(cols, col_widths))
    print(header)
    print(sep)
    for row in rows:
        print(" | ".join(str(v).ljust(w) for v, w in zip(row, col_widths)))
    if result.get("truncated"):
        print(f"... (showing {len(rows)} of {result['row_count']} rows)")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(0)

    cmd = args[0].lower()
    if cmd == "schema":
        table = args[1] if len(args) > 1 else None
        print(describe_schema(table))
    elif cmd == "stores":
        _print_result(list_stores())
    elif cmd == "sample":
        if len(args) < 2:
            print("Usage: python tools/kfc_tools.py sample TABLE [n]")
            sys.exit(1)
        n = int(args[2]) if len(args) > 2 else 5
        _print_result(sample_rows(args[1], n))
    elif cmd == "sql":
        if len(args) < 2:
            print("Usage: python tools/kfc_tools.py sql 'SELECT ...'")
            sys.exit(1)
        _print_result(run_sql(args[1]))
    else:
        print(f"Unknown command: {cmd}")
        print("Commands: schema, stores, sample, sql")
        sys.exit(1)
