import { Banknote, CreditCard } from 'lucide-react'
import type { Trip } from '../api'
import { duration, hhmm, minus, money } from '../format'

export function TripList({ trips, highlight }: { trips: Trip[]; highlight?: string }) {
  if (trips.length === 0) {
    return <p className="rounded-2xl border border-dashed border-line px-5 py-10 text-center text-muted">В этот день поездок нет</p>
  }
  return (
    <ul className="divide-y divide-line overflow-hidden rounded-2xl border border-line bg-white">
      {trips.map((trip) => (
        <li key={trip.id} className={`flex items-start gap-3 px-4 py-3.5 ${trip.id === highlight ? 'bg-amber-50' : ''}`}>
          <span
            className={`mt-0.5 grid size-8 shrink-0 place-items-center rounded-full ${trip.payment === 'cash' ? 'bg-cash/10 text-cash' : 'bg-card/10 text-card'}`}
            title={trip.payment === 'cash' ? 'Наличные' : 'Карта'}
          >
            {trip.payment === 'cash' ? <Banknote size={16} /> : <CreditCard size={16} />}
          </span>
          <div className="min-w-0 flex-1">
            <p className="font-medium">
              {hhmm(trip.started_at)}–{hhmm(trip.ended_at)}
              {trip.ended_at.slice(0, 10) !== trip.started_at.slice(0, 10) && <span className="ml-1 text-xs text-muted">+1 день</span>}
            </p>
            <p className="text-sm text-muted">
              {duration(trip.duration_min)} · {trip.payment === 'cash' ? 'наличные' : 'карта'}
            </p>
          </div>
          <div className="text-right">
            <p className="font-medium">{money(trip.amount)}</p>
            <p className="text-sm text-muted">{minus(trip.commission)}</p>
          </div>
        </li>
      ))}
    </ul>
  )
}
