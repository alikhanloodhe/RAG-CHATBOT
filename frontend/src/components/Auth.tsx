import React, { useState } from 'react';
import { API_BASE_URL } from '../config';

interface User {
  id: number;
  username: string;
}

interface AuthSession {
  access_token: string;
  token_type: 'bearer';
  user: User;
}

interface AuthProps {
  /** Callback triggered on successful login or registration */
  onAuthSuccess: (session: AuthSession) => void;
}

/**
 * Auth Component
 * Renders Login and Register panels. Interacts with the backend authentication routers
 * to obtain JWT bearer sessions, enabling multi-tenant isolation.
 */
export default function Auth({ onAuthSuccess }: AuthProps) {
  const [isLogin, setIsLogin] = useState(true);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  /**
   * Submits registration or login fields to the API.
   * Handles user validation, sets state errors, and triggers successful callbacks on authentication.
   */
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!username.trim() || !password.trim()) {
      setError('Please fill in all fields.');
      return;
    }

    if (!isLogin && password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    setLoading(true);
    const endpoint = isLogin ? 'login' : 'register';

    try {
      const response = await fetch(`${API_BASE_URL}/documents/auth/${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username, password }),
      });

      if (response.ok) {
        const data = await response.json();
        if (!isLogin) {
          setIsLogin(true);
          setPassword('');
          setConfirmPassword('');
          setError(null);
          onAuthSuccess(data);
        } else {
          onAuthSuccess(data);
        }
      } else {
        const errData = await response.json().catch(() => ({}));
        setError(errData.detail || `Authentication failed. Please check your credentials.`);
      }
    } catch (err) {
      console.error(err);
      setError('Connection to authentication server failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-card">
        <div className="auth-header">
          <div className="auth-logo">R</div>
          <h2>{isLogin ? 'Welcome Back' : 'Create Account'}</h2>
          <p>
            {isLogin 
              ? 'Log in to access your isolated knowledge base' 
              : 'Register with a username and password to start indexing documents'}
          </p>
        </div>

        <div className="auth-tabs">
          <button 
            type="button"
            className={isLogin ? 'auth-tab active' : 'auth-tab'} 
            onClick={() => { setIsLogin(true); setError(null); }}
          >
            Login
          </button>
          <button 
            type="button"
            className={!isLogin ? 'auth-tab active' : 'auth-tab'} 
            onClick={() => { setIsLogin(false); setError(null); }}
          >
            Register
          </button>
        </div>

        {error && <div className="auth-error-banner">{error}</div>}

        <form onSubmit={handleSubmit} className="auth-form">
          <div className="form-field">
            <label htmlFor="username">Username</label>
            <input
              id="username"
              type="text"
              placeholder="e.g. alice"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="text-input auth-input"
              disabled={loading}
              required
            />
          </div>

          <div className="form-field">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              placeholder="Enter password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="text-input auth-input"
              disabled={loading}
              required
            />
          </div>

          {!isLogin && (
            <div className="form-field">
              <label htmlFor="confirm-password">Confirm Password</label>
              <input
                id="confirm-password"
                type="password"
                placeholder="Verify password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="text-input auth-input"
                disabled={loading}
                required
              />
            </div>
          )}

          <button type="submit" className="btn-primary auth-submit" disabled={loading}>
            {loading ? 'Processing...' : isLogin ? 'Login' : 'Register Account'}
          </button>
        </form>
      </div>
    </div>
  );
}
