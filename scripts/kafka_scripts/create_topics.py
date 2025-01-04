from confluent_kafka.admin import AdminClient, NewTopic
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_topics():
    # Configuration du client admin
    admin_client = AdminClient({
        'bootstrap.servers': 'localhost:9092'
    })
    
    # Définition des topics à créer
    topics = [
        NewTopic(
            "orders",
            num_partitions=3,
            replication_factor=1
        )
    ]
    
    # Création des topics
    fs = admin_client.create_topics(topics)
    
    # Attente de la création des topics
    for topic, f in fs.items():
        try:
            f.result()  # Le résultat lève une exception en cas d'erreur
            logger.info(f"Topic {topic} créé avec succès")
        except Exception as e:
            if "TopicExistsError" in str(e):
                logger.info(f"Le topic {topic} existe déjà")
            else:
                logger.error(f"Erreur lors de la création du topic {topic}: {str(e)}")

if __name__ == "__main__":
    create_topics()