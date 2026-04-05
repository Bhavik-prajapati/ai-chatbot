import { useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

const starterPrompts = [
  'Explain this project structure and suggest improvements.',
  'Write a React login page with glassmorphism styling.',
  'Debug my Python API error and propose a fix.',
  'Summarize this chat into action items.',
];

function formatTime(value) {
  return new Date(value).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
  });
}

function sessionLabel(session) {
  return session?.title || 'New chat';
}

function MessageContent({ content }) {
  async function copyToClipboard(value) {
    try {
      await navigator.clipboard.writeText(value);
    } catch (error) {
      console.error('Copy failed', error);
    }
  }

  return (
    <div className="message-content">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          code(props) {
            const { inline, className, children, ...rest } = props;
            const match = /language-(\w+)/.exec(className || '');
            const code = String(children).replace(/\n$/, '');

            if (inline) {
              return (
                <code className="inline-code" {...rest}>
                  {children}
                </code>
              );
            }

            return (
              <div className="code-block">
                <div className="code-block-top">
                  <span>{match?.[1] || 'code'}</span>
                  <button
                    className="copy-button"
                    onClick={() => copyToClipboard(code)}
                    type="button"
                  >
                    Copy
                  </button>
                </div>
                <pre>
                  <code className={className} {...rest}>
                    {code}
                  </code>
                </pre>
              </div>
            );
          },
        }}
      >
        {content || ''}
      </ReactMarkdown>
    </div>
  );
}

export default function App() {
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [status, setStatus] = useState('Ready');
  const [activity, setActivity] = useState('');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

  useEffect(() => {
    bootstrap();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isStreaming]);

  async function bootstrap() {
    try {
      const sessionsResponse = await fetchJson('/api/sessions');
      const existingSessions = sessionsResponse.sessions || [];
      setSessions(existingSessions);

      if (existingSessions.length > 0) {
        await openSession(existingSessions[0].id);
      }
    } catch (error) {
      setStatus(error.message);
    }
  }

  async function fetchJson(path, options) {
    const response = await fetch(`${API_BASE}${path}`, options);
    if (!response.ok) {
      throw new Error(`Request failed: ${response.status}`);
    }
    return response.json();
  }

  async function createSession() {
    const data = await fetchJson('/api/sessions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    });
    const session = data.session;
    setSessions((current) => [data.session_summary, ...current]);
    setActiveSessionId(session.id);
    setMessages(session.messages || []);
    setSidebarOpen(false);
    return session;
  }

  function startDraftChat() {
    setActiveSessionId(null);
    setMessages([]);
    setStatus('Ready');
    setActivity('');
    setSidebarOpen(false);
  }

  async function openSession(sessionId) {
    const data = await fetchJson(`/api/sessions/${sessionId}`);
    setActiveSessionId(sessionId);
    setMessages(data.session.messages || []);
    setSidebarOpen(false);
  }

  async function deleteCurrentSession(sessionId) {
    await fetchJson(`/api/sessions/${sessionId}`, { method: 'DELETE' });
    const nextSessions = sessions.filter((session) => session.id !== sessionId);
    setSessions(nextSessions);

    if (activeSessionId === sessionId && nextSessions.length > 0) {
      await openSession(nextSessions[0].id);
      return;
    }

    if (activeSessionId === sessionId) {
      setActiveSessionId(null);
      setMessages([]);
    }
  }

  async function renameCurrentSession() {
    const current = sessions.find((session) => session.id === activeSessionId);
    const nextTitle = window.prompt('Rename this session', current?.title || '');
    if (!nextTitle || !activeSessionId) {
      return;
    }

    const data = await fetchJson(`/api/sessions/${activeSessionId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: nextTitle }),
    });

    setSessions((currentSessions) =>
      currentSessions.map((session) =>
        session.id === activeSessionId ? data.session_summary : session,
      ),
    );
  }

  function updateSessionSummary(summary) {
    setSessions((current) => {
      const withoutCurrent = current.filter((item) => item.id !== summary.id);
      return [summary, ...withoutCurrent];
    });
  }

  function applyStreamPayload(payload) {
    if (payload.type === 'meta') {
      updateSessionSummary(payload.session);
      setStatus(`Routed to ${payload.agent}`);
      return;
    }

    if (payload.type === 'status') {
      setStatus(payload.message || 'Working...');
      setActivity(payload.message || '');
      return;
    }

    if (payload.type === 'chunk') {
      setMessages((current) => {
        const next = [...current];
        if (next.length === 0) {
          return current;
        }
        next[next.length - 1] = {
          ...next[next.length - 1],
          content: `${next[next.length - 1].content}${payload.content}`,
        };
        return next;
      });
      return;
    }

    if (payload.type === 'done') {
      setMessages(payload.session.messages || []);
      updateSessionSummary(payload.session_summary);
      setStatus(`Completed with ${payload.agent}`);
      setActivity('');
      setIsStreaming(false);
    }
  }

  async function handleSubmit(event) {
    event.preventDefault();
    const content = input.trim();
    if (!content || isStreaming) {
      return;
    }

    let sessionId = activeSessionId;
    if (!sessionId) {
      const session = await createSession();
      sessionId = session.id;
    }

    const optimisticUser = {
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    };
    const optimisticAssistant = {
      role: 'assistant',
      content: '',
      created_at: new Date().toISOString(),
      streaming: true,
    };

    setMessages((current) => [...current, optimisticUser, optimisticAssistant]);
    setInput('');
    setStatus('Thinking');
    setActivity('');
    setIsStreaming(true);
    resizeTextarea('');

    try {
      const response = await fetch(`${API_BASE}/api/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: content, session_id: sessionId }),
      });

      if (!response.ok || !response.body) {
        throw new Error('Request failed');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) {
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (!line.trim()) {
            continue;
          }

          applyStreamPayload(JSON.parse(line));
        }
      }

      if (buffer.trim()) {
        applyStreamPayload(JSON.parse(buffer));
      }
    } catch (error) {
      setStatus(error.message);
      setActivity('');
      setMessages((current) => current.slice(0, -1));
      setInput(content);
    } finally {
      setIsStreaming(false);
    }
  }

  function resizeTextarea(value) {
    if (!textareaRef.current) {
      return;
    }
    textareaRef.current.style.height = '0px';
    textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 220)}px`;
    if (value === '') {
      textareaRef.current.style.height = '56px';
    }
  }

  function handleInputChange(event) {
    setInput(event.target.value);
    resizeTextarea(event.target.value);
  }

  const activeSession = sessions.find((session) => session.id === activeSessionId);

  return (
    <div className="app-shell">
      <aside className={`sidebar ${sidebarOpen ? 'sidebar-open' : ''}`}>
        <div className="sidebar-top">
          <div>
            <p className="eyebrow">AI Assistant</p>
            <h1>Chat</h1>
          </div>
          <button className="ghost-button" onClick={startDraftChat}>
            New chat
          </button>
        </div>

        <div className="sidebar-section">
          <p className="section-label">History</p>
          <div className="session-list">
            {sessions.map((session) => (
              <div
                key={session.id}
                className={`session-card ${
                  session.id === activeSessionId ? 'active-session' : ''
                }`}
              >
                <button className="session-main" onClick={() => openSession(session.id)}>
                  <span className="session-title">{sessionLabel(session)}</span>
                  <span className="session-preview">{session.preview || 'Open chat'}</span>
                </button>
                <button
                  className="session-delete"
                  onClick={() => deleteCurrentSession(session.id)}
                  aria-label={`Delete ${sessionLabel(session)}`}
                  title="Delete chat"
                >
                  🗑
                </button>
              </div>
            ))}
          </div>
        </div>
      </aside>

      <main className="main-panel">
        <header className="topbar">
          <button className="menu-button" onClick={() => setSidebarOpen((open) => !open)}>
            History
          </button>
          <div className="topbar-title">
            <p className="eyebrow">Current chat</p>
            <div className="title-row">
              <h2>{activeSession ? sessionLabel(activeSession) : 'New conversation'}</h2>
              <button
                className="icon-button"
                onClick={renameCurrentSession}
                disabled={!activeSessionId}
                aria-label="Rename chat"
                title="Rename chat"
              >
                ✎
              </button>
            </div>
          </div>
          <div className="topbar-actions">
            <button
              className="profile-button"
              type="button"
              aria-label="Profile"
              title="Profile"
            >
              A
            </button>
          </div>
        </header>

        <section className="chat-panel">
          {messages.length === 0 ? (
            <div className="empty-state">
              <h3>How can I help?</h3>
              <p>
                Start a new chat from the composer below. Only chats with real messages will appear
                in history.
              </p>
              <div className="prompt-grid">
                {starterPrompts.map((prompt) => (
                  <button key={prompt} className="prompt-card" onClick={() => setInput(prompt)}>
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="message-list">
              {messages.map((message, index) => (
                <article
                  key={`${message.role}-${index}-${message.created_at || index}`}
                  className={`message-bubble ${
                    message.role === 'user' ? 'user-bubble' : 'assistant-bubble'
                  }`}
                >
                  <div className="message-meta">
                    <span>{message.role === 'user' ? 'You' : 'Nova'}</span>
                    <span>{formatTime(message.created_at || new Date().toISOString())}</span>
                  </div>
                  {message.role === 'assistant' && message.streaming && activity ? (
                    <div className="message-activity">{activity}</div>
                  ) : null}
                  <MessageContent content={message.content || (message.streaming ? '...' : '')} />
                </article>
              ))}
              <div ref={messagesEndRef} />
            </div>
          )}
        </section>

        <form className="composer" onSubmit={handleSubmit}>
          <textarea
            ref={textareaRef}
            value={input}
            onChange={handleInputChange}
            placeholder="Ask anything. Debug code, brainstorm features, or query live knowledge."
            rows={1}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                handleSubmit(event);
              }
            }}
          />
          <div className="composer-footer">
            <span>{status}</span>
            <button type="submit" className="send-button" disabled={isStreaming}>
              {isStreaming ? 'Streaming...' : 'Send'}
            </button>
          </div>
        </form>
      </main>
    </div>
  );
}
