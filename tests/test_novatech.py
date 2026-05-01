"""Test RAG with NovaTech documentation."""
import requests
import json
import time

API_BASE = "http://localhost:5000/api/v1"
DOC_ID = "9479ad5c-bcf1-4937-ae4f-d23497e38bd2"

test_cases = [
    {
        "category": "Factual Extraction",
        "questions": [
            "When was NovaTech Solutions founded?",
            "How many enterprise clients does NovaTech serve?",
            "What is the API response time target?",
        ],
    },
    {
        "category": "Table Data",
        "questions": [
            "What products does NovaTech offer?",
            "What databases does the platform use?",
            "What are the security certifications?",
        ],
    },
    {
        "category": "Technical Details",
        "questions": [
            "What is the technology stack for the frontend?",
            "How many employees are in R&D?",
            "What is the system uptime target?",
        ],
    },
    {
        "category": "Negative Questions",
        "questions": [
            "What is NovaTech's stock price?",
            "Who is the CEO of NovaTech?",
        ],
    },
]


def test_question(question: str) -> dict:
    """Test a single question."""
    print(f"\nQ: {question}")
    
    payload = {
        "messages": [{"role": "user", "content": question}],
        "stream": True,
        "doc_ids": [DOC_ID],
    }
    
    try:
        start = time.time()
        response = requests.post(
            f"{API_BASE}/chat/completions",
            json=payload,
            stream=True,
            timeout=60,
        )
        
        if response.status_code != 200:
            print(f"  [ERROR] HTTP {response.status_code}")
            return {"quality": "error"}
        
        answer = ""
        references = []
        for line in response.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data: "):
                continue
            try:
                data = json.loads(line[6:])
                if data.get("type") == "answer":
                    answer += data.get("content", "")
                if data.get("done"):
                    references = data.get("references", [])
            except json.JSONDecodeError:
                pass
        
        elapsed = time.time() - start
        
        # Remove problematic unicode characters for Windows console
        safe_answer = answer.encode('gbk', errors='replace').decode('gbk')
        
        # Evaluate quality
        has_answer = len(answer) > 20
        has_refs = len(references) > 0
        has_denial = any(phrase in answer.lower() for phrase in ["not found", "未找到", "no information"])
        
        if has_answer and has_refs:
            quality = "good"
        elif has_denial and not has_refs:
            quality = "good"  # Correctly admits not found
        elif has_answer:
            quality = "acceptable"
        else:
            quality = "poor"
        
        print(f"  Time: {elapsed:.1f}s | Refs: {len(references)} | Quality: {quality}")
        print(f"  Answer: {safe_answer[:150]}...")
        
        return {
            "question": question,
            "answer": answer,
            "references": len(references),
            "quality": quality,
            "time": elapsed,
        }
        
    except Exception as e:
        print(f"  [ERROR] {e}")
        return {"quality": "error", "error": str(e)}


def main():
    print("=" * 60)
    print("NovaTech Documentation RAG Test")
    print("=" * 60)
    
    total = 0
    good = 0
    errors = 0
    
    for group in test_cases:
        print(f"\n--- {group['category']} ---")
        
        for q in group["questions"]:
            result = test_question(q)
            total += 1
            
            if result["quality"] == "good":
                good += 1
            elif result["quality"] == "error":
                errors += 1
    
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"Total: {total}")
    print(f"Good: {good}")
    print(f"Accuracy: {good/total*100:.1f}%")
    print(f"Errors: {errors}")


if __name__ == "__main__":
    main()
