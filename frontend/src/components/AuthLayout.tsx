import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import Logo from './Logo'
import Marquee from './Marquee'
import authPanel from '../assets/brand/auth-panel.webp'

const POINTS = [
  ['Roster', 'Add your class once. Members never sign up.'],
  ['Link', 'One payment link, confirmed by the gateway.'],
  ['Report', 'A ledger every member can open for themselves.'],
]

const TAPE = ['Free while in beta', 'Set up in one afternoon', 'Members pay in three minutes']

export default function AuthLayout({
  children,
  title,
  subtitle,
}: {
  children: ReactNode
  title: string
  subtitle?: string
}) {
  return (
    <div className="min-h-screen bg-paper-100 lg:grid lg:grid-cols-[1fr_minmax(380px,40%)]">
      {/* form */}
      <div className="flex flex-col items-center justify-center px-4 py-12 sm:px-8">
        <div className="w-full max-w-md">
          <Link to="/" className="mb-10 inline-block">
            <Logo size="lg" />
          </Link>

          <div className="mb-8">
            <h1 className="text-[clamp(1.75rem,4vw,2.25rem)] leading-none">{title}</h1>
            {subtitle && <p className="mt-3 text-[15px] text-ink-600">{subtitle}</p>}
          </div>

          {children}
        </div>
      </div>

      {/* statement panel */}
      <aside className="relative hidden flex-col justify-between overflow-hidden border-l-2 border-ink-900 bg-ink-900 text-paper-100 lg:flex">
        <img
          src={authPanel}
          alt=""
          aria-hidden
          className="pointer-events-none absolute inset-0 h-full w-full object-cover opacity-[0.18]"
        />
        <div className="pointer-events-none absolute inset-0 grid-lines opacity-[0.07]" aria-hidden />

        <div className="relative p-10">
          <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-gold-400">
            AcaFund
          </p>
          <p className="mt-5 max-w-[13ch] font-display text-[clamp(2rem,3.4vw,2.75rem)] uppercase leading-[0.95]">
            See who paid.
            <span className="mt-1 block bg-rose-600 px-2 text-white">See where it went.</span>
          </p>
        </div>

        <div className="relative px-10">
          <ul className="border-t border-paper-100/20">
            {POINTS.map(([label, text]) => (
              <li key={label} className="flex gap-4 border-b border-paper-100/20 py-4">
                <span className="w-16 shrink-0 font-mono text-[11px] uppercase tracking-[0.14em] text-gold-400">
                  {label}
                </span>
                <span className="text-[14px] leading-relaxed text-paper-100/70">{text}</span>
              </li>
            ))}
          </ul>
        </div>

        <Marquee items={TAPE} className="relative border-t-2 border-paper-100/20 py-2.5" />
      </aside>
    </div>
  )
}
