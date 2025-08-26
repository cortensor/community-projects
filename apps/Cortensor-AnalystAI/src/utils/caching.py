import time
from tinydb import TinyDB, Query
from src.config import CACHE_EXPIRATION_MINUTES

db = TinyDB('data/cache.db')
Cache = Query()

def get_cached_result(topic: str) -> str | None:
    """Retrieves a cached result if it exists and is not expired."""
    result = db.get(Cache.topic == topic.lower())
    if result:
        is_expired = (time.time() - result['timestamp']) > (CACHE_EXPIRATION_MINUTES * 60)
        if not is_expired:
            return result['data']
        else:
            db.remove(Cache.topic == topic.lower())
    return None

def set_cached_result(topic: str, data: str):
    """Saves a result to the cache."""
    db.upsert(
        {'topic': topic.lower(), 'data': data, 'timestamp': time.time()},
        Cache.topic == topic.lower()
    )

def delete_cached_result(topic: str) -> bool:
    """Deletes a specific topic from the cache. Returns True if an item was deleted."""
    removed_items = db.remove(Cache.topic == topic.lower())
    return len(removed_items) > 0

def clear_all_cache() -> int:
    """
    Deletes all entries from the cache. Returns the number of items that were deleted.
    """
    # --- THE FIX IS HERE ---
    # First, count how many items exist.
    count = len(db)
    # Then, delete them all.
    db.truncate()
    # Finally, return the count we got earlier.
    return count
