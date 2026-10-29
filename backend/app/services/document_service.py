import io
import re
import logging
from typing import Tuple, Dict, Any, Optional
from sqlalchemy.orm import Session
from pypdf import PdfReader

from backend.app.models.document import Document, DocumentRevision
from backend.app.services.llm_service import llm_service

logger = logging.getLogger(__name__)

# Max upload limit: 15 MB
MAX_UPLOAD_SIZE = 15 * 1024 * 1024


class DocumentService:
    """Handles document text extraction, document generation, and revision tracking."""

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Strips unsafe path characters and keeps standard alphanumeric and safe symbols."""
        clean_name = re.sub(r"[^\w\.-]", "_", filename)
        return clean_name or "uploaded_document"

    @staticmethod
    def extract_text_from_file(file_bytes: bytes, filename: str) -> Tuple[str, Dict[str, Any]]:
        """Extracts text and metadata from PDF, TXT, or Markdown bytes.

        Returns (extracted_text, metadata_dict).
        """
        if len(file_bytes) > MAX_UPLOAD_SIZE:
            raise ValueError(f"File size exceeds maximum allowed limit of {MAX_UPLOAD_SIZE // (1024 * 1024)} MB.")

        ext = filename.lower().split(".")[-1] if "." in filename else ""

        if ext == "pdf":
            try:
                reader = PdfReader(io.BytesIO(file_bytes))
                total_pages = len(reader.pages)
                pages_text = []
                for idx, page in enumerate(reader.pages):
                    page_text = page.extract_text() or ""
                    pages_text.append(f"[Page {idx + 1}]\n{page_text}")
                full_text = "\n\n".join(pages_text)
                metadata = {"pages": total_pages, "char_count": len(full_text)}
                return full_text, metadata
            except Exception as e:
                logger.error(f"Failed to extract PDF text from {filename}: {e}")
                raise ValueError(f"Could not parse PDF content: {str(e)}")

        elif ext in ["docx", "doc"]:
            try:
                import docx
                doc = docx.Document(io.BytesIO(file_bytes))
                parts = []
                for p in doc.paragraphs:
                    if p.text.strip():
                        parts.append(p.text.strip())
                for table in doc.tables:
                    for row in table.rows:
                        row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                        if row_text:
                            parts.append(row_text)
                full_text = "\n\n".join(parts)
                metadata = {"paragraphs": len(parts), "char_count": len(full_text)}
                return full_text, metadata
            except Exception as e:
                logger.error(f"Failed to parse Word document {filename}: {e}")
                raise ValueError(f"Could not parse Word (.docx) document: {str(e)}")

        elif ext in ["pptx", "ppt"]:
            try:
                import pptx
                prs = pptx.Presentation(io.BytesIO(file_bytes))
                slides_text = []
                for idx, slide in enumerate(prs.slides):
                    slide_lines = []
                    for shape in slide.shapes:
                        if shape.has_text_frame:
                            for paragraph in shape.text_frame.paragraphs:
                                if paragraph.text.strip():
                                    slide_lines.append(paragraph.text.strip())
                    slide_str = "\n".join(slide_lines)
                    slides_text.append(f"[Slide {idx + 1}]\n{slide_str}")
                full_text = "\n\n".join(slides_text)
                metadata = {"slides": len(prs.slides), "char_count": len(full_text)}
                return full_text, metadata
            except Exception as e:
                logger.error(f"Failed to parse PowerPoint presentation {filename}: {e}")
                raise ValueError(f"Could not parse PowerPoint (.pptx) presentation: {str(e)}")

        elif ext in ["xlsx", "xls"]:
            try:
                import openpyxl
                wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
                sheets_text = []
                for s_idx, sheet_name in enumerate(wb.sheetnames, 1):
                    sheet = wb[sheet_name]
                    rows_text = []
                    for row in sheet.iter_rows(values_only=True):
                        row_vals = [str(v).strip() for v in row if v is not None and str(v).strip()]
                        if row_vals:
                            rows_text.append(" | ".join(row_vals))
                    if rows_text:
                        sheets_text.append(f"[Page {s_idx}]\nSheet: {sheet_name}\n" + "\n".join(rows_text))
                full_text = "\n\n".join(sheets_text)
                metadata = {"sheets": len(wb.sheetnames), "char_count": len(full_text)}
                return full_text, metadata
            except Exception as e:
                logger.error(f"Failed to parse Excel spreadsheet {filename}: {e}")
                raise ValueError(f"Could not parse Excel spreadsheet: {str(e)}")

        elif ext in ["csv"]:
            try:
                full_text = file_bytes.decode("utf-8")
            except UnicodeDecodeError:
                full_text = file_bytes.decode("latin-1", errors="replace")
            metadata = {"char_count": len(full_text), "lines": len(full_text.splitlines())}
            return full_text, metadata

        elif ext in ["txt", "md", "markdown", "json", "py", "html"]:
            try:
                full_text = file_bytes.decode("utf-8")
            except UnicodeDecodeError:
                full_text = file_bytes.decode("latin-1", errors="replace")
            metadata = {"char_count": len(full_text), "lines": len(full_text.splitlines())}
            return full_text, metadata

        else:
            raise ValueError(
                f"Unsupported document format '.{ext}'. Supported formats: PDF, Word (DOCX), PowerPoint (PPTX), Excel (XLSX, CSV), TXT, Markdown (MD)."
            )

    @staticmethod
    def create_document_from_prompt(
        db: Session,
        title: str,
        prompt: str,
        file_type: str = "md"
    ) -> Document:
        """Generates a new document using Gemini from a prompt description."""
        system_prompt = (
            "You are an expert technical writer and document creator. "
            "Generate a comprehensive, well-structured, formatted document based on the user's request. "
            "Use clear headings, bullet points, and code/table blocks where appropriate."
        )

        generated_text = llm_service.generate_chat_response(
            prompt=f"Please create a document titled '{title}'. Requirements:\n{prompt}",
            system_instruction=system_prompt,
        )

        safe_filename = DocumentService.sanitize_filename(f"{title}.{file_type}")

        # Create Document record
        doc = Document(
            filename=safe_filename,
            file_type=file_type,
            file_size=len(generated_text.encode("utf-8")),
            status="uploaded",
            content=generated_text,
            metadata_json={"source": "ai_generated", "prompt": prompt},
        )
        db.add(doc)
        db.flush()  # to obtain doc.id

        # Save initial revision
        rev = DocumentRevision(
            document_id=doc.id,
            revision_number=1,
            content=generated_text,
            change_summary="Initial AI generation from user prompt",
        )
        db.add(rev)
        db.commit()
        db.refresh(doc)
        return doc

    @staticmethod
    def update_document(
        db: Session,
        document_id: str,
        instructions: Optional[str] = None,
        direct_content: Optional[str] = None,
    ) -> Document:
        """Applies edits to an existing document, records a revision, and updates the document."""
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            raise ValueError(f"Document with ID {document_id} not found.")

        current_content = doc.content

        if direct_content is not None:
            new_content = direct_content
            change_summary = "Manual edit by user"
        elif instructions:
            system_prompt = (
                "You are an expert editor. You will receive an existing document and specific revision instructions. "
                "Output the complete revised version of the document following all instructions faithfully. "
                "Do not include conversational preamble or explanation; output only the updated document content."
            )
            prompt = (
                f"--- ORIGINAL DOCUMENT ---\n{current_content}\n--- END ORIGINAL ---\n\n"
                f"REVISION INSTRUCTIONS: {instructions}\n\n"
                f"Please produce the updated document:"
            )
            new_content = llm_service.generate_chat_response(
                prompt=prompt,
                system_instruction=system_prompt,
            )
            change_summary = f"AI Revision: {instructions[:100]}"
        else:
            raise ValueError("Either 'instructions' or 'direct_content' must be provided to update a document.")

        # Determine next revision number
        highest_rev = db.query(DocumentRevision).filter(
            DocumentRevision.document_id == document_id
        ).order_by(DocumentRevision.revision_number.desc()).first()

        next_rev_num = (highest_rev.revision_number + 1) if highest_rev else 1

        # Add revision snapshot
        rev = DocumentRevision(
            document_id=doc.id,
            revision_number=next_rev_num,
            content=new_content,
            change_summary=change_summary,
        )
        db.add(rev)

        # Update document
        doc.content = new_content
        doc.file_size = len(new_content.encode("utf-8"))
        doc.status = "uploaded"  # Marked uploaded to signal re-indexing is required
        db.commit()
        db.refresh(doc)
        return doc


document_service = DocumentService()

