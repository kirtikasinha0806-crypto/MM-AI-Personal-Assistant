import os
import sys
import streamlit as st

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from frontend.components.sidebar import render_sidebar
from frontend.components.chat_view import render_chat_view

# Set page configuration
st.set_page_config(
    page_title="Multimodal AI Personal Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS to hide Deploy/Stop header, streamline chat styling, and lock input
st.markdown("""
<style>
    /* Hide Streamlit top bar, Deploy button, Stop button, and footer */
    header[data-testid="stHeader"] {
        display: none !important;
    }
    #MainMenu {
        visibility: hidden !important;
    }
    footer {
        visibility: hidden !important;
    }
    [data-testid="stToolbar"] {
        display: none !important;
    }
    [data-testid="stDecoration"] {
        display: none !important;
    }
    [data-testid="stStatusWidget"] {
        display: none !important;
    }

    /* Streamlined layout and clean spacing */
    .main .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 7rem !important;
        max-width: 900px;
    }

    /* Fixed bottom input container pinned strictly to viewport bottom like ChatGPT */
    div[data-testid="stBottom"] {
        background-color: transparent !important;
        padding-bottom: 1.2rem !important;
    }

    /* Chat input styling */
    div[data-testid="stChatInput"] {
        border-radius: 14px !important;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25) !important;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Session State
if "current_conversation_id" not in st.session_state:
    st.session_state.current_conversation_id = None
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []
if "mode" not in st.session_state:
    st.session_state.mode = "standard"
if "enable_web_search" not in st.session_state:
    st.session_state.enable_web_search = False
if "uploader_key_version" not in st.session_state:
    st.session_state.uploader_key_version = 0

# Render Left Navigation Sidebar
render_sidebar()

# Main Assistant Chat Area (Root Level Rendering - enables native bottom fixed st.chat_input)
render_chat_view()

