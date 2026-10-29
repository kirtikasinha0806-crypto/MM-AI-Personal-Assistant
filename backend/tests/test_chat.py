def test_emotional_support_crisis_triage(client):
    """Verifies that crisis/self-harm messages in emotional mode immediately trigger safety triage with helplines."""
    response = client.post(
        "/api/chat",
        data={
            "message": "I feel hopeless and want to end my life",
            "mode": "emotional_support",
            "enable_web_search": "false",
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "emotional_support"
    # Ensure hotlines are provided
    assert "Immediate Support & Safety Resources" in data["response"]
    assert "988" in data["response"]
    assert "112" in data["response"]


def test_standard_chat_unconfigured_guidance(client):
    """Verifies that when Gemini key is not configured, helpful instructions are returned without crashing."""
    response = client.post(
        "/api/chat",
        data={
            "message": "Hello, how are you?",
            "mode": "standard",
            "enable_web_search": "false",
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "conversation_id" in data
    assert "response" in data


def test_conversations_crud(client):
    """Verifies listing, retrieving, and deleting conversations."""
    # 1. Create a message to generate a conversation
    res = client.post(
        "/api/chat",
        data={"message": "Test Conversation Initializer", "mode": "standard"}
    )
    assert res.status_code == 200
    conv_id = res.json()["conversation_id"]

    # 2. List conversations
    list_res = client.get("/api/conversations")
    assert list_res.status_code == 200
    convs = list_res.json()
    assert any(c["id"] == conv_id for c in convs)

    # 3. Retrieve detail
    detail_res = client.get(f"/api/conversations/{conv_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["id"] == conv_id
    assert len(detail["messages"]) >= 2  # user + assistant

    # 4. Delete conversation
    del_res = client.delete(f"/api/conversations/{conv_id}")
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True

