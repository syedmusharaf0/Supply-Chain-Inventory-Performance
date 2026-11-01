-- ============================================================
-- Supply Chain & Inventory Performance - PostgreSQL schema
-- Star schema: 1 dimension table + 2 fact tables
-- Load order: dim_products -> fact_daily_stock / fact_purchase_orders
-- CSV files live in ../data/ (same column names as the tables below)
-- ============================================================

DROP TABLE IF EXISTS fact_daily_stock;
DROP TABLE IF EXISTS fact_purchase_orders;
DROP TABLE IF EXISTS dim_products;

CREATE TABLE dim_products (
    sku                     VARCHAR(10) PRIMARY KEY,
    product_name            VARCHAR(120) NOT NULL,
    category                VARCHAR(50)  NOT NULL,
    unit_cost_sar           NUMERIC(10,2) NOT NULL,
    unit_cost_inr           NUMERIC(10,2) NOT NULL,  -- SAR x 22.30, approximate Nov 2026 rate
    supplier                VARCHAR(80)  NOT NULL,
    standard_lead_time_days INT          NOT NULL,
    reorder_point_units     INT          NOT NULL,
    base_daily_demand       INT          NOT NULL
);

CREATE TABLE fact_daily_stock (
    date            DATE        NOT NULL,
    warehouse       VARCHAR(50) NOT NULL,
    sku             VARCHAR(10) NOT NULL REFERENCES dim_products (sku),
    opening_stock   INT         NOT NULL,
    units_received  INT         NOT NULL,
    units_sold      INT         NOT NULL,
    units_lost_sales INT        NOT NULL,
    closing_stock   INT         NOT NULL,
    stockout_day    SMALLINT    NOT NULL CHECK (stockout_day IN (0, 1)),
    PRIMARY KEY (date, warehouse, sku)
);

CREATE TABLE fact_purchase_orders (
    order_id                VARCHAR(12) PRIMARY KEY,
    order_date              DATE        NOT NULL,
    sku                     VARCHAR(10) NOT NULL REFERENCES dim_products (sku),
    warehouse               VARCHAR(50) NOT NULL,
    supplier                VARCHAR(80) NOT NULL,
    quantity_units          INT         NOT NULL,
    standard_lead_time_days INT         NOT NULL,
    actual_lead_time_days   INT         NOT NULL,
    arrival_date            DATE        NOT NULL
);

CREATE INDEX idx_stock_sku_date   ON fact_daily_stock (sku, date);
CREATE INDEX idx_stock_warehouse  ON fact_daily_stock (warehouse);
CREATE INDEX idx_orders_supplier  ON fact_purchase_orders (supplier);

-- Example load (adjust the path to your machine):
-- \copy dim_products FROM 'data/dim_products.csv' WITH (FORMAT csv, HEADER true);
-- \copy fact_daily_stock FROM 'data/fact_daily_stock.csv' WITH (FORMAT csv, HEADER true);
-- \copy fact_purchase_orders FROM 'data/fact_purchase_orders.csv' WITH (FORMAT csv, HEADER true);
