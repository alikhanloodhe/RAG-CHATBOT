import unittest
from unittest.mock import patch

from app.services import query_cache


class FakeCache:
    def __init__(self):
        self.values = {}

    def get(self, key):
        return self.values.get(key)

    def set(self, key, value, expire_seconds=3600):
        self.values[key] = value


class QueryCacheTests(unittest.TestCase):
    def test_cache_key_normalizes_query_and_scopes_to_user(self):
        fake_cache = FakeCache()

        with patch.object(query_cache, "cache_service", fake_cache):
            key_one = query_cache.build_query_cache_key(1, " What   Is RAG? ")
            key_two = query_cache.build_query_cache_key(1, "what is rag?")
            other_user_key = query_cache.build_query_cache_key(2, "what is rag?")

        self.assertEqual(key_one, key_two)
        self.assertNotEqual(key_one, other_user_key)

    def test_cache_namespace_changes_after_invalidation(self):
        fake_cache = FakeCache()

        with patch.object(query_cache, "cache_service", fake_cache):
            key_before = query_cache.build_query_cache_key(1, "what is rag?")
            query_cache.invalidate_user_query_cache(1)
            key_after = query_cache.build_query_cache_key(1, "what is rag?")

        self.assertNotEqual(key_before, key_after)


if __name__ == "__main__":
    unittest.main()
