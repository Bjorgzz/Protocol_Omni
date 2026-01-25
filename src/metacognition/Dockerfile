FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create module structure
RUN mkdir -p metacognition
COPY __init__.py engine.py gates.py metacognition/

EXPOSE 8011

CMD ["python", "-m", "metacognition.engine"]
