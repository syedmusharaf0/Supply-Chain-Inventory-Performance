"""Build ONE full dashboard image (images/power_bi_dashboard.svg) for the README.

A complete Power BI-style dashboard composed as a single figure: header band,
KPI card row, and six chart panels — so the GitHub README opens with the full
dashboard, followed by the individual graphs and tables.
Run AFTER python/kpi_analysis.py. A PNG twin is written to /tmp for preview.
"""
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
OUT, IMG = BASE / "outputs", BASE / "images"
NAVY, TEAL, AMBER, RED, GREEN, GREY = "#0d2b45", "#1f6f8b", "#ffb703", "#c0392b", "#2e7d32", "#61707e"

s = pd.read_csv(OUT / "kpi_summary.csv").iloc[0]
wh = pd.read_csv(OUT / "kpi_by_warehouse.csv")
sku = pd.read_csv(OUT / "kpi_by_sku.csv")
lt = pd.read_csv(OUT / "kpi_by_supplier_leadtime.csv")
monthly = pd.read_csv(OUT / "monthly_trend.csv", parse_dates=["Month"])
dim = pd.read_csv(BASE / "data/dim_products.csv")
stock = pd.read_csv(BASE / "data/fact_daily_stock.csv", parse_dates=["Stock Date"])
cost = dim.set_index("Product Code")["Unit Cost (INR)"]
stock["Sales Value (INR)"] = stock["Units Sold"] * stock["Product Code"].map(cost)
stock["Stock Value (INR)"] = stock["Closing Stock (units)"] * stock["Product Code"].map(cost)
DAYS = (stock["Stock Date"].max() - stock["Stock Date"].min()).days + 1
cat = dim.merge(stock.groupby("Product Code")["Units Sold"].sum().rename("sold"), on="Product Code")
cat["sold_value"] = cat["sold"] * cat["Unit Cost (INR)"]
inv_cat = stock.merge(dim[["Product Code", "Product Category"]], on="Product Code")
inv_cat = inv_cat.groupby(["Stock Date", "Product Category"])["Stock Value (INR)"].sum().groupby("Product Category").mean()
turnover_cat = (cat.groupby("Product Category")["sold_value"].sum() / inv_cat * 365 / DAYS).sort_values()

def inr_short(n):
    n = float(n)
    if abs(n) >= 1e7: return f"₹{n/1e7:.2f} Cr"
    if abs(n) >= 1e5: return f"₹{n/1e5:.1f} L"
    return f"₹{n:,.0f}"

plt.rcParams.update({"font.size": 11, "axes.edgecolor": "#d5dde3", "axes.linewidth": 0.8,
                     "text.color": "#1c2733", "axes.labelcolor": GREY, "xtick.color": GREY,
                     "ytick.color": GREY, "axes.titlesize": 13, "axes.titleweight": "bold",
                     "axes.titlecolor": NAVY})
fig = plt.figure(figsize=(16, 11.6))
fig.patch.set_facecolor("white")
gs = fig.add_gridspec(4, 3, height_ratios=[0.62, 0.85, 1.55, 1.55],
                      hspace=0.50, wspace=0.38, left=0.084, right=0.978, top=0.965, bottom=0.062)

# ---------- header band ----------
axh = fig.add_subplot(gs[0, :]); axh.axis("off")
axh.add_patch(FancyBboxPatch((0, 0.18), 1, 0.78, boxstyle="round,pad=0.004,rounding_size=0.012",
                             transform=axh.transAxes, facecolor=NAVY, edgecolor="none"))
axh.text(0.018, 0.70, "Supply Chain & Inventory Performance — Power BI Dashboard",
         transform=axh.transAxes, color="white", fontsize=19, fontweight="bold", va="center")
axh.text(0.018, 0.34, "Mumbai Central  ·  Delhi Hub  ·  Bengaluru Hub     |     Jan 2023 – Jun 2025     |     All values in INR (₹)",
         transform=axh.transAxes, color="#cfe3ec", fontsize=12.5, va="center")
axh.text(0.982, 0.52, "Syed Musharaf · Data Analyst", transform=axh.transAxes,
         color=AMBER, fontsize=12.5, fontweight="bold", va="center", ha="right")

# ---------- KPI cards ----------
kpis = [("TOTAL SALES", inr_short(s["Total Sales Value (INR)"]), "Jan 2023 – Jun 2025"),
        ("UNITS SOLD", f"{int(s['Total Units Sold']):,}", "across 24 products"),
        ("STOCK-OUT RATE", f"{s['Stock-Out Rate %']:.2f}%", f"{int(s['Total Lost Units']):,} units lost"),
        ("STOCK TURNOVER", f"{s['Stock Turnover Ratio']:.1f}×", "annualised"),
        ("AVG INVENTORY VALUE", inr_short(s["Average Inventory Value (INR)"]), "daily average"),
        ("CARRYING COST", inr_short(s["Carrying Cost (INR)"]), "20% per year"),
        ("LATE ORDERS", f"{s['Late Orders %']:.1f}%", f"of {int(s['Total Purchase Orders'])} orders")]
axk = fig.add_subplot(gs[1, :]); axk.axis("off"); axk.set_xlim(0, 7); axk.set_ylim(0, 1)
for i, (label, value, sub) in enumerate(kpis):
    axk.add_patch(FancyBboxPatch((i + 0.04, 0.10), 0.92, 0.84,
                                 boxstyle="round,pad=0.01,rounding_size=0.05",
                                 facecolor="#f2f7fa", edgecolor="#d5dde3", linewidth=1))
    axk.text(i + 0.5, 0.76, label, ha="center", fontsize=8.6, color=GREY, fontweight="bold")
    axk.text(i + 0.5, 0.47, value, ha="center", fontsize=15.5, color=NAVY, fontweight="bold")
    axk.text(i + 0.5, 0.22, sub, ha="center", fontsize=8.4, color=GREY)

def panel(ax, title):
    ax.set_title(title, loc="left", pad=10)
    ax.set_facecolor("white")
    for sp in ("top", "right"): ax.spines[sp].set_visible(False)
    ax.grid(axis="x", color="#eef2f5", linewidth=0.8); ax.set_axisbelow(True)

# ---------- row 1 of charts ----------
ax = fig.add_subplot(gs[2, 0]); panel(ax, "Stock Turnover by Product Category")
turnover_cat.plot.barh(ax=ax, color=TEAL); ax.set_xlabel("Turnover ratio (annualised)"); ax.tick_params(labelsize=10)

ax = fig.add_subplot(gs[2, 1]); panel(ax, "Monthly Stock-Out Rate (last 18 months)")
r18 = monthly.tail(18)
ax.plot(r18["Month"].dt.strftime("%b %y"), r18["Stock-Out Rate %"], marker="o", ms=3.5, color=TEAL, lw=1.8)
ax.grid(axis="y", color="#eef2f5", linewidth=0.8)
plt.setp(ax.get_xticklabels(), rotation=45, ha="left", fontsize=8.5); ax.set_ylabel("Stock-out rate (%)")

ax = fig.add_subplot(gs[2, 2]); panel(ax, "Units Sold — YoY Growth by Month")
r12 = monthly.tail(12)
colors = [GREEN if v >= 0 else RED for v in r12["Units Sold YoY Growth %"]]
ax.bar(r12["Month"].dt.strftime("%b %y"), r12["Units Sold YoY Growth %"], color=colors)
ax.axhline(0, color="#9fb2bf", lw=0.9); ax.grid(axis="y", color="#eef2f5", linewidth=0.8)
plt.setp(ax.get_xticklabels(), rotation=45, ha="left", fontsize=8.5); ax.set_ylabel("YoY growth (%)")

# ---------- row 2 of charts ----------
ax = fig.add_subplot(gs[3, 0]); panel(ax, "Stock-Out Rate by Warehouse")
w = wh.sort_values("Stock-Out Rate %")
ax.barh(w["Warehouse Name"], w["Stock-Out Rate %"], color=[RED if x > 8 else AMBER if x > 3 else TEAL for x in w["Stock-Out Rate %"]])
ax.set_xlabel("Stock-out rate (%)")

ax = fig.add_subplot(gs[3, 1]); panel(ax, "Lead Time Variance by Supplier")
l = lt.sort_values("Average Variance (days)")
ax.barh(l["Supplier Name"], l["Average Variance (days)"], color=RED); ax.tick_params(labelsize=9.5)
ax.set_xlabel("Average variance (days late)")

ax = fig.add_subplot(gs[3, 2]); panel(ax, "Top Bottleneck Products (lost sales ₹)")
top = sku.sort_values("Lost Sales Value (INR)").tail(5)
labels = top["Product Name"] + " (" + top["Warehouse Name"].str.replace(" Central", "").str.replace(" Hub", "") + ")"
ax.barh(labels, top["Lost Sales Value (INR)"] / 1e7, color="#e67e22"); ax.tick_params(labelsize=9.5)
ax.set_xlabel("Lost sales value (₹ Cr)")

fig.text(0.5, 0.008, "Built with PostgreSQL · Python (Pandas, SQLAlchemy) · Power BI (DAX)   |   Synthetic sample data (seed 42) for demonstration — no real company data",
         ha="center", fontsize=10, color=GREY)
fig.savefig(IMG / "power_bi_dashboard.svg", format="svg")
fig.savefig("/tmp/power_bi_dashboard.png", format="png", dpi=110)
print("dashboard image written:", (IMG / 'power_bi_dashboard.svg').stat().st_size / 1024, "KB (svg)")
