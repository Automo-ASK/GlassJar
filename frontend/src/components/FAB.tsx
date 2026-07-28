import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { Plus, Wallet, UserPlus, ReceiptText } from 'lucide-react'

export default function FAB() {
  const [open, setOpen] = useState(false)
  const navigate = useNavigate()
  const { pathname } = useLocation()

  const match = pathname.match(/^\/communities\/(\d+)/)
  const communityId = match ? match[1] : null
  if (!communityId) return null

  const QUICK_ACTIONS = [
    { icon: Wallet, label: 'New collection', to: `/communities/${communityId}/collections/create` },
    { icon: ReceiptText, label: 'New expense', to: `/communities/${communityId}/expenses/create` },
    { icon: UserPlus, label: 'Members', to: `/communities/${communityId}/members` },
  ]

  return (
    <>
      {open && (
        <div
          className="fixed inset-0 z-40 bg-ink-900/25 animate-fade-in"
          onClick={() => setOpen(false)}
          aria-hidden
        />
      )}

      <div className="fixed bottom-6 right-6 z-50 flex flex-col-reverse items-end gap-2">
        {open &&
          QUICK_ACTIONS.map(({ icon: Icon, label, to }, i) => (
            <button
              key={label}
              onClick={() => { setOpen(false); navigate(to) }}
              style={{ animationDelay: `${i * 45}ms` }}
              className="flex animate-fade-up items-center gap-2.5 border-2 border-ink-900 bg-paper-0 px-4 py-2.5 font-mono text-[12px] uppercase tracking-[0.1em] shadow-neo transition-all duration-150 hover:-translate-x-0.5 hover:-translate-y-0.5 hover:bg-gold-400"
            >
              <Icon size={14} />
              {label}
            </button>
          ))}

        <button
          onClick={() => setOpen(!open)}
          className={`flex h-14 w-14 items-center justify-center border-2 border-ink-900 bg-rose-600 text-white shadow-neo transition-all duration-200 ${
            open ? 'rotate-45' : 'hover:-translate-x-0.5 hover:-translate-y-0.5 hover:shadow-neo-lg'
          }`}
          aria-label="Quick actions"
          aria-expanded={open}
        >
          <Plus size={24} strokeWidth={2.5} />
        </button>
      </div>
    </>
  )
}
