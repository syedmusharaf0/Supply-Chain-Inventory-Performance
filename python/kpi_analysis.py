"""
KPI analysis - Supply Chain & Inventory Performance

Reads the loaded database (see etl_pipeline.py) and computes the executive
KPIs used in the Power BI dashboard:
  * Stock Turnover Ratio          * Carrying Cost (20% p.a. assumption)
  * Lead Time Variance            * Stock-out Rate
  * Bottleneck SKUs (lost sales)  * Overstocked SKUs (low turnover)

Exports: outputs/*.csv  and chart images in images/*.png
Run:  python python/kpi_analysis.py   (after etl_pipeline.py)
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from sqlalchemy import create_engine

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "outputs"
IMG = BASE / "images"
CARRYING_RATE = 0.20  # 20% of average inventory value per year
SAR_TO_INR = 22.30    # approximate reporting conversion, 1 SAR = 22.30 INR

plt.rcParams.update({"font.size": 10, "axes.edgecolor": "#666666",
                     "axes.labelcolor": "#222222", "figure.dpi": 150})


def main():
    engine = create_engine(f"sqlite:///{BASE / 'database' / 'supply_chain.db'}")
    stock = pd.read_sql("SELECT * FROM fact_daily_stock", engine, parse_dates=["date"])
    products = pd.read_sql("SELECT * FROM dim_products", engine)
    orders = pd.read_sql("SELECT * FROM fact_purchase_orders", engine)
    df = stock.merge(products, on="sku", how="left")
    days = (df["date"].max() - df["date"].min()).days + 1

    # Average inventory VALUE per SKU = sum over warehouses of each
    # location's mean closing-stock value (unit cost is constant per SKU).
    inv_by_sku_wh = (df.assign(inv_value=df["closing_stock"] * df["unit_cost_sar"])
                       .groupby(["sku", "warehouse"])["inv_value"].mean())
    avg_inv_by_sku = inv_by_sku_wh.groupby("sku").sum()
    avg_inv_by_wh = inv_by_sku_wh.groupby("warehouse").sum()

    # ---- KPI by SKU ------------------------------------------------------
    by_sku = df.groupby(["sku", "product_name", "category", "supplier"]).agg(
        units_sold=("units_sold", "sum"),
        stockout_days=("stockout_day", "sum"),
        total_days=("stockout_day", "size"),
        units_lost_sales=("units_lost_sales", "sum"),
    ).reset_index()
    cost = products.set_index("sku")["unit_cost_sar"]
    by_sku["cogs_sar"] = by_sku["units_sold"] * by_sku["sku"].map(cost)
    by_sku["avg_inventory_value_sar"] = by_sku["sku"].map(avg_inv_by_sku).round(2)
    by_sku["stock_turnover_ratio"] = (by_sku["cogs_sar"]
                                      / by_sku["avg_inventory_value_sar"]).round(2)
    by_sku["stockout_rate_pct"] = (100 * by_sku["stockout_days"]
                                   / by_sku["total_days"]).round(2)
    by_sku["est_lost_sales_value_sar"] = (by_sku["units_lost_sales"]
                                          * by_sku["sku"].map(cost)).round(2)
    by_sku["avg_inventory_value_inr"] = (by_sku["avg_inventory_value_sar"] * SAR_TO_INR).round(2)
    by_sku["est_lost_sales_value_inr"] = (by_sku["est_lost_sales_value_sar"] * SAR_TO_INR).round(2)
    by_sku = by_sku.drop(columns=["cogs_sar_x"], errors="ignore")

    # ---- KPI by warehouse -------------------------------------------------
    by_wh = df.groupby("warehouse").agg(
        units_sold=("units_sold", "sum"),
        units_lost_sales=("units_lost_sales", "sum"),
        stockout_days=("stockout_day", "sum"),
        total_days=("stockout_day", "size"),
    ).reset_index()
    by_wh = by_wh.set_index("warehouse")
    by_wh["avg_inventory_value_sar"] = avg_inv_by_wh.round(2)
    by_wh = by_wh.reset_index()
    by_wh["stockout_rate_pct"] = (100 * by_wh["stockout_days"] / by_wh["total_days"]).round(2)
    by_wh["carrying_cost_sar"] = (by_wh["avg_inventory_value_sar"]
                                  * CARRYING_RATE * days / 365).round(2)
    by_wh["avg_inventory_value_inr"] = (by_wh["avg_inventory_value_sar"] * SAR_TO_INR).round(2)
    by_wh["carrying_cost_inr"] = (by_wh["carrying_cost_sar"] * SAR_TO_INR).round(2)

    # ---- Lead time variance by supplier -----------------------------------
    orders["variance_days"] = orders["actual_lead_time_days"] - orders["standard_lead_time_days"]
    by_supplier = orders.groupby("supplier").agg(
        orders=("order_id", "count"),
        avg_standard_lead_days=("standard_lead_time_days", "mean"),
        avg_actual_lead_days=("actual_lead_time_days", "mean"),
        lead_time_variance_days=("variance_days", "mean"),
    ).reset_index()
    late = orders.assign(late=orders["actual_lead_time_days"] > orders["standard_lead_time_days"])
    by_supplier["pct_orders_late"] = (100 * late.groupby("supplier")["late"].mean()).values
    by_supplier = by_supplier.round(2).sort_values("lead_time_variance_days", ascending=False)

    # ---- Monthly trend ------------------------------------------------------
    monthly = df.set_index("date").groupby(pd.Grouper(freq="M")).agg(
        stockout_rate_pct=("stockout_day", lambda s: round(100 * s.mean(), 2)),
        units_lost_sales=("units_lost_sales", "sum"),
        units_sold=("units_sold", "sum"),
    ).reset_index()

    # ---- Headline summary ---------------------------------------------------
    summary = pd.DataFrame([{
        "period_days": days,
        "total_units_sold": int(df["units_sold"].sum()),
        "total_units_lost_sales": int(df["units_lost_sales"].sum()),
        "overall_stockout_rate_pct": round(100 * df["stockout_day"].mean(), 2),
        "overall_turnover_ratio_period": round(
            (df["units_sold"] * df["unit_cost_sar"]).sum()
            / df.groupby(["sku", "warehouse"]).apply(
                lambda g: (g["closing_stock"] * g["unit_cost_sar"]).mean()).sum(), 2),
        "total_avg_inventory_value_sar": round(float(by_wh["avg_inventory_value_sar"].sum()), 2),
        "total_carrying_cost_sar": round(float(by_wh["carrying_cost_sar"].sum()), 2),
        "total_carrying_cost_inr": round(float(by_wh["carrying_cost_inr"].sum()), 2),
        "sar_to_inr_rate": SAR_TO_INR,
        "avg_lead_time_variance_days": round(float(orders["variance_days"].mean()), 2),
        "pct_orders_late": round(100 * float(
            (orders["actual_lead_time_days"] > orders["standard_lead_time_days"]).mean()), 2),
    }])

    OUT.mkdir(exist_ok=True)
    IMG.mkdir(exist_ok=True)
    by_sku.sort_values("stock_turnover_ratio", ascending=False).to_csv(OUT / "kpi_by_sku.csv", index=False)
    by_wh.to_csv(OUT / "kpi_by_warehouse.csv", index=False)
    by_supplier.to_csv(OUT / "kpi_by_supplier_leadtime.csv", index=False)
    monthly.to_csv(OUT / "monthly_trend.csv", index=False)
    summary.to_csv(OUT / "kpi_summary.csv", index=False)

    # ---- Charts ---------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(7, 3.4))
    ax.plot(monthly["date"], monthly["stockout_rate_pct"], marker="o", color="#14406B")
    ax.set_title("Stock-out rate by month (%)")
    ax.set_ylabel("% of days with stock-outs")
    fig.tight_layout(); fig.savefig(IMG / "monthly_stockout_trend.svg"); plt.close(fig)

    cat = by_sku.groupby("category")["stock_turnover_ratio"].mean().sort_values()
    fig, ax = plt.subplots(figsize=(7, 3.4))
    ax.barh(cat.index, cat.values, color="#2E7D6B")
    ax.set_title("Average stock turnover ratio by category (period)")
    ax.set_xlabel("Turnover ratio")
    fig.tight_layout(); fig.savefig(IMG / "turnover_by_category.svg"); plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 3.4))
    ax.bar(by_supplier["supplier"], by_supplier["lead_time_variance_days"], color="#C05621")
    ax.axhline(0, color="#666666", linewidth=0.8)
    ax.set_title("Lead time variance by supplier (actual - standard, days)")
    ax.set_ylabel("Days")
    plt.setp(ax.get_xticklabels(), rotation=12, ha="right")
    fig.tight_layout(); fig.savefig(IMG / "lead_time_variance_by_supplier.svg"); plt.close(fig)

    top = by_sku.nlargest(8, "units_lost_sales").sort_values("units_lost_sales")
    fig, ax = plt.subplots(figsize=(7, 3.6))
    ax.barh(top["sku"] + " - " + top["product_name"], top["units_lost_sales"], color="#9B2C2C")
    ax.set_title("Bottleneck SKUs - units lost to stock-outs")
    ax.set_xlabel("Units lost")
    fig.tight_layout(); fig.savefig(IMG / "top_bottleneck_skus.svg"); plt.close(fig)

    print(summary.to_string(index=False))
    print("\nTop bottleneck SKUs:")
    print(by_sku.nlargest(5, "units_lost_sales")[
        ["sku", "product_name", "stockout_rate_pct", "units_lost_sales"]].to_string(index=False))
    print("\nOutputs written to outputs/ and images/")


if __name__ == "__main__":
    main()
