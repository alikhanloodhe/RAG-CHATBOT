import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import Auth from './components/Auth';
import { API_BASE_URL } from './config';

interface User {
  id: number;
  username: string;
}

interface AuthSession {
  access_token: string;
  token_type: 'bearer';
  user: User;
}

interface UserDocument {
  id: number;
  filename: string;
  content_type: string;
  size_bytes: number;
  uploaded_at: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  vector_count: number;
}

interface Message {
  id: string;
  sender: 'user' | 'bot';
  text: string;
  latency?: {
    total: string;
    llm: string;
    vector: string;
  };
  citations?: Citation[];
  cacheHit?: boolean;
}

interface Citation {
  source_id: string;
  score?: number | null;
  filename: string;
  chunk_index: number;
  text: string;
}

interface QueryResponse {
  answer: string;
  citations: Citation[];
  timings: {
    retrieval_ms: number;
    generation_ms: number;
    total_ms: number;
  };
  cache_hit: boolean;
}

/**
 * App Root Component
 * Handles global session management, document upload zones, listing user documents,
 * sending user prompts to the backend query pipeline, and displaying cited chat logs.
 */
function App() {
  // Session authentication state (persisted in localStorage)
  const [authSession, setAuthSession] = useState<AuthSession | null>(() => {
    const saved = localStorage.getItem('rag_auth');
    return saved ? JSON.parse(saved) : null;
  });
  const user = authSession?.user ?? null;

  // Global application states
  const [apiStatus, setApiStatus] = useState<'connected' | 'offline'>('offline');
  const [documents, setDocuments] = useState<UserDocument[]>([]);
  const [query, setQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadingFiles, setUploadingFiles] = useState<{ name: string; size: number }[]>([]);
  
  // Chat dialogue session history
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      sender: 'bot',
      text: 'Hello! I am your RAG chatbot assistant. Ask me questions grounded in your uploaded documents, and I will synthesize responses with precise sources.',
    }
  ]);

  const [notification, setNotification] = useState<{ type: 'success' | 'error' | 'info'; text: string } | null>(null);
  
  const fileInputRef = useRef<HTMLInputElement>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);

  // Memoized authorization header configuration
  const authHeaders = useMemo(() => {
    return authSession
      ? { Authorization: `Bearer ${authSession.access_token}` }
      : undefined;
  }, [authSession]);

  /** Formats standard runtime error logs for presentation */
  const getErrorMessage = (err: unknown) => {
    return err instanceof Error ? err.message : String(err);
  };

  /** Handles user logout session cleanup */
  const handleLogout = useCallback(() => {
    setAuthSession(null);
    setDocuments([]);
    localStorage.removeItem('rag_auth');
    setMessages([
      {
        id: 'welcome',
        sender: 'bot',
        text: 'Hello! I am your RAG chatbot assistant. Ask me questions grounded in your uploaded documents, and I will synthesize responses with precise sources.',
      }
    ]);
  }, []);

  // Poll API health
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/health`);
        if (response.ok) {
          const data = await response.json();
          if (data.status === 'ok') {
            setApiStatus('connected');
            return;
          }
        }
        setApiStatus('offline');
      } catch {
        setApiStatus('offline');
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 5000);
    return () => clearInterval(interval);
  }, []);

  // Fetch documents for the logged in user
  const fetchDocuments = useCallback(async () => {
    if (!authSession || apiStatus !== 'connected') return;
    try {
      const response = await fetch(`${API_BASE_URL}/documents/`, {
        headers: authHeaders,
      });
      if (response.ok) {
        const data = await response.json();
        setDocuments(data);
      } else if (response.status === 401) {
        handleLogout();
      }
    } catch (err) {
      console.error('Error fetching documents:', err);
    }
  }, [apiStatus, authHeaders, authSession, handleLogout]);

  // Poll documents when api is connected and user is logged in
  useEffect(() => {
    if (user && apiStatus === 'connected') {
      const initialFetch = setTimeout(fetchDocuments, 0);
      const interval = setInterval(fetchDocuments, 3000);
      return () => {
        clearTimeout(initialFetch);
        clearInterval(interval);
      };
    }
  }, [user, apiStatus, fetchDocuments]);

  // Scroll to bottom when messages update
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isSearching]);

  const showNotification = (type: 'success' | 'error' | 'info', text: string) => {
    setNotification({ type, text });
    setTimeout(() => setNotification(null), 5000);
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files || files.length === 0 || !user) return;

    setIsUploading(true);
    const filesList = Array.from(files).map((f) => ({ name: f.name, size: f.size }));
    setUploadingFiles(filesList);
    showNotification('info', `Uploading ${files.length} file(s)...`);

    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
      formData.append('files', files[i]);
    }

    try {
      const response = await fetch(`${API_BASE_URL}/documents/upload`, {
        method: 'POST',
        headers: authHeaders,
        body: formData,
      });

      if (response.ok) {
        showNotification('success', `Successfully uploaded ${files.length} file(s). Ingestion started.`);
        fetchDocuments();
      } else {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || 'Upload failed');
      }
    } catch (err: unknown) {
      showNotification('error', `Upload error: ${getErrorMessage(err)}`);
    } finally {
      setIsUploading(false);
      setUploadingFiles([]);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleDeleteDocument = async (id: number) => {
    if (!user || apiStatus !== 'connected') {
      showNotification('error', 'Cannot delete files in offline mode.');
      return;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/documents/${id}`, {
        method: 'DELETE',
        headers: authHeaders,
      });

      if (response.ok) {
        showNotification('success', 'Document deleted successfully.');
        fetchDocuments();
      } else {
        throw new Error('Delete request failed');
      }
    } catch (err: unknown) {
      showNotification('error', `Delete error: ${getErrorMessage(err)}`);
    }
  };

  const triggerFileDialog = () => {
    fileInputRef.current?.click();
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || !user) return;

    const queryText = query;
    setQuery('');
    
    // Add user query to chat feed
    const userMsgId = Date.now().toString();
    setMessages((prev) => [
      ...prev,
      { id: userMsgId, sender: 'user', text: queryText }
    ]);

    setIsSearching(true);
    if (apiStatus === 'connected') {
      try {
        const res = await fetch(`${API_BASE_URL}/documents/query`, {
          method: 'POST',
          headers: {
            ...authHeaders,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ query: queryText }),
        });

        if (res.ok) {
          const data: QueryResponse = await res.json();

          setMessages((prev) => [
            ...prev,
            {
              id: (Date.now() + 1).toString(),
              sender: 'bot',
              text: data.answer,
              latency: {
                total: `${data.timings.total_ms}ms`,
                llm: `${data.timings.generation_ms}ms`,
                vector: `${data.timings.retrieval_ms}ms`
              },
              citations: data.citations,
              cacheHit: data.cache_hit
            }
          ]);
        } else {
          throw new Error('Query generation failed');
        }
      } catch (err) {
        console.error(err);
        setMessages((prev) => [
          ...prev,
          { id: Date.now().toString(), sender: 'bot', text: 'Error: Failed to fetch synthesized response from backend.' }
        ]);
      } finally {
        setIsSearching(false);
      }
    } else {
      // Offline mock fallback simulation
      setTimeout(() => {
        setIsSearching(false);
        const total = Math.floor(Math.random() * 200) + 150;
        setMessages((prev) => [
          ...prev,
          {
            id: Date.now().toString(),
            sender: 'bot',
            text: `Offline query response: Embeddings for "${queryText}" require backend. Please boot the FastAPI server to process your request.`,
            latency: {
              total: `${total}ms`,
              llm: `${Math.round(total * 0.8)}ms`,
              vector: `${Math.round(total * 0.15)}ms`
            }
          }
        ]);
      }, 800);
    }
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  const formatCitationTitle = (citation: Citation) => {
    return `${citation.filename} - chunk ${citation.chunk_index}\n\n${citation.text}`;
  };

  const formatScore = (score?: number | null) => {
    return typeof score === 'number' ? `${Math.round(score * 100)}% match` : 'retrieved source';
  };

  if (!user) {
    return <Auth onAuthSuccess={(session) => { setAuthSession(session); localStorage.setItem('rag_auth', JSON.stringify(session)); }} />;
  }

  return (
    <div className="app-container">
      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        multiple
        style={{ display: 'none' }}
        onChange={handleFileUpload}
        accept=".txt,.md,.pdf,.csv,.json"
      />

      {/* Notification Banner */}
      {notification && (
        <div
          id="toast-notification"
          style={{
            background: notification.type === 'success' ? 'var(--status-ok-glow)' : notification.type === 'error' ? 'var(--status-err-glow)' : 'var(--primary-glow)',
            color: notification.type === 'success' ? 'var(--status-ok)' : notification.type === 'error' ? 'var(--status-err)' : 'var(--primary)',
            border: `1px solid ${notification.type === 'success' ? 'var(--status-ok)' : notification.type === 'error' ? 'var(--status-err)' : 'var(--primary)'}`,
            padding: '0.75rem 1rem',
            borderRadius: '8px',
            fontSize: '0.85rem',
            fontWeight: 500,
          }}
        >
          {notification.text}
        </div>
      )}

      {/* Sidebar Panel */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="sidebar-logo">R</div>
          <div>
            <h1 className="sidebar-title">RAG Chatbot</h1>
            <div className="sidebar-subtitle">Grounded Knowledge Console</div>
          </div>
        </div>

        <div className="sidebar-section">
          <div>
            <div className="sidebar-heading">Document Ingestion</div>
            <div
              className="upload-zone"
              onClick={triggerFileDialog}
              style={{ pointerEvents: isUploading ? 'none' : 'auto' }}
            >
              📤 {isUploading ? 'Uploading...' : 'Upload Data Files'}
            </div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '0.4rem', textAlign: 'center', lineHeight: 1.4 }}>
              PDF, TXT, MD, CSV, JSON (Limit: 200MB)
            </div>
          </div>

          <div>
            <div className="sidebar-heading">Registry ({documents.length + uploadingFiles.length})</div>
            <div className="doc-list">
              {uploadingFiles.map((file, idx) => (
                <div key={`uploading-${idx}-${file.name}`} className="doc-item" style={{ opacity: 0.85 }}>
                  <div className="doc-info">
                    <div className="doc-name" title={file.name}>{file.name}</div>
                    <div className="doc-meta">
                      {formatBytes(file.size)} • uploading...
                    </div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span className="doc-status-badge pending" style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                      <span className="spinner"></span> upload
                    </span>
                  </div>
                </div>
              ))}
              {documents.map((doc) => (
                <div key={doc.id} className="doc-item">
                  <div className="doc-info">
                    <div className="doc-name" title={doc.filename}>{doc.filename}</div>
                    <div className="doc-meta">
                      {formatBytes(doc.size_bytes)} • {doc.vector_count > 0 ? `${doc.vector_count} vectors` : 'no vectors'}
                    </div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span className={`doc-status-badge ${doc.status}`} style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                      {(doc.status === 'pending' || doc.status === 'processing') && (
                        <span className="spinner" style={{ borderTopColor: doc.status === 'processing' ? 'var(--primary)' : 'var(--status-warn)' }}></span>
                      )}
                      {doc.status === 'completed' ? 'ready' : doc.status}
                    </span>
                    <button
                      onClick={() => handleDeleteDocument(doc.id)}
                      className="btn-secondary"
                      style={{ padding: '0.2rem 0.4rem', border: 'none', background: 'transparent', color: 'var(--status-err)', fontSize: '0.85rem' }}
                      title="Delete document"
                    >
                      🗑️
                    </button>
                  </div>
                </div>
              ))}
              {documents.length === 0 && uploadingFiles.length === 0 && (
                <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem', textAlign: 'center', padding: '1rem' }}>
                  No documents uploaded yet.
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="sidebar-footer">
          <div className="user-profile">
            <div className="user-avatar">{user.username.substring(0, 2).toUpperCase()}</div>
            <div className="user-details">
              <span className="user-name">{user.username}</span>
              <span className="user-role">ID: #{user.id}</span>
            </div>
          </div>
          <button onClick={handleLogout} className="btn-secondary btn-logout">
            🚪 Log Out
          </button>
        </div>
      </aside>

      {/* Main Chat Area */}
      <main className="main-chat-container">
        <header className="chat-header">
          <div className="chat-header-info">
            <div className="dot connected"></div>
            <div className="chat-header-title">Grounded AI Chat Assistant</div>
          </div>
          <div style={{ fontSize: '0.8rem', color: apiStatus === 'connected' ? 'var(--status-ok)' : 'var(--text-muted)' }}>
            ● API {apiStatus.toUpperCase()}
          </div>
        </header>

        {/* Scrollable Chat feed */}
        <div className="chat-feed">
          {messages.map((msg) => (
            <div key={msg.id} className={`message-wrapper ${msg.sender}`}>
              <div className="message-bubble">
                <p style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
                  {msg.text}
                </p>

                {msg.citations && msg.citations.length > 0 && (
                  <details className="citation-dropdown">
                    <summary>
                      Sources ({msg.citations.length})
                    </summary>
                    <div className="citation-list">
                      {msg.citations.map((citation, index) => (
                        <article key={citation.source_id} className="citation-source">
                          <div className="citation-source-header">
                            <span className="citation-tag" title={formatCitationTitle(citation)}>
                              [{index + 1}] {citation.filename} #{citation.chunk_index}
                            </span>
                            <span className="citation-score">{formatScore(citation.score)}</span>
                          </div>
                          <p>{citation.text}</p>
                        </article>
                      ))}
                    </div>
                  </details>
                )}
                
                {msg.latency && (
                  <div className="latency-timeline">
                    <span className="latency-item">⏱️ Total: <span className="time-value">{msg.latency.total}</span></span>
                    <span className="latency-item">🤖 LLM: <span className="time-value">{msg.latency.llm}</span></span>
                    <span className="latency-item">🛰️ Vector: <span className="time-value">{msg.latency.vector}</span></span>
                    {msg.cacheHit && <span className="latency-item">Cache: <span className="time-value">hit</span></span>}
                  </div>
                )}
              </div>
            </div>
          ))}
          
          {isSearching && (
            <div className="message-wrapper bot">
              <div className="message-bubble" style={{ color: 'var(--text-muted)' }}>
                🔍 Searching index & generating grounded response...
              </div>
            </div>
          )}
          
          <div ref={chatEndRef} />
        </div>

        {/* Absolute bottom chat input deck */}
        <div className="chat-input-bar">
          <form onSubmit={handleSearch} className="chat-input-wrapper">
            <input
              type="text"
              placeholder="Ask a question grounded in your document registry..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              disabled={isSearching}
            />
            <button
              type="submit"
              className="btn-primary"
              style={{ borderRadius: '10px', padding: '0.6rem 1.2rem' }}
              disabled={isSearching || !query.trim()}
            >
              Send
            </button>
          </form>
        </div>
      </main>
    </div>
  );
}

export default App;
