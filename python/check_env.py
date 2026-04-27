"""Environment check script for Lumina Insight Python service.

Run this script to verify your environment is correctly configured.
Usage: python check_env.py

Exit codes:
  0 - All checks passed
  1 - One or more checks failed
"""
import os
import sys
import traceback


def check_result(name: str, passed: bool, error_msg: str = "") -> bool:
    """Print check result and return pass/fail status."""
    if passed:
        print(f"[PASS] {name}")
        return True
    else:
        print(f"[FAIL] {name}")
        if error_msg:
            print(f"       {error_msg}")
        return False


def main():
    print("=" * 60)
    print("Lumina Insight - Environment Check")
    print("=" * 60)
    print()

    all_passed = True

    # 1. Check Python version
    print("[1] Checking Python version...")
    py_version = sys.version_info
    if py_version.major >= 3 and py_version.minor >= 10:
        all_passed &= check_result(
            f"Python version {py_version.major}.{py_version.minor}.{py_version.micro}",
            True
        )
    else:
        all_passed &= check_result(
            f"Python version {py_version.major}.{py_version.minor}.{py_version.micro} (requires 3.10+)",
            False,
            "Please upgrade to Python 3.10 or higher"
        )

    # 2. Check .env file
    print("\n[2] Checking .env file...")
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        all_passed &= check_result(".env file exists", True)
        with open(env_path, "r") as f:
            env_content = f.read()
        has_api_key = "MINIMAX_API_KEY" in env_content and "sk-" in env_content
        has_group_id = "MINIMAX_GROUP_ID" in env_content
        all_passed &= check_result(
            "MINIMAX_API_KEY configured",
            has_api_key,
            "MINIMAX_API_KEY not found or invalid in .env"
        )
        all_passed &= check_result(
            "MINIMAX_GROUP_ID configured",
            has_group_id,
            "MINIMAX_GROUP_ID not found in .env"
        )
    else:
        all_passed &= check_result(
            ".env file exists",
            False,
            f".env not found at {env_path}. Please create it from .env.example"
        )
        all_passed &= check_result("MINIMAX_API_KEY configured", False)
        all_passed &= check_result("MINIMAX_GROUP_ID configured", False)

    # 3. Check core library imports
    print("\n[3] Checking core library imports...")
    libraries = [
        ("dotenv", "python-dotenv"),
        ("fastapi", "fastapi"),
        ("uvicorn", "uvicorn"),
        ("chromadb", "chromadb"),
        ("sentence_transformers", "sentence-transformers"),
        ("langchain.text_splitter", "langchain"),
        ("requests", "requests"),
        ("sseclient", "sseclient-py"),
        ("pydantic", "pydantic"),
        ("pdfplumber", "pdfplumber"),
        ("docx", "python-docx"),
    ]

    for module_name, package_name in libraries:
        try:
            __import__(module_name)
            all_passed &= check_result(f"{package_name}", True)
        except ImportError as e:
            all_passed &= check_result(
                f"{package_name}",
                False,
                f"Install with: pip install {package_name}"
            )

    # 4. Check project module imports
    print("\n[4] Checking project module imports...")

    # Add src to path for relative imports
    src_path = os.path.join(os.path.dirname(__file__), "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

    project_modules = [
        ("core.chunker.parent_child", "ParentChildChunker"),
        ("core.chunker.pdf_parser", "extract_text_from_pdf"),
        ("core.chunker.docx_parser", "extract_text_from_docx"),
        ("core.embedder.sentence_transformer", "SentenceTransformerEmbedder"),
        ("core.retriever.chroma", "ChromaRetriever"),
        ("core.storage.vector_store", "VectorStore"),
        ("core.llm.minimax", "MinimaxClient"),
    ]

    for module_name, _ in project_modules:
        try:
            # Convert path format to module format
            module_path = module_name.replace(".", "/")
            __import__(module_name)
            all_passed &= check_result(f"src.{module_name}", True)
        except ImportError as e:
            all_passed &= check_result(
                f"src.{module_name}",
                False,
                f"Import failed: {e}"
            )
        except Exception as e:
            all_passed &= check_result(
                f"src.{module_name}",
                False,
                f"Error: {e}"
            )

    # 5. Check ChromaDB initialization
    print("\n[5] Checking ChromaDB initialization...")
    try:
        import chromadb
        from chromadb.config import Settings
        client = chromadb.PersistentClient(path="./test_vector_db", settings=Settings(anonymized_telemetry=False))
        collection = client.get_or_create_collection("test_check")
        all_passed &= check_result("ChromaDB client initialization", True)
        # Cleanup
        client.delete_collection("test_check")
        import shutil
        shutil.rmtree("./test_vector_db", ignore_errors=True)
    except Exception as e:
        all_passed &= check_result(
            "ChromaDB client initialization",
            False,
            f"Error: {e}"
        )

    # 6. Summary
    print("\n" + "=" * 60)
    if all_passed:
        print("RESULT: All checks PASSED!")
        print("You can now start the Python service with:")
        print("  python -m src.api.server")
        print("=" * 60)
        return 0
    else:
        print("RESULT: Some checks FAILED!")
        print("Please fix the issues above before running the service.")
        print("\nQuick fix commands:")
        print("  pip install -r requirements.txt")
        print("  # Or use mirror:")
        print("  pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except Exception as e:
        print(f"\n[CRITICAL ERROR] {e}")
        traceback.print_exc()
        print("\nPlease report this error to the development team.")
        sys.exit(1)