# Dashboard Guide

Two dashboards ship with this project:

1. **Interactive HTML dashboard** — `dashboard/dashboard.html`
   A complete, self-contained executive dashboard (open it in any browser,
   no server or Power BI licence needed). Regenerate it any time with
   `python dashboard/build_dashboard.py` after running the analysis.
   It can also be published free through **GitHub Pages** (repo Settings → Pages → deploy from the `main` branch) for a shareable live link.

2. **Power BI dashboard** — build it from `dashboard/dax_measures.dax`
   following the layout below (3 pages: Executive, Warehouse & SKU
   Deep-Dive, Supplier Performance).

## Power BI layout

### Page 1 — Executive Overview
- KPI cards: Stock Turnover Ratio, Stock-Out Rate %, Average Inventory
  Value (₹), Carrying Cost (₹), Lost Sales Value (₹), Orders Late %
- Line chart: monthly Stock-Out Rate % trend
- Bar chart: Stock Turnover by Category
- Slicers: warehouse, category, month

### Page 2 — Warehouse & SKU Deep-Dive
- Matrix: warehouse × category turnover and stock-out rate
- Bar chart: Top Bottleneck SKUs by Lost Sales Value (₹)
- Table: SKUs Below Reorder Point (conditional formatting on closing stock)
- Drill-through on SKU to a daily stock movement page

### Page 3 — Supplier Performance
- Bar chart: Lead Time Variance by Supplier (days)
- Table: orders, late %, average variance by supplier
- Scatter: promised vs actual lead time by purchase order

## Refresh
Re-run `python/etl_pipeline.py` then `python/kpi_analysis.py` (and
`python dashboard/build_dashboard.py` for the HTML dashboard) whenever
the data extracts change.
