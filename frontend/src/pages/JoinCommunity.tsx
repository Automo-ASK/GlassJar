import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { UserCheck } from 'lucide-react'
import Input from '../components/ui/Input'
import Button from '../components/ui/Button'
import { joinCommunity, lookupCommunity } from '../lib/api'
import type { CommunityLookup } from '../lib/types'

export default function JoinCommunity() {
  const navigate = useNavigate()
  const [code, setCode] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [lookup, setLookup] = useState<CommunityLookup | null>(null)
  const [claimId, setClaimId] = useState<number | null>(null)

  const friendlyError = (err: unknown) => {
    const msg = err instanceof Error ? err.message : ''
    if (msg.toLowerCase().includes('invalid') || msg.toLowerCase().includes('not found'))
      return 'Invalid invite code. Check with your admin and try again.'
    if (msg.toLowerCase().includes('already'))
      return "You're already a member of this community."
    return msg || 'Failed to join. Please try again.'
  }

  const handleLookup = async (e: FormEvent) => {
    e.preventDefault()
    if (!code.trim()) { setError('Please enter an invite code'); return }
    setError('')
    setLoading(true)
    try {
      const found = await lookupCommunity(code.trim().toLowerCase())
      setLookup(found)
      setClaimId(null)
    } catch (err: unknown) {
      setError(friendlyError(err))
    } finally {
      setLoading(false)
    }
  }

  const handleJoin = async () => {
    setError('')
    setLoading(true)
    try {
      const member = await joinCommunity(code.trim().toLowerCase(), claimId ?? undefined)
      navigate(`/communities/${member.community_id}`)
    } catch (err: unknown) {
      setError(friendlyError(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-lg mx-auto">
      <div className="mb-8">
        <h1 className="text-[32px] font-bold tracking-tight">Join a Community</h1>
        <p className="text-[15px] text-on-surface-variant mt-1">
          Enter the invite code your community admin shared with you.
        </p>
      </div>

      {error && (
        <div className="mb-6 border-2 border-error bg-error-container p-3 text-[13px] font-bold text-error">
          {error}
        </div>
      )}

      {!lookup ? (
        <div className="border-4 border-black neo-shadow-lg bg-white p-8">
          <form onSubmit={handleLookup} className="flex flex-col gap-5">
            <Input
              id="code"
              label="Invite Code"
              placeholder="e.g. aB3xY9kL"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              className="text-center text-[22px] tracking-[0.2em] font-bold"
            />
            <Button type="submit" loading={loading} fullWidth size="lg">
              Find Community
            </Button>
          </form>
        </div>
      ) : (
        <div className="border-4 border-black neo-shadow-lg bg-white p-8 flex flex-col gap-5">
          <div>
            <p className="text-[12px] font-bold uppercase tracking-widest text-on-surface-variant">You're joining</p>
            <h2 className="text-[22px] font-bold">{lookup.name}</h2>
            {lookup.description && (
              <p className="text-[13px] text-on-surface-variant mt-1">{lookup.description}</p>
            )}
          </div>

          {lookup.unclaimed_members.length > 0 && (
            <div>
              <p className="text-[13px] font-bold mb-2 flex items-center gap-1.5">
                <UserCheck size={14} className="text-primary" />
                Are you already on the class list? Claim your spot:
              </p>
              <div className="flex flex-col gap-1.5 max-h-56 overflow-y-auto border-2 border-black p-2">
                {lookup.unclaimed_members.map((m) => (
                  <label
                    key={m.id}
                    className={`flex items-center gap-2 px-3 py-2 border-2 cursor-pointer text-[14px] font-bold ${
                      claimId === m.id ? 'border-primary bg-primary-container' : 'border-transparent hover:bg-surface-container'
                    }`}
                  >
                    <input
                      type="radio"
                      name="claim"
                      checked={claimId === m.id}
                      onChange={() => setClaimId(m.id)}
                    />
                    {m.display_name}
                  </label>
                ))}
                <label
                  className={`flex items-center gap-2 px-3 py-2 border-2 cursor-pointer text-[14px] ${
                    claimId === null ? 'border-primary bg-primary-container font-bold' : 'border-transparent hover:bg-surface-container'
                  }`}
                >
                  <input
                    type="radio"
                    name="claim"
                    checked={claimId === null}
                    onChange={() => setClaimId(null)}
                  />
                  I'm not on this list. Join as a new member
                </label>
              </div>
            </div>
          )}

          <div className="flex gap-2">
            <Button loading={loading} fullWidth size="lg" onClick={handleJoin}>
              {claimId !== null ? 'Claim & Join' : 'Join Community'}
            </Button>
            <Button variant="white" size="lg" onClick={() => { setLookup(null); setError('') }}>
              Back
            </Button>
          </div>
        </div>
      )}

      <p className="mt-6 text-center text-[13px] text-on-surface-variant">
        Don't have a code? Ask your class admin or{' '}
        <button
          onClick={() => navigate('/communities/create')}
          className="font-bold text-primary hover:underline"
        >
          create your own community
        </button>
        .
      </p>
    </div>
  )
}
