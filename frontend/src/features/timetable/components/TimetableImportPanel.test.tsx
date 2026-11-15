import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from '../../../shared/api/http'
import { importTimetable, previewTimetableImport } from '../api'
import type { TimetableImportPreview } from '../api'
import { TimetableImportPanel } from './TimetableImportPanel'

vi.mock('../api', async (importOriginal) => ({
  ...await importOriginal<typeof import('../api')>(),
  importTimetable: vi.fn(),
  previewTimetableImport: vi.fn(),
}))

const previewMock = vi.mocked(previewTimetableImport)
const importMock = vi.mocked(importTimetable)

const ready: TimetableImportPreview = {
  source_ref: 'demo-timetable-test',
  content_sha256: 'a'.repeat(64),
  source_registered: false,
  import_recorded: false,
  new_service_codes: ['DEMO_TEST'],
  existing_service_codes: [],
  stops_to_insert: 2,
  conflicts: [],
  can_import: true,
}

async function selectFiles(onSessionInvalid = vi.fn()) {
  const user = userEvent.setup()
  render(<TimetableImportPanel csrfToken="test-csrf" onSessionInvalid={onSessionInvalid} />)

  const dataset = screen.getByLabelText('Timetable dataset JSON')
  const metadata = screen.getByLabelText('Source metadata JSON')

  expect(screen.getByRole('button', { name: 'Preview import' })).toBeDisabled()
  await user.upload(dataset, new File(['{}\r\n'], 'dataset.json', { type: 'application/json' }))
  await user.upload(metadata, new File(['{}'], 'source.json', { type: 'application/json' }))

  return { user, dataset, metadata, onSessionInvalid }
}

describe('Timetable import panel', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    previewMock.mockResolvedValue(ready)
    importMock.mockResolvedValue({
      source_id: 'source-id',
      source_ref: ready.source_ref,
      content_sha256: ready.content_sha256,
      import_id: 'import-id',
      summary_created: true,
      imported_by_user_id: 'administrator-id',
      inserted_services: 1,
      existing_services: 0,
      inserted_stops: 2,
    })
  })

  afterEach(cleanup)

  it('previews the exact file bytes and imports only after confirmation', async () => {
    const { user } = await selectFiles()
    await user.click(screen.getByRole('button', { name: 'Preview import' }))

    const confirm = await screen.findByRole('button', { name: 'Confirm import' })
    expect(importMock).not.toHaveBeenCalled()
    const expectedInput = {
      dataset_base64: 'e30NCg==',
      metadata_base64: 'e30=',
    }
    expect(previewMock).toHaveBeenCalledWith(
      expectedInput,
      expect.any(AbortSignal),
      'test-csrf',
    )

    await user.click(confirm)

    expect(await screen.findByText('Timetable import recorded.')).toBeInTheDocument()
    expect(screen.getByText('import-id')).toBeInTheDocument()
    expect(importMock).toHaveBeenCalledTimes(1)
    expect(importMock).toHaveBeenCalledWith(
      expectedInput,
      expect.any(AbortSignal),
      'test-csrf',
    )
  })

  it('shows preview conflicts and blocks confirmation', async () => {
    previewMock.mockResolvedValue({
      ...ready,
      can_import: false,
      conflicts: ['Missing stations: DEMO_TEST'],
    })

    const { user } = await selectFiles()
    await user.click(screen.getByRole('button', { name: 'Preview import' }))

    expect(await screen.findByText('Missing stations: DEMO_TEST')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Confirm import' })).toBeDisabled()
    expect(importMock).not.toHaveBeenCalled()
  })

  it('clears the preview when a selected file changes', async () => {
    const { user, metadata } = await selectFiles()
    await user.click(screen.getByRole('button', { name: 'Preview import' }))
    await screen.findByRole('button', { name: 'Confirm import' })

    await user.upload(
      metadata,
      new File(['{"title":"Changed"}'], 'updated.json', { type: 'application/json' }),
    )

    expect(screen.queryByRole('button', { name: 'Confirm import' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Preview import' })).toBeEnabled()
  })

  it('requires a fresh preview after an uncertain import outcome', async () => {
    importMock.mockRejectedValue(new Error('Connection interrupted'))

    const { user } = await selectFiles()
    await user.click(screen.getByRole('button', { name: 'Preview import' }))
    await user.click(await screen.findByRole('button', { name: 'Confirm import' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'The import outcome could not be confirmed',
    )
    expect(screen.queryByRole('button', { name: 'Confirm import' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Preview import' })).toBeEnabled()
    expect(importMock).toHaveBeenCalledTimes(1)
  })

  it('requests a staff session refresh after a 401', async () => {
    previewMock.mockRejectedValue(
      new ApiError('Authentication required', 401, 'UNAUTHENTICATED', null, null),
    )

    const { user, onSessionInvalid } = await selectFiles()
    await user.click(screen.getByRole('button', { name: 'Preview import' }))
    await screen.findByRole('button', { name: 'Preview import' })

    await vi.waitFor(() => expect(onSessionInvalid).toHaveBeenCalledTimes(1))
    expect(importMock).not.toHaveBeenCalled()
  })
})
