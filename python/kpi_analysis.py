"""KPI analysis: compute supply chain KPIs with Pandas and export results + charts.

Mirrors sql/02_kpi_queries.sql so the same KPIs can be produced from either
SQL or Python. All monetary values are in Indian Rupees (INR).
Outputs -> outputs/ (CSV) and images/ (SVG charts).
"""
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
OUT, IMG = BASE / "outputs", BASE / "images"
OUT.mkdir(exist_ok=True); IMG.mkdir(exist_ok=True)
CARRYING_RATE, DAYS = 0.20, 181  # 20% p.a. carrying-cost assumption, Jan-Jun period

dim = pd.read_csv(BASE / "data/dim_products.csv")
stock = pd.read_csv(BASE / "data/fact_daily_stock.csv", parse_dates=["date"])
po = pd.read_csv(BASE / "data/fact_purchase_orders.csv", parse_dates=["order_date", "delivery_date"])
cost = dim.set_index("sku")["unit_cost_inr"]
stock["value"] = stock["closing_stock"] * stock["sku"].map(cost)

def turnover_and_stockout(df: pd.DataFrame) -> dict:
    sold_value = (df["units_sold"] * df["sku"].map(cost)).sum()
    avg_inv_value = df.groupby("date")["value"].sum().mean()
    demand = df["units_sold"].sum() + df["lost_sales_units"].sum()
    return dict(units_sold=int(df["units_sold"].sum()), lost_units=int(df["lost_sales_units"].sum()),
                stockout_rate_pct=round(100 * df["lost_sales_units"].sum() / demand, 2),
                avg_inventory_value_inr=round(avg_inv_value),
                turnover_period=round(sold_value / avg_inv_value, 2),
                carrying_cost_inr=round(avg_inv_value * CARRYING_RATE * DAYS / 365))

summary = turnover_and_stockout(stock)
summary["orders_total"] = len(po)
summary["orders_late_pct"] = round(100 * (po["actual_lead_time_days"] > po["promised_lead_time_days"]).mean(), 1)
summary["mean_lead_time_variance_days"] = round(
    (po["actual_lead_time_days"] - po["promised_lead_time_days"]).mean(), 2)
pd.DataFrame([summary]).to_csv(OUT / "kpi_summary.csv", index=False)

wh = stock.groupby("warehouse_id").apply(lambda d: pd.Series(turnover_and_stockout(d)))
wh.to_csv(OUT / "kpi_by_warehouse.csv")

sku = (stock.groupby(["sku", "warehouse_id"])
       .agg(units_sold=("units_sold", "sum"), lost_units=("lost_sales_units", "sum"))
       .reset_index())
sku["demand"] = sku["units_sold"] + sku["lost_units"]
sku["stockout_rate_pct"] = (100 * sku["lost_units"] / sku["demand"]).round(2)
sku["lost_sales_value_inr"] = (sku["lost_units"] * sku["sku"].map(cost)).round(0)
sku = sku.merge(dim[["sku", "product_name", "category"]], on="sku")
sku.sort_values("lost_sales_value_inr", ascending=False).to_csv(OUT / "kpi_by_sku.csv", index=False)

po["variance"] = po["actual_lead_time_days"] - po["promised_lead_time_days"]
lt = (po.assign(supplier=po["sku"].map(dim.set_index("sku")["supplier"]))
      .groupby("supplier")
      .agg(orders=("po_number", "count"), avg_variance_days=("variance", "mean"),
           late_pct=("variance", lambda s: round(100 * (s > 0).mean(), 1)))
      .round(2).reset_index())
lt.to_csv(OUT / "kpi_by_supplier_leadtime.csv", index=False)

monthly = (stock.set_index("date").groupby(pd.Grouper(freq="M"))
           .agg(units_sold=("units_sold", "sum"), lost_units=("lost_sales_units", "sum")))
monthly["stockout_rate_pct"] = (100 * monthly["lost_units"] /
                                (monthly["units_sold"] + monthly["lost_units"])).round(2)
monthly.to_csv(OUT / "monthly_trend.csv")

# ---------------- Charts (SVG = text, GitHub-friendly) ----------------
plt.rcParams.update({"font.size": 10, "axes.edgecolor": "#cccccc"})
cat = dim.merge(stock.groupby("sku")["units_sold"].sum().rename("sold"), on="sku")
cat["sold_value"] = cat["sold"] * cat["unit_cost_inr"]
inv_cat = stock.merge(dim[["sku", "category"]], on="sku")
inv_cat = inv_cat.groupby(["date", "category"])["value"].sum().groupby("category").mean()
tc = (cat.groupby("category")["sold_value"].sum() / inv_cat).sort_values()
fig, ax = plt.subplots(figsize=(7, 4)); tc.plot.barh(ax=ax, color="#1f6f8b")
ax.set_xlabel("Stock turnover (period)"); ax.set_title("Stock Turnover by Category")
fig.tight_layout(); fig.savefig(IMG / "turnover_by_category.svg", format="svg"); plt.close(fig)

fig, ax = plt.subplots(figsize=(7, 4))
lt.sort_values("avg_variance_days").plot.barh(x="supplier", y="avg_variance_days", ax=ax,
                                              color="#c0392b", legend=False)
ax.set_xlabel("Average lead time variance (days)"); ax.set_title("Lead Time Variance by Supplier")
fig.tight_layout(); fig.savefig(IMG / "lead_time_variance_by_supplier.svg", format="svg"); plt.close(fig)

top = sku.nlargest(8, "lost_sales_value_inr").iloc[::-1]
fig, ax = plt.subplots(figsize=(7, 4.5))
ax.barh(top["product_name"] + " (" + top["warehouse_id"] + ")", top["lost_sales_value_inr"] / 1000,
        color="#e67e22")
ax.set_xlabel("Lost sales value (₹ thousands)"); ax.set_title("Top Bottleneck SKUs by Lost Sales Value")
fig.tight_layout(); fig.savefig(IMG / "top_bottleneck_skus.svg", format="svg"); plt.close(fig)

fig, ax = plt.subplots(figsize=(7, 4))
ax.plot(monthly.index.strftime("%b"), monthly["stockout_rate_pct"], marker="o", color="#1f6f8b")
ax.set_ylabel("Stock-out rate (%)"); ax.set_title("Monthly Stock-Out Rate Trend")
fig.tight_layout(); fig.savefig(IMG / "monthly_stockout_trend.svg", format="svg"); plt.close(fig)

def inr(n):  # Indian digit grouping: 3,76,81,254
    s = str(int(round(n))); 
    if len(s) <= 3: return "₹" + s
    head, tail = s[:-3], s[-3:]
    parts = []
    while len(head) > 2: parts.insert(0, head[-2:]); head = head[:-2]
    if head: parts.insert(0, head)
    return "₹" + ",".join(parts + [tail])

print("SUMMARY:", {k: summary[k] for k in ("units_sold", "lost_units", "stockout_rate_pct",
                                           "turnover_period", "orders_late_pct")})
print(f"Avg inventory value: {inr(summary['avg_inventory_value_inr'])} | "
      f"Carrying cost: {inr(summary['carrying_cost_inr'])}")
print("\nBY WAREHOUSE:\n", wh.to_string())
print("\nTOP BOTTLENECKS:\n", sku.nlargest(5, "lost_sales_value_inr")[
    ["product_name", "warehouse_id", "stockout_rate_pct", "lost_units", "lost_sales_value_inr"]].to_string(index=False))
print("\nSUPPLIER LEAD TIME:\n", lt.to_string(index=False))
