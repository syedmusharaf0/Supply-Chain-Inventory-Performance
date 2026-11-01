"""
Generate a realistic SAMPLE supply chain dataset for portfolio demonstration.

The dataset is synthetic (generated with a fixed random seed) and models the
structure of the daily stock records used in the Cyepro Solutions supply chain
project: multi-regional warehouses, daily opening/received/sold/closing stock,
stock-out days and purchase orders with standard vs actual lead times.
It contains no real company data.

Outputs (in ../data/):
  dim_products.csv         - one row per SKU
  fact_daily_stock.csv     - one row per SKU x warehouse x day
  fact_purchase_orders.csv - one row per replenishment order
"""
import numpy as np
import pandas as pd
from pathlib import Path

RNG = np.random.default_rng(42)
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Approximate reporting conversion used across the project (Nov 2026).
SAR_TO_INR = 22.30  # 1 SAR = 22.30 INR

WAREHOUSES = ["Riyadh Central", "Jeddah Hub", "Dammam Hub"]

# sku, product, category, unit cost (SAR), supplier, standard lead time (days), demand class
PRODUCTS = [
    ("SKU-001", "Wireless Earbuds X2",        "Electronics",     145, "Gulf Trading Co.",        7,  "fast"),
    ("SKU-002", "Smart Watch Series 5",       "Electronics",     620, "Gulf Trading Co.",        9,  "medium"),
    ("SKU-003", "USB-C Fast Charger 65W",     "Electronics",      85, "Arabian Supply Ltd.",     5,  "fast"),
    ("SKU-004", "Bluetooth Speaker Mini",     "Electronics",     210, "Gulf Trading Co.",        8,  "medium"),
    ("SKU-005", "LED Desk Lamp",              "Electronics",     130, "Desert Logistics Supplies", 10, "slow"),
    ("SKU-006", "Instant Coffee 200g",        "FMCG",             32, "National Distribution Co.", 4, "fast"),
    ("SKU-007", "Olive Oil 500ml",            "FMCG",             28, "National Distribution Co.", 4, "fast"),
    ("SKU-008", "Basmati Rice 5kg",           "FMCG",             45, "National Distribution Co.", 6, "medium"),
    ("SKU-009", "Laundry Detergent 3kg",      "FMCG",             54, "Arabian Supply Ltd.",      5,  "medium"),
    ("SKU-010", "Organic Honey 250g",         "FMCG",             68, "Desert Logistics Supplies", 12, "slow"),
    ("SKU-011", "Men's Cotton T-Shirt",       "Apparel",          75, "Arabian Supply Ltd.",      8,  "medium"),
    ("SKU-012", "Running Shoes AirFlex",      "Apparel",         340, "Gulf Trading Co.",        11,  "medium"),
    ("SKU-013", "Winter Jacket NorthPeak",    "Apparel",         480, "Desert Logistics Supplies", 14, "slow"),
    ("SKU-014", "Kids School Backpack",       "Apparel",         120, "Arabian Supply Ltd.",      7,  "medium"),
    ("SKU-015", "Air Fryer 5L Digital",       "Home Appliances", 390, "Gulf Trading Co.",        10,  "medium"),
    ("SKU-016", "Vacuum Cleaner Cyclone",     "Home Appliances", 540, "Gulf Trading Co.",        12,  "slow"),
    ("SKU-017", "Electric Kettle 1.8L",       "Home Appliances",  95, "Arabian Supply Ltd.",      6,  "fast"),
    ("SKU-018", "Ceramic Dinner Set 16pc",    "Home Appliances", 260, "Desert Logistics Supplies", 13, "slow"),
    ("SKU-019", "Car Battery 70Ah",           "Auto Parts",      420, "National Distribution Co.", 8,  "medium"),
    ("SKU-020", "Brake Pads Set - Sedan",     "Auto Parts",      180, "National Distribution Co.", 7,  "medium"),
    ("SKU-021", "Engine Oil Filter",          "Auto Parts",       40, "Arabian Supply Ltd.",      5,  "fast"),
    ("SKU-022", "LED Headlight Bulbs Pair",   "Auto Parts",      150, "Gulf Trading Co.",         9,  "slow"),
    ("SKU-023", "Smartphone Case Armor",      "Electronics",      55, "Arabian Supply Ltd.",      5,  "fast"),
    ("SKU-024", "Dates Premium 1kg",          "FMCG",             60, "Desert Logistics Supplies", 6,  "medium"),
]
DEMAND_RANGE = {"fast": (25, 55), "medium": (8, 20), "slow": (1, 4)}

START = pd.Timestamp("2025-01-01")
DAYS = 181  # 1 Jan - 30 Jun 2025


def main():
    dim_rows, stock_rows, order_rows = [], [], []
    order_id = 1
    dates = pd.date_range(START, periods=DAYS, freq="D")

    for sku, name, cat, cost, supplier, std_lead, dclass in PRODUCTS:
        lo, hi = DEMAND_RANGE[dclass]
        base_demand = int(RNG.integers(lo, hi + 1))
        reorder_point = int(base_demand * (std_lead + 3))
        order_qty = int(base_demand * 14)
        dim_rows.append({
            "sku": sku, "product_name": name, "category": cat,
            "unit_cost_sar": cost, "unit_cost_inr": round(cost * SAR_TO_INR, 2),
            "supplier": supplier,
            "standard_lead_time_days": std_lead,
            "reorder_point_units": reorder_point,
            "base_daily_demand": base_demand,
        })

        for wh in WAREHOUSES:
            wh_factor = {"Riyadh Central": 1.15, "Jeddah Hub": 1.0, "Dammam Hub": 0.8}[wh]
            stock = int(order_qty * 1.2 * wh_factor) + 10
            pending = []  # (arrival_day_index, qty)
            for d, date in enumerate(dates):
                opening = stock
                received = 0
                still_pending = []
                for arr, qty in pending:
                    if arr == d:
                        received += qty
                    else:
                        still_pending.append((arr, qty))
                pending = still_pending
                stock += received

                seasonal = 1.0 + 0.18 * np.sin(d / 13.0) + (0.35 if date.day <= 3 else 0.0)
                demand = max(0, int(RNG.poisson(base_demand * wh_factor * seasonal)))
                sold = min(demand, stock)
                lost = demand - sold
                stock -= sold
                stockout = 1 if lost > 0 else 0

                stock_rows.append({
                    "date": date.date(), "warehouse": wh, "sku": sku,
                    "opening_stock": opening, "units_received": received,
                    "units_sold": sold, "units_lost_sales": lost,
                    "closing_stock": stock, "stockout_day": stockout,
                })

                if stock <= reorder_point and not pending:
                    actual_lead = max(1, int(round(RNG.normal(std_lead, 2.0))))
                    arrival_idx = d + actual_lead
                    order_rows.append({
                        "order_id": f"PO-{order_id:05d}",
                        "order_date": date.date(), "sku": sku, "warehouse": wh,
                        "supplier": supplier, "quantity_units": order_qty,
                        "standard_lead_time_days": std_lead,
                        "actual_lead_time_days": actual_lead,
                        "arrival_date": (date + pd.Timedelta(days=actual_lead)).date(),
                    })
                    order_id += 1
                    if arrival_idx < DAYS:
                        pending.append((arrival_idx, order_qty))

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(dim_rows).to_csv(DATA_DIR / "dim_products.csv", index=False)
    pd.DataFrame(stock_rows).to_csv(DATA_DIR / "fact_daily_stock.csv", index=False)
    pd.DataFrame(order_rows).to_csv(DATA_DIR / "fact_purchase_orders.csv", index=False)
    print(f"products: {len(dim_rows)}  daily stock rows: {len(stock_rows)}  orders: {len(order_rows)}")


if __name__ == "__main__":
    main()
