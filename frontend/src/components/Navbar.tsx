import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Menu, X } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import Logo from './Logo'

const NAV_LINKS = [
  { label: 'Features', href: '#features' },
  { label: 'How it works', href: '#dashboard' },
  { label: 'Start', href: '#about' },
]

export default function Navbar() {
  const [menuOpen, setMenuOpen] = useState(false)
  const [scrolled, setScrolled] = useState(false)
  const navigate = useNavigate()
  const { user } = useAuth()

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <nav
      className={`sticky top-0 z-50 border-b-2 border-ink-900 bg-paper-100 transition-shadow duration-200 ${
        scrolled ? 'shadow-neo-sm' : ''
      }`}
    >
      <div className="mx-auto flex h-[64px] max-w-[1400px] items-center justify-between px-4 md:px-8">
        <button onClick={() => navigate('/')} aria-label="GlassJar home" className="shrink-0">
          <Logo size="md" />
        </button>

        <div className="hidden items-center gap-8 md:flex">
          {NAV_LINKS.map(({ label, href }) => (
            <a
              key={label}
              href={href}
              className="flex min-h-[44px] items-center font-mono text-[12px] uppercase tracking-[0.14em] text-ink-600 transition-colors duration-150 hover:text-rose-600"
            >
              {label}
            </a>
          ))}
        </div>

        <div className="flex items-center gap-2">
          {user ? (
            <button
              onClick={() => navigate('/communities')}
              className="hidden border-2 border-ink-900 bg-rose-600 px-5 py-2 font-display text-[13px] uppercase text-white shadow-neo-sm transition-all duration-150 hover:-translate-x-0.5 hover:-translate-y-0.5 hover:shadow-neo sm:block"
            >
              Dashboard
            </button>
          ) : (
            <>
              <button
                onClick={() => navigate('/login')}
                className="hidden min-h-[44px] px-3 font-mono text-[12px] uppercase tracking-[0.14em] text-ink-600 transition-colors duration-150 hover:text-rose-600 sm:block"
              >
                Sign in
              </button>
              <button
                onClick={() => navigate('/register')}
                className="hidden border-2 border-ink-900 bg-rose-600 px-5 py-2 font-display text-[13px] uppercase text-white shadow-neo-sm transition-all duration-150 hover:-translate-x-0.5 hover:-translate-y-0.5 hover:shadow-neo sm:block"
              >
                Start
              </button>
            </>
          )}

          <button
            className="flex h-11 w-11 items-center justify-center border-2 border-ink-900 text-ink-900 transition-colors duration-150 hover:bg-ink-900 hover:text-paper-100 md:hidden"
            onClick={() => setMenuOpen(!menuOpen)}
            aria-label="Toggle menu"
            aria-expanded={menuOpen}
          >
            {menuOpen ? <X size={18} /> : <Menu size={18} />}
          </button>
        </div>
      </div>

      {menuOpen && (
        <div className="absolute inset-x-0 top-full border-b-2 border-ink-900 bg-paper-100 md:hidden">
          {NAV_LINKS.map(({ label, href }) => (
            <a
              key={label}
              href={href}
              onClick={() => setMenuOpen(false)}
              className="block border-t border-ink-100 px-4 py-3.5 font-mono text-[13px] uppercase tracking-[0.14em]"
            >
              {label}
            </a>
          ))}
          <div className="flex gap-2 border-t-2 border-ink-900 p-4">
            {user ? (
              <button
                onClick={() => { setMenuOpen(false); navigate('/communities') }}
                className="flex-1 border-2 border-ink-900 bg-rose-600 py-3 font-display text-[13px] uppercase text-white shadow-neo-sm"
              >
                Dashboard
              </button>
            ) : (
              <>
                <button
                  onClick={() => { setMenuOpen(false); navigate('/login') }}
                  className="flex-1 border-2 border-ink-900 bg-paper-0 py-3 font-display text-[13px] uppercase shadow-neo-sm"
                >
                  Sign in
                </button>
                <button
                  onClick={() => { setMenuOpen(false); navigate('/register') }}
                  className="flex-1 border-2 border-ink-900 bg-rose-600 py-3 font-display text-[13px] uppercase text-white shadow-neo-sm"
                >
                  Start
                </button>
              </>
            )}
          </div>
        </div>
      )}
    </nav>
  )
}
