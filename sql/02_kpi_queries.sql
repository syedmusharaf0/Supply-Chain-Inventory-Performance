-- Supply Chain & Inventory Performance — KPI queries (PostgreSQL)
-- KPIs: Stock Turnover Ratio, Carrying Cost, Lead Time Variance,
--       Stock-Out Rate, bottleneck / overstock SKU analysis.
-- All monetary values in Indian Rupees (INR).

-- 1) STOCK TURNOVER RATIO (period) = value of goods sold / average inventory value
SELECT
    ROUND(SUM(s.units_sold * p.unit_cost_inr) /
          AVG(daily.daily_value), 2) AS stock_turnover_ratio
FROM fact_daily_stock s
JOIN dim_products p ON p.sku = s.sku
JOIN (SELECT date, SUM(closing_stock * unit_cost_inr) AS daily_value
      FROM fact_daily_stock JOIN dim_products USING (sku)
      GROUP BY date) daily ON daily.date = s.date;

-- 2) AVERAGE INVENTORY VALUE + CARRYING COST (assumption: 20% per year, 181-day period)
SELECT
    ROUND(AVG(daily_value))                              AS avg_inventory_value_inr,
    ROUND(AVG(daily_value) * 0.20 * 181.0 / 365.0)       AS carrying_cost_inr
FROM (SELECT date, SUM(closing_stock * unit_cost_inr) AS daily_value
      FROM fact_daily_stock JOIN dim_products USING (sku)
      GROUP BY date) d;

-- 3) STOCK-OUT RATE overall and by warehouse
SELECT warehouse_id,
       SUM(units_sold) AS units_sold,
       SUM(lost_sales_units) AS lost_units,
       ROUND(100.0 * SUM(lost_sales_units) /
             NULLIF(SUM(units_sold) + SUM(lost_sales_units), 0), 2) AS stockout_rate_pct
FROM fact_daily_stock
GROUP BY warehouse_id
ORDER BY stockout_rate_pct DESC;

-- 4) LEAD TIME VARIANCE by supplier (promised vs actual)
SELECT p.supplier,
       COUNT(*) AS orders,
       ROUND(AVG(o.actual_lead_time_days - o.promised_lead_time_days), 2) AS avg_variance_days,
       ROUND(100.0 * AVG(CASE WHEN o.actual_lead_time_days > o.promised_lead_time_days
                              THEN 1 ELSE 0 END), 1) AS late_orders_pct
FROM fact_purchase_orders o
JOIN dim_products p ON p.sku = o.sku
GROUP BY p.supplier
ORDER BY avg_variance_days DESC;

-- 5) BOTTLENECK SKUs — highest lost-sales value (stock-outs costing the most)
SELECT s.sku, p.product_name, p.category, s.warehouse_id,
       SUM(s.lost_sales_units) AS lost_units,
       ROUND(100.0 * SUM(s.lost_sales_units) /
             NULLIF(SUM(s.units_sold) + SUM(s.lost_sales_units), 0), 2) AS stockout_rate_pct,
       ROUND(SUM(s.lost_sales_units) * p.unit_cost_inr) AS lost_sales_value_inr
FROM fact_daily_stock s
JOIN dim_products p ON p.sku = s.sku
GROUP BY s.sku, p.product_name, p.category, s.warehouse_id, p.unit_cost_inr
HAVING SUM(s.lost_sales_units) > 0
ORDER BY lost_sales_value_inr DESC
LIMIT 10;

-- 6) OVERSTOCKED SKUs — high average stock, low sales (carrying-cost drag)
SELECT s.sku, p.product_name, s.warehouse_id,
       ROUND(AVG(s.closing_stock)) AS avg_stock_units,
       SUM(s.units_sold) AS units_sold_period,
       ROUND(AVG(s.closing_stock) * p.unit_cost_inr) AS avg_stock_value_inr
FROM fact_daily_stock s
JOIN dim_products p ON p.sku = s.sku
GROUP BY s.sku, p.product_name, s.warehouse_id, p.unit_cost_inr
ORDER BY avg_stock_value_inr DESC
LIMIT 10;

-- 7) MONTHLY STOCK-OUT TREND (window function: month-over-month change)
WITH m AS (
    SELECT DATE_TRUNC('month', date) AS month,
           100.0 * SUM(lost_sales_units) /
           NULLIF(SUM(units_sold) + SUM(lost_sales_units), 0) AS stockout_rate_pct
    FROM fact_daily_stock GROUP BY 1
)
SELECT month,
       ROUND(stockout_rate_pct, 2) AS stockout_rate_pct,
       ROUND(stockout_rate_pct - LAG(stockout_rate_pct) OVER (ORDER BY month), 2) AS change_vs_prev_month
FROM m ORDER BY month;

-- 8) REORDER ALERTS — SKUs whose latest closing stock is below the reorder point
SELECT s.sku, p.product_name, s.warehouse_id, s.closing_stock, p.reorder_point
FROM fact_daily_stock s
JOIN dim_products p ON p.sku = s.sku
WHERE s.date = (SELECT MAX(date) FROM fact_daily_stock)
  AND s.closing_stock < p.reorder_point
ORDER BY s.closing_stock;
