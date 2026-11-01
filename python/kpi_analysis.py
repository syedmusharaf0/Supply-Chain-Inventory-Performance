"""KPI analysis: compute supply chain KPIs with Pandas and export results + charts.

Mirrors sql/02_kpi_queries.sql so the same KPIs can be produced from either
SQL or Python. All monetary values are in Indian Rupees (INR).
Includes LAG-style time comparisons: weekly (week-over-week), monthly
(month-over-month and year-over-year) and yearly growth percentages —
in SQL these use the LAG() window function; in Pandas, shift().
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
CARRYING_RATE = 0.20  # 20% per year carrying-cost assumption

dim = pd.read_csv(BASE / "data/dim_products.csv")
stock = pd.read_csv(BASE / "data/fact_daily_stock.csv", parse_dates=["stock_date"])
po = pd.read_csv(BASE / "data/fact_purchase_orders.csv", parse_dates=["order_date", "delivery_date"])
cost = dim.set_index("product_code")["unit_cost_inr"]
stock["stock_value_inr"] = stock["closing_stock_units"] * stock["product_code"].map(cost)
stock["sales_value_inr"] = stock["units_sold"] * stock["product_code"].map(cost)
DAYS = (stock["stock_date"].max() - stock["stock_date"].min()).days + 1

def kpis_for(df: pd.DataFrame) -> dict:
    sold_value = df["sales_value_inr"].sum()
    avg_inv_value = df.groupby("stock_date")["stock_value_inr"].sum().mean()
    demand = df["units_sold"].sum() + df["lost_sales_units"].sum()
    return dict(total_units_sold=int(df["units_sold"].sum()),
                total_lost_units=int(df["lost_sales_units"].sum()),
                stockout_rate_percent=round(100 * df["lost_sales_units"].sum() / demand, 2),
                average_inventory_value_inr=round(avg_inv_value),
                # annualised turnover so periods of any length stay comparable
                stock_turnover_ratio=round(sold_value / avg_inv_value * 365 / DAYS, 2),
                carrying_cost_inr=round(avg_inv_value * CARRYING_RATE * DAYS / 365))

summary = kpis_for(stock)
summary["total_purchase_orders"] = len(po)
summary["late_orders_percent"] = round(
    100 * (po["actual_lead_time_days"] > po["promised_lead_time_days"]).mean(), 1)
summary["average_lead_time_variance_days"] = round(
    (po["actual_lead_time_days"] - po["promised_lead_time_days"]).mean(), 2)
pd.DataFrame([summary]).to_csv(OUT / "kpi_summary.csv", index=False)

wh = stock.groupby("warehouse_name").apply(lambda d: pd.Series(kpis_for(d)))
wh.to_csv(OUT / "kpi_by_warehouse.csv")

sku = (stock.groupby(["product_code", "warehouse_name"])
       .agg(units_sold=("units_sold", "sum"), lost_units=("lost_sales_units", "sum"))
       .reset_index())
sku["total_demand_units"] = sku["units_sold"] + sku["lost_units"]
sku["stockout_rate_percent"] = (100 * sku["lost_units"] / sku["total_demand_units"]).round(2)
sku["lost_sales_value_inr"] = (sku["lost_units"] * sku["product_code"].map(cost)).round(0)
sku = sku.merge(dim[["product_code", "product_name", "product_category"]], on="product_code")
sku.sort_values("lost_sales_value_inr", ascending=False).to_csv(OUT / "kpi_by_sku.csv", index=False)

po["variance_days"] = po["actual_lead_time_days"] - po["promised_lead_time_days"]
lt = (po.assign(supplier_name=po["product_code"].map(dim.set_index("product_code")["supplier_name"]))
      .groupby("supplier_name")
      .agg(total_orders=("purchase_order_id", "count"),
           average_variance_days=("variance_days", "mean"),
           late_orders_percent=("variance_days", lambda s: round(100 * (s > 0).mean(), 1)))
      .round(2).reset_index())
lt.to_csv(OUT / "kpi_by_supplier_leadtime.csv", index=False)

# ---------- Time comparisons with LAG (shift in Pandas) ----------
def add_growth(df: pd.DataFrame, cols: list[str], lags: dict[int, str]) -> pd.DataFrame:
    df = df.copy()
    for lag, label in lags.items():
        for c in cols:
            prev = df[c].shift(lag)
            df[f"{c}_{label}_growth_percent"] = (100 * (df[c] - prev) / prev).round(2)
    return df

weekly = (stock.set_index("stock_date").groupby(pd.Grouper(freq="W"))
          .agg(units_sold=("units_sold", "sum"), lost_units=("lost_sales_units", "sum"),
               sales_value_inr=("sales_value_inr", "sum")))
weekly["stockout_rate_percent"] = (100 * weekly["lost_units"] /
                                   (weekly["units_sold"] + weekly["lost_units"])).round(2)
weekly = add_growth(weekly.reset_index().rename(columns={"stock_date": "week_ending"}),
                    ["units_sold", "sales_value_inr"], {1: "wow"})
weekly.to_csv(OUT / "weekly_trend.csv", index=False)

monthly = (stock.set_index("stock_date").groupby(pd.Grouper(freq="M"))
           .agg(units_sold=("units_sold", "sum"), lost_units=("lost_sales_units", "sum"),
                sales_value_inr=("sales_value_inr", "sum")))
monthly["stockout_rate_percent"] = (100 * monthly["lost_units"] /
                                    (monthly["units_sold"] + monthly["lost_units"])).round(2)
monthly = add_growth(monthly.reset_index().rename(columns={"stock_date": "month"}),
                     ["units_sold", "sales_value_inr"], {1: "mom", 12: "yoy"})
monthly.to_csv(OUT / "monthly_trend.csv", index=False)

daily_totals = stock.groupby("stock_date")["stock_value_inr"].sum()
avg_inv_by_year = daily_totals.groupby(daily_totals.index.year).mean().round(0)
yearly = (stock.assign(year=stock["stock_date"].dt.year)
          .groupby("year")
          .agg(units_sold=("units_sold", "sum"), lost_units=("lost_sales_units", "sum"),
               sales_value_inr=("sales_value_inr", "sum")).reset_index())
yearly["average_inventory_value_inr"] = yearly["year"].map(avg_inv_by_year)
yearly["period_note"] = yearly["year"].apply(
    lambda y: "Jan-Jun only (partial year)" if y == 2025 else "Full year")
yearly["stockout_rate_percent"] = (100 * yearly["lost_units"] /
                                   (yearly["units_sold"] + yearly["lost_units"])).round(2)
yearly = add_growth(yearly, ["units_sold", "sales_value_inr"], {1: "yoy"})
yearly.to_csv(OUT / "yearly_summary.csv", index=False)

# ---------------- Charts (SVG = text, GitHub-friendly) ----------------
plt.rcParams.update({"font.size": 10, "axes.edgecolor": "#cccccc"})
cat = dim.merge(stock.groupby("product_code")["units_sold"].sum().rename("sold"), on="product_code")
cat["sold_value"] = cat["sold"] * cat["unit_cost_inr"]
inv_cat = stock.merge(dim[["product_code", "product_category"]], on="product_code")
inv_cat = inv_cat.groupby(["stock_date", "product_category"])["stock_value_inr"].sum().groupby("product_category").mean()
tc = (cat.groupby("product_category")["sold_value"].sum() / inv_cat * 365 / DAYS).sort_values()
fig, ax = plt.subplots(figsize=(7, 4)); tc.plot.barh(ax=ax, color="#1f6f8b")
ax.set_xlabel("Stock turnover ratio (annualised)"); ax.set_title("Stock Turnover by Product Category")
fig.tight_layout(); fig.savefig(IMG / "turnover_by_category.svg", format="svg"); plt.close(fig)

fig, ax = plt.subplots(figsize=(7, 4))
lt.sort_values("average_variance_days").plot.barh(x="supplier_name", y="average_variance_days",
                                                 ax=ax, color="#c0392b", legend=False)
ax.set_xlabel("Average lead time variance (days)"); ax.set_title("Lead Time Variance by Supplier")
fig.tight_layout(); fig.savefig(IMG / "lead_time_variance_by_supplier.svg", format="svg"); plt.close(fig)

top = sku.nlargest(8, "lost_sales_value_inr").iloc[::-1]
fig, ax = plt.subplots(figsize=(7, 4.5))
ax.barh(top["product_name"] + " (" + top["warehouse_name"] + ")", top["lost_sales_value_inr"] / 1000,
        color="#e67e22")
ax.set_xlabel("Lost sales value (₹ thousands)"); ax.set_title("Top Bottleneck Products by Lost Sales Value")
fig.tight_layout(); fig.savefig(IMG / "top_bottleneck_skus.svg", format="svg"); plt.close(fig)

recent = monthly.tail(12)
fig, ax = plt.subplots(figsize=(7, 4))
ax.plot(recent["month"].dt.strftime("%b %y"), recent["stockout_rate_percent"], marker="o", color="#1f6f8b")
ax.set_ylabel("Stock-out rate (%)"); ax.set_title("Monthly Stock-Out Rate Trend (last 12 months)")
fig.tight_layout(); fig.savefig(IMG / "monthly_stockout_trend.svg", format="svg"); plt.close(fig)

fig, ax = plt.subplots(figsize=(7, 4))
ax.bar(recent["month"].dt.strftime("%b %y"), recent["units_sold_yoy_growth_percent"], color="#2e7d32")
ax.axhline(0, color="#888", linewidth=.8)
ax.set_ylabel("YoY growth (%)"); ax.set_title("Units Sold — Year-over-Year Growth by Month")
fig.tight_layout(); fig.savefig(IMG / "yoy_growth_trend.svg", format="svg"); plt.close(fig)

def inr(n):
    s = str(int(round(n)))
    if len(s) <= 3: return "₹" + s
    head, tail = s[:-3], s[-3:]
    parts = []
    while len(head) > 2: parts.insert(0, head[-2:]); head = head[:-2]
    if head: parts.insert(0, head)
    return "₹" + ",".join(parts + [tail])

print("PERIOD:", stock["stock_date"].min().date(), "to", stock["stock_date"].max().date(), f"({DAYS} days)")
print("SUMMARY:", {k: summary[k] for k in ("total_units_sold", "total_lost_units",
                                           "stockout_rate_percent", "stock_turnover_ratio",
                                           "late_orders_percent")})
print(f"Average inventory value: {inr(summary['average_inventory_value_inr'])} | "
      f"Carrying cost: {inr(summary['carrying_cost_inr'])}")
print("\nBY WAREHOUSE:\n", wh.to_string())
print("\nYEARLY:\n", yearly.to_string(index=False))
print("\nLATEST MONTH:", monthly.iloc[-1].to_dict())
print("\nTOP BOTTLENECKS:\n", sku.nlargest(5, "lost_sales_value_inr")[
    ["product_name", "warehouse_name", "stockout_rate_percent", "lost_units",
     "lost_sales_value_inr"]].to_string(index=False))
