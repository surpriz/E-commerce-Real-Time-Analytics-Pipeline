1. **Source initiale des données :**
   - Les données proviennent du dataset Kaggle "brazilian-ecommerce" (`olistbr/brazilian-ecommerce`)
   - Le téléchargement se fait via l'API Kaggle dans la méthode `download_kaggle_dataset()`

2. **Stockage local intermédiaire :**
   - Les fichiers sont d'abord téléchargés dans le dossier local : `data/raw`
   - Pour le contexte Airflow, le chemin complet est : `/opt/airflow/scripts/data/raw`

3. **Destination Snowflake :**
La configuration Snowflake montre que les données sont stockées dans :
```python
self.snowflake_config = {
    'account': 'xfarmgt-lx08599',
    'warehouse': 'ECOMMERCE_WH',    # Warehouse utilisé pour le traitement
    'database': 'ECOMMERCE_DB',     # Base de données de destination
    'schema': 'RAW'                 # Schéma utilisé
}
```

4. **Tables de destination dans Snowflake :**
Le mapping des fichiers vers les tables est défini dans `get_file_mapping()` :
```python
{
    'olist_customers_dataset.csv': 'raw_customers',
    'olist_orders_dataset.csv': 'raw_orders',
    'olist_order_items_dataset.csv': 'raw_order_items',
    'olist_products_dataset.csv': 'raw_products',
    'olist_sellers_dataset.csv': 'raw_sellers',
    'olist_order_reviews_dataset.csv': 'raw_order_reviews',
    'olist_order_payments_dataset.csv': 'raw_order_payments',
    'product_category_name_translation.csv': 'raw_product_category_name_translation'
}
```

5. **Processus de chargement dans Snowflake :**
   - Pour chaque fichier, un stage temporaire est créé (exemple : `raw_customers_stage`)
   - Les données sont d'abord chargées dans ce stage
   - Puis copiées du stage vers la table finale via la commande `COPY INTO`

Donc en résumé :
```
Kaggle → Fichiers locaux → Snowflake Stage → Tables Snowflake
(API)     (/opt/airflow/   (stages temporaires) (ECOMMERCE_DB.RAW.raw_*)
           scripts/data/raw)
```

Toutes les tables sont stockées dans :
- Base de données : `ECOMMERCE_DB`
- Schéma : `RAW`
- Noms des tables : préfixées par `raw_` (ex: `raw_customers`, `raw_orders`, etc.)

Le warehouse `ECOMMERCE_WH` est utilisé pour exécuter les opérations de chargement mais ne stocke pas les données en tant que tel - il fournit les ressources de calcul pour le traitement.


1. **Base de données (ECOMMERCE_DB)**
   C'est le conteneur principal qui contient 5 schémas différents :
   - DWH (Data Warehouse)
   - INFORMATION_SCHEMA
   - PUBLIC 
   - RAW (où sont stockées les données brutes)
   - STAGING (pour les données intermédiaires)

2. **Warehouses** (Ce sont les ressources de calcul)
Il y a 3 warehouses de taille XS :
   - COMPUTE_WH : Pour les calculs généraux
   - ECOMMERCE_WH : Dédié aux opérations e-commerce (celui utilisé dans le code)
   - SYSTEMS$STREAMLIT_NOTEBOOK : Un warehouse système

Important de comprendre :
- Les warehouses sont comme des "moteurs de calcul" - ils ne stockent pas de données
- Ils sont actuellement en statut "Suspended" pour économiser des crédits
- Ils sont tous de taille XS (extra small)

3. **Organisation des données**
```
ECOMMERCE_DB
    │
    ├── RAW (Données brutes)
    │   ├── raw_customers
    │   ├── raw_orders
    │   ├── raw_order_items
    │   ├── raw_products
    │   └── ... (autres tables raw)
    │
    ├── STAGING (Données intermédiaires)
    │
    ├── DWH (Data Warehouse - données transformées)
    │
    ├── PUBLIC
    │
    └── INFORMATION_SCHEMA
```

Le flux de données typique est :
1. Les données sont d'abord chargées dans le schéma RAW (données brutes)
2. Elles peuvent passer par le schéma STAGING pour transformation
3. Pour finir dans le schéma DWH pour l'analyse

ECOMMERCE_WH est le warehouse qui fournit la puissance de calcul pour exécuter les requêtes et les transformations, mais ne stocke pas les données lui-même.