import json
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.models.conversation import Conversation, Message
from backend.app.models.document import Document
from backend.app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    Citation,
    ConversationSchema,
    ConversationDetailSchema,
)
from backend.app.services.llm_service import llm_service
from backend.app.services.search_service import search_service
from backend.app.services.emotional_service import emotional_service
from backend.app.services.rag_service import rag_service
from backend.app.services.image_service import image_service
from backend.app.services.document_service import document_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Chat"])


@router.get("/conversations", response_model=List[ConversationSchema])
def list_conversations(db: Session = Depends(get_db)):
    """Lists all conversation sessions ordered by most recently updated."""
    conversations = db.query(Conversation).order_by(Conversation.updated_at.desc()).all()
    result = []
    for conv in conversations:
        count = len(conv.messages)
        schema_item = ConversationSchema.model_validate(conv)
        schema_item.message_count = count
        result.append(schema_item)
    return result


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailSchema)
def get_conversation(conversation_id: str, db: Session = Depends(get_db)):
    """Retrieves full conversation details and message history."""
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return conv


@router.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: str, db: Session = Depends(get_db)):
    """Deletes a conversation and its associated messages."""
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    db.delete(conv)
    db.commit()
    return {"success": True, "deleted_id": conversation_id}


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    message: str = Form(...),
    conversation_id: Optional[str] = Form(None),
    mode: Optional[str] = Form("standard"),
    enable_web_search: Optional[bool] = Form(False),
    document_id: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    """Multimodal chat endpoint accepting text, mode, web search toggle, RAG target, and optional media file."""
    # 1. Fetch or create conversation
    conv = None
    if conversation_id:
        conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()

    if not conv:
        title_summary = (message[:40] + "...") if len(message) > 40 else message
        conv = Conversation(title=title_summary, mode=mode or "standard")
        db.add(conv)
        db.commit()
        db.refresh(conv)

    # 2. Process uploaded file (Documents or Images - strictly isolated per conversation)
    DOC_EXTS = {"pdf", "docx", "doc", "pptx", "ppt", "xlsx", "xls", "csv", "txt", "md", "markdown"}
    IMAGE_EXTS = {"png", "jpg", "jpeg", "webp", "gif"}

    media_bytes = None
    media_mime_type = None
    media_metadata = None

    if file and file.filename:
        file_bytes = await file.read()
        file_ext = file.filename.lower().split(".")[-1] if "." in file.filename else ""
        safe_filename = document_service.sanitize_filename(file.filename)

        if file_ext in DOC_EXTS:
            # Handle document: extract text & index in RAG scoped specifically to this conversation
            try:
                extracted_text, doc_meta = document_service.extract_text_from_file(file_bytes, safe_filename)
                doc = Document(
                    filename=safe_filename,
                    file_type=file_ext,
                    file_size=len(file_bytes),
                    status="uploaded",
                    content=extracted_text,
                    metadata_json={**(doc_meta or {}), "conversation_id": conv.id},
                )
                db.add(doc)
                db.commit()
                db.refresh(doc)

                rag_service.index_document(db, doc)
                document_id = doc.id
                media_metadata = {
                    "type": "document",
                    "filename": safe_filename,
                    "document_id": doc.id,
                    "size": len(file_bytes),
                }
                logger.info(f"Indexed document '{safe_filename}' for conversation '{conv.id}'")
            except Exception as e:
                logger.error(f"Error indexing attached document {safe_filename}: {e}")
                media_metadata = {
                    "type": "document",
                    "filename": safe_filename,
                    "error": str(e),
                }
        else:
            # Handle image: multimodal vision processing
            media_bytes = file_bytes
            media_mime_type = file.content_type or f"image/{file_ext or 'jpeg'}"
            media_metadata = {
                "type": "image",
                "filename": safe_filename,
                "mime_type": media_mime_type,
                "size": len(media_bytes),
            }
            logger.info(f"Received image upload: {safe_filename} ({media_mime_type}, {len(media_bytes)} bytes)")

    # 3. Store user message in database
    user_msg = Message(
        conversation_id=conv.id,
        role="user",
        content=message,
        media_metadata=media_metadata,
    )
    db.add(user_msg)
    db.commit()

    # 3.1 Check for Image Generation intent
    is_img_gen, img_subject = image_service.detect_image_request(message)
    if is_img_gen and not file:
        logger.info(f"Image generation request detected: '{img_subject or message}'")
        gen_img = image_service.generate_image(img_subject or message)
        if gen_img:
            resp_text = f"🎨 Here is the generated image for: **{img_subject or message}**"
            assistant_msg = Message(
                conversation_id=conv.id,
                role="assistant",
                content=resp_text,
                media_metadata=gen_img,
            )
            db.add(assistant_msg)
            db.commit()
            return ChatResponse(
                conversation_id=conv.id,
                response=resp_text,
                mode=mode or "standard",
                sources=[],
                media_metadata=gen_img,
            )
        else:
            busy_text = "🎨 The image generation server is momentarily busy or cooling down (the free tier allows 1 image every 45 seconds). Please wait 15–20 seconds and try again!"
            assistant_msg = Message(
                conversation_id=conv.id,
                role="assistant",
                content=busy_text,
            )
            db.add(assistant_msg)
            db.commit()
            return ChatResponse(
                conversation_id=conv.id,
                response=busy_text,
                mode=mode or "standard",
                sources=[],
            )

    # 4. Check for Emotional Support mode & crisis safety check
    citations: List[Citation] = []
    system_instruction = None

    if mode == "emotional_support":
        is_crisis, crisis_reply = emotional_service.check_crisis(message)
        if is_crisis:
            # Immediate crisis intervention takes top priority
            assistant_msg = Message(
                conversation_id=conv.id,
                role="assistant",
                content=crisis_reply,
            )
            db.add(assistant_msg)
            db.commit()
            return ChatResponse(
                conversation_id=conv.id,
                response=crisis_reply,
                mode=mode,
                sources=[],
            )
        system_instruction = emotional_service.get_system_prompt()

    # 5. Handle Document RAG Context (strictly scoped to this conversation)
    rag_context = None
    target_doc_id = document_id

    # If no document was attached in this turn, check if this conversation previously had one
    if not target_doc_id:
        all_docs = db.query(Document).order_by(Document.created_at.desc()).all()
        for d in all_docs:
            if (d.metadata_json or {}).get("conversation_id") == conv.id:
                target_doc_id = d.id
                break

    if target_doc_id:
        relevant_chunks = rag_service.retrieve_relevant_chunks(db, query=message, document_id=target_doc_id, top_k=3)
        if relevant_chunks:
            blocks = []
            for chunk, score, filename in relevant_chunks:
                p_num = (chunk.metadata_json or {}).get("page_number")
                citations.append(Citation(
                    source_type="rag",
                    title=filename,
                    url=None,
                    snippet=chunk.chunk_text[:300],
                    page=p_num
                ))
                page_info = f" (Page/Slide {p_num})" if p_num else ""
                blocks.append(f"[{filename}{page_info}]: {chunk.chunk_text}")
            rag_context = "\n\n".join(blocks)

    # 6. Handle Live Web Search Context (if enabled)
    web_context = None
    if enable_web_search:
        search_results = search_service.search(query=message, max_results=4)
        if search_results:
            web_context = search_service.format_results_for_prompt(search_results)
            for res in search_results:
                citations.append(Citation(
                    source_type="web",
                    title=res.title,
                    url=res.url,
                    snippet=res.snippet,
                    page=None
                ))

    # 7. Build history context for LLM
    past_messages = [
        {"role": m.role, "content": m.content}
        for m in conv.messages[:-1]  # Exclude current user message which is passed directly
    ]

    # 8. Generate response from Gemini
    response_text = llm_service.generate_chat_response(
        prompt=message,
        conversation_history=past_messages,
        system_instruction=system_instruction,
        context_documents=rag_context,
        web_search_context=web_context,
        media_bytes=media_bytes,
        media_mime_type=media_mime_type,
    )

    # 9. Store assistant message in database
    citations_data = [c.dict() for c in citations]
    assistant_msg = Message(
        conversation_id=conv.id,
        role="assistant",
        content=response_text,
        sources=citations_data if citations_data else None,
    )
    db.add(assistant_msg)
    db.commit()

    return ChatResponse(
        conversation_id=conv.id,
        response=response_text,
        mode=mode or "standard",
        sources=citations,
        media_metadata=media_metadata,
    )

