-- models/facts/fact_orders.sql
WITH order_payments AS (
    SELECT 
        order_id,
        SUM(payment_value) as total_payment,
        MAX(payment_type) as payment_type,
        COUNT(payment_sequential) as payment_installments
    FROM {{ source('staging', 'stg_order_payments') }}
    GROUP BY 1
),

order_items_agg AS (
    SELECT 
        order_id,
        COUNT(DISTINCT product_id) as unique_products,
        COUNT(*) as total_items,
        SUM(price) as total_items_price,
        SUM(freight_value) as total_freight_value,
        ARRAY_AGG(product_id) as product_ids,
        ARRAY_AGG(seller_id) as seller_ids
    FROM {{ source('staging', 'stg_order_items') }}
    GROUP BY 1
),

order_reviews_agg AS (
    SELECT 
        order_id,
        AVG(review_score) as avg_review_score,
        COUNT(*) as review_count
    FROM {{ source('staging', 'stg_order_reviews') }}
    GROUP BY 1
)

SELECT DISTINCT
    o.order_id,
    o.customer_id,
    o.order_status,
    o.order_purchase_timestamp,
    o.order_approved_at,
    o.order_delivered_carrier_date,
    o.order_delivered_customer_date,
    o.order_estimated_delivery_date,
    
    -- Métriques des items
    COALESCE(oi.unique_products, 0) as unique_products,
    COALESCE(oi.total_items, 0) as total_items,
    COALESCE(oi.total_items_price, 0) as total_items_price,
    COALESCE(oi.total_freight_value, 0) as total_freight_value,
    oi.product_ids,
    oi.seller_ids,
    
    -- Métriques de paiement
    COALESCE(p.total_payment, 0) as total_payment,
    p.payment_type,
    COALESCE(p.payment_installments, 0) as payment_installments,
    
    -- Métriques de review
    r.avg_review_score,
    COALESCE(r.review_count, 0) as review_count,
    
    -- Métriques calculées
    COALESCE(oi.total_items_price, 0) + COALESCE(oi.total_freight_value, 0) as total_order_value
    
FROM {{ source('staging', 'stg_orders') }} o
LEFT JOIN order_items_agg oi ON o.order_id = oi.order_id
LEFT JOIN order_payments p ON o.order_id = p.order_id
LEFT JOIN order_reviews_agg r ON o.order_id = r.order_id