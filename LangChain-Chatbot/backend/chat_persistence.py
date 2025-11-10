# backend/chat_persistence.py
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from database import ChatSession, ChatMessage, User

class ChatPersistenceManager:
    """Manager for chat persistence using database."""
    
    def __init__(self):
        pass
    
    def create_session(self, db: Session, user: User, title: str = "New Chat") -> ChatSession:
        """Create a new chat session."""
        session = ChatSession(
            user_id=user.id,
            title=title
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return session
    
    def save_message(self, db: Session, session_id: int, role: str, content: str) -> ChatMessage:
        """Save a message to the database."""
        message = ChatMessage(
            session_id=session_id,
            role=role,
            content=content
        )
        db.add(message)
        db.commit()
        db.refresh(message)
        return message
    
    def get_session_messages(self, db: Session, session_id: int) -> List[ChatMessage]:
        """Get all messages for a chat session."""
        return db.query(ChatMessage).filter(
            ChatMessage.session_id == session_id
        ).order_by(ChatMessage.timestamp).all()
    
    def get_user_sessions(self, db: Session, user_id: int) -> List[ChatSession]:
        """Get all chat sessions for a user."""
        return db.query(ChatSession).filter(
            ChatSession.user_id == user_id
        ).order_by(ChatSession.updated_at.desc()).all()
    
    def update_session_title(self, db: Session, session_id: int, title: str):
        """Update the title of a chat session."""
        session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if session:
            session.title = title
            session.updated_at = datetime.utcnow()
            db.commit()
    
    def delete_session(self, db: Session, session_id: int, user_id: int):
        """Delete a chat session (only if user owns it)."""
        session = db.query(ChatSession).filter(
            ChatSession.id == session_id,
            ChatSession.user_id == user_id
        ).first()
        if session:
            db.delete(session)
            db.commit()
            return True
        return False
    
    def format_messages_for_llm(self, messages: List[ChatMessage]) -> str:
        """Format messages for LLM context."""
        formatted = []
        for msg in messages:
            role = "User" if msg.role == "user" else "Assistant"
            formatted.append(f"{role}: {msg.content}")
        return "\n\n".join(formatted)
    
    def get_recent_context(self, db: Session, session_id: int, limit: int = 10) -> str:
        """Get recent messages for context (excluding the current query)."""
        messages = db.query(ChatMessage).filter(
            ChatMessage.session_id == session_id
        ).order_by(ChatMessage.timestamp.desc()).limit(limit).all()
        
        # Reverse to get chronological order
        messages.reverse()
        return self.format_messages_for_llm(messages)

# Global instance
chat_manager = ChatPersistenceManager()
