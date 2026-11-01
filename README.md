# Supply Chain & Inventory Performance

**SQL · Python (Pandas) · Power BI** — inventory analytics for a multi-warehouse Indian
distribution network (Mumbai · Delhi · Bengaluru), Jan 2023 – Jun 2025.
All values in **Indian Rupees (₹)**. Every column uses a clear, friendly name —
see the [data dictionary](data/data_dictionary.md).

---

## 📊 Power BI Dashboard

| | |
|---|---|
| **Total Sales** | **₹973.00 Cr** |
| **Total Units Sold** | **967,953** |
| **Stock-Out Rate** | **7.20%** |
| **Stock Turnover (annualised)** | **50.52×** |
| **Average Inventory Value** | **₹7.71 Cr** |
| **Carrying Cost** | **₹3.85 Cr** |
| **Late Orders** | **41.1%** |

![Stock Turnover by Category](images/turnover_by_category.svg)
![YoY Growth](images/yoy_growth_trend.svg)
![Monthly Stock-Out Trend](images/monthly_stockout_trend.svg)

**Dashboard pages:** 1) Executive Overview — KPI cards, turnover by category, lost
sales by warehouse · 2) Growth & Trends — WoW / MoM / YoY comparisons (LAG) ·
3) Warehouse & Product Deep-Dive — bottleneck products, reorder alerts, drill-through ·
4) Supplier Performance — lead-time variance, late orders.

**Build it yourself (Power BI Desktop, ~20 min):**
[Build guide](dashboard/powerbi_build_guide.md) ·
[DAX measures](dashboard/dax_measures.dax) ·
[Power Query load code](dashboard/power_query_m.txt)

**No Power BI?** The same dashboard opens in any browser:
[`dashboard/dashboard.html`](dashboard/dashboard.html)

---

## Business questions
- Which warehouses and products lose the most sales to stock-outs?
- Where is capital locked up in slow-moving, overstocked inventory?
- Which suppliers miss their promised lead times, and by how much?
- What is the real cost of holding inventory (carrying cost)?
- How are sales growing — week over week, month over month, year over year?

## Key results (Jan 2023 – Jun 2025, sample data)

| KPI | Value |
|---|---|
| Total sales value | ₹9,72,99,57,050 |
| Total units sold | 967,953 |
| Units lost to stock-outs | 75,082 |
| Overall stock-out rate | 7.20% |
| Stock turnover (annualised) | 50.52× |
| Average inventory value | ₹7,70,85,270 |
| Carrying cost (20% per year) | ₹3,85,21,516 |
| Purchase orders late | 41.1% |
| Average lead-time variance | +1.24 days |

Dataset: 65,664 daily stock records · 878 purchase orders · 24 products · 3 warehouses.

## Growth — LAG comparisons (weekly · monthly · yearly)
Computed with the SQL **`LAG()` window function** (`sql/02_kpi_queries.sql`,
queries 9–11), mirrored in Python with `shift()` and in Power BI with DAX
time-intelligence measures:

- **Weekly:** week-over-week (WoW) growth % → `outputs/weekly_trend.csv`
- **Monthly:** month-over-month (MoM) and year-over-year (YoY) growth % → `outputs/monthly_trend.csv`
- **Yearly:** year-over-year growth % → `outputs/yearly_summary.csv` (2025 is Jan–Jun only, flagged partial)

Headline: 2024 total units sold grew **+6.1% YoY** over 2023,
and Jun 2025 is **+5.3% vs Jun 2024**.

## Insights
- **Mumbai Central is the bottleneck:** leanest stock, highest demand — a
  11.97% stock-out rate and
  51,245 lost units
  (68% of all lost units network-wide),
  on total sales of ₹380.47 Cr.
- **Bengaluru Hub is overstocked:** the highest average inventory
  (₹2,94,95,779) with the lowest turnover
  (36.38×) — capital sitting in slow stock.

## Top bottleneck products (lost sales value)

| Product | Warehouse | Stock-Out Rate | Lost Units | Lost Value |
|---|---|---|---|---|
| Water Purifier 8L | Mumbai Central | 15.00% | 4,468 | ₹7,17,56,080 |
| Smart Watch Series 5 | Mumbai Central | 6.87% | 1,723 | ₹5,57,21,820 |
| LED Desk Lamp | Mumbai Central | 12.40% | 2,945 | ₹5,12,13,550 |
| Memory Foam Pillow | Mumbai Central | 20.69% | 5,161 | ₹4,49,00,700 |
| Water Purifier 8L | Delhi Hub | 7.97% | 1,886 | ₹3,02,89,160 |

## More charts
![Lead Time Variance by Supplier](images/lead_time_variance_by_supplier.svg)
![Top Bottleneck Products](images/top_bottleneck_skus.svg)

## Repository structure
```
data/        dim_products, fact_daily_stock, fact_purchase_orders (CSV) + data dictionary
sql/         01_schema_postgresql.sql, 02_kpi_queries.sql (11 KPI queries incl. LAG growth)
python/      generate_sample_data.py, etl_pipeline.py, kpi_analysis.py
dashboard/   dashboard.html + build_dashboard.py (browser dashboard),
             powerbi_build_guide.md, power_query_m.txt, dax_measures.dax (Power BI pack)
outputs/     KPI tables with friendly column names: summary, by warehouse, by product,
             supplier lead time, weekly / monthly / yearly trends with growth %
images/      Charts (SVG)
```

## How to run
```bash
pip install -r requirements.txt
python python/generate_sample_data.py   # creates the sample dataset (seed 42)
python python/etl_pipeline.py           # validate -> transform -> load (SQLite demo DB)
python python/kpi_analysis.py           # KPI tables + charts + growth comparisons
python dashboard/build_dashboard.py     # builds dashboard/dashboard.html
```
For production, the same schema and queries run on PostgreSQL
(`sql/01_schema_postgresql.sql`); the ETL loads to SQLite locally so the full
pipeline runs anywhere with zero setup.

## Tools & skills demonstrated
PostgreSQL (joins, aggregation, `LAG()` window function for WoW/MoM/YoY growth) ·
Python (Pandas, SQLAlchemy, Matplotlib) · Power BI & DAX (incl. time-intelligence
measures) · KPI design (Total Sales, Stock Turnover, Stock-Out Rate, Carrying Cost,
Lead Time Variance) · Data validation & ETL design

## Note on data
The dataset is **synthetic sample data** generated by
`python/generate_sample_data.py`, modelled on the structure of a real supply
chain & inventory dashboard project (daily stock movements, purchase orders,
reorder levels, supplier lead times). It contains no real company data.

---
**Author:** Syed Musharaf — Data Analyst · [GitHub](https://github.com/syedmusharaf0)
