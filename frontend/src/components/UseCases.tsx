import { useReveal } from '../lib/useReveal'
import useDues from '../assets/brand/use-dues.webp'
import useEvent from '../assets/brand/use-event.webp'
import useTrip from '../assets/brand/use-trip.webp'
import useKit from '../assets/brand/use-kit.webp'
import useFund from '../assets/brand/use-fund.webp'
import useProject from '../assets/brand/use-project.webp'

/*
 * Straight from the PRD: GlassJar is not only class dues. Showing the range
 * up front is what stops a rep deciding this is the wrong tool for a dinner
 * or a trip.
 */
const CASES = [
  { image: useDues, title: 'Class dues', note: 'Semester and faculty levies', tone: 'bg-teal-100' },
  { image: useEvent, title: 'Dinners and owambe', note: 'Social events and outings', tone: 'bg-gold-100' },
  { image: useTrip, title: 'Study trips', note: 'Deposits and logistics', tone: 'bg-rose-100' },
  { image: useKit, title: 'Team kits', note: 'Sports clubs and societies', tone: 'bg-paper-200' },
  { image: useFund, title: 'Fundraisers', note: 'Departmental and charity drives', tone: 'bg-gold-100' },
  { image: useProject, title: 'Project materials', note: 'Group work and lab pooling', tone: 'bg-teal-100' },
]

export default function UseCases() {
  const ref = useReveal<HTMLElement>({ stagger: 70 })

  return (
    <section ref={ref} className="border-b-2 border-ink-900 bg-paper-100">
      <div className="mx-auto max-w-[1400px] px-4 md:px-8 py-20 md:py-28">
        <div className="flex flex-wrap items-end justify-between gap-6">
          <div>
            <p data-reveal className="eyebrow">Not just dues</p>
            <h2 data-reveal className="mt-4 max-w-[16ch] text-headline-lg">
              Anything your group chips in for
            </h2>
          </div>
          <p data-reveal className="max-w-[30ch] text-[14px] leading-relaxed text-ink-600">
            Same roster, same link, same ledger. Only the reason changes.
          </p>
        </div>

        <ul className="mt-12 grid grid-cols-2 border-l-2 border-t-2 border-ink-900 lg:grid-cols-3">
          {CASES.map(({ image, title, note, tone }) => (
            <li
              key={title}
              data-reveal
              className="group border-b-2 border-r-2 border-ink-900"
            >
              <div className={`aspect-[4/3] overflow-hidden border-b-2 border-ink-900 ${tone}`}>
                <img
                  src={image}
                  alt=""
                  aria-hidden
                  loading="lazy"
                  className="h-full w-full object-cover mix-blend-multiply transition-transform duration-300 ease-soft group-hover:scale-[1.04]"
                />
              </div>
              <div className="bg-paper-0 p-4 transition-colors duration-150 group-hover:bg-gold-400">
                <h3 className="text-[15px] leading-tight sm:text-[17px]">{title}</h3>
                <p className="mt-1 font-mono text-[10px] uppercase tracking-[0.12em] text-ink-500 group-hover:text-ink-700">
                  {note}
                </p>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}
