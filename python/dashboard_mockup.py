"""
dashboard_mockup.py
-------------------
Renders a static preview of the Power BI "Executive Overview" page from the
real data, so the repo shows the dashboard design without needing a .pbix.

Run:
    python python/dashboard_mockup.py
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
from matplotlib.patches import FancyBboxPatch
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA, IMG = ROOT / "data", ROOT / "images"
C = {"navy": "#1F4E79", "blue": "#2E86AB", "orange": "#F18F01", "red": "#C73E1D",
     "grey": "#6C757D", "bg": "#F4F6F9", "card": "#FFFFFF", "line": "#E5E8EC"}

f = pd.read_csv(DATA / "fact_sales.csv", parse_dates=["order_date"]).drop_duplicates("order_id")
f = f.merge(pd.read_csv(DATA / "dim_products.csv")[["product_id", "sub_category"]], on="product_id")
f = f.merge(pd.read_csv(DATA / "dim_regions.csv"), on="region_id")
s = f[~f.is_returned]

rev, prof = s.sales_amount.sum(), s.profit.sum()
orders = s.order_id.nunique()
y = s.groupby(s.order_date.dt.year).sales_amount.sum()
kpis = [("Total Revenue", f"₹{rev / 1e7:.2f} Cr"), ("Total Profit", f"₹{prof / 1e7:.2f} Cr"),
        ("Profit Margin", f"{prof / rev:.1%}"), ("Total Orders", f"{orders:,}"),
        ("Avg Order Value", f"₹{rev / orders:,.0f}"), ("Revenue YoY", f"+{y[2025] / y[2024] - 1:.1%}")]

fig = plt.figure(figsize=(16, 9), facecolor=C["bg"])


def panel(x, y_, w, h):
    fig.patches.append(FancyBboxPatch((x, y_), w, h, boxstyle="round,pad=0,rounding_size=0.006",
                                      transform=fig.transFigure, fc=C["card"], ec=C["line"], lw=1, zorder=-1))


# Header + slicers
fig.text(0.02, 0.945, "Sales Performance Dashboard", fontsize=20, weight="bold", color="#1B1B1B")
fig.text(0.02, 0.915, "Executive Overview · 2024–2025 · Net of returns", fontsize=10, color=C["grey"])
for i, sl in enumerate(["Year: All", "Region: All", "Segment: All", "Channel: All"]):
    x = 0.60 + i * 0.097
    panel(x, 0.915, 0.09, 0.045)
    fig.text(x + 0.045, 0.937, sl + "  ▾", ha="center", va="center", fontsize=9, color="#333")

# KPI cards
for i, (lab, val) in enumerate(kpis):
    x = 0.02 + i * 0.163
    panel(x, 0.76, 0.153, 0.125)
    fig.text(x + 0.012, 0.85, lab, fontsize=10, color=C["grey"])
    col = C["navy"] if "YoY" not in lab else "#3BB273"
    fig.text(x + 0.012, 0.785, val, fontsize=21, weight="bold", color=col)

# Monthly trend
panel(0.02, 0.38, 0.62, 0.36)
ax = fig.add_axes([0.06, 0.42, 0.56, 0.27])
m = s.groupby(s.order_date.dt.to_period("M")).sales_amount.sum()
xs = [p.strftime("%b %y") for p in m.index]
ax.bar(xs, m.values, color=C["blue"], alpha=0.85, label="Revenue")
ax.plot(xs, m.rolling(3).mean().values, color=C["orange"], lw=2.5, label="3M rolling avg")
ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda v, _: f"₹{v / 1e7:.1f}Cr"))
ax.tick_params(axis="x", rotation=60, labelsize=7.5); ax.tick_params(axis="y", labelsize=8)
for sp in ["top", "right"]: ax.spines[sp].set_visible(False)
ax.legend(frameon=False, fontsize=8, loc="upper left")
fig.text(0.035, 0.71, "Monthly Revenue Trend", fontsize=12, weight="bold")

# Region donut
panel(0.66, 0.38, 0.32, 0.36)
ax = fig.add_axes([0.68, 0.40, 0.28, 0.29])
r = s.groupby("region_name").sales_amount.sum().sort_values(ascending=False)
ax.pie(r, labels=[f"{k}\n{v / r.sum():.0%}" for k, v in r.items()], startangle=90, counterclock=False,
       colors=[C["navy"], C["blue"], C["orange"], C["grey"]], wedgeprops=dict(width=0.38, ec="white"),
       textprops=dict(fontsize=9))
ax.text(0, 0, f"₹{r.sum() / 1e7:.1f} Cr", ha="center", va="center", fontsize=12, weight="bold")
fig.text(0.675, 0.71, "Revenue by Region", fontsize=12, weight="bold")

# Sub-category bar
panel(0.02, 0.03, 0.47, 0.33)
ax = fig.add_axes([0.13, 0.06, 0.34, 0.24])
sc = s.groupby("sub_category").agg(rev=("sales_amount", "sum"), p=("profit", "sum"))
sc["m"] = sc.p / sc.rev
sc = sc.sort_values("rev")
ax.barh(sc.index, sc.rev, color=C["navy"])
for i, (v, mg) in enumerate(zip(sc.rev, sc.m)):
    ax.text(v, i, f"  {mg:.0%} margin", va="center", fontsize=7.5, color=C["grey"])
ax.xaxis.set_major_formatter(mtick.FuncFormatter(lambda v, _: f"₹{v / 1e7:.0f}Cr"))
ax.tick_params(labelsize=8)
for sp in ["top", "right"]: ax.spines[sp].set_visible(False)
fig.text(0.035, 0.325, "Revenue & Margin by Sub-category", fontsize=12, weight="bold")

# Discount vs margin
panel(0.51, 0.03, 0.47, 0.33)
ax = fig.add_axes([0.56, 0.07, 0.40, 0.23])
d = s.groupby("discount_pct").agg(rev=("sales_amount", "sum"), p=("profit", "sum"))
mg = d.p / d.rev
ax.bar([f"{v:.0%}" for v in d.index], mg, color=[C["red"] if v < 0 else C["navy"] for v in mg])
ax.axhline(0, color="black", lw=0.8)
ax.yaxis.set_major_formatter(mtick.PercentFormatter(1.0))
ax.tick_params(labelsize=8)
for sp in ["top", "right"]: ax.spines[sp].set_visible(False)
fig.text(0.525, 0.325, "Profit Margin by Discount Level", fontsize=12, weight="bold")

fig.savefig(IMG / "powerbi_dashboard_mockup.png", dpi=110, facecolor=C["bg"])
print("saved images/powerbi_dashboard_mockup.png")
