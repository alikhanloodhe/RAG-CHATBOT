import logging

from qdrant_client import QdrantClient
from app.core.config import settings

logger = logging.getLogger(__name__)

class RAGService:
    """Service handling interactions with the Qdrant vector database and hybrid search logic."""

    def __init__(self):
        """Initializes RAGService by setting client state placeholder."""
        self._client = None

    @property
    def client(self) -> QdrantClient:
        """Retrieves or instantiates the Qdrant client connection (lazy loaded).

        In production, tests settings.QDRANT_HOST. In local environments, falls back
        to local disk-based persistence storage at `./qdrant_local_data`.

        Returns:
            An active QdrantClient instance.
        """
        if self._client is None:
            # Check if live Qdrant host is defined, and test connection.
            if settings.QDRANT_HOST:
                try:
                    self._client = QdrantClient(
                        host=settings.QDRANT_HOST,
                        port=settings.QDRANT_PORT,
                        api_key=settings.QDRANT_API_KEY,
                        timeout=2.0  # Fast timeout for testing
                    )
                    self._client.get_collections()
                    logger.info(
                        "Connected to Qdrant",
                        extra={"host": settings.QDRANT_HOST, "port": settings.QDRANT_PORT},
                    )
                    return self._client
                except Exception as e:
                    if settings.is_production:
                        raise RuntimeError("Qdrant is required when APP_ENV=production") from e

                    logger.warning(
                        "Qdrant unavailable; using development fallback",
                        extra={
                            "host": settings.QDRANT_HOST,
                            "port": settings.QDRANT_PORT,
                            "error": e.__class__.__name__,
                        },
                    )

            # Fallback to local disk-based client for persistence in local dev environment
            if settings.is_production:
                raise RuntimeError("QDRANT_HOST must be configured when APP_ENV=production")

            logger.info("Initializing local persistent Qdrant client", extra={"path": "./qdrant_local_data"})
            self._client = QdrantClient(path="./qdrant_local_data")
        return self._client


    def ensure_collection(self, collection_name: str, size: int = 384):
        """Ensures that a Qdrant collection with the given name exists.

        If the collection does not exist, creates it configures with Cosine distance.

        Args:
            collection_name: The name of the vector collection.
            size: Dimension of the vectors (defaults to 384 for bge-small).
        """
        from qdrant_client.models import Distance, VectorParams
        try:
            self.client.get_collection(collection_name)
        except Exception:
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=size, distance=Distance.COSINE)
            )

    def upsert_vectors(self, collection_name: str, ids: list, vectors: list[list[float]], payloads: list[dict]):
        """Upserts a set of vectors and their metadata payloads into a Qdrant collection.

        Args:
            collection_name: Name of the vector collection.
            ids: List of unique UUIDs/strings for each vector.
            vectors: List of float lists representing vector embeddings.
            payloads: List of dicts representing metadata payloads matching each vector.
        """
        from qdrant_client.models import PointStruct
        self.ensure_collection(collection_name)
        points = [
            PointStruct(id=ids[i], vector=vectors[i], payload=payloads[i])
            for i in range(len(ids))
        ]
        self.client.upsert(
            collection_name=collection_name,
            points=points
        )

    def search(self, query: str, collection_name: str, limit: int = 5, user_id: int = None):
        """Performs a hybrid search combining dense vector similarity and local BM25 scoring.

        Uses Reciprocal Rank Fusion (RRF) to merge the top 20 dense and top 20 sparse
        results, returning the top 'limit' elements.

        Args:
            query: The search query string.
            collection_name: Qdrant collection name to search.
            limit: The maximum number of search results to return.
            user_id: The ID of the user querying, enforcing multi-tenant isolation.

        Returns:
            A list of dicts, each containing:
                - id: The chunk ID.
                - score: The merged RRF rank score.
                - payload: The document metadata (including filename, text content).
        """
        from app.services.embeddings import embedding_service
        try:
            query_vector = embedding_service.get_embedding(query)
            self.ensure_collection(collection_name)
            
            query_filter = None
            if user_id is not None:
                from qdrant_client.models import Filter, FieldCondition, MatchValue
                query_filter = Filter(
                    must=[
                        FieldCondition(
                            key="user_id",
                            match=MatchValue(value=user_id)
                        )
                    ]
                )

            # 1. Retrieve all points matching user_id to run BM25 locally
            all_points = []
            offset = None
            while True:
                scroll_result = self.client.scroll(
                    collection_name=collection_name,
                    scroll_filter=query_filter,
                    limit=100,
                    offset=offset,
                    with_payload=True,
                    with_vectors=False
                )
                records, offset = scroll_result
                all_points.extend(records)
                if offset is None:
                    break

            if not all_points:
                return []

            # 2. Run Dense vector search (get top 20 candidates)
            vector_hits = self.client.query_points(
                collection_name=collection_name,
                query=query_vector,
                query_filter=query_filter,
                limit=20
            ).points

            # 3. Run BM25 search (get top 20 candidates)
            import re
            from rank_bm25 import BM25Okapi

            def tokenize(text: str) -> list[str]:
                cleaned = re.sub(r'[^\w\s]', '', text.lower())
                return cleaned.split()

            point_map = {record.id: record for record in all_points}
            corpus = [tokenize(record.payload.get("text", "") if record.payload else "") for record in all_points]
            
            bm25 = BM25Okapi(corpus)
            query_tokens = tokenize(query)
            bm25_scores = bm25.get_scores(query_tokens)

            bm25_ranked = [(record.id, bm25_scores[i]) for i, record in enumerate(all_points) if bm25_scores[i] > 0]
            bm25_ranked.sort(key=lambda x: x[1], reverse=True)
            bm25_top_20 = bm25_ranked[:20]

            # 4. Perform Reciprocal Rank Fusion (RRF) reranking
            rrf_scores = {}
            k = 60

            # Add Vector search ranks
            for rank, hit in enumerate(vector_hits):
                rrf_scores[hit.id] = rrf_scores.get(hit.id, 0.0) + 1.0 / (k + (rank + 1))

            # Add BM25 search ranks
            for rank, (doc_id, score) in enumerate(bm25_top_20):
                rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + 1.0 / (k + (rank + 1))

            # Sort and select top candidates
            sorted_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)

            results_list = []
            for doc_id in sorted_ids[:limit]:
                point = point_map.get(doc_id)
                if not point:
                    # Fallback lookup in vector search results
                    for h in vector_hits:
                        if h.id == doc_id:
                            point = h
                            break
                if point:
                    results_list.append({
                        "id": doc_id,
                        "score": rrf_scores[doc_id],
                        "payload": point.payload
                    })
            return results_list

        except Exception as e:
            if settings.is_production:
                raise

            logger.exception("Qdrant search failed")
            return []

    def ping(self) -> int:
        """Pings the vector database and checks collection count.

        Returns:
            An integer count of collections in the database.
        """
        collections = self.client.get_collections()
        return len(collections.collections)


rag_service = RAGService()
