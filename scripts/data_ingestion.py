import os
import kaggle
import logging
from snowflake.connector import connect
from dotenv import load_dotenv
from datetime import datetime

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data_ingestion.log'),
        logging.StreamHandler()
    ]
)

class DataIngestion:
    def __init__(self):
        load_dotenv()
        self.snowflake_config = {
            'user': os.getenv('SNOWFLAKE_USER'),
            'password': os.getenv('SNOWFLAKE_PASSWORD'),
            'account': 'xfarmgt-lx08599',  # Format corrigé
            'warehouse': 'ECOMMERCE_WH',
            'database': 'ECOMMERCE_DB',
            'schema': 'RAW'
        }
        self.data_path = 'data/raw'
        
    def download_kaggle_dataset(self):
        """Télécharge le dataset Olist depuis Kaggle"""
        try:
            logging.info("Début du téléchargement du dataset Kaggle")
            kaggle.api.authenticate()
            kaggle.api.dataset_download_files(
                'olistbr/brazilian-ecommerce',
                path=self.data_path,
                unzip=True
            )
            logging.info("Dataset téléchargé avec succès")
        except Exception as e:
            logging.error(f"Erreur lors du téléchargement: {str(e)}")
            raise
            
    def get_file_mapping(self):
        """Mapping entre les fichiers CSV et les tables Snowflake"""
        return {
            'olist_customers_dataset.csv': 'raw_customers',
            'olist_orders_dataset.csv': 'raw_orders',
            'olist_order_items_dataset.csv': 'raw_order_items',
            'olist_products_dataset.csv': 'raw_products',
            'olist_sellers_dataset.csv': 'raw_sellers',
            'olist_order_reviews_dataset.csv': 'raw_order_reviews',
            'olist_order_payments_dataset.csv': 'raw_order_payments',
            'product_category_name_translation.csv': 'raw_product_category_name_translation'
        }
        
    def upload_to_snowflake(self, file_path, table_name):
        """Upload un fichier CSV vers Snowflake"""
        try:
            conn = connect(**self.snowflake_config)
            cur = conn.cursor()
            logging.info(f"Chargement du fichier {file_path} vers la table {table_name}")
            
            # Création du stage
            stage_name = f"{table_name}_stage"
            cur.execute(f"""
            CREATE OR REPLACE STAGE {stage_name}
            FILE_FORMAT = (
                TYPE = CSV 
                FIELD_DELIMITER = ',' 
                SKIP_HEADER = 1
                FIELD_OPTIONALLY_ENCLOSED_BY = '"'
            )
            """)
            
            # Upload vers le stage
            put_command = f"PUT file://{file_path} @{stage_name}"
            logging.info(f"Exécution de: {put_command}")
            cur.execute(put_command)
            
            # Copie dans la table
            copy_command = f"""
            COPY INTO {table_name}
            FROM @{stage_name}
            FILE_FORMAT = (
                TYPE = CSV 
                FIELD_DELIMITER = ',' 
                SKIP_HEADER = 1
                FIELD_OPTIONALLY_ENCLOSED_BY = '"'
            )
            ON_ERROR = CONTINUE
            """
            logging.info(f"Exécution de: COPY INTO {table_name}")
            cur.execute(copy_command)
            
            # Vérification
            cur.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cur.fetchone()[0]
            logging.info(f"Nombre de lignes chargées dans {table_name}: {count}")
            
        except Exception as e:
            logging.error(f"Erreur lors du chargement de {file_path}: {str(e)}")
            raise
        finally:
            if conn:
                conn.close()

def main():
    try:
        ingestion = DataIngestion()
        
        # Test de connexion
        conn = connect(**ingestion.snowflake_config)
        logging.info("Connexion à Snowflake réussie!")
        conn.close()
        
        # Téléchargement des données
        ingestion.download_kaggle_dataset()
        
        # Chargement de chaque fichier
        file_mapping = ingestion.get_file_mapping()
        for file_name, table_name in file_mapping.items():
            file_path = os.path.join(ingestion.data_path, file_name)
            if os.path.exists(file_path):
                ingestion.upload_to_snowflake(file_path, table_name)
            else:
                logging.warning(f"Fichier non trouvé: {file_path}")
                
    except Exception as e:
        logging.error(f"Erreur dans le processus d'ingestion: {str(e)}")
        raise

if __name__ == "__main__":
    main()