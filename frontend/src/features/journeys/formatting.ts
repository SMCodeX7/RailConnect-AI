const timezone = 'Asia/Colombo'

const timestampFormatter = new Intl.DateTimeFormat('en-GB', {
  timeZone: timezone,
  day: '2-digit',
  month: 'short',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
  hourCycle: 'h23',
})

export function getColomboToday(): string {
  const parts = new Intl.DateTimeFormat('en-GB', {
    timeZone: timezone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).formatToParts(new Date())

  const year = parts.find((part) => part.type === 'year')
  const month = parts.find((part) => part.type === 'month')
  const day = parts.find((part) => part.type === 'day')

  if (!year || !month || !day) {
    throw new Error('Unable to determine the local date.')
  }

  return `${year.value}-${month.value}-${day.value}`
}

export function formatJourneyTimestamp(value: string): string {
  return timestampFormatter.format(new Date(value))
}

export function formatDuration(minutes: number): string {
  const hours = Math.floor(minutes / 60)
  const remaining = minutes % 60

  if (hours === 0) return `${remaining} min`
  if (remaining === 0) return `${hours} h`

  return `${hours} h ${remaining} min`
}
