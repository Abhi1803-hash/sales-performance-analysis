"""
sales_analysis.py
-----------------
End-to-end sales analysis with pandas + matplotlib/seaborn.

Steps
    1. Load the star-schema CSVs and merge into one analytical table
    2. Clean: drop duplicates, fill missing channel, flag returns
    3. Feature engineering: year, month, margin, ship days, discount band
    4. KPIs, trends, category/region/segment breakdowns
    5. Customer analytics: Pareto + RFM segmentation
    6. Save charts to ../images and a summary to ../data/kpi_summary.csv

Run:
    python python/sales_analysis.py
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd
import seaborn as sns

ROOT = Path(__file__).resolve().parent.parent
DATA, IMG = ROOT / "data", ROOT / "images"
IMG.mkdir(exist_ok=True)

sns.set_theme(style="whitegrid", font_scale=1.0)
PALETTE = ["#1F4E79", "#2E86AB", "#F18F01", "#C73E1D", "#6C757D"]
plt.rcParams.update({"figure.dpi": 110, "axes.titleweight": "bold",
                     "axes.spines.top": False, "axes.spines.right": False})


def crore(x, _=None):
    """Format rupees in crores (1 Cr = 10 million)."""
    return f"₹{x / 1e7:.1f} Cr"


def lakh(x, _=None):
    return f"₹{x / 1e5:.0f} L"


def save(fig, name):
    fig.tight_layout()
    fig.savefig(IMG / name, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved images/{name}")


# ------------------------------------------------------------------ 1. load
def load() -> pd.DataFrame:
    fact = pd.read_csv(DATA / "fact_sales.csv", parse_dates=["order_date", "ship_date"])
    prod = pd.read_csv(DATA / "dim_products.csv")
    cust = pd.read_csv(DATA / "dim_customers.csv")
    reg = pd.read_csv(DATA / "dim_regions.csv")
    reps = pd.read_csv(DATA / "dim_sales_reps.csv")

    df = (fact
          .merge(prod.drop(columns="unit_price"), on="product_id", how="left")
          .merge(cust[["customer_id", "segment", "city"]], on="customer_id", how="left")
          .merge(reg[["region_id", "region_name"]], on="region_id", how="left")
          .merge(reps[["rep_id", "rep_name"]], on="rep_id", how="left"))
    return df


# ------------------------------------------------------------------ 2. clean
def clean(df: pd.DataFrame) -> pd.DataFrame:
    print("\n[Data quality]")
    print(f"  rows: {len(df):,}  |  duplicate order_ids: {df.duplicated('order_id').sum()}")
    print(f"  missing values:\n{df.isna().sum()[lambda s: s > 0].to_string()}")

    df = df.drop_duplicates("order_id").copy()
    df["channel"] = df["channel"].fillna("Unknown")

    # 3. feature engineering
    df["year"] = df["order_date"].dt.year
    df["month"] = df["order_date"].dt.to_period("M")
    df["month_name"] = df["order_date"].dt.strftime("%b")
    df["quarter"] = "Q" + df["order_date"].dt.quarter.astype(str)
    df["ship_days"] = (df["ship_date"] - df["order_date"]).dt.days
    df["margin_pct"] = df["profit"] / df["sales_amount"]
    df["discount_band"] = pd.cut(df["discount_pct"], [-0.01, 0, 0.10, 0.20, 1],
                                 labels=["No discount", "1-10%", "11-20%", ">20%"])
    print(f"  clean rows: {len(df):,}")
    return df


# ------------------------------------------------------------------ 4. KPIs
def kpis(sales: pd.DataFrame, all_orders: pd.DataFrame) -> pd.DataFrame:
    by_year = sales.groupby("year").agg(revenue=("sales_amount", "sum"),
                                        profit=("profit", "sum"),
                                        orders=("order_id", "nunique"),
                                        customers=("customer_id", "nunique"))
    by_year["aov"] = by_year["revenue"] / by_year["orders"]
    by_year["margin_pct"] = by_year["profit"] / by_year["revenue"] * 100
    by_year["return_rate_pct"] = all_orders.groupby("year")["is_returned"].mean() * 100
    yoy = by_year.pct_change().iloc[-1] * 100

    print("\n[KPIs by year]")
    print(by_year.round(1).to_string())
    print("\n[YoY change 2025 vs 2024, %]")
    print(yoy.round(1).to_string())
    by_year.round(2).to_csv(DATA / "kpi_summary.csv")
    return by_year


# ------------------------------------------------------------------ charts
def chart_monthly_trend(s):
    m = s.groupby("month")["sales_amount"].sum()
    m.index = m.index.to_timestamp()
    fig, ax = plt.subplots(figsize=(11, 4.5))
    ax.plot(m.index, m.values, marker="o", color=PALETTE[0], lw=2, label="Monthly revenue")
    ax.plot(m.index, m.rolling(3).mean(), ls="--", color=PALETTE[2], lw=2, label="3-month avg")
    peak = m.idxmax()
    ax.annotate(f"Peak: {crore(m.max())}", (peak, m.max()), xytext=(-110, 5),
                textcoords="offset points", fontsize=9, color=PALETTE[3])
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(crore))
    ax.set(title="Monthly Revenue Trend (2024–2025)", xlabel="", ylabel="Revenue")
    ax.legend(frameon=False)
    save(fig, "01_monthly_revenue_trend.png")


def chart_yoy_month(s):
    p = s.pivot_table(index="month_name", columns="year", values="sales_amount", aggfunc="sum")
    order = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    p = p.reindex(order)
    fig, ax = plt.subplots(figsize=(11, 4.5))
    p.plot(kind="bar", ax=ax, color=[PALETTE[4], PALETTE[0]], width=0.75)
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(crore))
    ax.set(title="Revenue by Month: 2025 vs 2024", xlabel="", ylabel="Revenue")
    ax.tick_params(axis="x", rotation=0)
    ax.legend(title="", frameon=False)
    save(fig, "02_yoy_by_month.png")


def chart_category(s):
    c = (s.groupby(["category", "sub_category"])
           .agg(revenue=("sales_amount", "sum"), profit=("profit", "sum"))
           .assign(margin=lambda d: d.profit / d.revenue * 100)
           .sort_values("revenue"))
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharey=True)
    labels = [f"{a} · {b}" for a, b in c.index]
    colors = c.index.get_level_values(0).map(
        {"Electronics": PALETTE[0], "Furniture": PALETTE[2], "Office Supplies": PALETTE[1]})
    axes[0].barh(labels, c.revenue, color=colors)
    axes[0].xaxis.set_major_formatter(mtick.FuncFormatter(crore))
    axes[0].set_title("Revenue by Sub-category")
    axes[1].barh(labels, c.margin, color=colors)
    axes[1].xaxis.set_major_formatter(mtick.PercentFormatter())
    axes[1].set_title("Profit Margin by Sub-category")
    for i, v in enumerate(c.margin):
        axes[1].text(v + 0.5, i, f"{v:.1f}%", va="center", fontsize=8)
    save(fig, "03_category_revenue_margin.png")


def chart_region_segment(s):
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    r = s.groupby("region_name")["sales_amount"].sum().sort_values(ascending=False)
    axes[0].bar(r.index, r.values, color=PALETTE[0])
    axes[0].yaxis.set_major_formatter(mtick.FuncFormatter(crore))
    axes[0].set_title("Revenue by Region")
    for i, v in enumerate(r.values):
        axes[0].text(i, v, f"{v / r.sum():.0%}", ha="center", va="bottom", fontsize=9)

    seg = s.pivot_table(index="segment", columns="channel", values="sales_amount",
                        aggfunc="sum").drop(columns="Unknown", errors="ignore")
    seg.plot(kind="bar", stacked=True, ax=axes[1], color=PALETTE[:3])
    axes[1].yaxis.set_major_formatter(mtick.FuncFormatter(crore))
    axes[1].set(title="Revenue by Segment & Channel", xlabel="")
    axes[1].tick_params(axis="x", rotation=0)
    axes[1].legend(frameon=False, fontsize=8)
    save(fig, "04_region_segment.png")


def chart_discount(s):
    d = (s.groupby("discount_pct")
           .agg(orders=("order_id", "count"), revenue=("sales_amount", "sum"),
                profit=("profit", "sum"))
           .assign(margin=lambda x: x.profit / x.revenue * 100))
    fig, ax = plt.subplots(figsize=(9, 4.5))
    colors = [PALETTE[3] if m < 0 else PALETTE[0] for m in d.margin]
    ax.bar([f"{v:.0%}" for v in d.index], d.margin, color=colors)
    ax.axhline(0, color="black", lw=0.8)
    ax.yaxis.set_major_formatter(mtick.PercentFormatter())
    for i, (m, n) in enumerate(zip(d.margin, d.orders)):
        ax.text(i, m + (0.6 if m >= 0 else -1.8), f"{m:.1f}%\n({n:,} orders)",
                ha="center", fontsize=8)
    ax.set(title="Profit Margin by Discount Level", xlabel="Discount", ylabel="Margin")
    save(fig, "05_discount_vs_margin.png")


def chart_reps(s, reps):
    r = (s[s.year == 2025].groupby("rep_id")["sales_amount"].sum()
         .rename("revenue").reset_index().merge(reps, on="rep_id"))
    r["achievement"] = r.revenue / r.annual_target * 100
    r = r.sort_values("achievement")
    fig, ax = plt.subplots(figsize=(9, 5.5))
    colors = [PALETTE[0] if a >= 100 else PALETTE[3] for a in r.achievement]
    ax.barh(r.rep_name, r.achievement, color=colors)
    ax.axvline(100, color="black", ls="--", lw=1)
    ax.text(101, -0.8, "Target", fontsize=8)
    ax.xaxis.set_major_formatter(mtick.PercentFormatter())
    ax.set(title="Sales Rep Target Achievement (2025)", xlabel="% of annual target")
    save(fig, "06_rep_target_achievement.png")


# ------------------------------------------------------------------ 5. customers
def pareto(s):
    c = s.groupby("customer_id")["sales_amount"].sum().sort_values(ascending=False)
    cum = c.cumsum() / c.sum() * 100
    x = np.arange(1, len(c) + 1) / len(c) * 100
    top20 = cum.iloc[int(len(c) * 0.2) - 1]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(x, cum.values, color=PALETTE[0], lw=2)
    ax.axvline(20, color=PALETTE[2], ls="--")
    ax.axhline(top20, color=PALETTE[2], ls="--")
    ax.text(22, top20 - 8, f"Top 20% of customers = {top20:.0f}% of revenue", fontsize=9)
    ax.xaxis.set_major_formatter(mtick.PercentFormatter())
    ax.yaxis.set_major_formatter(mtick.PercentFormatter())
    ax.set(title="Customer Revenue Concentration (Pareto)",
           xlabel="% of customers", ylabel="Cumulative % of revenue")
    save(fig, "07_pareto_customers.png")
    return top20


def rfm(s) -> pd.DataFrame:
    ref = s.order_date.max() + pd.Timedelta(days=1)
    r = s.groupby("customer_id").agg(
        recency=("order_date", lambda d: (ref - d.max()).days),
        frequency=("order_id", "nunique"),
        monetary=("sales_amount", "sum"))
    r["R"] = pd.qcut(r.recency, 4, labels=[4, 3, 2, 1]).astype(int)
    r["F"] = pd.qcut(r.frequency.rank(method="first"), 4, labels=[1, 2, 3, 4]).astype(int)
    r["M"] = pd.qcut(r.monetary, 4, labels=[1, 2, 3, 4]).astype(int)

    def label(row):
        if row.R >= 3 and row.F >= 3 and row.M >= 3:
            return "Champions"
        if row.R >= 3 and row.F >= 2:
            return "Loyal"
        if row.R >= 3:
            return "Promising"
        if row.R == 2:
            return "Needs Attention"
        return "At Risk"

    r["segment"] = r.apply(label, axis=1)
    summary = (r.groupby("segment")
                .agg(customers=("R", "size"), avg_recency=("recency", "mean"),
                     avg_orders=("frequency", "mean"), revenue=("monetary", "sum"))
                .sort_values("revenue", ascending=False))
    summary["revenue_share_pct"] = summary.revenue / summary.revenue.sum() * 100
    print("\n[RFM segments]")
    print(summary.round(1).to_string())
    r.to_csv(DATA / "rfm_scores.csv")

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar(summary.index, summary.customers, color=PALETTE[1])
    ax2 = ax.twinx()
    ax2.plot(summary.index, summary.revenue_share_pct, color=PALETTE[3], marker="o", lw=2)
    ax2.yaxis.set_major_formatter(mtick.PercentFormatter())
    ax2.grid(False)
    ax.set(title="RFM Segments: Customers vs Revenue Share", ylabel="Customers")
    ax2.set_ylabel("Revenue share", color=PALETTE[3])
    save(fig, "08_rfm_segments.png")
    return summary


# ------------------------------------------------------------------ main
def main():
    df = clean(load())
    sales = df[~df.is_returned]          # net sales excludes returned orders
    reps = pd.read_csv(DATA / "dim_sales_reps.csv")

    by_year = kpis(sales, df)

    print("\n[Charts]")
    chart_monthly_trend(sales)
    chart_yoy_month(sales)
    chart_category(sales)
    chart_region_segment(sales)
    chart_discount(sales)
    chart_reps(sales, reps)
    top20 = pareto(sales)
    rfm(sales)

    # Key insights printed for the README / report
    cat = sales.groupby("category")[["sales_amount", "profit"]].sum()
    cat["margin"] = cat.profit / cat.sales_amount * 100
    yoy = (by_year.revenue.iloc[-1] / by_year.revenue.iloc[0] - 1) * 100
    q4 = sales[sales.order_date.dt.month.isin([10, 11, 12])].sales_amount.sum() / sales.sales_amount.sum()
    print("\n[Key insights]")
    print(f"  • Revenue grew {yoy:.1f}% YoY (2025 vs 2024).")
    print(f"  • Q4 (Oct–Dec festive season) contributes {q4:.0%} of revenue.")
    print(f"  • Electronics drives {cat.sales_amount['Electronics'] / cat.sales_amount.sum():.0%} "
          f"of revenue but has the lowest margin ({cat.margin['Electronics']:.1f}%).")
    print(f"  • Top 20% of customers generate {top20:.0f}% of revenue.")
    print("  • Discounts above 20% make orders loss-making.")


if __name__ == "__main__":
    main()
