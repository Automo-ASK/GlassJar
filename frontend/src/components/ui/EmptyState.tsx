import type { LucideIcon } from 'lucide-react'
import emptyArt from '../../assets/brand/empty-state.webp'

interface Props {
  icon?: LucideIcon
  title: string
  description?: string
  action?: React.ReactNode
  /** Swap the illustration for an icon block where space is tight. */
  compact?: boolean
}

export default function EmptyState({ icon: Icon, title, description, action, compact }: Props) {
  return (
    <div className="flex flex-col items-center justify-center gap-5 border-2 border-dashed border-ink-300 py-14 text-center">
      {compact && Icon ? (
        <div className="flex h-14 w-14 items-center justify-center border-2 border-ink-900 bg-gold-400">
          <Icon size={24} strokeWidth={2} className="text-ink-900" />
        </div>
      ) : (
        <img
          src={emptyArt}
          alt=""
          aria-hidden
          loading="lazy"
          className="h-32 w-32 object-contain"
        />
      )}

      <div className="max-w-sm px-6">
        <p className="font-display text-[17px] uppercase leading-tight">{title}</p>
        {description && (
          <p className="mt-2 text-[14px] leading-relaxed text-ink-500">{description}</p>
        )}
      </div>

      {action}
    </div>
  )
}
