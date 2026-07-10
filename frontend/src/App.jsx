import { useSelector } from 'react-redux'
import ChatPanel from './components/ChatPanel'
import FormPanel from './components/FormPanel'
import './App.css'

export default function App() {
  const interaction = useSelector((state) => state.interaction.interaction)

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-brand">
          <div className="brand-icon">Rx</div>
          <div>
            <h1>AI-First CRM</h1>
            <p>HCP Interaction Manager</p>
          </div>
        </div>
        <div className="header-meta">
          <span className="meta-pill">LangGraph Agent</span>
          <span className="meta-pill">Groq · llama-3.3-70b-versatile</span>
        </div>
      </header>

      <main className="app-main">
        <section className="panel-form">
          <FormPanel interaction={interaction} />
        </section>
        <section className="panel-chat">
          <ChatPanel />
        </section>
      </main>
    </div>
  )
}
