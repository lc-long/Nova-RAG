"""ChromaDB diagnostic script - inspect database state and retrieval quality."""
import os
from dotenv import load_dotenv
load_dotenv()

os.environ["HF_ENDPOINT"] = os.getenv("HF_ENDPOINT", "https://hf-mirror.com")

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

PERSIST_DIR = "./vector_db"
COLLECTION_NAME = "lumina_docs"

print("=" * 60)
print("ChromaDB Diagnostic Report")
print("=" * 60)

# 1. Connect and count total chunks
client = chromadb.PersistentClient(
    path=PERSIST_DIR,
    settings=Settings(anonymized_telemetry=False)
)

try:
    collection = client.get_collection(name=COLLECTION_NAME)
except Exception as e:
    print(f"[ERROR] Cannot get collection: {e}")
    exit(1)

count = collection.count()
print(f"\n[1] Total chunks in DB: {count}")

# 2. Get all data to inspect metadata
all_data = collection.get()
print(f"[2] Metadata keys available: {list(all_data['metadatas'][0].keys()) if all_data['metadatas'] else 'N/A'}")

# Search for "报销" or "pdf" in metadata
doc_ids_found = set()
for i, meta in enumerate(all_data['metadatas']):
    doc_id = meta.get('doc_id', '')
    chunk_type = meta.get('chunk_type', '')
    # Search in doc_id or any metadata field
    for v in meta.values():
        if v and ('报销' in str(v) or 'pdf' in str(v).lower()):
            doc_ids_found.add(doc_id)
            break

print(f"    Documents matching '报销' or 'pdf': {len(doc_ids_found)}")
if doc_ids_found:
    for did in list(doc_ids_found)[:10]:
        print(f"    - {did}")
else:
    print("    (none found)")

# 3. Sample content
print(f"\n[3] Content samples (up to 3 chunks):")
docs = all_data['documents']
metas = all_data['metadatas']
for i in range(min(3, len(docs))):
    safe = docs[i][:150].replace('\n', ' ')
    print(f"    Chunk[{i}]: {safe}...")
    print(f"             doc_id={metas[i].get('doc_id')} type={metas[i].get('chunk_type')} page={metas[i].get('page_number')}")

# 4. Retrieval simulation
print(f"\n[4] Retrieval simulation for '总结报销':")

# Load embedder
print("    Loading embedding model...")
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

query_embedding = model.encode(["总结报销"]).tolist()
print(f"    Query embedding dim: {len(query_embedding[0])}")

# Query ChromaDB
results = collection.query(
    query_embeddings=query_embedding,
    n_results=5,
    include=["documents", "metadatas", "distances"]
)

distances = results.get('distances', [[]])[0]
documents = results.get('documents', [[]])[0]
metadatas = results.get('metadatas', [[]])[0]

print(f"    Top-5 retrieval results:")
for i, (dist, doc, meta) in enumerate(zip(distances, documents, metadatas)):
    safe_doc = doc[:100].replace('\n', ' ') if doc else '(empty)'
    print(f"    [{i}] distance={dist:.4f} doc_id={meta.get('doc_id')} chunk={meta.get('chunk_type')} content={safe_doc}...")

print(f"\n    Distance interpretation:")
print(f"    - Distance < 0.5: highly relevant")
print(f"    - Distance 0.5-1.0: somewhat relevant")
print(f"    - Distance > 1.0: not relevant (semantic mismatch)")
if distances and distances[0] > 1.0:
    print(f"    -> WARNING: top result distance={distances[0]:.4f} > 1.0 indicates poor retrieval!")
else:
    print(f"    -> Retrieval quality appears acceptable")

print("\n" + "=" * 60)
print("Diagnostic complete")
print("=" * 60)