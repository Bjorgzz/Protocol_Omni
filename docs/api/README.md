# Inference API Reference

Protocol OMNI exposes an OpenAI-compatible API for inference.

## Base URL

```
http://192.168.3.10:8000
```

## Authentication

Local deployment uses a placeholder API key:

```
Authorization: Bearer sk-local
```

## Endpoints

### Health Check

```http
GET /health
```

**Response**:
```json
{
  "status": "healthy",
  "model": "deepseek-v3.2",
  "gpu_memory_used": "120GB",
  "uptime_seconds": 3600
}
```

### List Models

```http
GET /v1/models
```

**Response**:
```json
{
  "object": "list",
  "data": [
    {
      "id": "deepseek-v3.2",
      "object": "model",
      "created": 1234567890,
      "owned_by": "protocol-omni"
    }
  ]
}
```

### Chat Completions

```http
POST /v1/chat/completions
Content-Type: application/json
Authorization: Bearer sk-local
```

**Request Body**:
```json
{
  "model": "deepseek-v3.2",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello, how are you?"}
  ],
  "temperature": 0.7,
  "max_tokens": 2048,
  "stream": false
}
```

**Response**:
```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "deepseek-v3.2",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Hello! I'm doing well, thank you for asking."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 25,
    "completion_tokens": 15,
    "total_tokens": 40
  }
}
```

### Streaming

Set `stream: true` for Server-Sent Events:

```bash
curl -N http://192.168.3.10:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-local" \
  -d '{
    "model": "deepseek-v3.2",
    "messages": [{"role": "user", "content": "Hello"}],
    "stream": true
  }'
```

**Response Stream**:
```
data: {"id":"chatcmpl-abc123","choices":[{"delta":{"content":"Hello"}}]}

data: {"id":"chatcmpl-abc123","choices":[{"delta":{"content":"!"}}]}

data: [DONE]
```

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model` | string | required | Model ID (e.g., `deepseek-v3.2`) |
| `messages` | array | required | Conversation messages |
| `temperature` | float | 0.7 | Sampling temperature (0.0-2.0) |
| `max_tokens` | int | 2048 | Maximum tokens to generate |
| `stream` | bool | false | Enable SSE streaming |
| `top_p` | float | 1.0 | Nucleus sampling threshold |
| `presence_penalty` | float | 0.0 | Penalize repeated topics |
| `frequency_penalty` | float | 0.0 | Penalize repeated tokens |
| `stop` | array | null | Stop sequences |

## Rate Limits

Local deployment has no rate limits, but be aware of:

- **Throughput**: ~20 tokens/second (varies by context length)
- **Max Context**: 32K tokens (limited by VRAM)
- **Concurrent Requests**: 1 (model is single-threaded)

## Error Responses

### 503 Service Unavailable

Model is still loading:

```json
{
  "error": {
    "message": "Model not ready",
    "type": "service_unavailable",
    "code": 503
  }
}
```

### 500 Internal Server Error

GPU memory exhausted:

```json
{
  "error": {
    "message": "CUDA out of memory",
    "type": "internal_error",
    "code": 500
  }
}
```

## Client Examples

### Python (OpenAI SDK)

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://192.168.3.10:8000/v1",
    api_key="sk-local"
)

response = client.chat.completions.create(
    model="deepseek-v3.2",
    messages=[{"role": "user", "content": "Hello!"}]
)

print(response.choices[0].message.content)
```

### curl

```bash
curl http://192.168.3.10:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-local" \
  -d '{
    "model": "deepseek-v3.2",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

### JavaScript (fetch)

```javascript
const response = await fetch('http://192.168.3.10:8000/v1/chat/completions', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer sk-local'
  },
  body: JSON.stringify({
    model: 'deepseek-v3.2',
    messages: [{ role: 'user', content: 'Hello!' }]
  })
});

const data = await response.json();
console.log(data.choices[0].message.content);
```

## IDE Configuration

For VS Code, Cursor, or other IDEs with OpenAI integration:

| Setting | Value |
|---------|-------|
| API Base | `http://192.168.3.10:8000/v1` |
| API Key | `sk-local` |
| Model | `deepseek-v3.2` |

## Related

- [Architecture Overview](../architecture/overview.md)
- [Monitoring](../operations/monitoring.md)
- [Troubleshooting](../operations/troubleshooting.md)
