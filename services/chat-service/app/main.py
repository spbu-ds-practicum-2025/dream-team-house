"""
Chat Service - Agent coordination service
FastAPI application with Redis Streams
"""
import os
import json
import logging
from typing import List, Optional
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
import redis.asyncio as redis

from app.redis_client import get_redis, close_redis
from app.schemas import (
    ChatMessageRequest,
    ChatMessageResponse,
    ChatMessage,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

STREAM_NAME = "chat:messages"
MAX_MESSAGES = 1000


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info("Chat Service starting")
    redis_client = await get_redis()
    logger.info(f"Connected to Redis: {os.getenv('REDIS_URL', 'redis://localhost:6379')}")
    
    yield
    
    # Shutdown
    logger.info("Chat Service shutting down")
    await close_redis()


app = FastAPI(
    title="Chat Service",
    description="Agent coordination service",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        redis_client = await get_redis()
        await redis_client.ping()
        return {"status": "healthy"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Redis connection failed")


@app.post("/api/chat/messages", response_model=ChatMessageResponse)
async def post_message(
    request: ChatMessageRequest,
    redis_client: redis.Redis = Depends(get_redis)
):
    """
    Post a message to chat using Redis Streams
    Automatically limits to 1000 most recent messages
    """
    try:
        # Prepare message data
        message_data = {
            "agent_id": request.agent_id,
            "message": request.message,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        # Add structured entities if present
        if request.intent:
            message_data["intent"] = request.intent.model_dump_json()
        
        if request.comment:
            message_data["comment"] = request.comment.model_dump_json()
        
        # Add message to Redis Stream with MAXLEN limit
        # The ~ makes MAXLEN approximate for better performance
        message_id = await redis_client.xadd(
            STREAM_NAME,
            message_data,
            maxlen=MAX_MESSAGES,
            approximate=True,
        )
        
        logger.info(f"Message posted by {request.agent_id}: {message_id}")
        
        return ChatMessageResponse(
            message_id=message_id,
            timestamp=message_data["timestamp"],
        )
    
    except Exception as e:
        logger.error(f"Error posting message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/chat/messages", response_model=List[ChatMessage])
async def get_messages(
    since: Optional[str] = None,
    limit: int = 100,
    redis_client: redis.Redis = Depends(get_redis)
):
    """
    Get chat messages since timestamp
    Uses Redis XRANGE to retrieve messages
    """
    try:
        # Determine start ID
        if since:
            # Convert ISO timestamp to message ID
            # Redis Stream IDs are in format: timestamp-sequence
            # We convert ISO timestamp to milliseconds
            try:
                dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
                timestamp_ms = int(dt.timestamp() * 1000)
                start_id = f"{timestamp_ms}-0"
            except (ValueError, AttributeError):
                # If can't parse, treat as message ID
                start_id = since
        else:
            # Get all messages
            start_id = "-"
        
        # Get messages from Redis Stream
        messages = await redis_client.xrange(
            STREAM_NAME,
            min=start_id,
            max="+",
            count=limit,
        )
        
        # Parse messages
        result = []
        for msg_id, msg_data in messages:
            # Parse structured entities
            intent = None
            comment = None
            
            if "intent" in msg_data:
                try:
                    intent = json.loads(msg_data["intent"])
                except (json.JSONDecodeError, KeyError):
                    pass
            
            if "comment" in msg_data:
                try:
                    comment = json.loads(msg_data["comment"])
                except (json.JSONDecodeError, KeyError):
                    pass
            
            result.append(ChatMessage(
                message_id=msg_id,
                agent_id=msg_data.get("agent_id", "unknown"),
                message=msg_data.get("message", ""),
                timestamp=msg_data.get("timestamp", ""),
                intent=intent,
                comment=comment,
            ))
        
        logger.info(f"Retrieved {len(result)} messages (since={since}, limit={limit})")
        
        return result
    
    except Exception as e:
        logger.error(f"Error retrieving messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))
