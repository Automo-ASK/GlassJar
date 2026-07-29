import { useReveal } from '../lib/useReveal'

/*
 * The argument stated plainly: what the class rep does today, against what
 * the ledger does instead. Two hard blocks. The contrast is the design.
 */
const OLD = [
  'Your account number pasted in the group chat',
  'Screenshots to check one by one',
  'An Excel sheet only you can see',
  'Answering "have you confirmed my payment?" all week',
  'No way to prove you spent it properly',
]

const NEW = [
  'One payment link for the whole class',
  'Every transfer confirmed by the gateway',
  'A ledger every member can open',
  'Members check their own status themselves',
  'An auditor signs off before money leaves',
]

export default function Contrast() {
  const ref = useReveal<HTMLElement>({ stagger: 70 })

  return (
    <section ref={ref} className="border-b-2 border-ink-900 bg-paper-100">
      <div className="mx-auto max-w-[1400px] px-4 md:px-8 py-20 md:py-28">
        <p data-reveal className="eyebrow">The swap</p>
        <h2 data-reveal className="mt-4 max-w-[18ch] text-headline-lg">
          Same class, same money, different books
        </h2>

        <div className="mt-12 grid border-2 border-ink-900 md:grid-cols-2">
          <div data-reveal className="border-b-2 border-ink-900 bg-paper-0 p-7 sm:p-10 md:border-b-0 md:border-r-2">
            <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-ink-400">
              Right now
            </p>
            <p className="mt-2 font-display text-[22px] uppercase leading-none text-ink-400">
              The group chat
            </p>

            <ul className="mt-7">
              {OLD.map((item) => (
                <li
                  key={item}
                  className="flex items-baseline gap-3 border-t border-ink-100 py-3 text-[15px] text-ink-500 first:border-t-0"
                >
                  <span aria-hidden className="font-mono text-[13px] text-rose-600">✕</span>
                  <span className="line-through decoration-ink-300">{item}</span>
                </li>
              ))}
            </ul>
          </div>

          <div data-reveal className="bg-teal-400 p-7 text-ink-900 sm:p-10">
            <p className="font-mono text-[11px] uppercase tracking-[0.18em]">With GlassJarr</p>
            <p className="mt-2 font-display text-[22px] uppercase leading-none">The ledger</p>

            <ul className="mt-7">
              {NEW.map((item) => (
                <li
                  key={item}
                  className="flex items-baseline gap-3 border-t border-ink-900/20 py-3 text-[15px] font-medium first:border-t-0"
                >
                  <span aria-hidden className="font-mono text-[13px]">✓</span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </section>
  )
}
