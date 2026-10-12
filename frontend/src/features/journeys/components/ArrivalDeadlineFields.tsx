interface ArrivalDeadlineFieldsProps {
  travelDate: string
  arriveBefore: string
  arrivalDate: string
  disabled: boolean
  onTimeChange: (value: string) => void
  onDateChange: (value: string) => void
}

export function ArrivalDeadlineFields({
  travelDate,
  arriveBefore,
  arrivalDate,
  disabled,
  onTimeChange,
  onDateChange,
}: ArrivalDeadlineFieldsProps) {
  const invalidDate = Boolean(
    arriveBefore && arrivalDate && arrivalDate < travelDate,
  )

  return (
    <fieldset className="arrival-deadline-fields" disabled={disabled}>
      <legend>Optional arrival deadline</legend>

      <div className="station-grid">
        <div className="field">
          <label htmlFor="arrive-before">Arrive by</label>
          <input
            id="arrive-before"
            type="time"
            step="60"
            value={arriveBefore}
            aria-describedby="arrival-deadline-help"
            onChange={(event) => onTimeChange(event.target.value)}
          />
        </div>

        <div className="field">
          <label htmlFor="arrival-deadline-date">Arrival deadline date</label>
          <input
            id="arrival-deadline-date"
            type="date"
            value={arrivalDate}
            min={travelDate || undefined}
            disabled={disabled || !arriveBefore}
            aria-invalid={invalidDate || undefined}
            aria-describedby={
              invalidDate
                ? 'arrival-deadline-help arrival-deadline-error'
                : 'arrival-deadline-help'
            }
            onChange={(event) => onDateChange(event.target.value)}
          />
        </div>
      </div>

      <p id="arrival-deadline-help" className="muted">
        Times use Asia/Colombo. Leave the time blank for no deadline.
        Without an arrival date, the deadline uses your travel date.
        Choose the following date for an overnight arrival.
      </p>

      {invalidDate && (
        <p id="arrival-deadline-error" role="alert">
          The arrival deadline date cannot precede the travel date.
        </p>
      )}
    </fieldset>
  )
}
