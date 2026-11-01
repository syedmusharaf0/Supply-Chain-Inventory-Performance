"""KPI analysis: compute supply chain KPIs with Pandas and export results + charts.

Mirrors sql/02_kpi_queries.sql so the same KPIs can be produced from either
SQL or Python. All monetary values are in Indian Rupees (INR).
All tables use the friendly display column names (see data/data_dictionary.md).
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
stock = pd.read_csv(BASE / "data/fact_daily_stock.csv", parse_dates=["Stock Date"])
po = pd.read_csv(BASE / "data/fact_purchase_orders.csv", parse_dates=["Order Date", "Delivery Date"])
cost = dim.set_index("Product Code")["Unit Cost (INR)"]
stock["Stock Value (INR)"] = stock["Closing Stock (units)"] * stock["Product Code"].map(cost)
stock["Sales Value (INR)"] = stock["Units Sold"] * stock["Product Code"].map(cost)
DAYS = (stock["Stock Date"].max() - stock["Stock Date"].min()).days + 1

def kpis_for(df: pd.DataFrame) -> dict:
    sold_value = df["Sales Value (INR)"].sum()
    avg_inv_value = df.groupby("Stock Date")["Stock Value (INR)"].sum().mean()
    demand = df["Units Sold"].sum() + df["Lost Sales (units)"].sum()
    return dict(**{
        "Total Units Sold": int(df["Units Sold"].sum()),
        "Total Lost Units": int(df["Lost Sales (units)"].sum()),
        "Stock-Out Rate %": round(100 * df["Lost Sales (units)"].sum() / demand, 2),
        "Average Inventory Value (INR)": round(avg_inv_value),
        # annualised turnover so periods of any length stay comparable
        "Stock Turnover Ratio": round(sold_value / avg_inv_value * 365 / DAYS, 2),
        "Carrying Cost (INR)": round(avg_inv_value * CARRYING_RATE * DAYS / 365),
        "Total Sales Value (INR)": round(sold_value)})

summary = kpis_for(stock)
summary["Total Purchase Orders"] = len(po)
summary["Late Orders %"] = round(
    100 * (po["Actual Lead Time (days)"] > po["Promised Lead Time (days)"]).mean(), 1)
summary["Average Lead Time Variance (days)"] = round(
    (po["Actual Lead Time (days)"] - po["Promised Lead Time (days)"]).mean(), 2)
pd.DataFrame([summary]).to_csv(OUT / "kpi_summary.csv", index=False)

wh = stock.groupby("Warehouse Name").apply(lambda d: pd.Series(kpis_for(d)))
wh.to_csv(OUT / "kpi_by_warehouse.csv")

sku = (stock.groupby(["Product Code", "Warehouse Name"])
       .agg(**{"Units Sold": ("Units Sold", "sum"), "Lost Units": ("Lost Sales (units)", "sum")})
       .reset_index())
sku["Total Demand (units)"] = sku["Units Sold"] + sku["Lost Units"]
sku["Stock-Out Rate %"] = (100 * sku["Lost Units"] / sku["Total Demand (units)"]).round(2)
sku["Lost Sales Value (INR)"] = (sku["Lost Units"] * sku["Product Code"].map(cost)).round(0)
sku = sku.merge(dim[["Product Code", "Product Name", "Product Category"]], on="Product Code")
sku = sku[["Product Code", "Product Name", "Product Category", "Warehouse Name", "Units Sold",
           "Lost Units", "Total Demand (units)", "Stock-Out Rate %", "Lost Sales Value (INR)"]]
sku.sort_values("Lost Sales Value (INR)", ascending=False).to_csv(OUT / "kpi_by_sku.csv", index=False)

po["Variance (days)"] = po["Actual Lead Time (days)"] - po["Promised Lead Time (days)"]
lt = (po.assign(**{"Supplier Name": po["Product Code"].map(dim.set_index("Product Code")["Supplier Name"])})
      .groupby("Supplier Name")
      .agg(**{"Total Orders": ("Purchase Order ID", "count"),
              "Average Variance (days)": ("Variance (days)", "mean"),
              "Late Orders %": ("Variance (days)", lambda s: round(100 * (s > 0).mean(), 1))})
      .round(2).reset_index())
lt.to_csv(OUT / "kpi_by_supplier_leadtime.csv", index=False)

# ---------- Time comparisons with LAG (shift in Pandas) ----------
def add_growth(df: pd.DataFrame, cols: list[str], lags: dict[int, str]) -> pd.DataFrame:
    df = df.copy()
    for lag, label in lags.items():
        for c in cols:
            prev = df[c].shift(lag)
            df[f"{c} {label} Growth %"] = (100 * (df[c] - prev) / prev).round(2)
    return df

weekly = (stock.set_index("Stock Date").groupby(pd.Grouper(freq="W"))
          .agg(**{"Units Sold": ("Units Sold", "sum"), "Lost Units": ("Lost Sales (units)", "sum"),
                  "Sales Value (INR)": ("Sales Value (INR)", "sum")}))
weekly["Stock-Out Rate %"] = (100 * weekly["Lost Units"] /
                              (weekly["Units Sold"] + weekly["Lost Units"])).round(2)
weekly = add_growth(weekly.reset_index().rename(columns={"Stock Date": "Week Ending"}),
                    ["Units Sold", "Sales Value (INR)"], {1: "WoW"})
weekly.to_csv(OUT / "weekly_trend.csv", index=False)

monthly = (stock.set_index("Stock Date").groupby(pd.Grouper(freq="M"))
           .agg(**{"Units Sold": ("Units Sold", "sum"), "Lost Units": ("Lost Sales (units)", "sum"),
                   "Sales Value (INR)": ("Sales Value (INR)", "sum")}))
monthly["Stock-Out Rate %"] = (100 * monthly["Lost Units"] /
                               (monthly["Units Sold"] + monthly["Lost Units"])).round(2)
monthly = add_growth(monthly.reset_index().rename(columns={"Stock Date": "Month"}),
                     ["Units Sold", "Sales Value (INR)"], {1: "MoM", 12: "YoY"})
monthly.to_csv(OUT / "monthly_trend.csv", index=False)

daily_totals = stock.groupby("Stock Date")["Stock Value (INR)"].sum()
avg_inv_by_year = daily_totals.groupby(daily_totals.index.year).mean().round(0)
yearly = (stock.assign(Year=stock["Stock Date"].dt.year)
          .groupby("Year")
          .agg(**{"Units Sold": ("Units Sold", "sum"), "Lost Units": ("Lost Sales (units)", "sum"),
                  "Sales Value (INR)": ("Sales Value (INR)", "sum")}).reset_index())
yearly["Average Inventory Value (INR)"] = yearly["Year"].map(avg_inv_by_year)
yearly["Period Note"] = yearly["Year"].apply(
    lambda y: "Jan-Jun only (partial year)" if y == 2025 else "Full year")
yearly["Stock-Out Rate %"] = (100 * yearly["Lost Units"] /
                              (yearly["Units Sold"] + yearly["Lost Units"])).round(2)
yearly = add_growth(yearly, ["Units Sold", "Sales Value (INR)"], {1: "YoY"})
yearly.to_csv(OUT / "yearly_summary.csv", index=False)

# ---------------- Charts (SVG = text, GitHub-friendly) ----------------
plt.rcParams.update({"font.size": 10, "axes.edgecolor": "#cccccc"})
cat = dim.merge(stock.groupby("Product Code")["Units Sold"].sum().rename("sold"), on="Product Code")
cat["sold_value"] = cat["sold"] * cat["Unit Cost (INR)"]
inv_cat = stock.merge(dim[["Product Code", "Product Category"]], on="Product Code")
inv_cat = inv_cat.groupby(["Stock Date", "Product Category"])["Stock Value (INR)"].sum().groupby("Product Category").mean()
tc = (cat.groupby("Product Category")["sold_value"].sum() / inv_cat * 365 / DAYS).sort_values()
fig, ax = plt.subplots(figsize=(7, 4)); tc.plot.barh(ax=ax, color="#1f6f8b")
ax.set_xlabel("Stock turnover ratio (annualised)"); ax.set_title("Stock Turnover by Product Category")
fig.tight_layout(); fig.savefig(IMG / "turnover_by_category.svg", format="svg"); plt.close(fig)

fig, ax = plt.subplots(figsize=(7, 4))
lt.sort_values("Average Variance (days)").plot.barh(x="Supplier Name", y="Average Variance (days)",
                                                   ax=ax, color="#c0392b", legend=False)
ax.set_xlabel("Average lead time variance (days)"); ax.set_title("Lead Time Variance by Supplier")
fig.tight_layout(); fig.savefig(IMG / "lead_time_variance_by_supplier.svg", format="svg"); plt.close(fig)

top = sku.nlargest(8, "Lost Sales Value (INR)").iloc[::-1]
fig, ax = plt.subplots(figsize=(7, 4.5))
ax.barh(top["Product Name"] + " (" + top["Warehouse Name"] + ")", top["Lost Sales Value (INR)"] / 1000,
        color="#e67e22")
ax.set_xlabel("Lost sales value (₹ thousands)"); ax.set_title("Top Bottleneck Products by Lost Sales Value")
fig.tight_layout(); fig.savefig(IMG / "top_bottleneck_skus.svg", format="svg"); plt.close(fig)

recent = monthly.tail(12)
fig, ax = plt.subplots(figsize=(7, 4))
ax.plot(recent["Month"].dt.strftime("%b %y"), recent["Stock-Out Rate %"], marker="o", color="#1f6f8b")
ax.set_ylabel("Stock-out rate (%)"); ax.set_title("Monthly Stock-Out Rate Trend (last 12 months)")
fig.tight_layout(); fig.savefig(IMG / "monthly_stockout_trend.svg", format="svg"); plt.close(fig)

fig, ax = plt.subplots(figsize=(7, 4))
ax.bar(recent["Month"].dt.strftime("%b %y"), recent["Units Sold YoY Growth %"], color="#2e7d32")
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

print("PERIOD:", stock["Stock Date"].min().date(), "to", stock["Stock Date"].max().date(), f"({DAYS} days)")
print("SUMMARY:", summary)
print("\nBY WAREHOUSE:\n", wh.to_string())
print("\nYEARLY:\n", yearly.to_string(index=False))
print("\nLATEST MONTH:", monthly.iloc[-1].to_dict())
