import { useEffect, useRef, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Plus, Receipt, RefreshCw, Banknote, Clock, AlertTriangle, KeyRound } from 'lucide-react'
import Button from '../components/ui/Button'
import Badge from '../components/ui/Badge'
import LoadingState from '../components/ui/LoadingState'
import EmptyState from '../components/ui/EmptyState'
import ErrorState from '../components/ui/ErrorState'
import { getExpenses, getMembers } from '../lib/api'
import type { Expense, CommunityMember, ExpenseStatus } from '../lib/types'
import { useAuth } from '../contexts/AuthContext'

function fmt(n: number) { return `₦${n.toLocaleString('en-NG')}` }

function statusBadge(s: ExpenseStatus): { color: 'yellow' | 'blue' | 'green' | 'red'; label: string } {
  switch (s) {
    case 'pending':       return { color: 'yellow', label: 'Sending…' }
    case 'awaiting_otp':  return { color: 'blue',   label: 'Needs Code' }
    case 'paid_out':      return { color: 'green',  label: 'Paid Out' }
    case 'failed':        return { color: 'red',    label: 'Failed' }
  }
}

const StatusIcon = ({ status }: { status: ExpenseStatus }) => {
  if (status === 'paid_out') return <Banknote size={16} className="text-primary" />
  if (status === 'awaiting_otp') return <KeyRound size={16} className="text-tertiary" />
  if (status === 'failed') return <AlertTriangle size={16} className="text-error" />
  return <Clock size={16} className="text-on-surface-variant" />
}

export default function Expenses() {
  const { id } = useParams<{ id: string }>()
  const communityId = Number(id)
  const navigate = useNavigate()
  const { user } = useAuth()

  const [expenses, setExpenses] = useState<Expense[]>([])
  const [members, setMembers] = useState<CommunityMember[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const myRole = members.find((m) => m.user_id === user?.id)?.role
  const canManage = myRole === 'admin' || myRole === 'treasurer'

  const load = async () => {
    setLoading(true); setError('')
    try {
      const [exps, mems] = await Promise.all([
        getExpenses(communityId),
        getMembers(communityId),
      ])
      setExpenses(exps)
      setMembers(mems)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load expenses')
    } finally { setLoading(false) }
  }

  useEffect(() => { load() }, [communityId])

  const pollRef = useRef<number | null>(null)
  const hasInFlight = expenses.some((e) => e.status === 'pending' || e.status === 'awaiting_otp')

  useEffect(() => {
    if (hasInFlight) {
      pollRef.current = window.setInterval(async () => {
        try {
          const exps = await getExpenses(communityId)
          setExpenses(exps)
        } catch {
          // keep polling
        }
      }, 5000)
    }
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [hasInFlight, communityId])

  const needsAttention = expenses.filter((e) => e.status === 'awaiting_otp' || e.status === 'failed')

  if (loading) return <LoadingState />
  if (error) return <ErrorState message={error} onRetry={load} />

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-[28px] font-bold tracking-tight">Expenses</h1>
          <p className="text-[14px] text-on-surface-variant">
            {expenses.length} total
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="white" size="sm" onClick={load}>
            <RefreshCw size={13} /> Refresh
          </Button>
          {canManage && (
            <Button size="sm" onClick={() => navigate(`/communities/${communityId}/expenses/create`)}>
              <Plus size={14} /> Pay For Something
            </Button>
          )}
        </div>
      </div>

      {canManage && needsAttention.length > 0 && (
        <div className="border-2 border-black bg-tertiary-container p-4">
          <p className="text-[13px] font-bold mb-3">
            {needsAttention.length} expense{needsAttention.length !== 1 ? 's' : ''} need attention
          </p>
          <div className="flex flex-col gap-2">
            {needsAttention.map((exp) => {
              const { color, label } = statusBadge(exp.status)
              return (
                <button
                  key={exp.id}
                  onClick={() => navigate(`/expenses/${exp.id}?community=${communityId}`)}
                  className="border-2 border-black bg-white p-3 flex justify-between items-center neo-shadow-sm neo-btn text-left"
                >
                  <span className="text-[14px] font-bold">{exp.title}</span>
                  <span className="flex items-center gap-2 text-[13px] font-bold">
                    {fmt(exp.amount)}
                    <Badge color={color}>{label}</Badge>
                  </span>
                </button>
              )
            })}
          </div>
        </div>
      )}

      {expenses.length === 0 ? (
        <EmptyState
          icon={Receipt}
          title="No expenses yet"
          description={canManage ? 'Pay for something to get started.' : 'No expenses have been recorded.'}
          action={canManage && (
            <Button size="sm" onClick={() => navigate(`/communities/${communityId}/expenses/create`)}>
              <Plus size={14} /> Pay For Something
            </Button>
          )}
        />
      ) : (
        <div className="flex flex-col gap-2">
          {expenses.map((exp) => {
            const { color, label } = statusBadge(exp.status)
            return (
              <button
                key={exp.id}
                onClick={() => navigate(`/expenses/${exp.id}?community=${communityId}`)}
                className="border-2 border-black bg-white neo-shadow p-4 neo-btn text-left flex items-center justify-between gap-4 w-full"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <StatusIcon status={exp.status} />
                  <div className="min-w-0">
                    <p className="text-[15px] font-bold truncate">{exp.title}</p>
                    <p className="text-[12px] text-on-surface-variant">{exp.category}</p>
                  </div>
                </div>
                <div className="text-right flex-shrink-0">
                  <p className="text-[15px] font-bold">{fmt(exp.amount)}</p>
                  <Badge color={color}>{label}</Badge>
                </div>
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}
