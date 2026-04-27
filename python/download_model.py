"""Manual model download script for Lumina Insight.

Run this script BEFORE starting the server to pre-download the embedding model.
Usage:
    cd python
    uv run python download_model.py

This avoids network issues during server startup.
"""
import os
import sys

# Configure HuggingFace mirror
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

print("=" * 60)
print("Lumina Insight - Model Downloader")
print("=" * 60)
print()
print(f"Using mirror: {os.environ['HF_ENDPOINT']}")
print()

try:
    from sentence_transformers import SentenceTransformer

    model_name = "all-MiniLM-L6-v2"
    print(f"Downloading model '{model_name}'...")

    model = SentenceTransformer(model_name)

    print()
    print(f"Model downloaded successfully!")
    print(f"Model cache location: {model.tokenizer.name_or_path}")

    # Test embedding
    print()
    print("Testing embedding generation...")
    test_embedding = model.encode(["测试文本"], convert_to_numpy=True)
    print(f"Embedding vector dimension: {len(test_embedding[0])}")
    print()
    print("All checks PASSED! You can now start the server.")

except Exception as e:
    print()
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    print()
    print("If you see SSL/EOF errors, try:")
    print("  1. Check your network connection")
    print("  2. Set HF_ENDPOINT to a different mirror in .env")
    print("  3. Or manually download the model from https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2")
    sys.exit(1)