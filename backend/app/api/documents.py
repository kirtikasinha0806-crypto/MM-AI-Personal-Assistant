import io
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.models.document import Document, DocumentChunk, DocumentRevision
from backend.app.schemas.document import (
    DocumentSchema,
    DocumentDetailSchema,
    DocumentCreateRequest,
    DocumentUpdateRequest,
    RAGQueryRequest,
    RAGQueryResponse,
)
from backend.app.services.document_service import document_service
from backend.app.services.rag_service import rag_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/documents", tags=["Documents"])


@router.get("", response_model=List[DocumentSchema])
def list_documents(db: Session = Depends(get_db)):
    """Lists all uploaded or created documents and their indexing statuses."""
    docs = db.query(Document).order_by(Document.created_at.desc()).all()
    results = []
    for doc in docs:
        count = len(doc.chunks)
        schema_obj = DocumentSchema.model_validate(doc)
        schema_obj.chunk_count = count
        results.append(schema_obj)
    return results


@router.post("/upload", response_model=DocumentSchema)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Uploads a PDF, TXT, or MD document, extracts content, and indexes vector embeddings."""
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No file selected for upload.")

    safe_name = document_service.sanitize_filename(file.filename)
    ext = safe_name.split(".")[-1].lower() if "." in safe_name else "txt"

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")

    try:
        extracted_text, metadata = document_service.extract_text_from_file(file_bytes, safe_name)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # Check for duplicate document by filename
    existing = db.query(Document).filter(Document.filename == safe_name).first()
    if existing:
        # Update existing document content
        existing.content = extracted_text
        existing.file_size = len(file_bytes)
        existing.status = "uploaded"
        existing.metadata_json = metadata
        doc = existing
    else:
        doc = Document(
            filename=safe_name,
            file_type=ext,
            file_size=len(file_bytes),
            status="uploaded",
            content=extracted_text,
            metadata_json=metadata,
        )
        db.add(doc)

    db.commit()
    db.refresh(doc)

    # Index chunks in pgvector
    try:
        chunk_count = rag_service.index_document(db, doc)
    except Exception as e:
        logger.error(f"Error indexing chunks for {safe_name}: {e}")
        chunk_count = 0

    schema_obj = DocumentSchema.model_validate(doc)
    schema_obj.chunk_count = chunk_count
    return schema_obj


@router.post("/create", response_model=DocumentDetailSchema)
def create_document(
    req: DocumentCreateRequest,
    db: Session = Depends(get_db),
):
    """Creates a new document using Gemini from a prompt description."""
    try:
        doc = document_service.create_document_from_prompt(
            db=db,
            title=req.title,
            prompt=req.prompt,
            file_type=req.file_type or "md",
        )
        # Index chunks
        rag_service.index_document(db, doc)
        return doc
    except Exception as e:
        logger.error(f"Failed to generate document: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{document_id}", response_model=DocumentDetailSchema)
def get_document(document_id: str, db: Session = Depends(get_db)):
    """Retrieves document detail, full content, and revision history."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    schema_obj = DocumentDetailSchema.model_validate(doc)
    schema_obj.chunk_count = len(doc.chunks)
    return schema_obj


@router.patch("/{document_id}", response_model=DocumentDetailSchema)
def update_document(
    document_id: str,
    req: DocumentUpdateRequest,
    db: Session = Depends(get_db),
):
    """Updates an existing document using prompt instructions or manual edit, creates a revision snapshot, and reindexes."""
    try:
        doc = document_service.update_document(
            db=db,
            document_id=document_id,
            instructions=req.instructions,
            direct_content=req.direct_content,
        )
        # Re-index document automatically
        rag_service.index_document(db, doc)
        return doc
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Document update failed: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/{document_id}")
def delete_document(document_id: str, db: Session = Depends(get_db)):
    """Deletes a document and cascades deletion to all chunks, revisions, and vector embeddings."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    db.delete(doc)
    db.commit()
    return {"success": True, "deleted_id": document_id}


@router.post("/{document_id}/reindex", response_model=DocumentSchema)
def reindex_document(document_id: str, db: Session = Depends(get_db)):
    """Manually triggers chunk re-generation and vector re-indexing for a document."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    chunk_count = rag_service.index_document(db, doc)
    schema_obj = DocumentSchema.model_validate(doc)
    schema_obj.chunk_count = chunk_count
    return schema_obj


@router.post("/{document_id}/query", response_model=RAGQueryResponse)
def query_document(
    document_id: str,
    req: RAGQueryRequest,
    db: Session = Depends(get_db),
):
    """Queries a specific document using vector similarity and grounded RAG answer synthesis."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    answer, citations = rag_service.generate_grounded_answer(
        db=db,
        query=req.query,
        document_id=document_id,
        top_k=req.top_k or 3,
    )

    return RAGQueryResponse(
        document_id=document_id,
        query=req.query,
        answer=answer,
        citations=citations,
    )


@router.get("/{document_id}/download")
def download_document(
    document_id: str,
    export_format: Optional[str] = "original",
    db: Session = Depends(get_db),
):
    """Exports and downloads document content as .txt, .md, or .pdf."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    content = doc.content or ""
    base_name = doc.filename.rsplit(".", 1)[0]

    if export_format == "pdf":
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas

            buffer = io.BytesIO()
            p = canvas.Canvas(buffer, pagesize=letter)
            width, height = letter
            y = height - 50

            # Title
            p.setFont("Helvetica-Bold", 14)
            p.drawString(50, y, f"Document: {doc.filename}")
            y -= 30
            p.setFont("Helvetica", 10)

            for line in content.splitlines():
                if y < 50:
                    p.showPage()
                    p.setFont("Helvetica", 10)
                    y = height - 50
                p.drawString(50, y, line[:90])
                y -= 14

            p.save()
            buffer.seek(0)
            return StreamingResponse(
                buffer,
                media_type="application/pdf",
                headers={"Content-Disposition": f'attachment; filename="{base_name}.pdf"'}
            )
        except Exception as e:
            logger.error(f"PDF export failed: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="PDF export failed.")

    elif export_format == "txt":
        return Response(
            content=content,
            media_type="text/plain",
            headers={"Content-Disposition": f'attachment; filename="{base_name}.txt"'}
        )
    else:  # markdown / original
        return Response(
            content=content,
            media_type="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="{base_name}.md"'}
        )

