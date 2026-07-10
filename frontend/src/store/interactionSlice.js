import { createSlice } from '@reduxjs/toolkit'

const emptyInteraction = () => ({
  id: null,
  doctorName: '',
  date: '',
  products: '',
  sentiment: '',
  brochure: false,
  samples: false,
  notes: '',
  followUpDate: '',
  followUpStatus: 'pending',
})

const initialState = {
  interaction: emptyInteraction(),
  messages: [
    {
      id: 'welcome',
      role: 'assistant',
      content:
        'Welcome! I\'m your HCP Interaction Assistant. Tell me about your visit — e.g. "Today I met Dr. Smith. We discussed Product X. He liked it. Shared brochures."',
      toolUsed: null,
    },
  ],
  isLoading: false,
  error: null,
  pendingConfirmation: false,
  sessionId: `session-${Date.now()}`,
}

const interactionSlice = createSlice({
  name: 'interaction',
  initialState,
  reducers: {
    setInteraction(state, action) {
      state.interaction = { ...state.interaction, ...action.payload }
    },
    addMessage(state, action) {
      state.messages.push({
        id: `msg-${Date.now()}-${Math.random().toString(36).slice(2)}`,
        ...action.payload,
      })
    },
    setLoading(state, action) {
      state.isLoading = action.payload
    },
    setError(state, action) {
      state.error = action.payload
    },
    setPendingConfirmation(state, action) {
      state.pendingConfirmation = action.payload
    },
    resetInteraction(state) {
      state.interaction = emptyInteraction()
      state.pendingConfirmation = false
    },
  },
})

export const {
  setInteraction,
  addMessage,
  setLoading,
  setError,
  setPendingConfirmation,
  resetInteraction,
} = interactionSlice.actions

export default interactionSlice.reducer
