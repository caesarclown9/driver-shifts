import { Banknote, CreditCard, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { addTrip, type Payment, type Trip } from '../api'
import { shiftDay, utcOffset } from '../format'

type Props = {
  open: boolean
  day: string
  timezone: string
  onClose: () => void
  onSaved: (trip: Trip, duplicate: boolean) => void
}

type Form = { day: string; start: string; end: string; overnight: boolean; amount: string; commission: string; payment: Payment }

const emptyForm = (day: string): Form => ({ day, start: '', end: '', overnight: false, amount: '', commission: '', payment: 'cash' })

const normalizeMoney = (v: string) => v.trim().replace(/\s/g, '').replace(',', '.')

export function AddTripSheet({ open, day, timezone, onClose, onSaved }: Props) {
  const dialog = useRef<HTMLDialogElement>(null)
  const [form, setForm] = useState<Form>(() => emptyForm(day))
  // One id per trip being entered: a retry after a timeout resends the same id and cannot create a second row.
  const [tripId, setTripId] = useState(() => crypto.randomUUID())
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [banner, setBanner] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    const el = dialog.current
    if (!el) return
    if (open && !el.open) {
      setForm(emptyForm(day))
      setTripId(crypto.randomUUID())
      setErrors({})
      setBanner(null)
      el.showModal()
    }
    if (!open && el.open) el.close()
  }, [open, day])

  const set = <K extends keyof Form>(key: K, value: Form[K]) => {
    setForm((f) => ({ ...f, [key]: value }))
    // Editing the trip makes it a different trip: a new id, so it is not mistaken for a conflict.
    setTripId(crypto.randomUUID())
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    const local: Record<string, string> = {}
    if (!form.start) local.started_at = 'Укажите время начала'
    if (!form.end) local.ended_at = 'Укажите время окончания'
    if (!form.amount.trim()) local.amount = 'Укажите сумму'
    if (!form.commission.trim()) local.commission = 'Укажите комиссию (0, если нет)'
    setErrors(local)
    setBanner(null)
    if (Object.keys(local).length) return

    const endDay = form.overnight ? shiftDay(form.day, 1) : form.day
    setSaving(true)
    try {
      const result = await addTrip({
        id: tripId,
        started_at: `${form.day}T${form.start}:00${utcOffset(form.day, form.start, timezone)}`,
        ended_at: `${endDay}T${form.end}:00${utcOffset(endDay, form.end, timezone)}`,
        amount: normalizeMoney(form.amount),
        commission: normalizeMoney(form.commission),
        payment: form.payment,
      })
      if (result.kind === 'invalid') setErrors(result.fields)
      else if (result.kind === 'conflict') setBanner(result.message)
      else onSaved(result.trip, result.kind === 'duplicate')
    } catch (err) {
      setBanner(`Не удалось сохранить: ${err instanceof Error ? err.message : 'нет связи'}. Нажмите ещё раз — дубля не будет.`)
    } finally {
      setSaving(false)
    }
  }

  return (
    <dialog
      ref={dialog}
      onClose={onClose}
      className="m-0 mt-auto w-full max-w-none rounded-t-3xl bg-white p-0 text-ink sm:m-auto sm:max-w-md sm:rounded-3xl"
    >
      <form onSubmit={submit} noValidate className="flex flex-col gap-4 p-5 pb-[max(1.25rem,env(safe-area-inset-bottom))]">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Новая поездка</h2>
          <button type="button" onClick={onClose} className="grid size-9 place-items-center rounded-full hover:bg-paper" aria-label="Закрыть">
            <X size={18} />
          </button>
        </div>

        <Field label="Дата" error={errors.day}>
          <input type="date" value={form.day} onChange={(e) => set('day', e.target.value)} className={inputCls(false)} required />
        </Field>

        <div className="grid grid-cols-2 gap-3">
          <Field label="Начало" error={errors.started_at}>
            <input type="time" value={form.start} onChange={(e) => set('start', e.target.value)} className={inputCls(!!errors.started_at)} />
          </Field>
          <Field label="Окончание" error={errors.ended_at}>
            <input type="time" value={form.end} onChange={(e) => set('end', e.target.value)} className={inputCls(!!errors.ended_at)} />
          </Field>
        </div>
        <label className="-mt-2 flex items-center gap-2 text-sm text-muted">
          <input type="checkbox" checked={form.overnight} onChange={(e) => set('overnight', e.target.checked)} className="size-4 accent-ink" />
          Закончилась после полуночи
        </label>

        <div className="grid grid-cols-2 gap-3">
          <Field label="Сумма, сом" error={errors.amount}>
            <input inputMode="decimal" placeholder="350" value={form.amount} onChange={(e) => set('amount', e.target.value)} className={inputCls(!!errors.amount)} />
          </Field>
          <Field label="Комиссия, сом" error={errors.commission}>
            <input inputMode="decimal" placeholder="52,50" value={form.commission} onChange={(e) => set('commission', e.target.value)} className={inputCls(!!errors.commission)} />
          </Field>
        </div>

        <fieldset>
          <legend className="mb-1.5 text-sm text-muted">Оплата</legend>
          <div className="grid grid-cols-2 gap-2 rounded-xl bg-paper p-1">
            <PayOption active={form.payment === 'cash'} onClick={() => set('payment', 'cash')} icon={<Banknote size={16} />} label="Наличные" />
            <PayOption active={form.payment === 'card'} onClick={() => set('payment', 'card')} icon={<CreditCard size={16} />} label="Карта" />
          </div>
          {errors.payment && <p className="mt-1 text-sm text-danger">{errors.payment}</p>}
        </fieldset>

        {banner && <p className="rounded-xl bg-danger/10 px-3 py-2 text-sm text-danger" role="alert">{banner}</p>}

        <button type="submit" disabled={saving} className="h-12 rounded-xl bg-ink font-medium text-white transition-opacity disabled:opacity-60">
          {saving ? 'Сохраняю…' : 'Сохранить'}
        </button>
      </form>
    </dialog>
  )
}

const inputCls = (bad: boolean) =>
  `h-11 w-full rounded-xl border bg-white px-3 text-base outline-none focus:border-ink ${bad ? 'border-danger' : 'border-line'}`

function Field({ label, error, children }: { label: string; error?: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-sm text-muted">{label}</span>
      {children}
      {error && <span className="mt-1 block text-sm text-danger">{error}</span>}
    </label>
  )
}

function PayOption(props: { active: boolean; onClick: () => void; icon: React.ReactNode; label: string }) {
  return (
    <button
      type="button"
      onClick={props.onClick}
      aria-pressed={props.active}
      className={`flex h-10 items-center justify-center gap-2 rounded-lg text-sm font-medium transition-colors ${props.active ? 'bg-white shadow-sm' : 'text-muted'}`}
    >
      {props.icon}
      {props.label}
    </button>
  )
}
