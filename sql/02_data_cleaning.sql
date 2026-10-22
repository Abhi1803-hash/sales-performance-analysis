-- =====================================================================
-- 02_data_cleaning.sql  |  Data quality checks + clean view
-- =====================================================================

-- 1. Row counts and duplicate order_ids
SELECT COUNT(*)                         AS total_rows,
       COUNT(DISTINCT order_id)         AS distinct_orders,
       COUNT(*) - COUNT(DISTINCT order_id) AS duplicate_rows
FROM fact_sales;

-- 2. Null check on key columns
SELECT SUM(CASE WHEN channel      IS NULL THEN 1 ELSE 0 END) AS null_channel,
       SUM(CASE WHEN customer_id  IS NULL THEN 1 ELSE 0 END) AS null_customer,
       SUM(CASE WHEN sales_amount IS NULL THEN 1 ELSE 0 END) AS null_sales
FROM fact_sales;

-- 3. Sanity checks: negative values, ship before order
SELECT
    SUM(CASE WHEN quantity <= 0      THEN 1 ELSE 0 END) AS bad_qty,
    SUM(CASE WHEN sales_amount < 0   THEN 1 ELSE 0 END) AS negative_sales,
    SUM(CASE WHEN ship_date < order_date THEN 1 ELSE 0 END) AS ship_before_order
FROM fact_sales;

-- 4. Clean view: de-duplicate, fill missing channel, exclude returns
DROP VIEW IF EXISTS v_sales_clean;
CREATE VIEW v_sales_clean AS
WITH dedup AS (
    SELECT *,
           ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY order_date) AS rn
    FROM fact_sales
)
SELECT order_id, order_date, ship_date, customer_id, product_id, rep_id, region_id,
       COALESCE(channel, 'Unknown') AS channel,
       payment_mode, quantity, unit_price, discount_pct,
       sales_amount, cost_amount, profit, is_returned
FROM dedup
WHERE rn = 1
  AND is_returned = 0;   -- returns analysed separately

-- 5. Confirm clean view
SELECT COUNT(*) AS clean_rows, COUNT(DISTINCT order_id) AS distinct_orders
FROM v_sales_clean;
