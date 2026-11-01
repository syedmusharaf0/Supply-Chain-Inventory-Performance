# Power BI Dashboard — Build Guide

Executive dashboard for the Supply Chain & Inventory Performance project.
Data model: `dim_products` (dimension) related 1→many to `fact_daily_stock`
and `fact_purchase_orders`. All measures are in `dax_measures.dax`.

## Page 1 — Executive Overview
KPI cards (top row):
- Total Units Sold
- Stock Turnover Ratio
- Stock-out Rate %
- Carrying Cost (SAR)
- Avg Lead Time Variance (Days)
- Estimated Lost Sales Value (SAR)

Visuals:
- Line chart: Stock-out Rate % by month (trend, with previous-month comparison)
- Bar chart: Units Sold and Units Lost Sales by Warehouse
- Bar chart: Avg Inventory Value (SAR) by Warehouse vs Carrying Cost (SAR)

Slicers: Warehouse, Category, Supplier, Date range.

## Page 2 — Inventory Health
- Bar chart: Stock Turnover Ratio by Category
- Bar chart: Stock Turnover Ratio by SKU (sorted ascending — slowest movers first)
- Matrix: SKU × Warehouse with Closing Stock, Stock-out Rate %, Days of Cover
  (conditional formatting: red where Stock-out Rate % > 3)
- Scatter: Avg Inventory Value (x) vs Stock Turnover Ratio (y), size = Units Sold
  — SKUs in the bottom-right are overstocked (high value, low turnover)

## Page 3 — Supplier & Lead Time Performance
- Bar chart: Avg Lead Time Variance (Days) by Supplier
- Card: % Orders Late
- Table: Orders by Supplier — orders, standard vs actual lead time, % late
- Drill-through from a supplier to its SKUs

## Drill-through page — SKU Detail
Filter by SKU: daily closing stock line chart with the reorder point as a
constant line, stock-out days highlighted, purchase order history table.

## Refresh
Re-run `python/etl_pipeline.py` after new daily stock files are added to
`data/`, then refresh the dataset in Power BI (the model reads the same
tables produced by the ETL: PostgreSQL or the CSV exports in `outputs/`).
