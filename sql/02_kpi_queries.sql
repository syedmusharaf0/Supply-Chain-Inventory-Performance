-- ============================================================
-- Supply Chain & Inventory Performance - KPI queries (PostgreSQL)
-- KPIs: Stock Turnover Ratio, Carrying Cost, Lead Time Variance,
--       Stock-out Rate, bottleneck SKUs, overstocked SKUs
-- Carrying cost assumption: 20% of average inventory value per year,
-- pro-rated for the number of days in the analysis period.
-- ============================================================

-- ------------------------------------------------------------
-- 1) STOCK TURNOVER RATIO by SKU
--    Turnover = COGS / Average Inventory Value
--    (period turnover; multiply by 365/days for annualised)
-- ------------------------------------------------------------
SELECT
    s.sku,
    p.product_name,
    p.category,
    SUM(s.units_sold)                                   AS units_sold,
    SUM(s.units_sold * p.unit_cost_sar)                 AS cogs_sar,
    AVG(s.closing_stock * p.unit_cost_sar)              AS avg_inventory_value_sar,
    ROUND(SUM(s.units_sold * p.unit_cost_sar)
          / NULLIF(AVG(s.closing_stock * p.unit_cost_sar), 0), 2) AS stock_turnover_ratio
FROM fact_daily_stock s
JOIN dim_products p ON p.sku = s.sku
GROUP BY s.sku, p.product_name, p.category
ORDER BY stock_turnover_ratio DESC;

-- ------------------------------------------------------------
-- 2) CARRYING COST by warehouse
-- ------------------------------------------------------------
WITH period AS (
    SELECT (MAX(date) - MIN(date) + 1) AS days_in_period FROM fact_daily_stock
)
SELECT
    s.warehouse,
    ROUND(AVG(s.closing_stock * p.unit_cost_sar), 2)              AS avg_inventory_value_sar,
    ROUND(AVG(s.closing_stock * p.unit_cost_sar)
          * 0.20 * (SELECT days_in_period FROM period) / 365.0, 2) AS carrying_cost_sar,
    -- Indian Rupee equivalents (unit_cost_inr = SAR x 22.30)
    ROUND(AVG(s.closing_stock * p.unit_cost_inr), 2)              AS avg_inventory_value_inr,
    ROUND(AVG(s.closing_stock * p.unit_cost_inr)
          * 0.20 * (SELECT days_in_period FROM period) / 365.0, 2) AS carrying_cost_inr
FROM fact_daily_stock s
JOIN dim_products p ON p.sku = s.sku
GROUP BY s.warehouse
ORDER BY carrying_cost_sar DESC;

-- ------------------------------------------------------------
-- 3) STOCK-OUT RATE by SKU (share of days with lost sales)
-- ------------------------------------------------------------
SELECT
    s.sku,
    p.product_name,
    s.warehouse,
    COUNT(*)                                   AS total_days,
    SUM(s.stockout_day)                        AS stockout_days,
    ROUND(100.0 * SUM(s.stockout_day) / COUNT(*), 2) AS stockout_rate_pct,
    SUM(s.units_lost_sales)                    AS units_lost_sales
FROM fact_daily_stock s
JOIN dim_products p ON p.sku = s.sku
GROUP BY s.sku, p.product_name, s.warehouse
ORDER BY stockout_rate_pct DESC;

-- ------------------------------------------------------------
-- 4) LEAD TIME VARIANCE by supplier
--    Variance = Actual - Standard lead time (days)
-- ------------------------------------------------------------
SELECT
    supplier,
    COUNT(*)                                            AS orders,
    ROUND(AVG(standard_lead_time_days), 2)              AS avg_standard_lead_days,
    ROUND(AVG(actual_lead_time_days), 2)                AS avg_actual_lead_days,
    ROUND(AVG(actual_lead_time_days
              - standard_lead_time_days), 2)            AS lead_time_variance_days,
    ROUND(100.0 * SUM(CASE WHEN actual_lead_time_days
              > standard_lead_time_days THEN 1 ELSE 0 END)
          / COUNT(*), 2)                                AS pct_orders_late
FROM fact_purchase_orders
GROUP BY supplier
ORDER BY lead_time_variance_days DESC;

-- ------------------------------------------------------------
-- 5) BOTTLENECK SKUs - highest stock-out rate AND lost sales
-- ------------------------------------------------------------
SELECT
    s.sku,
    p.product_name,
    p.category,
    p.supplier,
    ROUND(100.0 * SUM(s.stockout_day) / COUNT(*), 2) AS stockout_rate_pct,
    SUM(s.units_lost_sales)                          AS units_lost_sales,
    ROUND(SUM(s.units_lost_sales * p.unit_cost_sar), 2) AS est_lost_sales_value_sar
FROM fact_daily_stock s
JOIN dim_products p ON p.sku = s.sku
GROUP BY s.sku, p.product_name, p.category, p.supplier
ORDER BY units_lost_sales DESC
LIMIT 10;

-- ------------------------------------------------------------
-- 6) OVERSTOCKED SKUs - high average stock, low turnover
-- ------------------------------------------------------------
SELECT
    s.sku,
    p.product_name,
    p.category,
    ROUND(AVG(s.closing_stock), 0)                       AS avg_closing_stock_units,
    ROUND(AVG(s.closing_stock * p.unit_cost_sar), 2)     AS avg_inventory_value_sar,
    ROUND(SUM(s.units_sold * p.unit_cost_sar)
          / NULLIF(AVG(s.closing_stock * p.unit_cost_sar), 0), 2) AS stock_turnover_ratio
FROM fact_daily_stock s
JOIN dim_products p ON p.sku = s.sku
GROUP BY s.sku, p.product_name, p.category
HAVING AVG(s.closing_stock) > 200
ORDER BY stock_turnover_ratio ASC
LIMIT 10;

-- ------------------------------------------------------------
-- 7) MONTHLY STOCK-OUT TREND with LAG() - month-over-month change
-- ------------------------------------------------------------
WITH monthly AS (
    SELECT
        DATE_TRUNC('month', date)::date                    AS month,
        ROUND(100.0 * SUM(stockout_day) / COUNT(*), 2)     AS stockout_rate_pct,
        SUM(units_lost_sales)                              AS units_lost_sales
    FROM fact_daily_stock
    GROUP BY DATE_TRUNC('month', date)
)
SELECT
    month,
    stockout_rate_pct,
    LAG(stockout_rate_pct) OVER (ORDER BY month)           AS prev_month_pct,
    ROUND(stockout_rate_pct
          - LAG(stockout_rate_pct) OVER (ORDER BY month), 2) AS mom_change_pct_points,
    units_lost_sales
FROM monthly
ORDER BY month;

-- ------------------------------------------------------------
-- 8) WAREHOUSE PERFORMANCE SUMMARY
-- ------------------------------------------------------------
SELECT
    s.warehouse,
    SUM(s.units_sold)                                       AS units_sold,
    SUM(s.units_lost_sales)                                 AS units_lost_sales,
    ROUND(100.0 * SUM(s.stockout_day) / COUNT(*), 2)        AS stockout_rate_pct,
    ROUND(AVG(s.closing_stock * p.unit_cost_sar), 2)        AS avg_inventory_value_sar
FROM fact_daily_stock s
JOIN dim_products p ON p.sku = s.sku
GROUP BY s.warehouse
ORDER BY stockout_rate_pct DESC;
