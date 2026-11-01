# Power BI Dashboard — Professional Build Guide

Build the `.pbix` in **Power BI Desktop** (free from Microsoft) in about
20 minutes using this pack. Everything is specified exactly: data load,
model, measures, page layouts, colours and formatting.

## Pack contents
| File | Use |
|---|---|
| `power_query_m.txt` | Paste into Power BI to load the 3 tables with correct types |
| `dax_measures.dax` | All measures — create a measure table and paste them in |
| This guide | Page-by-page layout spec |

## Step 1 — Load the data (5 min)
1. Power BI Desktop → **Get Data → Blank Query** → Advanced Editor → paste the
   `dim_products` block from `power_query_m.txt` (set your `DataFolder` path).
   Name the query `dim_products`. Repeat for `fact_daily_stock` and
   `fact_purchase_orders`. **Close & Apply**.
2. **Model view:** create relationships —
   `dim_products[product_code]` → `fact_daily_stock[product_code]` and
   → `fact_purchase_orders[product_code]` (one-to-many, single direction).
3. **Modeling → New table:** paste the `Calendar` DAX from the end of
   `power_query_m.txt`; relate `Calendar[Date]` → `fact_daily_stock[stock_date]`;
   right-click Calendar → **Mark as date table**.

## Step 2 — Create the measures (5 min)
Modeling → New table → name it `_Measures` (enter `1` as the formula, then
delete that placeholder measure). Paste each measure from `dax_measures.dax`
as a new measure in `_Measures`. Hide the fact-table numeric columns
(units_sold, lost_sales_units, …) so report builders use measures only.
**Formatting:** set currency measures (Sales Value INR, Lost Sales Value INR,
Average Inventory Value INR, Carrying Cost INR) to format `₹ #,##0`;
percent measures to 0.00 with a "%" suffix in the card titles.

## Theme (use View → Themes → Customize current theme)
| Role | Colour |
|---|---|
| Primary / headers | `#0D2B45` (deep navy) |
| Secondary / bars | `#1F6F8B` (teal) |
| Accent / highlights | `#FFB703` (amber) |
| Alert (late, stock-out) | `#C0392B` |
| Page background | `#F2F5F8` |
Font: Segoe UI. Page size: 16:9.

## Step 3 — Build the pages (10 min)

### Page 1 — Executive Overview
- **Row of 6 KPI cards:** Total Units Sold · Stock-Out Rate % · Stock Turnover
  Ratio · Average Inventory Value INR · Carrying Cost INR · Orders Late %.
- **Line chart:** Calendar month on axis, **Stock-Out Rate %** — add a constant
  target line at 3% (Analytics pane) labelled "Target 3%".
- **Bar chart:** Stock Turnover Ratio by `product_category` (teal, data labels on).
- **Bar chart:** Lost Sales Value INR by `warehouse_name` (amber; Mumbai should stand out).
- **Slicers (top):** `warehouse_name`, `product_category`, Calendar month.
- Title text box: "Supply Chain & Inventory Performance — Executive Overview".

### Page 2 — Growth & Trends (LAG comparisons)
- **Line + column combo:** month axis; columns = Total Units Sold;
  line = **YoY Growth %** (from `dax_measures.dax`).
- **Line chart:** **MoM Growth %** by month.
- **Clustered column:** units sold by **week** with **WoW Growth %** as a line
  (secondary axis) — switch the axis to Calendar week for this visual.
- **Table:** month, Total Units Sold, MoM Growth %, YoY Growth %, Sales Value
  INR, Sales Value YoY Growth % — conditional formatting (data bars) on the
  growth columns: green above 0, red below 0.
- **Yearly small table:** year, Total Units Sold, YoY Growth %, Stock-Out
  Rate % — add a note under 2025: "Jan–Jun only (partial year)".

### Page 3 — Warehouse & Product Deep-Dive
- **Matrix:** rows `warehouse_name`, columns `product_category`, values
  Stock-Out Rate % + Stock Turnover Ratio (background colour scale on rate).
- **Bar chart (Top N = 10):** Lost Sales Value INR by `product_name`,
  filtered by `warehouse_name` when drilled.
- **Table — Reorder alerts:** product_name, warehouse_name,
  closing_stock_units (latest date), reorder_level — conditional formatting:
  red fill when closing stock < reorder level (use the
  **Products Below Reorder Level** measure in the page title card).
- Enable **drill-through** on product_name to this page from Page 1.

### Page 4 — Supplier Performance
- **Bar chart:** Avg Lead Time Variance (days) by `supplier_name` (red).
- **Cards:** Orders Late % · Avg Lead Time Variance (days) · total orders.
- **Table:** supplier_name, total orders, average variance, late % (from
  `outputs/kpi_by_supplier_leadtime.csv` logic — or rebuild from measures).
- **Scatter:** promised_lead_time_days (x) vs actual_lead_time_days (y),
  one dot per purchase order, details = purchase_order_id.

## Step 4 — Polish & publish
- Add the amber header band + white title text on each page (rectangle shape).
- Check: every visual has a clear title in plain words; ₹ values use Indian
  digit grouping (set data labels format `₹ #,##0`); no default "Sum of …"
  titles remain.
- **File → Publish** (needs a free Power BI account) or keep the `.pbix` and
  export page 1 as PDF/PNG for your portfolio and LinkedIn.

> The browser version of this same dashboard lives in `dashboard.html`
> (open it in any browser) — the Power BI version adds slicers, drill-through
> and live growth comparisons on top of the same data and measures.
