# Protocol OMNI v16.2.6 - Agent Orchestrator
# Cognitive Router with Dual Model Architecture (Concrete Bunker Doctrine)
# Build context: src/ (set in docker/omni-stack.yaml)

FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements from agent directory (build context is now src/)
COPY agent/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy both modules as proper Python packages
COPY agent/ /app/agent/
COPY memory/ /app/memory/

ENV PYTHONPATH="/app:${PYTHONPATH}"
ENV ORACLE_ENDPOINT="http://deepseek-v32:8000/v1"
ENV ORACLE_BACKUP="http://kimi-k2:8001/v1"
ENV EXECUTOR_ENDPOINT="http://qwen-executor:8002/v1"
ENV FAILSAFE_ENDPOINT="http://minimax-failsafe:8003/v1"
ENV METACOG_ENDPOINT="http://metacognition:8011"
ENV GEPA_ENDPOINT="http://gepa-engine:8010"
ENV PHOENIX_ENDPOINT="http://arize-phoenix:4317"
ENV LOG_LEVEL="INFO"

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

CMD ["uvicorn", "agent.main:app", "--host", "0.0.0.0", "--port", "8080"]
