-- Supply Chain & Inventory Performance — PostgreSQL schema
-- Star schema: one product dimension, two fact tables.
-- All monetary values in Indian Rupees (INR). Indian regional warehouses.

CREATE TABLE IF NOT EXISTS dim_products (
    sku           VARCHAR(10) PRIMARY KEY,
    product_name  VARCHAR(120) NOT NULL,
    category      VARCHAR(40)  NOT NULL,
    supplier      VARCHAR(60)  NOT NULL,
    unit_cost_inr NUMERIC(12,2) NOT NULL,
    reorder_point INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS fact_daily_stock (
    date            DATE NOT NULL,
    sku             VARCHAR(10) NOT NULL REFERENCES dim_products(sku),
    warehouse_id    VARCHAR(10) NOT NULL,   -- WH-MUM Mumbai Central, WH-DEL Delhi Hub, WH-BLR Bengaluru Hub
    opening_stock   INTEGER NOT NULL,
    units_received  INTEGER NOT NULL DEFAULT 0,
    units_sold      INTEGER NOT NULL DEFAULT 0,
    lost_sales_units INTEGER NOT NULL DEFAULT 0,
    closing_stock   INTEGER NOT NULL,
    PRIMARY KEY (date, sku, warehouse_id)
);

CREATE TABLE IF NOT EXISTS fact_purchase_orders (
    po_number               VARCHAR(12) PRIMARY KEY,
    order_date              DATE NOT NULL,
    sku                     VARCHAR(10) NOT NULL REFERENCES dim_products(sku),
    warehouse_id            VARCHAR(10) NOT NULL,
    quantity_ordered        INTEGER NOT NULL,
    promised_lead_time_days INTEGER NOT NULL,
    actual_lead_time_days   INTEGER NOT NULL,
    delivery_date           DATE NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_stock_sku ON fact_daily_stock (sku);
CREATE INDEX IF NOT EXISTS idx_stock_wh  ON fact_daily_stock (warehouse_id);
CREATE INDEX IF NOT EXISTS idx_po_sku    ON fact_purchase_orders (sku);
