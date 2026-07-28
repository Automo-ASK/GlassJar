import { Check, X } from 'lucide-react'
import { useInView } from '../lib/useInView'

/*
 * Each feature shows the artefact it actually produces, built from type and
 * blocks. A treasury product should be able to show its own paperwork.
 */

/* Roster: the class list, with no signups attached to it */
export function RosterList() {
  const members = [
    { name: 'Adeola Okonkwo', paid: true },
    { name: 'Chidi Kamara', paid: true },
    { name: 'Blessing Eze', paid: true },
    { name: 'Tunde Adeyemi', paid: false },
    { name: 'Ngozi Anozie', paid: true },
  ]

  return (
    <div className="flex h-full flex-col justify-center">
      <p className="eyebrow">Roster · Stats 200</p>

      <ul className="mt-3 border-2 border-ink-900 bg-paper-0">
        {members.map(({ name, paid }) => (
          <li
            key={name}
            className="flex items-center justify-between gap-3 border-b border-ink-100 px-3 py-2 last:border-b-0"
          >
            <span className="truncate text-[13px] font-medium">{name}</span>
            <span
              className={`shrink-0 border-2 border-ink-900 px-1.5 font-mono text-[9px] font-bold uppercase tracking-[0.1em] ${
                paid ? 'bg-teal-400 text-ink-900' : 'bg-paper-200 text-ink-500'
              }`}
            >
              {paid ? 'Paid' : 'Unpaid'}
            </span>
          </li>
        ))}
      </ul>

      <p className="mt-3 font-mono text-[11px] text-ink-500">
        4 of 5 paid. None of them signed up.
      </p>
    </div>
  )
}

/* Collection: money arrives on whatever rail the student has */
export function Channels() {
  const { ref, inView } = useInView<HTMLDivElement>()
  const rows = [
    { label: 'Bank transfer', amount: '₦1,240,000', pct: 62 },
    { label: 'USSD', amount: '₦620,000', pct: 31 },
    { label: 'Card', amount: '₦140,000', pct: 7 },
  ]

  return (
    <div ref={ref} className="flex h-full flex-col justify-center gap-3">
      <p className="eyebrow">Matched automatically</p>

      {rows.map(({ label, amount, pct }, i) => (
        <div key={label} className="border-2 border-ink-900 bg-paper-0 p-3">
          <div className="flex items-baseline justify-between gap-3">
            <span className="text-[13px] font-semibold">{label}</span>
            <span data-money className="font-mono text-[12px] font-bold">{amount}</span>
          </div>
          <div className="mt-2 h-2 bg-ink-100">
            <div
              className={`h-full origin-left bg-ink-900 ${inView ? 'animate-bar-grow' : ''}`}
              style={{
                width: `${pct}%`,
                animationDelay: `${i * 140}ms`,
                transform: inView ? undefined : 'scaleX(0)',
              }}
            />
          </div>
        </div>
      ))}
    </div>
  )
}

/* Verification: the gateway confirms it, so a screenshot proves nothing */
export function ReceiptStamp() {
  const { ref, inView } = useInView<HTMLDivElement>()

  return (
    <div ref={ref} className="flex h-full items-center justify-center">
      <div className="relative w-full max-w-[240px] border-2 border-ink-900 bg-paper-0 p-4">
        <p className="eyebrow">Payment A492</p>
        <p data-money className="mt-2 font-display text-[30px] leading-none">₦5,000</p>

        <div className="mt-3 space-y-1.5">
          {['Confirmed by gateway', 'Payer matched to roster', 'Not a duplicate'].map((line) => (
            <p key={line} className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.1em]">
              <Check size={11} strokeWidth={3} className="text-teal-700" />
              {line}
            </p>
          ))}
          <p className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.1em] text-ink-400 line-through">
            <X size={11} strokeWidth={3} className="text-rose-600" />
            Screenshot B201
          </p>
        </div>

        <span
          className={`absolute -right-3 top-6 border-2 border-teal-700 bg-paper-0 px-2 py-0.5 font-display text-[13px] uppercase tracking-[0.06em] text-teal-700 ${
            inView ? 'animate-stamp-in' : 'opacity-0'
          }`}
          style={{ animationDelay: '260ms' }}
        >
          Verified
        </span>
      </div>
    </div>
  )
}

/* Approval: treasurer submits, an independent auditor signs off */
export function ApprovalChain() {
  const steps = [
    { role: 'Treasurer', action: 'Submitted with receipt', state: 'done' },
    { role: 'Auditor', action: 'Approved 12 Mar', state: 'done' },
    { role: 'Payout', action: 'Released to vendor', state: 'live' },
  ]

  return (
    <div className="flex h-full flex-col justify-center">
      <div className="border-2 border-ink-900 bg-paper-0">
        <div className="flex items-baseline justify-between border-b-2 border-ink-900 px-3 py-2">
          <span className="font-mono text-[10px] uppercase tracking-[0.14em]">Venue deposit</span>
          <span data-money className="font-mono text-[12px] font-bold text-rose-600">₦150,000</span>
        </div>

        <ol>
          {steps.map(({ role, action, state }, i) => (
            <li key={role} className="flex items-start gap-3 border-b border-ink-100 px-3 py-2.5 last:border-b-0">
              <span
                className={`mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center border-2 border-ink-900 ${
                  state === 'done' ? 'bg-teal-400' : 'bg-gold-400'
                }`}
                aria-hidden
              >
                {state === 'done' && <Check size={9} strokeWidth={4} className="text-ink-900" />}
              </span>
              <span className="min-w-0">
                <span className="block font-mono text-[10px] uppercase tracking-[0.12em] text-ink-500">
                  Step {i + 1} · {role}
                </span>
                <span className="block text-[13px] font-medium">{action}</span>
              </span>
            </li>
          ))}
        </ol>
      </div>

      <p className="mt-3 font-mono text-[11px] text-ink-500">
        No single person can move money alone.
      </p>
    </div>
  )
}

/* Report: the document the next rep inherits */
export function ReportCover() {
  return (
    <div className="flex h-full items-center justify-center">
      <div className="w-full max-w-[240px] border-2 border-paper-100 bg-ink-800 p-5 text-paper-100">
        <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-gold-400">
          Transparency report
        </p>
        <p className="mt-3 font-display text-[22px] leading-[0.95] uppercase">
          Stats 200
          <br />
          2025/26
        </p>

        <div className="mt-4 space-y-2">
          {['Collected', 'Spent', 'Balance', 'Approvals'].map((l) => (
            <div key={l} className="flex items-center justify-between gap-2">
              <span className="font-mono text-[9px] uppercase tracking-[0.1em] text-paper-100/60">{l}</span>
              <span className="h-px flex-1 bg-paper-100/25" />
              <span className="h-1.5 w-8 bg-gold-400" />
            </div>
          ))}
        </div>

        <p className="mt-5 border-t border-paper-100/25 pt-2 font-mono text-[9px] uppercase tracking-[0.12em] text-paper-100/60">
          Open to every member
        </p>
      </div>
    </div>
  )
}
