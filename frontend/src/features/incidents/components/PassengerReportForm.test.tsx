import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from '../../../shared/api/http'
import { submitPassengerReport } from '../api'
import type { ReportSubmission } from '../types'
import { PassengerReportForm } from './PassengerReportForm'

vi.mock('../api', () => ({
  submitPassengerReport: vi.fn(),
}))

const receipt: ReportSubmission = {
  report_id: 'synthetic-report-reference',
  status: 'pending',
  submitted_at: '2026-10-18T06:00:00Z',
  message: 'Report received.',
}

function fillReport(observedAt = '2020-01-02T10:30') {
  fireEvent.change(screen.getByLabelText('Report title'), {
    target: { value: 'Synthetic station observation' },
  })

  fireEvent.change(
    screen.getByLabelText('Describe what you observed'),
    {
      target: {
        value: 'A fictional observation for the portfolio demonstration.',
      },
    },
  )

  fireEvent.change(
    screen.getByLabelText('Observation date and time'),
    {
      target: { value: observedAt },
    },
  )
}

describe('Passenger report form', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('explains that reports require staff review', () => {
    render(<PassengerReportForm />)

    expect(
      screen.getByRole('heading', { name: 'Report a disruption' }),
    ).toBeInTheDocument()

    expect(
      screen.getByText(
        /Reports are unverified claims until reviewed by authorized staff/,
      ),
    ).toBeInTheDocument()

    expect(
      screen.getByText(/Enter Sri Lanka time/),
    ).toBeInTheDocument()
  })

  it('rejects whitespace-only content without submitting', () => {
    render(<PassengerReportForm />)
    fillReport()

    fireEvent.change(screen.getByLabelText('Report title'), {
      target: { value: '   ' },
    })

    fireEvent.click(
      screen.getByRole('button', { name: 'Submit report' }),
    )

    expect(screen.getByRole('alert')).toHaveTextContent(
      'Enter a title, description and observation time.',
    )
    expect(submitPassengerReport).not.toHaveBeenCalled()
  })

  it('rejects future observation times', () => {
    render(<PassengerReportForm />)
    fillReport('2099-01-02T10:30')

    fireEvent.click(
      screen.getByRole('button', { name: 'Submit report' }),
    )

    expect(screen.getByRole('alert')).toHaveTextContent(
      'not in the future',
    )
    expect(submitPassengerReport).not.toHaveBeenCalled()
  })

  it('converts Sri Lanka time to UTC and displays a pending receipt', async () => {
    vi.mocked(submitPassengerReport).mockResolvedValue(receipt)

    render(<PassengerReportForm />)
    fillReport()

    fireEvent.click(
      screen.getByRole('button', { name: 'Submit report' }),
    )

    await screen.findByText(
      'Report received. Its status is pending staff review.',
    )

    expect(submitPassengerReport).toHaveBeenCalledWith(
      {
        title: 'Synthetic station observation',
        narrative:
          'A fictional observation for the portfolio demonstration.',
        observed_at: '2020-01-02T05:00:00.000Z',
      },
      expect.any(AbortSignal),
    )

    expect(
      screen.getByText('synthetic-report-reference'),
    ).toBeInTheDocument()

    expect(
      screen.getByText(
        'This receipt does not verify the reported disruption.',
      ),
    ).toBeInTheDocument()

    expect(
      screen.queryByRole('button', { name: 'Submit report' }),
    ).not.toBeInTheDocument()
  })

  it('prevents duplicate submissions while a request is pending', async () => {
    let complete: ((value: ReportSubmission) => void) | undefined

    vi.mocked(submitPassengerReport).mockImplementation(
      () =>
        new Promise<ReportSubmission>((resolve) => {
          complete = resolve
        }),
    )

    render(<PassengerReportForm />)
    fillReport()

    const button = screen.getByRole('button', {
      name: 'Submit report',
    })

    fireEvent.click(button)
    fireEvent.click(button)

    expect(submitPassengerReport).toHaveBeenCalledTimes(1)
    expect(
      screen.getByRole('button', { name: 'Submitting report…' }),
    ).toBeDisabled()
    expect(screen.getByLabelText('Report title')).toBeDisabled()

    await act(async () => {
      complete?.(receipt)
    })

    expect(
      screen.getByText(
        'Report received. Its status is pending staff review.',
      ),
    ).toBeInTheDocument()
  })

  it('shows the retry interval and preserves input after rate limiting', async () => {
    vi.mocked(submitPassengerReport).mockRejectedValue(
      new ApiError(
        'Too many requests.',
        429,
        'RATE_LIMITED',
        null,
        45,
      ),
    )

    render(<PassengerReportForm />)
    fillReport()

    fireEvent.click(
      screen.getByRole('button', { name: 'Submit report' }),
    )

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Too many reports. Try again in 45 seconds.',
    )

    expect(screen.getByLabelText('Report title')).toHaveValue(
      'Synthetic station observation',
    )
    expect(
      screen.getByRole('button', { name: 'Submit report' }),
    ).toBeEnabled()
  })

  it('does not claim failure or success when submission is uncertain', async () => {
    vi.mocked(submitPassengerReport).mockRejectedValue(
      new Error('Connection interrupted.'),
    )

    render(<PassengerReportForm />)
    fillReport()

    fireEvent.click(
      screen.getByRole('button', { name: 'Submit report' }),
    )

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Submission could not be confirmed.',
    )
    expect(screen.getByRole('alert')).toHaveTextContent(
      'Your report may have been received.',
    )
    expect(
      screen.queryByText('synthetic-report-reference'),
    ).not.toBeInTheDocument()
  })

  it('starts another report with cleared fields', async () => {
    vi.mocked(submitPassengerReport).mockResolvedValue(receipt)
    const user = userEvent.setup()

    render(<PassengerReportForm />)
    fillReport()

    await user.click(
      screen.getByRole('button', { name: 'Submit report' }),
    )

    await user.click(
      await screen.findByRole('button', {
        name: 'Start another report',
      }),
    )

    expect(screen.getByLabelText('Report title')).toHaveValue('')
    expect(
      screen.getByLabelText('Describe what you observed'),
    ).toHaveValue('')
    expect(
      screen.getByLabelText('Observation date and time'),
    ).toHaveValue('')
  })

  it('aborts submission when the form unmounts', async () => {
    vi.mocked(submitPassengerReport).mockImplementation(
      () => new Promise<ReportSubmission>(() => {}),
    )

    const { unmount } = render(<PassengerReportForm />)
    fillReport()

    fireEvent.click(
      screen.getByRole('button', { name: 'Submit report' }),
    )

    await waitFor(() => {
      expect(submitPassengerReport).toHaveBeenCalledTimes(1)
    })

    const signal = vi.mocked(submitPassengerReport).mock.calls[0][1]
    expect(signal.aborted).toBe(false)

    unmount()

    expect(signal.aborted).toBe(true)
  })
})
