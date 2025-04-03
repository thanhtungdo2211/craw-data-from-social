FROM apache/airflow:2.10.0-python3.10

USER root

RUN apt-get update && \
    apt-get install -y \
    default-jre-headless \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    ffmpeg \
    git \  
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    # Create a directory for the cache
    && mkdir -p /home/airflow/.cache/torch \
    && chown -R airflow:0 /home/airflow/.cache \
    && chmod -R 775 /home/airflow/.cache
    
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

USER airflow
COPY ./dags/ ${AIRFLOW_HOME}/dags/