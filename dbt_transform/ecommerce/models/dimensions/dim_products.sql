-- dbt_transform/ecommerce/models/dimensions/dim_products.sql
WITH product_metrics AS (
    SELECT 
        product_id,
        COUNT(DISTINCT order_id) as total_orders,
        COUNT(DISTINCT seller_id) as total_sellers,
        AVG(price) as avg_price,
        MIN(price) as min_price,
        MAX(price) as max_price
    FROM {{ source('staging', 'stg_order_items') }}
    GROUP BY 1
)

SELECT DISTINCT  -- Ajout du DISTINCT pour éviter les doublons
    p.product_id,
    p.product_category_name,
    p.product_weight_g,
    p.product_length_cm,
    p.product_height_cm,
    p.product_width_cm,
    p.product_volume_cm3,
    p.weight_category,
    m.total_orders,
    m.total_sellers,
    m.avg_price,
    m.min_price,
    m.max_price,
    CASE  -- Ajout du price_range basé sur avg_price
        WHEN m.avg_price < 50 THEN 'Low'
        WHEN m.avg_price < 150 THEN 'Medium'
        ELSE 'High'
    END as price_range
FROM {{ source('staging', 'stg_products') }} p
LEFT JOIN product_metrics m 
    ON p.product_id = m.product_id