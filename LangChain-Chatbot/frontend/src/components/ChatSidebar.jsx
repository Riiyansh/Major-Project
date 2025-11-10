import React, { useState, useEffect } from 'react';
import { chatAPI } from '../api';
import './ChatSidebar.css';

export default function ChatSidebar({ currentSessionId, onSessionSelect, onNewChat }) {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadSessions();
  }, []);

  const loadSessions = async () => {
    try {
      const data = await chatAPI.getSessions();
      setSessions(data);
    } catch (error) {
      console.error('Failed to load sessions:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteSession = async (sessionId, e) => {
    e.stopPropagation();
    if (window.confirm('Are you sure you want to delete this chat?')) {
      try {
        await chatAPI.deleteSession(sessionId);
        setSessions(sessions.filter(s => s.id !== sessionId));
        if (currentSessionId === sessionId) {
          onNewChat();
        }
      } catch (error) {
        console.error('Failed to delete session:', error);
        alert('Failed to delete chat session');
      }
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffTime = Math.abs(now - date);
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    
    if (diffDays === 1) return 'Today';
    if (diffDays === 2) return 'Yesterday';
    if (diffDays <= 7) return `${diffDays - 1} days ago`;
    return date.toLocaleDateString();
  };

  if (loading) {
    return (
      <div className="chat-sidebar">
        <div className="sidebar-header">
          <h3>Chat History</h3>
        </div>
        <div className="loading">Loading...</div>
      </div>
    );
  }

  return (
    <div className="chat-sidebar">
      <div className="sidebar-header">
        <h3>Chat History</h3>
        <button onClick={onNewChat} className="new-chat-button">
          + New Chat
        </button>
      </div>
      
      <div className="sessions-list">
        {sessions.length === 0 ? (
          <div className="no-sessions">
            <p>No chat history yet</p>
            <p>Start a new conversation!</p>
          </div>
        ) : (
          sessions.map((session) => (
            <div
              key={session.id}
              className={`session-item ${currentSessionId === session.id ? 'active' : ''}`}
              onClick={() => onSessionSelect(session.id)}
            >
              <div className="session-content">
                <div className="session-title">{session.title}</div>
                <div className="session-date">{formatDate(session.updated_at)}</div>
              </div>
              <button
                className="delete-button"
                onClick={(e) => handleDeleteSession(session.id, e)}
                title="Delete chat"
              >
                ×
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
