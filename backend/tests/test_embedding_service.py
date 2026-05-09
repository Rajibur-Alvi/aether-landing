import asyncio
import sys
import types
import unittest


class FakeSettings:
    embedding_model_name = "llama-text-embed-v2"
    pinecone_dimension = 768


sys.modules.setdefault("config", types.SimpleNamespace(get_settings=lambda: FakeSettings()))
sys.modules.setdefault("pinecone", types.ModuleType("pinecone"))
sys.modules.setdefault(
    "pinecone.pinecone",
    types.SimpleNamespace(Pinecone=object),
)

import services.embedding_service as embedding_service


class FakeInference:
    def __init__(self):
        self.calls = []

    def embed(self, *, model, inputs, parameters):
        self.calls.append({
            "model": model,
            "inputs": inputs,
            "parameters": parameters,
        })
        return types.SimpleNamespace(
            data=[
                types.SimpleNamespace(values=[0.1, 0.2, 0.3]),
                types.SimpleNamespace(values=[0.4, 0.5, 0.6]),
            ]
        )


class FakePinecone:
    def __init__(self):
        self.inference = FakeInference()


class EmbeddingServiceTest(unittest.TestCase):
    def test_get_embeddings_uses_pinecone_inference(self):
        fake_pinecone = FakePinecone()
        embedding_service._get_pinecone = lambda: fake_pinecone
        embedding_service.get_settings = lambda: FakeSettings()

        embeddings = asyncio.run(embedding_service.get_embeddings(["alpha", "beta"]))

        self.assertEqual(embeddings, [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]])
        self.assertEqual(fake_pinecone.inference.calls, [{
            "model": "llama-text-embed-v2",
            "inputs": ["alpha", "beta"],
            "parameters": {
                "input_type": "passage",
                "truncate": "END",
                "dimension": 768,
            },
        }])


if __name__ == "__main__":
    unittest.main()
