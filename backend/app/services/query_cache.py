import hashlib

from app.core.config import settings
from app.services.cache import cache_service

QUERY_CACHE_VERSION = "v2"


def normalize_query(query: str) -> str:
    """Normalizes the search query by trimming, lowercasing, and collapses whitespaces.

    Args:
        query: The raw search string.

    Returns:
        The normalized query string.
    """
    return " ".join(query.strip().lower().split())


def user_cache_namespace_key(user_id: int) -> str:
    """Derives the Redis lookup key for the user's query cache namespace indicator.

    Args:
        user_id: The ID of the authenticated user.

    Returns:
        A string key representation.
    """
    return f"rag:query:{QUERY_CACHE_VERSION}:user:{user_id}:namespace"


def get_user_cache_namespace(user_id: int) -> str:
    """Fetches the current cache namespace counter for the user.

    Args:
        user_id: The ID of the authenticated user.

    Returns:
        The namespace count as a string, defaults to "0" if missing.
    """
    return cache_service.get(user_cache_namespace_key(user_id)) or "0"


def invalidate_user_query_cache(user_id: int) -> None:
    """Invalidates the query cache for a user by incrementing their namespace counter.

    This ensures all old query caches become immediately unreachable (evicted logically).

    Args:
        user_id: The ID of the authenticated user whose cache is invalidated.
    """
    namespace_key = user_cache_namespace_key(user_id)
    try:
        current_namespace = int(cache_service.get(namespace_key) or "0")
    except ValueError:
        current_namespace = 0
    cache_service.set(namespace_key, str(current_namespace + 1), expire_seconds=settings.QUERY_CACHE_TTL_SECONDS)


def build_query_cache_key(user_id: int, query: str) -> str:
    """Assembles a cache key for a given user query.

    Key is derived from the user ID, current namespace counter, and a SHA256
    hash of the normalized query string.

    Args:
        user_id: The ID of the authenticated user.
        query: The raw query string.

    Returns:
        A unique query cache key string.
    """
    normalized_query = normalize_query(query)
    query_digest = hashlib.sha256(normalized_query.encode("utf-8")).hexdigest()
    namespace = get_user_cache_namespace(user_id)
    return f"rag:query:{QUERY_CACHE_VERSION}:user:{user_id}:ns:{namespace}:sha256:{query_digest}"
