import os
import sys
import traceback

print("=== TEST ENV SCRIPT ===")
print(f"Python: {sys.version}")

try:
    print("Importing dotenv...")
    from dotenv import load_dotenv
    print("OK: dotenv")

    print("Importing chromadb...")
    import chromadb
    from chromadb.config import Settings
    print("OK: chromadb")

    print("Importing sentence_transformers...")
    from sentence_transformers import SentenceTransformer
    print("OK: sentence_transformers")

    print("Importing langchain...")
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    print("OK: langchain-text-splitters")

    print("Loading .env...")
    load_dotenv()
    print(f"API_KEY: {bool(os.getenv('MINIMAX_API_KEY'))}")

    print("ALL IMPORTS SUCCESS")
except Exception as e:
    print(f"ERROR: {e}")
    traceback.print_exc()