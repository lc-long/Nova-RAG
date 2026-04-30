"""Test the parent-child chunking implementation."""
import sys
sys.path.insert(0, "python/src")

from core.chunker.parent_child import ParentChildChunker, Chunk


def test_parent_child_chunking():
    """Test that parent-child chunking produces correct structure."""
    chunker = ParentChildChunker(
        parent_chunk_size=200,
        child_chunk_size=80,
        overlap=10
    )

    text = """这是第一段文字，包含一些内容。

这是第二段文字，包含更多内容用于测试父子分块策略。

这是第三段文字，也是最后一节。"""

    chunks = chunker.chunk(text, "test_doc_1")

    parent_chunks = [c for c in chunks if c.chunk_type == "parent"]
    child_chunks = [c for c in chunks if c.chunk_type == "child"]

    print(f"Total chunks: {len(chunks)}")
    print(f"Parent chunks: {len(parent_chunks)}")
    print(f"Child chunks: {len(child_chunks)}")

    for chunk in parent_chunks:
        print(f"\nPARENT [{chunk.chunk_id}]:")
        print(f"  Content: {chunk.content[:50]}...")
        child_of_this = [c for c in child_chunks if c.parent_id == chunk.chunk_id]
        print(f"  Children: {len(child_of_this)}")

    for chunk in child_chunks[:3]:
        print(f"\nCHILD [{chunk.chunk_id}]:")
        print(f"  Parent: {chunk.parent_id}")
        print(f"  Content: {chunk.content[:50]}...")


if __name__ == "__main__":
    test_parent_child_chunking()
