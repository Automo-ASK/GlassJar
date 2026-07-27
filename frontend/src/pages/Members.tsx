import { useEffect, useState, type FormEvent } from 'react'
import { useParams } from 'react-router-dom'
import { User, RefreshCw, UserPlus, Users, Trash2 } from 'lucide-react'
import Button from '../components/ui/Button'
import Badge from '../components/ui/Badge'
import Input from '../components/ui/Input'
import LoadingState from '../components/ui/LoadingState'
import EmptyState from '../components/ui/EmptyState'
import ErrorState from '../components/ui/ErrorState'
import {
  getMembers, changeMemberRole, addMember, addMembersBulk, removeMember,
} from '../lib/api'
import type { CommunityMember, MemberRole } from '../lib/types'
import { useAuth } from '../contexts/AuthContext'

const ROLES: MemberRole[] = ['admin', 'treasurer', 'auditor', 'member']

const roleBadgeColor = (r: MemberRole) =>
  r === 'admin' ? 'green' : r === 'treasurer' ? 'blue' : r === 'auditor' ? 'yellow' : 'gray'

export default function Members() {
  const { id } = useParams<{ id: string }>()
  const communityId = Number(id)
  const { user } = useAuth()

  const [members, setMembers] = useState<CommunityMember[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [changing, setChanging] = useState<number | null>(null)
  const [roleError, setRoleError] = useState<Record<number, string>>({})

  const [showAdd, setShowAdd] = useState(false)
  const [addName, setAddName] = useState('')
  const [addEmail, setAddEmail] = useState('')
  const [bulkNames, setBulkNames] = useState('')
  const [bulkMode, setBulkMode] = useState(false)
  const [adding, setAdding] = useState(false)
  const [addError, setAddError] = useState('')

  const myRole = members.find((m) => m.user_id === user?.id)?.role
  const isAdmin = myRole === 'admin'

  const load = async () => {
    setLoading(true)
    setError('')
    try {
      setMembers(await getMembers(communityId))
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load members')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [communityId])

  const handleRoleChange = async (memberId: number, newRole: MemberRole) => {
    setChanging(memberId)
    setRoleError((prev) => ({ ...prev, [memberId]: '' }))
    try {
      const updated = await changeMemberRole(communityId, memberId, newRole)
      setMembers((prev) => prev.map((m) => (m.id === memberId ? { ...m, role: updated.role } : m)))
    } catch (e: unknown) {
      setRoleError((prev) => ({
        ...prev,
        [memberId]: e instanceof Error ? e.message : 'Role change failed',
      }))
    } finally {
      setChanging(null)
    }
  }

  const handleRemove = async (member: CommunityMember) => {
    if (!confirm(`Remove ${member.display_name} from the community?`)) return
    setRoleError((prev) => ({ ...prev, [member.id]: '' }))
    try {
      await removeMember(communityId, member.id)
      setMembers((prev) => prev.filter((m) => m.id !== member.id))
    } catch (e: unknown) {
      setRoleError((prev) => ({
        ...prev,
        [member.id]: e instanceof Error ? e.message : 'Remove failed',
      }))
    }
  }

  const handleAdd = async (e: FormEvent) => {
    e.preventDefault()
    setAddError('')
    setAdding(true)
    try {
      if (bulkMode) {
        const names = bulkNames.split('\n').map((n) => n.trim()).filter(Boolean)
        if (names.length === 0) { setAddError('Paste at least one name'); return }
        const created = await addMembersBulk(communityId, names)
        setMembers((prev) => [...prev, ...created])
        setBulkNames('')
      } else {
        if (!addName.trim()) { setAddError('Name is required'); return }
        const created = await addMember(communityId, {
          display_name: addName.trim(),
          email: addEmail.trim() || undefined,
        })
        setMembers((prev) => [...prev, created])
        setAddName('')
        setAddEmail('')
      }
    } catch (err: unknown) {
      setAddError(err instanceof Error ? err.message : 'Failed to add')
    } finally {
      setAdding(false)
    }
  }

  if (loading) return <LoadingState />
  if (error) return <ErrorState message={error} onRetry={load} />

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-[28px] font-bold tracking-tight">Members</h1>
          <p className="text-[14px] text-on-surface-variant">{members.length} member{members.length !== 1 ? 's' : ''}</p>
        </div>
        <div className="flex gap-2">
          {isAdmin && (
            <Button variant="primary" size="sm" onClick={() => setShowAdd((v) => !v)}>
              <UserPlus size={13} />
              Add Members
            </Button>
          )}
          <Button variant="white" size="sm" onClick={load}>
            <RefreshCw size={13} />
            Refresh
          </Button>
        </div>
      </div>

      {isAdmin && showAdd && (
        <form onSubmit={handleAdd} className="border-2 border-black bg-white p-5 neo-shadow flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <h2 className="text-[14px] font-bold uppercase tracking-[0.06em]">
              {bulkMode ? 'Paste your class list' : 'Add a member'}
            </h2>
            <button
              type="button"
              onClick={() => { setBulkMode((v) => !v); setAddError('') }}
              className="flex items-center gap-1.5 text-[12px] font-bold text-primary hover:underline"
            >
              <Users size={13} />
              {bulkMode ? 'Add one by one' : 'Bulk paste names'}
            </button>
          </div>

          {bulkMode ? (
            <textarea
              value={bulkNames}
              onChange={(e) => setBulkNames(e.target.value)}
              rows={6}
              placeholder={'One name per line, e.g.\nAda Obi\nBola Ade\nChidi Eze'}
              className="border-2 border-black px-3 py-2 text-[14px] bg-white focus:outline-none focus:ring-2 focus:ring-primary"
            />
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <Input
                id="add-name"
                label="Full Name"
                placeholder="e.g. Ada Obi"
                value={addName}
                onChange={(e) => setAddName(e.target.value)}
              />
              <Input
                id="add-email"
                label="Email (optional — lets them claim their spot)"
                placeholder="ada@example.com"
                value={addEmail}
                onChange={(e) => setAddEmail(e.target.value)}
              />
            </div>
          )}

          {addError && <p className="text-[12px] text-error font-bold">{addError}</p>}
          <div className="flex gap-2">
            <Button type="submit" size="sm" loading={adding}>
              {bulkMode ? 'Add All' : 'Add Member'}
            </Button>
            <Button type="button" size="sm" variant="white" onClick={() => setShowAdd(false)}>
              Done
            </Button>
          </div>
          <p className="text-[12px] text-on-surface-variant">
            Members added by name don't need an account — they can pay as guests
            from the collection link and claim their spot later with the invite code.
          </p>
        </form>
      )}

      {members.length === 0 ? (
        <EmptyState icon={User} title="No members yet" description="Add your class list or share the invite code." />
      ) : (
        <div className="flex flex-col gap-2">
          {members.map((m) => (
            <div
              key={m.id}
              className="border-2 border-black bg-white p-4 neo-shadow flex flex-col sm:flex-row sm:items-center justify-between gap-3"
            >
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 bg-surface-container border-2 border-black flex items-center justify-center flex-shrink-0">
                  <User size={16} />
                </div>
                <div>
                  <p className="text-[14px] font-bold flex items-center gap-2">
                    {m.display_name}
                    {!m.is_claimed && (
                      <span className="text-[10px] font-bold uppercase tracking-widest border border-black px-1.5 py-0.5 bg-surface-container text-on-surface-variant">
                        Unclaimed
                      </span>
                    )}
                  </p>
                  {m.email && (
                    <p className="text-[12px] text-on-surface-variant">{m.email}</p>
                  )}
                </div>
              </div>

              <div className="flex items-center gap-3">
                {isAdmin && m.user_id !== user?.id ? (
                  <div className="flex flex-col gap-1">
                    <div className="flex items-center gap-2">
                      <select
                        value={m.role}
                        disabled={changing === m.id || !m.is_claimed}
                        title={m.is_claimed ? undefined : 'Members must claim their spot (create an account) before holding a role'}
                        onChange={(e) => handleRoleChange(m.id, e.target.value as MemberRole)}
                        className="border-2 border-black bg-white px-3 py-1.5 text-[13px] font-bold uppercase tracking-widest focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
                      >
                        {ROLES.map((r) => (
                          <option key={r} value={r}>{r}</option>
                        ))}
                      </select>
                      <button
                        onClick={() => handleRemove(m)}
                        className="border-2 border-black p-1.5 neo-shadow-sm neo-btn bg-white text-error"
                        aria-label={`Remove ${m.display_name}`}
                        title="Remove member"
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                    {changing === m.id && (
                      <p className="text-[11px] text-on-surface-variant">Updating…</p>
                    )}
                    {roleError[m.id] && (
                      <p className="text-[11px] text-error font-bold">{roleError[m.id]}</p>
                    )}
                  </div>
                ) : (
                  <Badge color={roleBadgeColor(m.role)}>{m.role}</Badge>
                )}
                {m.user_id === user?.id && (
                  <span className="text-[11px] font-bold text-on-surface-variant">(you)</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

    </div>
  )
}
