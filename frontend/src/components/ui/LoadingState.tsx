import JarLoader from '../JarLoader'

export default function LoadingState({ message = 'Loading' }: { message?: string }) {
  return (
    <div
      className="flex flex-col items-center justify-center gap-4 py-20"
      role="status"
      aria-live="polite"
    >
      <JarLoader size={72} label={message} />
      <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-ink-500">
        {message}
        <span className="animate-blink">_</span>
      </p>
    </div>
  )
}
