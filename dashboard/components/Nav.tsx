'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'

const links = [
  { href: '/',            label: 'Overview' },
  { href: '/boutiques',   label: 'Boutiques' },
  { href: '/clients',     label: 'Clients' },
  { href: '/inventory',   label: 'Inventory' },
  { href: '/online',      label: 'Online Store' },
  { href: '/wholesale',   label: 'Wholesale' },
]

export default function Nav() {
  const path = usePathname()
  return (
    <nav className="w-56 min-h-screen bg-nav flex flex-col flex-shrink-0 sticky top-0">
      <div className="px-6 pt-8 pb-6 border-b border-white/5">
        <h1 className="text-xl text-white font-light tracking-wide leading-tight"
          style={{ fontFamily: 'var(--font-cormorant)' }}>
          Maison<br />Vellara
        </h1>
        <div className="flex items-center gap-1.5 mt-2">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse-dot" />
          <span className="text-[10px] text-emerald-400/80 tracking-widest uppercase font-mono">Live</span>
        </div>
      </div>

      <div className="flex flex-col gap-0.5 p-3 flex-1">
        {links.map(l => (
          <Link key={l.href} href={l.href}
            className={`px-3 py-2 text-xs tracking-wide rounded-sm transition-colors font-mono
              ${path === l.href
                ? 'bg-gold/15 text-gold border-l-2 border-gold pl-[10px]'
                : 'text-white/40 hover:text-white/80 hover:bg-white/5'
              }`}>
            {l.label}
          </Link>
        ))}
      </div>

      <div className="px-4 pb-6 text-[9px] text-white/20 font-mono leading-relaxed">
        <p>SOURCE 1 · SUPABASE</p>
        <p>SOURCE 2 · FASTAPI</p>
        <p>SOURCE 3 · AZURE BLOB</p>
      </div>
    </nav>
  )
}
