"""
Sales & Revenue Analytics Dashboard (Streamlit)

Run locally :  streamlit run app.py
Deployed on :  Streamlit Community Cloud
"""

import sqlite3
from datetime import date
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

BASE = Path(__file__).resolve().parent
DB_PATH = BASE / "data" / "sales.db"

st.set_page_config(page_title="Sales & Revenue Analytics", layout="wide")


@st.cache_resource
def get_connection():
    if not DB_PATH.exists():
        st.error(f"Database not found at {DB_PATH}. Run `python db/setup_db.py` first.")
        st.stop()
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def query(sql: str, params: tuple = ()) -> pd.DataFrame:
    return pd.read_sql_query(sql, get_connection(), params=params)


@st.cache_data(ttl=300)
def load_filter_options():
    return query(
        """
        SELECT
            MIN(order_date) AS min_date,
            MAX(order_date) AS max_date,
            region, category, customer_segment
        FROM sales
        GROUP BY region, category, customer_segment
        """
    )


def build_where(filters: dict) -> tuple:
    clauses, params = [], []
    if filters.get("regions"):
        clauses.append("region IN (%s)" % ",".join("?" * len(filters["regions"])))
        params.extend(filters["regions"])
    if filters.get("categories"):
        clauses.append("category IN (%s)" % ",".join("?" * len(filters["categories"])))
        params.extend(filters["categories"])
    if filters.get("segments"):
        clauses.append("customer_segment IN (%s)" % ",".join("?" * len(filters["segments"])))
        params.extend(filters["segments"])
    if filters.get("start"):
        clauses.append("order_date >= ?")
        params.append(filters["start"])
    if filters.get("end"):
        clauses.append("order_date <= ?")
        params.append(filters["end"])
    where = "WHERE " + " AND ".join(clauses) if clauses else ""
    return where, params


# ------------------------------------------------------------------
# Load filter options + build sidebar
# ------------------------------------------------------------------
options = load_filter_options()

st.sidebar.title("Filters")

regions = st.sidebar.multiselect("Region", options["region"].unique().tolist())
categories = st.sidebar.multiselect("Category", options["category"].unique().tolist())
segments = st.sidebar.multiselect("Customer Segment", options["customer_segment"].unique().tolist())

min_date = pd.to_datetime(options["min_date"].iloc[0]).date()
max_date = pd.to_datetime(options["max_date"].iloc[0]).date()
date_range = st.sidebar.date_input(
    "Order date range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)

filters = {
    "regions": regions,
    "categories": categories,
    "segments": segments,
    "start": date_range[0].isoformat(),
    "end": date_range[1].isoformat(),
}
where, params = build_where(filters)

# ------------------------------------------------------------------
# KPI cards
# ------------------------------------------------------------------
kpiv = query(
    f"""
    SELECT
        COUNT(*)                    AS total_orders,
        SUM(quantity)               AS total_units,
        ROUND(SUM(revenue), 2)      AS total_revenue,
        ROUND(AVG(revenue), 2)      AS avg_order_value,
        ROUND(SUM(profit), 2)       AS total_profit,
        ROUND(SUM(profit) / SUM(revenue) * 100, 2) AS profit_margin_pct
    FROM sales {where}
    """,
    params,
).iloc[0]

st.title("Sales & Revenue Analytics Dashboard")
st.caption("SQL queries + pandas cleaning + Streamlit + Plotly")

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total Revenue", f"${kpiv['total_revenue']:,.0f}")
c2.metric("Total Orders", f"{kpiv['total_orders']:,.0f}")
c3.metric("Avg Order Value", f"${kpiv['avg_order_value']:,.2f}")
c4.metric("Total Profit", f"${kpiv['total_profit']:,.0f}")
c5.metric("Profit Margin", f"{kpiv['profit_margin_pct']:.1f}%")

st.divider()

# ------------------------------------------------------------------
# Monthly revenue & profit trend
# ------------------------------------------------------------------
st.subheader("Revenue & Profit Trend")
trend = query(
    f"""
    SELECT
        printf('%04d-%02d', year, month) AS yearmonth,
        SUM(revenue) AS revenue,
        SUM(profit)  AS profit
    FROM sales
    {where}
    GROUP BY year, month
    ORDER BY yearmonth
    """,
    params,
)

fig_trend = go.Figure()
fig_trend.add_trace(
    go.Scatter(x=trend["yearmonth"], y=trend["revenue"], name="Revenue",
               mode="lines+markers", line=dict(color="#2E86AB", width=2))
)
fig_trend.add_trace(
    go.Scatter(x=trend["yearmonth"], y=trend["profit"], name="Profit",
               mode="lines+markers", line=dict(color="#16A085", width=2))
)
fig_trend.update_layout(
    xaxis_title="Month", yaxis_title="Amount ($)", height=380,
    hovermode="x unified", margin=dict(l=10, r=10, t=30, b=10),
)
st.plotly_chart(fig_trend, use_container_width=True)

# ------------------------------------------------------------------
# Region + category breakdown
# ------------------------------------------------------------------
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Revenue by Region")
    region_df = query(
        f"""
        SELECT region,
               COUNT(*)            AS orders,
               ROUND(SUM(revenue), 2) AS revenue,
               ROUND(AVG(revenue), 2) AS avg_order_value
        FROM sales
        {where}
        GROUP BY region
        ORDER BY revenue DESC
        """,
        params,
    )
    fig_region = px.bar(
        region_df, x="region", y="revenue", color="region", text_auto=".2s"
    )
    fig_region.update_layout(showlegend=False, height=360, margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fig_region, use_container_width=True)

with col_right:
    st.subheader("Revenue by Category")
    cat_df = query(
        f"""
        SELECT category,
               SUM(quantity)         AS units_sold,
               ROUND(SUM(revenue), 2) AS revenue,
               ROUND(SUM(profit), 2)  AS profit
        FROM sales
        {where}
        GROUP BY category
        ORDER BY revenue DESC
        """,
        params,
    )
    fig_cat = px.bar(
        cat_df, x="category", y="revenue", color="category", text_auto=".2s"
    )
    fig_cat.update_layout(showlegend=False, height=360, margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fig_cat, use_container_width=True)

# ------------------------------------------------------------------
# Top products + segment share
# ------------------------------------------------------------------
col_left2, col_right2 = st.columns(2)

with col_left2:
    st.subheader("Top 10 Products by Revenue")
    top_products = query(
        f"""
        SELECT product,
               category,
               SUM(quantity)          AS units_sold,
               ROUND(SUM(revenue), 2) AS revenue
        FROM sales
        {where}
        GROUP BY product
        ORDER BY revenue DESC
        LIMIT 10
        """,
        params,
    )
    fig_products = px.bar(
        top_products,
        x="revenue",
        y="product",
        orientation="h",
        color="category",
        text_auto=".2s",
    )
    fig_products.update_layout(height=420, margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fig_products, use_container_width=True)

with col_right2:
    st.subheader("Revenue Share by Customer Segment")
    seg_df = query(
        f"""
        SELECT customer_segment,
               ROUND(SUM(revenue), 2) AS revenue
        FROM sales
        {where}
        GROUP BY customer_segment
        """,
        params,
    )
    fig_seg = px.pie(seg_df, names="customer_segment", values="revenue", hole=0.45)
    fig_seg.update_layout(height=420, margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fig_seg, use_container_width=True)

st.divider()

# ------------------------------------------------------------------
# Raw data table
# ------------------------------------------------------------------
with st.expander("View underlying SQL query data"):
    sample = query(
        f"""
        SELECT order_id, order_date, region, category, product,
               customer_segment, quantity, revenue, profit
        FROM sales
        {where}
        ORDER BY order_date DESC
        LIMIT 500
        """,
        params,
    )
    st.dataframe(sample, use_container_width=True, height=320)

st.caption(
    "Built with Python (pandas + SQL + Plotly) and Streamlit. "
    "Source data: data/sales.csv -> cleaned & loaded via db/setup_db.py."
)