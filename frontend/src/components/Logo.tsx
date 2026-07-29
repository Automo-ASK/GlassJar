import markUrl from '../assets/brand/logo-mark.webp'

interface Props {
  size?: 'sm' | 'md' | 'lg'
  variant?: 'default' | 'white'
  markOnly?: boolean
}

const SIZES = {
  sm: { mark: 26, word: 'text-[16px]', gap: 'gap-2' },
  md: { mark: 32, word: 'text-[20px]', gap: 'gap-2.5' },
  lg: { mark: 42, word: 'text-[26px]', gap: 'gap-3' },
}

/**
 * The mark is a jar with a visible fill level: a shared pot you can see into.
 *
 * Its outline is near-black, so on dark surfaces it sits on a paper plate
 * rather than disappearing. That reads as a printed sticker, which suits the
 * rest of the system.
 */
export function LogoMark({
  size = 32,
  variant = 'default',
}: {
  size?: number
  variant?: 'default' | 'white'
}) {
  const img = (
    <img
      src={markUrl}
      width={size}
      height={size}
      alt=""
      aria-hidden
      className="block"
      style={{ width: size, height: size }}
    />
  )

  if (variant !== 'white') return img

  return (
    <span
      className="inline-flex items-center justify-center border-2 border-ink-900 bg-paper-100"
      style={{ padding: Math.round(size * 0.11) }}
    >
      {img}
    </span>
  )
}

export default function Logo({ size = 'md', variant = 'default', markOnly = false }: Props) {
  const s = SIZES[size]
  const isWhite = variant === 'white'

  if (markOnly) return <LogoMark size={s.mark} variant={variant} />

  return (
    <span className={`inline-flex items-center ${s.gap} select-none`}>
      <LogoMark size={s.mark} variant={variant} />
      <span
        className={`font-display uppercase leading-none tracking-[-0.04em] ${s.word} ${
          isWhite ? 'text-paper-100' : 'text-ink-900'
        }`}
      >
        Glass<span className="text-rose-600">Jarr</span>
      </span>
    </span>
  )
}
