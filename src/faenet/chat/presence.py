import os

import redis

_redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
_redis = redis.Redis.from_url(_redis_url, decode_responses=True)


def _key(slug: str) -> str:
    return f"presence:{slug}"


def user_joined(slug: str, username: str, channel_name: str) -> list[str]:
    """Track a connection joining a room. Keyed by channel_name for accuracy.

    Each WebSocket connection gets its own entry (field=channel_name,
    value=username). This handles multi-tab correctly and avoids count
    drift from container restarts where disconnect() never fires.
    """
    _redis.hset(_key(slug), channel_name, username)
    return get_online_users(slug)


def user_left(slug: str, channel_name: str) -> list[str]:
    """Remove a specific connection from a room's presence."""
    _redis.hdel(_key(slug), channel_name)
    return get_online_users(slug)


def get_online_users(slug: str) -> list[str]:
    """Return sorted list of unique usernames currently online in a room."""
    usernames = _redis.hvals(_key(slug))
    return sorted(set(usernames))


def should_announce(slug: str, username: str, action: str, cooldown: int = 120) -> bool:
    """Return True if this join/leave announcement should be broadcast.

    Uses a Redis key with TTL to suppress duplicate announcements for the
    same user+action within the cooldown period.
    """
    key = f"announce:{slug}:{username}:{action}"
    # SET NX returns True only if the key didn't exist (first announcement)
    return bool(_redis.set(key, "1", nx=True, ex=cooldown))


def flush_all_presence() -> None:
    """Clear all presence data. Called on server startup to remove stale
    entries from previous process that exited without clean disconnects."""
    cursor = 0
    while True:
        cursor, keys = _redis.scan(cursor, match="presence:*", count=100)
        if keys:
            _redis.delete(*keys)
        if cursor == 0:
            break
