-- =====================================================================
-- 01_schema.sql  |  Star schema for the Sales Analysis project
-- Dialect: SQLite (portable to PostgreSQL / MySQL with minor changes)
-- =====================================================================

DROP TABLE IF EXISTS fact_sales;
DROP TABLE IF EXISTS dim_customers;
DROP TABLE IF EXISTS dim_products;
DROP TABLE IF EXISTS dim_sales_reps;
DROP TABLE IF EXISTS dim_regions;

CREATE TABLE dim_regions (
    region_id    INTEGER PRIMARY KEY,
    region_name  VARCHAR(20) NOT NULL,
    country      VARCHAR(30) NOT NULL
);

CREATE TABLE dim_products (
    product_id    INTEGER PRIMARY KEY,
    product_name  VARCHAR(60) NOT NULL,
    category      VARCHAR(30) NOT NULL,
    sub_category  VARCHAR(30) NOT NULL,
    unit_price    DECIMAL(12,2) NOT NULL,
    unit_cost     DECIMAL(12,2) NOT NULL
);

CREATE TABLE dim_sales_reps (
    rep_id         INTEGER PRIMARY KEY,
    rep_name       VARCHAR(60) NOT NULL,
    region_id      INTEGER REFERENCES dim_regions(region_id),
    hire_date      DATE,
    annual_target  DECIMAL(14,2)
);

CREATE TABLE dim_customers (
    customer_id    VARCHAR(10) PRIMARY KEY,
    customer_name  VARCHAR(60),
    segment        VARCHAR(20),
    region_id      INTEGER REFERENCES dim_regions(region_id),
    city           VARCHAR(30),
    signup_date    DATE
);

CREATE TABLE fact_sales (
    order_id      VARCHAR(12),
    order_date    DATE NOT NULL,
    ship_date     DATE,
    customer_id   VARCHAR(10) REFERENCES dim_customers(customer_id),
    product_id    INTEGER     REFERENCES dim_products(product_id),
    rep_id        INTEGER     REFERENCES dim_sales_reps(rep_id),
    region_id     INTEGER     REFERENCES dim_regions(region_id),
    channel       VARCHAR(20),
    payment_mode  VARCHAR(20),
    quantity      INTEGER,
    unit_price    DECIMAL(12,2),
    discount_pct  DECIMAL(4,2),
    sales_amount  DECIMAL(14,2),
    cost_amount   DECIMAL(14,2),
    profit        DECIMAL(14,2),
    is_returned   BOOLEAN
);

CREATE INDEX idx_sales_date     ON fact_sales(order_date);
CREATE INDEX idx_sales_customer ON fact_sales(customer_id);
CREATE INDEX idx_sales_product  ON fact_sales(product_id);
