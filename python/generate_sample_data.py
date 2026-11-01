"""Generate the SAMPLE dataset for the Supply Chain & Inventory Performance project.

IMPORTANT: This is synthetic sample data created for demonstration and learning.
It is modelled on the structure of a real supply chain & inventory dashboard
project (daily stock records, purchase orders, product master data) across
Indian regional warehouses, with all monetary values in Indian Rupees (INR).
It does not contain any real company data.

Column names are written in clear, full words (see data/data_dictionary.md).
"""
import numpy as np
import pandas as pd
from pathlib import Path

rng = np.random.default_rng(42)
DATA = Path(__file__).resolve().parent.parent / "data"
DATA.mkdir(exist_ok=True)

# ---------------- Product master (INR) ----------------
# product_code, product_name, product_category, supplier_name, unit_cost_inr
PRODUCTS = [
    ("SKU-001", "Wireless Earbuds Pro", "Electronics", "TechNova Supplies", 19850),
    ("SKU-002", "Smart Watch Series 5", "Electronics", "TechNova Supplies", 32340),
    ("SKU-003", "Bluetooth Speaker", "Electronics", "TechNova Supplies", 7140),
    ("SKU-004", "USB-C Fast Charger", "Electronics", "VoltEdge Traders", 4680),
    ("SKU-005", "Laptop Stand Aluminium", "Electronics", "VoltEdge Traders", 12040),
    ("SKU-006", "Cotton T-Shirt", "Apparel", "UrbanThread Apparel", 2790),
    ("SKU-007", "Denim Jacket", "Apparel", "UrbanThread Apparel", 5800),
    ("SKU-008", "Running Shoes", "Apparel", "UrbanThread Apparel", 2120),
    ("SKU-009", "Winter Jacket NorthPeak", "Apparel", "NorthPeak Clothing", 3900),
    ("SKU-010", "Organic Basmati Rice 5kg", "FMCG", "FreshKart Distributors", 15160),
    ("SKU-011", "Cold-Pressed Olive Oil 1L", "FMCG", "FreshKart Distributors", 25650),
    ("SKU-012", "Protein Powder 1kg", "FMCG", "NutriCore India", 5350),
    ("SKU-013", "Vitamin D3 Supplements", "FMCG", "NutriCore India", 9370),
    ("SKU-014", "Ceramic Dinner Set 12pc", "Home & Living", "HomeNest Living", 3350),
    ("SKU-015", "LED Desk Lamp", "Home & Living", "HomeNest Living", 17390),
    ("SKU-016", "Memory Foam Pillow", "Home & Living", "HomeNest Living", 8700),
    ("SKU-017", "Car Vacuum Cleaner", "Automotive", "AutoGrip Parts", 6130),
    ("SKU-018", "Car Battery 12V 70Ah", "Automotive", "AutoGrip Parts", 13600),
    ("SKU-019", "Tyre Inflator Portable", "Automotive", "AutoGrip Parts", 4010),
    ("SKU-020", "Yoga Mat Pro 6mm", "Sports", "FlexFit Sports", 5130),
    ("SKU-021", "Dumbbell Set 10kg", "Sports", "FlexFit Sports", 7920),
    ("SKU-022", "Cricket Bat English Willow", "Sports", "FlexFit Sports", 11040),
    ("SKU-023", "Air Fryer 5L", "Electronics", "TechNova Supplies", 1960),
    ("SKU-024", "Water Purifier 8L", "Home & Living", "HomeNest Living", 16060),
]

# Reorder level scales with each product's typical daily demand (clear rule:
# reorder when roughly 4-6 days of stock remain).
base_demand = {code: int(rng.integers(2, 26)) for code, *_ in PRODUCTS}
dim = pd.DataFrame(
    [(code, name, cat, sup, cost,
      int(np.clip(round(base_demand[code] * rng.uniform(5.5, 8.5)), 30, 400)))
     for code, name, cat, sup, cost in PRODUCTS],
    columns=["product_code", "product_name", "product_category", "supplier_name",
             "unit_cost_inr", "reorder_level"])
dim.to_csv(DATA / "dim_products.csv", index=False)

# ---------------- Warehouses (India) ----------------
WAREHOUSES = ["Mumbai Central", "Delhi Hub", "Bengaluru Hub"]
# demand multiplier and starting-stock cover per warehouse
WH_PROFILE = {
    "Mumbai Central": dict(demand=1.25, cover=0.95),   # busiest, lean stock -> most stock-outs
    "Delhi Hub": dict(demand=1.00, cover=1.10),
    "Bengaluru Hub": dict(demand=0.80, cover=1.45),    # quieter, heavy stock -> overstock
}

# ---------------- Daily stock facts ----------------
dates = pd.date_range("2023-01-01", "2025-06-30", freq="D")
rows = []
for _, p in dim.iterrows():
    for wh, prof in WH_PROFILE.items():
        stock = int(p["reorder_level"] * prof["cover"] * rng.uniform(1.2, 1.9))
        pending_day, pending_qty = None, 0   # replenishment in flight (lead-time delay)
        for i, d in enumerate(dates):
            received = 0
            if pending_day is not None and i >= pending_day:
                received, stock = pending_qty, stock + pending_qty
                pending_day, pending_qty = None, 0
            opening = stock
            months_in = (d.year - 2023) * 12 + (d.month - 1)
            trend = 1.006 ** months_in  # gentle ~7% per year demand growth
            lam = base_demand[p["product_code"]] * prof["demand"] * trend * (1 + 0.18 * np.sin(d.dayofyear / 28.0))
            demand = int(rng.poisson(max(lam, 0.5)))
            sold = min(demand, stock)
            lost = demand - sold
            stock_end = stock - sold
            # reorder when low; delivery lands after a lead-time delay,
            # so a fast-selling product can stock out while waiting (realistic)
            if stock_end < p["reorder_level"] and pending_day is None:
                pending_day = i + int(rng.integers(3, 10))
                pending_qty = int(p["reorder_level"] * rng.uniform(1.4, 2.2))
            rows.append((d.date(), p["product_code"], wh, opening, received, sold, lost, stock_end))
            stock = stock_end

fact = pd.DataFrame(rows, columns=["stock_date", "product_code", "warehouse_name",
                                   "opening_stock_units", "units_received", "units_sold",
                                   "lost_sales_units", "closing_stock_units"])
fact.to_csv(DATA / "fact_daily_stock.csv", index=False)

# ---------------- Purchase orders ----------------
SUPPLIER_LEAD = {"TechNova Supplies": 7, "VoltEdge Traders": 5, "UrbanThread Apparel": 10,
                 "NorthPeak Clothing": 14, "FreshKart Distributors": 4, "NutriCore India": 6,
                 "HomeNest Living": 9, "AutoGrip Parts": 8, "FlexFit Sports": 11}
po_rows, po_id = [], 1000
for _, p in dim.iterrows():
    for wh in WAREHOUSES:
        for _ in range(rng.integers(10, 16)):
            po_id += 1
            order_date = pd.Timestamp("2023-01-01") + pd.Timedelta(days=int(rng.integers(0, 875)))
            promised = SUPPLIER_LEAD[p["supplier_name"]] + int(rng.integers(-1, 2))
            delay = int(rng.choice([0, 0, 0, 1, 2, 3, 5, 7], p=[.45, .1, .05, .12, .1, .08, .06, .04]))
            actual = max(promised + delay, 1)
            po_rows.append((f"PO-{po_id}", order_date.date(), p["product_code"], wh,
                            int(rng.integers(80, 420)), promised, actual,
                            (order_date + pd.Timedelta(days=actual)).date()))
po = pd.DataFrame(po_rows, columns=["purchase_order_id", "order_date", "product_code",
                                    "warehouse_name", "quantity_ordered",
                                    "promised_lead_time_days", "actual_lead_time_days",
                                    "delivery_date"])
po.to_csv(DATA / "fact_purchase_orders.csv", index=False)

print(f"dim_products: {len(dim)} rows | fact_daily_stock: {len(fact)} rows | purchase_orders: {len(po)} rows")
print("Warehouses:", WAREHOUSES)
