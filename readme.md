# E-commerce Real-Time Analytics Pipeline

![Dashboard Screenshot](./docs/images/dashboard.png)

Une solution complète d'analyse de données e-commerce combinant données historiques et temps réel, construite avec Kafka, Snowflake, DBT et Streamlit.

## 📋 Vue d'ensemble

Ce projet met en place un pipeline de données complet pour analyser les ventes e-commerce selon deux axes :
1. **Analyse historique** : Traitement des données passées via Kaggle
2. **Analyse temps réel** : Streaming des nouvelles commandes via Kafka

### Technologies utilisées

- **Apache Kafka** : Streaming des données temps réel
- **Snowflake** : Data Warehouse cloud
- **DBT** : Transformation et modélisation des données
- **Streamlit** : Dashboard de visualisation
- **Airflow** : Orchestration des tâches
- **Docker** : Conteneurisation des services

## 🏗 Architecture

Le pipeline est composé de deux flux principaux :

### 1. Flux Historique
```
Kaggle Dataset -> Python Script -> Snowflake (RAW) -> DBT -> Snowflake (DWH)
```

### 2. Flux Temps Réel
```
Kafka Producer -> Kafka -> Kafka Consumer -> Snowflake (RAW) -> DBT -> Snowflake (DWH)
```

Les deux flux alimentent le même modèle de données final, permettant une analyse unifiée via le dashboard Streamlit.

## ⚙️ Installation

1. **Prérequis**
```bash
# Installation des dépendances système
python 3.9+
docker
docker-compose
```

2. **Configuration**

Créez un fichier `.env` à la racine :
```env
SNOWFLAKE_USER=votre_user
SNOWFLAKE_PASSWORD=votre_password
SNOWFLAKE_ACCOUNT=votre_account
```

3. **Démarrage des services**
```bash
# Lancer l'infrastructure
docker-compose up -d

# Vérifier les services
docker-compose ps
```

## 🚀 Utilisation

### 1. Ingestion des données historiques

```bash
# Activation de l'environnement virtuel
cd scripts/kafka_scripts
python -m venv venv
source venv/bin/activate

# Exécution du script d'ingestion
python data_ingestion.py
```

### 2. Flux temps réel

```bash
# Terminal 1 : Producer
python order_producer.py

# Terminal 2 : Consumer
python order_consumer.py
```

### 3. Transformations DBT

Les transformations DBT créent :
- Dimensions (customers, products, sellers)
- Faits (orders)

```bash
# Exécution des transformations
dbt run
dbt test
```

### 4. Dashboard

Le dashboard est accessible à :
- http://localhost:8501 (Streamlit)
- http://localhost:9000 (Kafdrop - monitoring Kafka)
- http://localhost:8080 (Airflow)

## 📊 Monitoring

Le projet inclut plusieurs points de monitoring :
- **Kafdrop** : Visualisation des topics et messages Kafka
- **Airflow** : Supervision des tâches et pipelines
- **Streamlit** : Dashboard temps réel avec alertes

## 📁 Structure du projet

```
ecommerce_pipeline/
├── airflow/
│   └── dags/                # DAGs Airflow
├── data/
│   └── raw/                 # Données Kaggle
├── dbt_transform/
│   ├── models/             # Modèles DBT
│   └── profiles/           # Configuration DBT
├── docker/
│   └── docker-compose.yml  # Configuration Docker
└── scripts/
    └── kafka_scripts/      # Scripts Python
```

## 🔍 Points clés

- **Modèle de données** : Structure en étoile pour optimiser les analyses
- **Temps réel** : Latence < 5 secondes pour les nouvelles commandes
- **Scalabilité** : Architecture distribuée via Kafka et Snowflake
- **Monitoring** : Alertes sur pics de vente et anomalies
- **Documentation** : Auto-générée via DBT

## 🤝 Contribution

Les contributions sont les bienvenues ! N'hésitez pas à :
1. Fork le projet
2. Créer une branche (`git checkout -b feature/amazing-feature`)
3. Commit vos changements (`git commit -m 'Add amazing feature'`)
4. Push vers la branche (`git push origin feature/amazing-feature`)
5. Ouvrir une Pull Request