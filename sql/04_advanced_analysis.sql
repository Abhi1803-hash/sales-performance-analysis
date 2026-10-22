-- =====================================================================
-- 04_advanced_analysis.sql  |  Window functions, CTEs, RFM, cohorts
-- =====================================================================

-- A1. Monthly revenue with MoM growth and running total
WITH monthly AS (
    SELECT strftime('%Y-%m', order_date) AS month,
           SUM(sales_amount)             AS revenue
    FROM v_sales_clean
    GROUP BY month
)
SELECT month,
       ROUND(revenue, 0) AS revenue,
       ROUND(100.0 * (revenue - LAG(revenue) OVER (ORDER BY month))
                   / LAG(revenue) OVER (ORDER BY month), 1)          AS mom_growth_pct,
       ROUND(SUM(revenue) OVER (PARTITION BY substr(month, 1, 4)
                                ORDER BY month), 0)                 AS ytd_revenue,
       ROUND(AVG(revenue) OVER (ORDER BY month
                                ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 0) AS rolling_3m_avg
FROM monthly
ORDER BY month;

-- A2. Year-over-year growth by month (2025 vs 2024)
WITH m AS (
    SELECT strftime('%m', order_date) AS mon,
           SUM(CASE WHEN strftime('%Y', order_date) = '2024' THEN sales_amount END) AS rev_2024,
           SUM(CASE WHEN strftime('%Y', order_date) = '2025' THEN sales_amount END) AS rev_2025
    FROM v_sales_clean
    GROUP BY mon
)
SELECT mon,
       ROUND(rev_2024, 0) AS rev_2024,
       ROUND(rev_2025, 0) AS rev_2025,
       ROUND(100.0 * (rev_2025 - rev_2024) / rev_2024, 1) AS yoy_growth_pct
FROM m
ORDER BY mon;

-- A3. Top 3 products in each category (RANK)
WITH prod AS (
    SELECT p.category, p.product_name, SUM(s.sales_amount) AS revenue
    FROM v_sales_clean s
    JOIN dim_products p ON p.product_id = s.product_id
    GROUP BY p.category, p.product_name
), ranked AS (
    SELECT *, RANK() OVER (PARTITION BY category ORDER BY revenue DESC) AS rnk
    FROM prod
)
SELECT category, rnk, product_name, ROUND(revenue, 0) AS revenue
FROM ranked
WHERE rnk <= 3
ORDER BY category, rnk;

-- A4. Sales rep performance vs annual target (2025)
WITH rep_sales AS (
    SELECT rep_id, SUM(sales_amount) AS revenue_2025
    FROM v_sales_clean
    WHERE strftime('%Y', order_date) = '2025'
    GROUP BY rep_id
)
SELECT sr.rep_name, r.region_name,
       ROUND(rs.revenue_2025, 0)                              AS revenue_2025,
       sr.annual_target,
       ROUND(100.0 * rs.revenue_2025 / sr.annual_target, 1)   AS target_achievement_pct,
       DENSE_RANK() OVER (ORDER BY rs.revenue_2025 DESC)      AS overall_rank,
       CASE WHEN rs.revenue_2025 >= sr.annual_target THEN 'Met' ELSE 'Missed' END AS status
FROM rep_sales rs
JOIN dim_sales_reps sr ON sr.rep_id = rs.rep_id
JOIN dim_regions r     ON r.region_id = sr.region_id
ORDER BY target_achievement_pct DESC;

-- A5. Pareto: share of revenue from top 20% of customers
WITH cust AS (
    SELECT customer_id, SUM(sales_amount) AS revenue
    FROM v_sales_clean
    GROUP BY customer_id
), ranked AS (
    SELECT revenue,
           NTILE(5) OVER (ORDER BY revenue DESC) AS quintile
    FROM cust
)
SELECT quintile,
       COUNT(*)                                                 AS customers,
       ROUND(SUM(revenue), 0)                                   AS revenue,
       ROUND(100.0 * SUM(revenue) / (SELECT SUM(revenue) FROM cust), 1) AS revenue_share_pct
FROM ranked
GROUP BY quintile
ORDER BY quintile;

-- A6. RFM customer segmentation (reference date = day after last order)
WITH ref AS (SELECT DATE(MAX(order_date), '+1 day') AS ref_date FROM v_sales_clean),
rfm AS (
    SELECT customer_id,
           CAST(julianday((SELECT ref_date FROM ref)) - julianday(MAX(order_date)) AS INT) AS recency_days,
           COUNT(DISTINCT order_id) AS frequency,
           SUM(sales_amount)        AS monetary
    FROM v_sales_clean
    GROUP BY customer_id
), scored AS (
    SELECT *,
           NTILE(4) OVER (ORDER BY recency_days DESC) AS r_score,  -- recent = 4
           NTILE(4) OVER (ORDER BY frequency)         AS f_score,
           NTILE(4) OVER (ORDER BY monetary)          AS m_score
    FROM rfm
)
SELECT CASE
         WHEN r_score >= 3 AND f_score >= 3 AND m_score >= 3 THEN 'Champions'
         WHEN r_score >= 3 AND f_score >= 2                  THEN 'Loyal'
         WHEN r_score >= 3                                   THEN 'Promising'
         WHEN r_score = 2                                    THEN 'Needs Attention'
         ELSE 'At Risk'
       END                         AS rfm_segment,
       COUNT(*)                    AS customers,
       ROUND(AVG(recency_days), 0) AS avg_recency_days,
       ROUND(AVG(frequency), 1)    AS avg_orders,
       ROUND(SUM(monetary), 0)     AS revenue
FROM scored
GROUP BY rfm_segment
ORDER BY revenue DESC;

-- A7. Monthly cohort retention (2024 first-purchase cohorts)
WITH first_order AS (
    SELECT customer_id, MIN(strftime('%Y-%m', order_date)) AS cohort
    FROM v_sales_clean
    GROUP BY customer_id
), activity AS (
    SELECT DISTINCT s.customer_id, f.cohort,
           (CAST(strftime('%Y', s.order_date) AS INT) - CAST(substr(f.cohort,1,4) AS INT)) * 12
         + (CAST(strftime('%m', s.order_date) AS INT) - CAST(substr(f.cohort,6,2) AS INT)) AS month_n
    FROM v_sales_clean s
    JOIN first_order f ON f.customer_id = s.customer_id
)
SELECT cohort,
       COUNT(DISTINCT CASE WHEN month_n = 0 THEN customer_id END) AS m0,
       ROUND(100.0 * COUNT(DISTINCT CASE WHEN month_n = 1 THEN customer_id END)
             / COUNT(DISTINCT CASE WHEN month_n = 0 THEN customer_id END), 1) AS m1_pct,
       ROUND(100.0 * COUNT(DISTINCT CASE WHEN month_n = 3 THEN customer_id END)
             / COUNT(DISTINCT CASE WHEN month_n = 0 THEN customer_id END), 1) AS m3_pct,
       ROUND(100.0 * COUNT(DISTINCT CASE WHEN month_n = 6 THEN customer_id END)
             / COUNT(DISTINCT CASE WHEN month_n = 0 THEN customer_id END), 1) AS m6_pct
FROM activity
WHERE cohort LIKE '2024-%'
GROUP BY cohort
ORDER BY cohort;

-- A8. Customers who bought in 2024 but not in 2025 (churned)
SELECT COUNT(*) AS churned_customers
FROM (
    SELECT customer_id FROM v_sales_clean WHERE strftime('%Y', order_date) = '2024'
    EXCEPT
    SELECT customer_id FROM v_sales_clean WHERE strftime('%Y', order_date) = '2025'
);
