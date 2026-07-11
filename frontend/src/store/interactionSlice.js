import { createSlice } from '@reduxjs/toolkit'

const emptyInteraction = () => ({
  id: null,
  doctorName: '',
  interactionType: 'Meeting',
  date: '',
  time: '',
  attendees: '',
  topicsDiscussed: '',
  products: '',
  sentiment: 'neutral',
  brochure: false,
  samples: false,
  materialsShared: '',
  samplesDistributed: '',
  outcomes: '',
  followUpActions: '',
  notes: '',
  followUpDate: '',
  followUpStatus: 'pending',
  aiSuggestedFollowups: [],
})

const initialState = {
  interaction: emptyInteraction(),
  messages: [
    {
      id: 'welcome',
      role: 'assistant',
      content:
        "Log interaction details here (e.g., 'Met Dr. Smith, discussed Product X efficacy, positive sentiment, shared brochure') or ask for help.",
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
      const payload = action.payload || {}
      state.interaction = { ...emptyInteraction(), ...payload }
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
