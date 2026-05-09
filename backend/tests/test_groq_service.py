import asyncio
import sys
import types
import unittest


class FakeAsyncGroq:
    pass


sys.modules.setdefault("groq", types.SimpleNamespace(AsyncGroq=FakeAsyncGroq))
sys.modules.setdefault("config", types.SimpleNamespace(get_settings=lambda: types.SimpleNamespace(groq_api_key="")))

from services import groq_service


class FakeCompletions:
    def __init__(self):
        self.messages = None

    async def create(self, **kwargs):
        self.messages = kwargs["messages"]
        return types.SimpleNamespace(
            choices=[
                types.SimpleNamespace(
                    message=types.SimpleNamespace(content="The answer is ALPHA SPARK. [1]"),
                    finish_reason="stop",
                )
            ],
            usage=types.SimpleNamespace(total_tokens=20, completion_tokens=8),
        )


class FakeClient:
    def __init__(self):
        self.completions = FakeCompletions()
        self.chat = types.SimpleNamespace(completions=self.completions)


class GroqServiceTest(unittest.TestCase):
    def test_custom_system_prompt_preserves_rag_context(self):
        fake_client = FakeClient()
        groq_service._get_async_client = lambda: fake_client

        asyncio.run(groq_service.generate_rag_response(
            query="What is the phrase?",
            context_chunks=[{
                "document_id": "doc-1",
                "score": 0.9,
                "text": "The unique phrase is ALPHA SPARK.",
            }],
            system_prompt="Answer tersely.",
        ))

        system_message = fake_client.completions.messages[0]["content"]
        self.assertIn("Answer tersely.", system_message)
        self.assertIn("CONTEXT:", system_message)
        self.assertIn("ALPHA SPARK", system_message)


if __name__ == "__main__":
    unittest.main()
