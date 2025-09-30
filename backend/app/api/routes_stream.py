"""API routes for real-time event streaming via Server-Sent Events."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncGenerator

import redis.asyncio as aioredis
from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stream", tags=["streaming"])


async def event_stream_generator(request: Request) -> AsyncGenerator[dict, None]:
    """
    Generator function that listens to Redis pub/sub and yields events.
    
    Args:
        request: FastAPI request object (used to detect client disconnect)
        
    Yields:
        Dictionary with event data in SSE format
    """
    # Connect to Redis
    redis_client = await aioredis.from_url(
        settings.redis_url,
        decode_responses=True,
    )
    pubsub = redis_client.pubsub()
    
    try:
        # Subscribe to events channel
        await pubsub.subscribe("events")
        logger.info("Client connected to event stream")
        
        # Send initial connection message
        yield {
            "event": "connected",
            "data": json.dumps({
                "message": "Connected to event stream",
                "timestamp": asyncio.get_event_loop().time(),
            }),
        }
        
        # Listen for messages
        while True:
            # Check if client disconnected
            if await request.is_disconnected():
                logger.info("Client disconnected from event stream")
                break
            
            try:
                # Get message with timeout to allow checking for disconnect
                message = await asyncio.wait_for(
                    pubsub.get_message(ignore_subscribe_messages=True),
                    timeout=1.0,
                )
                
                if message and message["type"] == "message":
                    event_data = message["data"]
                    
                    logger.debug(f"Broadcasting event: {event_data}")
                    
                    yield {
                        "event": "new_event",
                        "data": event_data,
                    }
                    
            except asyncio.TimeoutError:
                # No message received, continue loop to check for disconnect
                continue
                
    except Exception as e:
        logger.error(f"Error in event stream: {e}")
        yield {
            "event": "error",
            "data": json.dumps({"error": str(e)}),
        }
    finally:
        # Cleanup
        await pubsub.unsubscribe("events")
        await pubsub.close()
        await redis_client.close()
        logger.info("Event stream closed")


@router.get("/events")
async def stream_events(request: Request) -> EventSourceResponse:
    """
    Stream real-time trending events to clients via Server-Sent Events (SSE).
    
    This endpoint maintains a long-lived HTTP connection and pushes events
    as they are detected by the backend workers.
    
    Events are published to Redis pub/sub channel "events" by the
    detect_events Celery task.
    
    Example usage with curl:
        curl -N http://localhost:8000/api/v1/stream/events
    
    Example usage with JavaScript:
        const eventSource = new EventSource('/api/v1/stream/events');
        eventSource.addEventListener('new_event', (e) => {
            const data = JSON.parse(e.data);
            console.log('New event:', data);
        });
    
    Returns:
        EventSourceResponse: SSE stream with events in format:
            event: new_event
            data: {"event_id": 1, "cluster_id": 3, "severity": "high", ...}
    """
    return EventSourceResponse(event_stream_generator(request))


@router.get("/health")
async def stream_health() -> dict[str, str]:
    """
    Health check endpoint for streaming service.
    
    Returns:
        Dictionary with status
    """
    return {"status": "ok", "service": "streaming"}


__all__ = ["router"]
