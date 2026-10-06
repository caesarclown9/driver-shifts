export type Payment = 'cash' | 'card'

export type Trip = {
  id: string
  started_at: string // ISO in the driver's timezone, e.g. 2026-10-06T08:05:00+06:00
  ended_at: string
  duration_min: number
  amount: string // money stays a string end to end
  commission: string
  net: string
  payment: Payment
}

export type Summary = {
  trips: number
  revenue: string
  commission: string
  net: string
  cash: { trips: number; revenue: string }
  card: { trips: number; revenue: string }
}

export type DayResponse = { date: string; timezone: string; currency: string; summary: Summary; trips: Trip[] }
export type DaysResponse = { timezone: string; currency: string; days: { date: string; trips: number }[] }

export type NewTrip = {
  id: string
  started_at: string
  ended_at: string
  amount: string
  payment: Payment
  commission: string
}

export type AddResult =
  | { kind: 'created' | 'duplicate'; trip: Trip }
  | { kind: 'conflict'; message: string }
  | { kind: 'invalid'; fields: Record<string, string> }

async function getJson<T>(url: string): Promise<T> {
  const res = await fetch(url)
  if (!res.ok) throw new Error(`${url}: HTTP ${res.status}`)
  return res.json() as Promise<T>
}

export const fetchDays = () => getJson<DaysResponse>('/api/days')
export const fetchDay = (date: string) => getJson<DayResponse>(`/api/days/${date}`)

export async function addTrip(trip: NewTrip): Promise<AddResult> {
  const res = await fetch('/api/trips', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(trip),
  })
  const body = await res.json().catch(() => null)
  if (res.status === 201) return { kind: 'created', trip: body.trip }
  if (res.status === 200) return { kind: 'duplicate', trip: body.trip }
  if (res.status === 409) return { kind: 'conflict', message: 'Поездка с этим номером уже сохранена с другими данными' }
  if (res.status === 422 && Array.isArray(body?.detail)) {
    const fields: Record<string, string> = {}
    for (const err of body.detail as { loc: (string | number)[]; msg: string }[]) {
      const field = String(err.loc.at(-1))
      fields[field] ??= translateError(err.msg)
    }
    return { kind: 'invalid', fields }
  }
  throw new Error(`Сервер ответил ${res.status}`)
}

const MESSAGES: [RegExp, string][] = [
  [/must be greater than 0/, 'Сумма должна быть больше нуля'],
  [/cannot exceed 1000000/, 'Слишком большая сумма'],
  [/max 2 decimal places|must look like/, 'Число, не больше двух знаков после запятой'],
  [/must be a string/, 'Число, не больше двух знаков после запятой'],
  [/must end after it starts/, 'Окончание должно быть позже начала'],
  [/longer than 24 hours/, 'Поездка не может длиться больше суток'],
  [/commission cannot be negative/, 'Комиссия не может быть отрицательной'],
  [/commission cannot exceed/, 'Комиссия больше суммы поездки'],
  [/timezone/, 'Не указан часовой пояс'],
  [/Field required/, 'Обязательное поле'],
]

function translateError(msg: string): string {
  for (const [re, text] of MESSAGES) if (re.test(msg)) return text
  return msg
}
