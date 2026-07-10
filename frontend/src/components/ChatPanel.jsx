import { useEffect, useRef, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import {
  addMessage,
  setError,
  setInteraction,
  setLoading,
  setPendingConfirmation,
} from '../store/interactionSlice'
import { sendChatMessage } from '../services/api'
import './ChatPanel.css'

const SUGGESTIONS = [
  'Today I met Dr. Smith. Discussed Product X. Positive sentiment. Shared brochures.',
  'Show my last meeting with Dr. Smith',
  'Summarize today\'s visit',
  'Schedule follow-up next Monday',
  'Change sentiment to negative',
]

export default function ChatPanel() {
  const dispatch = useDispatch()
  const {
    interaction,
    messages,
    isLoading,
    error,
    pendingConfirmation,
    sessionId,
  } = useSelector((state) => state.interaction)

  const [input, setInput] = useState('')
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  const handleSend = async (text) => {
    const message = (text || input).trim()
    if (!message || isLoading) return

    setInput('')
    dispatch(addMessage({ role: 'user', content: message }))
    dispatch(setLoading(true))
    dispatch(setError(null))

    const history = messages
      .filter((m) => m.id !== 'welcome')
      .map((m) => ({ role: m.role, content: m.content }))

    try {
      const data = await sendChatMessage({
        message,
        sessionId,
        currentInteraction: interaction,
        pendingConfirmation,
        conversationHistory: history,
      })

      dispatch(setInteraction(data.interaction))
      dispatch(setPendingConfirmation(data.pending_confirmation))
      dispatch(
        addMessage({
          role: 'assistant',
          content: data.reply,
          toolUsed: data.tool_used,
        }),
      )
    } catch (err) {
      dispatch(setError(err.message))
      dispatch(
        addMessage({
          role: 'assistant',
          content: `Sorry, something went wrong: ${err.message}. Make sure the backend is running and GROQ_API_KEY is set.`,
          toolUsed: null,
        }),
      )
    } finally {
      dispatch(setLoading(false))
      inputRef.current?.focus()
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="chat-panel">
      <div className="chat-panel-header">
        <div>
          <h2>AI Assistant</h2>
          <p className="chat-subtitle">LangGraph Agent · Groq LLM</p>
        </div>
        {pendingConfirmation && (
          <span className="confirm-badge">Awaiting confirmation</span>
        )}
      </div>

      <div className="chat-messages">
        {messages.map((msg) => (
          <div key={msg.id} className={`message message-${msg.role}`}>
            <div className="message-avatar">
              {msg.role === 'user' ? 'You' : 'AI'}
            </div>
            <div className="message-body">
              <div className="message-bubble">
                {msg.content.split('\n').map((line, i) => (
                  <span key={i}>
                    {line}
                    {i < msg.content.split('\n').length - 1 && <br />}
                  </span>
                ))}
              </div>
              {msg.toolUsed && (
                <span className="tool-tag">Tool: {msg.toolUsed.replace(/_/g, ' ')}</span>
              )}
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="message message-assistant">
            <div className="message-avatar">AI</div>
            <div className="message-body">
              <div className="message-bubble typing">
                <span /><span /><span />
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {error && <div className="chat-error">{error}</div>}

      <div className="chat-suggestions">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            className="suggestion-chip"
            onClick={() => handleSend(s)}
            disabled={isLoading}
          >
            {s.length > 55 ? s.slice(0, 55) + '…' : s}
          </button>
        ))}
      </div>

      <div className="chat-input-area">
        <textarea
          ref={inputRef}
          className="chat-input"
          placeholder={
            pendingConfirmation
              ? 'Type "yes" to save or "no" to cancel…'
              : 'Describe your HCP interaction…'
          }
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={2}
          disabled={isLoading}
        />
        <button
          className="send-btn"
          onClick={() => handleSend()}
          disabled={!input.trim() || isLoading}
        >
          Send
        </button>
      </div>
    </div>
  )
}
