import unittest

from app.services.chunker import TextChunker


class ChunkerTests(unittest.TestCase):
    def test_chunker_uses_word_estimation_without_tokenizer(self):
        chunker = TextChunker.__new__(TextChunker)
        chunker.tokenizer = None

        text = "Sentence one. Sentence two. Sentence three."
        chunks = chunker.chunk_text(text, min_tokens=1, max_tokens=5, overlap_tokens=1)

        self.assertGreaterEqual(len(chunks), 1)
        self.assertTrue(all(chunk.strip() for chunk in chunks))


if __name__ == "__main__":
    unittest.main()
