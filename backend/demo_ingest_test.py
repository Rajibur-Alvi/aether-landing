import json
import urllib.request
import urllib.error

INGEST_URL = 'http://127.0.0.1:8000/api/public/ingest/text'
CHAT_URL = 'http://127.0.0.1:8000/api/public/chat/ask'

payload = {
    'title': 'Entropy Aesthetic Demo Document',
    'content': (
        'Entropy Aesthetic is a document intelligence engine built for rapid retrieval and AI reasoning. '
        'The public demo allows users to ingest large text payloads, then query them with an AI assistant. '
        'This test document contains multiple paragraphs describing the feature set, including ingestion, chunking, '
        'vector storage, relevance search, and guided responses. The system must split long text into chunks, store '
        'embeddings in Pinecone, and then answer questions about the content with context-aware accuracy. '
        'By design, the demo supports two free test queries before the paywall appears, and it should be reliable '
        'for visitors trying the product without a login. The document also highlights model selection, response '
        'temperature, and metadata tracking so the AI can cite source chunks. The test should prove End-to-end '
        'document ingestion and question answering with our public RAG endpoint. '
        'In practice, the engine can read product briefs, meeting notes, research summaries, and customer support '
        'documentation. It transforms raw text into searchable vectors and generates answers based on the most '
        'relevant chunks. This sample text is intentionally long to trigger chunk splitting and validate the backend '
        'logic for large payloads. The query step should return an answer referencing the document description, '
        'feature list, and demo experience.'
    )
}

def run_demo():
    json_data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(INGEST_URL, data=json_data, headers={'Content-Type': 'application/json'})
    print('Sending ingest request...')
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            print('Ingest status:', resp.status)
            ingest_resp = json.loads(resp.read().decode('utf-8'))
            print('Ingest response:', json.dumps(ingest_resp, indent=2))
    except urllib.error.HTTPError as e:
        print('Ingest HTTP error:', e.code, e.read().decode('utf-8'))
        raise
    except Exception as e:
        print('Ingest failed:', e)
        raise

    if ingest_resp.get('document_id'):
        ask_payload = {
            'message': 'What does the demo document say the system is built to do?',
            'document_id': ingest_resp['document_id'],
        }
        ask_data = json.dumps(ask_payload).encode('utf-8')
        ask_req = urllib.request.Request(CHAT_URL, data=ask_data, headers={'Content-Type': 'application/json'})
        print('Sending chat request...')
        try:
            with urllib.request.urlopen(ask_req, timeout=120) as resp:
                print('Chat status:', resp.status)
                chat_resp = json.loads(resp.read().decode('utf-8'))
                print('Chat response:', json.dumps(chat_resp, indent=2))
        except urllib.error.HTTPError as e:
            print('Chat HTTP error:', e.code, e.read().decode('utf-8'))
        except Exception as e:
            print('Chat failed:', e)
    else:
        print('No document_id returned; skipping chat test.')


if __name__ == "__main__":
    run_demo()
