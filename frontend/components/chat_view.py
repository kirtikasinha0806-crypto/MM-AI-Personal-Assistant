import base64
import streamlit as st
from frontend.utils.api_client import api_client


def _render_generated_image(media_meta: dict):
    """Renders a generated image using watermark-free base64 bytes with compact, balanced sizing."""
    b64 = media_meta.get("base64")
    img_url = media_meta.get("url")
    caption = media_meta.get("prompt", "Generated Image")

    img_bytes = None
    if b64:
        # Use clean, watermark-stripped bytes from backend (width=420 keeps it compact and shows the full image)
        img_bytes = base64.b64decode(b64)
        st.image(img_bytes, caption=caption, width=420)
    elif img_url:
        st.image(img_url, caption=caption, width=420)

    col_dl1, col_dl2 = st.columns([1, 2])
    with col_dl1:
        if img_bytes:
            st.download_button(
                label="💾 Download Clean Image",
                data=img_bytes,
                file_name="generated_image.jpg",
                mime="image/jpeg",
                key=f"dl_{abs(hash(b64[:30]))}",
            )
    with col_dl2:
        if img_url:
            st.link_button("Open Full Image", url=img_url)


def render_citations(sources):
    """Renders formatted citation accordions distinguishing between Document RAG and Web Search."""
    if not sources:
        return

    rag_sources = [s for s in sources if s.get("source_type") == "rag"]
    web_sources = [s for s in sources if s.get("source_type") == "web"]

    if rag_sources or web_sources:
        with st.expander("📚 Verified References & Sources", expanded=False):
            if rag_sources:
                st.markdown("##### 📄 Document Excerpts (RAG)")
                for idx, src in enumerate(rag_sources, 1):
                    doc_title = src.get("title", "Document")
                    page = src.get("page")
                    loc = f" (Page {page})" if page else ""
                    snippet = src.get("snippet", "")
                    st.markdown(f"**[{idx}] {doc_title}{loc}**")
                    st.caption(f"> \"{snippet}\"")

            if web_sources:
                st.markdown("##### 🌐 Live Web Results (Tavily)")
                for idx, src in enumerate(web_sources, 1):
                    title = src.get("title", "Web Page")
                    url = src.get("url", "#")
                    snippet = src.get("snippet", "")
                    st.markdown(f"**[{idx}] [{title}]({url})**")
                    st.caption(f"> \"{snippet}\"")


def render_chat_view():
    """Renders the unified multimodal chat interface with history, document/image upload, and input."""
    # Header bar
    col_title, col_action = st.columns([4, 1])
    with col_title:
        current_mode = st.session_state.get("mode", "standard")
        if current_mode == "emotional_support":
            st.markdown("### 💚 Emotional Support Space")
            st.caption("A supportive, non-judgmental space to reflect and talk through what's on your mind.")
        else:
            st.markdown("### 💬 Multimodal AI Assistant")
            st.caption("Ask questions, analyze images & documents, search the web, or generate images.")

    with col_action:
        if st.session_state.get("chat_messages"):
            if st.button("🧹 Clear Chat", key="clear_chat_btn"):
                st.session_state.chat_messages = []
                st.session_state.uploader_key_version = st.session_state.get("uploader_key_version", 0) + 1
                st.rerun()

    # Unified Document & Image Attachment Bar (Zero audio)
    uploader_ver = st.session_state.get("uploader_key_version", 0)
    with st.expander("📎 Attach Document or Image", expanded=False):
        uploaded_media = st.file_uploader(
            "Upload Document (PDF, Word, PPTX, Excel, CSV, TXT, MD) or Image (PNG, JPG, WEBP):",
            type=["pdf", "docx", "pptx", "xlsx", "csv", "txt", "md", "png", "jpg", "jpeg", "webp"],
            key=f"media_uploader_{uploader_ver}"
        )
        if uploaded_media:
            is_image = uploaded_media.type.startswith("image") or any(
                uploaded_media.name.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".webp"]
            )
            if is_image:
                st.success(f"🖼️ Attached Image: **{uploaded_media.name}**")
                st.image(uploaded_media, caption="Preview of attached image", width=220)
            else:
                st.success(f"📄 Attached Document: **{uploaded_media.name}**")

    # Render Chat History (Flows naturally across page, like ChatGPT)
    messages = st.session_state.get("chat_messages", [])
    if not messages:
        st.info("👋 Hello! Send a message, generate an image, or attach a document/image above to ask questions.")
    else:
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            sources = msg.get("sources", [])
            media_meta = msg.get("media_metadata")

            avatar = "👤" if role == "user" else "🤖"
            with st.chat_message(role, avatar=avatar):
                if media_meta:
                    # Case 1: Assistant generated image (use watermark-free base64)
                    if media_meta.get("type") == "generated_image":
                        _render_generated_image(media_meta)
                    # Case 2: Attached document
                    elif media_meta.get("type") == "document":
                        fn = media_meta.get("filename", "Document")
                        st.caption(f"📄 Attached document: `{fn}`")
                    # Case 3: Other attached file
                    elif media_meta.get("filename"):
                        fn = media_meta.get("filename", "")
                        st.caption(f"📎 Attached file: `{fn}`")

                st.markdown(content)
                if sources:
                    render_citations(sources)

    # Fixed Chat Input Box at root level (locked to viewport bottom like ChatGPT)
    user_prompt = st.chat_input("Type your message, ask about attached documents/images, or request an image...")

    if user_prompt:
        # Append user message to UI state immediately
        user_media_meta = None
        media_bytes = None
        media_name = None
        media_type = None

        if uploaded_media:
            media_bytes = uploaded_media.getvalue()
            media_name = uploaded_media.name
            media_type = uploaded_media.type
            file_ext = media_name.lower().split(".")[-1] if "." in media_name else ""
            doc_exts = {"pdf", "docx", "pptx", "xlsx", "csv", "txt", "md"}
            meta_type = "document" if file_ext in doc_exts else "image"
            user_media_meta = {"type": meta_type, "filename": media_name, "mime_type": media_type}
            # Clear file uploader for subsequent messages
            st.session_state.uploader_key_version = uploader_ver + 1

        st.session_state.setdefault("chat_messages", []).append({
            "role": "user",
            "content": user_prompt,
            "media_metadata": user_media_meta
        })

        # Render immediately
        with st.chat_message("user", avatar="👤"):
            if user_media_meta:
                prefix = "📄 Attached document" if user_media_meta.get("type") == "document" else "📎 Attached file"
                st.caption(f"{prefix}: `{media_name}`")
            st.markdown(user_prompt)

        # Send request to FastAPI backend
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("AI is thinking and processing..."):
                resp = api_client.send_chat_message(
                    message=user_prompt,
                    conversation_id=st.session_state.get("current_conversation_id"),
                    mode=st.session_state.get("mode", "standard"),
                    enable_web_search=st.session_state.get("enable_web_search", False),
                    document_id=None,
                    file_bytes=media_bytes,
                    filename=media_name,
                    mime_type=media_type,
                )

                reply_text = resp.get("response", "No response generated.")
                sources = resp.get("sources", [])
                resp_media = resp.get("media_metadata")
                st.session_state.current_conversation_id = resp.get("conversation_id")

                if resp_media and resp_media.get("type") == "generated_image":
                    _render_generated_image(resp_media)

                st.markdown(reply_text)
                if sources:
                    render_citations(sources)

                # Append assistant reply to state
                st.session_state.chat_messages.append({
                    "role": "assistant",
                    "content": reply_text,
                    "sources": sources,
                    "media_metadata": resp_media,
                })
        st.rerun()

