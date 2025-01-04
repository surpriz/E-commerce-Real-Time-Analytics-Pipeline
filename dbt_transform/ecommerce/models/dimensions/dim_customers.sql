-- dbt_transform/ecommerce/models/dimensions/dim_customers.sql
-- ------- Résumé -------
-- Ce script SQL crée une dimension clients (dim_customers) en combinant les données clients de base
-- avec des métriques calculées (nombre de commandes, dates première/dernière commande).
-- Il gère également la déduplication des données clients en gardant les informations les plus récentes.

-- Calcul des métriques par client (sous-requête)
WITH customer_metrics AS (
    SELECT 
        customer_id,  -- Identifiant unique du client
        COUNT(DISTINCT order_id) as total_orders,  -- Nombre total de commandes par client
        MIN(order_purchase_timestamp) as first_order_date,  -- Date de première commande
        MAX(order_purchase_timestamp) as last_order_date    -- Date de dernière commande
    FROM {{ source('staging', 'stg_orders') }}  -- Source des données : table staging des commandes
    GROUP BY 1  -- Groupement par customer_id
)

-- Requête principale : combine les données clients avec leurs métriques
SELECT DISTINCT  -- Élimine les doublons potentiels
    c.customer_id,  -- Clé primaire de la dimension client
    
    -- Pour chaque attribut client, on prend la valeur la plus récente
    -- en se basant sur la dernière date de commande
    FIRST_VALUE(c.customer_unique_id) OVER (
        PARTITION BY c.customer_id 
        ORDER BY m.last_order_date DESC
    ) as customer_unique_id,  -- Identifiant unique du client (peut différer du customer_id)
    
    FIRST_VALUE(c.customer_city) OVER (
        PARTITION BY c.customer_id 
        ORDER BY m.last_order_date DESC
    ) as customer_city,  -- Ville du client (version la plus récente)
    
    FIRST_VALUE(c.customer_state) OVER (
        PARTITION BY c.customer_id 
        ORDER BY m.last_order_date DESC
    ) as customer_state,  -- État/région du client (version la plus récente)
    
    FIRST_VALUE(c.customer_zip_code_prefix) OVER (
        PARTITION BY c.customer_id 
        ORDER BY m.last_order_date DESC
    ) as customer_zip_code_prefix,  -- Code postal du client (version la plus récente)
    
    -- Métriques calculées dans la sous-requête
    m.total_orders,  -- Nombre total de commandes du client
    m.first_order_date,  -- Date de première commande
    m.last_order_date,  -- Date de dernière commande
    
    -- Calcul de la durée de vie du client en jours
    DATEDIFF('day', m.first_order_date, m.last_order_date) as customer_lifetime_days

-- Jointure entre les données clients et leurs métriques
FROM {{ source('staging', 'stg_customers') }} c  -- Table source des données clients
LEFT JOIN customer_metrics m  -- Jointure avec les métriques calculées
    ON c.customer_id = m.customer_id  -- Condition de jointure sur l'ID client