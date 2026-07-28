import { useNavigate } from 'react-router-dom'
import { ArrowRight } from 'lucide-react'
import { useReveal } from '../lib/useReveal'
import Marquee from './Marquee'

const TAPE = [
  'Free while in beta',
  'No card required',
  'Set up in one afternoon',
  'Your books stay yours',
]

export default function CTA() {
  const ref = useReveal<HTMLElement>({ stagger: 80 })
  const navigate = useNavigate()

  return (
    <section ref={ref} id="about" className="border-b-2 border-ink-900 bg-rose-600 text-white">
      <div className="mx-auto max-w-[1400px] px-4 md:px-8 py-20 md:py-28">
        <div className="grid gap-10 lg:grid-cols-[1.3fr_1fr] lg:items-end">
          <div>
            <p data-reveal className="font-mono text-[11px] uppercase tracking-[0.18em] text-white/70">
              Start a chapter
            </p>
            <h2 data-reveal className="mt-4 max-w-[13ch] text-display-md">
              Give your class its books back
            </h2>
          </div>

          <div data-reveal className="lg:pb-2">
            <p className="max-w-md text-body-lg text-white/85">
              Takes one afternoon to set up. Costs nothing while we are in beta. The next rep will
              thank you.
            </p>

            <div className="mt-8 flex flex-col sm:flex-row gap-3">
              <button
                onClick={() => navigate('/register')}
                className="group inline-flex items-center justify-center gap-2.5 border-2 border-ink-900 bg-gold-400 px-7 py-4 font-display text-[15px] uppercase text-ink-900 shadow-neo transition-all duration-150 hover:-translate-x-0.5 hover:-translate-y-0.5 hover:shadow-neo-lg active:translate-x-px active:translate-y-px active:shadow-neo-sm"
              >
                Create a chapter
                <ArrowRight size={17} className="transition-transform duration-200 group-hover:translate-x-1" />
              </button>

              <button
                onClick={() => navigate('/login')}
                className="inline-flex items-center justify-center border-2 border-ink-900 bg-white px-7 py-4 font-display text-[15px] uppercase text-ink-900 shadow-neo transition-all duration-150 hover:-translate-x-0.5 hover:-translate-y-0.5 hover:shadow-neo-lg active:translate-x-px active:translate-y-px active:shadow-neo-sm"
              >
                Sign in
              </button>
            </div>
          </div>
        </div>
      </div>

      <Marquee
        items={TAPE}
        reverse
        className="border-t-2 border-ink-900 bg-ink-900 py-2.5 text-paper-100"
        separator="●"
      />
    </section>
  )
}
