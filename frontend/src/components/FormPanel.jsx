import './FormPanel.css'

const SENTIMENT_OPTIONS = ['positive', 'neutral', 'negative']

function Field({ label, value, placeholder, full = false, multiline = false }) {
  const display = value || ''
  const isEmpty = !display
  return (
    <div className={`field-group ${full ? 'field-full' : ''}`}>
      <label className="field-label">{label}</label>
      {multiline ? (
        <div className={`field-input field-textarea ${isEmpty ? 'empty' : ''}`}>
          {isEmpty ? placeholder : display}
        </div>
      ) : (
        <div className={`field-input ${isEmpty ? 'empty' : ''}`}>
          {isEmpty ? placeholder : display}
        </div>
      )}
    </div>
  )
}

function SentimentField({ value }) {
  const current = (value || 'neutral').toLowerCase()
  return (
    <div className="field-group field-full">
      <label className="field-label">Observed/Inferred HCP Sentiment</label>
      <div className="sentiment-group">
        {SENTIMENT_OPTIONS.map((opt) => (
          <div
            key={opt}
            className={`sentiment-option ${current === opt ? 'selected' : ''}`}
          >
            <span className="sentiment-icon">
              {opt === 'positive' ? '🙂' : opt === 'negative' ? '🙁' : '😐'}
            </span>
            <span>{opt.charAt(0).toUpperCase() + opt.slice(1)}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function MaterialsSection({ materials, samples }) {
  return (
    <div className="field-group field-full">
      <label className="field-label">Materials Shared / Samples Distributed</label>
      <div className="materials-row">
        <div className="material-box">
          <div className="material-title">Materials Shared</div>
          <div className="material-value">
            {materials || 'No materials added'}
          </div>
        </div>
        <div className="material-box">
          <div className="material-title">Samples Distributed</div>
          <div className="material-value">
            {samples || 'No samples added'}
          </div>
        </div>
      </div>
    </div>
  )
}

export default function FormPanel({ interaction, pendingConfirmation, onSuggestionClick }) {
  const suggestions = interaction.aiSuggestedFollowups?.length
    ? interaction.aiSuggestedFollowups
    : [
        'Schedule follow-up meeting in 2 weeks',
        'Send product information PDF',
        'Add HCP to advisory board invite list',
      ]

  return (
    <div className="form-panel">
      <div className="form-page-header">
        <h1>Log HCP Interaction</h1>
        <div className="form-badges">
          {pendingConfirmation && (
            <span className="badge draft">Draft — type YES to save</span>
          )}
          {interaction.id && !pendingConfirmation && (
            <span className="badge saved">Saved #{interaction.id}</span>
          )}
        </div>
      </div>

      <h2 className="section-title">Interaction Details</h2>
      <p className="section-subtitle">AI-controlled — fields update via chat only</p>

      <div className="form-body">
        <Field
          label="HCP Name"
          value={interaction.doctorName}
          placeholder="Search or select HCP..."
        />
        <Field
          label="Interaction Type"
          value={interaction.interactionType}
          placeholder="Meeting"
        />
        <Field
          label="Date"
          value={interaction.date ? interaction.date.split('-').reverse().join('-') : ''}
          placeholder="DD-MM-YYYY"
        />
        <Field
          label="Time"
          value={interaction.time}
          placeholder="HH:MM"
        />
        <Field
          label="Attendees"
          value={interaction.attendees}
          placeholder="Enter names or search..."
          full
        />
        <Field
          label="Topics Discussed"
          value={interaction.topicsDiscussed || interaction.notes}
          placeholder="Enter key discussion points..."
          full
          multiline
        />

        <MaterialsSection
          materials={interaction.materialsShared || (interaction.brochure ? 'Brochure shared' : '')}
          samples={interaction.samplesDistributed || (interaction.samples ? 'Samples provided' : '')}
        />

        <SentimentField value={interaction.sentiment} />

        <Field
          label="Outcomes"
          value={interaction.outcomes}
          placeholder="Key outcomes or agreements..."
          full
          multiline
        />
        <Field
          label="Follow-up Actions"
          value={interaction.followUpActions || (interaction.followUpDate ? `Follow-up on ${interaction.followUpDate}` : '')}
          placeholder="Enter next steps or tasks..."
          full
          multiline
        />

        <div className="field-group field-full">
          <label className="field-label">AI Suggested Follow-ups</label>
          <div className="suggestions-list">
            {suggestions.map((s) => (
              <button
                key={s}
                type="button"
                className="suggestion-link"
                onClick={() => onSuggestionClick?.(s)}
              >
                + {s}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
