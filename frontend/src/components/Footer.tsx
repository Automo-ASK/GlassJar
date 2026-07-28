import { AtSign, Network, ExternalLink } from 'lucide-react'
import Logo from './Logo'

const SOCIAL = [
  { icon: AtSign, label: 'Email' },
  { icon: Network, label: 'Community' },
  { icon: ExternalLink, label: 'LinkedIn' },
]

const LINKS = ['Privacy policy', 'Terms of service', 'Contact support']

export default function Footer() {
  return (
    <footer className="bg-ink-900 text-paper-100">
      <div className="mx-auto max-w-[1400px] px-4 md:px-8 py-14">
        <div className="grid gap-10 md:grid-cols-[1.4fr_1fr_1fr]">
          <div>
            <Logo size="md" variant="white" />
            <p className="mt-5 max-w-xs text-[14px] leading-relaxed text-paper-100/60">
              A shared treasury for African student communities. Every naira gets a name.
            </p>
          </div>

          <nav className="flex flex-col gap-2.5">
            <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-paper-100/40">
              Company
            </p>
            {LINKS.map((link) => (
              <a
                key={link}
                href="#"
                className="flex min-h-[44px] w-fit items-center text-[14px] text-paper-100/75 transition-colors hover:text-gold-400"
              >
                {link}
              </a>
            ))}
          </nav>

          <div className="flex flex-col gap-2.5">
            <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-paper-100/40">
              Elsewhere
            </p>
            <div className="flex gap-2">
              {SOCIAL.map(({ icon: Icon, label }) => (
                <button
                  key={label}
                  aria-label={label}
                  className="flex h-11 w-11 items-center justify-center border-2 border-paper-100/25 text-paper-100/75 transition-colors duration-150 hover:border-gold-400 hover:bg-gold-400 hover:text-ink-900"
                >
                  <Icon size={16} />
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="mt-12 flex flex-col justify-between gap-2 border-t border-paper-100/20 pt-6 sm:flex-row">
          <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-paper-100/40">
            © 2026 AcaFund
          </p>
          <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-paper-100/40">
            Built for African student communities
          </p>
        </div>
      </div>
    </footer>
  )
}
