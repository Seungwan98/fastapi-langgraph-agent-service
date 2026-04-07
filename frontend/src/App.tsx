import { useCallback, useEffect, useMemo, useRef, useState, type KeyboardEvent } from 'react'
import './App.css'

type MessageRole = 'user' | 'assistant'
type HealthState = 'idle' | 'loading' | 'ready' | 'not-ready' | 'error'

type AgentMetadata = {
  triage_level: string
  triage_reasons: string[]
  fallback_used: boolean
  guardrail_sanitized: boolean
  sanitizer_reasons?: string[]
  request_id?: string | null
}

type SafetyEvent = {
  triage_level: string
  triage_reasons: string[]
  fallback_used?: boolean
  guardrail_sanitized?: boolean
  sanitizer_reasons?: string[]
  request_id?: string | null
  blocked?: boolean
}

type ChatMessage = {
  id: string
  role: MessageRole
  text: string
  createdAt: number
  loading?: boolean
  model?: string
  metadata?: AgentMetadata
}

const apiBaseUrl = (import.meta.env.VITE_API_URL ?? '').trim().replace(/\/$/, '')

const apiUrl = (path: string) => (apiBaseUrl ? `${apiBaseUrl}${path}` : path)

const sidebarItems = [
  { label: 'Chat', icon: '✦', active: true },
  { label: 'Health Data', icon: '◌' },
  { label: 'Mindfulness', icon: '☼' },
  { label: 'Assessment', icon: '▣' },
]

const quickPrompts = [
  'Help me think clearly about my symptoms.',
  'Guide me through a calming breathing exercise.',
  'What details should I track before I panic?',
]

const formatter = new Intl.DateTimeFormat('en-US', {
  hour: '2-digit',
  minute: '2-digit',
})

const healthCopy: Record<HealthState, { label: string; detail: string }> = {
  idle: {
    label: 'Checking soon',
    detail: 'We have not checked the backend yet.',
  },
  loading: {
    label: 'Checking backend',
    detail: 'Confirming the API is ready to respond.',
  },
  ready: {
    label: 'Ready',
    detail: 'The chat backend is available right now.',
  },
  'not-ready': {
    label: 'Not ready',
    detail: 'The backend responded but is missing required config.',
  },
  error: {
    label: 'Connection issue',
    detail: 'We could not confirm backend health.',
  },
}

const threatIntelHealthCopy: Record<HealthState, { label: string; detail: string }> = {
  idle: {
    label: 'Checking soon',
    detail: 'We have not checked workbook RAG readiness yet.',
  },
  loading: {
    label: 'Checking workbook RAG',
    detail: 'Confirming the PDF ingest/query backend is configured.',
  },
  ready: {
    label: 'Workbook ready',
    detail: 'Threat-intel PDF ingest and query endpoints are available.',
  },
  'not-ready': {
    label: 'Workbook not ready',
    detail: 'The workbook RAG backend is missing required config.',
  },
  error: {
    label: 'Workbook issue',
    detail: 'We could not confirm workbook RAG readiness.',
  },
}

const triageCopy: Record<string, { label: string; detail: string }> = {
  GREEN: { label: 'Green', detail: 'Routine conversation flow.' },
  AMBER: { label: 'Amber', detail: 'Handled with extra caution.' },
  RED: { label: 'Red', detail: 'Blocked before agent execution.' },
}

const formatClock = (value: number) => formatter.format(value)

function App() {
  const [composerValue, setComposerValue] = useState('')
  const [threadIdInput, setThreadIdInput] = useState('')
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null)
  const [model, setModel] = useState('')
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [loading, setLoading] = useState(false)
  const [healthReady, setHealthReady] = useState<HealthState>('idle')
  const [healthError, setHealthError] = useState('')
  const [requestError, setRequestError] = useState('')
  const [threatIntelReady, setThreatIntelReady] = useState<HealthState>('idle')
  const [threatIntelHealthError, setThreatIntelHealthError] = useState('')
  const [latestSafetyEvent, setLatestSafetyEvent] = useState<SafetyEvent | null>(null)
  const [threatIntelQuestion, setThreatIntelQuestion] = useState('What keeps health anxiety going?')
  const [threatIntelAnswer, setThreatIntelAnswer] = useState('')
  const [threatIntelSources, setThreatIntelSources] = useState<
    Array<{ doc_id?: string; doc_key?: string; page?: number; source?: string }>
  >([])
  const [threatIntelBusy, setThreatIntelBusy] = useState<'idle' | 'querying'>('idle')
  const [threatIntelError, setThreatIntelError] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const checkHealth = useCallback(async () => {
    setHealthReady('loading')
    setHealthError('')

    try {
      const res = await fetch(apiUrl('/health/ready'))

      if (res.status === 503) {
        setHealthReady('not-ready')
        const text = await res.text()
        throw new Error(`HTTP 503 Service Unavailable: ${text || 'Not ready'}`)
      }

      if (!res.ok) {
        const text = await res.text()
        throw new Error(`HTTP ${res.status} ${res.statusText}: ${text || 'No details'}`)
      }

      setHealthReady('ready')
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error'
      setHealthError(message)
      setHealthReady((prev) => (prev === 'not-ready' ? prev : 'error'))
    }
  }, [])

  const checkThreatIntelHealth = useCallback(async () => {
    setThreatIntelReady('loading')
    setThreatIntelHealthError('')

    try {
      const res = await fetch(apiUrl('/api/v1/threat-intel/ready'))

      if (res.status === 503) {
        setThreatIntelReady('not-ready')
        const text = await res.text()
        throw new Error(`HTTP 503 Service Unavailable: ${text || 'Threat intel not ready'}`)
      }

      if (!res.ok) {
        const text = await res.text()
        throw new Error(`HTTP ${res.status} ${res.statusText}: ${text || 'No details'}`)
      }

      setThreatIntelReady('ready')
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error'
      setThreatIntelHealthError(message)
      setThreatIntelReady((prev) => (prev === 'not-ready' ? prev : 'error'))
    }
  }, [])

  useEffect(() => {
    void checkHealth()
  }, [checkHealth])

  useEffect(() => {
    void checkThreatIntelHealth()
  }, [checkThreatIntelHealth])

  const clearRequestState = () => {
    setRequestError('')
    setModel('')
  }

  const resetConversation = () => {
    setMessages([])
    setComposerValue('')
    setThreadIdInput('')
    setActiveThreadId(null)
    setModel('')
    setRequestError('')
    setLatestSafetyEvent(null)
  }

  const runThreatIntelQuery = async () => {
    const question = threatIntelQuestion.trim()

    if (threatIntelReady !== 'ready') {
      setThreatIntelError('Workbook RAG is not ready. Fix threat-intel readiness before querying PDFs.')
      return
    }

    if (!question) {
      setThreatIntelError('Enter a workbook question before querying.')
      return
    }

    setThreatIntelBusy('querying')
    setThreatIntelError('')

    try {
      const res = await fetch(apiUrl('/api/v1/threat-intel/query'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question }),
      })

      if (!res.ok) {
        const errorText = await res.text()
        throw new Error(`HTTP ${res.status} ${res.statusText}: ${errorText || 'No response details'}`)
      }

      const payload = (await res.json()) as {
        answer: string
        retrieved_sources: Array<{ doc_id?: string; doc_key?: string; page?: number; source?: string }>
      }

      setThreatIntelAnswer(payload.answer)
      setThreatIntelSources(payload.retrieved_sources)
    } catch (err) {
      setThreatIntelError(err instanceof Error ? err.message : 'Unknown query error')
    } finally {
      setThreatIntelBusy('idle')
    }
  }

  const sendMessage = async (outgoingRaw: string) => {
    const outgoing = outgoingRaw.trim()

    if (healthReady !== 'ready') {
      setRequestError('Backend is not ready. Please fix readiness before sending.')
      return
    }

    if (!outgoing) {
      setRequestError('Please enter a message before sending.')
      return
    }

    setLoading(true)
    clearRequestState()

    const messageId = crypto.randomUUID()
    const createdAt = Date.now()
    const placeholderId = `assistant-${messageId}`
    const finalThreadId = threadIdInput.trim() || activeThreadId || ''

    setComposerValue('')
    setMessages((prevMessages) => [
      ...prevMessages,
      {
        id: `user-${messageId}`,
        role: 'user',
        text: outgoing,
        createdAt,
      },
      {
        id: placeholderId,
        role: 'assistant',
        text: '',
        createdAt: createdAt + 1,
        loading: true,
      },
    ])

    const updatePlaceholder = (updater: Partial<ChatMessage>) => {
      setMessages((prevMessages) =>
        prevMessages.map((item) => (item.id === placeholderId ? { ...item, ...updater } : item)),
      )
    }

    try {
      const body = finalThreadId ? { message: outgoing, thread_id: finalThreadId } : { message: outgoing }
      const res = await fetch(apiUrl('/api/v1/agent/invoke'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })

      if (res.status === 400) {
        const errorPayload = (await res.json()) as {
          detail?: { message?: string; reasons?: string[] }
        }
        const detail = errorPayload.detail ?? {}
        const reasons = detail.reasons ?? []
        const blockedMessage = detail.message || 'Request blocked by safety triage'

        setLatestSafetyEvent({
          triage_level: 'RED',
          triage_reasons: reasons,
          blocked: true,
        })
        setRequestError(blockedMessage)
        updatePlaceholder({
          loading: false,
          text: reasons.length
            ? `${blockedMessage}\n\nReasons:\n- ${reasons.join('\n- ')}`
            : blockedMessage,
        })
        return
      }

      if (!res.ok) {
        const errorText = await res.text()
        throw new Error(`HTTP ${res.status} ${res.statusText}: ${errorText || 'No response details'}`)
      }

      const payload = (await res.json()) as {
        output: string
        thread_id: string
        model: string
        metadata?: AgentMetadata
      }

      updatePlaceholder({
        loading: false,
        text: payload.output,
        model: payload.model,
        metadata: payload.metadata,
      })
      if (payload.metadata) {
        setLatestSafetyEvent({
          triage_level: payload.metadata.triage_level,
          triage_reasons: payload.metadata.triage_reasons,
          fallback_used: payload.metadata.fallback_used,
          guardrail_sanitized: payload.metadata.guardrail_sanitized,
          sanitizer_reasons: payload.metadata.sanitizer_reasons,
          request_id: payload.metadata.request_id,
        })
      }
      setModel(payload.model)
      setActiveThreadId(payload.thread_id)
      setThreadIdInput(payload.thread_id)
    } catch (err) {
      setRequestError(err instanceof Error ? err.message : 'Unknown request error')
      updatePlaceholder({
        loading: false,
        text: 'Unable to fetch a response right now. Please try again.',
      })
    } finally {
      setLoading(false)
    }
  }

  const onComposerKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault()
      if (!loading) {
        void sendMessage(composerValue)
      }
    }
  }

  useEffect(() => {
    if (messages.length > 0) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
    }
  }, [messages.length])

  const lastAssistantMessage = useMemo(
    () => [...messages].reverse().find((item) => item.role === 'assistant' && !item.loading),
    [messages],
  )

  const lastAssistantWithModel = useMemo(
    () => [...messages].reverse().find((item) => item.role === 'assistant' && item.model),
    [messages],
  )

  const currentModel = lastAssistantWithModel?.model || model
  const latestMetadata = latestSafetyEvent ?? lastAssistantMessage?.metadata
  const triageState = latestMetadata?.triage_level ?? 'GREEN'
  const triageInfo = triageCopy[triageState] ?? {
    label: triageState,
    detail: 'Returned by the backend metadata.',
  }
  const healthInfo = healthCopy[healthReady]
  const threatIntelHealthInfo = threatIntelHealthCopy[threatIntelReady]
  const isReady = healthReady === 'ready'
  const threatIntelIsReady = threatIntelReady === 'ready'
  const conversationCount = messages.filter((message) => message.role === 'user').length
  const readinessText = isReady
    ? 'Describe what you feel and the backend will keep the conversation context with thread memory.'
    : 'The interface is ready visually, but sending stays disabled until the backend health check passes.'

  return (
    <div className="serene-shell">
      <aside className="serene-sidebar">
        <div className="brand-lockup">
          <div className="brand-mark">S</div>
          <div>
            <p className="eyebrow">Your digital sanctuary</p>
            <h1>Serene</h1>
          </div>
        </div>

        <section className="sidebar-section">
          <p className="section-label">Core Focus</p>
          <nav className="sidebar-nav" aria-label="primary">
            {sidebarItems.map((item) => (
              <button
                key={item.label}
                type="button"
                className={`nav-pill${item.active ? ' nav-pill--active' : ''}`}
              >
                <span className="nav-pill__icon" aria-hidden="true">
                  {item.icon}
                </span>
                <span>{item.label}</span>
              </button>
            ))}
          </nav>
        </section>

        <section className="sidebar-card">
          <div className="sidebar-card__row">
            <div>
              <p className="section-label">Conversation</p>
              <h2>Thread memory</h2>
            </div>
            <button type="button" className="secondary-button" onClick={resetConversation}>
              New chat
            </button>
          </div>

          <label htmlFor="thread-id" className="field-label">
            Thread ID
          </label>
          <input
            id="thread-id"
            type="text"
            value={threadIdInput}
            onChange={(event) => setThreadIdInput(event.target.value)}
            placeholder="Use an existing thread or leave blank"
            spellCheck={false}
            autoComplete="off"
            className="thread-input"
          />
          <p className="helper-copy">
            Active thread: <span>{activeThreadId || 'Starts after your first successful reply'}</span>
          </p>
        </section>

        <div className="sidebar-footer">
          <button
            type="button"
            className="quick-calm-button"
            onClick={() =>
              setComposerValue(
                'I feel overwhelmed and need a calm, grounded way to think about what I am feeling.',
              )
            }
          >
            Quick Calm
          </button>
          <p className="sidebar-note">
            Gentle structure, same backend behavior.
          </p>
        </div>
      </aside>

      <main className="serene-main">
        <header className="serene-topbar">
          <div>
            <p className="eyebrow">Calm health guidance</p>
            <h2>Feel heard without losing clarity.</h2>
          </div>

          <div className="topbar-actions">
            <span className={`status-pill status-pill--${healthReady}`}>{healthInfo.label}</span>
            <button type="button" className="secondary-button" onClick={checkHealth}>
              Recheck
            </button>
            <div className="profile-pill">Profile ◎</div>
          </div>
        </header>

        <section className="serene-workspace">
          <div className="ambient ambient--one" />
          <div className="ambient ambient--two" />

          <section className="chat-stage" aria-live="polite">
            <div className="chat-scroll">
              {messages.length === 0 ? (
                <div className="welcome-stack">
                  <article className="message-card message-card--assistant message-card--hero">
                    <div className="message-badge">Serene AI</div>
                    <div className="message-bubble">
                      <p>
                        Hello. I&apos;m here to help you slow the spiral, organize what you&apos;re feeling,
                        and ask clearer follow-up questions.
                      </p>
                      <p>{readinessText}</p>
                    </div>
                    <span className="message-stamp">Now</span>
                  </article>

                  <article className="welcome-panel">
                    <h3>How this experience works</h3>
                    <ul>
                      <li>Health readiness is checked before you can send.</li>
                      <li>Your returned thread id keeps the conversation context alive.</li>
                      <li>Backend triage and sanitization still run exactly as before.</li>
                    </ul>
                  </article>
                </div>
              ) : (
                messages.map((message) => (
                  <article
                    key={message.id}
                    className={`message-card message-card--${message.role}${message.loading ? ' message-card--loading' : ''}`}
                  >
                    <div className="message-badge">{message.role === 'assistant' ? 'Serene AI' : 'You'}</div>
                    <div className={`message-bubble message-bubble--${message.role}`}>
                      {message.loading ? (
                        <span className="typing-indicator" aria-live="polite">
                          Thinking
                        </span>
                      ) : (
                        <>
                          <p>{message.text}</p>
                          {message.metadata && (
                            <div className="message-meta-row">
                              <span className={`mini-pill mini-pill--${message.metadata.triage_level.toLowerCase()}`}>
                                {message.metadata.triage_level}
                              </span>
                              {message.metadata.fallback_used && <span className="mini-pill">Fallback</span>}
                              {message.metadata.guardrail_sanitized && <span className="mini-pill">Sanitized</span>}
                            </div>
                          )}
                        </>
                      )}
                    </div>
                    <span className="message-stamp">{formatClock(message.createdAt)}</span>
                  </article>
                ))
              )}
              <div ref={messagesEndRef} />
            </div>

            <div className="prompt-row">
              {quickPrompts.map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  className="prompt-chip"
                  onClick={() => void sendMessage(prompt)}
                  disabled={!isReady || loading}
                >
                  {prompt}
                </button>
              ))}
            </div>

            <form
              className="composer-shell"
              onSubmit={(event) => {
                event.preventDefault()
                void sendMessage(composerValue)
              }}
            >
              <div className="composer-frame">
                <button type="button" className="icon-button" aria-label="calm action">
                  ＋
                </button>
                <textarea
                  id="message"
                  value={composerValue}
                  onChange={(event) => setComposerValue(event.target.value)}
                  onKeyDown={onComposerKeyDown}
                  placeholder="Describe how you feel..."
                  rows={3}
                  disabled={loading}
                  className="composer-input"
                />
                <button type="submit" disabled={loading || !isReady} className="send-button">
                  {loading ? 'Sending…' : 'Send'}
                </button>
              </div>

              <div className="composer-footer">
                <p className="meta-line">
                  <span>Model: {currentModel || 'Waiting for first reply'}</span>
                  <span>Thread: {activeThreadId || 'Not started yet'}</span>
                </p>
                {requestError ? <p className="inline-error">{requestError}</p> : null}
              </div>
            </form>
          </section>

          <aside className="insight-panel">
            <article className="panel-card panel-card--accent">
              <div className="panel-header">
                <div>
                  <p className="section-label">Instant grounding</p>
                  <h3>Emergency Calm</h3>
                </div>
                <span className="panel-icon">☁</span>
              </div>
              <p>
                If the conversation feels intense, use a gentler prompt first and then return to the details once your breathing settles.
              </p>
              <button
                type="button"
                className="panel-cta"
                onClick={() =>
                  setComposerValue(
                    'Please guide me through a brief grounding exercise before we continue talking about my symptoms.',
                  )
                }
              >
                Start calm prompt
              </button>
            </article>

            <article className="panel-card panel-card--metrics">
              <div className="panel-header">
                <div>
                  <p className="section-label">Backend pulse</p>
                  <h3>{healthInfo.label}</h3>
                </div>
                <span className={`status-dot status-dot--${healthReady}`} />
              </div>
              <p>{healthInfo.detail}</p>

              <div className="metric-bars" aria-hidden="true">
                <span />
                <span />
                <span />
                <span />
                <span />
                <span className="metric-bars__active" />
              </div>

              <dl className="stats-grid">
                <div>
                  <dt>Turns</dt>
                  <dd>{conversationCount}</dd>
                </div>
                <div>
                  <dt>Model</dt>
                  <dd>{currentModel || '-'}</dd>
                </div>
              </dl>

              {healthError ? <p className="panel-error">{healthError}</p> : null}
            </article>

            <article className="panel-card panel-card--threat-intel">
              <div className="panel-header">
                <div>
                  <p className="section-label">Workbook RAG</p>
                  <h3>Helping Health Anxiety PDFs</h3>
                </div>
                <span className="panel-icon">⌘</span>
              </div>

              <p>Ask grounded questions over the workbook PDFs after ingest has been run from the backend or CLI.</p>

              <div className="threat-intel-actions">
                <span className={`status-pill status-pill--${threatIntelReady}`}>{threatIntelHealthInfo.label}</span>
              </div>

              <p className="soft-copy">{threatIntelHealthInfo.detail}</p>
              <p className="soft-copy">
                Ingest is admin-only now. Run <code>python scripts/ingest_threat_intel_pdf.py</code> or call the backend
                ingest route with an admin token from a trusted environment.
              </p>

              <label htmlFor="threat-intel-question" className="field-label">
                Workbook question
              </label>
              <textarea
                id="threat-intel-question"
                className="threat-intel-input"
                rows={4}
                value={threatIntelQuestion}
                onChange={(event) => setThreatIntelQuestion(event.target.value)}
                placeholder="Ask something like: What keeps health anxiety going?"
                disabled={threatIntelBusy !== 'idle'}
              />

              <button
                type="button"
                className="panel-cta"
                onClick={() => void runThreatIntelQuery()}
                disabled={threatIntelBusy !== 'idle' || !threatIntelIsReady}
              >
                {threatIntelBusy === 'querying' ? 'Querying…' : 'Ask workbook RAG'}
              </button>

              <div className="reason-block">
                <p className="reason-block__title">Ingest path</p>
                <ul>
                  <li>CLI: <code>python scripts/ingest_threat_intel_pdf.py</code></li>
                  <li>API: <code>POST /api/v1/threat-intel/ingest</code> with admin token</li>
                </ul>
              </div>

              <div className="reason-block">
                <p className="reason-block__title">Latest workbook answer</p>
                {threatIntelAnswer ? (
                  <>
                    <p className="soft-copy">{threatIntelAnswer}</p>
                    {threatIntelSources.length > 0 ? (
                      <ul>
                        {threatIntelSources.map((source, index) => (
                          <li key={`${source.doc_id || source.doc_key || 'source'}-${index}`}>
                            {source.doc_key || source.doc_id || 'source'}, page {source.page ?? '—'}
                          </li>
                        ))}
                      </ul>
                    ) : null}
                  </>
                ) : (
                  <p className="soft-copy">Run a workbook query to see grounded results here.</p>
                )}
              </div>

              {threatIntelHealthError ? <p className="panel-error">{threatIntelHealthError}</p> : null}
              {threatIntelError ? <p className="panel-error">{threatIntelError}</p> : null}
            </article>

            <article className="panel-card panel-card--quote">
              <div className="panel-header">
                <div>
                  <p className="section-label">Conversation snapshot</p>
                  <h3>{triageInfo.label}</h3>
                </div>
                <span className={`mini-pill mini-pill--${triageState.toLowerCase()}`}>{triageState}</span>
              </div>
              <p>{triageInfo.detail}</p>
              <ul className="snapshot-list">
                <li>
                  <span>Fallback used</span>
                  <strong>{latestMetadata?.fallback_used ? 'Yes' : 'No'}</strong>
                </li>
                <li>
                  <span>Sanitized</span>
                  <strong>{latestMetadata?.guardrail_sanitized ? 'Yes' : 'No'}</strong>
                </li>
                <li>
                  <span>Blocked</span>
                  <strong>{latestSafetyEvent?.blocked ? 'Yes' : 'No'}</strong>
                </li>
                <li>
                  <span>Request id</span>
                  <strong>{latestMetadata?.request_id || '—'}</strong>
                </li>
              </ul>

              {latestMetadata?.triage_reasons?.length ? (
                <div className="reason-block">
                  <p className="reason-block__title">Latest backend notes</p>
                  <ul>
                    {latestMetadata.triage_reasons.map((reason) => (
                      <li key={reason}>{reason}</li>
                    ))}
                  </ul>
                </div>
              ) : (
                <p className="soft-copy">Once the backend responds, triage reasons and safety flags will appear here.</p>
              )}
            </article>
          </aside>
        </section>
      </main>
    </div>
  )
}

export default App
