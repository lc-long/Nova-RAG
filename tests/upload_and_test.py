"""Upload PDF and run test."""
import requests
import json
import sys

API_BASE = "http://localhost:5000/api/v1"

def upload_document(file_path: str) -> str:
    """Upload document and return doc_id."""
    print(f"Uploading: {file_path}")
    
    with open(file_path, 'rb') as f:
        files = {'file': (file_path.split('/')[-1], f, 'application/pdf')}
        response = requests.post(f"{API_BASE}/docs/upload", files=files, timeout=60)
    
    if response.status_code == 200:
        data = response.json()
        doc_id = data.get('id')
        print(f"Upload successful! doc_id: {doc_id}")
        return doc_id
    else:
        print(f"Upload failed: {response.status_code} - {response.text}")
        return None

def wait_for_processing(doc_id: str, timeout: int = 60):
    """Wait for document to be processed."""
    import time
    print("Waiting for processing...")
    
    start = time.time()
    while time.time() - start < timeout:
        response = requests.get(f"{API_BASE}/docs", timeout=10)
        if response.status_code == 200:
            docs = response.json()
            for doc in docs:
                if doc['id'] == doc_id and doc['status'] == 'ready':
                    print("Document ready!")
                    return True
        time.sleep(2)
    
    print("Timeout waiting for processing")
    return False

if __name__ == "__main__":
    file_path = "tests/novatech_documentation.pdf"
    
    # Upload
    doc_id = upload_document(file_path)
    if not doc_id:
        sys.exit(1)
    
    # Wait for processing
    if wait_for_processing(doc_id):
        print(f"\nUse this doc_id for testing: {doc_id}")
    else:
        print("Document may not be fully processed yet")
        print(f"doc_id: {doc_id}")
