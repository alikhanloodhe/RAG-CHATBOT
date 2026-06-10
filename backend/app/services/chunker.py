import logging
import re
from transformers import AutoTokenizer

logger = logging.getLogger(__name__)

class TextChunker:
    """Service to split raw text into token-bounded semantic chunks preserving sentence boundaries."""

    def __init__(self):
        """Initializes the TextChunker by loading the HuggingFace tokenizer for BGE-small.
        
        Falls back to character-based heuristic token counts if the tokenizer is unavailable.
        """
        try:
            # Initialize tokenizer for BAAI/bge-small-en-v1.5
            self.tokenizer = AutoTokenizer.from_pretrained("BAAI/bge-small-en-v1.5")
        except Exception as e:
            logger.warning(
                "Could not load BGE tokenizer; falling back to word estimation",
                extra={"error": e.__class__.__name__},
            )
            self.tokenizer = None

    def count_tokens(self, text: str) -> int:
        """Estimates or counts the number of tokens in the given text.

        Args:
            text: The text string to measure.

        Returns:
            The number of tokens as an integer.
        """
        if self.tokenizer:
            try:
                return len(self.tokenizer.encode(text, add_special_tokens=False))
            except Exception:
                pass
        # Fallback approximation: 1 token is about 4 characters
        return max(1, len(text) // 4)

    def split_into_sentences(self, text: str) -> list[str]:
        """Splits raw text into a list of individual sentences.

        Args:
            text: The full string of text to split.

        Returns:
            A list of strings representing the individual sentences.
        """
        # Split text by sentence-ending punctuation (. ! ?) followed by whitespace
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]

    def chunk_text(self, text: str, min_tokens: int = 300, max_tokens: int = 500, overlap_tokens: int = 50) -> list[str]:
        """Segments raw text into overlapping token-bounded chunks.

        Maintains complete sentences where possible. If a single sentence is larger
        than the max_tokens limit, it is split into words to avoid truncation issues.

        Args:
            text: The raw text string to split.
            min_tokens: Minimum token target for chunks.
            max_tokens: Maximum token ceiling for chunks (defaults to 500 for BGE context window).
            overlap_tokens: Count of tokens to overlap between adjacent chunks.

        Returns:
            A list of string chunks.
        """
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        sentences = self.split_into_sentences(text)
        if not sentences:
            return []

        chunks = []
        current_sentences = []
        current_tokens = 0

        for sentence in sentences:
            sentence_tokens = self.count_tokens(sentence)

            # If a single sentence exceeds max_tokens on its own, chunk it by word slices
            if sentence_tokens > max_tokens:
                if current_sentences:
                    chunks.append(" ".join(current_sentences))
                    current_sentences = []
                    current_tokens = 0

                words = sentence.split()
                sub_sentence = []
                sub_tokens = 0
                for word in words:
                    word_tokens = self.count_tokens(word)
                    if sub_tokens + word_tokens > max_tokens:
                        chunks.append(" ".join(sub_sentence))
                        # Carry over 20 words for overlap
                        sub_sentence = sub_sentence[-20:] + [word]
                        sub_tokens = self.count_tokens(" ".join(sub_sentence))
                    else:
                        sub_sentence.append(word)
                        sub_tokens += word_tokens
                if sub_sentence:
                    chunks.append(" ".join(sub_sentence))
                continue

            # If this sentence pushes the current chunk past max_tokens, save chunk and apply overlap
            if current_tokens + sentence_tokens > max_tokens:
                chunks.append(" ".join(current_sentences))

                # Assemble overlap from the end of the current chunk
                overlap_sentences = []
                overlap_tokens_count = 0
                for s in reversed(current_sentences):
                    s_tokens = self.count_tokens(s)
                    if overlap_tokens_count + s_tokens > overlap_tokens:
                        if overlap_sentences:  # Ensure we have at least one overlap sentence if possible
                            break
                    overlap_sentences.insert(0, s)
                    overlap_tokens_count += s_tokens

                current_sentences = overlap_sentences + [sentence]
                current_tokens = overlap_tokens_count + sentence_tokens
            else:
                current_sentences.append(sentence)
                current_tokens += sentence_tokens

        # Append last remaining sentences
        if current_sentences:
            chunks.append(" ".join(current_sentences))

        return chunks

text_chunker = TextChunker()
