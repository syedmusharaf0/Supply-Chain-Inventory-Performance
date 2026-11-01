"""ETL pipeline: load raw CSV extracts, validate, clean and load into a database.

In production this targets PostgreSQL (see sql/01_schema_postgresql.sql).
For a self-contained local run it loads into a SQLite database file using the
same table/column names, so the whole pipeline can be executed anywhere.
All monetary values are in Indian Rupees (INR).
"""
import pandas as pd
from pathlib import Path
from sqlalchemy import create_engine

BASE = Path(__file__).resolve().parent.parent
DATA, DBDIR = BASE / "data", BASE / "database"
DBDIR.mkdir(exist_ok=True)

def validate(df: pd.DataFrame, name: str, key_cols: list[str]) -> None:
    assert not df.duplicated(subset=key_cols).any(), f"{name}: duplicate keys on {key_cols}"
    assert df[key_cols].notna().all().all(), f"{name}: null values in key columns"
    print(f"  [OK] {name}: {len(df):,} rows, keys unique, no null keys")

# Source CSVs carry friendly display headers (what you see in the dashboards);
# the ETL maps them to the database column names used in sql/01_schema_postgresql.sql.
PRODUCT_COLUMNS = {"Product Code": "product_code", "Product Name": "product_name",
                   "Product Category": "product_category", "Supplier Name": "supplier_name",
                   "Unit Cost (INR)": "unit_cost_inr", "Reorder Level": "reorder_level"}
STOCK_COLUMNS = {"Stock Date": "stock_date", "Product Code": "product_code",
                 "Warehouse Name": "warehouse_name", "Opening Stock (units)": "opening_stock_units",
                 "Units Received": "units_received", "Units Sold": "units_sold",
                 "Lost Sales (units)": "lost_sales_units", "Closing Stock (units)": "closing_stock_units"}
ORDER_COLUMNS = {"Purchase Order ID": "purchase_order_id", "Order Date": "order_date",
                 "Product Code": "product_code", "Warehouse Name": "warehouse_name",
                 "Quantity Ordered": "quantity_ordered",
                 "Promised Lead Time (days)": "promised_lead_time_days",
                 "Actual Lead Time (days)": "actual_lead_time_days", "Delivery Date": "delivery_date"}

def main() -> None:
    print("EXTRACT")
    dim = pd.read_csv(DATA / "dim_products.csv").rename(columns=PRODUCT_COLUMNS)
    stock = pd.read_csv(DATA / "fact_daily_stock.csv", parse_dates=["Stock Date"]).rename(columns=STOCK_COLUMNS)
    po = pd.read_csv(DATA / "fact_purchase_orders.csv",
                     parse_dates=["Order Date", "Delivery Date"]).rename(columns=ORDER_COLUMNS)

    print("VALIDATE")
    validate(dim, "dim_products", ["product_code"])
    validate(stock, "fact_daily_stock", ["stock_date", "product_code", "warehouse_name"])
    validate(po, "fact_purchase_orders", ["purchase_order_id"])
    assert (stock["closing_stock_units"] >= 0).all(), "negative closing stock found"
    assert set(stock["warehouse_name"]) <= {"Mumbai Central", "Delhi Hub", "Bengaluru Hub"}, "unknown warehouse"
    assert (po["actual_lead_time_days"] > 0).all(), "non-positive lead time found"
    print("  [OK] business-rule checks passed")

    print("TRANSFORM")
    stock["inventory_value_inr"] = stock["closing_stock_units"] * stock["product_code"].map(
        dim.set_index("product_code")["unit_cost_inr"])
    po["lead_time_variance_days"] = po["actual_lead_time_days"] - po["promised_lead_time_days"]
    po["is_late"] = po["lead_time_variance_days"] > 0
    print(f"  enriched fact_daily_stock with inventory_value_inr; "
          f"purchase orders flagged late: {po['is_late'].mean():.1%} of orders")

    print("LOAD")
    engine = create_engine(f"sqlite:///{DBDIR / 'inventory.db'}")
    dim.to_sql("dim_products", engine, if_exists="replace", index=False)
    stock.to_sql("fact_daily_stock", engine, if_exists="replace", index=False)
    po.to_sql("fact_purchase_orders", engine, if_exists="replace", index=False)
    print(f"  loaded 3 tables into {DBDIR / 'inventory.db'}")
    print(f"  average inventory value (INR): {stock.groupby('stock_date')['inventory_value_inr'].sum().mean():,.0f}")

if __name__ == "__main__":
    main()
