# Company FAQ Chatbot (RAG, Ollama, FastAPI, React)

A local, privacy-friendly FAQ chatbot with user authentication and chat persistence. Answers strictly from your PDF knowledge base using RAG (FAISS + sentence-transformers) and a free local LLM served by Ollama. Features a modern React UI with chat history management.

## Features
- **User Authentication**: Email/password registration and login with JWT tokens
- **Chat Persistence**: Save and resume previous conversations using LangGraph
- **Retrieval-augmented generation** over a PDF (`backend/data/company_faq.pdf`)
- **Local LLM** via Ollama (no API keys required)
- **FastAPI backend** with authentication, health, and debug endpoints
- **Modern React UI** with chat history sidebar and session management
- **SQLite database** for user management and chat storage

## Stack
- **Backend**: Python, FastAPI, SQLAlchemy, FAISS, sentence-transformers, pypdf, LangGraph
- **Authentication**: JWT tokens, bcrypt password hashing
- **Database**: SQLite for user management and chat persistence
- **LLM Runtime**: Ollama (default `llama3.1:8b`, configurable via `OLLAMA_MODEL`)
- **Frontend**: React with React Router, Axios for API calls

## Prerequisites
- macOS (or Linux) with Homebrew recommended
- Node 18+ and npm
- Python 3.10+ (virtualenv recommended)
- Ollama

Install Ollama and pull a small free model:
```bash
brew install ollama
brew services start ollama   # or: ollama serve
ollama pull llama3.2:3b      # small and fast; default in this project
```

## Quickstart
1) Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# Optional: choose model (must be pulled in Ollama first)
export OLLAMA_MODEL=llama3.2:3b
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

Health checks:
```bash
curl -s http://localhost:8000/api/health
curl -s http://localhost:8000/api/debug_model
```

2) Frontend
```bash
cd frontend
npm install
# If port 3000 is busy (e.g., Grafana), run on another port:
PORT=3002 npm start
```
Open the app at:
- http://localhost:3000 or
- http://localhost:3002 (if you chose the alternate port)

## How it works
- **Authentication**: Users register/login with email and password. JWT tokens provide secure session management.
- **Chat Persistence**: Each conversation is saved as a session with individual messages stored in SQLite.
- **RAG Pipeline**: At backend startup, `loader.py` loads or builds a FAISS index from `backend/data/company_faq.pdf` using `all-MiniLM-L6-v2` embeddings.
- **Context-Aware Responses**: On each chat request, we retrieve top-k relevant chunks from the PDF and include recent conversation history.
- **Constrained Generation**: The LLM answers strictly from the retrieved context and conversation history; if nothing matches, it replies: "Sorry, I don't have that information."

## Configuration
Environment variables (optional):
- `PDF_PATH` – path to the PDF (default: `data/company_faq.pdf`)
- `OLLAMA_MODEL` – Ollama model name/tag (default: `llama3.2:3b`)

Change PDF and rebuild index:
```bash
# Replace the file
cp /path/to/your.pdf backend/data/company_faq.pdf
# Remove old index so it rebuilds next start
rm -f backend/faiss_index.faiss backend/texts.pkl
# Restart backend (it will rebuild automatically)
```

## API

### Authentication
- `POST /api/register` → Register new user with email/password
- `POST /api/login` → Login user, returns JWT token
- `GET /api/me` → Get current user info (requires authentication)

### Chat Management
- `GET /api/chat/sessions` → Get all chat sessions for current user
- `POST /api/chat/sessions` → Create new chat session
- `GET /api/chat/sessions/{id}/messages` → Get messages for a session
- `DELETE /api/chat/sessions/{id}` → Delete a chat session

### Chat
- `POST /api/chat` body:
```json
{
  "user": "Your question",
  "top_k": 3,
  "session_id": 123
}
```
Response:
```json
{
  "reply": "Answer strictly from the PDF context.",
  "sources_used": ["..."],
  "session_id": 123
}
```

### System
- `GET /api/health` → `{ status, ollama, model }`
- `GET /api/debug_model` → tries a tiny generation, returns `{ ok, model, output }` or an error

Note: All chat endpoints require authentication via JWT token in Authorization header.

## Troubleshooting
- Ollama not found: install/start Ollama and pull the model.
  ```bash
  brew install ollama && brew services start ollama
  ollama pull llama3.2:3b
  ```
- Backend error: check `GET /api/debug_model` and ensure `OLLAMA_MODEL` is pulled.
- Port 3000 shows Grafana: run the frontend on another port, e.g. `PORT=3002 npm start`.
- No answers: ensure the PDF has extractable text and the index was built (delete old index files to rebuild).

## Project structure
```
LangChain-Chatbot/
  backend/
    app.py                 # FastAPI app with auth and chat endpoints
    auth.py                # JWT authentication and password hashing
    database.py            # SQLAlchemy models and database setup
    chat_persistence.py    # LangGraph-based chat persistence
    loader.py              # PDF reading, embeddings, FAISS index
    data/company_faq.pdf   # Your knowledge base (replaceable)
    requirements.txt
    faiss_index.faiss      # Built at runtime
    texts.pkl              # Stored page texts
    chatbot.db             # SQLite database (created at runtime)
  frontend/
    src/
      App.jsx              # Main app with routing
      AuthContext.js       # Authentication context provider
      api.js               # API calls with auth headers
      components/
        Login.jsx          # Login form
        Register.jsx       # Registration form
        Dashboard.jsx      # Main chat interface
        Chat.jsx           # Chat component with persistence
        ChatSidebar.jsx    # Chat history sidebar
        Auth.css           # Authentication styles
        Chat.css           # Chat interface styles
        Dashboard.css      # Dashboard layout styles
        ChatSidebar.css    # Sidebar styles
    public/index.html
    package.json
```

## Notes
- All models run locally; no tokens required.
- You can swap to another Ollama model (e.g., `qwen2.5:3b`) by pulling it and updating `OLLAMA_MODEL`.
- **Security**: Change the `SECRET_KEY` in production for JWT token security.
- **Database**: SQLite database is created automatically on first run.
- **Chat History**: All conversations are persisted and can be resumed across sessions.

## First Time Setup
1. Install dependencies and start Ollama
2. Start the backend server
3. Start the frontend
4. Register a new account or login
5. Start chatting with your AI assistant!

---
Enjoy your local, private, authenticated RAG chatbot with persistent chat history!
