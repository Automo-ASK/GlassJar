type Color = 'green' | 'purple' | 'blue' | 'red' | 'gray' | 'yellow'

interface Props {
  children: React.ReactNode
  color?: Color
  dot?: boolean
}

/* Status reads as a stamped block, not a soft pill. */
const colorMap: Record<Color, string> = {
  green:  'bg-teal-400 text-ink-900',
  purple: 'bg-ink-900 text-paper-100',
  blue:   'bg-paper-0 text-ink-900',
  red:    'bg-rose-600 text-white',
  gray:   'bg-paper-200 text-ink-700',
  yellow: 'bg-gold-400 text-ink-900',
}

export default function Badge({ children, color = 'gray', dot = false }: Props) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 whitespace-nowrap border-2 border-ink-900 px-2 py-0.5 font-mono text-[10px] font-bold uppercase tracking-[0.12em] ${colorMap[color]}`}
    >
      {dot && <span className="h-1.5 w-1.5 rounded-full bg-current animate-pulse-dot" />}
      {children}
    </span>
  )
}
