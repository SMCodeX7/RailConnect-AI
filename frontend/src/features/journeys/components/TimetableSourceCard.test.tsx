import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import type { TimetableSource } from '../types'
import { TimetableSourceCard } from './TimetableSourceCard'

const source: TimetableSource = {
  id: '40000000-0000-4000-8000-000000000001',
  source_ref: 'demo-timetable-v1',
  title: 'Fictional demonstration timetable',
  source_uri: 'data/processed/demo_timetable.json',
  reuse_basis: 'Project-generated fictional data.',
  data_kind: 'demonstration',
  content_sha256: 'a'.repeat(64),
  effective_from: '2026-01-01',
  effective_until: '2028-12-31',
  retrieved_at: null,
  registered_at: '2026-10-12T08:00:00Z',
}

describe('Timetable source card', () => {
  it('displays provenance without implying live updates', () => {
    render(
      <TimetableSourceCard
        source={source}
        sourceRef={source.source_ref}
      />,
    )

    const card = screen.getByRole('region', { name: 'Timetable source' })
    expect(within(card).getByText(source.title)).toBeInTheDocument()
    expect(within(card).getByText('Fictional demonstration data')).toBeInTheDocument()
    expect(within(card).getByText(source.content_sha256)).toBeInTheDocument()
    expect(within(card).getByText(source.source_uri)).toBeInTheDocument()
    expect(within(card).getByText('2026-01-01 to 2028-12-31')).toBeInTheDocument()
    expect(within(card).getByText('No external retrieval recorded')).toBeInTheDocument()
    expect(within(card).getByText(/do not establish a live railway update/))
      .toBeInTheDocument()
    expect(within(card).queryByRole('link')).not.toBeInTheDocument()
  })

  it('explains missing provenance explicitly', () => {
    render(
      <TimetableSourceCard
        source={null}
        sourceRef="unregistered-timetable"
      />,
    )

    expect(screen.getByText('Source reference: unregistered-timetable'))
      .toBeInTheDocument()
    expect(screen.getByText(/Detailed provenance has not been registered/))
      .toBeInTheDocument()
    expect(screen.queryByText('Registered in RailConnect')).not.toBeInTheDocument()
  })

  it('distinguishes external retrieval from registration', () => {
    render(
      <TimetableSourceCard
        source={{ ...source, retrieved_at: '2026-10-10T07:00:00Z' }}
        sourceRef={source.source_ref}
      />,
    )

    expect(screen.getByText('External retrieval')).toBeInTheDocument()
    expect(screen.getByText('Registered in RailConnect')).toBeInTheDocument()
    expect(screen.queryByText('No external retrieval recorded')).not.toBeInTheDocument()
    expect(document.querySelector('time[datetime="2026-10-10T07:00:00Z"]'))
      .toBeInTheDocument()
  })
})
