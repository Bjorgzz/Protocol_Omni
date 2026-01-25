"""Mem0 REST API Server for Protocol OMNI v16.2."""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from mem0 import Memory

memory = None

config = {
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "host": os.getenv("QDRANT_HOST", "localhost"),
            "port": int(os.getenv("QDRANT_PORT", "6333")),
            "embedding_model_dims": 384,
        }
    },
    "embedder": {
        "provider": "huggingface",
        "config": {
            "model": "sentence-transformers/all-MiniLM-L6-v2",
        }
    },
    "llm": {
        "provider": "openai",
        "config": {
            "api_key": os.getenv("LLM_API_KEY", "sk-local"),
            "openai_base_url": os.getenv("LLM_BASE_URL", "http://localhost:8000/v1"),
            "model": os.getenv("LLM_MODEL", "deepseek-v3.2"),
        }
    },
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    global memory
    memory = Memory.from_config(config)
    yield

app = FastAPI(title="Mem0 Memory Server", version="1.0.0", lifespan=lifespan)

@app.get("/health")
async def health():
    return {"status": "ok", "vector_store": "qdrant"}

class AddRequest(BaseModel):
    messages: List[Dict[str, str]]
    user_id: str
    metadata: Optional[Dict[str, Any]] = None

class SearchRequest(BaseModel):
    query: str
    user_id: str
    limit: Optional[int] = 10

# v16.2.4: Routes use /v1 prefix to match client expectations
@app.post("/v1/memories/")
@app.post("/v1/memories")
@app.post("/memories")
async def add_memory(request: AddRequest):
    try:
        result = memory.add(request.messages, user_id=request.user_id, metadata=request.metadata)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/memories/search/")
@app.post("/v1/memories/search")
@app.post("/memories/search")
async def search_memory(request: SearchRequest):
    try:
        results = memory.search(request.query, user_id=request.user_id, limit=request.limit)
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/v1/memories/")
@app.get("/v1/memories")
async def get_all_memories_v1(user_id: str):
    try:
        results = memory.get_all(user_id=user_id)
        return {"memories": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/memories/{user_id}")
async def get_all_memories(user_id: str):
    try:
        results = memory.get_all(user_id=user_id)
        return {"memories": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/v1/memories/{memory_id}/")
@app.get("/v1/memories/{memory_id}")
async def get_memory(memory_id: str):
    try:
        result = memory.get(memory_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/v1/memories/{memory_id}/")
@app.delete("/v1/memories/{memory_id}")
@app.delete("/memories/{memory_id}")
async def delete_memory(memory_id: str):
    try:
        memory.delete(memory_id)
        return {"status": "deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
