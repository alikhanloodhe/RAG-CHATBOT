import unittest

from app.services.cache import CacheService


class CacheTests(unittest.TestCase):
    def test_memory_cache_round_trip(self):
        cache = CacheService.__new__(CacheService)
        cache.client = None
        cache.backend = "memory"
        cache._memory_cache = {}

        cache.set("key", "value", expire_seconds=60)

        self.assertEqual(cache.get("key"), "value")
        self.assertTrue(cache.ping())


if __name__ == "__main__":
    unittest.main()
