import streamlit as st
from frontend.utils.api_client import api_client


def render_sidebar():
    """Renders the left navigation sidebar including conversations, modes, toggles, and system status."""
    st.sidebar.title("🤖 MM Assistant")
    st.sidebar.caption("Multimodal Personal AI Assistant")

    # 1. New Conversation Button
    if st.sidebar.button("➕ New Conversation", use_container_width=True, type="primary"):
        st.session_state.current_conversation_id = None
        st.session_state.chat_messages = []
        st.session_state.uploader_key_version = st.session_state.get("uploader_key_version", 0) + 1
        st.rerun()

    st.sidebar.divider()

    # 2. Modes & Assistant Toggles
    st.sidebar.subheader("⚙️ Settings & Mode")
    
    # Mode selector
    mode_options = ["Standard Assistant", "Emotional Support Mode"]
    current_mode_index = 1 if st.session_state.get("mode") == "emotional_support" else 0
    selected_mode = st.sidebar.radio(
        "Interaction Mode:",
        mode_options,
        index=current_mode_index,
        help="Select between standard multimodal Q&A/coding or compassionate emotional support."
    )
    st.session_state.mode = "emotional_support" if selected_mode == "Emotional Support Mode" else "standard"

    if st.session_state.mode == "emotional_support":
        st.sidebar.info("💡 **Emotional Support Active**: Empathetic, supportive active listening with crisis triage safeguards.")

    # Web search toggle
    st.session_state.enable_web_search = st.sidebar.checkbox(
        "🌐 Enable Web Search (Tavily)",
        value=st.session_state.get("enable_web_search", False),
        help="Enables Tavily live web retrieval for current facts and source links."
    )

    st.sidebar.divider()

    # 3. Conversation History
    st.sidebar.subheader("💬 Recent Conversations")
    conversations = api_client.list_conversations()
    
    if conversations:
        for conv in conversations[:12]:
            title = conv.get("title", "Untitled Chat")
            conv_id = conv.get("id")
            is_active = (conv_id == st.session_state.get("current_conversation_id"))
            
            col1, col2 = st.sidebar.columns([4, 1])
            with col1:
                button_label = f"{'👉 ' if is_active else ''}{title[:22]}"
                if st.button(button_label, key=f"conv_{conv_id}", use_container_width=True):
                    st.session_state.current_conversation_id = conv_id
                    st.session_state.active_page = "💬 Assistant Chat"
                    st.session_state.uploader_key_version = st.session_state.get("uploader_key_version", 0) + 1
                    # Load conversation history
                    conv_detail = api_client.get_conversation(conv_id)
                    if conv_detail:
                        st.session_state.chat_messages = conv_detail.get("messages", [])
                        st.session_state.mode = conv_detail.get("mode", "standard")
                    st.rerun()
            with col2:
                if st.button("🗑️", key=f"del_{conv_id}", help="Delete chat"):
                    api_client.delete_conversation(conv_id)
                    if st.session_state.get("current_conversation_id") == conv_id:
                        st.session_state.current_conversation_id = None
                        st.session_state.chat_messages = []
                        st.session_state.uploader_key_version = st.session_state.get("uploader_key_version", 0) + 1
                    st.rerun()
    else:
        st.sidebar.caption("No saved conversations yet.")

