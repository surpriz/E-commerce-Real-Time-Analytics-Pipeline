# ------- Résumé -------
# Ce script Python télécharge un jeu de données e-commerce depuis Kaggle, le stocke localement, puis le charge dans une base de données Snowflake.
# Il gère la connexion à Snowflake, le téléchargement des données, la correspondance entre les fichiers CSV et les tables de la base de données, ainsi que le chargement des données dans Snowflake.
# Le processus est entièrement loggé pour faciliter le suivi et la déboggage.

import os  # Pour manipuler des chemins de fichiers et des variables d'environnement
import kaggle  # Pour interagir avec l'API Kaggle et télécharger des datasets
import logging  # Pour enregistrer des messages de log
from snowflake.connector import connect  # Pour se connecter à Snowflake
from dotenv import load_dotenv  # Pour charger les variables d'environnement depuis un fichier .env
from datetime import datetime  # Pour manipuler les dates et heures (non utilisé dans ce script)

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,  # Niveau de log minimal à enregistrer
    format='%(asctime)s - %(levelname)s - %(message)s',  # Format des messages de log
    handlers=[  # Les destinations des messages de log
        logging.FileHandler('data_ingestion.log'),  # Enregistre les logs dans un fichier
        logging.StreamHandler()  # Affiche les logs dans la console
    ]
)

class DataIngestion:
    def __init__(self):
        load_dotenv()  # Charge les variables d'environnement à partir du fichier .env
        self.snowflake_config = {  # Configuration pour se connecter à Snowflake
            'user': os.getenv('SNOWFLAKE_USER'),  # Nom d'utilisateur Snowflake
            'password': os.getenv('SNOWFLAKE_PASSWORD'),  # Mot de passe Snowflake
            'account': 'xfarmgt-lx08599',  # Nom du compte Snowflake
            'warehouse': 'ECOMMERCE_WH',  # Nom du warehouse Snowflake
            'database': 'ECOMMERCE_DB',  # Nom de la base de données Snowflake
            'schema': 'RAW'  # Nom du schéma Snowflake
        }
        self.data_path = 'data/raw'  # Chemin vers le répertoire où les données seront téléchargées

    def download_kaggle_dataset(self):
        """Télécharge le dataset Olist depuis Kaggle"""
        try:
            logging.info("Début du téléchargement du dataset Kaggle")
            kaggle.api.authenticate()  # Authentification à l'API Kaggle
            kaggle.api.dataset_download_files(
                'olistbr/brazilian-ecommerce',  # Identifiant du dataset Kaggle
                path=self.data_path,  # Répertoire de destination
                unzip=True  # Décompresse les fichiers après le téléchargement
            )
            logging.info("Dataset téléchargé avec succès")
        except Exception as e:
            logging.error(f"Erreur lors du téléchargement: {str(e)}")
            raise  # Relève l'exception pour qu'elle soit traitée à un niveau supérieur

    def get_file_mapping(self):
        """Mapping entre les fichiers CSV et les tables Snowflake"""
        return {  # Dictionnaire associant chaque fichier CSV à une table Snowflake
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
        conn = None
        try:
            # Vérification des paramètres de connexion
            logging.info("Configuration Snowflake:")
            for key, value in self.snowflake_config.items():
                if key != 'password':
                    logging.info(f"{key}: {value}")
                    
            # Tentative de connexion
            logging.info("Tentative de connexion à Snowflake...")
            conn = connect(**self.snowflake_config)  # Se connecte à Snowflake avec les paramètres configurés
            logging.info("Connexion à Snowflake réussie")
            
            cur = conn.cursor()  # Obtient un curseur pour exécuter des commandes SQL
            logging.info(f"Chargement du fichier {file_path} vers la table {table_name}")
            
            # Création du stage
            stage_name = f"{table_name}_stage"  # Nom du stage Snowflake
            cur.execute(f"""
            CREATE OR REPLACE STAGE {stage_name}
            FILE_FORMAT = (
                TYPE = CSV 
                FIELD_DELIMITER = ',' 
                SKIP_HEADER = 1
                FIELD_OPTIONALLY_ENCLOSED_BY = '"'
            )
            """)  # Crée un stage Snowflake pour stocker les fichiers CSV
            
            # Upload vers le stage
            put_command = f"PUT file://{file_path} @{stage_name}"  # Commande pour uploader le fichier vers le stage
            logging.info(f"Exécution de: {put_command}")
            cur.execute(put_command)  # Exécute la commande PUT
            
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
            cur.execute(copy_command)  # Exécute la commande COPY pour charger les données dans la table
            
            # Vérification
            cur.execute(f"SELECT COUNT(*) FROM {table_name}")  # Vérifie le nombre de lignes chargées
            count = cur.fetchone()[0]
            logging.info(f"Nombre de lignes chargées dans {table_name}: {count}")
            
        except Exception as e:
            logging.error(f"Erreur lors du chargement de {file_path}: {str(e)}")
            raise  # Relève l'exception pour qu'elle soit traitée à un niveau supérieur
        finally:
            if conn:
                conn.close()  # Ferme la connexion à Snowflake
                logging.info("Connexion Snowflake fermée")

    def process_all_files(self):
        """Traite tous les fichiers du dataset"""
        try:
            logging.info("Début du traitement de tous les fichiers")
            
            # Les fichiers sont déjà présents, pas besoin de les télécharger
            # Mais on peut vérifier leur présence
            file_mapping = self.get_file_mapping()
            processed_files = []
            
            for file_name, table_name in file_mapping.items():
                file_path = os.path.join('/opt/airflow/scripts/data/raw', file_name)  # Chemin complet du fichier
                if os.path.exists(file_path):
                    logging.info(f"Traitement du fichier: {file_path}")
                    self.upload_to_snowflake(file_path, table_name)  # Charge le fichier vers Snowflake
                    processed_files.append(file_name)
                else:
                    logging.warning(f"Fichier non trouvé: {file_path}")
            
            logging.info(f"Fichiers traités avec succès: {processed_files}")
            return processed_files
        except Exception as e:
            logging.error(f"Erreur lors du traitement des fichiers: {str(e)}")
            raise  # Relève l'exception pour qu'elle soit traitée à un niveau supérieur

def main():
    try:
        ingestion = DataIngestion()  # Instancie la classe DataIngestion
        
        # Test de connexion
        conn = connect(**ingestion.snowflake_config)  # Se connecte à Snowflake pour vérifier la connexion
        logging.info("Connexion à Snowflake réussie!")
        conn.close()
        
        # Téléchargement des données
        ingestion.download_kaggle_dataset()  # Télécharge le dataset depuis Kaggle
        
        # Chargement de chaque fichier
        file_mapping = ingestion.get_file_mapping()  # Obtient le mapping des fichiers et tables
        for file_name, table_name in file_mapping.items():
            file_path = os.path.join(ingestion.data_path, file_name)  # Chemin complet du fichier
            if os.path.exists(file_path):
                ingestion.upload_to_snowflake(file_path, table_name)  # Charge le fichier vers Snowflake
            else:
                logging.warning(f"Fichier non trouvé: {file_path}")
                
    except Exception as e:
        logging.error(f"Erreur dans le processus d'ingestion: {str(e)}")
        raise  # Relève l'exception pour qu'elle soit traitée à un niveau supérieur

if __name__ == "__main__":
    main()  # Exécute le script principal si ce fichier est exécuté directement