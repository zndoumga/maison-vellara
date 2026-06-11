'use client'
import { useEffect, useState, useCallback } from 'react'
import { supabase } from '@/lib/supabase'
import { STORE_NAMES, TYPE_BADGE } from '@/lib/constants'
import PageHeader from '@/components/PageHeader'

const PAGE_SIZE = 50

interface Tx {
  transaction_id: string; store_id: string; terminal_id: string
  transaction_date: string; transaction_time: string; advisor_id: string | null
  client_id: string | null; sku_id: string; quantity: number; unit_price: number
  currency: string; payment_method: string; transaction_type: string
}

export default function BoutiquesPage() {
  const [rows, setRows] = useState<Tx[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(0)
  const [store, setStore] = useState('')
  const [type, setType] = useState('')
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    let q = supabase.schema('pos').from('transactions')
      .select('*', { count: 'exact' })
      .order('transaction_date', { ascending: false })
      .order('transaction_time', { ascending: false })
      .range(page * PAGE_SIZE, page * PAGE_SIZE + PAGE_SIZE - 1)
    if (store) q = q.eq('store_id', store)
    if (type) q = q.eq('transaction_type', type)
    const { data, count } = await q
    setRows((data as Tx[]) ?? [])
    setTotal(count ?? 0)
    setLoading(false)
  }, [page, store, type])

  useEffect(() => { load() }, [load])
  useEffect(() => { setPage(0) }, [store, type])

  const pages = Math.ceil(total / PAGE_SIZE)

  return (
    <div className="p-6 md:p-8 max-w-[1400px] mx-auto">
      <PageHeader title="Boutiques" subtitle="POS transactions — Source 1 · Supabase Postgres" />

      <div className="flex flex-wrap gap-3 mb-4 items-center">
        <select value={store} onChange={e => setStore(e.target.value)}
          className="bg-white border border-paper-border rounded-sm px-3 py-1.5 text-xs font-mono text-ink">
          <option value="">All stores</option>
          {Object.entries(STORE_NAMES).map(([id, name]) => <option key={id} value={id}>{name}</option>)}
        </select>
        <select value={type} onChange={e => setType(e.target.value)}
          className="bg-white border border-paper-border rounded-sm px-3 py-1.5 text-xs font-mono text-ink">
          <option value="">All types</option>
          <option value="SALE">Sale</option>
          <option value="RETURN">Return</option>
          <option value="CORRECTION">Correction</option>
        </select>
        <span className="text-xs text-ink-faint font-mono ml-auto">
          {total.toLocaleString()} transactions
        </span>
      </div>

      <div className="card overflow-x-auto">
        <table>
          <thead><tr>
            <th>Transaction</th><th>Type</th><th>Store</th><th>SKU</th><th>Advisor</th>
            <th>Client</th><th className="text-right">Qty</th><th className="text-right">Amount</th>
            <th>Payment</th><th>Date</th><th>Time</th>
          </tr></thead>
          <tbody>
            {loading ? (
              [...Array(10)].map((_, i) => <tr key={i}><td colSpan={11}><div className="h-5 bg-paper rounded animate-pulse" /></td></tr>)
            ) : rows.map(t => (
              <tr key={t.transaction_id + t.sku_id + t.transaction_time}>
                <td className="text-ink-faint">{t.transaction_id}</td>
                <td><span className={`text-[10px] px-1.5 py-0.5 rounded border ${TYPE_BADGE[t.transaction_type]}`}>{t.transaction_type}</span></td>
                <td className="text-ink-muted whitespace-nowrap">{STORE_NAMES[t.store_id] ?? t.store_id}</td>
                <td className="text-ink-muted">{t.sku_id}</td>
                <td className="text-ink-faint">{t.advisor_id ?? '—'}</td>
                <td className="text-ink-faint">{t.client_id ?? <span className="text-ink-faint/60 italic">anon</span>}</td>
                <td className="text-right">{t.quantity}</td>
                <td className="text-right font-medium text-ink whitespace-nowrap">{Number(t.unit_price).toLocaleString()} {t.currency}</td>
                <td className="text-ink-faint">{t.payment_method}</td>
                <td className="text-ink-faint whitespace-nowrap">{t.transaction_date}</td>
                <td className="text-ink-faint">{t.transaction_time?.slice(0,5)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between mt-4 text-xs font-mono text-ink-muted">
        <button disabled={page === 0} onClick={() => setPage(p => p - 1)}
          className="px-3 py-1.5 border border-paper-border rounded-sm disabled:opacity-30 hover:bg-paper-hover">← Prev</button>
        <span>Page {page + 1} of {pages || 1}</span>
        <button disabled={page >= pages - 1} onClick={() => setPage(p => p + 1)}
          className="px-3 py-1.5 border border-paper-border rounded-sm disabled:opacity-30 hover:bg-paper-hover">Next →</button>
      </div>
    </div>
  )
}
