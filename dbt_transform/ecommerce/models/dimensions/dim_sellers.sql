-- dbt_transform/ecommerce/models/dimensions/dim_sellers.sql
WITH seller_metrics AS (
    SELECT 
        seller_id,
        COUNT(DISTINCT order_id) as total_orders,
        COUNT(DISTINCT product_id) as total_products,
        SUM(price) as total_revenue,
        AVG(price) as avg_order_value
    FROM {{ source('staging', 'stg_order_items') }}
    GROUP BY 1
)

SELECT 
    s.seller_id,
    s.seller_city,
    s.seller_state,
    s.seller_zip_code_prefix,
    m.total_orders,
    m.total_products,
    m.total_revenue,
    m.avg_order_value
FROM {{ source('staging', 'stg_sellers') }} s
LEFT JOIN seller_metrics m 
    ON s.seller_id = m.seller_id