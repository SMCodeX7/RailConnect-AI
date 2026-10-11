import type { Station } from '../types'

interface StationSelectProps {
  id: string
  label: string
  value: string
  stations: Station[]
  excludedId: string
  disabled: boolean
  onChange: (value: string) => void
}

export function StationSelect({
  id,
  label,
  value,
  stations,
  excludedId,
  disabled,
  onChange,
}: StationSelectProps) {
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <select
        id={id}
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
      >
        <option value="">Select a station</option>
        {stations.map((station) => (
          <option
            key={station.id}
            value={station.id}
            disabled={station.id === excludedId}
          >
            {station.name}
          </option>
        ))}
      </select>
    </div>
  )
}
