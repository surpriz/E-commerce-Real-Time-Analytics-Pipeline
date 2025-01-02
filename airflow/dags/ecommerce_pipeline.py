"""
DAG pour orchestrer le pipeline E-commerce
"""
from datetime import datetime, timedelta
from airflow.decorators import dag, task
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
import sys
import os
import logging
from airflow.models import Variable
from airflow.utils.email import send_email
import json




# Ajout du chemin des scripts au PYTHONPATH
SCRIPT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))
sys.path.insert(0, SCRIPT_PATH)

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

@dag(
    dag_id='ecommerce_pipeline',
    default_args={
        'owner': 'airflow',
        'depends_on_past': False,
        'email_on_failure': False,
        'email_on_retry': False,
        'retries': 1,
        'retry_delay': timedelta(minutes=5)
    },
    description='Pipeline ETL E-commerce complet',
    schedule_interval='0 1 * * *',
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=['ecommerce', 'etl']
)
def ecommerce_etl():
    
    @task(task_id="check_source_data")
    def verify_source_files():
        """Vérifie la présence des fichiers source"""
        required_files = [
            'olist_customers_dataset.csv',
            'olist_orders_dataset.csv',
            'olist_products_dataset.csv',
            'olist_sellers_dataset.csv'
        ]
        base_path = '/opt/airflow/scripts/data/raw'
        logging.info(f"Vérification des fichiers dans {base_path}")
        
        # Afficher le contenu du répertoire pour debug
        logging.info(f"Contenu du répertoire: {os.listdir(base_path)}")
        
        missing_files = []
        for file in required_files:
            file_path = os.path.join(base_path, file)
            if not os.path.exists(file_path):
                missing_files.append(file)
                logging.warning(f"Fichier manquant : {file}")
            else:
                logging.info(f"Fichier trouvé : {file}")
        
        if missing_files:
            raise FileNotFoundError(f"Fichiers manquants : {missing_files}")
        return True

    @task(task_id="load_raw_data")
    def load_raw_data():
        """Charge les données brutes dans Snowflake"""
        try:
            logging.info(f"PYTHONPATH actuel : {sys.path}")
            logging.info(f"Répertoire de travail : {os.getcwd()}")
            logging.info(f"Contenu de /opt/airflow/scripts : {os.listdir('/opt/airflow/scripts')}")
            
            # Import relatif depuis le dossier scripts
            sys.path.insert(0, '/opt/airflow/scripts')
            from data_ingestion import DataIngestion
            
            logging.info("Module data_ingestion importé avec succès")
            ingestion = DataIngestion()
            logging.info("Instance DataIngestion créée")
            
            # Traitement des fichiers
            processed_files = ingestion.process_all_files()
            logging.info(f"Fichiers traités : {processed_files}")
            
            return len(processed_files)
        except Exception as e:
            logging.error(f"Erreur dans load_raw_data : {str(e)}")
            logging.error(f"Détails de l'erreur : {type(e).__name__}")
            raise

    # Tâche DBT pour transformer les données
    dbt_run = BashOperator(
        task_id='dbt_run',
        bash_command='''
        cd /opt/dbt_transform/ecommerce && \
        dbt run --profiles-dir /opt/dbt_transform/profiles
        ''',
    )

    # Tâche DBT pour les tests
    dbt_test = BashOperator(
        task_id='dbt_test',
        bash_command='''
        cd /opt/dbt_transform/ecommerce && \
        dbt test --profiles-dir /opt/dbt_transform/profiles
        ''',
    )

    @task(task_id="verify_data_quality")
    def verify_data_quality():
        """Vérifie la qualité des données finales"""
        import snowflake.connector
        from os import getenv
        
        logging.info("Début de la vérification de la qualité des données")
        
        try:
            conn = snowflake.connector.connect(
                user=getenv('SNOWFLAKE_USER'),
                password=getenv('SNOWFLAKE_PASSWORD'),
                account=getenv('SNOWFLAKE_ACCOUNT'),
                warehouse='ECOMMERCE_WH',
                database='ECOMMERCE_DB',
                schema='DWH'
            )
            
            cur = conn.cursor()
            checks = [
                "SELECT COUNT(*) FROM dim_customers",
                "SELECT COUNT(*) FROM dim_products",
                "SELECT COUNT(*) FROM dim_sellers",
                "SELECT COUNT(*) FROM fact_orders"
            ]
            
            results = {}
            for check in checks:
                cur.execute(check)
                table_name = check.split('FROM')[1].strip()
                count = cur.fetchone()[0]
                results[table_name] = count
                logging.info(f"Table {table_name} : {count} lignes")
                
                if count == 0:
                    raise ValueError(f"Table {table_name} est vide!")
            
            cur.close()
            conn.close()
            return results
            
        except Exception as e:
            logging.error(f"Erreur lors de la vérification de la qualité : {str(e)}")
            raise

    @task(task_id="advanced_data_quality")
    def check_data_quality():
        import snowflake.connector
        from os import getenv
        
        # Connexion à Snowflake
        conn = snowflake.connector.connect(
            user=getenv('SNOWFLAKE_USER'),
            password=getenv('SNOWFLAKE_PASSWORD'),
            account=getenv('SNOWFLAKE_ACCOUNT'),
            warehouse='ECOMMERCE_WH',
            database='ECOMMERCE_DB',
            schema='DWH'
        )
        
        cur = conn.cursor()
        
        # Liste des vérifications à effectuer
        quality_checks = [
            # Vérification des doublons
            """
            SELECT COUNT(*) as duplicate_count
            FROM (
                SELECT customer_id, COUNT(*) as cnt
                FROM dim_customers
                GROUP BY customer_id
                HAVING cnt > 1
            )
            """,
            
            # Vérification de la cohérence des relations
            """
            SELECT COUNT(*) as orphan_orders
            FROM fact_orders f
            LEFT JOIN dim_customers c ON f.customer_id = c.customer_id
            WHERE c.customer_id IS NULL
            """,
            
            # Vérification des valeurs nulles critiques
            """
            SELECT 
                COUNT(CASE WHEN customer_id IS NULL THEN 1 END) as null_customers,
                COUNT(CASE WHEN order_purchase_timestamp IS NULL THEN 1 END) as null_dates
            FROM fact_orders
            """
        ]
        
        results = {}
        try:
            for idx, check in enumerate(quality_checks):
                cur.execute(check)
                results[f'check_{idx}'] = cur.fetchall()
                
            # Analyse des résultats
            if results['check_0'][0][0] > 0:  # Doublons trouvés
                logging.warning(f"Doublons détectés dans dim_customers: {results['check_0'][0][0]}")
                
            if results['check_1'][0][0] > 0:  # Commandes orphelines
                logging.error(f"Commandes sans client: {results['check_1'][0][0]}")
                
            null_checks = results['check_2'][0]
            if null_checks[0] > 0 or null_checks[1] > 0:
                logging.warning(f"Valeurs nulles détectées - Clients: {null_checks[0]}, Dates: {null_checks[1]}")
                
        finally:
            cur.close()
            conn.close()
        
        return results
        

    def alert_on_failure(context):
        """Fonction de callback en cas d'échec"""
        dag_id = context['dag'].dag_id
        task_id = context['task'].task_id
        execution_date = context['execution_date']
        error_message = context.get('exception', 'Unknown error')
        
        subject = f"Échec dans le pipeline {dag_id}"
        html_content = f"""
        <h3>Erreur dans le pipeline E-commerce</h3>
        <p><strong>DAG:</strong> {dag_id}</p>
        <p><strong>Tâche:</strong> {task_id}</p>
        <p><strong>Date d'exécution:</strong> {execution_date}</p>
        <p><strong>Erreur:</strong> {error_message}</p>
        """
        
        # Envoi de l'email
        send_email(
            to=['votre.email@example.com'],
            subject=subject,
            html_content=html_content
        )

    # Modifier les tâches pour inclure le callback
    verify_data_quality.on_failure_callback = alert_on_failure
    check_data_quality.on_failure_callback = alert_on_failure



    # Définition du flux de travail
    check_files = verify_source_files()
    load_data = load_raw_data()
    verify_quality = verify_data_quality()
    advanced_checks = check_data_quality()

    # Orchestration des tâches
    check_files >> load_data >> dbt_run >> dbt_test >> verify_quality >> advanced_checks

# Instanciation du DAG
dag = ecommerce_etl()