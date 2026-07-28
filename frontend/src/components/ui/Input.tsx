import type { InputHTMLAttributes } from 'react'

interface Props extends InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
  hint?: string
}

export default function Input({ label, error, hint, id, className = '', ...props }: Props) {
  return (
    <div className="flex flex-col gap-1.5">
      {label && (
        <label
          htmlFor={id}
          className="font-mono text-[11px] uppercase tracking-[0.14em] text-ink-700"
        >
          {label}
        </label>
      )}

      <input
        id={id}
        aria-invalid={error ? true : undefined}
        className={`w-full border-2 bg-paper-0 px-3.5 py-2.5 text-[15px] text-ink-900 transition-shadow duration-150 placeholder:text-ink-300 focus:outline-none disabled:cursor-not-allowed disabled:bg-paper-200 disabled:text-ink-400 ${
          error
            ? 'border-rose-600 focus:shadow-[3px_3px_0_0_theme(colors.rose.600)]'
            : 'border-ink-900 focus:shadow-neo-sm'
        } ${className}`}
        {...props}
      />

      {hint && !error && <p className="font-mono text-[11px] text-ink-500">{hint}</p>}
      {error && <p className="font-mono text-[11px] font-bold text-rose-600">{error}</p>}
    </div>
  )
}
