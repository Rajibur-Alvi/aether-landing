import os
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec
from config import get_settings

load_dotenv()
settings = get_settings()

api_key = settings.pinecone_api_key or os.getenv('PINECONE_API_KEY')
if not api_key:
    print("PINECONE_API_KEY not found in .env")
    exit(1)

pc = Pinecone(api_key=api_key)

if not pc.has_index(settings.pinecone_index_name):
    pc.create_index(
        name=settings.pinecone_index_name,
        dimension=settings.pinecone_dimension,
        metric='cosine',
        spec=ServerlessSpec(cloud='aws', region='us-east-1')
    )
    print("Index created")
else:
    print("Index already exists")
