-- dbt_transform/ecommerce/tests/assert_price_consistency.sql
-- Ce test vérifie que total_order_value = item_price + shipping_cost
SELECT 
    order_id,
    item_price,
    shipping_cost,
    total_order_value,
    ABS((item_price + shipping_cost) - total_order_value) as price_diff
FROM {{ ref('fact_orders') }}
WHERE ABS((item_price + shipping_cost) - total_order_value) > 0.01  -- Tolérance de 0.01