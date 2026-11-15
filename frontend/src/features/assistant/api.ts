import { getJson, postJson } from '../../shared/api/http'

const CONVERSATIONS = '/api/v1/assistant/conversations'

type AssistantLookup =
  | {
      kind: 'journey'
      departure: string
      arrival: string
      travel_date: string
    }
  | {
      kind: 'incident'
      incident_id: string
    }

export interface AssistantInput {
  question: string
  lookup?: AssistantLookup
}

export type AssistantCitation =
  | {
      source_id: string
      source_version: string
      chunk_id: string
      title: string
    }
  | {
      kind: 'journey' | 'incident'
      title: string
      href: string
      record_version: number
      revision_id: string | null
    }

export interface AssistantTurn {
  turn_number: number
  question: string
  answer: {
    status: 'answered' | 'clarify' | 'unavailable'
    answer: string
    citations: AssistantCitation[]
  }
}

interface ConversationReference {
  conversation_id: string
}

interface ConversationHistory extends ConversationReference {
  turns: AssistantTurn[]
}

function conversationPath(id: string) {
  return `${CONVERSATIONS}/${encodeURIComponent(id)}`
}

export function createConversation(signal: AbortSignal) {
  return postJson<ConversationReference>(CONVERSATIONS, {}, signal)
}

export function getConversation(id: string, signal: AbortSignal) {
  return getJson<ConversationHistory>(conversationPath(id), signal)
}

export function sendAssistantTurn(
  id: string,
  input: AssistantInput,
  signal: AbortSignal,
) {
  return postJson<AssistantTurn>(`${conversationPath(id)}/turns`, input, signal)
}
