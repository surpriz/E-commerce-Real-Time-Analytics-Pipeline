import streamlit as st
import snowflake.connector
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

def create_snowflake_connection():
    return snowflake.connector.connect(
        user=os.getenv('SNOWFLAKE_USER'),
        password=os.getenv('SNOWFLAKE_PASSWORD'),
        account=os.getenv('SNOWFLAKE_ACCOUNT'),
        warehouse='ECOMMERCE_WH',
        database='ECOMMERCE_DB',
        schema='RAW'
    )

def get_real_time_metrics(conn):
    return pd.read_sql("""
        SELECT 
            DATE_TRUNC('hour', order_timestamp) AS "hour",
            COUNT(*) AS "orders_count",
            SUM(price * quantity) AS "total_revenue",
            SUM(quantity) AS "items_count"
        FROM raw_orders_stream
        GROUP BY 1
        ORDER BY 1 DESC
        LIMIT 24
    """, conn)

def get_top_sellers(conn, period="Dernière heure"):
    period_filter = """
        WHERE order_timestamp >= DATEADD(hour, -1, CURRENT_TIMESTAMP())
    """
    if period == "Aujourd'hui":
        period_filter = """
            WHERE DATE(order_timestamp) = CURRENT_DATE()
        """
    elif period == "Cette semaine":
        period_filter = """
            WHERE order_timestamp >= DATEADD(day, -7, CURRENT_TIMESTAMP())
        """
    
    query = f"""
        SELECT 
            seller_id AS "seller_id",
            SUM(price * quantity) AS "revenue"
        FROM raw_orders_stream
        {period_filter}
        GROUP BY 1
        ORDER BY 2 DESC
        LIMIT 10
    """
    return pd.read_sql(query, conn)

def get_sales_status(conn):
    return pd.read_sql("""
        CALL check_sales_spike()
    """, conn).iloc[0, 0]

# Configuration de la page
st.set_page_config(page_title="E-commerce Real-Time Analytics", layout="wide")
st.title("E-commerce Real-Time Analytics")

try:
    # Connexion à Snowflake
    conn = create_snowflake_connection()

    # KPIs
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)

    kpi_data = pd.read_sql("""
        SELECT 
            COUNT(*) AS "orders_count",
            SUM(quantity) AS "items_count",
            ROUND(AVG(price), 2) AS "avg_value",
            COUNT(DISTINCT seller_id) AS "sellers_count"
        FROM raw_orders_stream
        WHERE order_timestamp >= DATEADD(hour, -1, CURRENT_TIMESTAMP())
    """, conn)
    
    # Ajouter des logs pour déboguer
    st.write("Données KPI récupérées :", kpi_data)
    st.write("Colonnes disponibles :", kpi_data.columns)

    kpi1.metric("Commandes (1h)", kpi_data['orders_count'].iloc[0])
    kpi2.metric("Articles vendus (1h)", kpi_data['items_count'].iloc[0])
    kpi3.metric("Panier moyen", f"€{kpi_data['avg_value'].iloc[0]}")
    kpi4.metric("Vendeurs actifs", kpi_data['sellers_count'].iloc[0])

    # Graphiques
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Ventes horaires")
        metrics = get_real_time_metrics(conn)
        
        # Ajouter des logs pour déboguer
        st.write("Données Ventes Horaires :", metrics)
        st.write("Colonnes disponibles :", metrics.columns)
        
        metric_mapping = {
            "Nombre de commandes": "orders_count",
            "Chiffre d'affaires": "total_revenue",
            "Quantité d'articles": "items_count"
        }
        
        selected_metric = st.selectbox(
            "Choisir la métrique",
            list(metric_mapping.keys())
        )
        
        fig = px.line(
            metrics,
            x='hour',  # Assurez-vous que 'hour' correspond à l'alias cité
            y=metric_mapping[selected_metric],
            title=f"Evolution des {selected_metric.lower()}"
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Top 10 Vendeurs")
        period = st.selectbox(
            "Période",
            ["Dernière heure", "Aujourd'hui", "Cette semaine"]
        )
        sellers = get_top_sellers(conn, period)
        
        # Ajouter des logs pour déboguer
        st.write("Données Top Vendeurs :", sellers)
        st.write("Colonnes disponibles :", sellers.columns)
        
        fig = px.bar(
            sellers,
            x='seller_id',  # Maintenant, 'seller_id' est correctement nommé
            y='revenue',
            title="Revenus par vendeur"
        )
        st.plotly_chart(fig, use_container_width=True)

    # Distribution des ventes
    st.subheader("Distribution des ventes")
    heatmap_data = pd.read_sql("""
        SELECT 
            DAYNAME(order_timestamp) AS "day_of_week",
            HOUR(order_timestamp) AS "hour_of_day",
            COUNT(*) AS "order_count"
        FROM raw_orders_stream
        GROUP BY 1, 2
    """, conn)
    
    # Ajouter des logs pour déboguer
    st.write("Données Heatmap :", heatmap_data)
    st.write("Colonnes disponibles :", heatmap_data.columns)
    
    fig = px.density_heatmap(
        heatmap_data,
        x='hour_of_day',
        y='day_of_week',
        z='order_count',
        title="Distribution des commandes par jour et heure"
    )
    st.plotly_chart(fig, use_container_width=True)

    # Statut des ventes
    status = get_sales_status(conn)
    if "ALERT" in status:
        st.error(status)
    else:
        st.success(status)

finally:
    # Fermeture de la connexion
    if 'conn' in locals():
        conn.close()

# Bouton de rafraîchissement
if st.button("Rafraîchir les données"):
    st.experimental_rerun()
