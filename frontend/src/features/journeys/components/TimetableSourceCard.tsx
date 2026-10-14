import { formatJourneyTimestamp } from '../formatting'
import type { TimetableSource } from '../types'

interface TimetableSourceCardProps {
  source: TimetableSource | null
  sourceRef: string
}

export function TimetableSourceCard({
  source,
  sourceRef,
}: TimetableSourceCardProps) {
  if (!source) {
    return (
      <section className="source-card" aria-label="Timetable source">
        <h4>Timetable source</h4>
        <p>Source reference: {sourceRef}</p>
        <p>
          Detailed provenance has not been registered for this timetable.
          No live-update freshness is established.
        </p>
      </section>
    )
  }

  return (
    <section className="source-card" aria-label="Timetable source">
      <h4>Timetable source</h4>
      <p>{source.title}</p>

      <dl className="source-metadata">
        <div>
          <dt>Data kind</dt>
          <dd>
            {source.data_kind === 'demonstration'
              ? 'Fictional demonstration data'
              : 'Observed data'}
          </dd>
        </div>
        <div>
          <dt>Source reference</dt>
          <dd>{source.source_ref}</dd>
        </div>
        <div>
          <dt>Source location</dt>
          <dd><code>{source.source_uri}</code></dd>
        </div>
        <div>
          <dt>Effective period</dt>
          <dd>{source.effective_from} to {source.effective_until}</dd>
        </div>
        <div>
          <dt>Reuse basis</dt>
          <dd>{source.reuse_basis}</dd>
        </div>
        <div>
          <dt>Registered in RailConnect</dt>
          <dd>
            <time dateTime={source.registered_at}>
              {formatJourneyTimestamp(source.registered_at)}
            </time>
          </dd>
        </div>
        <div>
          <dt>External retrieval</dt>
          <dd>
            {source.retrieved_at ? (
              <time dateTime={source.retrieved_at}>
                {formatJourneyTimestamp(source.retrieved_at)}
              </time>
            ) : (
              'No external retrieval recorded'
            )}
          </dd>
        </div>
        <div>
          <dt>Dataset SHA-256</dt>
          <dd><code>{source.content_sha256}</code></dd>
        </div>
      </dl>

      <p className="muted">
        Registration and retrieval times do not establish a live railway update.
      </p>
    </section>
  )
}
