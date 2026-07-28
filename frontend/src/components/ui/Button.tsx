import type { ButtonHTMLAttributes, ReactNode } from 'react'

type Variant = 'primary' | 'black' | 'white' | 'danger' | 'ghost' | 'accent'
type Size = 'sm' | 'md' | 'lg'

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: Size
  loading?: boolean
  children: ReactNode
  fullWidth?: boolean
}

/* Every variant is a flat block with a hard rule and a solid offset shadow.
   Pressing moves the block onto its own shadow. */
const variantClasses: Record<Variant, string> = {
  primary: 'bg-rose-600 text-white',
  black:   'bg-ink-900 text-paper-100',
  accent:  'bg-gold-400 text-ink-900',
  white:   'bg-paper-0 text-ink-900',
  danger:  'bg-rose-700 text-white',
  ghost:   'bg-transparent text-ink-600 border-transparent shadow-none hover:bg-ink-900 hover:text-paper-100',
}

const sizeClasses: Record<Size, string> = {
  sm: 'px-4 py-2 text-[12px] gap-1.5',
  md: 'px-5 py-2.5 text-[13px] gap-2',
  lg: 'px-7 py-4 text-[15px] gap-2.5',
}

export default function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  children,
  fullWidth = false,
  disabled,
  className = '',
  ...props
}: Props) {
  const isGhost = variant === 'ghost'

  return (
    <button
      disabled={disabled || loading}
      className={`group/btn inline-flex items-center justify-center border-2 border-ink-900 font-display uppercase tracking-[0.02em] transition-all duration-150 ease-soft ${
        isGhost ? '' : 'shadow-neo-sm'
      } ${variantClasses[variant]} ${sizeClasses[size]} ${fullWidth ? 'w-full' : ''} ${
        disabled || loading
          ? 'cursor-not-allowed opacity-45'
          : isGhost
            ? ''
            : 'hover:-translate-x-0.5 hover:-translate-y-0.5 hover:shadow-neo active:translate-x-px active:translate-y-px active:shadow-none'
      } ${className}`}
      {...props}
    >
      {loading && (
        <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent" />
      )}
      {children}
    </button>
  )
}
