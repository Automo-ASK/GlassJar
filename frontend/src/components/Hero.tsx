import { useNavigate } from 'react-router-dom'
import { ArrowRight } from 'lucide-react'
import CollectionFlow from './CollectionFlow'
import Marquee from './Marquee'

const TAPE = [
  'Adeola O. paid ₦5,000',
  'Payment A492 verified',
  'Venue deposit approved by auditor',
  'Blessing E. paid ₦10,000',
  'Duplicate B201 rejected',
  'Dinner fund at 40 percent',
  'Chidi K. paid ₦5,000',
]

/** Headline lines rise out of a clipped box, staggered. */
function Line({ children, delay }: { children: React.ReactNode; delay: number }) {
  return (
    <span className="line-mask">
      <span className="block animate-rise-line" style={{ animationDelay: `${delay}ms` }}>
        {children}
      </span>
    </span>
  )
}

export default function Hero() {
  const navigate = useNavigate()

  return (
    <section className="relative border-b-2 border-ink-900">
      <div className="pointer-events-none absolute inset-0 grid-lines opacity-[0.05]" aria-hidden />

      <div className="relative mx-auto max-w-[1400px] px-4 md:px-8 pt-14 pb-16 md:pt-20">
        <div className="grid gap-12 lg:grid-cols-[1.05fr_minmax(0,540px)] lg:gap-16 items-start">
          {/* ---- statement ---- */}
          <div>
            <div
              className="inline-flex items-center gap-2 border-2 border-ink-900 bg-teal-400 px-3 py-1 animate-fade-in"
              style={{ animationDelay: '700ms' }}
            >
              <span className="h-1.5 w-1.5 rounded-full bg-ink-900 animate-pulse-dot" />
              <span className="font-mono text-[11px] uppercase tracking-[0.18em] text-ink-900">
                Free while in beta
              </span>
            </div>

            {/* Each highlighted line carries its own inline-block so the
                Rosewood field is sized to that line's text. A single spanning
                highlight collides with the line above at this line-height. */}
            <h1 className="mt-6 text-display-lg leading-[0.98]">
              <Line delay={0}>See who paid.</Line>
              {['See where', 'it went.'].map((text, i) => (
                <span
                  key={text}
                  className="mt-2 block animate-fade-up"
                  style={{ animationDelay: `${200 + i * 110}ms` }}
                >
                  <span className="inline-block bg-rose-600 px-3 py-1 text-paper-100">
                    {text}
                  </span>
                </span>
              ))}
            </h1>

            <p
              className="mt-8 max-w-md text-body-lg text-ink-600 animate-fade-up"
              style={{ animationDelay: '520ms' }}
            >
              AcaFund collects your class money through one payment link, confirms every transfer
              automatically, and shows the whole community the same ledger. Members pay without
              creating an account.
            </p>

            <div
              className="mt-9 flex flex-col sm:flex-row gap-3 animate-fade-up"
              style={{ animationDelay: '640ms' }}
            >
              <button
                onClick={() => navigate('/register')}
                className="group inline-flex items-center justify-center gap-2.5 border-2 border-ink-900 bg-rose-600 px-7 py-4 font-display text-[15px] uppercase tracking-[0.02em] text-white shadow-neo transition-all duration-150 hover:-translate-x-0.5 hover:-translate-y-0.5 hover:shadow-neo-lg active:translate-x-px active:translate-y-px active:shadow-neo-sm"
              >
                Start a community
                <ArrowRight size={17} className="transition-transform duration-200 group-hover:translate-x-1" />
              </button>

              <a
                href="#features"
                className="inline-flex items-center justify-center border-2 border-ink-900 bg-paper-0 px-7 py-4 font-display text-[15px] uppercase tracking-[0.02em] text-ink-900 shadow-neo transition-all duration-150 hover:-translate-x-0.5 hover:-translate-y-0.5 hover:shadow-neo-lg active:translate-x-px active:translate-y-px active:shadow-neo-sm"
              >
                See how it works
              </a>
            </div>

            <dl
              className="mt-12 grid grid-cols-3 border-2 border-ink-900 animate-fade-up"
              style={{ animationDelay: '760ms' }}
            >
              {[
                ['3 min', 'To pay'],
                ['₦0', 'For members'],
                ['1 link', 'Per collection'],
              ].map(([value, label], i) => (
                <div key={label} className={`px-4 py-3.5 ${i < 2 ? 'border-r-2 border-ink-900' : ''}`}>
                  <dt className="eyebrow">{label}</dt>
                  <dd data-money className="mt-1 font-display text-[clamp(1.25rem,2.4vw,1.75rem)] leading-none">
                    {value}
                  </dd>
                </div>
              ))}
            </dl>
          </div>

          {/* ---- the ledger ---- */}
          <div className="animate-fade-up lg:mt-2" style={{ animationDelay: '360ms' }}>
            <CollectionFlow />
            <p className="mt-3 font-mono text-[11px] uppercase tracking-[0.16em] text-ink-400">
              Click a member to make them pay
            </p>
          </div>
        </div>
      </div>

      <Marquee
        items={TAPE}
        className="border-t-2 border-ink-900 bg-ink-900 py-2.5 text-paper-100"
      />
    </section>
  )
}
