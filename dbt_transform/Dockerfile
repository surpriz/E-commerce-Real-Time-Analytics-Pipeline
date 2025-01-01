FROM python:3.9-slim

WORKDIR /usr/app

# Installation des dépendances
RUN apt-get update && \
    apt-get install -y git && \
    pip install dbt-snowflake

# Copie des fichiers du projet
COPY . .

# Commande par défaut
ENTRYPOINT ["dbt"]