-- Supply Chain & Inventory Performance — KPI queries (PostgreSQL)
-- KPIs: Stock Turnover Ratio, Carrying Cost, Lead Time Variance,
--       Stock-Out Rate, bottleneck / overstock product analysis.
-- All monetary values in Indian Rupees (INR).

-- 1) STOCK TURNOVER RATIO (annualised) = value of goods sold / average inventory value x 365 / days
SELECT
    ROUND(SUM(s.units_sold * p.unit_cost_inr) /
          AVG(daily.daily_value) * 365.0 /
          (MAX(s.stock_date) - MIN(s.stock_date) + 1), 2) AS stock_turnover_ratio
FROM fact_daily_stock s
JOIN dim_products p ON p.product_code = s.product_code
JOIN (SELECT stock_date, SUM(closing_stock_units * unit_cost_inr) AS daily_value
      FROM fact_daily_stock JOIN dim_products USING (product_code)
      GROUP BY stock_date) daily ON daily.stock_date = s.stock_date;

-- 2) AVERAGE INVENTORY VALUE + CARRYING COST (assumption: 20% per year, 181-day period)
SELECT
    ROUND(AVG(daily_value))                        AS average_inventory_value_inr,
    ROUND(AVG(daily_value) * 0.20 * 181.0 / 365.0) AS carrying_cost_inr
FROM (SELECT stock_date, SUM(closing_stock_units * unit_cost_inr) AS daily_value
      FROM fact_daily_stock JOIN dim_products USING (product_code)
      GROUP BY stock_date) d;

-- 3) STOCK-OUT RATE overall and by warehouse
SELECT warehouse_name,
       SUM(units_sold) AS total_units_sold,
       SUM(lost_sales_units) AS total_lost_units,
       ROUND(100.0 * SUM(lost_sales_units) /
             NULLIF(SUM(units_sold) + SUM(lost_sales_units), 0), 2) AS stockout_rate_percent
FROM fact_daily_stock
GROUP BY warehouse_name
ORDER BY stockout_rate_percent DESC;

-- 4) LEAD TIME VARIANCE by supplier (promised vs actual)
SELECT p.supplier_name,
       COUNT(*) AS total_orders,
       ROUND(AVG(o.actual_lead_time_days - o.promised_lead_time_days), 2) AS average_variance_days,
       ROUND(100.0 * AVG(CASE WHEN o.actual_lead_time_days > o.promised_lead_time_days
                              THEN 1 ELSE 0 END), 1) AS late_orders_percent
FROM fact_purchase_orders o
JOIN dim_products p ON p.product_code = o.product_code
GROUP BY p.supplier_name
ORDER BY average_variance_days DESC;

-- 5) BOTTLENECK PRODUCTS — highest lost-sales value (stock-outs costing the most)
SELECT s.product_code, p.product_name, p.product_category, s.warehouse_name,
       SUM(s.lost_sales_units) AS lost_units,
       ROUND(100.0 * SUM(s.lost_sales_units) /
             NULLIF(SUM(s.units_sold) + SUM(s.lost_sales_units), 0), 2) AS stockout_rate_percent,
       ROUND(SUM(s.lost_sales_units) * p.unit_cost_inr) AS lost_sales_value_inr
FROM fact_daily_stock s
JOIN dim_products p ON p.product_code = s.product_code
GROUP BY s.product_code, p.product_name, p.product_category, s.warehouse_name, p.unit_cost_inr
HAVING SUM(s.lost_sales_units) > 0
ORDER BY lost_sales_value_inr DESC
LIMIT 10;

-- 6) OVERSTOCKED PRODUCTS — high average stock, low sales (carrying-cost drag)
SELECT s.product_code, p.product_name, s.warehouse_name,
       ROUND(AVG(s.closing_stock_units)) AS average_stock_units,
       SUM(s.units_sold) AS total_units_sold,
       ROUND(AVG(s.closing_stock_units) * p.unit_cost_inr) AS average_stock_value_inr
FROM fact_daily_stock s
JOIN dim_products p ON p.product_code = s.product_code
GROUP BY s.product_code, p.product_name, s.warehouse_name, p.unit_cost_inr
ORDER BY average_stock_value_inr DESC
LIMIT 10;

-- 7) MONTHLY STOCK-OUT TREND (window function: month-over-month change)
WITH m AS (
    SELECT DATE_TRUNC('month', stock_date) AS month,
           100.0 * SUM(lost_sales_units) /
           NULLIF(SUM(units_sold) + SUM(lost_sales_units), 0) AS stockout_rate_percent
    FROM fact_daily_stock GROUP BY 1
)
SELECT month,
       ROUND(stockout_rate_percent, 2) AS stockout_rate_percent,
       ROUND(stockout_rate_percent - LAG(stockout_rate_percent) OVER (ORDER BY month), 2)
           AS change_vs_previous_month
FROM m ORDER BY month;

-- 8) REORDER ALERTS — products whose latest closing stock is below the reorder level
SELECT s.product_code, p.product_name, s.warehouse_name,
       s.closing_stock_units, p.reorder_level
FROM fact_daily_stock s
JOIN dim_products p ON p.product_code = s.product_code
WHERE s.stock_date = (SELECT MAX(stock_date) FROM fact_daily_stock)
  AND s.closing_stock_units < p.reorder_level
ORDER BY s.closing_stock_units;

-- 9) WEEKLY COMPARISON with LAG — this week vs last week (WoW growth %)
WITH w AS (
    SELECT DATE_TRUNC('week', stock_date) AS week_start,
           SUM(units_sold) AS units_sold,
           ROUND(SUM(units_sold * unit_cost_inr)) AS sales_value_inr,
           SUM(lost_sales_units) AS lost_units
    FROM fact_daily_stock JOIN dim_products USING (product_code)
    GROUP BY 1
)
SELECT week_start, units_sold,
       LAG(units_sold) OVER (ORDER BY week_start) AS previous_week_units_sold,
       ROUND(100.0 * (units_sold - LAG(units_sold) OVER (ORDER BY week_start))
             / NULLIF(LAG(units_sold) OVER (ORDER BY week_start), 0), 2) AS wow_growth_percent,
       ROUND(sales_value_inr) AS sales_value_inr,
       ROUND(100.0 * (sales_value_inr - LAG(sales_value_inr) OVER (ORDER BY week_start))
             / NULLIF(LAG(sales_value_inr) OVER (ORDER BY week_start), 0), 2) AS sales_wow_growth_percent,
       lost_units
FROM w ORDER BY week_start;

-- 10) MONTHLY COMPARISON with LAG — MoM growth % and YoY growth % (same month last year)
WITH m AS (
    SELECT DATE_TRUNC('month', stock_date) AS month,
           SUM(units_sold) AS units_sold,
           ROUND(SUM(units_sold * unit_cost_inr)) AS sales_value_inr,
           SUM(lost_sales_units) AS lost_units,
           ROUND(100.0 * SUM(lost_sales_units) /
                 NULLIF(SUM(units_sold) + SUM(lost_sales_units), 0), 2) AS stockout_rate_percent
    FROM fact_daily_stock JOIN dim_products USING (product_code)
    GROUP BY 1
)
SELECT month, units_sold,
       ROUND(100.0 * (units_sold - LAG(units_sold, 1) OVER (ORDER BY month))
             / NULLIF(LAG(units_sold, 1) OVER (ORDER BY month), 0), 2) AS mom_growth_percent,
       ROUND(100.0 * (units_sold - LAG(units_sold, 12) OVER (ORDER BY month))
             / NULLIF(LAG(units_sold, 12) OVER (ORDER BY month), 0), 2) AS yoy_growth_percent,
       sales_value_inr,
       ROUND(100.0 * (sales_value_inr - LAG(sales_value_inr, 12) OVER (ORDER BY month))
             / NULLIF(LAG(sales_value_inr, 12) OVER (ORDER BY month), 0), 2) AS sales_yoy_growth_percent,
       stockout_rate_percent, lost_units
FROM m ORDER BY month;

-- 11) YEARLY COMPARISON with LAG — year-over-year growth %
WITH y AS (
    SELECT DATE_TRUNC('year', stock_date) AS year,
           SUM(units_sold) AS units_sold,
           ROUND(SUM(units_sold * unit_cost_inr)) AS sales_value_inr,
           SUM(lost_sales_units) AS lost_units
    FROM fact_daily_stock JOIN dim_products USING (product_code)
    GROUP BY 1
)
SELECT year, units_sold,
       ROUND(100.0 * (units_sold - LAG(units_sold) OVER (ORDER BY year))
             / NULLIF(LAG(units_sold) OVER (ORDER BY year), 0), 2) AS yoy_growth_percent,
       sales_value_inr,
       ROUND(100.0 * (sales_value_inr - LAG(sales_value_inr) OVER (ORDER BY year))
             / NULLIF(LAG(sales_value_inr) OVER (ORDER BY year), 0), 2) AS sales_yoy_growth_percent,
       lost_units
FROM y ORDER BY year;
