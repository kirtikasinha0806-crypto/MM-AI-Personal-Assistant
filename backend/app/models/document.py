import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from backend.app.db.session import Base
from backend.app.core.config import settings


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Document(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(20), nullable=False)  # 'pdf', 'txt', 'md'
    file_size = Column(Integer, nullable=False, default=0)
    status = Column(String(20), nullable=False, default="uploaded")  # 'uploaded', 'processing', 'indexed', 'failed'
    content = Column(Text, nullable=False, default="")
    metadata_json = Column(JSON, nullable=True, default=dict)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan", order_by="DocumentChunk.chunk_index")
    revisions = relationship("DocumentRevision", back_populates="document", cascade="all, delete-orphan", order_by="DocumentRevision.revision_number.desc()")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False, default=0)
    chunk_text = Column(Text, nullable=False)
    embedding = Column(Vector(settings.EMBEDDING_DIMENSION), nullable=True)
    metadata_json = Column(JSON, nullable=True, default=dict)  # e.g. {"page_number": 1}
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    document = relationship("Document", back_populates="chunks")


class DocumentRevision(Base):
    __tablename__ = "document_revisions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    revision_number = Column(Integer, nullable=False, default=1)
    content = Column(Text, nullable=False)
    change_summary = Column(String(255), nullable=False, default="Initial version")
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    document = relationship("Document", back_populates="revisions")

