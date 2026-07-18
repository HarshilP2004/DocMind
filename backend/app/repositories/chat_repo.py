from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from app.models.models import ChatSession, ChatMessage

class ChatRepository:
    @staticmethod
    def create_session(db: Session, visitor_id: str, title: str = "New Chat") -> ChatSession:
        db_sess = ChatSession(visitor_id=visitor_id, title=title)
        db.add(db_sess)
        db.commit()
        db.refresh(db_sess)
        return db_sess

    @staticmethod
    def get_session(db: Session, session_id: int) -> Optional[ChatSession]:
        return db.query(ChatSession).filter(ChatSession.id == session_id).first()

    @staticmethod
    def list_sessions_by_visitor(db: Session, visitor_id: str) -> List[ChatSession]:
        return db.query(ChatSession).filter(ChatSession.visitor_id == visitor_id).order_by(ChatSession.created_at.desc()).all()

    @staticmethod
    def delete_session(db: Session, session_id: int) -> bool:
        db_sess = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if db_sess:
            db.delete(db_sess)
            db.commit()
            return True
        return False

    @staticmethod
    def create_message(
        db: Session, 
        session_id: int, 
        role: str, 
        content: str, 
        citations: Optional[List[Dict[str, Any]]] = None,
        ip_address: Optional[str] = None
    ) -> ChatMessage:
        db_msg = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            citations=citations or [],
            ip_address=ip_address
        )
        db.add(db_msg)
        db.commit()
        db.refresh(db_msg)
        return db_msg

    @staticmethod
    def get_messages_by_session(db: Session, session_id: int) -> List[ChatMessage]:
        return db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at.asc()).all()

chat_repo = ChatRepository()
