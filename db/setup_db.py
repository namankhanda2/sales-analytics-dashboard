"""
Loads the raw CSV with pandas, cleans it, and builds a SQLite database
with a clean `sales` table plus pre-aggregated views for fast dashboards.

Run: python db/setup_db.py
Writes: data/sales.db
"""

import sqlite3
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent.parent
DATA_DIR = BASE / "data"

CLEAN_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS sales (
    order_id        TEXT PRIMARY KEY,
    order_date      TEXT NOT NULL,
    year            INTEGER NOT NULL,
    month           INTEGER NOT NULL,
    region          TEXT NOT NULL,
    category        TEXT NOT NULL,
    product         TEXT NOT NULL,
    customer_segment TEXT NOT NULL,
    quantity        INTEGER NOT NULL,
    unit_price      REAL NOT NULL,
    discount        REAL NOT NULL,
    revenue         REAL NOT NULL,
    cost            REAL NOT NULL,
    profit          REAL NOT NULL
);
"""


def clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
    df = df.dropna(subset=["order_date"])

    df = df.drop_duplicates(subset=["order_id"])

    money_cols = ["unit_price", "revenue", "cost", "profit"]
    for col in money_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["revenue"])

    df = df[df["quantity"] > 0]
    df = df[df["revenue"] > 0]

    for col in ["region", "category", "product", "customer_segment"]:
        df[col] = df[col].astype(str).str.strip().str.title()

    df["revenue"] = df["revenue"].round(2)
    df["cost"] = df["cost"].round(2)
    df["profit"] = df["profit"].round(2)

    return df.reset_index(drop=True)


def build_views(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE VIEW IF NOT EXISTS v_monthly_sales AS
        SELECT
            year,
            month,
            printf('%04d-%02d', year, month) AS yearmonth,
            COUNT(*)                        AS order_count,
            SUM(quantity)                   AS units_sold,
            ROUND(SUM(revenue), 2)          AS revenue,
            ROUND(SUM(profit), 2)           AS profit
        FROM sales
        GROUP BY year, month;

        CREATE VIEW IF NOT EXISTS v_region_sales AS
        SELECT
            region,
            COUNT(*)            AS order_count,
            ROUND(AVG(revenue), 2) AS avg_order_value,
            ROUND(SUM(revenue), 2) AS revenue
        FROM sales
        GROUP BY region;

        CREATE VIEW IF NOT EXISTS v_category_sales AS
        SELECT
            category,
            SUM(quantity)         AS units_sold,
            ROUND(SUM(revenue), 2) AS revenue,
            ROUND(SUM(profit), 2)  AS profit
        FROM sales
        GROUP BY category;

        CREATE VIEW IF NOT EXISTS v_aggregates AS
        SELECT
            COUNT(DISTINCT order_id) AS total_orders,
            SUM(quantity)            AS total_units,
            ROUND(SUM(revenue), 2)   AS total_revenue,
            ROUND(AVG(revenue), 2)   AS avg_order_value,
            ROUND(SUM(profit), 2)    AS total_profit,
            ROUND(AVG(
                CASE WHEN revenue > 0 THEN (profit / revenue) END
            ), 4)                    AS profit_margin
        FROM sales;
        """
    )
    conn.commit()


def main() -> None:
    df = pd.read_csv(DATA_DIR / "sales.csv")
    print(f"Raw rows: {len(df)}")

    df = clean(df)
    print(f"Clean rows: {len(df)}")

    df["year"] = df["order_date"].dt.year
    df["month"] = df["order_date"].dt.month
    df["order_date"] = df["order_date"].dt.strftime("%Y-%m-%d")

    db_path = DATA_DIR / "sales.db"
    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(db_path)
    conn.execute(CLEAN_TABLE_SQL)
    df.to_sql("sales", conn, if_exists="replace", index=False)
    build_views(conn)
    conn.close()

    print(f"Database written -> {db_path}")


if __name__ == "__main__":
    main()