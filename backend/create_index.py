import os
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec

load_dotenv()

api_key = os.getenv('PINECONE_API_KEY')
if not api_key:
    print("PINECONE_API_KEY not found in .env")
    exit(1)

pc = Pinecone(api_key=api_key)

if not pc.has_index('entropy-vectors'):
    pc.create_index(
        name='entropy-vectors',
        dimension=384,
        metric='cosine',
        spec=ServerlessSpec(cloud='aws', region='us-east-1')
    )
    print("Index created")
else:
    print("Index already exists")