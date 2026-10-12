from cachetools import TTLCache


class EventsCache:
    def __init__(self):
        self._cache = TTLCache(maxsize=1000, ttl=30)

    def get(self, key):
        return self._cache.get(key)

    def set(self, key, value):
        self._cache[key] = value

    def delete(self, key):
        if key in self._cache:
            del self._cache[key]

    def clear(self):
        self._cache.clear()
