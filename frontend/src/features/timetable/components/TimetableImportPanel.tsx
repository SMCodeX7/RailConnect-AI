import { useEffect, useRef, useState } from 'react'

import { ApiError } from '../../../shared/api/http'
import {
  encodeImportFiles,
  importTimetable,
  MAX_DATASET_BYTES,
  MAX_METADATA_BYTES,
  previewTimetableImport,
} from '../api'
import type {
  TimetableImportInput,
  TimetableImportPreview,
  TimetableImportResult,
} from '../api'

interface TimetableImportPanelProps {
  csrfToken: string
  onSessionInvalid: () => void
}

interface ReviewedImport {
  input: TimetableImportInput
  preview: TimetableImportPreview
}

type Action = 'preview' | 'import'

function failureMessage(error: unknown, action: Action): string {
  if (error instanceof ApiError) {
    if (error.status === 403) {
      return 'Timetable access was denied. Refresh your staff session and try again.'
    }

    if (error.status === 409) {
      return 'The import conflicts with the current timetable. Preview the files again.'
    }

    if (error.status === 413) {
      return 'The selected files exceed the server upload size limit.'
    }

    if (error.status === 422) {
      return 'The server could not validate the timetable or source metadata file.'
    }
  }

  if (action === 'import') {
    return 'The import outcome could not be confirmed. Preview again to check whether it was recorded.'
  }

  return 'Unable to preview the selected files. Check the files and try again.'
}

export function TimetableImportPanel({
  csrfToken,
  onSessionInvalid,
}: TimetableImportPanelProps) {
  const activeRequest = useRef<AbortController | null>(null)
  const [dataset, setDataset] = useState<File | null>(null)
  const [metadata, setMetadata] = useState<File | null>(null)
  const [reviewed, setReviewed] = useState<ReviewedImport | null>(null)
  const [result, setResult] = useState<TimetableImportResult | null>(null)
  const [action, setAction] = useState<Action | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => () => activeRequest.current?.abort(), [])

  function clearReview() {
    setReviewed(null)
    setResult(null)
    setError(null)
  }

  async function run(nextAction: Action) {
    if (activeRequest.current || !dataset || !metadata) return
    if (nextAction === 'import' && !reviewed?.preview.can_import) return

    clearReview()

    if (dataset.size === 0 || dataset.size > MAX_DATASET_BYTES) {
      setError('Select a timetable dataset between 1 byte and 5 MiB.')
      return
    }

    if (metadata.size === 0 || metadata.size > MAX_METADATA_BYTES) {
      setError('Select a source metadata file between 1 byte and 64 KiB.')
      return
    }

    const controller = new AbortController()
    activeRequest.current = controller
    setAction(nextAction)

    try {
      if (nextAction === 'import' && reviewed) {
        const receipt = await importTimetable(reviewed.input, controller.signal, csrfToken)
        if (!controller.signal.aborted) setResult(receipt)
      } else {
        const input = await encodeImportFiles(dataset, metadata)
        if (controller.signal.aborted) return

        const preview = await previewTimetableImport(input, controller.signal, csrfToken)
        if (!controller.signal.aborted) setReviewed({ input, preview })
      }
    } catch (failure) {
      if (controller.signal.aborted) return

      if (failure instanceof ApiError && failure.status === 401) {
        onSessionInvalid()
      } else {
        setError(failureMessage(failure, nextAction))
      }
    } finally {
      activeRequest.current = null
      if (!controller.signal.aborted) setAction(null)
    }
  }

  const preview = reviewed?.preview

  return (
    <section aria-labelledby="timetable-import-heading" aria-busy={action !== null}>
      <h3 id="timetable-import-heading">Timetable import</h3>

      <p className="muted">
        Upload a demonstration timetable and its source metadata. Dated runs
        are prepared separately.
      </p>

      <form
        onSubmit={(event) => {
          event.preventDefault()
          void run('preview')
        }}
      >
        <fieldset className="report-fields" disabled={action !== null}>
          <legend>Import files</legend>

          <div className="report-field">
            <label htmlFor="timetable-dataset">Timetable dataset JSON</label>
            <input
              id="timetable-dataset"
              type="file"
              accept=".json,application/json"
              onChange={(event) => {
                setDataset(event.target.files?.[0] ?? null)
                clearReview()
              }}
            />
          </div>

          <div className="report-field">
            <label htmlFor="timetable-metadata">Source metadata JSON</label>
            <input
              id="timetable-metadata"
              type="file"
              accept=".json,application/json"
              onChange={(event) => {
                setMetadata(event.target.files?.[0] ?? null)
                clearReview()
              }}
            />
          </div>

          <button type="submit" disabled={!dataset || !metadata}>
            Preview import
          </button>
        </fieldset>
      </form>

      {action && (
        <p role="status">
          {action === 'preview' ? 'Checking timetable files…' : 'Importing timetable…'}
        </p>
      )}
      {error && <p className="error" role="alert">{error}</p>}

      {preview && (
        <>
          <h4>Import preview</h4>
          <p role="status">
            {preview.can_import ? 'Preview ready for confirmation.' : 'Resolve conflicts before importing.'}
          </p>
          <dl className="staff-account-details">
            <div><dt>Source reference</dt><dd>{preview.source_ref}</dd></div>
            <div><dt>Dataset SHA-256</dt><dd style={{ overflowWrap: 'anywhere' }}>{preview.content_sha256}</dd></div>
            <div><dt>Source registered</dt><dd>{preview.source_registered ? 'Yes' : 'No'}</dd></div>
            <div><dt>Import already recorded</dt><dd>{preview.import_recorded ? 'Yes' : 'No'}</dd></div>
            <div><dt>New services</dt><dd>{preview.new_service_codes.length}</dd></div>
            <div><dt>Existing services</dt><dd>{preview.existing_service_codes.length}</dd></div>
            <div><dt>Stops to insert</dt><dd>{preview.stops_to_insert}</dd></div>
          </dl>

          <details>
            <summary>Service codes</summary>
            <p>New services: {preview.new_service_codes.join(', ') || 'None'}.</p>
            <p>Existing services: {preview.existing_service_codes.join(', ') || 'None'}.</p>
          </details>

          {preview.conflicts.length > 0 && (
            <ul aria-label="Import conflicts">
              {preview.conflicts.map((conflict, index) => (
                <li key={`${index}:${conflict}`}>{conflict}</li>
              ))}
            </ul>
          )}

          <button
            type="button"
            disabled={action !== null || !preview.can_import}
            onClick={() => void run('import')}
          >
            Confirm import
          </button>
        </>
      )}

      {result && (
        <>
          <h4>Import receipt</h4>
          <p role="status">
            {result.summary_created
              ? 'Timetable import recorded.'
              : 'Existing import verified. The original record was retained.'}
          </p>
          <dl className="staff-account-details">
            <div><dt>Import reference</dt><dd>{result.import_id}</dd></div>
            <div><dt>Source reference</dt><dd>{result.source_ref}</dd></div>
            <div>
              <dt>Original importing staff reference</dt>
              <dd>{result.imported_by_user_id ?? 'No staff account recorded'}</dd>
            </div>
            <div><dt>Services inserted</dt><dd>{result.inserted_services}</dd></div>
            <div><dt>Existing services verified</dt><dd>{result.existing_services}</dd></div>
            <div><dt>Stops inserted</dt><dd>{result.inserted_stops}</dd></div>
          </dl>
        </>
      )}
    </section>
  )
}
