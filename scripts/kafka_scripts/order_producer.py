import json
import random
from datetime import datetime
from confluent_kafka import Producer
import time
import logging
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class OrderProducer:
    def __init__(self):
        self.conf = {
            'bootstrap.servers': 'localhost:9092',
            'client.id': 'order_producer'
        }
        self.producer = Producer(self.conf)
        
        # Chemin absolu vers les fichiers de données
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        data_path = os.path.join(base_path, 'data', 'raw')
        
        logger.info(f"Lecture des données depuis: {data_path}")
        
        # Charger les données de référence
        products_path = os.path.join(data_path, 'olist_products_dataset.csv')
        sellers_path = os.path.join(data_path, 'olist_sellers_dataset.csv')
        
        with open(products_path, 'r') as f:
            self.products = [line.split(',')[0] for line in f.readlines()[1:]]
        logger.info(f"Nombre de produits chargés: {len(self.products)}")
            
        with open(sellers_path, 'r') as f:
            self.sellers = [line.split(',')[0] for line in f.readlines()[1:]]
        logger.info(f"Nombre de vendeurs chargés: {len(self.sellers)}")
    
    def delivery_report(self, err, msg):
        if err is not None:
            logger.error(f'Erreur de livraison du message: {err}')
        else:
            logger.info(f'Message livré à {msg.topic()} [{msg.partition()}] à offset {msg.offset()}')
    
    def generate_order(self):
        """Génère une commande aléatoire"""
        now = datetime.now()
        return {
            'order_id': f"ORDER_{now.strftime('%Y%m%d')}_{random.randint(1000, 9999)}",
            'customer_id': f"CUST_{random.randint(1000, 9999)}",
            'product_id': random.choice(self.products),
            'seller_id': random.choice(self.sellers),
            'quantity': random.randint(1, 5),
            'price': round(random.uniform(10.0, 500.0), 2),
            'timestamp': now.isoformat()
        }
    
    def start_producing(self, topic_name='orders', interval=5):
        """Commence à produire des messages"""
        try:
            while True:
                order = self.generate_order()
                self.producer.produce(
                    topic_name,
                    key=order['order_id'],
                    value=json.dumps(order),
                    callback=self.delivery_report
                )
                self.producer.poll(0)
                logger.info(f"Message envoyé: {order}")
                time.sleep(interval)
        except KeyboardInterrupt:
            logger.info("Arrêt du producteur...")
        finally:
            logger.info("Purge des messages en attente...")
            self.producer.flush()

if __name__ == "__main__":
    producer = OrderProducer()
    producer.start_producing()