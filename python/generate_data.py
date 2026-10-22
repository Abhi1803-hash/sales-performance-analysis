"""
generate_data.py
----------------
Generates a realistic, reproducible retail sales dataset (star schema) for the
Sales Analysis portfolio project.

Output (in ../data):
    dim_customers.csv, dim_products.csv, dim_regions.csv,
    dim_sales_reps.csv, fact_sales.csv

Run:
    python python/generate_data.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
rng = np.random.default_rng(SEED)
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

START, END = "2024-01-01", "2025-12-31"
N_ORDERS = 12_000

# ---------------------------------------------------------------- regions
regions = pd.DataFrame({
    "region_id": [1, 2, 3, 4],
    "region_name": ["North", "South", "East", "West"],
    "country": ["India"] * 4,
})
cities = {
    1: ["Delhi", "Chandigarh", "Jaipur", "Lucknow"],
    2: ["Chennai", "Bengaluru", "Hyderabad", "Kochi"],
    3: ["Kolkata", "Bhubaneswar", "Patna", "Guwahati"],
    4: ["Mumbai", "Pune", "Ahmedabad", "Surat"],
}

# ---------------------------------------------------------------- products
catalog = {
    "Electronics": {
        "Mobiles": [("Smartphone A1", 15999), ("Smartphone Pro X", 42999), ("Feature Phone F2", 1999)],
        "Laptops": [("Laptop Air 13", 54999), ("Laptop Gamer 15", 89999), ("Chromebook C1", 24999)],
        "Accessories": [("Wireless Earbuds", 2499), ("Power Bank 20k", 1499), ("Smartwatch S3", 4999)],
    },
    "Furniture": {
        "Chairs": [("Office Chair Ergo", 8999), ("Gaming Chair Z", 14999)],
        "Tables": [("Study Table", 5999), ("Dining Table 6S", 24999)],
        "Storage": [("Bookshelf 5T", 4499), ("Wardrobe 3D", 19999)],
    },
    "Office Supplies": {
        "Paper": [("A4 Ream 500", 349), ("Notebook Pack 6", 299)],
        "Writing": [("Gel Pen Box", 199), ("Marker Set 12", 249)],
        "Organizers": [("Desk Organizer", 799), ("File Folder Set", 399)],
    },
}
rows, pid = [], 101
for cat, subs in catalog.items():
    for sub, items in subs.items():
        for name, price in items:
            margin = {"Electronics": 0.18, "Furniture": 0.30, "Office Supplies": 0.40}[cat]
            cost = round(price * (1 - margin + rng.uniform(-0.04, 0.04)), 2)
            rows.append((pid, name, cat, sub, price, cost))
            pid += 1
products = pd.DataFrame(rows, columns=["product_id", "product_name", "category",
                                       "sub_category", "unit_price", "unit_cost"])

# ---------------------------------------------------------------- sales reps
first = ["Aarav", "Diya", "Rohan", "Priya", "Kabir", "Ananya", "Vikram", "Sneha",
         "Arjun", "Isha", "Karan", "Meera"]
last = ["Sharma", "Verma", "Iyer", "Reddy", "Das", "Patel", "Singh", "Nair",
        "Ghosh", "Mehta", "Kapoor", "Rao"]
reps = pd.DataFrame({
    "rep_id": range(1, 13),
    "rep_name": [f"{f} {l}" for f, l in zip(first, last)],
    "region_id": np.repeat([1, 2, 3, 4], 3),
    "hire_date": pd.to_datetime(rng.choice(pd.date_range("2018-01-01", "2023-06-30"), 12)).date,
    "annual_target": rng.choice([9_000_000, 11_000_000, 13_000_000], 12),
})

# ---------------------------------------------------------------- customers
n_cust = 1_500
segments = rng.choice(["Consumer", "Corporate", "Small Business"], n_cust, p=[0.55, 0.25, 0.20])
cust_region = rng.choice([1, 2, 3, 4], n_cust, p=[0.30, 0.25, 0.20, 0.25])
customers = pd.DataFrame({
    "customer_id": [f"C{10000 + i}" for i in range(n_cust)],
    "customer_name": [f"Customer {10000 + i}" for i in range(n_cust)],
    "segment": segments,
    "region_id": cust_region,
    "city": [rng.choice(cities[r]) for r in cust_region],
    "signup_date": pd.to_datetime(rng.choice(pd.date_range("2022-01-01", "2025-10-31"), n_cust)).date,
})

# ---------------------------------------------------------------- fact_sales
dates = pd.date_range(START, END, freq="D")
# seasonality: festive peak Oct-Nov, dip Feb, plus YoY growth
month_w = np.array([0.9, 0.75, 0.95, 0.9, 0.95, 0.85, 0.9, 1.0, 1.05, 1.35, 1.5, 1.2])
day_w = month_w[dates.month - 1] * np.where(dates.year == 2025, 1.15, 1.0)
day_w = day_w / day_w.sum()
order_dates = np.sort(rng.choice(dates, N_ORDERS, p=day_w))

cust_pick = customers.sample(N_ORDERS, replace=True, random_state=SEED,
                             weights=rng.pareto(1.5, n_cust) + 0.1).reset_index(drop=True)
# product popularity: cheaper items sell more often
pop = 1 / np.log(products["unit_price"] + 10)
prod_pick = products.sample(N_ORDERS, replace=True, random_state=SEED + 1,
                            weights=pop).reset_index(drop=True)

qty = np.where(prod_pick["category"] == "Office Supplies",
               rng.integers(1, 15, N_ORDERS), rng.integers(1, 4, N_ORDERS))
qty = np.where(cust_pick["segment"] == "Corporate", qty * rng.integers(1, 3, N_ORDERS), qty)
discount = rng.choice([0, 0.05, 0.10, 0.15, 0.20], N_ORDERS, p=[0.45, 0.2, 0.18, 0.12, 0.05])
# festive season = deeper discounts
discount = np.where(pd.DatetimeIndex(order_dates).month.isin([10, 11]),
                    np.minimum(discount + 0.05, 0.30), discount)

rep_by_region = reps.groupby("region_id")["rep_id"].apply(list).to_dict()
rep_ids = [rng.choice(rep_by_region[r]) for r in cust_pick["region_id"]]

gross = qty * prod_pick["unit_price"].values
sales = np.round(gross * (1 - discount), 2)
cost = np.round(qty * prod_pick["unit_cost"].values, 2)

order_dt = pd.to_datetime(order_dates)
ship_days = rng.choice([1, 2, 3, 4, 5, 7], N_ORDERS, p=[0.1, 0.3, 0.3, 0.15, 0.1, 0.05])
fact = pd.DataFrame({
    "order_id": [f"ORD-{200000 + i}" for i in range(N_ORDERS)],
    "order_date": order_dt.date,
    "ship_date": (order_dt + pd.to_timedelta(ship_days, unit="D")).date,
    "customer_id": cust_pick["customer_id"],
    "product_id": prod_pick["product_id"],
    "rep_id": rep_ids,
    "region_id": cust_pick["region_id"],
    "channel": rng.choice(["Online", "Retail Store", "Distributor"], N_ORDERS, p=[0.5, 0.35, 0.15]),
    "payment_mode": rng.choice(["UPI", "Card", "Net Banking", "COD"], N_ORDERS, p=[0.45, 0.3, 0.1, 0.15]),
    "quantity": qty,
    "unit_price": prod_pick["unit_price"],
    "discount_pct": discount,
    "sales_amount": sales,
    "cost_amount": cost,
    "profit": np.round(sales - cost, 2),
    "is_returned": rng.random(N_ORDERS) < 0.04,
})

# Inject a few realistic data-quality issues for the cleaning step
dirty = fact.copy()
dirty.loc[rng.choice(N_ORDERS, 25, replace=False), "channel"] = None
dup = dirty.sample(15, random_state=7)
dirty = pd.concat([dirty, dup], ignore_index=True)

for name, df in {"dim_regions": regions, "dim_products": products, "dim_sales_reps": reps,
                 "dim_customers": customers, "fact_sales": dirty}.items():
    df.to_csv(DATA_DIR / f"{name}.csv", index=False)
    print(f"{name:<16} {len(df):>6,} rows")
