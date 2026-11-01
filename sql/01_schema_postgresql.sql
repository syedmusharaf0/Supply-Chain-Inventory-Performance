-- Supply Chain & Inventory Performance — PostgreSQL schema
-- Star schema: one product dimension, two fact tables.
-- All monetary values in Indian Rupees (INR). Column names use clear, full
-- words — see data/data_dictionary.md for a plain-English explanation of each.

CREATE TABLE IF NOT EXISTS dim_products (
    product_code   VARCHAR(10) PRIMARY KEY,   -- unique product code, e.g. SKU-001
    product_name   VARCHAR(120) NOT NULL,     -- product display name
    product_category VARCHAR(40) NOT NULL,    -- Electronics / Apparel / FMCG / ...
    supplier_name  VARCHAR(60)  NOT NULL,     -- supplying vendor
    unit_cost_inr  NUMERIC(12,2) NOT NULL,    -- cost of one unit, in rupees
    reorder_level  INTEGER NOT NULL           -- place a new order when stock falls to this level
);

CREATE TABLE IF NOT EXISTS fact_daily_stock (
    stock_date          DATE NOT NULL,        -- the calendar day
    product_code        VARCHAR(10) NOT NULL REFERENCES dim_products(product_code),
    warehouse_name      VARCHAR(40) NOT NULL, -- Mumbai Central / Delhi Hub / Bengaluru Hub
    opening_stock_units INTEGER NOT NULL,     -- units available at start of day
    units_received      INTEGER NOT NULL DEFAULT 0,  -- units delivered that day
    units_sold          INTEGER NOT NULL DEFAULT 0,  -- units sold that day
    lost_sales_units    INTEGER NOT NULL DEFAULT 0,  -- demand lost to stock-outs
    closing_stock_units INTEGER NOT NULL,     -- opening + received - sold
    PRIMARY KEY (stock_date, product_code, warehouse_name)
);

CREATE TABLE IF NOT EXISTS fact_purchase_orders (
    purchase_order_id       VARCHAR(12) PRIMARY KEY,
    order_date              DATE NOT NULL,    -- date the order was placed
    product_code            VARCHAR(10) NOT NULL REFERENCES dim_products(product_code),
    warehouse_name          VARCHAR(40) NOT NULL,  -- receiving warehouse
    quantity_ordered        INTEGER NOT NULL, -- units ordered
    promised_lead_time_days INTEGER NOT NULL, -- supplier-promised lead time
    actual_lead_time_days   INTEGER NOT NULL, -- actual lead time
    delivery_date           DATE NOT NULL     -- order_date + actual lead time
);

CREATE INDEX IF NOT EXISTS idx_stock_product   ON fact_daily_stock (product_code);
CREATE INDEX IF NOT EXISTS idx_stock_warehouse ON fact_daily_stock (warehouse_name);
CREATE INDEX IF NOT EXISTS idx_po_product      ON fact_purchase_orders (product_code);
