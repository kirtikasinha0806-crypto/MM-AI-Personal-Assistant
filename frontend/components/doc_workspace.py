import streamlit as st
from frontend.utils.api_client import api_client


def render_doc_workspace():
    """Renders the document workspace for uploading, generating, editing, querying, and downloading documents."""
    st.markdown("### 📁 Document Workspace & Knowledge Base")
    st.caption("Upload reference documents, generate new files with Gemini, revise existing content, and export downloads.")

    tab_library, tab_create, tab_query = st.tabs(["📚 Document Library", "✨ Create New Document", "🔍 Grounded Document Q&A"])

    # TAB 1: Document Library & Editor
    with tab_library:
        col_up1, col_up2 = st.columns([3, 1])
        with col_up1:
            uploaded_doc = st.file_uploader(
                "Upload Document (PDF, Word DOCX, PowerPoint PPTX, Excel XLSX/CSV, TXT, Markdown):",
                type=["pdf", "docx", "pptx", "xlsx", "csv", "txt", "md"],
                key="doc_file_uploader"
            )
        with col_up2:
            st.write("")
            st.write("")
            if uploaded_doc and st.button("📤 Upload & Index", key="upload_doc_btn", type="primary"):
                with st.spinner("Extracting text and generating vector embeddings..."):
                    res = api_client.upload_document(uploaded_doc.getvalue(), uploaded_doc.name)
                    if res.get("error"):
                        st.error(f"Upload failed: {res.get('detail')}")
                    else:
                        st.success(f"Uploaded and indexed `{uploaded_doc.name}` successfully!")
                        st.rerun()

        st.divider()

        docs = api_client.list_documents()
        if not docs:
            st.info("No documents uploaded yet. Upload a PDF/TXT/MD above or generate one in the 'Create New Document' tab.")
        else:
            st.markdown(f"**Indexed Documents ({len(docs)}):**")
            for doc in docs:
                doc_id = doc.get("id")
                fn = doc.get("filename")
                status = doc.get("status")
                chunk_count = doc.get("chunk_count", 0)
                file_size_kb = round(doc.get("file_size", 0) / 1024, 1)

                with st.expander(f"📄 {fn} | Status: {status.upper()} | {chunk_count} Chunks | {file_size_kb} KB"):
                    # Actions row
                    btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 1])
                    with btn_col1:
                        if st.button("🔄 Re-index", key=f"reindex_{doc_id}"):
                            with st.spinner("Re-indexing chunks..."):
                                api_client.reindex_document(doc_id)
                                st.success("Re-indexed successfully!")
                                st.rerun()
                    with btn_col2:
                        if st.button("🗑️ Delete", key=f"del_doc_{doc_id}"):
                            api_client.delete_document(doc_id)
                            st.warning(f"Deleted `{fn}` and all embeddings.")
                            st.rerun()
                    with btn_col3:
                        pass

                    # Fetch document details
                    doc_detail = api_client.get_document(doc_id)
                    if doc_detail:
                        content = doc_detail.get("content", "")
                        
                        # Document preview
                        st.markdown("##### Content Preview:")
                        st.text_area("Content", value=content, height=180, key=f"preview_{doc_id}", disabled=True)

                        # Download controls
                        dl_col1, dl_col2, dl_col3 = st.columns(3)
                        with dl_col1:
                            st.download_button(
                                "📥 Download .md",
                                data=content,
                                file_name=f"{fn.rsplit('.', 1)[0]}.md",
                                mime="text/markdown",
                                key=f"dl_md_{doc_id}"
                            )
                        with dl_col2:
                            st.download_button(
                                "📥 Download .txt",
                                data=content,
                                file_name=f"{fn.rsplit('.', 1)[0]}.txt",
                                mime="text/plain",
                                key=f"dl_txt_{doc_id}"
                            )
                        with dl_col3:
                            # PDF Download link from backend export
                            backend_url = api_client.base_url
                            pdf_url = f"{backend_url}/api/documents/{doc_id}/download?export_format=pdf"
                            st.link_button("📥 Export PDF", url=pdf_url)

                        # Document AI Revision Editor
                        st.markdown("##### ✏️ Revise Document with AI Instructions:")
                        revision_prompt = st.text_input(
                            "Revision Instructions:",
                            placeholder="e.g. 'Add a section on future improvements' or 'Make it more concise'",
                            key=f"rev_input_{doc_id}"
                        )
                        if st.button("🚀 Apply Revision", key=f"apply_rev_{doc_id}"):
                            if revision_prompt:
                                with st.spinner("Revising document with Gemini..."):
                                    res = api_client.update_document(doc_id, instructions=revision_prompt)
                                    if res.get("error"):
                                        st.error(f"Revision failed: {res.get('detail')}")
                                    else:
                                        st.success("Document updated and re-indexed!")
                                        st.rerun()

                        # Revision History
                        revisions = doc_detail.get("revisions", [])
                        if revisions:
                            with st.expander(f"📜 Version History ({len(revisions)} revisions)"):
                                for r in revisions:
                                    rev_num = r.get("revision_number")
                                    summary = r.get("change_summary")
                                    created = r.get("created_at")
                                    st.write(f"- **Rev #{rev_num}**: {summary} (`{created}`)")

    # TAB 2: Create New Document
    with tab_create:
        st.markdown("#### ✨ Generate a New Document from a Prompt")
        new_title = st.text_input("Document Title:", placeholder="e.g. AI Ethics Research Summary")
        new_format = st.selectbox("File Format:", ["md", "txt"])
        new_prompt = st.text_area(
            "Content Description / Requirements:",
            placeholder="Describe what the document should contain in detail...",
            height=150
        )
        if st.button("Create Document", type="primary"):
            if not new_title or not new_prompt:
                st.warning("Please provide both a title and description.")
            else:
                with st.spinner("Generating structured document with Gemini..."):
                    res = api_client.create_document(title=new_title, prompt=new_prompt, file_type=new_format)
                    if res.get("error"):
                        st.error(f"Creation failed: {res.get('detail')}")
                    else:
                        st.success(f"Document `{res.get('filename')}` generated and indexed!")
                        st.rerun()

    # TAB 3: Grounded Document Q&A (Standalone RAG)
    with tab_query:
        st.markdown("#### 🔍 Query a Specific Document (Strict Grounding)")
        docs = api_client.list_documents()
        if not docs:
            st.info("No indexed documents available to query.")
        else:
            doc_map = {f"{d.get('filename')} ({d.get('chunk_count', 0)} chunks)": d.get("id") for d in docs}
            chosen_label = st.selectbox("Select Document:", list(doc_map.keys()))
            chosen_id = doc_map[chosen_label]

            rag_question = st.text_input("Ask a question about this document:")
            top_k = st.slider("Number of source chunks to retrieve:", min_value=1, max_value=5, value=3)

            if st.button("Query Document", type="primary", key="rag_query_btn"):
                if not rag_question:
                    st.warning("Please enter a question.")
                else:
                    with st.spinner("Searching document vectors and synthesizing grounded answer..."):
                        res = api_client.query_document(chosen_id, rag_question, top_k=top_k)
                        answer = res.get("answer", "")
                        citations = res.get("citations", [])

                        st.markdown("##### Answer:")
                        st.write(answer)

                        if citations:
                            with st.expander("📚 Retrieved Excerpts"):
                                for idx, c in enumerate(citations, 1):
                                    page = c.get("page")
                                    loc = f" (Page {page})" if page else ""
                                    st.markdown(f"**[{idx}] {c.get('title')}{loc}**")
                                    st.caption(f"> {c.get('snippet')}")

