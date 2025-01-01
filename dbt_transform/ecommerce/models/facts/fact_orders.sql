-- dbt_transform/ecommerce/models/facts/fact_orders.sql
WITH order_payments AS (
    SELECT 
        order_id,
        SUM(payment_value) as total_payment,
        MAX(payment_type) as payment_type,
        COUNT(payment_sequential) as payment_installments
    FROM {{ source('staging', 'stg_order_payments') }}
    GROUP BY 1
),

order_reviews AS (
    SELECT 
        order_id,
        AVG(review_score) as avg_review_score,
        COUNT(*) as review_count
    FROM {{ source('staging', 'stg_order_reviews') }}
    GROUP BY 1
)

SELECT 
    -- Clés
    o.order_id,
    o.customer_id,
    oi.seller_id,
    oi.product_id,
    
    -- Timestamps
    o.order_purchase_timestamp,
    o.order_approved_at,
    o.order_delivered_carrier_date,
    o.order_delivered_customer_date,
    o.order_estimated_delivery_date,
    
    -- Métriques de commande
    oi.price as item_price,
    oi.freight_value as shipping_cost,
    p.total_payment,
    p.payment_type,
    p.payment_installments,
    
    -- Métriques de livraison
    o.delivery_delay_days,
    o.is_delivered_on_time,
    
    -- Reviews
    r.avg_review_score,
    r.review_count,
    
    -- Métriques calculées
    (oi.price + oi.freight_value) as total_order_value
FROM {{ source('staging', 'stg_orders') }} o
JOIN {{ source('staging', 'stg_order_items') }} oi 
    ON o.order_id = oi.order_id
LEFT JOIN order_payments p 
    ON o.order_id = p.order_id
LEFT JOIN order_reviews r 
    ON o.order_id = r.order_id