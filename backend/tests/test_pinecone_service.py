import asyncio
import sys
import types
import unittest


sys.modules.setdefault("pinecone", types.ModuleType("pinecone"))
sys.modules.setdefault(
    "pinecone.pinecone",
    types.SimpleNamespace(Pinecone=object),
)
sys.modules.setdefault(
    "config",
    types.SimpleNamespace(get_settings=lambda: types.SimpleNamespace(pinecone_api_key="")),
)

from services import pinecone_service


class FakeIndex:
    def __init__(self, matches):
        self.matches = matches
        self.filters = []

    def query(self, **kwargs):
        self.filters.append(kwargs.get("filter"))
        return {"matches": self.matches}


class PineconeServiceSearchTest(unittest.TestCase):
    def setUp(self):
        self.original_get_single_embedding = pinecone_service.get_single_embedding
        self.original_get_index = pinecone_service._get_index
        pinecone_service.get_single_embedding = self._fake_embedding

    def tearDown(self):
        pinecone_service.get_single_embedding = self.original_get_single_embedding
        pinecone_service._get_index = self.original_get_index

    async def _fake_embedding(self, text):
        return [0.1, 0.2, 0.3]

    def test_document_search_returns_best_match_when_threshold_discards_all(self):
        index = FakeIndex([
            {
                "score": 0.42,
                "metadata": {
                    "chunk_text": "Aether analyzes entropy in uploaded documents.",
                    "document_id": "doc-123",
                    "chunk_index": 0,
                },
            }
        ])
        pinecone_service._get_index = lambda: index

        matches = asyncio.run(pinecone_service.search_similar_chunks(
            query="What does Aether analyze?",
            user_id="test-user",
            document_id="doc-123",
            top_k=3,
        ))

        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["text"], "Aether analyzes entropy in uploaded documents.")
        self.assertEqual(matches[0]["score"], 0.42)
        self.assertEqual(index.filters, [{"user_id": "test-user", "document_id": "doc-123"}])


if __name__ == "__main__":
    unittest.main()
