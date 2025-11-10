import React, { useEffect, useMemo, useRef, useState } from "react";
import { chatAPI } from "../api";
import "./Chat.css";

export default function Chat({ sessionId, onSessionCreated }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [currentSessionId, setCurrentSessionId] = useState(sessionId);
  const endRef = useRef(null);
  const textareaRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  useEffect(() => {
    if (sessionId) {
      loadSessionMessages(sessionId);
      setCurrentSessionId(sessionId);
    } else {
      setMessages([]);
      setCurrentSessionId(null);
    }
  }, [sessionId]);

  const loadSessionMessages = async (sessionId) => {
    try {
      const messages = await chatAPI.getSessionMessages(sessionId);
      setMessages(messages.map(msg => ({
        id: msg.id,
        from: msg.role,
        text: msg.content,
        timestamp: msg.timestamp
      })));
    } catch (error) {
      console.error('Failed to load session messages:', error);
      setError('Failed to load chat history');
    }
  };

  const canSend = useMemo(() => input.trim().length > 0 && !isLoading, [input, isLoading]);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!canSend) return;
    
    setError("");
    const userText = input.trim();
    const userMsg = { 
      id: Date.now(), 
      from: "user", 
      text: userText,
      timestamp: new Date().toISOString()
    };
    
    setMessages(prev => [...prev, userMsg]);
    setInput("");
    setIsLoading(true);
    
    try {
      const res = await chatAPI.sendMessage(userText, currentSessionId);
      
      // Update current session ID if this was a new session
      if (!currentSessionId && res.session_id) {
        setCurrentSessionId(res.session_id);
        onSessionCreated(res.session_id);
      }
      
      const assistantMsg = {
        id: Date.now() + 1,
        from: "assistant",
        text: res?.reply ?? "",
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, assistantMsg]);
    } catch (err) {
      console.error(err);
      setError("Failed to get response. Ensure backend and Ollama are running.");
    } finally {
      setIsLoading(false);
      textareaRef.current?.focus();
    }
  }

  function onKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (canSend) handleSubmit(e);
    }
  }

  return (
    <div className="chat-container">
      <div className="chat-main">
        <div className="messages">
          {messages.length === 0 ? (
            <div className="welcome-message">
              <h2>Welcome to your AI Assistant</h2>
              <p>Ask me anything about the company FAQ document!</p>
            </div>
          ) : (
            messages.map(m => (
              <MessageBubble key={m.id} message={m} />
            ))
          )}
          {isLoading && <TypingIndicator />}
          <div ref={endRef} />
        </div>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <form onSubmit={handleSubmit} className="composer">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="Message"
          rows={1}
        />
        <button type="submit" disabled={!canSend}>Send</button>
      </form>
    </div>
  );
}

function MessageBubble({ message }) {
  const isUser = message.from === "user";
  return (
    <div className={`message ${isUser ? "user" : "assistant"}`}>
      <div className="avatar">{isUser ? "🧑" : "🤖"}</div>
      <div className="bubble">
        <div>{message.text}</div>
      </div>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="message assistant">
      <div className="avatar">🤖</div>
      <div className="bubble typing">
        <span className="dot" />
        <span className="dot" />
        <span className="dot" />
      </div>
    </div>
  );
}
