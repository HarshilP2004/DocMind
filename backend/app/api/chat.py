from fastapi import APIRouter, Depends, HTTPException, status, Header, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Generator
from datetime import datetime
import json

from app.db.session import get_db, SessionLocal
from app.models.models import ChatSession, ChatMessage, UserLimit
from app.repositories.chat_repo import chat_repo
from app.schemas.schemas import ChatSessionCreate, ChatSessionResponse, ChatMessageResponse, QueryRequest
from app.services.rag.rag_service import rag_service

router = APIRouter()

# Dependency to extract anonymous visitor ID from the request header
def get_visitor_id(x_visitor_id: Optional[str] = Header(None, alias="X-Visitor-ID")) -> str:
    return x_visitor_id or "default_visitor"

# Utility to resolve client IP with support for standard reverse proxy headers
def get_client_ip(request: Request) -> str:
    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    x_real_ip = request.headers.get("X-Real-IP")
    if x_real_ip:
        return x_real_ip.strip()
    return request.client.host if request.client else "127.0.0.1"


@router.post("/sessions", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(
    session_in: ChatSessionCreate,
    db: Session = Depends(get_db),
    visitor_id: str = Depends(get_visitor_id)
):
    """
    Create a new chat session.
    """
    return chat_repo.create_session(db, visitor_id=visitor_id, title=session_in.title)


@router.get("/sessions", response_model=List[ChatSessionResponse])
def list_sessions(
    db: Session = Depends(get_db),
    visitor_id: str = Depends(get_visitor_id)
):
    """
    List all chat sessions.
    """
    return chat_repo.list_sessions_by_visitor(db, visitor_id=visitor_id)


@router.get("/sessions/{session_id}/messages", response_model=List[ChatMessageResponse])
def get_session_messages(
    session_id: int,
    db: Session = Depends(get_db),
    visitor_id: str = Depends(get_visitor_id)
):
    """
    Get messages for a chat session.
    """
    sess = chat_repo.get_session(db, session_id)
    if not sess or sess.visitor_id != visitor_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found."
        )
    return chat_repo.get_messages_by_session(db, session_id=session_id)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_200_OK)
def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
    visitor_id: str = Depends(get_visitor_id)
):
    """
    Delete a chat session.
    """
    sess = chat_repo.get_session(db, session_id)
    if not sess or sess.visitor_id != visitor_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found."
        )
    chat_repo.delete_session(db, session_id=session_id)
    return {"detail": "Chat session successfully deleted"}


@router.get("/limit-status")
def get_limit_status(
    fastapi_request: Request,
    db: Session = Depends(get_db)
):
    """
    Get the remaining chat query limit status for the client IP.
    """
    client_ip = get_client_ip(fastapi_request)
    limit_row = db.query(UserLimit).filter(UserLimit.ip_address == client_ip).first()
    daily_limit = limit_row.daily_limit if limit_row else 5
    
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    message_count = db.query(ChatMessage).filter(
        ChatMessage.ip_address == client_ip,
        ChatMessage.role == "user",
        ChatMessage.created_at >= today_start
    ).count()
    
    return {
        "limit": daily_limit,
        "used": message_count,
        "remaining": max(0, daily_limit - message_count)
    }


@router.post("/query")
def chat_query(
    request: QueryRequest,
    fastapi_request: Request,
    db: Session = Depends(get_db),
    visitor_id: str = Depends(get_visitor_id)
):
    """
    Ask a question over uploaded documents. Enforces a daily rate limit of 5 messages per IP.
    Returns an SSE streaming response.
    """
    client_ip = get_client_ip(fastapi_request)
    
    # 1. Enforce Daily Limit (resets automatically at midnight UTC)
    limit_row = db.query(UserLimit).filter(UserLimit.ip_address == client_ip).first()
    daily_limit = limit_row.daily_limit if limit_row else 5
    
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    message_count = db.query(ChatMessage).filter(
        ChatMessage.ip_address == client_ip,
        ChatMessage.role == "user",
        ChatMessage.created_at >= today_start
    ).count()
    
    if message_count >= daily_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Daily query limit reached. You can only send {daily_limit} messages per day."
        )

    # 2. Resolve or create chat session
    sess_id = request.session_id
    if not sess_id:
        title = request.query[:30] + "..." if len(request.query) > 30 else request.query
        db_sess = chat_repo.create_session(db, visitor_id=visitor_id, title=title)
        sess_id = db_sess.id
    else:
        db_sess = chat_repo.get_session(db, sess_id)
        if not db_sess or db_sess.visitor_id != visitor_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found."
            )

    # Save user query to DB with IP address
    chat_repo.create_message(
        db, 
        session_id=sess_id, 
        role="user", 
        content=request.query, 
        ip_address=client_ip
    )

    # 3. SSE stream wrapper that saves response upon completion
    def stream_wrapper() -> Generator[str, None, None]:
        bg_db = SessionLocal()
        collected_tokens = []
        citations_metadata = []
        
        generator = rag_service.generate_streaming_response(
            bg_db, 
            visitor_id=visitor_id, 
            query=request.query, 
            session_id=sess_id
        )
        
        try:
            for event in generator:
                yield event
                
                # Parse event details for DB storage
                if event.startswith("event: citations\ndata: "):
                    try:
                        citations_str = event.replace("event: citations\ndata: ", "").strip()
                        citations_metadata = json.loads(citations_str)
                    except Exception:
                        pass
                elif event.startswith("event: token\ndata: "):
                    try:
                        token_data_str = event.replace("event: token\ndata: ", "").strip()
                        token_json = json.loads(token_data_str)
                        collected_tokens.append(token_json.get("token", ""))
                    except Exception:
                        pass
                        
            # Once stream is complete, write assistant message to DB
            full_response = "".join(collected_tokens)
            chat_repo.create_message(
                bg_db, 
                session_id=sess_id, 
                role="assistant", 
                content=full_response, 
                citations=citations_metadata,
                ip_address=client_ip
            )
        except Exception as e:
            print(f"Error in stream wrapper database logging: {e}")
        finally:
            bg_db.close()

    return StreamingResponse(
        stream_wrapper(), 
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
