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

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  useEffect(() => {
    const handler = (e) => handleSend(e.detail)
    window.addEventListener('hcp-chat-send', handler)
    return () => window.removeEventListener('hcp-chat-send', handler)
  }, [interaction, pendingConfirmation, isLoading, messages])

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
          content: `Sorry, something went wrong: ${err.message}`,
          toolUsed: null,
        }),
      )
    } finally {
      dispatch(setLoading(false))
    }
  }

  return (
    <div className="chat-sidebar">
      <div className="chat-sidebar-header">
        <div className="ai-icon">🌐</div>
        <div>
          <h2>AI Assistant</h2>
          <p>Log interaction via chat</p>
        </div>
        {pendingConfirmation && (
          <span className="awaiting-badge">Awaiting save</span>
        )}
      </div>

      <div className="chat-sidebar-messages">
        {messages.map((msg) => (
          <div key={msg.id} className={`chat-msg chat-msg-${msg.role}`}>
            {msg.role === 'assistant' && (
              <div className="chat-msg-label">AI Assistant</div>
            )}
            <div className="chat-msg-bubble">
              {msg.content.split('\n').map((line, i) => (
                <span key={i}>
                  {line}
                  {i < msg.content.split('\n').length - 1 && <br />}
                </span>
              ))}
            </div>
            {msg.toolUsed && (
              <span className="chat-tool-tag">Tool: {msg.toolUsed.replace(/_/g, ' ')}</span>
            )}
          </div>
        ))}

        {isLoading && (
          <div className="chat-msg chat-msg-assistant">
            <div className="chat-msg-bubble typing">
              <span /><span /><span />
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {error && <div className="chat-sidebar-error">{error}</div>}

      <div className="chat-sidebar-input">
        <input
          type="text"
          className="chat-text-input"
          placeholder={
            pendingConfirmation
              ? 'Type "yes" to save or "no" to cancel...'
              : 'Describe interaction...'
          }
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          disabled={isLoading}
        />
        <button
          className="chat-log-btn"
          onClick={() => handleSend()}
          disabled={!input.trim() || isLoading}
        >
          Log
        </button>
      </div>
    </div>
  )
}
