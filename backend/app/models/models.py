from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from app.db.session import Base

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    visitor_id = Column(String, index=True, nullable=True)  # Anonymous browser tracking
    filename = Column(String, nullable=False)
    file_type = Column(String, nullable=False)  # pdf, png, jpg, jpeg
    file_path = Column(String, nullable=False)
    status = Column(String, default="uploaded")  # uploaded, processing, completed, failed
    ocr_used = Column(Boolean, default=False)
    total_chunks = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    metadata_records = relationship("DocumentMetadata", back_populates="document", cascade="all, delete-orphan", uselist=False)
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")


class DocumentMetadata(Base):
    __tablename__ = "document_metadata"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), unique=True, nullable=False)
    doc_type = Column(String, nullable=False)  # Invoice, Contract, Medical Report, ID, Passport, Policy, Manual, Employee Doc, etc.
    extracted_data = Column(JSONB, nullable=False, default={})  # Key-value structured metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    document = relationship("Document", back_populates="metadata_records")


class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    page_number = Column(Integer, nullable=True)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(768), nullable=True)  # BAAI/bge-base-en-v1.5 has 768 dimensions
    chunk_metadata = Column(JSONB, nullable=False, default={})  # headings, page context, etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    document = relationship("Document", back_populates="chunks")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    visitor_id = Column(String, index=True, nullable=True)  # Anonymous browser tracking
    title = Column(String, nullable=False, default="New Chat")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)
    role = Column(String, nullable=False)  # user, assistant
    content = Column(Text, nullable=False)
    citations = Column(JSONB, nullable=True, default=[])  # Sources referenced in the response
    ip_address = Column(String, nullable=True, index=True)  # Client IP for rate limiting
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    session = relationship("ChatSession", back_populates="messages")


class UserLimit(Base):
    __tablename__ = "user_limits"

    ip_address = Column(String, primary_key=True, index=True)
    daily_limit = Column(Integer, nullable=False, default=5)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
