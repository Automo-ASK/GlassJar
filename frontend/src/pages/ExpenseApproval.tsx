import { useEffect, useState } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import { ExternalLink, Banknote, Building2, AlertTriangle, RefreshCw } from 'lucide-react'
import Button from '../components/ui/Button'
import Badge from '../components/ui/Badge'
import LoadingState from '../components/ui/LoadingState'
import ErrorState from '../components/ui/ErrorState'
import {
  getExpenses, getMembers, retryExpensePayout,
  authorizeExpensePayout, resendExpenseOtp, markExpensePaidManually,
} from '../lib/api'
import type { Expense, CommunityMember, ExpenseStatus } from '../lib/types'
import { useAuth } from '../contexts/AuthContext'

function fmt(n: number) { return `₦${n.toLocaleString('en-NG')}` }

function statusBadge(s: ExpenseStatus): { color: 'yellow' | 'blue' | 'green' | 'red'; label: string } {
  switch (s) {
    case 'pending':      return { color: 'yellow', label: 'Sending…' }
    case 'awaiting_otp':  return { color: 'blue',   label: 'Needs Authorization Code' }
    case 'paid_out':      return { color: 'green',  label: 'Paid Out' }
    case 'failed':         return { color: 'red',    label: 'Transfer Failed' }
  }
}

export default function ExpenseApproval() {
  const { id } = useParams<{ id: string }>()
  const [searchParams] = useSearchParams()
  const expenseId = Number(id)
  const communityId = Number(searchParams.get('community'))
  const { user } = useAuth()

  const [expense, setExpense] = useState<Expense | null>(null)
  const [members, setMembers] = useState<CommunityMember[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [actionError, setActionError] = useState('')

  const [otp, setOtp] = useState('')
  const [authorizing, setAuthorizing] = useState(false)
  const [resending, setResending] = useState(false)
  const [retrying, setRetrying] = useState(false)

  const [manualOpen, setManualOpen] = useState(false)
  const [manualRef, setManualRef] = useState('')
  const [manualLoading, setManualLoading] = useState(false)

  const myRole = members.find((m) => m.user_id === user?.id)?.role
  const canManage = myRole === 'admin' || myRole === 'treasurer'

  const load = async () => {
    if (!communityId) {
      setError('Community context missing. Navigate here from the Expenses list.')
      setLoading(false)
      return
    }
    setLoading(true)
    try {
      const [exps, mems] = await Promise.all([
        getExpenses(communityId),
        getMembers(communityId),
      ])
      const found = exps.find((e) => e.id === expenseId)
      if (found) setExpense(found)
      else setError('Expense not found in this community.')
      setMembers(mems)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load expense')
    } finally { setLoading(false) }
  }

  useEffect(() => { load() }, [expenseId, communityId])

  const handleAuthorize = async () => {
    if (!otp.trim()) { setActionError('Enter the authorization code'); return }
    setAuthorizing(true); setActionError('')
    try {
      setExpense(await authorizeExpensePayout(expenseId, otp.trim()))
      setOtp('')
    } catch (e: unknown) {
      setActionError(e instanceof Error ? e.message : 'Authorization failed')
    } finally { setAuthorizing(false) }
  }

  const handleResend = async () => {
    setResending(true); setActionError('')
    try {
      await resendExpenseOtp(expenseId)
    } catch (e: unknown) {
      setActionError(e instanceof Error ? e.message : 'Could not resend code')
    } finally { setResending(false) }
  }

  const handleRetry = async () => {
    setRetrying(true); setActionError('')
    try {
      setExpense(await retryExpensePayout(expenseId))
    } catch (e: unknown) {
      setActionError(e instanceof Error ? e.message : 'Retry failed')
    } finally { setRetrying(false) }
  }

  const handleManual = async () => {
    if (!manualRef.trim()) { setActionError('Reference is required'); return }
    setManualLoading(true); setActionError('')
    try {
      setExpense(await markExpensePaidManually(expenseId, manualRef.trim()))
      setManualOpen(false)
      setManualRef('')
    } catch (e: unknown) {
      setActionError(e instanceof Error ? e.message : 'Failed to record payout')
    } finally { setManualLoading(false) }
  }

  if (loading) return <LoadingState />
  if (error || !expense) return <ErrorState message={error} onRetry={load} />

  const { color, label } = statusBadge(expense.status)

  return (
    <div className="max-w-lg mx-auto flex flex-col gap-6">
      <div>
        <Badge color={color}>{label}</Badge>
        <h1 className="text-[28px] font-bold tracking-tight mt-2">{expense.title}</h1>
      </div>

      {actionError && (
        <div className="border-2 border-error bg-error-container p-3 text-[13px] font-bold text-error">{actionError}</div>
      )}

      {/* Detail card */}
      <div className="border-2 border-black bg-white p-6 neo-shadow flex flex-col gap-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-[11px] font-bold uppercase tracking-[0.08em] text-on-surface-variant">Amount</p>
            <p className="text-[24px] font-bold">{fmt(expense.amount)}</p>
          </div>
          <div>
            <p className="text-[11px] font-bold uppercase tracking-[0.08em] text-on-surface-variant">Category</p>
            <p className="text-[16px] font-bold">{expense.category}</p>
          </div>
        </div>

        <div>
          <p className="text-[11px] font-bold uppercase tracking-[0.08em] text-on-surface-variant">Requested by</p>
          <p className="text-[14px]">User #{expense.requested_by}</p>
        </div>

        <div>
          <p className="text-[11px] font-bold uppercase tracking-[0.08em] text-on-surface-variant">Date</p>
          <p className="text-[14px]">{new Date(expense.created_at).toLocaleString()}</p>
        </div>

        {/* Destination account */}
        {(expense.destination_bank_name || expense.destination_account_number) && (
          <div className="border-2 border-black bg-surface-container p-4 flex flex-col gap-2">
            <div className="flex items-center gap-2 mb-1">
              <Building2 size={14} className="text-on-surface-variant" />
              <p className="text-[11px] font-bold uppercase tracking-[0.08em] text-on-surface-variant">Sent To</p>
            </div>
            {expense.destination_bank_name && (
              <div>
                <p className="text-[11px] font-bold uppercase tracking-[0.08em] text-on-surface-variant">Bank</p>
                <p className="text-[14px] font-bold">{expense.destination_bank_name}</p>
              </div>
            )}
            {expense.destination_account_number && (
              <div>
                <p className="text-[11px] font-bold uppercase tracking-[0.08em] text-on-surface-variant">Account Number</p>
                <p className="text-[16px] font-bold tracking-[0.06em]">{expense.destination_account_number}</p>
              </div>
            )}
            {expense.destination_account_name && (
              <div>
                <p className="text-[11px] font-bold uppercase tracking-[0.08em] text-on-surface-variant">Account Name</p>
                <p className="text-[14px] font-bold">{expense.destination_account_name}</p>
              </div>
            )}
          </div>
        )}

        {expense.receipt_url && (
          <a
            href={expense.receipt_url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 text-[13px] font-bold text-primary hover:underline"
          >
            <ExternalLink size={14} /> View Receipt
          </a>
        )}
      </div>

      {/* Paid out proof */}
      {expense.status === 'paid_out' && (
        <div className="border-2 border-black bg-primary-container p-4 flex items-center gap-3">
          <Banknote size={16} className="text-primary flex-shrink-0" />
          <div>
            <p className="text-[12px] font-bold uppercase tracking-[0.06em] text-on-surface-variant">
              {expense.manual_payout ? 'Payout Recorded Manually' : 'Payout Confirmed'}
            </p>
            {expense.payout_reference && (
              <p className="text-[14px] font-bold">Ref: {expense.payout_reference}</p>
            )}
            {expense.paid_out_at && (
              <p className="text-[12px] text-on-surface-variant">
                {new Date(expense.paid_out_at).toLocaleString()}
              </p>
            )}
          </div>
        </div>
      )}

      {/* Still sending */}
      {expense.status === 'pending' && (
        <p className="text-[13px] text-on-surface-variant text-center">
          Transfer in progress. Refresh in a moment.
        </p>
      )}

      {/* Awaiting OTP — admin/treasurer only */}
      {expense.status === 'awaiting_otp' && canManage && (
        <div className="border-2 border-black bg-white p-5 neo-shadow flex flex-col gap-3">
          <p className="text-[13px] font-bold">
            Monnify sent an authorization code to complete this transfer.
          </p>
          <input
            autoFocus
            value={otp}
            onChange={(e) => setOtp(e.target.value)}
            placeholder="Enter code"
            className="border-2 border-black px-3 py-2 text-[14px] font-bold bg-white focus:outline-none focus:ring-2 focus:ring-primary"
          />
          <div className="flex gap-2">
            <Button size="sm" loading={authorizing} onClick={handleAuthorize}>
              Confirm & Pay
            </Button>
            <Button size="sm" variant="white" loading={resending} onClick={handleResend}>
              <RefreshCw size={13} /> Resend Code
            </Button>
          </div>
        </div>
      )}

      {/* Failed — retry via API or fall back to manual */}
      {expense.status === 'failed' && canManage && (
        <div className="border-2 border-error bg-error-container p-4 flex flex-col gap-3">
          <div className="flex items-start gap-2">
            <AlertTriangle size={16} className="text-error flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-[13px] font-bold text-error">The transfer didn't go through.</p>
              {expense.payout_error && (
                <p className="text-[12px] text-error mt-1">{expense.payout_error}</p>
              )}
            </div>
          </div>
          <div className="flex gap-2">
            <Button size="sm" variant="white" loading={retrying} onClick={handleRetry}>
              Retry Transfer
            </Button>
            <Button size="sm" variant="white" onClick={() => setManualOpen((v) => !v)}>
              I Sent It Myself
            </Button>
          </div>
          {manualOpen && (
            <div className="flex flex-col gap-2 border-t-2 border-error pt-3">
              <p className="text-[12px] text-on-surface-variant">
                If you transferred the money outside the app, record the reference here.
              </p>
              <div className="flex gap-2 flex-wrap">
                <input
                  value={manualRef}
                  onChange={(e) => setManualRef(e.target.value)}
                  placeholder="e.g. TRF20240112ABC"
                  className="flex-1 min-w-0 border-2 border-black px-3 py-2 text-[14px] font-bold bg-white focus:outline-none focus:ring-2 focus:ring-primary"
                />
                <Button size="sm" variant="black" loading={manualLoading} onClick={handleManual}>
                  Confirm
                </Button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
