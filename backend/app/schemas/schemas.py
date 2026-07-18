from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

# --- Auth Schemas ---
class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)

class UserResponse(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None


# --- Document Schemas ---
class DocumentResponse(BaseModel):
    id: int
    filename: str
    file_type: str
    status: str
    ocr_used: bool
    total_chunks: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentMetadataResponse(BaseModel):
    document_id: int
    doc_type: str
    extracted_data: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True


# --- Chat & RAG Schemas ---
class CitationSchema(BaseModel):
    document_name: str
    page_number: Optional[int] = None
    content: str


class ChatMessageCreate(BaseModel):
    content: str


class ChatMessageResponse(BaseModel):
    id: int
    role: str
    content: str
    citations: Optional[List[CitationSchema]] = []
    created_at: datetime

    class Config:
        from_attributes = True


class ChatSessionCreate(BaseModel):
    title: Optional[str] = "New Chat"


class ChatSessionResponse(BaseModel):
    id: int
    title: str
    created_at: datetime

    class Config:
        from_attributes = True


class QueryRequest(BaseModel):
    query: str
    session_id: Optional[int] = None
