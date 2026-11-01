"""
ETL pipeline - Supply Chain & Inventory Performance

Extract : daily stock records, products and purchase orders from ../data/*.csv
Transform: type parsing, de-duplication, validation checks
           (closing = opening + received - sold; no negative stock)
Load    : SQLAlchemy -> PostgreSQL when DATABASE_URL is set,
          otherwise a local SQLite file (database/supply_chain.db)
          so the project runs anywhere with no server setup.

Run:  python python/etl_pipeline.py
      DATABASE_URL=postgresql+psycopg2://user:pass@localhost:5432/supply_chain \
          python python/etl_pipeline.py
"""
import os
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data"
DB_DIR = BASE / "database"


def extract():
    products = pd.read_csv(DATA / "dim_products.csv")
    stock = pd.read_csv(DATA / "fact_daily_stock.csv", parse_dates=["date"])
    orders = pd.read_csv(DATA / "fact_purchase_orders.csv",
                         parse_dates=["order_date", "arrival_date"])
    return products, stock, orders


def transform(products, stock, orders):
    # De-duplicate on the natural key
    before = len(stock)
    stock = stock.drop_duplicates(subset=["date", "warehouse", "sku"])
    dupes = before - len(stock)

    # Validation 1: stock balance identity
    stock["balance_check"] = (stock["opening_stock"] + stock["units_received"]
                              - stock["units_sold"] - stock["closing_stock"])
    bad_balance = int((stock["balance_check"] != 0).sum())
    stock = stock.drop(columns=["balance_check"])

    # Validation 2: no negative values in stock columns
    stock_cols = ["opening_stock", "units_received", "units_sold",
                  "units_lost_sales", "closing_stock"]
    negatives = int((stock[stock_cols] < 0).any(axis=1).sum())

    # Validation 3: every stock/order SKU exists in the product dimension
    known = set(products["sku"])
    unknown = int((~stock["sku"].isin(known)).sum()
                  + (~orders["sku"].isin(known)).sum())

    print(f"validation: duplicates removed={dupes}, balance mismatches={bad_balance}, "
          f"negative rows={negatives}, unknown SKUs={unknown}")
    return products, stock, orders


def load(products, stock, orders):
    url = os.environ.get("DATABASE_URL")
    if not url:
        DB_DIR.mkdir(parents=True, exist_ok=True)
        url = f"sqlite:///{DB_DIR / 'supply_chain.db'}"
    engine = create_engine(url)
    products.to_sql("dim_products", engine, if_exists="replace", index=False)
    stock.to_sql("fact_daily_stock", engine, if_exists="replace", index=False)
    orders.to_sql("fact_purchase_orders", engine, if_exists="replace", index=False)
    print(f"loaded -> {url}")
    print(f"rows: dim_products={len(products)}, fact_daily_stock={len(stock)}, "
          f"fact_purchase_orders={len(orders)}")


if __name__ == "__main__":
    load(*transform(*extract()))
