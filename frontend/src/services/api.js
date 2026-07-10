const API_BASE = import.meta.env.VITE_API_BASE || '/api'

export async function sendChatMessage({
  message,
  sessionId,
  currentInteraction,
  pendingConfirmation,
  conversationHistory,
}) {
  const response = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      session_id: sessionId,
      current_interaction: currentInteraction,
      pending_confirmation: pendingConfirmation,
      conversation_history: conversationHistory,
    }),
  })

  if (!response.ok) {
    const err = await response.json().catch(() => ({}))
    const detail = err.detail
    const message = typeof detail === 'string'
      ? detail
      : Array.isArray(detail)
        ? detail.map((d) => d.msg).join(', ')
        : `Request failed (${response.status})`
    throw new Error(message)
  }

  return response.json()
}

export async function checkHealth() {
  const response = await fetch(`${API_BASE}/health`)
  return response.json()
}
