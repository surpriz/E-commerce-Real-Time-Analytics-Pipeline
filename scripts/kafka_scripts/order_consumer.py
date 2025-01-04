from confluent_kafka import Consumer, KafkaError
import json
import logging
from snowflake.connector import connect
import os
from datetime import datetime
from dotenv import load_dotenv
from time import sleep

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class OrderConsumer:
    def __init__(self):
        load_dotenv()
        
        # Configuration Kafka
        self.conf = {
            'bootstrap.servers': 'localhost:9092',
            'group.id': 'order_consumer_group',
            'auto.offset.reset': 'earliest'
        }
        self.consumer = Consumer(self.conf)
        
        # Configuration Snowflake
        self.snowflake_config = {
            'user': os.getenv('SNOWFLAKE_USER'),
            'password': os.getenv('SNOWFLAKE_PASSWORD'),
            'account': os.getenv('SNOWFLAKE_ACCOUNT'),
            'warehouse': 'ECOMMERCE_WH',
            'database': 'ECOMMERCE_DB',
            'schema': 'RAW',
            'role': 'ACCOUNTADMIN'
        }
        
        # Initialisation de la connexion
        self.conn = None
        self.cur = None
        self.batch = []
        self.batch_size = 10  # Nombre de commandes à accumuler avant insertion
        self.reconnect()
        
    def reconnect(self):
        """Établit une nouvelle connexion à Snowflake"""
        try:
            if self.conn:
                self.conn.close()
            self.conn = connect(**self.snowflake_config)
            self.cur = self.conn.cursor()
            logger.info("Connexion Snowflake établie")
            
            # Création de la table si nécessaire
            self.cur.execute("""
            CREATE TABLE IF NOT EXISTS raw_orders_stream (
                order_id VARCHAR(50),
                customer_id VARCHAR(50),
                product_id VARCHAR(50),
                seller_id VARCHAR(50),
                quantity INTEGER,
                price FLOAT,
                order_timestamp TIMESTAMP,
                insert_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
            )
            """)
            self.conn.commit()
            
        except Exception as e:
            logger.error(f"Erreur de connexion: {str(e)}")
            raise
    
    def store_batch(self):
        """Stocke un lot de commandes dans Snowflake"""
        if not self.batch:
            return
            
        try:
            # Préparation de la requête d'insertion multiple
            values = []
            for order in self.batch:
                values.append((
                    order['order_id'],
                    order['customer_id'],
                    order['product_id'].strip('"'),
                    order['seller_id'].strip('"'),
                    order['quantity'],
                    order['price'],
                    order['timestamp']
                ))
            
            # Insertion du lot
            self.cur.executemany("""
            INSERT INTO raw_orders_stream (
                order_id, customer_id, product_id, seller_id,
                quantity, price, order_timestamp
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, values)
            
            self.conn.commit()
            logger.info(f"Lot de {len(self.batch)} commandes stocké dans Snowflake")
            self.batch = []
            
        except Exception as e:
            logger.error(f"Erreur lors du stockage du lot: {str(e)}")
            self.reconnect()  # Tentative de reconnexion en cas d'erreur
    
    def start_consuming(self):
        """Commence à consommer les messages"""
        try:
            self.consumer.subscribe(['orders'])
            last_batch_time = datetime.now()
            
            while True:
                msg = self.consumer.poll(1.0)
                
                if msg is None:
                    # Si le batch n'est pas vide et que 5 secondes se sont écoulées
                    if self.batch and (datetime.now() - last_batch_time).seconds >= 5:
                        self.store_batch()
                        last_batch_time = datetime.now()
                    continue
                    
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    else:
                        logger.error(f'Erreur Kafka: {msg.error()}')
                        continue
                
                order = json.loads(msg.value().decode('utf-8'))
                logger.info(f"Message reçu: {order}")
                self.batch.append(order)
                
                # Si le batch atteint la taille maximale
                if len(self.batch) >= self.batch_size:
                    self.store_batch()
                    last_batch_time = datetime.now()
                    
        except KeyboardInterrupt:
            logger.info("Arrêt du consommateur...")
        finally:
            if self.batch:  # Stocker les dernières commandes
                self.store_batch()
            if self.conn:
                self.conn.close()
            self.consumer.close()

if __name__ == "__main__":
    consumer = OrderConsumer()
    consumer.start_consuming()