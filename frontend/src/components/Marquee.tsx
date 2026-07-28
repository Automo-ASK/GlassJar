interface Props {
  items: string[]
  className?: string
  reverse?: boolean
  /** Rendered between items. A ledger uses a bullet, not a decoration. */
  separator?: string
}

/**
 * Continuous band. The track is duplicated and translated by exactly -50%,
 * so the loop is seamless. aria-hidden on the clone keeps it out of the
 * accessibility tree.
 */
export default function Marquee({
  items,
  className = '',
  reverse = false,
  separator = '/',
}: Props) {
  const Track = ({ clone = false }: { clone?: boolean }) => (
    <div
      className="flex shrink-0 items-center"
      aria-hidden={clone || undefined}
    >
      {items.map((item, i) => (
        <span key={`${item}-${i}`} className="flex items-center whitespace-nowrap">
          <span className="px-5 font-mono text-[12px] uppercase tracking-[0.18em]">{item}</span>
          <span className="opacity-40" aria-hidden>{separator}</span>
        </span>
      ))}
    </div>
  )

  return (
    <div className={`flex overflow-hidden ${className}`}>
      <div className={`flex ${reverse ? 'animate-marquee-rev' : 'animate-marquee'}`}>
        <Track />
        <Track clone />
      </div>
    </div>
  )
}
