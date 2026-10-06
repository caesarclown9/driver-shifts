import { ChevronLeft, ChevronRight, Plus } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { fetchDay, fetchDays, type DayResponse, type DaysResponse, type Trip } from './api'
import { AddTripSheet } from './components/AddTripSheet'
import { SummaryCard } from './components/SummaryCard'
import { TripList } from './components/TripList'
import { dayTitle, shiftDay, todayIn, weekday } from './format'

export default function App() {
  const [days, setDays] = useState<DaysResponse | null>(null)
  const [day, setDay] = useState<string | null>(null)
  const [data, setData] = useState<DayResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [sheetOpen, setSheetOpen] = useState(false)
  const [toast, setToast] = useState<{ text: string; tripId: string } | null>(null)
  const chips = useRef<HTMLElement>(null)

  useEffect(() => {
    chips.current?.querySelector('[aria-current]')?.scrollIntoView({ block: 'nearest', inline: 'center', behavior: 'smooth' })
  }, [day, days])

  const loadDays = useCallback(async () => {
    const res = await fetchDays()
    setDays(res)
    return res
  }, [])

  // Open on today, or on the last day with trips if today is empty.
  useEffect(() => {
    fetchDays()
      .then((res) => {
        setDays(res)
        const today = todayIn(res.timezone)
        const hasToday = res.days.some((d) => d.date === today)
        setDay(hasToday || res.days.length === 0 ? today : res.days[res.days.length - 1].date)
      })
      .catch((e: Error) => setError(e.message))
  }, [])

  useEffect(() => {
    if (!day) return
    let cancelled = false
    fetchDay(day)
      .then((res) => !cancelled && (setData(res), setError(null)))
      .catch((e: Error) => !cancelled && setError(e.message))
    return () => {
      cancelled = true
    }
  }, [day])

  useEffect(() => {
    if (!toast) return
    const t = setTimeout(() => setToast(null), 3500)
    return () => clearTimeout(t)
  }, [toast])

  async function handleSaved(trip: Trip, duplicate: boolean) {
    setSheetOpen(false)
    const tripDay = trip.started_at.slice(0, 10)
    await loadDays().catch(() => undefined)
    const fresh = await fetchDay(tripDay).catch(() => null)
    if (fresh) setData(fresh)
    setDay(tripDay)
    setToast({ text: duplicate ? 'Эта поездка уже была в дневнике — дубль не создан' : 'Поездка сохранена', tripId: trip.id })
  }

  const tripDays = days?.days ?? []
  const prevWithTrips = day ? [...tripDays].reverse().find((d) => d.date < day)?.date : undefined
  const nextWithTrips = day ? tripDays.find((d) => d.date > day)?.date : undefined
  const shown = data && data.date === day ? data : null

  return (
    <div className="mx-auto min-h-dvh max-w-md px-4 pb-28 pt-[max(1rem,env(safe-area-inset-top))]">
      <header className="flex items-center justify-between gap-2 py-2">
        <NavButton label="Предыдущий день" onClick={() => day && setDay(shiftDay(day, -1))} disabled={!day}>
          <ChevronLeft size={20} />
        </NavButton>
        <label className="relative flex-1 cursor-pointer text-center">
          <span className="block text-xl font-semibold">{day ? dayTitle(day) : '…'}</span>
          <span className="block text-sm capitalize text-muted">
            {day ? weekday(day) : ''}
            {day && days && day === todayIn(days.timezone) ? ' · сегодня' : ''}
          </span>
          {day && (
            <input
              type="date"
              value={day}
              onChange={(e) => e.target.value && setDay(e.target.value)}
              className="absolute inset-0 cursor-pointer opacity-0"
              aria-label="Выбрать дату"
            />
          )}
        </label>
        <NavButton label="Следующий день" onClick={() => day && setDay(shiftDay(day, 1))} disabled={!day}>
          <ChevronRight size={20} />
        </NavButton>
      </header>

      {tripDays.length > 0 && (
        <nav ref={chips} className="no-scrollbar -mx-4 mb-3 flex gap-2 overflow-x-auto px-4 pb-1" aria-label="Дни с поездками">
          {tripDays.map((d) => (
            <button
              key={d.date}
              onClick={() => setDay(d.date)}
              aria-current={d.date === day ? 'date' : undefined}
              className={`shrink-0 rounded-full border px-3 py-1.5 text-sm transition-colors ${d.date === day ? 'border-ink bg-ink text-white' : 'border-line bg-white text-ink'}`}
            >
              {d.date.slice(8, 10)}.{d.date.slice(5, 7)} <span className={d.date === day ? 'text-white/60' : 'text-muted'}>· {d.trips}</span>
            </button>
          ))}
        </nav>
      )}

      {error && (
        <p className="mb-3 rounded-xl bg-danger/10 px-3 py-2 text-sm text-danger" role="alert">
          Не удалось загрузить данные: {error}
        </p>
      )}

      {shown ? (
        <main className="flex flex-col gap-4">
          <SummaryCard summary={shown.summary} currency={shown.currency} />
          {shown.trips.length === 0 && (prevWithTrips || nextWithTrips) && (
            <div className="flex justify-between text-sm">
              {prevWithTrips ? <button className="text-card" onClick={() => setDay(prevWithTrips)}>← {dayTitle(prevWithTrips)}</button> : <span />}
              {nextWithTrips ? <button className="text-card" onClick={() => setDay(nextWithTrips)}>{dayTitle(nextWithTrips)} →</button> : <span />}
            </div>
          )}
          <TripList trips={shown.trips} highlight={toast?.tripId} />
        </main>
      ) : (
        !error && <div className="h-64 animate-pulse rounded-2xl bg-line/50" />
      )}

      <button
        onClick={() => setSheetOpen(true)}
        disabled={!day || !days}
        className="fixed bottom-[max(1.25rem,env(safe-area-inset-bottom))] left-1/2 flex h-14 -translate-x-1/2 items-center gap-2 rounded-full bg-ink px-6 font-medium text-white shadow-lg shadow-ink/20 disabled:opacity-50"
      >
        <Plus size={20} /> Поездка
      </button>

      {toast && (
        <div className="fixed inset-x-4 top-4 mx-auto max-w-md rounded-xl bg-ink px-4 py-3 text-sm text-white shadow-lg" role="status">
          {toast.text}
        </div>
      )}

      {day && days && (
        <AddTripSheet open={sheetOpen} day={day} timezone={days.timezone} onClose={() => setSheetOpen(false)} onSaved={handleSaved} />
      )}
    </div>
  )
}

function NavButton(props: { label: string; onClick: () => void; disabled?: boolean; children: React.ReactNode }) {
  return (
    <button
      onClick={props.onClick}
      disabled={props.disabled}
      aria-label={props.label}
      className="grid size-11 shrink-0 place-items-center rounded-full border border-line bg-white disabled:opacity-40"
    >
      {props.children}
    </button>
  )
}
