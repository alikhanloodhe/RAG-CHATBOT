import unittest
from unittest.mock import MagicMock, patch
from app.services.rag import RAGService

class MockRecord:
    def __init__(self, record_id, payload):
        self.id = record_id
        self.payload = payload

class MockScoredPoint:
    def __init__(self, point_id, score, payload):
        self.id = point_id
        self.score = score
        self.payload = payload

class MockQueryResult:
    def __init__(self, points):
        self.points = points

class HybridSearchTests(unittest.TestCase):
    def test_hybrid_search_runs_vector_and_bm25_then_fuses_rrf(self):
        # Create a clean RAGService instance
        rag_service = RAGService()
        
        # Create mock records for scroll (BM25 corpus)
        record_1 = MockRecord(1, {"text": "Redis supports volatile-lru eviction policy", "filename": "redis.txt"})
        record_2 = MockRecord(2, {"text": "PostgreSQL database connection pool limits", "filename": "postgres.txt"})
        record_3 = MockRecord(3, {"text": "Docker container orchestration using Kubernetes", "filename": "docker.txt"})
        
        mock_client = MagicMock()
        # Mock scroll to return our 3 records in the first call, and None for next offset
        mock_client.scroll.side_effect = [
            ([record_1, record_2, record_3], None)
        ]
        
        # Mock query_points to return search results (e.g. record 3 and record 2)
        scored_point_3 = MockScoredPoint(3, 0.85, {"text": "Docker container orchestration using Kubernetes", "filename": "docker.txt"})
        scored_point_2 = MockScoredPoint(2, 0.72, {"text": "PostgreSQL database connection pool limits", "filename": "postgres.txt"})
        mock_client.query_points.return_value = MockQueryResult([scored_point_3, scored_point_2])
        
        # Set the mock client on the rag service
        rag_service._client = mock_client
        
        # Mock embedding service to return a dummy vector
        mock_embeddings = MagicMock()
        mock_embeddings.get_embedding.return_value = [0.1] * 384
        
        # Run search for a query that contains "Redis eviction"
        # Word matches: "Redis supports volatile-lru eviction policy" (record 1 has 2 exact term matches)
        with patch("app.services.embeddings.embedding_service", mock_embeddings):
            results = rag_service.search("Redis eviction", collection_name="test_collection", limit=2, user_id=1)
            
        # Verify the scroll API was called to load corpus
        mock_client.scroll.assert_called_once()
        
        # Verify the vector search was called
        mock_client.query_points.assert_called_once()
        
        # Check that results are returned and sorted by RRF
        # Record 1 matches the query terms perfectly in BM25, so it should rank high despite not being in vector hits.
        self.assertGreater(len(results), 0)
        self.assertTrue(any(item["id"] == 1 for item in results), "BM25 match (record 1) should be in the results")
        self.assertTrue(any(item["id"] == 3 for item in results), "Vector match (record 3) should be in the results")

if __name__ == "__main__":
    unittest.main()
