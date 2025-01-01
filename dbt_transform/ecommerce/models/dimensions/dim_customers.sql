-- dbt_transform/ecommerce/models/dimensions/dim_customers.sql
WITH customer_metrics AS (
    SELECT 
        customer_id,
        COUNT(DISTINCT order_id) as total_orders,
        MIN(order_purchase_timestamp) as first_order_date,
        MAX(order_purchase_timestamp) as last_order_date
    FROM {{ source('staging', 'stg_orders') }}
    GROUP BY 1
)

SELECT DISTINCT  -- Ajout du DISTINCT pour éviter les doublons
    c.customer_id,
    FIRST_VALUE(c.customer_unique_id) OVER (
        PARTITION BY c.customer_id 
        ORDER BY m.last_order_date DESC
    ) as customer_unique_id,
    FIRST_VALUE(c.customer_city) OVER (
        PARTITION BY c.customer_id 
        ORDER BY m.last_order_date DESC
    ) as customer_city,
    FIRST_VALUE(c.customer_state) OVER (
        PARTITION BY c.customer_id 
        ORDER BY m.last_order_date DESC
    ) as customer_state,
    FIRST_VALUE(c.customer_zip_code_prefix) OVER (
        PARTITION BY c.customer_id 
        ORDER BY m.last_order_date DESC
    ) as customer_zip_code_prefix,
    m.total_orders,
    m.first_order_date,
    m.last_order_date,
    DATEDIFF('day', m.first_order_date, m.last_order_date) as customer_lifetime_days
FROM {{ source('staging', 'stg_customers') }} c
LEFT JOIN customer_metrics m 
    ON c.customer_id = m.customer_id