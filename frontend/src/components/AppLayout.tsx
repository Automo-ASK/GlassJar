import { useState } from 'react'
import { Outlet, NavLink, useNavigate, useLocation } from 'react-router-dom'
import {
  LayoutDashboard, Users, Wallet, Receipt, BookOpen,
  Sparkles, LogOut, Menu, X, ChevronLeft,
} from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import Logo from './Logo'
import FAB from './FAB'

function NavItem({
  to, icon: Icon, label, onClick,
}: {
  to?: string; icon: React.ElementType; label: string; onClick?: () => void
}) {
  const base =
    'flex items-center gap-3 border-2 px-3 py-2.5 font-mono text-[12px] uppercase tracking-[0.1em] transition-all duration-150'

  if (to) {
    return (
      <NavLink
        to={to}
        end
        className={({ isActive }) =>
          `${base} ${
            isActive
              ? 'border-ink-900 bg-rose-600 text-white shadow-neo-sm'
              : 'border-transparent text-ink-600 hover:border-ink-900 hover:bg-paper-0'
          }`
        }
        onClick={onClick}
      >
        <Icon size={15} strokeWidth={2} />
        {label}
      </NavLink>
    )
  }

  return (
    <button
      className={`${base} w-full border-transparent text-left text-ink-600 hover:border-ink-900 hover:bg-paper-0`}
      onClick={onClick}
    >
      <Icon size={15} strokeWidth={2} />
      {label}
    </button>
  )
}

export default function AppLayout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const communityMatch = pathname.match(/^\/communities\/(\d+)/)
  const communityId = communityMatch ? communityMatch[1] : undefined
  const [mobileOpen, setMobileOpen] = useState(false)

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const initials = (user?.full_name ?? '')
    .split(' ')
    .map((p) => p[0])
    .filter(Boolean)
    .slice(0, 2)
    .join('')
    .toUpperCase()

  const communityLinks = communityId
    ? [
        { to: `/communities/${communityId}`, icon: LayoutDashboard, label: 'Dashboard' },
        { to: `/communities/${communityId}/members`, icon: Users, label: 'Members' },
        { to: `/communities/${communityId}/collections`, icon: Wallet, label: 'Collections' },
        { to: `/communities/${communityId}/expenses`, icon: Receipt, label: 'Expenses' },
        { to: `/communities/${communityId}/ledger`, icon: BookOpen, label: 'Ledger' },
        { to: `/communities/${communityId}/assistant`, icon: Sparkles, label: 'Assistant' },
      ]
    : []

  const SidebarContent = () => (
    <div className="flex h-full flex-col overflow-y-auto">
      <div className="flex h-[64px] shrink-0 items-center justify-between border-b-2 border-ink-900 px-4">
        <Logo size="md" />
        <button
          className="border-2 border-ink-900 p-1 md:hidden"
          onClick={() => setMobileOpen(false)}
          aria-label="Close menu"
        >
          <X size={16} />
        </button>
      </div>

      {communityId && (
        <NavLink
          to="/communities"
          className="flex items-center gap-1.5 border-b-2 border-ink-900 px-4 py-2.5 font-mono text-[11px] uppercase tracking-[0.14em] text-ink-500 transition-colors hover:text-rose-600"
          onClick={() => setMobileOpen(false)}
        >
          <ChevronLeft size={13} />
          My communities
        </NavLink>
      )}

      <nav className="flex flex-1 flex-col gap-1 p-2">
        {!communityId && (
          <NavItem
            to="/communities"
            icon={LayoutDashboard}
            label="My communities"
            onClick={() => setMobileOpen(false)}
          />
        )}
        {communityLinks.map((link) => (
          <NavItem key={link.to} {...link} onClick={() => setMobileOpen(false)} />
        ))}
      </nav>

      <div className="shrink-0 border-t-2 border-ink-900 p-3">
        <div className="mb-3 flex items-center gap-2.5">
          <span className="flex h-8 w-8 shrink-0 items-center justify-center border-2 border-ink-900 bg-gold-400 font-mono text-[11px] font-bold">
            {initials || '?'}
          </span>
          <div className="min-w-0">
            <p className="truncate text-[13px] font-semibold">{user?.full_name}</p>
            <p className="truncate font-mono text-[10px] text-ink-500">{user?.email}</p>
          </div>
        </div>
        <button
          onClick={handleLogout}
          className="flex w-full items-center gap-2 border-2 border-transparent px-3 py-2 font-mono text-[11px] uppercase tracking-[0.12em] text-ink-500 transition-all duration-150 hover:border-ink-900 hover:bg-rose-600 hover:text-white"
        >
          <LogOut size={14} />
          Sign out
        </button>
      </div>
    </div>
  )

  return (
    <div className="flex min-h-screen bg-paper-100">
      <aside className="sticky top-0 hidden h-screen w-60 shrink-0 flex-col border-r-2 border-ink-900 bg-paper-100 md:flex">
        <SidebarContent />
      </aside>

      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-ink-900/50 md:hidden animate-fade-in"
          onClick={() => setMobileOpen(false)}
        />
      )}
      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-[270px] flex-col border-r-2 border-ink-900 bg-paper-100 transition-transform duration-200 ease-soft md:hidden ${
          mobileOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <SidebarContent />
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex h-[56px] items-center gap-3 border-b-2 border-ink-900 bg-paper-100 px-4 md:hidden">
          <button
            onClick={() => setMobileOpen(true)}
            aria-label="Open menu"
            className="border-2 border-ink-900 p-1.5"
          >
            <Menu size={16} />
          </button>
          <Logo size="sm" />
        </header>

        <main className="mx-auto w-full max-w-5xl flex-1 p-4 md:p-8">
          <Outlet />
        </main>
      </div>

      <FAB />
    </div>
  )
}
