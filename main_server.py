"""
Hello Zombie Main Server - FastAPI Dispatcher
Connects Extension to Ollama LLM with proper validation and security
"""

import os
import json
import logging
import sqlite3
import yaml
import hashlib
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
from functools import lru_cache
import threading

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import httpx
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('main_server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load agent configuration
CONFIG_PATH = Path("Extension/agent_config/hello_zombie.yaml")
try:
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    logger.info(f"Loaded agent config: {config['agent']['name']}")
except Exception as e:
    logger.error(f"Failed to load config: {e}")
    config = {}

# Load ZombieCoder meta memory
META_MEMORY_PATH = Path("config/agents/zombiecoder_meta.json")
try:
    with open(META_MEMORY_PATH, 'r', encoding='utf-8') as f:
        zombiecoder_meta = json.load(f)
    logger.info(f"Loaded ZombieCoder meta memory: {zombiecoder_meta['agent_name']}")
except Exception as e:
    logger.error(f"Failed to load meta memory: {e}")
    zombiecoder_meta = {}

# Pydantic models for request/response validation
class ChatRequest(BaseModel):
    agent: str = Field(..., description="Agent identifier")
    input: str = Field(..., min_length=1, max_length=10000, description="User input")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")

class ChatResponse(BaseModel):
    id: str
    author: str
    text: str
    timestamp: str
    model: str
    success: bool

# OpenAI API compatible models
class OpenAIMessage(BaseModel):
    role: str = Field(..., description="Message role (user, assistant, system)")
    content: str = Field(..., description="Message content")

class OpenAICompletionRequest(BaseModel):
    model: str = Field(..., description="Model name")
    messages: List[OpenAIMessage] = Field(..., description="List of messages")
    temperature: Optional[float] = Field(default=0.7, description="Temperature for generation")
    max_tokens: Optional[int] = Field(default=1000, description="Maximum tokens to generate")
    stream: Optional[bool] = Field(default=False, description="Stream response")

class OpenAIChoice(BaseModel):
    index: int
    message: OpenAIMessage
    finish_reason: str

class OpenAIUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

class OpenAICompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[OpenAIChoice]
    usage: OpenAIUsage

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    ollama_status: str
    memory_status: str

class ModelInfo(BaseModel):
    name: str
    size: int
    modified_at: str

# Initialize FastAPI app
app = FastAPI(
    title="Hello Zombie Main Server",
    description="FastAPI dispatcher for Hello Zombie Extension",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for local development
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Global variables
OLLAMA_HOST = config.get('infrastructure', {}).get('ollama', {}).get('host', 'http://localhost:11434')
OLLAMA_MODEL = config.get('infrastructure', {}).get('ollama', {}).get('model_name', 'gemma:2b')
MEMORY_PATH = config.get('infrastructure', {}).get('memory', {}).get('location', 'data/memory/hello_zombie_memory.sqlite')

# Performance optimization variables
response_cache = {}
cache_lock = threading.Lock()
CACHE_TTL = 3600  # 1 hour cache TTL
MAX_CACHE_SIZE = 1000  # Maximum cached responses

# Connection pooling
db_connections = {}
db_lock = threading.Lock()
MAX_DB_CONNECTIONS = 10

# System prompt generation with meta memory
def generate_system_prompt() -> str:
    """Generate optimized system prompt with ZombieCoder meta memory injection"""
    if not zombiecoder_meta:
        return "You are Hello Zombie, a local AI assistant."
    
    # Optimized system prompt (shorter to avoid timeout)
    system_prompt = f"""তুমি হচ্ছো {zombiecoder_meta.get('agent_name', 'ZombieCoder')} AI Agent।
Tagline: {zombiecoder_meta.get('tagline', 'যেখানে কোড ও কথা বলে')}

Owner: {zombiecoder_meta.get('owner', 'Sahon Srabon')}
Company: {zombiecoder_meta.get('company', 'Developer Zone')}
Contact: {zombiecoder_meta.get('contact', '+880 1323-626282')}

Core Rules:
- {zombiecoder_meta.get('core_rules', {}).get('prefix', 'ভাইয়া')} prefix ব্যবহার করো
- {zombiecoder_meta.get('core_rules', {}).get('tone', 'বন্ধুসুলভ, সত্যবাদী')} tone বজায় রাখো
- ইন্ডাস্ট্রি best practice অনুসরণ করো
- Laravel, Node.js, Next.js, Python সহ যেকোন ভাষায় কোডিং সহায়তা দাও
- কাজের আগে logic ব্যাখ্যা করো
- কাজ শেষে terminal/browser logs থেকে verification দাও
- সত্য ছাড়া আর কিছু বলবে না
- কোনো demo/test ফাইল তৈরি করবে না
- লোকাল সার্ভার চালানোর পর লগ ফাইল অবশ্যই চেক করবে

Skills: {', '.join(zombiecoder_meta.get('core_rules', {}).get('skills', [])[:10])}"""
    return system_prompt.strip()

# Caching functions
def get_cache_key(prompt: str, model: str) -> str:
    """Generate cache key for prompt and model"""
    return hashlib.md5(f"{prompt}_{model}".encode()).hexdigest()

def get_cached_response(cache_key: str) -> Optional[Dict]:
    """Get cached response if available and not expired"""
    with cache_lock:
        if cache_key in response_cache:
            cached_data = response_cache[cache_key]
            if time.time() - cached_data['timestamp'] < CACHE_TTL:
                logger.info(f"Cache hit for key: {cache_key[:8]}...")
                return cached_data['response']
            else:
                # Remove expired cache
                del response_cache[cache_key]
                logger.info(f"Cache expired for key: {cache_key[:8]}...")
    return None

def set_cached_response(cache_key: str, response: Dict):
    """Cache response with TTL"""
    with cache_lock:
        # Clean up old cache if size limit reached
        if len(response_cache) >= MAX_CACHE_SIZE:
            # Remove oldest 20% of cache
            sorted_items = sorted(response_cache.items(), key=lambda x: x[1]['timestamp'])
            for key, _ in sorted_items[:MAX_CACHE_SIZE // 5]:
                del response_cache[key]
        
        response_cache[cache_key] = {
            'response': response,
            'timestamp': time.time()
        }
        logger.info(f"Cached response for key: {cache_key[:8]}...")

# Database connection pooling
def get_db_connection():
    """Get database connection from pool"""
    thread_id = threading.get_ident()
    with db_lock:
        if thread_id not in db_connections:
            if len(db_connections) < MAX_DB_CONNECTIONS:
                conn = sqlite3.connect(MEMORY_PATH, check_same_thread=False)
                conn.row_factory = sqlite3.Row
                db_connections[thread_id] = conn
                logger.info(f"Created new DB connection for thread {thread_id}")
            else:
                # Reuse existing connection
                conn = list(db_connections.values())[0]
        else:
            conn = db_connections[thread_id]
    return conn

def cleanup_old_conversations():
    """Clean up conversations older than 30 days"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Delete conversations older than 30 days
        cutoff_date = (datetime.now() - timedelta(days=30)).isoformat()
        cursor.execute('''
            DELETE FROM conversations 
            WHERE timestamp < ?
        ''', (cutoff_date,))
        
        deleted_count = cursor.rowcount
        conn.commit()
        
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old conversations")
        
        return deleted_count
    except Exception as e:
        logger.error(f"Failed to cleanup old conversations: {e}")
        return 0

# Initialize memory database
def init_memory_db():
    """Initialize SQLite database for conversation memory"""
    try:
        os.makedirs(os.path.dirname(MEMORY_PATH), exist_ok=True)
        conn = sqlite3.connect(MEMORY_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                agent TEXT NOT NULL,
                user_input TEXT NOT NULL,
                ai_response TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                model TEXT NOT NULL,
                context TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info(f"Memory database initialized at {MEMORY_PATH}")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize memory database: {e}")
        return False

# Memory functions
def save_conversation(conversation_id: str, agent: str, user_input: str, 
                     ai_response: str, model: str, context: Optional[Dict] = None):
    """Save conversation to memory database using connection pooling"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO conversations (id, agent, user_input, ai_response, timestamp, model, context)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (conversation_id, agent, user_input, ai_response, 
              datetime.now().isoformat(), model, json.dumps(context) if context else None))
        
        conn.commit()
        logger.info(f"Conversation saved: {conversation_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to save conversation: {e}")
        return False

def get_conversation_history(agent: str, limit: int = 10) -> List[Dict]:
    """Retrieve conversation history for an agent using connection pooling"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, user_input, ai_response, timestamp, model, context
            FROM conversations 
            WHERE agent = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', (agent, limit))
        
        rows = cursor.fetchall()
        
        history = []
        for row in rows:
            history.append({
                'id': row[0],
                'user_input': row[1],
                'ai_response': row[2],
                'timestamp': row[3],
                'model': row[4],
                'context': json.loads(row[5]) if row[5] else None
            })
        
        return history
    except Exception as e:
        logger.error(f"Failed to retrieve conversation history: {e}")
        return []

# Ollama integration
async def call_ollama(prompt: str, model: str = OLLAMA_MODEL) -> Dict[str, Any]:
    """Call Ollama API with proper error handling and meta memory injection"""
    try:
        # Generate system prompt with meta memory
        system_prompt = generate_system_prompt()
        
        # Combine system prompt with user prompt
        full_prompt = f"{system_prompt}\n\nUser: {prompt}\n\nAssistant:"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            payload = {
                "model": model,
                "prompt": full_prompt,
                "stream": False
            }
            
            response = await client.post(
                f"{OLLAMA_HOST}/api/generate",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Ollama API error: {response.status_code} - {response.text}")
                return {"error": f"Ollama API error: {response.status_code}"}
                
    except httpx.TimeoutException:
        logger.error("Ollama API timeout")
        return {"error": "Ollama API timeout"}
    except Exception as e:
        logger.error(f"Ollama API exception: {e}")
        return {"error": str(e)}

async def check_ollama_health() -> bool:
    """Check if Ollama server is healthy"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{OLLAMA_HOST}/api/tags")
            return response.status_code == 200
    except Exception as e:
        logger.error(f"Ollama health check failed: {e}")
        return False

# API Endpoints
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    ollama_healthy = await check_ollama_health()
    memory_healthy = os.path.exists(MEMORY_PATH)
    
    return HealthResponse(
        status="healthy" if ollama_healthy and memory_healthy else "unhealthy",
        timestamp=datetime.now().isoformat(),
        ollama_status="healthy" if ollama_healthy else "unhealthy",
        memory_status="healthy" if memory_healthy else "unhealthy"
    )

@app.get("/models")
async def get_models():
    """Get available models from Ollama"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{OLLAMA_HOST}/api/tags")
            if response.status_code == 200:
                data = response.json()
                models = []
                for model in data.get('models', []):
                    models.append(ModelInfo(
                        name=model['name'],
                        size=model['size'],
                        modified_at=model['modified_at']
                    ))
                return {"models": models}
            else:
                raise HTTPException(status_code=500, detail="Failed to fetch models")
    except Exception as e:
        logger.error(f"Failed to get models: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Main chat endpoint with caching optimization"""
    try:
        # Generate conversation ID
        conversation_id = f"conv_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(request.input) % 10000}"
        
        # Prepare prompt with context
        prompt = request.input
        if request.context:
            context_str = json.dumps(request.context, indent=2)
            prompt = f"Context: {context_str}\n\nUser Input: {request.input}"
        
        # Check cache first
        cache_key = get_cache_key(prompt, OLLAMA_MODEL)
        cached_response = get_cached_response(cache_key)
        
        if cached_response:
            logger.info(f"Returning cached response for: {conversation_id}")
            return ChatResponse(
                id=conversation_id,
                author="Hello Zombie (Cached)",
                text=cached_response.get("response", "No response generated"),
                timestamp=datetime.now().isoformat(),
                model=cached_response.get("model", OLLAMA_MODEL),
                success=True
            )
        
        # Call Ollama if not cached
        logger.info(f"Processing chat request: {conversation_id}")
        start_time = time.time()
        ollama_response = await call_ollama(prompt, OLLAMA_MODEL)
        response_time = time.time() - start_time
        
        if "error" in ollama_response:
            raise HTTPException(status_code=500, detail=ollama_response["error"])
        
        # Extract response
        ai_response = ollama_response.get("response", "No response generated")
        model_used = ollama_response.get("model", OLLAMA_MODEL)
        
        # Cache the response
        set_cached_response(cache_key, ollama_response)
        
        # Save to memory
        save_conversation(
            conversation_id=conversation_id,
            agent=request.agent,
            user_input=request.input,
            ai_response=ai_response,
            model=model_used,
            context=request.context
        )
        
        logger.info(f"Response generated in {response_time:.2f}s for: {conversation_id}")
        
        # Return response
        return ChatResponse(
            id=conversation_id,
            author="Hello Zombie",
            text=ai_response,
            timestamp=datetime.now().isoformat(),
            model=model_used,
            success=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/agents/configure")
async def configure_agent():
    """Agent configuration endpoint"""
    return {
        "agent": config.get('agent', {}),
        "infrastructure": config.get('infrastructure', {}),
        "status": "configured"
    }

@app.get("/conversations/{agent_id}")
async def get_conversations(agent_id: str, limit: int = 10):
    """Get conversation history for an agent"""
    history = get_conversation_history(agent_id, limit)
    return {"conversations": history}

# OpenAI API compatible endpoints
@app.post("/v1/chat/completions", response_model=OpenAICompletionResponse)
async def openai_chat_completions(request: OpenAICompletionRequest):
    """OpenAI API compatible chat completions endpoint with caching optimization"""
    try:
        # Extract the last user message
        user_messages = [msg for msg in request.messages if msg.role == "user"]
        if not user_messages:
            raise HTTPException(status_code=400, detail="No user message found")
        
        user_input = user_messages[-1].content
        
        # Generate conversation ID
        conversation_id = f"openai_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(user_input) % 10000}"
        
        # Check cache first
        cache_key = get_cache_key(user_input, request.model)
        cached_response = get_cached_response(cache_key)
        
        if cached_response:
            logger.info(f"Returning cached OpenAI response for: {conversation_id}")
            ai_response = cached_response.get("response", "No response generated")
            model_used = cached_response.get("model", request.model)
        else:
            # Call Ollama if not cached
            logger.info(f"Processing OpenAI compatible request: {conversation_id}")
            start_time = time.time()
            ollama_response = await call_ollama(user_input, OLLAMA_MODEL)
            response_time = time.time() - start_time
            
            if "error" in ollama_response:
                raise HTTPException(status_code=500, detail=ollama_response["error"])
            
            # Extract response
            ai_response = ollama_response.get("response", "No response generated")
            model_used = ollama_response.get("model", OLLAMA_MODEL)
            
            # Cache the response
            set_cached_response(cache_key, ollama_response)
            logger.info(f"OpenAI response generated in {response_time:.2f}s for: {conversation_id}")
        
        # Save to memory
        save_conversation(
            conversation_id=conversation_id,
            agent="hello_zombie",
            user_input=user_input,
            ai_response=ai_response,
            model=model_used,
            context={"source": "openai_api", "model_requested": request.model}
        )
        
        # Create OpenAI compatible response
        response_message = OpenAIMessage(role="assistant", content=ai_response)
        choice = OpenAIChoice(
            index=0,
            message=response_message,
            finish_reason="stop"
        )
        
        # Estimate token usage (rough approximation)
        prompt_tokens = len(user_input.split()) * 1.3  # Rough estimation
        completion_tokens = len(ai_response.split()) * 1.3
        usage = OpenAIUsage(
            prompt_tokens=int(prompt_tokens),
            completion_tokens=int(completion_tokens),
            total_tokens=int(prompt_tokens + completion_tokens)
        )
        
        return OpenAICompletionResponse(
            id=conversation_id,
            created=int(datetime.now().timestamp()),
            model=request.model,
            choices=[choice],
            usage=usage
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OpenAI compatible endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/v1/models")
async def openai_models():
    """OpenAI API compatible models endpoint"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{OLLAMA_HOST}/api/tags")
            if response.status_code == 200:
                data = response.json()
                models = []
                for model in data.get('models', []):
                    models.append({
                        "id": model['name'],
                        "object": "model",
                        "created": int(datetime.now().timestamp()),
                        "owned_by": "hello-zombie"
                    })
                return {"object": "list", "data": models}
            else:
                raise HTTPException(status_code=500, detail="Failed to fetch models")
    except Exception as e:
        logger.error(f"Failed to get OpenAI compatible models: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/performance")
async def get_performance_metrics():
    """Get performance metrics and cache statistics"""
    try:
        with cache_lock:
            cache_stats = {
                "total_cached_responses": len(response_cache),
                "cache_hit_rate": "N/A",  # Would need to track hits/misses
                "max_cache_size": MAX_CACHE_SIZE,
                "cache_ttl_seconds": CACHE_TTL
            }
        
        with db_lock:
            db_stats = {
                "active_connections": len(db_connections),
                "max_connections": MAX_DB_CONNECTIONS
            }
        
        # Get database size
        db_size = 0
        if os.path.exists(MEMORY_PATH):
            db_size = os.path.getsize(MEMORY_PATH)
        
        return {
            "cache": cache_stats,
            "database": db_stats,
            "database_size_bytes": db_size,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get performance metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/cleanup")
async def cleanup_old_data():
    """Manually trigger cleanup of old conversations"""
    try:
        deleted_count = cleanup_old_conversations()
        return {
            "status": "success",
            "deleted_conversations": deleted_count,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to cleanup old data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup with optimization"""
    logger.info("Starting Hello Zombie Main Server with optimizations...")
    
    # Initialize memory database
    if init_memory_db():
        logger.info("Memory database initialized successfully")
    else:
        logger.error("Failed to initialize memory database")
    
    # Check Ollama connection
    if await check_ollama_health():
        logger.info("Ollama server is healthy")
    else:
        logger.warning("Ollama server is not responding")
    
    # Cleanup old conversations on startup
    deleted_count = cleanup_old_conversations()
    if deleted_count > 0:
        logger.info(f"Cleaned up {deleted_count} old conversations on startup")
    
    # Initialize performance monitoring
    logger.info("Performance optimizations enabled:")
    logger.info(f"  - Response caching: {MAX_CACHE_SIZE} max entries, {CACHE_TTL}s TTL")
    logger.info(f"  - Database connection pooling: {MAX_DB_CONNECTIONS} max connections")
    logger.info(f"  - Automatic cleanup: 30 days retention")

if __name__ == "__main__":
    uvicorn.run(
        "main_server:app",
        host="0.0.0.0",
        port=12346,
        reload=False,
        log_level="info"
    )
