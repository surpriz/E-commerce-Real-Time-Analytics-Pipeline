# ------- Résumé -------
# Ce script Python télécharge un jeu de données e-commerce depuis Kaggle, le stocke localement, puis le charge dans une base de données Snowflake.
# Il gère la connexion à Snowflake, le téléchargement des données, la correspondance entre les fichiers CSV et les tables de la base de données, ainsi que le chargement des données dans Snowflake.
# Le processus est entièrement loggé pour faciliter le suivi et la déboggage.

import os
import kaggle
import logging
from snowflake.connector import connect
from dotenv import load_dotenv

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('data_ingestion.log'), logging.StreamHandler()]
)

class DataIngestion:
    def __init__(self):
        load_dotenv()
        self.snowflake_config = {
            'user': os.getenv('SNOWFLAKE_USER'),
            'password': os.getenv('SNOWFLAKE_PASSWORD'),
            'account': 'xfarmgt-lx08599',
            'warehouse': 'ECOMMERCE_WH',
            'database': 'ECOMMERCE_DB',
            'schema': 'RAW'
        }
        self.data_path = 'data/raw'

    def download_kaggle_dataset(self):
        """Télécharge le dataset Olist depuis Kaggle"""
        logging.info("Début du téléchargement du dataset Kaggle")
        kaggle.api.authenticate()
        kaggle.api.dataset_download_files(
            'olistbr/brazilian-ecommerce',
            path=self.data_path,
            unzip=True
        )
        logging.info("Dataset téléchargé avec succès")

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

    def upload_to_snowflake(self, file_path: str, table_name: str):
        """Upload un fichier CSV vers Snowflake"""
        conn = None
        try:
            logging.info("Configuration Snowflake:")
            for key, value in self.snowflake_config.items():
                if key != 'password':
                    logging.info(f"{key}: {value}")

            logging.info("Tentative de connexion à Snowflake...")
            conn = connect(**self.snowflake_config)
            logging.info("Connexion à Snowflake réussie")

            with conn.cursor() as cur:
                logging.info(f"Chargement du fichier {file_path} vers la table {table_name}")

                stage_name = f"{table_name}_stage"
                cur.execute(f"""
                CREATE OR REPLACE STAGE {stage_name}
                FILE_FORMAT = (
                    TYPE = 'CSV'
                    FIELD_DELIMITER = ','
                    SKIP_HEADER = 1
                    FIELD_OPTIONALLY_ENCLOSED_BY = '"'
                )
                """)

                put_command = f"PUT file://{file_path} @{stage_name}"
                logging.info(f"Exécution de: {put_command}")
                cur.execute(put_command)

                copy_command = f"""
                COPY INTO {table_name}
                FROM @{stage_name}
                FILE_FORMAT = (
                    TYPE = 'CSV'
                    FIELD_DELIMITER = ','
                    SKIP_HEADER = 1
                    FIELD_OPTIONALLY_ENCLOSED_BY = '"'
                )
                ON_ERROR = 'CONTINUE'
                """
                logging.info(f"Exécution de: COPY INTO {table_name}")
                cur.execute(copy_command)

                cur.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cur.fetchone()[0]
                logging.info(f"Nombre de lignes chargées dans {table_name}: {count}")

        except Exception as e:
            logging.error(f"Erreur lors du chargement de {file_path}: {str(e)}")
        finally:
            if conn:
                conn.close()
                logging.info("Connexion Snowflake fermée")

    def process_all_files(self):
        """Traite tous les fichiers du dataset"""
        logging.info("Début du traitement de tous les fichiers")
        file_mapping = self.get_file_mapping()
        processed_files = []

        for file_name, table_name in file_mapping.items():
            file_path = os.path.join(self.data_path, file_name)
            if os.path.exists(file_path):
                logging.info(f"Traitement du fichier: {file_path}")
                self.upload_to_snowflake(file_path, table_name)
                processed_files.append(file_name)
            else:
                logging.warning(f"Fichier non trouvé: {file_path}")

        logging.info(f"Fichiers traités avec succès: {processed_files}")
        return processed_files

def main():
    ingestion = DataIngestion()

    # Test de connexion
    try:
        with connect(**ingestion.snowflake_config) as conn:
            logging.info("Connexion à Snowflake réussie!")
    except Exception as e:
        logging.error(f"Erreur de connexion à Snowflake: {str(e)}")
        return

    # Téléchargement des données
    ingestion.download_kaggle_dataset()

    # Chargement de chaque fichier
    ingestion.process_all_files()

if __name__ == "__main__":
    main()