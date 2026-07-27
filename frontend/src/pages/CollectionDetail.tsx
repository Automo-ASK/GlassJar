import { useEffect, useState, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Share2, Lock, RefreshCw, CheckCircle, Clock, User, ChevronLeft,
  Link as LinkIcon, Undo2, UserPlus,
} from 'lucide-react'
import Button from '../components/ui/Button'
import Badge from '../components/ui/Badge'
import LoadingState from '../components/ui/LoadingState'
import ErrorState from '../components/ui/ErrorState'
import {
  getCollection, getMyPayment,
  initiatePayment, closeCollection, getMembers, getCollectionResponses,
  markEntryPaid, waiveEntry, revertEntry, syncCollectionEntries,
} from '../lib/api'
import type {
  CollectionDetail as CollDetailType,
  CollectionMemberEntry, CommunityMember, ManualChannel,
  CollectionResponses,
} from '../lib/types'
import { useAuth } from '../contexts/AuthContext'

function fmt(n: number) {
  return `₦${n.toLocaleString('en-NG')}`
}

export default function CollectionDetail() {
  const { id } = useParams<{ id: string }>()
  const collectionId = Number(id)
  const { user } = useAuth()
  const navigate = useNavigate()

  const [collection, setCollection] = useState<CollDetailType | null>(null)
  const [anonPayments, setAnonPayments] = useState<CollectionResponses | null>(null)
  const [myPayment, setMyPayment] = useState<CollectionMemberEntry | null>(null)
  const [communityMembers, setCommunityMembers] = useState<CommunityMember[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [paying, setPaying] = useState(false)
  const [closing, setClosing] = useState(false)
  const [actionError, setActionError] = useState('')
  const [copied, setCopied] = useState<'report' | 'paylink' | null>(null)
  const [entryBusy, setEntryBusy] = useState<number | null>(null)

  const myRole = communityMembers.find((m) => m.user_id === user?.id)?.role
  const isManager = myRole === 'admin' || myRole === 'treasurer'

  const load = useCallback(async () => {
    setLoading(true); setError('')
    try {
      const col = await getCollection(collectionId)
      const [anon, pay] = await Promise.all([
        getCollectionResponses(collectionId).catch(() => null),
        getMyPayment(collectionId).catch(() => null),
      ])
      setCollection(col)
      setAnonPayments(anon)
      setMyPayment(pay)
      // fetch community members to determine role
      const mems = await getMembers(col.community_id).catch(() => [])
      setCommunityMembers(mems)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load collection')
    } finally { setLoading(false) }
  }, [collectionId])

  useEffect(() => { load() }, [load])

  const handlePay = async () => {
    setActionError(''); setPaying(true)
    try {
      const { checkout_url, payment_reference } = await initiatePayment(collectionId)
      sessionStorage.setItem('acafund_payment_collection_id', String(collectionId))
      sessionStorage.setItem('acafund_payment_reference', payment_reference)
      window.location.href = checkout_url
    } catch (e: unknown) {
      setActionError(e instanceof Error ? e.message : 'Payment initiation failed')
      setPaying(false)
    }
  }

  const handleClose = async () => {
    if (!confirm('Close this collection? No further payments will be accepted.')) return
    setClosing(true); setActionError('')
    try {
      await closeCollection(collectionId)
      await load()
    } catch (e: unknown) {
      setActionError(e instanceof Error ? e.message : 'Failed to close collection')
    } finally { setClosing(false) }
  }

  const copyLink = (kind: 'report' | 'paylink', url: string) => {
    navigator.clipboard.writeText(url)
    setCopied(kind)
    setTimeout(() => setCopied(null), 2000)
  }

  const patchEntry = (updated: CollectionMemberEntry) => {
    setCollection((prev) =>
      prev ? { ...prev, entries: prev.entries.map((e) => (e.id === updated.id ? updated : e)) } : prev,
    )
  }

  const handleMarkPaid = async (entry: CollectionMemberEntry, channel: ManualChannel) => {
    setEntryBusy(entry.id); setActionError('')
    try {
      patchEntry(await markEntryPaid(collectionId, entry.id, channel))
    } catch (e: unknown) {
      setActionError(e instanceof Error ? e.message : 'Failed to mark as paid')
    } finally { setEntryBusy(null) }
  }

  const handleWaive = async (entry: CollectionMemberEntry) => {
    if (!confirm(`Waive ${entry.display_name}'s dues for this collection?`)) return
    setEntryBusy(entry.id); setActionError('')
    try {
      patchEntry(await waiveEntry(collectionId, entry.id))
    } catch (e: unknown) {
      setActionError(e instanceof Error ? e.message : 'Failed to waive')
    } finally { setEntryBusy(null) }
  }

  const handleRevert = async (entry: CollectionMemberEntry) => {
    if (!confirm(`Undo the ${entry.status} mark for ${entry.display_name}? Gateway-verified payments cannot be undone.`)) return
    setEntryBusy(entry.id); setActionError('')
    try {
      patchEntry(await revertEntry(collectionId, entry.id))
    } catch (e: unknown) {
      setActionError(e instanceof Error ? e.message : 'Failed to undo')
    } finally { setEntryBusy(null) }
  }

  const handleSyncEntries = async () => {
    setActionError('')
    try {
      const { added } = await syncCollectionEntries(collectionId)
      if (added > 0) await load()
    } catch (e: unknown) {
      setActionError(e instanceof Error ? e.message : 'Failed to sync roster')
    }
  }

  if (loading) return <LoadingState />
  if (error || !collection) return <ErrorState message={error} onRetry={load} />

  const payLink = `${window.location.origin}/pay/${collection.share_token}`

  return (
    <div className="flex flex-col gap-6 max-w-3xl">
      {/* Back nav */}
      <button
        onClick={() => navigate(`/communities/${collection.community_id}/collections`)}
        className="flex items-center gap-1.5 text-[12px] font-bold uppercase tracking-[0.06em] text-on-surface-variant hover:text-primary transition-colors w-fit"
      >
        <ChevronLeft size={14} /> Back to Collections
      </button>

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
        <div>
          <Badge color={collection.status === 'active' ? 'green' : 'gray'}>{collection.status}</Badge>
          <h1 className="text-[28px] font-bold tracking-tight mt-2">{collection.title}</h1>
          {collection.description && (
            <p className="text-[14px] text-on-surface-variant mt-1">{collection.description}</p>
          )}
        </div>
        <div className="flex gap-2 flex-wrap">
          <Button variant="white" size="sm" onClick={load}>
            <RefreshCw size={13} /> Refresh
          </Button>
          {myRole === 'admin' && (
            <Button variant="white" size="sm" onClick={() => copyLink('report', `${window.location.origin}/report/${collectionId}`)}>
              <Share2 size={13} />
              {copied === 'report' ? 'Link Copied!' : 'Share Report'}
            </Button>
          )}
        </div>
      </div>

      {/* Shareable payment link — the core distribution loop */}
      {isManager && collection.status === 'active' && (
        <div className="border-2 border-black bg-secondary-fixed p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="min-w-0">
            <p className="text-[11px] font-bold uppercase tracking-[0.08em] text-on-surface-variant">Payment Link — share with your class</p>
            <p className="text-[13px] font-bold truncate">{payLink}</p>
            <p className="text-[11px] text-on-surface-variant mt-0.5">
              Anyone with the link can pay directly — no account or sign-up needed.
            </p>
          </div>
          <Button variant="black" size="sm" onClick={() => copyLink('paylink', payLink)}>
            <LinkIcon size={13} />
            {copied === 'paylink' ? 'Copied!' : 'Copy Link'}
          </Button>
        </div>
      )}

      {actionError && (
        <div className="border-2 border-error bg-error-container p-3 text-[13px] font-bold text-error">{actionError}</div>
      )}

      {/* Pay now CTA */}
      {myPayment?.status === 'pending' && collection.status === 'active' && (
        <div className="border-4 border-black neo-shadow-lg bg-primary-container p-6 flex items-center justify-between gap-4">
          <div>
            <p className="text-[12px] font-bold uppercase tracking-widest text-on-primary-container/70">Your dues</p>
            <p className="text-[24px] font-bold">{fmt(myPayment.amount_due)}</p>
            <p className="text-[13px] text-on-primary-container/70">Status: <strong>Pending</strong></p>
          </div>
          <Button variant="black" size="lg" loading={paying} onClick={handlePay}>
            Pay Now
          </Button>
        </div>
      )}

      {myPayment?.status === 'paid' && (
        <div className="border-2 border-primary bg-primary-container/30 p-4 flex items-center gap-3">
          <CheckCircle size={20} className="text-primary" />
          <p className="text-[14px] font-bold text-primary">
            You've paid {fmt(myPayment.amount_due)} — thank you!
          </p>
        </div>
      )}

      {/* Budget allocation */}
      {collection.budget_allocation && Object.keys(collection.budget_allocation).length > 0 && (
        <div className="border-2 border-black bg-white p-5 neo-shadow">
          <h2 className="text-[14px] font-bold uppercase tracking-[0.06em] mb-4">Budget Allocation</h2>
          <div className="flex flex-col gap-3">
            {Object.entries(collection.budget_allocation).map(([cat, share]) => (
              <div key={cat}>
                <div className="flex justify-between text-[13px] font-bold mb-1">
                  <span>{cat}</span>
                  <span>{share}%</span>
                </div>
                <div className="w-full bg-surface-container border border-black h-2">
                  <div className="bg-secondary h-full" style={{ width: `${share}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Member payment list */}
      <div className="border-2 border-black bg-white neo-shadow">
        <div className="border-b-2 border-black px-5 py-3 flex items-center justify-between">
          <h2 className="text-[14px] font-bold uppercase tracking-[0.06em]">Member Payments</h2>
          <div className="flex items-center gap-3">
            {isManager && collection.status === 'active' && (
              <button
                onClick={handleSyncEntries}
                className="flex items-center gap-1 text-[11px] font-bold uppercase tracking-widest text-primary hover:underline"
                title="Enroll roster members added after this collection was created"
              >
                <UserPlus size={12} /> Sync roster
              </button>
            )}
            <span className="text-[12px] text-on-surface-variant">
              {collection.entries.length} enrolled
              {anonPayments && anonPayments.responses.length > 0 && ` · ${anonPayments.responses.length} paid via link`}
            </span>
          </div>
        </div>
        <div className="divide-y-2 divide-black">
          {collection.entries.map((entry) => (
            <div key={entry.id} className="px-5 py-3 flex items-center justify-between gap-3">
              <div className="flex items-center gap-3 min-w-0">
                {entry.status === 'paid'
                  ? <CheckCircle size={16} className="text-primary flex-shrink-0" />
                  : <Clock size={16} className="text-on-surface-variant flex-shrink-0" />
                }
                <div className="min-w-0">
                  <p className="text-[13px] font-bold flex items-center gap-1 truncate">
                    <User size={12} className="flex-shrink-0" /> {entry.display_name}
                    {myPayment?.id === entry.id && <span className="text-on-surface-variant font-normal">(you)</span>}
                  </p>
                  {entry.paid_at && (
                    <p className="text-[11px] text-on-surface-variant">
                      {new Date(entry.paid_at).toLocaleDateString()}
                    </p>
                  )}
                  {entry.note && (
                    <p className="text-[11px] text-on-surface-variant italic truncate">{entry.note}</p>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-3 flex-shrink-0">
                <div className="text-right">
                  <p className="text-[13px] font-bold">{fmt(entry.amount_due)}</p>
                  <Badge color={entry.status === 'paid' ? 'green' : entry.status === 'waived' ? 'blue' : 'gray'}>
                    {entry.status}
                  </Badge>
                </div>
                {isManager && collection.status === 'active' && (
                  entry.status === 'pending' ? (
                    <div className="flex flex-col gap-1">
                      <button
                        disabled={entryBusy === entry.id}
                        onClick={() => handleMarkPaid(entry, 'manual_cash')}
                        className="border-2 border-black bg-white px-2 py-1 text-[10px] font-bold uppercase tracking-widest neo-shadow-sm neo-btn disabled:opacity-50"
                        title="Record a cash payment received in person"
                      >
                        Got Cash
                      </button>
                      <button
                        disabled={entryBusy === entry.id}
                        onClick={() => handleMarkPaid(entry, 'manual_transfer')}
                        className="border-2 border-black bg-white px-2 py-1 text-[10px] font-bold uppercase tracking-widest neo-shadow-sm neo-btn disabled:opacity-50"
                        title="Record a transfer made outside the platform"
                      >
                        Got Transfer
                      </button>
                      {myRole === 'admin' && (
                        <button
                          disabled={entryBusy === entry.id}
                          onClick={() => handleWaive(entry)}
                          className="border-2 border-black bg-surface-container px-2 py-1 text-[10px] font-bold uppercase tracking-widest neo-shadow-sm neo-btn disabled:opacity-50"
                        >
                          Waive
                        </button>
                      )}
                    </div>
                  ) : (
                    <button
                      disabled={entryBusy === entry.id}
                      onClick={() => handleRevert(entry)}
                      className="border-2 border-black bg-white p-1.5 neo-shadow-sm neo-btn disabled:opacity-50"
                      title="Undo (manual marks and waivers only)"
                      aria-label={`Undo mark for ${entry.display_name}`}
                    >
                      <Undo2 size={13} />
                    </button>
                  )
                )}
              </div>
            </div>
          ))}
          {anonPayments?.responses.map((p) => {
            const details = anonPayments.custom_fields
              .map((f) => p.values[f.key])
              .filter((v) => v !== undefined && v !== null && v !== '')
              .join(' · ')
            return (
              <div key={p.payment_id} className="px-5 py-3 flex items-center justify-between gap-3">
                <div className="flex items-center gap-3 min-w-0">
                  <CheckCircle size={16} className="text-primary flex-shrink-0" />
                  <div className="min-w-0">
                    <p className="text-[13px] font-bold flex items-center gap-1 truncate">
                      <User size={12} className="flex-shrink-0" /> {details || 'Guest'}
                    </p>
                    {p.paid_at && (
                      <p className="text-[11px] text-on-surface-variant">
                        {new Date(p.paid_at).toLocaleDateString()}
                      </p>
                    )}
                  </div>
                </div>
                <div className="text-right flex-shrink-0">
                  <p className="text-[13px] font-bold">{fmt(p.amount)}</p>
                  <Badge color="green">paid via link</Badge>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Admin actions */}
      {myRole === 'admin' && collection.status === 'active' && (
        <div className="border-2 border-black p-4 bg-surface-container flex items-center justify-between gap-4">
          <p className="text-[13px] text-on-surface-variant">Close this collection to prevent further payments.</p>
          <Button variant="danger" size="sm" loading={closing} onClick={handleClose}>
            <Lock size={13} /> Close Collection
          </Button>
        </div>
      )}
    </div>
  )
}
