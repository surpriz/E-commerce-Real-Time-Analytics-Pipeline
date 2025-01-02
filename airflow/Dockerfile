FROM apache/airflow:2.7.1

USER root

# Installation des dépendances système
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER airflow

# Installation des packages Python nécessaires
COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt \
    && pip install --no-cache-dir dbt-snowflake