export default function LoadingState({ message = 'Loading' }: { message?: string }) {
  return (
    <div
      className="flex flex-col items-center justify-center gap-4 py-20"
      role="status"
      aria-live="polite"
    >
      {/* three blocks filling, in the ledger's own rhythm */}
      <div className="flex gap-1.5" aria-hidden>
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="h-3 w-3 border-2 border-ink-900 bg-rose-600 animate-pulse-dot"
            style={{ animationDelay: `${i * 180}ms` }}
          />
        ))}
      </div>
      <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-ink-500">
        {message}
        <span className="animate-blink">_</span>
      </p>
    </div>
  )
}
