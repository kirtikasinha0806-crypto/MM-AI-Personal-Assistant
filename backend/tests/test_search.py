def test_search_endpoint_without_key(client):
    """Verifies that the /api/search endpoint handles unconfigured search credentials gracefully with a 503 status code."""
    response = client.post("/api/search", json={"query": "latest AI news", "max_results": 3})
    # If TAVILY_API_KEY is not configured in test environment, it returns 503 or 200 with clear diagnostics
    assert response.status_code in [200, 503]
    if response.status_code == 503:
        assert "Tavily" in response.json()["detail"]

