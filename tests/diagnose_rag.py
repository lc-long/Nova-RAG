"""Diagnose RAG performance issues."""
import requests
import json
import time

API_BASE = "http://localhost:5000/api/v1"
DOC_ID = "9479ad5c-bcf1-4937-ae4f-d23497e38bd2"

test_queries = [
    "When was NovaTech Solutions founded?",
    "How many enterprise clients does NovaTech serve?",
    "What is the API response time target?",
]

def test_query(query: str):
    """Test a single query with detailed timing."""
    print(f"\n{'='*50}")
    print(f"Q: {query}")
    print(f"{'='*50}")
    
    payload = {
        "messages": [{"role": "user", "content": query}],
        "stream": True,
        "doc_ids": [DOC_ID],
    }
    
    start = time.time()
    
    try:
        response = requests.post(
            f"{API_BASE}/chat/completions",
            json=payload,
            stream=True,
            timeout=60,
        )
        
        if response.status_code != 200:
            print(f"[ERROR] HTTP {response.status_code}: {response.text[:200]}")
            return
        
        thought_time = None
        reasoning_time = None
        answer_time = None
        answer = ""
        thoughts = []
        
        chunk_start = time.time()
        
        for line in response.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data: "):
                continue
            
            try:
                data = json.loads(line[6:])
                chunk_type = data.get("type", "")
                current_time = time.time() - start
                
                if chunk_type == "thought":
                    thoughts.append(data.get("content", ""))
                    if thought_time is None:
                        thought_time = current_time
                        print(f"[{current_time:.1f}s] Thought phase started")
                
                elif chunk_type == "reasoning":
                    if reasoning_time is None:
                        reasoning_time = current_time
                        print(f"[{current_time:.1f}s] Reasoning phase started")
                
                elif chunk_type == "answer":
                    if answer_time is None:
                        answer_time = current_time
                        print(f"[{current_time:.1f}s] Answer phase started")
                    answer += data.get("content", "")
                
                elif data.get("done"):
                    total_time = time.time() - start
                    print(f"[{total_time:.1f}s] Done")
                    
            except json.JSONDecodeError:
                pass
        
        total_time = time.time() - start
        
        print(f"\n--- Summary ---")
        print(f"Total time: {total_time:.1f}s")
        print(f"Thought phase: {thought_time:.1f}s" if thought_time else "Thought phase: N/A")
        print(f"Reasoning phase: {reasoning_time:.1f}s" if reasoning_time else "Reasoning phase: N/A")
        print(f"Answer phase: {answer_time:.1f}s" if answer_time else "Answer phase: N/A")
        print(f"Answer length: {len(answer)} chars")
        print(f"Thoughts: {len(thoughts)}")
        
        if answer:
            safe_answer = answer.encode('gbk', errors='replace').decode('gbk')
            print(f"Answer preview: {safe_answer[:100]}...")
        else:
            print("Answer: [EMPTY]")
            
    except requests.exceptions.Timeout:
        print(f"[TIMEOUT] Request timed out after {time.time()-start:.1f}s")
    except Exception as e:
        print(f"[ERROR] {e}")


if __name__ == "__main__":
    print("RAG Performance Diagnosis")
    print("="*60)
    
    for query in test_queries:
        test_query(query)
        time.sleep(1)
