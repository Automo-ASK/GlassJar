import type { ReactNode } from 'react'
import ScrollStack, { ScrollStackItem } from './ScrollStack'
import { useReveal } from '../lib/useReveal'
import { RosterList, Channels, ReceiptStamp, ApprovalChain, ReportCover } from './FeatureVisuals'

interface Feature {
  tag: string
  title: string
  desc: string
  /* Each card owns a full colour field. The palette is used as blocks. */
  field: string
  panel: string
  visual: ReactNode
}

const FEATURES: Feature[] = [
  {
    tag: 'Roster',
    title: 'Add your class, not their signups',
    desc: 'Type or upload the class list once. Members never create an account. They open your link, find their name, and pay.',
    field: 'bg-teal-400 text-ink-900',
    panel: 'bg-teal-100',
    visual: <RosterList />,
  },
  {
    tag: 'Collection',
    title: 'One link for the whole class',
    desc: 'Share a single payment link on WhatsApp. Transfers, USSD and card all come back confirmed and matched to the right member automatically.',
    field: 'bg-gold-400 text-ink-900',
    panel: 'bg-gold-100',
    visual: <Channels />,
  },
  {
    tag: 'Verification',
    title: 'No more checking screenshots',
    desc: 'The payment gateway confirms each transfer server side. Payer, amount and reference are matched for you, so a screenshot proves nothing and nobody has to chase it.',
    field: 'bg-rose-600 text-white',
    panel: 'bg-rose-100',
    visual: <ReceiptStamp />,
  },
  {
    tag: 'Approval',
    title: 'Spending needs a second signature',
    desc: 'The treasurer submits an expense with a receipt. An independent auditor has to approve it before any money leaves the community account.',
    field: 'bg-paper-0 text-ink-900',
    panel: 'bg-paper-200',
    visual: <ApprovalChain />,
  },
  {
    tag: 'Report',
    title: 'Prove it without being asked',
    desc: 'Every member can open the transparency report and see what came in, what went out, and who approved it. Handover is a document, not a conversation.',
    field: 'bg-ink-900 text-paper-100',
    panel: 'bg-ink-800',
    visual: <ReportCover />,
  },
]

export default function Features() {
  const headRef = useReveal<HTMLDivElement>({ stagger: 80 })

  return (
    <section id="features" className="relative border-b-2 border-ink-900 bg-paper-100">
      <div ref={headRef} className="mx-auto max-w-[1400px] px-4 md:px-8 pt-20 md:pt-28">
        <p data-reveal className="eyebrow">What you get</p>
        <h2 data-reveal className="mt-4 max-w-[16ch] text-headline-lg">
          Five jobs, handled
        </h2>
        <p data-reveal className="mt-5 max-w-lg text-body-lg text-ink-600">
          Everything a class rep currently does by hand, done by the system instead.
        </p>
      </div>

      <div className="mx-auto max-w-[1180px] px-4 md:px-8">
        <ScrollStack
          useWindowScroll
          itemDistance={110}
          itemStackDistance={24}
          itemScale={0.024}
          baseScale={0.87}
          stackPosition="16%"
          scaleEndPosition="7%"
          blurAmount={0}
        >
          {FEATURES.map(({ tag, title, desc, field, panel, visual }) => (
            <ScrollStackItem key={tag}>
              <div className={`grid md:grid-cols-[1.05fr_1fr] ${field}`}>
                <div className="flex flex-col justify-between gap-8 p-7 sm:p-9 md:p-11">
                  <div className="flex items-center gap-3">
                    <span className="border-2 border-current px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.18em]">
                      {tag}
                    </span>
                    <span className="h-px flex-1 bg-current opacity-25" />
                  </div>

                  <div>
                    <h3 className="max-w-[15ch] text-[clamp(1.6rem,3.2vw,2.6rem)] leading-[0.95]">
                      {title}
                    </h3>
                    <p className="mt-4 max-w-[46ch] text-[15px] leading-relaxed opacity-80">
                      {desc}
                    </p>
                  </div>
                </div>

                <div
                  className={`border-t-2 border-ink-900 p-7 sm:p-9 md:border-l-2 md:border-t-0 md:p-10 ${panel} text-ink-900`}
                >
                  {visual}
                </div>
              </div>
            </ScrollStackItem>
          ))}
        </ScrollStack>
      </div>
    </section>
  )
}
