import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'

import { ApiError } from '../../../shared/api/http'
import { createConversation, getConversation, sendAssistantTurn } from '../api'
import type { AssistantCitation, AssistantInput, AssistantTurn } from '../api'

const STORAGE_KEY = 'railconnect.assistant.conversation'
const UUID_PATTERN = '[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}'

type Mode = 'guide' | 'journey' | 'incident'

function readSavedConversation() {
  try {
    const id = sessionStorage.getItem(STORAGE_KEY)
    return id && new RegExp(`^${UUID_PATTERN}$`).test(id) ? id : null
  } catch {
    return null
  }
}

function saveConversation(id: string | null) {
  try {
    if (id) sessionStorage.setItem(STORAGE_KEY, id)
    else sessionStorage.removeItem(STORAGE_KEY)
  } catch {
    // History remains available while the current screen is open.
  }
}

function Citation({ citation }: { citation: AssistantCitation }) {
  if ('kind' in citation) {
    const prefix = citation.kind === 'journey' ? '/api/v1/journeys/' : '/api/v1/incidents/'
    const safeLink = citation.href.startsWith(prefix)
    return (
      <>
        {safeLink ? <a href={citation.href}>{citation.title}</a> : citation.title}
        {' · '}Record version {citation.record_version}
      </>
    )
  }

  return (
    <>
      {citation.title}
      {' · '}RailConnect passenger guide v{citation.source_version}
      {' · '}{citation.chunk_id}
    </>
  )
}

export function PassengerAssistant() {
  const [conversationId, setConversationId] = useState(readSavedConversation)
  const [historyRequest, setHistoryRequest] = useState<{ id: string } | null>(
    () => conversationId ? { id: conversationId } : null,
  )
  const [turns, setTurns] = useState<AssistantTurn[]>([])
  const [mode, setMode] = useState<Mode>('guide')
  const [question, setQuestion] = useState('')
  const [departure, setDeparture] = useState('')
  const [arrival, setArrival] = useState('')
  const [travelDate, setTravelDate] = useState('')
  const [incidentId, setIncidentId] = useState('')
  const [sending, setSending] = useState(false)
  const [blocked, setBlocked] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const activeSend = useRef<AbortController | null>(null)

  const busy = sending || historyRequest !== null

  useEffect(() => () => activeSend.current?.abort(), [])

  useEffect(() => {
    if (!historyRequest) return
    const controller = new AbortController()

    void getConversation(historyRequest.id, controller.signal)
      .then((history) => {
        if (controller.signal.aborted) return
        setTurns(history.turns)
        setBlocked(false)
        setError(null)
      })
      .catch((failure: unknown) => {
        if (controller.signal.aborted) return
        setBlocked(true)
        setError(
          failure instanceof ApiError && failure.status === 404
            ? 'This conversation is no longer available in this browser. Start a new conversation.'
            : 'Unable to load the conversation. Try Refresh conversation.',
        )
      })
      .finally(() => {
        if (!controller.signal.aborted) setHistoryRequest(null)
      })

    return () => controller.abort()
  }, [historyRequest])

  function startNewConversation() {
    saveConversation(null)
    setConversationId(null)
    setTurns([])
    setBlocked(false)
    setError(null)
  }

  function buildInput(): AssistantInput {
    if (mode === 'journey') {
      return {
        question: `Find a direct journey from ${departure.trim()} to ${arrival.trim()} on ${travelDate}.`,
        lookup: {
          kind: 'journey',
          departure: departure.trim(),
          arrival: arrival.trim(),
          travel_date: travelDate,
        },
      }
    }

    if (mode === 'incident') {
      return {
        question: `Look up verified incident ${incidentId.trim()}.`,
        lookup: { kind: 'incident', incident_id: incidentId.trim() },
      }
    }

    return { question: question.trim() }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (busy || blocked || activeSend.current) return
    if (mode === 'guide' && !question.trim()) return
    if (mode === 'journey' && (!departure.trim() || !arrival.trim() || !travelDate)) return

    const controller = new AbortController()
    activeSend.current = controller
    setSending(true)
    setError(null)

    let id = conversationId

    try {
      if (!id) {
        const created = await createConversation(controller.signal)
        if (controller.signal.aborted) return
        id = created.conversation_id
        saveConversation(id)
        setConversationId(id)
      }

      const turn = await sendAssistantTurn(id, buildInput(), controller.signal)
      if (controller.signal.aborted) return
      setTurns((previous) => [...previous, turn])
      if (mode === 'guide') setQuestion('')
    } catch (failure) {
      if (controller.signal.aborted) return

      if (failure instanceof ApiError && failure.status === 404) {
        setBlocked(true)
        setError('This conversation is no longer available. Start a new conversation.')
      } else if (failure instanceof ApiError && failure.status === 409) {
        setBlocked(true)
        setError('This conversation has reached its turn limit. Start a new conversation.')
      } else if (failure instanceof ApiError && failure.status === 422) {
        setError('Check the question or lookup details and try again.')
      } else if (id) {
        setBlocked(true)
        setError('The question may have been saved. Refresh the conversation before sending again.')
      } else {
        setError('Unable to start a conversation. Please try again.')
      }
    } finally {
      activeSend.current = null
      if (!controller.signal.aborted) setSending(false)
    }
  }

  return (
    <section className="card passenger-assistant" aria-labelledby="assistant-heading">
      <h2 id="assistant-heading">Passenger assistant</h2>
      <p>Ask about RailConnect or look up a demonstration journey or verified incident.</p>

      {conversationId && (
        <div className="assistant-actions">
          <button
            type="button"
            disabled={busy}
            onClick={() => setHistoryRequest({ id: conversationId })}
          >
            Refresh conversation
          </button>
          <button type="button" disabled={busy} onClick={startNewConversation}>
            Start a new conversation
          </button>
        </div>
      )}

      {historyRequest && <p role="status">Loading conversation…</p>}
      {error && <p className="error" role="alert">{error}</p>}

      <div role="log" aria-label="Conversation history" aria-busy={busy}>
        {turns.length > 0 && (
          <ol className="assistant-turns">
            {turns.map((turn) => (
              <li key={turn.turn_number}>
                <article className="assistant-turn">
                  <h3>{turn.question}</h3>
                  <p className="assistant-answer">{turn.answer.answer}</p>
                  {turn.answer.citations.length > 0 && (
                    <ul className="assistant-sources" aria-label="Sources">
                      {turn.answer.citations.map((citation) => (
                        <li key={'kind' in citation ? citation.href : citation.chunk_id}>
                          <Citation citation={citation} />
                        </li>
                      ))}
                    </ul>
                  )}
                </article>
              </li>
            ))}
          </ol>
        )}
      </div>

      <form className="assistant-form" onSubmit={(event) => void submit(event)}>
        <fieldset className="report-fields assistant-fields" disabled={busy || blocked}>
          <legend>Ask the assistant</legend>

          <div className="report-field">
            <label htmlFor="assistant-mode">Help with</label>
            <select
              id="assistant-mode"
              value={mode}
              onChange={(event) => setMode(event.target.value as Mode)}
            >
              <option value="guide">Passenger guide</option>
              <option value="journey">Direct journey</option>
              <option value="incident">Verified incident</option>
            </select>
          </div>

          {mode === 'guide' && (
            <div className="report-field">
              <label htmlFor="assistant-question">Question</label>
              <textarea
                id="assistant-question"
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                placeholder="How do I report a disruption?"
                maxLength={500}
                required
              />
            </div>
          )}

          {mode === 'journey' && (
            <>
              <div className="report-field">
                <label htmlFor="assistant-departure">Departure station name or code</label>
                <input id="assistant-departure" value={departure} maxLength={120} required
                  onChange={(event) => setDeparture(event.target.value)} />
              </div>
              <div className="report-field">
                <label htmlFor="assistant-arrival">Arrival station name or code</label>
                <input id="assistant-arrival" value={arrival} maxLength={120} required
                  onChange={(event) => setArrival(event.target.value)} />
              </div>
              <div className="report-field">
                <label htmlFor="assistant-date">Boarding date</label>
                <input id="assistant-date" type="date" value={travelDate} required
                  onChange={(event) => setTravelDate(event.target.value)} />
              </div>
            </>
          )}

          {mode === 'incident' && (
            <div className="report-field">
              <label htmlFor="assistant-incident">Public incident ID</label>
              <input id="assistant-incident" value={incidentId} pattern={UUID_PATTERN} required
                onChange={(event) => setIncidentId(event.target.value)} />
            </div>
          )}

          <button type="submit">{sending ? 'Sending…' : 'Send'}</button>
        </fieldset>
      </form>
    </section>
  )
}
