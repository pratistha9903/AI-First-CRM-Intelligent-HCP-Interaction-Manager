import { useSelector } from 'react-redux'
import ChatPanel from './components/ChatPanel'
import FormPanel from './components/FormPanel'
import './App.css'

export default function App() {
  const interaction = useSelector((state) => state.interaction.interaction)
  const pendingConfirmation = useSelector((state) => state.interaction.pendingConfirmation)

  const handleSuggestionClick = (suggestion) => {
    window.dispatchEvent(new CustomEvent('hcp-chat-send', { detail: suggestion }))
  }

  return (
    <div className="app">
      <main className="app-layout">
        <section className="layout-form">
          <FormPanel
            interaction={interaction}
            pendingConfirmation={pendingConfirmation}
            onSuggestionClick={handleSuggestionClick}
          />
        </section>
        <section className="layout-chat">
          <ChatPanel />
        </section>
      </main>
    </div>
  )
}
