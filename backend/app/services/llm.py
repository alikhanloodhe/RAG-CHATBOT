import logging

from groq import Groq
from app.core.config import settings

logger = logging.getLogger(__name__)

class LLMService:
    """Service interfacing with Groq API for generating answers based on retrieved context."""

    def __init__(self):
        """Initializes LLMService by setting up the Groq client.
        
        Reads the GROQ_API_KEY from configuration settings and cleans extra formatting.
        """
        self.client = None
        if settings.GROQ_API_KEY:
            # Clean API key references of quotes or spaces
            api_key = settings.GROQ_API_KEY.strip().replace('"', '').replace("'", "")
            self.client = Groq(api_key=api_key)
        else:
            logger.warning("GROQ_API_KEY not set; LLM completions are unavailable")

    def generate_answer(self, query: str, context_items: list[dict]) -> str:
        """Synthesizes an answer grounded in the retrieved document context.

        Submits a strictly bounded prompt to Groq (using llama-3.1-8b-instant or configuration
        defaults) with a temperature of 0.0 to prevent hallucinations.

        Args:
            query: The user's input question.
            context_items: A list of payloads from matching document chunks.

        Returns:
            The synthesized answer string, including inline citation markers.
        """
        if not self.client:
            return "The language model is not configured, so I cannot synthesize an answer right now."

        if not context_items:
            return "I cannot find the answer in the provided documents."

        # Format retrieved context chunks for the prompt. Citation numbers match the API citation order.
        context_blocks = []
        for i, item in enumerate(context_items):
            filename = item.get("filename", "unknown")
            idx = item.get("chunk_index", 0)
            text = item.get("text", "")
            context_blocks.append(f"[{i + 1}] {filename} - Segment #{idx}\n{text}")

        context_text = "\n\n".join(context_blocks)

        system_message = (
            "You are a helpful, factual, and strictly grounded Retrieval-Augmented Generation (RAG) assistant. "
            "Your task is to answer the user's question using ONLY the provided document context. "
            "Do not assume, hallucinate, or extrapolate facts outside the context. "
            "If the provided context does not contain enough information to answer the question, state: "
            "'I cannot find the answer in the provided documents.' and do not attempt to make up an answer.\n\n"
            "OUTPUT RULES:\n"
            "1. Write one clean paragraph unless the question truly requires multiple paragraphs.\n"
            "2. Use compact citation markers like [1] or [2] after the relevant sentence.\n"
            "3. Do not include filenames, segment labels, quotes, or source details inside the paragraph.\n"
            "4. Do not write a separate Sources section. The application will render cited sources after the answer."
        )

        user_message = (
            f"Document Context:\n"
            f"----------------------\n"
            f"{context_text}\n"
            f"----------------------\n\n"
            f"Question: {query}\n\n"
            f"Answer with compact citation markers only:"
        )

        try:
            response = self.client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.0,  # Enforce deterministic, factual output
                max_tokens=1024
            )
            return response.choices[0].message.content
        except Exception:
            logger.exception("LLM completion failed")
            return "I could not generate an answer right now. Please try again later."

    def is_configured(self) -> bool:
        """Checks if the Groq LLM API is configured.

        Returns:
            True if Groq client is initialized, False otherwise.
        """
        return self.client is not None

llm_service = LLMService()
