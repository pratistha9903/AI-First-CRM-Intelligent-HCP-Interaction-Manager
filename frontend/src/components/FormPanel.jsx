import './FormPanel.css'

const SENTIMENT_COLORS = {
  positive: '#00a896',
  negative: '#e63946',
  neutral: '#5a6a7e',
}

function ReadOnlyField({ label, value, type = 'text' }) {
  if (type === 'checkbox') {
    return (
      <div className="form-field">
        <label className="form-label">{label}</label>
        <div className={`form-checkbox ${value ? 'checked' : ''}`}>
          <span className="checkbox-icon">{value ? '✓' : '—'}</span>
          <span>{value ? 'Yes' : 'No'}</span>
        </div>
      </div>
    )
  }

  if (type === 'sentiment') {
    const color = SENTIMENT_COLORS[value?.toLowerCase()] || 'var(--color-text-muted)'
    return (
      <div className="form-field">
        <label className="form-label">{label}</label>
        <div className="form-value sentiment-badge" style={{ color, borderColor: color }}>
          {value || '—'}
        </div>
      </div>
    )
  }

  if (type === 'textarea') {
    return (
      <div className="form-field form-field-full">
        <label className="form-label">{label}</label>
        <div className="form-value form-textarea">{value || '—'}</div>
      </div>
    )
  }

  return (
    <div className="form-field">
      <label className="form-label">{label}</label>
      <div className="form-value">{value || '—'}</div>
    </div>
  )
}

export default function FormPanel({ interaction }) {
  return (
    <div className="form-panel">
      <div className="form-panel-header">
        <div>
          <h2>Interaction Form</h2>
          <p className="form-subtitle">AI-controlled — updates via chat only</p>
        </div>
        {interaction.id && (
          <span className="interaction-id">ID #{interaction.id}</span>
        )}
      </div>

      <div className="form-grid">
        <ReadOnlyField label="Doctor Name" value={interaction.doctorName} />
        <ReadOnlyField label="Visit Date" value={interaction.date} />
        <ReadOnlyField label="Products Discussed" value={interaction.products} />
        <ReadOnlyField
          label="Sentiment"
          value={interaction.sentiment}
          type="sentiment"
        />
        <ReadOnlyField
          label="Brochure Shared"
          value={interaction.brochure}
          type="checkbox"
        />
        <ReadOnlyField
          label="Samples Provided"
          value={interaction.samples}
          type="checkbox"
        />
        <ReadOnlyField
          label="Follow-up Date"
          value={interaction.followUpDate}
        />
        <ReadOnlyField
          label="Follow-up Status"
          value={interaction.followUpStatus}
        />
        <ReadOnlyField label="Notes" value={interaction.notes} type="textarea" />
      </div>

      <div className="form-footer">
        <div className="ai-badge">
          <span className="ai-dot" />
          Form updates automatically when AI processes your messages
        </div>
      </div>
    </div>
  )
}
