FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    fastapi>=0.115.0 \
    uvicorn>=0.32.0 \
    httpx>=0.27.0 \
    pydantic>=2.10.0 \
    pyyaml>=6.0.0 \
    prometheus-client>=0.21.0 \
    opentelemetry-api>=1.22.0 \
    opentelemetry-sdk>=1.22.0

COPY . /app/

RUN addgroup --gid 1000 mcp && \
    adduser --disabled-password --uid 1000 --gid 1000 mcp

USER mcp

EXPOSE 8070

CMD ["python", "-m", "uvicorn", "gateway:app", "--host", "0.0.0.0", "--port", "8070"]
