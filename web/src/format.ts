const NBSP = ' '

// Formats the API money string without turning it into a float: "12345.50" -> "12 345,50".
export function money(value: string): string {
  const negative = value.startsWith('-')
  const [int, frac = '00'] = value.replace('-', '').split('.')
  const grouped = int.replace(/\B(?=(\d{3})+(?!\d))/g, NBSP)
  return `${negative ? '−' : ''}${grouped},${frac.padEnd(2, '0')}`
}

// "−76,50" for a deduction, plain "0,00" when there is nothing to deduct.
export const minus = (value: string) => (/^0+(\.0+)?$/.test(value) ? money(value) : `−${money(value)}`)

export const hhmm = (iso: string) => iso.slice(11, 16)

export function duration(min: number): string {
  if (min < 60) return `${min} мин`
  const h = Math.floor(min / 60)
  const m = min % 60
  return m ? `${h} ч ${m} мин` : `${h} ч`
}

export function plural(n: number, one: string, few: string, many: string): string {
  const mod10 = n % 10
  const mod100 = n % 100
  if (mod10 === 1 && mod100 !== 11) return one
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return few
  return many
}

// Calendar dates are plain "YYYY-MM-DD" strings; built at local noon so no timezone can shift the day.
const toDate = (day: string) => new Date(`${day}T12:00:00`)

export function shiftDay(day: string, delta: number): string {
  const d = toDate(day)
  d.setDate(d.getDate() + delta)
  return isoDay(d)
}

export function isoDay(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

export function todayIn(timeZone: string): string {
  // en-CA formats as YYYY-MM-DD
  return new Intl.DateTimeFormat('en-CA', { timeZone, year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date())
}

export function dayTitle(day: string): string {
  return new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'long' }).format(toDate(day))
}

export function weekday(day: string): string {
  return new Intl.DateTimeFormat('ru-RU', { weekday: 'long' }).format(toDate(day))
}

// "+06:00" for the driver's timezone on that date (handles DST zones too).
export function utcOffset(day: string, time: string, timeZone: string): string {
  const probe = new Date(`${day}T${time}:00Z`)
  const name = new Intl.DateTimeFormat('en-US', { timeZone, timeZoneName: 'longOffset' })
    .formatToParts(probe)
    .find((p) => p.type === 'timeZoneName')?.value
  const match = name?.match(/GMT([+-]\d{2}:\d{2})/)
  return match ? match[1] : '+00:00'
}
