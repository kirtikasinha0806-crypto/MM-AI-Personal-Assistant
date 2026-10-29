def test_health_endpoint(client):
    """Verifies that the /health endpoint responds with status 200 and expected diagnostic fields."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "gemini_configured" in data
    assert "gemini_model" in data
    assert "tavily_configured" in data
    assert "version" in data

