"""DAG pour monitorer le pipeline temps réel"""
from datetime import datetime, timedelta
from airflow.decorators import dag, task
import snowflake.connector
import os

@dag(
    dag_id='realtime_pipeline_monitoring',
    schedule_interval='*/5 * * * *',  # Toutes les 5 minutes
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=['monitoring', 'realtime']
)
def monitor_pipeline():
    
    @task()
    def check_pipeline_health():
        """Vérifie la santé du pipeline temps réel"""
        conn = snowflake.connector.connect(
            user=os.getenv('SNOWFLAKE_USER'),
            password=os.getenv('SNOWFLAKE_PASSWORD'),
            account=os.getenv('SNOWFLAKE_ACCOUNT'),
            warehouse='ECOMMERCE_WH',
            database='ECOMMERCE_DB',
            schema='RAW'
        )
        
        try:
            cur = conn.cursor()
            
            # Vérifier les dernières insertions
            cur.execute("""
                SELECT COUNT(*) 
                FROM raw_orders_stream 
                WHERE insert_timestamp >= DATEADD(minute, -5, CURRENT_TIMESTAMP())
            """)
            recent_count = cur.fetchone()[0]
            
            if recent_count == 0:
                raise ValueError("Aucune nouvelle donnée dans les 5 dernières minutes!")
                
            # Vérifier les métriques
            cur.execute("CALL check_sales_spike()")
            spike_status = cur.fetchone()[0]
            
            return {
                'recent_orders': recent_count,
                'spike_status': spike_status
            }
            
        finally:
            conn.close()
    
    # Exécution des tâches
    pipeline_status = check_pipeline_health()

monitor_dag = monitor_pipeline()