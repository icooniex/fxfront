"""
Redis Client for FX Trading Application

Handles:
- Bot heartbeat storage with TTL
- Trade event streaming
- Real-time data caching

Usage:
    from trading.redis_client import redis_client, set_bot_heartbeat, get_bot_heartbeat
"""

import redis
from django.conf import settings
from typing import Optional, Dict, Any, List
import json
import logging

logger = logging.getLogger(__name__)

# Initialize Redis client
try:
    redis_client = redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_keepalive=True,
        health_check_interval=30
    )
    redis_client.ping()
    logger.info("Redis connection established successfully")
except Exception as e:
    logger.error(f"Failed to connect to Redis: {e}")
    redis_client = None


# ============================================
# Bot Heartbeat Functions
# ============================================

def set_bot_heartbeat(account_id: int, status: Dict[str, Any], ttl: int = 60) -> bool:
    """
    Store bot heartbeat in Redis with TTL.
    
    Args:
        account_id: User trade account ID
        status: Dict containing bot status (e.g., {"status": "running", "timestamp": "...", "trades_count": 5})
        ttl: Time to live in seconds (default 60s)
    
    Returns:
        True if successful, False otherwise
    """
    if not redis_client:
        return False
    
    try:
        key = f"bot:heartbeat:{account_id}"
        redis_client.setex(key, ttl, json.dumps(status))
        return True
    except Exception as e:
        logger.error(f"Failed to set bot heartbeat for account {account_id}: {e}")
        return False


def get_bot_heartbeat(account_id: int) -> Optional[Dict[str, Any]]:
    """
    Get bot heartbeat from Redis.
    
    Args:
        account_id: User trade account ID
    
    Returns:
        Dict with bot status or None if not found/expired
    """
    if not redis_client:
        return None
    
    try:
        key = f"bot:heartbeat:{account_id}"
        data = redis_client.get(key)
        if data:
            return json.loads(data)
        return None
    except Exception as e:
        logger.error(f"Failed to get bot heartbeat for account {account_id}: {e}")
        return None


def get_multiple_bot_heartbeats(account_ids: List[int]) -> Dict[int, Optional[Dict[str, Any]]]:
    """
    Get multiple bot heartbeats in one pipeline call (more efficient).
    
    Args:
        account_ids: List of user trade account IDs
    
    Returns:
        Dict mapping account_id -> heartbeat data (or None if not found)
    """
    if not redis_client or not account_ids:
        return {}
    
    try:
        pipe = redis_client.pipeline()
        keys = [f"bot:heartbeat:{acc_id}" for acc_id in account_ids]
        
        for key in keys:
            pipe.get(key)
        
        results = pipe.execute()
        
        heartbeats = {}
        for acc_id, data in zip(account_ids, results):
            if data:
                try:
                    heartbeats[acc_id] = json.loads(data)
                except json.JSONDecodeError:
                    heartbeats[acc_id] = None
            else:
                heartbeats[acc_id] = None
        
        return heartbeats
    except Exception as e:
        logger.error(f"Failed to get multiple bot heartbeats: {e}")
        return {}


def is_bot_alive(account_id: int) -> bool:
    """
    Check if bot is alive based on heartbeat presence.
    
    Args:
        account_id: User trade account ID
    
    Returns:
        True if heartbeat exists (bot is alive), False otherwise
    """
    return get_bot_heartbeat(account_id) is not None


# ============================================
# Trade Event Streaming Functions
# ============================================

def add_trade_event(event_type: str, data: Dict[str, Any]) -> bool:
    """
    Add trade event to Redis Stream for Celery processing.
    
    Args:
        event_type: Type of event ('create', 'update', 'close', 'batch_update')
        data: Event data dictionary
    
    Returns:
        True if successful, False otherwise
    """
    if not redis_client:
        return False
    
    try:
        stream_key = "trade:events"
        event = {
            "type": event_type,
            "data": json.dumps(data)
        }
        redis_client.xadd(stream_key, event)
        return True
    except Exception as e:
        logger.error(f"Failed to add trade event to stream: {e}")
        return False


def get_stream_length(stream_key: str = "trade:events") -> int:
    """
    Get the number of pending events in Redis Stream.
    
    Args:
        stream_key: Stream key name
    
    Returns:
        Number of events in stream
    """
    if not redis_client:
        return 0
    
    try:
        return redis_client.xlen(stream_key)
    except Exception as e:
        logger.error(f"Failed to get stream length: {e}")
        return 0


def read_trade_events(
    stream_key: str = "trade:events",
    count: int = 10,
    block: int = 5000,
    last_id: str = ">"
) -> List[tuple]:
    """
    Read trade events from Redis Stream (for Celery consumer).
    
    Args:
        stream_key: Stream key name
        count: Maximum number of events to read
        block: Block for N milliseconds if no events (0 = forever, None = non-blocking)
        last_id: Start reading from this ID (use ">" for new messages only)
    
    Returns:
        List of (message_id, data) tuples
    """
    if not redis_client:
        return []
    
    try:
        result = redis_client.xread(
            {stream_key: last_id},
            count=count,
            block=block
        )
        
        if not result:
            return []
        
        # result format: [(stream_name, [(message_id, data_dict), ...])]
        events = []
        for stream_name, messages in result:
            for message_id, data in messages:
                events.append((message_id, data))
        
        return events
    except Exception as e:
        logger.error(f"Failed to read trade events from stream: {e}")
        return []


def ack_trade_event(stream_key: str, group: str, message_id: str) -> bool:
    """
    Acknowledge processed event in Redis Stream (if using consumer groups).
    
    Args:
        stream_key: Stream key name
        group: Consumer group name
        message_id: Message ID to acknowledge
    
    Returns:
        True if successful, False otherwise
    """
    if not redis_client:
        return False
    
    try:
        redis_client.xack(stream_key, group, message_id)
        return True
    except Exception as e:
        logger.error(f"Failed to acknowledge message {message_id}: {e}")
        return False


# ============================================
# Cache Helper Functions
# ============================================

def set_cache(key: str, value: Any, ttl: int = 300) -> bool:
    """
    Set a cache value with TTL.
    
    Args:
        key: Cache key
        value: Value to cache (will be JSON serialized)
        ttl: Time to live in seconds
    
    Returns:
        True if successful, False otherwise
    """
    if not redis_client:
        return False
    
    try:
        redis_client.setex(key, ttl, json.dumps(value))
        return True
    except Exception as e:
        logger.error(f"Failed to set cache for key {key}: {e}")
        return False


def get_cache(key: str) -> Optional[Any]:
    """
    Get a cached value.
    
    Args:
        key: Cache key
    
    Returns:
        Cached value or None if not found
    """
    if not redis_client:
        return None
    
    try:
        data = redis_client.get(key)
        if data:
            return json.loads(data)
        return None
    except Exception as e:
        logger.error(f"Failed to get cache for key {key}: {e}")
        return None


def delete_cache(key: str) -> bool:
    """
    Delete a cache key.
    
    Args:
        key: Cache key
    
    Returns:
        True if successful, False otherwise
    """
    if not redis_client:
        return False
    
    try:
        redis_client.delete(key)
        return True
    except Exception as e:
        logger.error(f"Failed to delete cache for key {key}: {e}")
        return False
