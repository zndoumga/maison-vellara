'use client'
import { useEffect, useState, useCallback } from 'react'
import { supabase } from '@/lib/supabase'
import { STORE_NAMES } from '@/lib/constants'
import PageHeader from '@/components/PageHeader'

interface Snap {
  store_id: string; sku_id: string; qty_on_hand: number; qty_reserved: number
  qty_in_transit: number; last_replenishment_dt: string | null; reorder_flag: boolean
  snapshot_ts: string
}

export default function InventoryPage() {
  const [rows, setRows] = useState<Snap[]>([])
  const [store, setStore] = useState('ST001')
  const [latestDate, setLatestDate] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [onlyAlerts, setOnlyAlerts] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    // find latest snapshot timestamp for this store
    const { data: latest } = await supabase.schema('inventory').from('snapshots')
      .select('snapshot_ts').eq('store_id', store)
      .order('snapshot_ts', { ascending: false }).limit(1)
    const ts = latest?.[0]?.snapshot_ts
    if (!ts) { setRows([]); setLoading(false); return }
    const day = ts.slice(0, 10)
    setLatestDate(day)
    let q = supabase.schema('inventory').from('snapshots')
      .select('*').eq('store_id', store)
      .gte('snapshot_ts', `${day}T00:00:00`).lte('snapshot_ts', `${day}T23:59:59`)
      .order('sku_id')
    if (onlyAlerts) q = q.eq('reorder_flag', true)
    const { data } = await q
    setRows((data as Snap[]) ?? [])
    setLoading(false)
  }, [store, onlyAlerts])

  useEffect(() => { load() }, [load])

  const totalUnits = rows.reduce((s, r) => s + Math.max(r.qty_on_hand, 0), 0)
  const alertCount = rows.filter(r => r.reorder_flag).length

  return (
    <div className="p-6 md:p-8 max-w-[1400px] mx-auto">
      <PageHeader title="Inventory" subtitle="Stock positions — Source 1 · Supabase Postgres" />

      <div className="flex flex-wrap gap-3 mb-4 items-center">
        <select value={store} onChange={e => setStore(e.target.value)}
          className="bg-white border border-paper-border rounded-sm px-3 py-1.5 text-xs font-mono text-ink">
          {Object.entries(STORE_NAMES).map(([id, name]) => <option key={id} value={id}>{name}</option>)}
        </select>
        <label className="flex items-center gap-2 text-xs font-mono text-ink-muted cursor-pointer">
          <input type="checkbox" checked={onlyAlerts} onChange={e => setOnlyAlerts(e.target.checked)} className="accent-gold" />
          Reorder alerts only
        </label>
        <div className="ml-auto flex gap-4 text-xs font-mono text-ink-faint">
          <span>{rows.length} SKUs</span>
          <span>{totalUnits} units on hand</span>
          <span className={alertCount > 0 ? 'text-red-600' : 'text-emerald-600'}>{alertCount} alerts</span>
          {latestDate && <span>as of {latestDate}</span>}
        </div>
      </div>

      <div className="card overflow-x-auto">
        <table>
          <thead><tr>
            <th>SKU</th><th className="text-right">On Hand</th><th className="text-right">Reserved</th>
            <th className="text-right">In Transit</th><th>Last Replenished</th><th>Status</th>
          </tr></thead>
          <tbody>
            {loading ? (
              [...Array(12)].map((_, i) => <tr key={i}><td colSpan={6}><div className="h-5 bg-paper rounded animate-pulse" /></td></tr>)
            ) : rows.map(r => (
              <tr key={r.sku_id}>
                <td className="text-ink-muted">{r.sku_id}</td>
                <td className={`text-right font-medium ${r.qty_on_hand < 0 ? 'text-red-600' : r.qty_on_hand === 0 ? 'text-orange-600' : 'text-ink'}`}>{r.qty_on_hand}</td>
                <td className="text-right text-ink-faint">{r.qty_reserved}</td>
                <td className="text-right text-ink-faint">{r.qty_in_transit}</td>
                <td className="text-ink-faint whitespace-nowrap">{r.last_replenishment_dt ?? '—'}</td>
                <td>
                  {r.reorder_flag
                    ? <span className={`text-[10px] px-1.5 py-0.5 rounded border ${r.qty_on_hand < 0 ? 'text-red-600 bg-red-50 border-red-200' : 'text-amber-700 bg-amber-50 border-amber-200'}`}>
                        {r.qty_on_hand < 0 ? 'OVERALLOCATED' : 'REORDER'}</span>
                    : <span className="text-[10px] px-1.5 py-0.5 rounded border text-emerald-700 bg-emerald-50 border-emerald-200">OK</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-[10px] text-ink-faint mt-3 font-mono">
        Negative on-hand reflects the timing window between a recorded sale and replenishment receipt — a realistic operational artefact for dbt to resolve.
      </p>
    </div>
  )
}
