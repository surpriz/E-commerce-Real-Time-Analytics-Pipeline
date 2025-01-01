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

SELECT 
    c.customer_id,
    c.customer_unique_id,
    c.customer_city,
    c.customer_state,
    c.customer_zip_code_prefix,
    m.total_orders,
    m.first_order_date,
    m.last_order_date,
    DATEDIFF('day', m.first_order_date, m.last_order_date) as customer_lifetime_days
FROM {{ source('staging', 'stg_customers') }} c
LEFT JOIN customer_metrics m 
    ON c.customer_id = m.customer_id