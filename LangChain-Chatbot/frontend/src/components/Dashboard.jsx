import React, { useState } from 'react';
import { useAuth } from '../AuthContext';
import ChatSidebar from './ChatSidebar';
import Chat from './Chat';
import './Dashboard.css';

export default function Dashboard() {
  const { user, logout } = useAuth();
  const [currentSessionId, setCurrentSessionId] = useState(null);

  const handleSessionSelect = (sessionId) => {
    setCurrentSessionId(sessionId);
  };

  const handleNewChat = () => {
    setCurrentSessionId(null);
  };

  const handleSessionCreated = (sessionId) => {
    setCurrentSessionId(sessionId);
  };

  return (
    <div className="dashboard">
      <ChatSidebar
        currentSessionId={currentSessionId}
        onSessionSelect={handleSessionSelect}
        onNewChat={handleNewChat}
      />
      <div className="main-content">
        <div className="header">
          <h1>AI Assistant</h1>
          <div className="user-info">
            <span className="user-email">{user.email}</span>
            <button onClick={logout} className="logout-button">
              Logout
            </button>
          </div>
        </div>
        <Chat
          sessionId={currentSessionId}
          onSessionCreated={handleSessionCreated}
        />
      </div>
    </div>
  );
}
