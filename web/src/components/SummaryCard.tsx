import { Banknote, CreditCard } from 'lucide-react'
import type { Summary } from '../api'
import { minus, money, plural } from '../format'

export function SummaryCard({ summary, currency }: { summary: Summary; currency: string }) {
  const revenue = Number(summary.revenue) // width of the split bar only, never shown as money
  const cashShare = revenue > 0 ? (Number(summary.cash.revenue) / revenue) * 100 : 0

  return (
    <section className="rounded-2xl border border-line bg-white p-5" aria-label="Сводка за день">
      <p className="text-sm text-muted">На руки</p>
      <p className="mt-1 text-4xl font-semibold tracking-tight">
        {money(summary.net)} <span className="text-xl font-medium text-muted">{currency === 'KGS' ? 'сом' : currency}</span>
      </p>

      <dl className="mt-5 grid grid-cols-3 gap-3 border-t border-line pt-4">
        <Stat label="Выручка" value={money(summary.revenue)} />
        <Stat label="Комиссия" value={minus(summary.commission)} />
        <Stat label={plural(summary.trips, 'Поездка', 'Поездки', 'Поездок')} value={String(summary.trips)} />
      </dl>

      <div className="mt-5">
        <div className="flex h-2 overflow-hidden rounded-full bg-line" aria-hidden>
          <div className="bg-cash transition-[width] duration-500" style={{ width: `${cashShare}%` }} />
          <div className="bg-card transition-[width] duration-500" style={{ width: `${revenue > 0 ? 100 - cashShare : 0}%` }} />
        </div>
        <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
          <Split icon={<Banknote size={16} />} tone="text-cash" label="Наличные" trips={summary.cash.trips} value={summary.cash.revenue} />
          <Split icon={<CreditCard size={16} />} tone="text-card" label="Карта" trips={summary.card.trips} value={summary.card.revenue} />
        </div>
      </div>
    </section>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs text-muted">{label}</dt>
      <dd className="mt-0.5 text-base font-medium">{value}</dd>
    </div>
  )
}

function Split(props: { icon: React.ReactNode; tone: string; label: string; trips: number; value: string }) {
  return (
    <div>
      <p className={`flex items-center gap-1.5 font-medium ${props.tone}`}>
        {props.icon}
        {props.label}
      </p>
      <p className="mt-0.5">
        {money(props.value)} <span className="text-muted">· {props.trips}</span>
      </p>
    </div>
  )
}
