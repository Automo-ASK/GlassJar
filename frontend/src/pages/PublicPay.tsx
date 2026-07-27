import { useEffect, useState, useCallback } from 'react'
import { useParams } from 'react-router-dom'
import { CheckCircle, Clock, Search, ShieldCheck } from 'lucide-react'
import Button from '../components/ui/Button'
import LoadingState from '../components/ui/LoadingState'
import ErrorState from '../components/ui/ErrorState'
import { getPublicCollection, guestPay } from '../lib/api'
import type { PublicCollection, PublicEntry } from '../lib/types'

function fmt(n: number) {
  return `₦${n.toLocaleString('en-NG')}`
}

/** Public guest payment page: open the shared link, pick your name, pay.
 *  No account, no login — the whole point of the roster-first model. */
export default function PublicPay() {
  const { shareToken } = useParams<{ shareToken: string }>()

  const [collection, setCollection] = useState<PublicCollection | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState<PublicEntry | null>(null)
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
    if (!shareToken || !selected) return
    setPaying(true)
    setPayError('')
    try {
      const { checkout_url, payment_reference } = await guestPay(
        shareToken, selected.id, email.trim() || undefined,
      )
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

  const filtered = collection.entries.filter((e) =>
    e.display_name.toLowerCase().includes(search.toLowerCase()),
  )
  const paidCount = collection.entries.filter((e) => e.status === 'paid').length

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
          <p className="text-[20px] font-bold mt-3">{fmt(collection.amount_per_member)} <span className="text-[13px] font-normal text-on-surface-variant">per member</span></p>
          <p className="text-[12px] text-on-surface-variant mt-1">
            {paidCount} of {collection.entries.length} paid
          </p>
        </div>

        {collection.status !== 'active' && (
          <div className="border-2 border-black bg-surface-container p-4 text-center text-[13px] font-bold">
            This collection is closed and no longer accepting payments.
          </div>
        )}

        {selected ? (
          /* Confirm step */
          <div className="border-4 border-black neo-shadow-lg bg-white p-6 flex flex-col gap-4">
            <div>
              <p className="text-[12px] font-bold uppercase tracking-widest text-on-surface-variant">Paying as</p>
              <p className="text-[22px] font-bold">{selected.display_name}</p>
              <p className="text-[15px] font-bold text-primary mt-1">{fmt(collection.amount_per_member)}</p>
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
            <div className="flex gap-2">
              <Button fullWidth size="lg" loading={paying} onClick={handlePay}>
                Pay {fmt(collection.amount_per_member)}
              </Button>
              <Button variant="white" size="lg" onClick={() => { setSelected(null); setPayError('') }}>
                Back
              </Button>
            </div>
            <p className="text-[11px] text-on-surface-variant flex items-center gap-1.5 justify-center">
              <ShieldCheck size={12} className="text-primary" />
              Secured by Monnify — verified automatically, no screenshots needed.
            </p>
          </div>
        ) : (
          /* Pick-your-name step */
          <div className="border-4 border-black neo-shadow-lg bg-white">
            <div className="border-b-2 border-black p-4">
              <p className="text-[14px] font-bold mb-2">Find your name to pay</p>
              <div className="flex items-center gap-2 border-2 border-black px-3 py-2">
                <Search size={14} className="text-on-surface-variant flex-shrink-0" />
                <input
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search your name…"
                  className="w-full text-[14px] bg-transparent focus:outline-none"
                />
              </div>
            </div>
            <div className="divide-y-2 divide-black max-h-96 overflow-y-auto">
              {filtered.length === 0 && (
                <p className="p-4 text-[13px] text-on-surface-variant text-center">
                  No name matches "{search}". Ask your rep to add you to the list.
                </p>
              )}
              {filtered.map((entry) => (
                <div key={entry.id} className="px-4 py-3 flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2.5">
                    {entry.status === 'paid'
                      ? <CheckCircle size={16} className="text-primary flex-shrink-0" />
                      : <Clock size={16} className="text-on-surface-variant flex-shrink-0" />}
                    <p className="text-[14px] font-bold">{entry.display_name}</p>
                  </div>
                  {entry.status === 'pending' && collection.status === 'active' ? (
                    <Button size="sm" onClick={() => setSelected(entry)}>
                      This is me
                    </Button>
                  ) : (
                    <span className="text-[11px] font-bold uppercase tracking-widest text-on-surface-variant">
                      {entry.status}
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        <p className="text-center text-[12px] text-on-surface-variant">
          Powered by AcaFund — transparent community money for students.
        </p>
      </div>
    </div>
  )
}
