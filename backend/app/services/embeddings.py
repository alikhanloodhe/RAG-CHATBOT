import logging

from sentence_transformers import SentenceTransformer
from app.core.config import settings

logger = logging.getLogger(__name__)

class EmbeddingService:
    """Service to generate vector embeddings for text chunks using SentenceTransformers."""

    def __init__(self):
        """Initializes the EmbeddingService by loading the local SentenceTransformer model.
        
        Falls back to a mock handler in non-production environments if the loading fails.
        """
        self.model_name = "BAAI/bge-small-en-v1.5"
        try:
            # Initialize the model. It automatically downloads from HuggingFace on first run
            self.model = SentenceTransformer(self.model_name)
            logger.info("Loaded sentence-transformer model", extra={"model": self.model_name})
        except Exception as e:
            if settings.is_production:
                raise RuntimeError("Embedding model is required when APP_ENV=production") from e

            logger.warning(
                "Could not load embedding model; using development mock fallback",
                extra={"model": self.model_name, "error": e.__class__.__name__},
            )
            self.model = None

    def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Generates dense vector embeddings for a list of text strings.

        Args:
            texts: A list of strings to be embedded.

        Returns:
            A list of vector embeddings, where each embedding is a list of floats.
        """
        if not self.model:
            if settings.is_production:
                raise RuntimeError("Embedding model is unavailable in production")

            # Return dummy 384-dimensional vectors for robustness in local testing
            return [[0.01 * (i % 10) for i in range(384)] for _ in texts]
        
        # BGE models benefit from normalisation for cosine similarity
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()

    def get_embedding(self, text: str, is_query: bool = True) -> list[float]:
        """Generates a single dense vector embedding for the input text.

        Args:
            text: The string content to embed.
            is_query: Flag indicating if the text is a search query. If True and 
                      a BGE model is used, prepends the asymmetric search instruction.

        Returns:
            A list of floats representing the dense vector embedding.
        """
        if is_query and self.model and self.model_name.startswith("BAAI/bge-"):
            text = f"Represent this sentence for searching relevant passages: {text}"
        return self.get_embeddings([text])[0]

    def is_ready(self) -> bool:
        """Checks if the embedding model loaded successfully.

        Returns:
            True if the model is ready, False otherwise.
        """
        return self.model is not None

embedding_service = EmbeddingService()
