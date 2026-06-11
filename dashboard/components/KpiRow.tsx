'use client'
import { useEffect, useState } from 'react'
import { supabase } from '@/lib/supabase'
import { fetchEcomOrders } from '@/lib/api'
import { format } from 'date-fns'
import KpiCard from './KpiCard'

export default function KpiRow() {
  const [k, setK] = useState<{ boutique: number | null; online: number | null; repairs: number | null; clients: number | null }>(
    { boutique: null, online: null, repairs: null, clients: null }
  )

  useEffect(() => {
    const today = format(new Date(), 'yyyy-MM-dd')
    async function load() {
      const [pos, as, crm, orders] = await Promise.all([
        supabase.schema('pos').from('transactions')
          .select('transaction_id', { count: 'exact', head: true })
          .eq('transaction_date', today).eq('transaction_type', 'SALE'),
        supabase.schema('after_sales').from('orders')
          .select('repair_id', { count: 'exact', head: true }).neq('status', 'collected'),
        supabase.schema('crm').from('clients')
          .select('client_id', { count: 'exact', head: true }).gte('created_at', `${today}T00:00:00Z`),
        fetchEcomOrders(today),
      ])
      setK({
        boutique: pos.count ?? 0,
        repairs: as.count ?? 0,
        clients: crm.count ?? 0,
        online: Array.isArray(orders) ? orders.length : 0,
      })
    }
    load()
  }, [])

  return (
    <section className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
      <KpiCard label="Boutique Sales Today" value={k.boutique} unit="txns" delay={0} />
      <KpiCard label="Online Orders Today"  value={k.online}   unit="orders" delay={80} />
      <KpiCard label="Active Repairs"       value={k.repairs}  unit="open" delay={160} />
      <KpiCard label="New Clients Today"    value={k.clients}  unit="CRM" delay={240} />
    </section>
  )
}
