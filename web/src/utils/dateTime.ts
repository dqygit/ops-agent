export function formatDateTime(value: string | null | undefined, formatter: Intl.DateTimeFormat, fallback = 'JUST NOW') {
  if (!value) {
    return fallback
  }

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }

  return formatter.format(date)
}
