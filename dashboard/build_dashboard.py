"""Build the standalone executive dashboard: dashboard/dashboard.html

Reads the KPI outputs (outputs/*.csv) and the SVG charts (images/*.svg) and
produces one self-contained HTML file — no server, no dependencies.
Run AFTER python/kpi_analysis.py.
"""
import pandas as pd
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
OUT, IMG = BASE / "outputs", BASE / "images"
WH_NAMES = {"WH-MUM": "Mumbai Central", "WH-DEL": "Delhi Hub", "WH-BLR": "Bengaluru Hub"}

def inr(n):
    s = str(int(round(float(n))))
    if len(s) <= 3: return "₹" + s
    head, tail = s[:-3], s[-3:]
    parts = []
    while len(head) > 2: parts.insert(0, head[-2:]); head = head[:-2]
    if head: parts.insert(0, head)
    return "₹" + ",".join(parts + [tail])

def inr_short(n):
    n = float(n)
    if abs(n) >= 1e7: return f"₹{n/1e7:.2f} Cr"
    if abs(n) >= 1e5: return f"₹{n/1e5:.1f} L"
    return inr(n)

def svg_inline(path):
    txt = Path(path).read_text(encoding="utf-8")
    i = txt.find("<svg")
    return txt[i:] if i >= 0 else txt

s = pd.read_csv(OUT / "kpi_summary.csv").iloc[0]
wh = pd.read_csv(OUT / "kpi_by_warehouse.csv")
sku = pd.read_csv(OUT / "kpi_by_sku.csv")
top = sku.nlargest(8, "lost_sales_value_inr")
mum_share = 100 * wh.loc[wh.warehouse_id == "WH-MUM", "lost_units"].iloc[0] / s["lost_units"]
worst = sku.loc[sku["lost_sales_value_inr"].idxmax()]
best_wh = wh.loc[wh["avg_inventory_value_inr"].idxmax()]

cards = [
    ("Units Sold", f"{int(s['units_sold']):,}", "Jan – Jun 2025"),
    ("Stock-Out Rate", f"{s['stockout_rate_pct']:.2f}%", f"{int(s['lost_units']):,} units lost"),
    ("Stock Turnover", f"{s['turnover_period']:.1f}×", "period (181 days)"),
    ("Avg Inventory Value", inr_short(s["avg_inventory_value_inr"]), inr(s["avg_inventory_value_inr"])),
    ("Carrying Cost", inr_short(s["carrying_cost_inr"]), "20% p.a. assumption"),
    ("Late Orders", f"{s['orders_late_pct']:.1f}%", f"of {int(s['orders_total'])} purchase orders"),
]
cards_html = "".join(
    f'<div class="card"><div class="kpi-label">{a}</div><div class="kpi-value">{b}</div>'
    f'<div class="kpi-sub">{c}</div></div>' for a, b, c in cards)

wh_rows = "".join(
    f"<tr><td>{WH_NAMES[r.warehouse_id]}</td><td>{int(r.units_sold):,}</td>"
    f"<td>{r.stockout_rate_pct:.2f}%</td><td>{r.turnover_period:.2f}×</td>"
    f"<td>{inr(r.avg_inventory_value_inr)}</td><td>{int(r.lost_units):,}</td></tr>"
    for r in wh.sort_values("stockout_rate_pct", ascending=False).itertuples())

sku_rows = "".join(
    f"<tr><td>{r.product_name}</td><td>{r.category}</td><td>{WH_NAMES[r.warehouse_id]}</td>"
    f"<td>{r.stockout_rate_pct:.2f}%</td><td>{int(r.lost_units):,}</td>"
    f"<td>{inr(r.lost_sales_value_inr)}</td></tr>" for r in top.itertuples())

charts = "".join(
    f'<div class="chart"><h3>{t}</h3>{svg_inline(IMG / f)}</div>'
    for f, t in [("turnover_by_category.svg", "Stock Turnover by Category"),
                 ("monthly_stockout_trend.svg", "Monthly Stock-Out Rate Trend"),
                 ("lead_time_variance_by_supplier.svg", "Lead Time Variance by Supplier"),
                 ("top_bottleneck_skus.svg", "Top Bottleneck SKUs by Lost Sales Value")])

html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Supply Chain &amp; Inventory Performance Dashboard — Syed Musharaf</title>
<style>
* {{ box-sizing: border-box; margin: 0; font-family: 'Segoe UI', Arial, sans-serif; }}
body {{ background: #f2f5f8; color: #1c2733; }}
header {{ background: linear-gradient(120deg, #0d2b45, #1f6f8b); color: #fff; padding: 28px 36px; }}
header h1 {{ font-size: 26px; }} header p {{ opacity: .85; margin-top: 6px; font-size: 14px; }}
.badge {{ display: inline-block; background: #ffb703; color: #0d2b45; font-weight: 600;
  padding: 3px 12px; border-radius: 20px; font-size: 12px; margin-top: 12px; }}
main {{ max-width: 1180px; margin: 0 auto; padding: 24px 20px 40px; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 14px; }}
.card {{ background: #fff; border-radius: 12px; padding: 18px; box-shadow: 0 1px 4px rgba(13,43,69,.10); }}
.kpi-label {{ font-size: 12px; text-transform: uppercase; letter-spacing: .06em; color: #61707e; }}
.kpi-value {{ font-size: 27px; font-weight: 700; color: #0d2b45; margin: 6px 0 2px; }}
.kpi-sub {{ font-size: 12px; color: #61707e; }}
h2 {{ font-size: 18px; color: #0d2b45; margin: 28px 0 12px; }}
.panel {{ background: #fff; border-radius: 12px; padding: 20px; box-shadow: 0 1px 4px rgba(13,43,69,.10); }}
.insights {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 14px; }}
.insight {{ background: #fff7e8; border-left: 4px solid #ffb703; border-radius: 8px; padding: 14px 16px; font-size: 14px; line-height: 1.5; }}
.charts {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(420px, 1fr)); gap: 14px; }}
.chart {{ background: #fff; border-radius: 12px; padding: 16px; box-shadow: 0 1px 4px rgba(13,43,69,.10); }}
.chart h3 {{ font-size: 14px; color: #0d2b45; margin-bottom: 8px; }}
.chart svg {{ width: 100%; height: auto; }}
table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
th {{ text-align: left; padding: 9px 10px; background: #0d2b45; color: #fff; }}
td {{ padding: 8px 10px; border-bottom: 1px solid #e5ebf0; }}
tr:nth-child(even) td {{ background: #f7fafc; }}
footer {{ text-align: center; color: #61707e; font-size: 12.5px; padding: 22px; line-height: 1.6; }}
@media print {{ body {{ background: #fff; }} }}
</style></head><body>
<header>
  <h1>Supply Chain &amp; Inventory Performance</h1>
  <p>Executive Dashboard · Jan – Jun 2025 · Mumbai Central · Delhi Hub · Bengaluru Hub · All values in INR (₹)</p>
  <span class="badge">Syed Musharaf · Data Analyst</span>
</header>
<main>
  <div class="grid">{cards_html}</div>

  <h2>Key Insights</h2>
  <div class="insights">
    <div class="insight"><strong>Mumbai Central is the bottleneck.</strong>
      It holds the leanest stock yet the highest demand, producing a
      {wh.loc[wh.warehouse_id=='WH-MUM','stockout_rate_pct'].iloc[0]:.2f}% stock-out rate —
      {mum_share:.0f}% of all lost units across the network.</div>
    <div class="insight"><strong>Bengaluru is overstocked.</strong>
      It carries the highest average inventory ({inr_short(best_wh['avg_inventory_value_inr'])})
      with the lowest turnover ({best_wh['turnover_period']:.1f}×) — capital is locked in slow
      stock while its stock-out rate is only {best_wh['stockout_rate_pct']:.2f}%.</div>
    <div class="insight"><strong>Top bottleneck SKU:</strong>
      {worst['product_name']} at {WH_NAMES[worst['warehouse_id']]} lost
      {inr_short(worst['lost_sales_value_inr'])} in sales to stock-outs
      ({worst['stockout_rate_pct']:.1f}% of its demand unfulfilled).</div>
  </div>

  <h2>Warehouse Performance</h2>
  <div class="panel"><table>
    <tr><th>Warehouse</th><th>Units Sold</th><th>Stock-Out Rate</th><th>Turnover</th>
        <th>Avg Inventory Value</th><th>Lost Units</th></tr>
    {wh_rows}
  </table></div>

  <h2>Charts</h2>
  <div class="charts">{charts}</div>

  <h2>Top Bottleneck SKUs (by lost sales value)</h2>
  <div class="panel"><table>
    <tr><th>Product</th><th>Category</th><th>Warehouse</th><th>Stock-Out Rate</th>
        <th>Lost Units</th><th>Lost Sales Value</th></tr>
    {sku_rows}
  </table></div>
</main>
<footer>
  Built with PostgreSQL · Python (Pandas, SQLAlchemy) · Power BI (DAX) ·
  Dashboard generated by <code>dashboard/build_dashboard.py</code><br>
  Synthetic sample data (seed 42) modelled on a real supply chain &amp; inventory
  dashboard project — no real company data.
</footer>
</body></html>"""

out = BASE / "dashboard" / "dashboard.html"
out.write_text(html, encoding="utf-8")
print(f"dashboard written: {out} ({out.stat().st_size/1024:.0f} KB)")
