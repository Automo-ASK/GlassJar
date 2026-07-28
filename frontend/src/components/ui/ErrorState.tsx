import { AlertTriangle, RefreshCw } from 'lucide-react'
import Button from './Button'

interface Props {
  message?: string
  onRetry?: () => void
}

export default function ErrorState({ message = 'Something went wrong.', onRetry }: Props) {
  return (
    <div className="flex flex-col items-center justify-center gap-5 border-2 border-ink-900 bg-rose-100 py-14 text-center shadow-neo">
      <div className="flex h-14 w-14 items-center justify-center border-2 border-ink-900 bg-rose-600">
        <AlertTriangle size={24} strokeWidth={2} className="text-white" />
      </div>

      <div className="max-w-sm px-6">
        <p className="font-display text-[17px] uppercase leading-tight text-rose-700">
          That did not work
        </p>
        <p className="mt-2 text-[14px] leading-relaxed text-ink-600">{message}</p>
      </div>

      {onRetry && (
        <Button variant="white" size="sm" onClick={onRetry}>
          <RefreshCw size={14} />
          Try again
        </Button>
      )}
    </div>
  )
}
