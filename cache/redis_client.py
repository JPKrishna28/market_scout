"""
Market Intelligence Scout — Redis Caching Layer

Enterprise-grade Redis client with:
  • Graceful degradation (cache miss ≠ failure)
  • Rate limiting (OWASP)
  • Structured logging
  • Connection pooling via singleton
"""

import json
import hashlib
import logging
from typing import Optional, Any

import redis
from app.config import settings
from observability.metrics import CACHE_OPERATIONS

logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────────────
# Singleton Connection Pool
# ────────────────────────────────────────────────────────────────────

_pool: Optional[redis.ConnectionPool] = None


def _get_pool() -> redis.ConnectionPool:
    """Lazy-initialise a shared connection pool."""
    global _pool
    if _pool is None:
        _pool = redis.ConnectionPool(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            decode_responses=True,
            max_connections=20,
            socket_connect_timeout=3,
            socket_timeout=3,
        )
    return _pool


def get_redis() -> redis.Redis:
    """Return a Redis client backed by the shared pool."""
    return redis.Redis(connection_pool=_get_pool())


# ────────────────────────────────────────────────────────────────────
# Cache Helpers
# ────────────────────────────────────────────────────────────────────

def make_cache_key(prefix: str, raw_key: str) -> str:
    """Deterministic, collision-resistant key from a human-readable prefix
    and an arbitrary string (e.g. URL, company name)."""
    digest = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:16]
    return f"mscout:{prefix}:{digest}"


def set_cache(key: str, value: Any, expire: int = settings.CACHE_EXPIRY) -> bool:
    """Serialise *value* as JSON and store with TTL.

    Returns True on success, False on failure (never raises).
    """
    try:
        conn = get_redis()
        conn.setex(key, expire, json.dumps(value, default=str))
        CACHE_OPERATIONS.labels(operation="set", status="success").inc()
        logger.debug("CACHE SET  key=%s ttl=%ds", key, expire)
        return True
    except redis.RedisError as exc:
        CACHE_OPERATIONS.labels(operation="set", status="error").inc()
        logger.warning("Redis SET failed (key=%s): %s — continuing without cache", key, exc)
        return False


def get_cache(key: str) -> Optional[Any]:
    """Retrieve and deserialise a cached value.

    Returns None on miss or error (never raises).
    """
    try:
        conn = get_redis()
        data = conn.get(key)
        if data is not None:
            CACHE_OPERATIONS.labels(operation="get", status="hit").inc()
            logger.debug("CACHE HIT  key=%s", key)
            return json.loads(data)
        CACHE_OPERATIONS.labels(operation="get", status="miss").inc()
        logger.debug("CACHE MISS key=%s", key)
        return None
    except redis.RedisError as exc:
        CACHE_OPERATIONS.labels(operation="get", status="error").inc()
        logger.warning("Redis GET failed (key=%s): %s — treating as miss", key, exc)
        return None


def delete_cache(key: str) -> bool:
    """Remove a key from cache. Returns True on success."""
    try:
        conn = get_redis()
        conn.delete(key)
        return True
    except redis.RedisError as exc:
        logger.warning("Redis DELETE failed (key=%s): %s", key, exc)
        return False


# ────────────────────────────────────────────────────────────────────
# Rate Limiting (OWASP)
# ────────────────────────────────────────────────────────────────────

def check_rate_limit(
    identifier: str,
    limit: int = 10,
    window_seconds: int = 60,
) -> bool:
    """Sliding-window rate limiter.

    Returns True if the request is ALLOWED, False if rate-limited.
    On Redis failure, defaults to ALLOWED (fail-open).
    """
    key = f"mscout:rate:{identifier}"
    try:
        conn = get_redis()
        current = conn.get(key)
        if current is not None and int(current) >= limit:
            logger.warning("RATE LIMIT exceeded for %s (%s/%s in %ds)",
                           identifier, current, limit, window_seconds)
            return False

        pipe = conn.pipeline()
        pipe.incr(key)
        pipe.expire(key, window_seconds)
        pipe.execute()
        return True
    except redis.RedisError as exc:
        logger.warning("Rate-limit check failed: %s — defaulting to ALLOW", exc)
        return True


# ────────────────────────────────────────────────────────────────────
# Audit Logging (Redis Lists)
# ────────────────────────────────────────────────────────────────────

def append_audit_log(log_key: str, entry: dict, max_entries: int = 500) -> bool:
    """Append an audit entry (dict) to a Redis list, capping at *max_entries*.

    Used by the Date Validation node to record discarded URLs.
    """
    try:
        conn = get_redis()
        conn.rpush(log_key, json.dumps(entry, default=str))
        conn.ltrim(log_key, -max_entries, -1)  # Keep only the latest N
        return True
    except redis.RedisError as exc:
        logger.warning("Audit log append failed (key=%s): %s", log_key, exc)
        return False


def get_audit_log(log_key: str, start: int = 0, end: int = -1) -> list:
    """Retrieve audit log entries."""
    try:
        conn = get_redis()
        raw = conn.lrange(log_key, start, end)
        return [json.loads(r) for r in raw]
    except redis.RedisError as exc:
        logger.warning("Audit log read failed (key=%s): %s", log_key, exc)
        return []