import io


def test_document_upload_and_chunking(client):
    """Verifies document upload, text parsing, chunking, and database indexing."""
    sample_content = (
        "# Artificial Intelligence\n\n"
        "Artificial Intelligence (AI) is intelligence demonstrated by machines, "
        "as opposed to the natural intelligence displayed by animals including humans.\n\n"
        "AI applications include advanced web search engines, recommendation systems, "
        "understanding human speech, and self-driving cars."
    )
    file_bytes = sample_content.encode("utf-8")
    files = {"file": ("ai_overview.md", io.BytesIO(file_bytes), "text/markdown")}

    # 1. Upload document
    upload_res = client.post("/api/documents/upload", files=files)
    assert upload_res.status_code == 200
    doc_data = upload_res.json()
    assert doc_data["filename"] == "ai_overview.md"
    assert doc_data["status"] == "indexed"
    assert doc_data["chunk_count"] > 0
    doc_id = doc_data["id"]

    # 2. Get document detail
    detail_res = client.get(f"/api/documents/{doc_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert "Artificial Intelligence" in detail["content"]

    # 3. Query document via RAG
    query_res = client.post(
        f"/api/documents/{doc_id}/query",
        json={"query": "What are AI applications?", "top_k": 2}
    )
    assert query_res.status_code == 200
    rag_data = query_res.json()
    assert "answer" in rag_data
    assert len(rag_data["citations"]) > 0
    assert rag_data["citations"][0]["title"] == "ai_overview.md"

    # 4. Reindex document
    reindex_res = client.post(f"/api/documents/{doc_id}/reindex")
    assert reindex_res.status_code == 200
    assert reindex_res.json()["chunk_count"] > 0

    # 5. Download document
    dl_res = client.get(f"/api/documents/{doc_id}/download?export_format=md")
    assert dl_res.status_code == 200
    assert "Artificial Intelligence" in dl_res.text

    # 6. Delete document
    del_res = client.delete(f"/api/documents/{doc_id}")
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True

