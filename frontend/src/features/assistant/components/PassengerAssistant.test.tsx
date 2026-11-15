import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { createConversation, getConversation, sendAssistantTurn } from '../api'
import type { AssistantTurn } from '../api'
import { PassengerAssistant } from './PassengerAssistant'

vi.mock('../api', () => ({
  createConversation: vi.fn(),
  getConversation: vi.fn(),
  sendAssistantTurn: vi.fn(),
}))

const CONVERSATION_ID = '00000000-0000-4000-8000-000000000001'
const STORAGE_KEY = 'railconnect.assistant.conversation'

const guideTurn: AssistantTurn = {
  turn_number: 1,
  question: 'How do I report a disruption?',
  answer: {
    status: 'answered',
    answer: 'Open Report a disruption and enter your observation details.',
    citations: [
      {
        source_id: 'railconnect-passenger-guide',
        source_version: '1',
        chunk_id: 'report-disruption',
        title: 'Report a disruption',
      },
    ],
  },
}

beforeEach(() => {
  vi.resetAllMocks()
  sessionStorage.clear()
  vi.mocked(createConversation).mockResolvedValue({
    conversation_id: CONVERSATION_ID,
  })
  vi.mocked(sendAssistantTurn).mockResolvedValue(guideTurn)
})

afterEach(() => {
  cleanup()
  sessionStorage.clear()
})

describe('Passenger assistant', () => {
  it('creates a conversation and shows a cited guide answer', async () => {
    const user = userEvent.setup()
    render(<PassengerAssistant />)

    expect(createConversation).not.toHaveBeenCalled()
    await user.type(screen.getByLabelText('Question'), guideTurn.question)
    await user.click(screen.getByRole('button', { name: 'Send' }))

    expect(await screen.findByText(guideTurn.answer.answer)).toBeInTheDocument()
    expect(screen.getByText(/RailConnect passenger guide v1/)).toBeInTheDocument()
    expect(sendAssistantTurn).toHaveBeenCalledWith(
      CONVERSATION_ID,
      { question: guideTurn.question },
      expect.any(AbortSignal),
    )
    expect(sessionStorage.getItem(STORAGE_KEY)).toBe(CONVERSATION_ID)
  })

  it('submits the selected journey details and links the cited record', async () => {
    const user = userEvent.setup()
    const href = '/api/v1/journeys/00000000-0000-4000-8000-000000000002'
    vi.mocked(sendAssistantTurn).mockResolvedValue({
      turn_number: 1,
      question: 'Find a direct journey from Jaffna to Colombo Fort on 2026-11-16.',
      answer: {
        status: 'answered',
        answer: 'Demo Northern Return has a scheduled arrival at 16:00.',
        citations: [
          {
            kind: 'journey',
            title: 'Demo Northern Return',
            href,
            record_version: 1,
            revision_id: null,
          },
        ],
      },
    })
    render(<PassengerAssistant />)

    await user.selectOptions(screen.getByLabelText('Help with'), 'journey')
    await user.type(screen.getByLabelText('Departure station name or code'), 'Jaffna')
    await user.type(screen.getByLabelText('Arrival station name or code'), 'Colombo Fort')
    fireEvent.change(screen.getByLabelText('Boarding date'), {
      target: { value: '2026-11-16' },
    })
    await user.click(screen.getByRole('button', { name: 'Send' }))

    const source = await screen.findByRole('link', { name: 'Demo Northern Return' })
    expect(source).toHaveAttribute('href', href)
    expect(sendAssistantTurn).toHaveBeenCalledWith(
      CONVERSATION_ID,
      {
        question: 'Find a direct journey from Jaffna to Colombo Fort on 2026-11-16.',
        lookup: {
          kind: 'journey',
          departure: 'Jaffna',
          arrival: 'Colombo Fort',
          travel_date: '2026-11-16',
        },
      },
      expect.any(AbortSignal),
    )
  })

  it('restores the saved conversation without creating another one', async () => {
    sessionStorage.setItem(STORAGE_KEY, CONVERSATION_ID)
    vi.mocked(getConversation).mockResolvedValue({
      conversation_id: CONVERSATION_ID,
      turns: [guideTurn],
    })
    render(<PassengerAssistant />)

    expect(await screen.findByText(guideTurn.answer.answer)).toBeInTheDocument()
    expect(getConversation).toHaveBeenCalledWith(CONVERSATION_ID, expect.any(AbortSignal))
    expect(createConversation).not.toHaveBeenCalled()
  })

  it('requires a history refresh after an uncertain send', async () => {
    const user = userEvent.setup()
    vi.mocked(sendAssistantTurn).mockRejectedValue(new Error('Connection interrupted'))
    vi.mocked(getConversation).mockResolvedValue({
      conversation_id: CONVERSATION_ID,
      turns: [guideTurn],
    })
    render(<PassengerAssistant />)

    await user.type(screen.getByLabelText('Question'), guideTurn.question)
    await user.click(screen.getByRole('button', { name: 'Send' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('may have been saved')
    expect(screen.getByRole('button', { name: 'Send' })).toBeDisabled()
    expect(sendAssistantTurn).toHaveBeenCalledTimes(1)

    await user.click(screen.getByRole('button', { name: 'Refresh conversation' }))

    expect(await screen.findByText(guideTurn.answer.answer)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Send' })).toBeEnabled()
    expect(sendAssistantTurn).toHaveBeenCalledTimes(1)
  })
})
