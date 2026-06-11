import { Suspense } from 'react'
import { format } from 'date-fns'
import { supabase } from '@/lib/supabase'
import { fetchEcomOrders } from '@/lib/api'
import KpiCard from '@/components/KpiCard'
import LiveFeed from '@/components/LiveFeed'
import SalesChart from '@/components/SalesChart'
import InventoryAlerts from '@/components/InventoryAlerts'
import WholesaleCards from '@/components/WholesaleCards'

async function getKpis() {
  const today = format(new Date(), 'yyyy-MM-dd')

  const [posRes, asRes, crmRes, ecomOrders] = await Promise.all([
    supabase.schema('pos').from('transactions')
      .select('transaction_id', { count: 'exact', head: true })
      .eq('transaction_date', today).eq('transaction_type', 'SALE'),
    supabase.schema('after_sales').from('orders')
      .select('repair_id', { count: 'exact', head: true })
      .neq('status', 'collected'),
    supabase.schema('crm').from('clients')
      .select('client_id', { count: 'exact', head: true })
      .gte('created_at', `${today}T00:00:00Z`),
    fetchEcomOrders(today),
  ])

  return {
    boutiqueSales: posRes.count ?? 0,
    onlineOrders: Array.isArray(ecomOrders) ? ecomOrders.length : 0,
    activeRepairs: asRes.count ?? 0,
    newClients: crmRes.count ?? 0,
  }
}

export default async function Dashboard() {
  const kpis = await getKpis().catch(() => ({
    boutiqueSales: 0, onlineOrders: 0, activeRepairs: 0, newClients: 0,
  }))

  const now = new Date()

  return (
    <main className="relative z-10 min-h-screen p-6 md:p-8 max-w-[1400px] mx-auto">

      {/* ── Header ─────────────────────────────────────────────────── */}
      <header className="mb-8 animate-fade-up">
        <div className="flex items-start justify-between flex-wrap gap-4">
          <div>
            <h1
              className="text-5xl md:text-6xl font-light tracking-wide text-cream leading-none"
              style={{ fontFamily: 'var(--font-cormorant)' }}
            >
              Maison Vellara
            </h1>
            <div className="flex items-center gap-3 mt-2">
              <span className="text-xs tracking-[0.3em] uppercase text-gold-dim font-mono">
                Data Platform
              </span>
              <span className="text-obsidian-muted">·</span>
              <span className="flex items-center gap-1.5 text-xs text-emerald-400 font-mono">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse-dot inline-block" />
                Live
              </span>
            </div>
          </div>
          <div className="text-right">
            <p className="text-xs text-obsidian-muted font-mono">
              {format(now, 'EEEE, d MMMM yyyy')}
            </p>
            <p className="text-xs text-gold-dim font-mono mt-0.5">
              Updated {format(now, 'HH:mm')} UTC
            </p>
          </div>
        </div>
        <div className="gold-rule mt-6" />
      </header>

      {/* ── KPI Row ─────────────────────────────────────────────────── */}
      <section className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <KpiCard label="Boutique Sales Today"  value={kpis.boutiqueSales}  unit="txns"   delay={0}   />
        <KpiCard label="Online Orders Today"   value={kpis.onlineOrders}   unit="orders" delay={80}  />
        <KpiCard label="Active Repairs"        value={kpis.activeRepairs}  unit="open"   delay={160} />
        <KpiCard label="New Clients Today"     value={kpis.newClients}     unit="CRM"    delay={240} />
      </section>

      {/* ── Middle Row: Live Feed + Chart ────────────────────────────── */}
      <section className="grid grid-cols-1 lg:grid-cols-2 gap-3 mb-6">
        <Suspense fallback={<div className="card p-5 h-64 animate-pulse" />}>
          <LiveFeed />
        </Suspense>
        <Suspense fallback={<div className="card p-5 h-64 animate-pulse" />}>
          <SalesChart />
        </Suspense>
      </section>

      {/* ── Bottom Row: Inventory + Wholesale ───────────────────────── */}
      <section className="grid grid-cols-1 lg:grid-cols-2 gap-3 mb-8">
        <Suspense fallback={<div className="card p-5 h-48 animate-pulse" />}>
          <InventoryAlerts />
        </Suspense>
        <Suspense fallback={<div className="card p-5 h-48 animate-pulse" />}>
          <WholesaleCards />
        </Suspense>
      </section>

      {/* ── Footer ──────────────────────────────────────────────────── */}
      <footer className="border-t border-obsidian-border pt-6">
        <div className="flex flex-wrap gap-6 items-center justify-between text-[10px] font-mono text-obsidian-muted tracking-widest">
          <div className="flex gap-6">
            <span>SOURCE 1 · SUPABASE POSTGRES</span>
            <span>SOURCE 2 · FASTAPI / FIREBASE</span>
            <span>SOURCE 3 · AZURE BLOB</span>
          </div>
          <span>MAISON VELLARA © {now.getFullYear()} · PORTFOLIO PROJECT</span>
        </div>
      </footer>

    </main>
  )
}

export const revalidate = 60 // ISR — revalidate server data every 60s
