# backend/app.py
import os
import traceback
from datetime import timedelta
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import ollama
from loader import build_or_load_index, similarity_search
from database import get_db, create_tables, User, ChatSession
from auth import (
    get_password_hash, authenticate_user, create_access_token, 
    get_current_user, ACCESS_TOKEN_EXPIRE_MINUTES
)
from chat_persistence import chat_manager

# Config
PDF_PATH = os.environ.get("PDF_PATH", "data/company_faq.pdf")  # path to your static PDF
# Default to a small, efficient local model. User can `ollama pull llama3.1:8b` or change via env
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1:8b")

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3002",
        "http://127.0.0.1:3002",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create database tables
create_tables()

# Load / build index at startup
print("Loading or building index...")
index, pages, embed_model = build_or_load_index(PDF_PATH)
if index is None:
    raise RuntimeError("Failed to build/load FAISS index. Make sure the PDF exists at data/company_faq.pdf")
print(f"Index ready. Pages: {len(pages)}")

# Pydantic models
class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class ChatRequest(BaseModel):
    user: str
    top_k: int = 3
    session_id: Optional[int] = None

class ChatSessionCreate(BaseModel):
    title: str = "New Chat"

class ChatSessionResponse(BaseModel):
    id: int
    title: str
    created_at: str
    updated_at: str

# Authentication endpoints
@app.post("/api/register", response_model=Token)
def register(user: UserCreate, db: Session = Depends(get_db)):
    """Register a new user."""
    # Check if user already exists
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user.password)
    db_user = User(email=user.email, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/login", response_model=Token)
def login(user: UserLogin, db: Session = Depends(get_db)):
    """Login user and return access token."""
    authenticated_user = authenticate_user(db, user.email, user.password)
    if not authenticated_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/me")
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    return {"email": current_user.email, "id": current_user.id}

# Chat session endpoints
@app.post("/api/chat/sessions", response_model=ChatSessionResponse)
def create_chat_session(
    session_data: ChatSessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new chat session."""
    session = chat_manager.create_session(db, current_user, session_data.title)
    return ChatSessionResponse(
        id=session.id,
        title=session.title,
        created_at=session.created_at.isoformat(),
        updated_at=session.updated_at.isoformat()
    )

@app.get("/api/chat/sessions")
def get_chat_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all chat sessions for the current user."""
    sessions = chat_manager.get_user_sessions(db, current_user.id)
    return [
        {
            "id": session.id,
            "title": session.title,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat()
        }
        for session in sessions
    ]

@app.get("/api/chat/sessions/{session_id}/messages")
def get_session_messages(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get messages for a specific chat session."""
    # Verify user owns the session
    from database import ChatSession
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    messages = chat_manager.get_session_messages(db, session_id)
    return [
        {
            "id": msg.id,
            "role": msg.role,
            "content": msg.content,
            "timestamp": msg.timestamp.isoformat()
        }
        for msg in messages
    ]

@app.delete("/api/chat/sessions/{session_id}")
def delete_chat_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a chat session."""
    success = chat_manager.delete_session(db, session_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    return {"message": "Session deleted successfully"}

@app.get("/api/health")
def health():
    try:
        # lightweight check: list models to ensure daemon reachable
        _ = ollama.list()
        return {"status": "ok", "ollama": True, "model": OLLAMA_MODEL}
    except Exception:
        return {"status": "degraded", "ollama": False, "model": OLLAMA_MODEL}

@app.get("/api/debug_model")
def debug_model():
    """
    Validate Ollama is running and the target model is available.
    Returns a tiny generation to confirm functionality.
    """
    try:
        # Try a tiny generation first; if it works, we're good
        res = ollama.generate(model=OLLAMA_MODEL, prompt="Say hello in one short sentence.")
        return {"ok": True, "model": OLLAMA_MODEL, "output": res.get("response", "")}
    except Exception as e:
        tb = traceback.format_exc()
        print("DEBUG MODEL ERROR\n", tb)
        # Fallback: also return installed models to help the user diagnose
        try:
            available = ollama.list()
            model_names = [m.get("name") or m.get("model") for m in available.get("models", [])]
        except Exception:
            model_names = []
        raise HTTPException(status_code=500, detail={"error": str(e), "trace": tb, "available_models": model_names})

def format_context(results):
    # Add separators and trim long passages if needed
    return "\n\n---\n\n".join(results)

@app.post("/api/chat")
async def chat(
    req: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        user_msg = req.user.strip()
        if not user_msg:
            return {"reply": "Please send a non-empty question."}

        # Get or create chat session
        session_id = req.session_id
        if not session_id:
            # Create new session for first message
            session = chat_manager.create_session(db, current_user, user_msg[:50] + "..." if len(user_msg) > 50 else user_msg)
            session_id = session.id
        else:
            # Verify user owns the session
            from database import ChatSession
            session = db.query(ChatSession).filter(
                ChatSession.id == session_id,
                ChatSession.user_id == current_user.id
            ).first()
            if not session:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Session not found"
                )

        # Save user message
        chat_manager.save_message(db, session_id, "user", user_msg)

        # Get recent chat history for context
        recent_context = chat_manager.get_recent_context(db, session_id, limit=5)
        
        # Retrieve relevant passages from PDF
        results = similarity_search(index, pages, embed_model, user_msg, top_k=req.top_k)
        context_text = format_context(results) if results else ""
        print("QUERY:", user_msg)
        print("RETRIEVED PAGES:", len(results))
        print("CONTEXT_SNIPPET:", (context_text[:200] + "...") if len(context_text) > 200 else context_text)

        # Build prompt with chat history and PDF context
        prompt_parts = [
            "You are an assistant that answers customer questions strictly using the provided company/document context and recent conversation history.",
            "If the answer cannot be found in the context, reply exactly: \"Sorry, I don't have that information.\"",
            "Be concise and helpful.\n"
        ]
        
        if recent_context:
            prompt_parts.append(f"RECENT CONVERSATION:\n{recent_context}\n")
        
        if context_text:
            prompt_parts.append(f"DOCUMENT CONTEXT:\n{context_text}\n")
        
        prompt_parts.extend([
            f"Question: {user_msg}\n",
            "Answer:"
        ])
        
        prompt = "\n".join(prompt_parts)

        # Call local Ollama model
        try:
            response = ollama.generate(model=OLLAMA_MODEL, prompt=prompt)
            answer = (response.get("response") or "").strip()
        except Exception:
            tb = traceback.format_exc()
            print("OLLAMA CALL ERROR\n", tb)
            raise

        # Save assistant response
        chat_manager.save_message(db, session_id, "assistant", answer)

        # If no context was provided (no retrieved pages), return fallback directly
        if context_text.strip() == "":
            return {
                "reply": "Sorry, I don't have that information.", 
                "sources_used": [],
                "session_id": session_id
            }

        # Return reply and the raw sources used
        return {
            "reply": answer, 
            "sources_used": results,
            "session_id": session_id
        }

    except Exception as e:
        tb = traceback.format_exc()
        # print full traceback to backend console for easy debugging
        print("UNHANDLED CHAT ERROR:\n", tb)
        # return the error to client (safe during dev)
        raise HTTPException(status_code=500, detail={"error": str(e), "trace": tb})


@app.post("/api/chat/stream")
def chat_stream(
    req: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Server-Sent Events streaming endpoint for chat replies."""
    user_msg = (req.user or "").strip()
    if not user_msg:
        raise HTTPException(status_code=400, detail="Empty message")

    # ensure session
    session_id = req.session_id
    if not session_id:
        session = chat_manager.create_session(db, current_user, user_msg[:50] + "..." if len(user_msg) > 50 else user_msg)
        session_id = session.id
    else:
        session = db.query(ChatSession).filter(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id
        ).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

    # Save user message immediately
    chat_manager.save_message(db, session_id, "user", user_msg)

    # Build context
    results = similarity_search(index, pages, embed_model, user_msg, top_k=req.top_k)
    context_text = format_context(results) if results else ""
    recent_context = chat_manager.get_recent_context(db, session_id, limit=5)

    prompt_parts = [
        "You are an assistant that answers customer questions strictly using the provided company/document context and recent conversation history.",
        "If the answer cannot be found in the context, reply exactly: \"Sorry, I don't have that information.\"",
        "Be concise and helpful.\n"
    ]
    if recent_context:
        prompt_parts.append(f"RECENT CONVERSATION:\n{recent_context}\n")
    if context_text:
        prompt_parts.append(f"DOCUMENT CONTEXT:\n{context_text}\n")
    prompt_parts.extend([
        f"Question: {user_msg}\n",
        "Answer:"
    ])
    prompt = "\n".join(prompt_parts)

    def event_generator():
        accumulated = []
        try:
            for chunk in ollama.generate(model=OLLAMA_MODEL, prompt=prompt, stream=True):
                piece = (chunk.get("response") or "")
                if piece:
                    accumulated.append(piece)
                    yield f"data: {piece}\n\n"
            # finalize and persist assistant message
            final_text = "".join(accumulated).strip()
            chat_manager.save_message(db, session_id, "assistant", final_text)
            # send done signal with session id
            yield f"event: done\ndata: {session_id}\n\n"
        except Exception as e:
            err = str(e)
            yield f"event: error\ndata: {err}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
