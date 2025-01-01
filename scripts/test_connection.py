import os
from dotenv import load_dotenv
from snowflake.connector import connect
import logging

logging.basicConfig(level=logging.INFO)

def test_snowflake_connection():
    load_dotenv()
    
    # Configuration
    snow_config = {
        'user': os.getenv('SNOWFLAKE_USER'),
        'password': os.getenv('SNOWFLAKE_PASSWORD'),
        'account': 'xfarmgt-lx08599',
        'warehouse': 'ECOMMERCE_WH',
        'database': 'ECOMMERCE_DB',
        'schema': 'RAW'
    }
    
    try:
        print("Tentative de connexion à Snowflake...")
        print(f"Account: {snow_config['account']}")
        
        conn = connect(**snow_config)
        cur = conn.cursor()
        
        # Test simple
        cur.execute('SELECT current_version()')
        version = cur.fetchone()[0]
        print(f"Connexion réussie! Version Snowflake: {version}")
        
        # Liste des schémas
        print("\nSchémas disponibles:")
        cur.execute('SHOW SCHEMAS')
        schemas = cur.fetchall()
        for schema in schemas:
            print(f"- {schema[1]}")
            
        conn.close()
        print("\nTest terminé avec succès!")
        
    except Exception as e:
        print(f"Erreur de connexion: {str(e)}")
        raise

if __name__ == "__main__":
    test_snowflake_connection()