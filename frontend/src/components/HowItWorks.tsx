import { useReveal } from '../lib/useReveal'

/*
 * Numbered because this genuinely is a sequence. You cannot share a payment
 * link before the roster exists, so order carries information the reader
 * needs and the numerals earn their place.
 */
const STEPS = [
  { n: '01', title: 'Build the roster', desc: 'Add the class list once. Members do not need to sign up for anything.', tone: 'bg-paper-0' },
  { n: '02', title: 'Open a collection', desc: 'Name it, set the amount and the deadline. Dues, a dinner, a trip, a kit.', tone: 'bg-teal-400' },
  { n: '03', title: 'Share one link', desc: 'Post it in the class group. Payments confirm themselves and the ledger updates live.', tone: 'bg-gold-400' },
  { n: '04', title: 'Publish the report', desc: 'Close the collection and share a record of every naira in and out.', tone: 'bg-rose-600 text-white' },
]

export default function HowItWorks() {
  const ref = useReveal<HTMLElement>({ stagger: 90 })

  return (
    <section ref={ref} id="dashboard" className="border-b-2 border-ink-900 bg-paper-100">
      <div className="mx-auto max-w-[1400px] px-4 md:px-8 py-20 md:py-28">
        <div className="flex flex-wrap items-end justify-between gap-6">
          <div>
            <p data-reveal className="eyebrow">How it works</p>
            <h2 data-reveal className="mt-4 max-w-[14ch] text-headline-lg">
              Set up in one afternoon
            </h2>
          </div>
          <p data-reveal className="max-w-[30ch] text-[14px] leading-relaxed text-ink-600">
            Every step writes to the same ledger, so nothing happens off the books.
          </p>
        </div>

        <ol className="mt-12 grid gap-0 border-2 border-ink-900 sm:grid-cols-2 lg:grid-cols-4">
          {STEPS.map(({ n, title, desc, tone }, i) => (
            <li
              key={n}
              data-reveal
              className={`group relative flex min-h-[240px] flex-col justify-between p-6 ${tone} ${
                i < 2 ? 'border-b-2 border-ink-900 lg:border-b-0' : ''
              } ${i % 2 === 0 ? 'sm:border-r-2 sm:border-ink-900' : ''} ${
                i < 3 ? 'lg:border-r-2 lg:border-ink-900' : ''
              }`}
            >
              <span className="font-display text-[clamp(2.75rem,5vw,4rem)] leading-none opacity-25 transition-opacity duration-200 group-hover:opacity-100">
                {n}
              </span>

              <div>
                <h3 className="text-[19px] leading-tight">{title}</h3>
                <p className="mt-2 text-[14px] leading-relaxed opacity-80">{desc}</p>
              </div>
            </li>
          ))}
        </ol>
      </div>
    </section>
  )
}
