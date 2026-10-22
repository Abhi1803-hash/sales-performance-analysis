-- =====================================================================
-- 03_kpi_analysis.sql  |  Core business KPIs (associate-level)
-- All queries run on the cleaned view v_sales_clean
-- =====================================================================

-- Q1. Headline KPIs
SELECT ROUND(SUM(sales_amount), 0)                       AS total_revenue,
       ROUND(SUM(profit), 0)                             AS total_profit,
       ROUND(100.0 * SUM(profit) / SUM(sales_amount), 2) AS profit_margin_pct,
       COUNT(DISTINCT order_id)                          AS total_orders,
       COUNT(DISTINCT customer_id)                       AS active_customers,
       ROUND(SUM(sales_amount) / COUNT(DISTINCT order_id), 0) AS avg_order_value,
       SUM(quantity)                                     AS units_sold
FROM v_sales_clean;

-- Q2. Revenue and profit by year
SELECT strftime('%Y', order_date)              AS yr,
       ROUND(SUM(sales_amount), 0)             AS revenue,
       ROUND(SUM(profit), 0)                   AS profit,
       COUNT(DISTINCT order_id)                AS orders
FROM v_sales_clean
GROUP BY yr
ORDER BY yr;

-- Q3. Revenue by category & sub-category with margin
SELECT p.category, p.sub_category,
       ROUND(SUM(s.sales_amount), 0)                         AS revenue,
       ROUND(SUM(s.profit), 0)                               AS profit,
       ROUND(100.0 * SUM(s.profit) / SUM(s.sales_amount), 1) AS margin_pct
FROM v_sales_clean s
JOIN dim_products p ON p.product_id = s.product_id
GROUP BY p.category, p.sub_category
ORDER BY revenue DESC;

-- Q4. Revenue by region and its share of total
SELECT r.region_name,
       ROUND(SUM(s.sales_amount), 0) AS revenue,
       ROUND(100.0 * SUM(s.sales_amount) / (SELECT SUM(sales_amount) FROM v_sales_clean), 1)
                                     AS revenue_share_pct
FROM v_sales_clean s
JOIN dim_regions r ON r.region_id = s.region_id
GROUP BY r.region_name
ORDER BY revenue DESC;

-- Q5. Top 10 products by revenue
SELECT p.product_name, p.category,
       SUM(s.quantity)               AS units,
       ROUND(SUM(s.sales_amount), 0) AS revenue
FROM v_sales_clean s
JOIN dim_products p ON p.product_id = s.product_id
GROUP BY p.product_name, p.category
ORDER BY revenue DESC
LIMIT 10;

-- Q6. Segment and channel performance
SELECT c.segment, s.channel,
       COUNT(DISTINCT s.order_id)    AS orders,
       ROUND(SUM(s.sales_amount), 0) AS revenue,
       ROUND(AVG(s.sales_amount), 0) AS avg_order_value
FROM v_sales_clean s
JOIN dim_customers c ON c.customer_id = s.customer_id
GROUP BY c.segment, s.channel
ORDER BY c.segment, revenue DESC;

-- Q7. Discount impact on margin
SELECT discount_pct,
       COUNT(*)                                          AS orders,
       ROUND(SUM(sales_amount), 0)                       AS revenue,
       ROUND(100.0 * SUM(profit) / SUM(sales_amount), 1) AS margin_pct
FROM v_sales_clean
GROUP BY discount_pct
ORDER BY discount_pct;

-- Q8. Return rate by category (uses raw table, de-duplicated)
SELECT p.category,
       COUNT(DISTINCT f.order_id) AS orders,
       COUNT(DISTINCT CASE WHEN f.is_returned = 1 THEN f.order_id END) AS returned,
       ROUND(100.0 * COUNT(DISTINCT CASE WHEN f.is_returned = 1 THEN f.order_id END)
                   / COUNT(DISTINCT f.order_id), 2) AS return_rate_pct
FROM fact_sales f
JOIN dim_products p ON p.product_id = f.product_id
GROUP BY p.category
ORDER BY return_rate_pct DESC;

-- Q9. Average shipping days by region
SELECT r.region_name,
       ROUND(AVG(julianday(s.ship_date) - julianday(s.order_date)), 2) AS avg_ship_days
FROM v_sales_clean s
JOIN dim_regions r ON r.region_id = s.region_id
GROUP BY r.region_name
ORDER BY avg_ship_days;
