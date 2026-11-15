import { postJson } from '../../shared/api/http'

const IMPORT_URL = '/api/v1/staff/timetable/imports'

export const MAX_DATASET_BYTES = 5 * 1024 * 1024
export const MAX_METADATA_BYTES = 64 * 1024

export interface TimetableImportInput {
  dataset_base64: string
  metadata_base64: string
}

export interface TimetableImportPreview {
  source_ref: string
  content_sha256: string
  source_registered: boolean
  import_recorded: boolean
  new_service_codes: string[]
  existing_service_codes: string[]
  stops_to_insert: number
  conflicts: string[]
  can_import: boolean
}

export interface TimetableImportResult {
  source_id: string
  source_ref: string
  content_sha256: string
  import_id: string
  summary_created: boolean
  imported_by_user_id: string | null
  inserted_services: number
  existing_services: number
  inserted_stops: number
}

function readFileAsBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()

    reader.onload = () => {
      const result = reader.result
      const separator = typeof result === 'string' ? result.indexOf(',') : -1

      if (typeof result !== 'string' || separator < 0) {
        reject(new Error('Unable to encode the selected file.'))
        return
      }

      resolve(result.slice(separator + 1))
    }

    reader.onerror = () => reject(new Error('Unable to read the selected file.'))
    reader.onabort = () => reject(new Error('File reading was interrupted.'))
    reader.readAsDataURL(file)
  })
}

export async function encodeImportFiles(
  dataset: File,
  metadata: File,
): Promise<TimetableImportInput> {
  const [datasetBase64, metadataBase64] = await Promise.all([
    readFileAsBase64(dataset),
    readFileAsBase64(metadata),
  ])

  return {
    dataset_base64: datasetBase64,
    metadata_base64: metadataBase64,
  }
}

export function previewTimetableImport(
  input: TimetableImportInput,
  signal: AbortSignal,
  csrfToken: string,
): Promise<TimetableImportPreview> {
  return postJson<TimetableImportPreview>(
    `${IMPORT_URL}/preview`,
    input,
    signal,
    csrfToken,
  )
}

export function importTimetable(
  input: TimetableImportInput,
  signal: AbortSignal,
  csrfToken: string,
): Promise<TimetableImportResult> {
  return postJson<TimetableImportResult>(IMPORT_URL, input, signal, csrfToken)
}
