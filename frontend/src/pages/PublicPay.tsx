import { useEffect, useState, useCallback } from 'react'
import { useParams } from 'react-router-dom'
import { ShieldCheck } from 'lucide-react'
import Button from '../components/ui/Button'
import LoadingState from '../components/ui/LoadingState'
import ErrorState from '../components/ui/ErrorState'
import { getPublicCollection, publicPay } from '../lib/api'
import type { PublicCollection } from '../lib/types'

function fmt(n: number) {
  return `₦${n.toLocaleString('en-NG')}`
}

/** Public payment page: open the shared link, pay. Anyone can pay, no
 *  account, no roster match, no picking a name off a list. */
export default function PublicPay() {
  const { shareToken } = useParams<{ shareToken: string }>()

  const [collection, setCollection] = useState<PublicCollection | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [email, setEmail] = useState('')
  const [paying, setPaying] = useState(false)
  const [payError, setPayError] = useState('')

  const load = useCallback(async () => {
    if (!shareToken) return
    setLoading(true)
    setError('')
    try {
      setCollection(await getPublicCollection(shareToken))
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'This payment link is invalid or has been removed.')
    } finally {
      setLoading(false)
    }
  }, [shareToken])

  useEffect(() => { load() }, [load])

  const handlePay = async () => {
    if (!shareToken) return
    setPaying(true)
    setPayError('')
    try {
      const { checkout_url, payment_reference } = await publicPay(shareToken, email.trim() || undefined)
      sessionStorage.setItem('acafund_payment_reference', payment_reference)
      sessionStorage.setItem('acafund_pay_token', shareToken)
      window.location.href = checkout_url
    } catch (e: unknown) {
      setPayError(e instanceof Error ? e.message : 'Could not start payment')
      setPaying(false)
    }
  }

  if (loading) return <LoadingState />
  if (error || !collection) return <ErrorState message={error} onRetry={load} />

  return (
    <div className="min-h-screen bg-surface px-4 py-10">
      <div className="max-w-lg mx-auto flex flex-col gap-6">
        {/* Header */}
        <div className="text-center">
          <p className="text-[12px] font-bold uppercase tracking-widest text-on-surface-variant">
            {collection.community_name}
          </p>
          <h1 className="text-[28px] font-bold tracking-tight mt-1">{collection.title}</h1>
          {collection.description && (
            <p className="text-[14px] text-on-surface-variant mt-1">{collection.description}</p>
          )}
        </div>

        {collection.status !== 'active' ? (
          <div className="border-2 border-black bg-surface-container p-4 text-center text-[13px] font-bold">
            This collection is closed and no longer accepting payments.
          </div>
        ) : (
          <div className="border-4 border-black neo-shadow-lg bg-white p-6 flex flex-col gap-4">
            <div className="text-center">
              <p className="text-[12px] font-bold uppercase tracking-widest text-on-surface-variant">Amount</p>
              <p className="text-[26px] font-bold text-primary">{fmt(collection.amount_per_member)}</p>
            </div>
            <div className="flex flex-col gap-1">
              <label htmlFor="guest-email" className="text-[12px] font-bold uppercase tracking-[0.06em]">
                Email for receipt (optional)
              </label>
              <input
                id="guest-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="border-2 border-black px-3 py-2 text-[14px] bg-white focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
            {payError && (
              <p className="text-[12px] text-error font-bold">{payError}</p>
            )}
            <Button fullWidth size="lg" loading={paying} onClick={handlePay}>
              Pay {fmt(collection.amount_per_member)}
            </Button>
            <p className="text-[11px] text-on-surface-variant flex items-center gap-1.5 justify-center">
              <ShieldCheck size={12} className="text-primary" />
              Secured by Monnify. Verified automatically, no screenshots needed.
            </p>
          </div>
        )}

        <p className="text-center text-[12px] text-on-surface-variant">
          Powered by GlassJar. Transparent community money for students.
        </p>
      </div>
    </div>
  )
}
